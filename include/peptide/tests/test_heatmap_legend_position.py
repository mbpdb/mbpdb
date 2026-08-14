"""
Tests for the heatmap "Legend Position" option.

'right' keeps the historical single combined legend beside the plot; 'below'
splits each legend group into its own unit under the x-axis, the units laid
out side by side (wrapping to further rows when they would not fit).

Run with:
    cd /home/kuhfeldrf/mbpdb/include/peptide
    /home/kuhfeldrf/mbpdb/.venv/bin/python -m pytest tests/test_heatmap_legend_position.py -v
"""
import unittest

import numpy as np
import pandas as pd

# conftest.py bootstraps Django; import the service directly.
from peptide.heatmap_viz.services import heatmap_renderer as R

SEQ = 'MKVLILACLVALALARELEELNVPGEIVESLSSSEESITRINKKIEKFQSEEQQQTEDELQDKIHPF'
LEGEND_TITLES = ['Sample Type:', 'Peptide Counts:', 'Average Abundance:', '',
                 'Average Abundance:']
Y_TICKS = [1e4, 5e5, 1e6]


def _make_var(label, seed):
    rng = np.random.default_rng(seed)
    n = len(SEQ)
    counts = rng.integers(0, 8, n)
    ms = rng.random(n) * 1e6 + 1e4
    return {
        'protein_id': 'P02666', 'protein_name': 'Beta-casein', 'label': label,
        'var_label': label, 'protein_sequence': SEQ, 'AA_list': list(SEQ),
        'peptide_counts': pd.Series(counts), 'ms_data': pd.Series(ms),
        'ms_data_list': list(ms),
        'heatmap_df': pd.DataFrame({'count': counts, 'average': ms, 'AA': list(SEQ)}),
        'bioactive_peptide_abs_df': pd.DataFrame({'average': ms}),
        'bioactive_peptide_func_df': pd.DataFrame(),
    }


def _vars():
    return {'High': _make_var('High NE', 1), 'Low': _make_var('Low NE', 2)}


def _interactive(orientation, legend_position):
    import matplotlib.pyplot as plt
    R.max_count, R.num_colors = 8, 6
    return R.visualize_sequence_heatmap_interactive(
        _vars(), orientation, 'Beta-casein Sequence', 'Averaged Peptide Abundance',
        LEGEND_TITLES, plt.get_cmap('RdYlGn_r'), plt.get_cmap('Dark2'), 'Set3',
        [], [], 'yes', 'no', 'all-peptides', False, Y_TICKS,
        legend_position=legend_position,
    )


def _compact(legend_position):
    import matplotlib.pyplot as plt
    R.max_count, R.num_colors = 8, 6
    return R.visualize_sequence_heatmap_compact(
        _vars(), 'Beta-casein Sequence', 'Abundance', LEGEND_TITLES,
        plt.get_cmap('RdYlGn_r'), Y_TICKS, False,
        legend_position=legend_position,
    )


def _legends(fig):
    """All populated legend objects on the figure, keyed by layout name."""
    out = {}
    for key in ('legend', 'legend2', 'legend3', 'legend4'):
        leg = getattr(fig.layout, key, None)
        if leg is not None and leg.to_plotly_json():
            out[key] = leg
    return out


class TestNormalizeLegendPosition(unittest.TestCase):
    def test_below_aliases(self):
        for value in ('below', 'Below', ' bottom ', 'under'):
            self.assertEqual(R.normalize_legend_position(value), 'below')

    def test_default_and_unknown_fall_back_to_right(self):
        for value in (None, '', 'right', 'left', 'nonsense'):
            self.assertEqual(R.normalize_legend_position(value), 'right')


class TestRightIsUnchanged(unittest.TestCase):
    """'right' must keep the one combined, vertically-stacked legend."""

    def test_single_vertical_legend_with_group_titles(self):
        for orientation in ('Landscape', 'Portrait'):
            with self.subTest(orientation=orientation):
                fig = _interactive(orientation, 'right')
                legends = _legends(fig)
                self.assertEqual(list(legends), ['legend'])
                self.assertEqual(legends['legend'].orientation, 'v')
                # every visible entry carries its group header inside that legend
                titles = {t.legendgrouptitle.text for t in fig.data if t.showlegend}
                self.assertIn('Sample Type:', titles)
                self.assertIn('Peptide Counts:', titles)
                # nothing is routed to a secondary legend
                self.assertFalse([t for t in fig.data if t.legend not in (None, 'legend')])
                # width is still reserved on the right for it
                self.assertGreaterEqual(fig.layout.margin.r, 180)


class TestBelowSplitsIntoUnits(unittest.TestCase):
    def test_landscape_two_units_side_by_side(self):
        fig = _interactive('Landscape', 'below')
        legends = _legends(fig)
        self.assertEqual(sorted(legends), ['legend', 'legend2'])
        self.assertEqual([legends[k].title.text for k in ('legend', 'legend2')],
                         ['Sample Type:', 'Peptide Counts:'])
        for leg in legends.values():
            self.assertEqual(leg.orientation, 'h')     # items run across, not down
            self.assertLess(leg.y, 0)                  # under the x-axis
            self.assertEqual(leg.yanchor, 'top')
        # one row → same y, drawn left to right within the figure
        self.assertEqual(legends['legend'].y, legends['legend2'].y)
        self.assertLess(legends['legend'].x, legends['legend2'].x)
        for leg in legends.values():
            self.assertTrue(0 < leg.x < 1)
            self.assertEqual(leg.xanchor, 'center')

    def test_portrait_adds_the_abundance_unit(self):
        fig = _interactive('Portrait', 'below')
        titles = [leg.title.text for leg in _legends(fig).values()]
        self.assertEqual(sorted(titles),
                         ['Average Abundance:', 'Peptide Counts:', 'Sample Type:'])

    def test_compact_two_units(self):
        fig = _compact('below')
        titles = [leg.title.text for leg in _legends(fig).values()]
        self.assertEqual(sorted(titles), ['Average Abundance:', 'Peptide Counts:'])

    def test_entries_are_routed_to_their_unit(self):
        fig = _interactive('Landscape', 'below')
        by_legend = {}
        for trace in fig.data:
            if trace.showlegend:
                by_legend.setdefault(trace.legend, []).append(trace.name)
        self.assertEqual(sorted(by_legend['legend']), ['High NE', 'Low NE'])
        self.assertTrue(all('-' in n for n in by_legend['legend2']))
        # no legendgroup survives: inside a horizontal legend Plotly would lay
        # each group out as its own vertical column.
        self.assertFalse([t for t in fig.data if t.showlegend and t.legendgroup])

    def test_width_moves_from_the_right_margin_to_the_bottom(self):
        right = _interactive('Landscape', 'right')
        below = _interactive('Landscape', 'below')
        self.assertLess(below.layout.margin.r, right.layout.margin.r)
        self.assertGreater(below.layout.margin.b, right.layout.margin.b)
        # the plot rows themselves are untouched — the figure just grows taller
        self.assertGreater(below.layout.height, right.layout.height)


class TestUnitPacking(unittest.TestCase):
    def test_units_wrap_to_a_second_row_when_too_wide(self):
        units = {
            f'Group {i}:': {'ref': 'legend' if i == 0 else f'legend{i + 1}',
                            'labels': [f'entry {j}' for j in range(6)]}
            for i in range(4)
        }
        rows = R._pack_legend_rows(units, 15)
        self.assertGreater(len(rows), 1)
        self.assertEqual(sum(len(r) for r in rows), 4)
        # each row stays within the reference width
        for row in rows:
            span = (sum(w for _, _, w in row)
                    + R.LEGEND_UNIT_GAP_PX * (len(row) - 1))
            self.assertLessEqual(span, R.LEGEND_REF_WIDTH_PX)
        # rows stack downwards, each row centred on its own y
        layout = R._below_legend_layout(units, 15, plot_area_px=600)
        ys = sorted({leg['y'] for leg in layout.values()}, reverse=True)
        self.assertEqual(len(ys), len(rows))
        self.assertTrue(all(y < 0 for y in ys))

    def test_each_row_is_centred_on_the_figure(self):
        units = {
            'Sample Type:': {'ref': 'legend', 'labels': ['High NE', 'Low NE']},
            'Peptide Counts:': {'ref': 'legend2',
                                'labels': ['1 - 2', '2 - 3', '3 - 4']},
        }
        layout = R._below_legend_layout(units, 15, plot_area_px=600)
        for row in R._pack_legend_rows(units, 15):
            # left edge of the first unit and right edge of the last, in the
            # same paper fractions Plotly positions them with
            first_ref, _, first_w = row[0]
            last_ref, _, last_w = row[-1]
            left = layout[first_ref]['x'] - first_w / (2 * R.LEGEND_REF_WIDTH_PX)
            right = layout[last_ref]['x'] + last_w / (2 * R.LEGEND_REF_WIDTH_PX)
            self.assertAlmostEqual((left + right) / 2, 0.5, places=6)

    def test_strip_height_grows_with_row_count(self):
        one = {'A:': {'ref': 'legend', 'labels': ['x']}}
        many = {
            f'Group {i}:': {'ref': f'legend{i + 1}',
                            'labels': [f'entry {j}' for j in range(6)]}
            for i in range(4)
        }
        self.assertLess(R._below_legend_strip_px(one, 15),
                        R._below_legend_strip_px(many, 15))


if __name__ == '__main__':
    unittest.main()
