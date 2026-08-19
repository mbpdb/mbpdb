"""
Tests for the derived plot filter (Data Analysis).

The "Plot Filter" dropdown was removed from the UI: what the user selects in the
Proteins / Functions selectors *is* the filter. Each selector carries an explicit
"None" sentinel so that "no filter on this dimension" stays distinguishable from
"every protein / every function" — those are different plots, and the old
dropdown made the distinction impossible to express.
"""
import unittest

import numpy as np
import pandas as pd

from peptide.data_analysis.services.data_processor import (
    ALL_PROTEINS,
    ALL_FUNCTIONAL,
    NON_FUNCTIONAL,
    NO_FUNCTION_FILTER,
    NO_PROTEIN_FILTER,
    DataAnalysisState,
    derive_plot_filter,
)


class TestDerivePlotFilter(unittest.TestCase):
    def test_none_in_both_is_no_filter(self):
        self.assertEqual(
            derive_plot_filter([NO_PROTEIN_FILTER], [NO_FUNCTION_FILTER]),
            'No Filter')

    def test_empty_selections_are_no_filter(self):
        self.assertEqual(derive_plot_filter([], []), 'No Filter')

    def test_proteins_only(self):
        self.assertEqual(
            derive_plot_filter(['P02666'], [NO_FUNCTION_FILTER]),
            'Selected Protein(s)')

    def test_functions_only(self):
        self.assertEqual(
            derive_plot_filter([NO_PROTEIN_FILTER], ['ACE-inhibitory']),
            'Selected Function(s)')

    def test_both_selected_is_both(self):
        self.assertEqual(
            derive_plot_filter(['P02666'], ['ACE-inhibitory']), 'Both')

    def test_all_proteins_is_a_real_filter_not_no_filter(self):
        # The ambiguity that motivated the change: "every protein" means break
        # the plot out per protein, which is NOT the same as no filter at all.
        self.assertEqual(
            derive_plot_filter([ALL_PROTEINS], [NO_FUNCTION_FILTER]),
            'Selected Protein(s)')

    def test_all_proteins_and_all_functions_is_both(self):
        self.assertEqual(
            derive_plot_filter([ALL_PROTEINS], [ALL_FUNCTIONAL]), 'Both')

    def test_all_functional_plus_non_functional_is_the_split_mode(self):
        self.assertEqual(
            derive_plot_filter([NO_PROTEIN_FILTER], [ALL_FUNCTIONAL, NON_FUNCTIONAL]),
            'Functional vs Non-Functional Peptides')

    def test_split_mode_wins_over_a_protein_selection(self):
        self.assertEqual(
            derive_plot_filter(['P02666'], [ALL_FUNCTIONAL, NON_FUNCTIONAL]),
            'Functional vs Non-Functional Peptides')

    def test_non_functional_alone_is_a_function_filter(self):
        self.assertEqual(
            derive_plot_filter([NO_PROTEIN_FILTER], [NON_FUNCTIONAL]),
            'Selected Function(s)')


class TestStateDerivesFilter(unittest.TestCase):
    GROUPS = ['A', 'B']

    def _dataset(self):
        reps = {g: [f'{g}_1', f'{g}_2', f'{g}_3'] for g in self.GROUPS}
        rows = []
        for i in range(8):
            # Half the peptides carry no function annotation at all.
            fn = 'ACE-inhibitory' if i % 2 == 0 else np.nan
            prot = 'P02666' if i < 4 else 'P02662'
            row = {'Unique Peptide ID': f'pep{i}', 'Protein': prot, 'function': fn}
            for g in self.GROUPS:
                for rc in reps[g]:
                    row[rc] = 100.0 + i
                row[f'Avg_{g}'] = 100.0 + i
            rows.append(row)
        protein_dict = {'P02666': {'name': 'Beta-casein'},
                        'P02662': {'name': 'Alpha-S1-casein'}}
        return pd.DataFrame(rows), reps, protein_dict

    def _state(self, **extra):
        merged, reps, pdct = self._dataset()
        params = dict(selected_groups=self.GROUPS, abs_or_count='Abundance',
                      metric_type='Absolute', orientation='By Sample')
        params.update(extra)
        st = DataAnalysisState(merged, reps, pdct, params)
        st.run_pipeline()
        return st

    def test_defaults_to_no_filter(self):
        # No selections supplied at all -> the whole dataset, as before.
        st = self._state()
        self.assertEqual(st.plot_filter, 'No Filter')
        self.assertEqual(len(st.filtered_df), 8)

    def test_explicit_plot_filter_still_wins(self):
        # Programmatic callers (and the existing test suite) may pin the mode.
        st = self._state(selected_proteins=['P02666'], plot_filter='No Filter')
        self.assertEqual(st.plot_filter, 'No Filter')
        self.assertEqual(len(st.filtered_df), 8)

    def test_protein_selection_filters_rows(self):
        st = self._state(selected_proteins=['P02666'],
                         selected_functions=[NO_FUNCTION_FILTER])
        self.assertEqual(st.plot_filter, 'Selected Protein(s)')
        self.assertEqual(set(st.filtered_df['Protein']), {'P02666'})

    def test_none_sentinel_leaves_rows_untouched(self):
        st = self._state(selected_proteins=[NO_PROTEIN_FILTER],
                         selected_functions=[NO_FUNCTION_FILTER])
        self.assertEqual(len(st.filtered_df), 8)
        # Resolution still yields a concrete protein list for downstream lookups.
        self.assertEqual(set(st.selected_proteins), {'P02666', 'P02662'})

    def test_sentinel_is_never_treated_as_a_protein_id(self):
        st = self._state(selected_proteins=[NO_PROTEIN_FILTER, 'P02666'],
                         selected_functions=[NO_FUNCTION_FILTER])
        self.assertNotIn(NO_PROTEIN_FILTER, st.selected_proteins)
        self.assertEqual(st.selected_proteins, ['P02666'])

    def test_sentinel_is_never_treated_as_a_function(self):
        st = self._state(selected_functions=[NO_FUNCTION_FILTER, 'ACE-inhibitory'])
        self.assertNotIn(NO_FUNCTION_FILTER, st.selected_functions)
        self.assertEqual(st.selected_functions, ['ACE-inhibitory'])

    def test_split_mode_keeps_both_categories(self):
        st = self._state(selected_functions=[ALL_FUNCTIONAL, NON_FUNCTIONAL])
        self.assertEqual(st.plot_filter, 'Functional vs Non-Functional Peptides')
        self.assertEqual(st.selected_functions,
                         ['Functional Peptides', 'Non-Functional Peptides'])
        # The split happens downstream, so no row is dropped.
        self.assertEqual(len(st.filtered_df), 8)
        self.assertIn('Non-Functional Peptides',
                      set(st.function_df['Description']))

    def test_split_mode_still_honours_a_protein_selection(self):
        # New: the removed dropdown made these two mutually exclusive.
        st = self._state(selected_proteins=['P02666'],
                         selected_functions=[ALL_FUNCTIONAL, NON_FUNCTIONAL])
        self.assertEqual(st.plot_filter, 'Functional vs Non-Functional Peptides')
        self.assertEqual(set(st.filtered_df['Protein']), {'P02666'})

    def test_non_functional_only_keeps_unannotated_peptides(self):
        st = self._state(selected_functions=[NON_FUNCTIONAL])
        self.assertEqual(st.plot_filter, 'Selected Function(s)')
        self.assertTrue(st.filtered_df['function'].isna().all())


if __name__ == '__main__':
    unittest.main()
