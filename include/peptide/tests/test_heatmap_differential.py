"""
Tests for the heatmap differential-comparison feature
(manuscript/docs/HEATMAP_DIFFERENTIAL_STATS.md).

Step 1 — replicate-aware loader: the heatmap data_processor must parse the
``"<col> 'Grouped: (Group)'"`` replicate framework and surface per-group
replicate columns so a pooled SD (Cohen's d) can be computed downstream.

Run with:
    cd /home/kuhfeldrf/mbpdb/include/peptide
    /home/kuhfeldrf/mbpdb/.venv/bin/python -m pytest tests/test_heatmap_differential.py -v
"""
import io
import unittest

import numpy as np
import pandas as pd

# conftest.py bootstraps Django; import the services directly.
from peptide.heatmap_viz.services import data_processor as hdp
from peptide.heatmap_viz.services import heatmap_renderer as hdp_render


def _csv_bytes(df: pd.DataFrame) -> io.BytesIO:
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf


class TestParseGroupedReplicates(unittest.TestCase):
    def test_parses_and_renames(self):
        df = pd.DataFrame({
            'Protein': ['P02666'],
            "S1 'Grouped: (Bitter)'": [10],
            "S2 'Grouped: (Bitter)'": [12],
            "S3 'Grouped: (NonBitter)'": [3],
        })
        renamed, reps = hdp._parse_grouped_replicates(df)
        self.assertEqual(reps, {'Bitter': ['S1', 'S2'], 'NonBitter': ['S3']})
        # Columns renamed back to base names for indexing by replicate.
        self.assertIn('S1', renamed.columns)
        self.assertNotIn("S1 'Grouped: (Bitter)'", renamed.columns)

    def test_multi_group_membership(self):
        # A replicate can belong to more than one group (semicolon list).
        df = pd.DataFrame({"S1 'Grouped: (A; B)'": [1]})
        _, reps = hdp._parse_grouped_replicates(df)
        self.assertEqual(reps, {'A': ['S1'], 'B': ['S1']})

    def test_no_grouped_columns_is_noop(self):
        df = pd.DataFrame({'Protein': ['P1'], 'Avg_X': [1.0]})
        renamed, reps = hdp._parse_grouped_replicates(df)
        self.assertEqual(reps, {})
        self.assertTrue(renamed.equals(df))


class TestLoadMergedFileReplicates(unittest.TestCase):
    def _df(self):
        return pd.DataFrame({
            'Protein': ['P02666', 'P02666'],
            'start': [60, 73],
            'end': [68, 79],
            'Unique Peptide ID': ['pep1', 'pep2'],
            "S1 'Grouped: (Bitter)'": [10, 5],
            "S2 'Grouped: (Bitter)'": [12, 6],
            "S3 'Grouped: (Bitter)'": [11, 4],
            "S4 'Grouped: (NonBitter)'": [3, 8],
            "S5 'Grouped: (NonBitter)'": [2, 9],
            "S6 'Grouped: (NonBitter)'": [4, 7],
            'Avg_Bitter': [11.0, 5.0],
            'Avg_NonBitter': [3.0, 8.0],
        })

    def test_replicate_columns_attached(self):
        df, gdd, pdict, col_order, err = hdp.load_merged_file(
            _csv_bytes(self._df()), 'merged.csv')
        self.assertIsNone(err)
        # group_data_dict keyed by ordinal; Bitter first, NonBitter second.
        by_var = {v['grouping_variable']: v for v in gdd.values()}
        self.assertEqual(by_var['Bitter']['replicate_columns'], ['S1', 'S2', 'S3'])
        self.assertEqual(by_var['NonBitter']['replicate_columns'], ['S4', 'S5', 'S6'])
        self.assertEqual(sorted(col_order), ['Bitter', 'NonBitter'])

    def test_single_average_file_disables_comparison(self):
        # No 'Grouped:' columns -> replicate_columns empty, load still succeeds.
        df = pd.DataFrame({
            'Protein': ['P02666'], 'start': [60], 'end': [68],
            'Unique Peptide ID': ['pep1'],
            'Avg_Bitter': [11.0], 'Avg_NonBitter': [3.0],
        })
        _, gdd, _, _, err = hdp.load_merged_file(_csv_bytes(df), 'merged.csv')
        self.assertIsNone(err)
        for v in gdd.values():
            self.assertEqual(v['replicate_columns'], [])


class TestContrastTrack(unittest.TestCase):
    """Step 4 — per-position contrast builder over replicate position-means."""

    def _peptides(self):
        # Two peptides spanning a 10-residue protein; 3 replicates per group.
        # Bitter reps clearly higher than NonBitter at every covered position.
        return pd.DataFrame({
            'start': [1, 4],
            'end': [5, 8],
            'B1': [10, 20], 'B2': [12, 22], 'B3': [11, 21],
            'N1': [3, 5], 'N2': [2, 6], 'N3': [4, 4],
        })

    def test_position_means_shape_and_drop(self):
        seq = 'ACDEFGHIKL'  # length 10
        m = hdp_render.calculate_replicate_position_means(seq, self._peptides(), ['B1', 'B2', 'B3'])
        self.assertEqual(list(m.columns), ['B1', 'B2', 'B3'])
        self.assertEqual(len(m), 10)
        # position 1 (index 0) covered only by peptide 1 -> B1 == 10
        self.assertAlmostEqual(m.iloc[0]['B1'], 10.0)
        # positions 9-10 (index 8,9) covered by neither peptide -> NaN (dropped)
        self.assertTrue(m.iloc[8].isna().all())

    def test_smd_positive_when_a_higher(self):
        seq = 'ACDEFGHIKL'
        peps = self._peptides()
        a = hdp_render.calculate_replicate_position_means(seq, peps, ['B1', 'B2', 'B3'])
        b = hdp_render.calculate_replicate_position_means(seq, peps, ['N1', 'N2', 'N3'])
        track = hdp_render.calculate_contrast_track(a, b, metric='smd')
        self.assertEqual(len(track), 10)
        # covered positions: Bitter >> NonBitter -> strongly positive d
        self.assertGreater(track[0], 1.0)
        # uncovered tail -> NaN gap, not a value
        self.assertTrue(np.isnan(track[8]))

    def test_log2fc_metric(self):
        seq = 'ACDEFGHIKL'
        peps = self._peptides()
        a = hdp_render.calculate_replicate_position_means(seq, peps, ['B1', 'B2', 'B3'])
        b = hdp_render.calculate_replicate_position_means(seq, peps, ['N1', 'N2', 'N3'])
        track = hdp_render.calculate_contrast_track(a, b, metric='log2fc')
        self.assertGreater(track[0], 0)  # A higher -> positive log2FC

    def test_unequal_length_alignment(self):
        # Shorter B frame -> positions beyond it are NaN, no crash.
        a = pd.DataFrame({'r1': [1.0, 2.0, 3.0], 'r2': [1.1, 2.1, 3.1], 'r3': [0.9, 1.9, 2.9]})
        b = pd.DataFrame({'s1': [0.1, 0.2], 's2': [0.1, 0.2], 's3': [0.1, 0.2]})
        track = hdp_render.calculate_contrast_track(a, b, metric='smd')
        self.assertEqual(len(track), 3)
        self.assertTrue(np.isnan(track[2]))


class TestSignedYTicks(unittest.TestCase):
    """Step 5 — symmetric diverging axis for the SMD / log2FC track."""

    def test_symmetric_about_zero(self):
        ticks = hdp_render.calculate_signed_y_ticks(-0.3, 0.54)
        self.assertEqual(ticks[1], 0.0)
        self.assertEqual(ticks[0], -ticks[2])

    def test_bound_covers_max_magnitude(self):
        # bound must be >= the largest |value| seen
        for lo, hi in [(-0.3, 0.54), (-3.49, 1.2), (-0.1, 0.05)]:
            ticks = hdp_render.calculate_signed_y_ticks(lo, hi)
            self.assertGreaterEqual(ticks[2], max(abs(lo), abs(hi)))

    def test_negative_dominant(self):
        ticks = hdp_render.calculate_signed_y_ticks(-3.49, 0.2)
        self.assertGreaterEqual(ticks[2], 3.49)
        self.assertEqual(ticks[0], -ticks[2])

    def test_degenerate_and_nan(self):
        self.assertEqual(hdp_render.calculate_signed_y_ticks(0, 0), [-1.0, 0.0, 1.0])
        self.assertEqual(
            hdp_render.calculate_signed_y_ticks(float('nan'), float('nan')),
            [-1.0, 0.0, 1.0])


if __name__ == '__main__':
    unittest.main()
