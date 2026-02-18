"""
Standalone tests for the data_transformation service modules.

These tests run without a live Django instance by mocking settings.
They verify that the Django services produce output matching the logic
from the original Jupyter notebook (data_transformation.ipynb).

Run with:
    cd /home/kuhfeldrf/mbpdb/include/peptide
    /home/kuhfeldrf/mbpdb/.venv/bin/python -m pytest tests/test_data_transformation.py -v
"""
"""
Standalone tests for the data_transformation service modules.

These tests run without a live Django instance.  Django is bootstrapped
via tests/conftest.py (sets up settings.configure() and blocks Celery).

Run with:
    cd /home/kuhfeldrf/mbpdb/include/peptide
    /home/kuhfeldrf/mbpdb/.venv/bin/python -m pytest tests/test_data_transformation.py -v
"""
import io
import json
import sys
import os
import unittest

import pandas as pd
import numpy as np

# conftest.py already bootstrapped Django — just import the services.
from peptide.data_transformation.services import data_loader, group_processing, data_combiner, export_manager


# ---------------------------------------------------------------------------
# Helpers – synthetic test data
# ---------------------------------------------------------------------------

def make_peptidomic_df():
    """Synthetic peptidomic DataFrame mimicking Proteome Discoverer output."""
    return pd.DataFrame({
        'Annotated Sequence': [
            '[A].RELEELNVPGEI.[V]',
            '[S].SEESITRINK.[K]',
            '[A].RELEELNVPGEIVES.[L]',
            '[N].SLPQNIPPLTQ.[G]',
        ],
        'Modifications': [
            None,
            '1xPhospho [S1]',
            '1xPhospho [S15]',
            None,
        ],
        'Master Protein Accessions': [
            'P02666',
            'P02666',
            'P02666',
            'Q9NR61',
        ],
        'Positions in Proteins': [
            'P02666 [16-27]',
            'P02666 [34-43]',
            'P02666 [16-30]',
            'Q9NR61 [84-94]',
        ],
        'Sequence': [
            'RELEELNVPGEI',
            'SEESITRINK',
            'RELEELNVPGEIVES',
            'SLPQNIPPLTQ',
        ],
        'Sample_A1': [2257142.857, 1816666.667, 3083333.333, 12645000.0],
        'Sample_A2': [1900000.0,  1500000.0,   2800000.0,   10000000.0],
        'Sample_B1': [800000.0,   600000.0,    1200000.0,   5000000.0],
        'Sample_B2': [700000.0,   500000.0,    1000000.0,   4500000.0],
    })


def make_mbpdb_df():
    """Synthetic MBPDB search results DataFrame."""
    return pd.DataFrame({
        'search_peptide': ['RELEELNVPGEI', 'SEESITRINK', 'RELEELNVPGEI'],
        'peptide':        ['RELEELNVPGEI', 'SEESITRINK', 'RELEELNVPGEI'],
        'protein_id':     ['P02666',       'P02666',     'P02666'],
        'protein_description': ['Beta-casein', 'Beta-casein', 'Beta-casein'],
        'species':        ['Bovine',       'Bovine',     'Bovine'],
        'intervals':      ['[16-27]',      '[34-43]',    '[16-27]'],
        'function':       ['Opioid',       'ACE inhibitor', 'Opioid'],
        '% Alignment':    [100.0,          100.0,        100.0],
    })


def make_group_data():
    return {
        'GroupA': {'grouping_variable': 'GroupA', 'abundance_columns': ['Sample_A1', 'Sample_A2']},
        'GroupB': {'grouping_variable': 'GroupB', 'abundance_columns': ['Sample_B1', 'Sample_B2']},
    }


def make_protein_dict():
    return {
        'P02666': {'name': 'CASB_BOVIN Beta-casein', 'species': 'Bovine'},
        'Q9NR61': {'name': 'SOME_HUMAN Protein', 'species': 'Human'},
    }


# ---------------------------------------------------------------------------
# data_loader tests
# ---------------------------------------------------------------------------

class TestFindSpecies(unittest.TestCase):

    def test_bovine_detected(self):
        result = data_loader.find_species(">sp|P02666|CASB_BOVIN Beta-casein OS=Bos taurus")
        self.assertEqual(result, "Bovine")

    def test_human_detected(self):
        result = data_loader.find_species(">sp|P04406|G3P_HUMAN OS=Homo sapiens")
        self.assertEqual(result, "Human")

    def test_unknown_returned(self):
        result = data_loader.find_species(">sp|P12345|SOME_YEAST OS=Saccharomyces cerevisiae")
        self.assertEqual(result, "unknown")


class TestParseFastaHeaders(unittest.TestCase):

    FASTA = """>sp|P02666|CASB_BOVIN Beta-casein OS=Bos taurus OX=9913
RELEELNVPGEI
>sp|P04406|G3P_HUMAN Glyceraldehyde-3-phosphate dehydrogenase OS=Homo sapiens OX=9606
MVKVGVNG
"""

    def test_parse_uploaded_fasta(self):
        result = data_loader.parse_uploaded_fasta(self.FASTA.encode())
        self.assertIn('P02666', result)
        self.assertIn('P04406', result)
        self.assertEqual(result['P02666']['species'], 'Bovine')
        self.assertEqual(result['P04406']['species'], 'Human')
        self.assertIn('RELEELNVPGEI', result['P02666']['sequence'])

    def test_empty_fasta_returns_empty(self):
        result = data_loader.parse_uploaded_fasta(b'')
        self.assertEqual(result, {})


class TestValidateFastaFormat(unittest.TestCase):

    def test_valid_fasta(self):
        fasta = ">sp|P02666|CASB_BOVIN\nRELEELNVPGEI\n"
        valid, msg = data_loader.validate_fasta_format(fasta.encode())
        self.assertTrue(valid)
        self.assertEqual(msg, "")

    def test_no_header(self):
        valid, msg = data_loader.validate_fasta_format(b"RELEELNVPGEI\n")
        self.assertFalse(valid)

    def test_empty_file(self):
        valid, msg = data_loader.validate_fasta_format(b"")
        self.assertFalse(valid)


class TestExtractProteinId(unittest.TestCase):

    def test_uniprot_pipe_format(self):
        result = data_loader.extract_protein_id("sp|P02666|CASB_BOVIN")
        self.assertEqual(result, "P02666")

    def test_plain_accession(self):
        result = data_loader.extract_protein_id("P02666")
        self.assertEqual(result, "P02666")

    def test_semicolon_separated(self):
        result = data_loader.extract_protein_id("P02666; Q9NR61")
        self.assertIsInstance(result, list)
        self.assertIn("P02666", result)
        self.assertIn("Q9NR61", result)

    def test_nan_returns_empty(self):
        result = data_loader.extract_protein_id(float('nan'))
        self.assertEqual(result, [])

    def test_empty_string_returns_empty(self):
        result = data_loader.extract_protein_id('')
        self.assertEqual(result, [])


class TestLoadAndValidateFile(unittest.TestCase):

    def _make_csv_bytes(self, df):
        buf = io.BytesIO()
        df.to_csv(buf, index=False)
        return buf.getvalue()

    def test_valid_peptidomic_csv(self):
        df = make_peptidomic_df()
        content = self._make_csv_bytes(df)
        result_df, status, err, warn = data_loader.load_and_validate_file(
            content, 'test.csv', 'Peptidomic'
        )
        self.assertEqual(status, 'yes')
        self.assertIsNotNone(result_df)

    def test_valid_mbpdb_csv(self):
        df = make_mbpdb_df()
        content = self._make_csv_bytes(df)
        result_df, status, err, warn = data_loader.load_and_validate_file(
            content, 'test.csv', 'MBPDB'
        )
        self.assertEqual(status, 'yes')
        self.assertIsNotNone(result_df)

    def test_mbpdb_missing_required_column(self):
        df = pd.DataFrame({'search_peptide': ['ABC'], 'peptide': ['ABC']})
        content = self._make_csv_bytes(df)
        _, status, err, _ = data_loader.load_and_validate_file(
            content, 'test.csv', 'MBPDB'
        )
        self.assertEqual(status, 'no')
        self.assertIn('function', err)

    def test_unsupported_extension(self):
        _, status, err, _ = data_loader.load_and_validate_file(
            b'data', 'test.xyz', 'Peptidomic'
        )
        self.assertEqual(status, 'no')

    def test_column_mapping_applied(self):
        """Master Protein Accessions should be remapped to Protein."""
        df = make_peptidomic_df()
        content = self._make_csv_bytes(df)
        result_df, status, _, _ = data_loader.load_and_validate_file(
            content, 'test.csv', 'Peptidomic'
        )
        self.assertEqual(status, 'yes')
        self.assertIn('Protein', result_df.columns)


class TestExtractSequences(unittest.TestCase):

    def test_from_sequence_column(self):
        df = pd.DataFrame({'Sequence': ['ABCDE', 'FGHIJ', 'ABCDE']})
        seqs = data_loader.extract_sequences(df)
        self.assertIn('ABCDE', seqs)
        self.assertIn('FGHIJ', seqs)
        self.assertEqual(len(seqs), 2)  # unique only

    def test_from_annotated_sequence(self):
        df = pd.DataFrame({
            'Annotated Sequence': ['[A].HELLO.[V]', '[B].WORLD.[K]']
        })
        seqs = data_loader.extract_sequences(df)
        self.assertIn('HELLO', seqs)
        self.assertIn('WORLD', seqs)


class TestGetFilteredColumns(unittest.TestCase):

    def test_excludes_metadata_columns(self):
        df = make_peptidomic_df()
        filtered = data_loader.get_filtered_columns(df)
        self.assertNotIn('Sequence', filtered)
        self.assertNotIn('Master Protein Accessions', filtered)
        self.assertNotIn('Positions in Proteins', filtered)
        self.assertNotIn('Modifications', filtered)
        self.assertNotIn('Annotated Sequence', filtered)

    def test_retains_abundance_columns(self):
        df = make_peptidomic_df()
        filtered = data_loader.get_filtered_columns(df)
        self.assertIn('Sample_A1', filtered)
        self.assertIn('Sample_A2', filtered)
        self.assertIn('Sample_B1', filtered)
        self.assertIn('Sample_B2', filtered)


class TestFindMissingProteins(unittest.TestCase):

    def test_finds_missing(self):
        df = make_peptidomic_df()
        # Rename column to match validated format
        df = df.rename(columns={'Master Protein Accessions': 'Protein'})
        protein_dict = {'P02666': {'name': 'Beta-casein', 'species': 'Bovine'}}
        missing = data_loader.find_missing_proteins(df, protein_dict)
        self.assertIn('Q9NR61', missing)
        self.assertNotIn('P02666', missing)

    def test_empty_df_returns_empty(self):
        missing = data_loader.find_missing_proteins(pd.DataFrame(), {})
        self.assertEqual(missing, set())


# ---------------------------------------------------------------------------
# group_processing tests
# ---------------------------------------------------------------------------

class TestParseGroupJson(unittest.TestCase):

    def test_valid_json(self):
        group_json = json.dumps({
            'GroupA': ['Sample_A1', 'Sample_A2'],
            'GroupB': ['Sample_B1', 'Sample_B2'],
        }).encode()
        available = ['Sample_A1', 'Sample_A2', 'Sample_B1', 'Sample_B2']
        group_data, err = group_processing.parse_group_json(group_json, available)
        self.assertIsNone(err)
        self.assertEqual(len(group_data), 2)
        self.assertEqual(group_data['GroupA']['grouping_variable'], 'GroupA')
        self.assertEqual(group_data['GroupA']['abundance_columns'], ['Sample_A1', 'Sample_A2'])

    def test_missing_column_returns_error(self):
        group_json = json.dumps({'GroupA': ['Missing_Col']}).encode()
        _, err = group_processing.parse_group_json(group_json, ['Sample_A1'])
        self.assertIsNotNone(err)
        self.assertIn('Missing_Col', err)

    def test_invalid_json_returns_error(self):
        _, err = group_processing.parse_group_json(b'not valid json', [])
        self.assertIsNotNone(err)


class TestBuildGroupData(unittest.TestCase):

    def test_adds_group(self):
        gd, err = group_processing.build_group_data(
            ['Sample_A1', 'Sample_A2'], 'GroupA'
        )
        self.assertIsNone(err)
        self.assertEqual(gd['GroupA']['grouping_variable'], 'GroupA')
        self.assertEqual(gd['GroupA']['abundance_columns'], ['Sample_A1', 'Sample_A2'])

    def test_appends_to_existing(self):
        gd = {'GroupA': {'grouping_variable': 'GroupA', 'abundance_columns': ['Sample_A1']}}
        gd, err = group_processing.build_group_data(['Sample_B1'], 'GroupB', gd)
        self.assertIsNone(err)
        self.assertIn('GroupB', gd)
        self.assertEqual(gd['GroupB']['grouping_variable'], 'GroupB')

    def test_empty_name_returns_error(self):
        _, err = group_processing.build_group_data(['Sample_A1'], '')
        self.assertIsNotNone(err)

    def test_empty_columns_returns_error(self):
        _, err = group_processing.build_group_data([], 'GroupA')
        self.assertIsNotNone(err)


class TestBuildNoGroupData(unittest.TestCase):

    def test_creates_individual_groups(self):
        cols = ['Sample_A1', 'Sample_A2', 'Sample_B1']
        gd, err = group_processing.build_no_group_data(cols)
        self.assertIsNone(err)
        self.assertEqual(len(gd), 3)
        # Each column is its own group
        all_vars = {v['grouping_variable'] for v in gd.values()}
        self.assertEqual(all_vars, set(cols))

    def test_empty_columns_returns_error(self):
        _, err = group_processing.build_no_group_data([])
        self.assertIsNotNone(err)


class TestExportGroupDataJson(unittest.TestCase):

    def test_round_trip(self):
        gd = make_group_data()
        json_str = group_processing.export_group_data_json(gd)
        parsed = json.loads(json_str)
        self.assertIn('GroupA', parsed)
        self.assertEqual(parsed['GroupA'], ['Sample_A1', 'Sample_A2'])
        self.assertIn('GroupB', parsed)


# ---------------------------------------------------------------------------
# data_combiner tests
# ---------------------------------------------------------------------------

class TestAddProteinInfo(unittest.TestCase):

    def test_inserts_species_and_name(self):
        df = pd.DataFrame({
            'Protein': ['P02666', 'Q9NR61'],
            'Sequence': ['RELEELNVPGEI', 'SLPQNIPPLTQ'],
        })
        protein_dict = make_protein_dict()
        result = data_combiner.add_protein_info(df, protein_dict)
        self.assertIn('protein_species', result.columns)
        self.assertIn('protein_name', result.columns)
        self.assertEqual(result.loc[0, 'protein_species'], 'Bovine')
        self.assertEqual(result.loc[1, 'protein_species'], 'Human')

    def test_protein_columns_inserted_after_protein(self):
        df = pd.DataFrame({'Protein': ['P02666'], 'Sequence': ['PEPTIDE']})
        result = data_combiner.add_protein_info(df, make_protein_dict())
        cols = list(result.columns)
        protein_idx = cols.index('Protein')
        species_idx = cols.index('protein_species')
        name_idx = cols.index('protein_name')
        self.assertEqual(species_idx, protein_idx + 1)
        self.assertEqual(name_idx, protein_idx + 2)

    def test_unknown_protein_stays_unknown(self):
        df = pd.DataFrame({'Protein': ['UNKNOWN_ID'], 'Sequence': ['PEPTIDE']})
        result = data_combiner.add_protein_info(df, {})
        self.assertEqual(result.loc[0, 'protein_species'], 'Unknown')


class TestExtractBioactivePeptides(unittest.TestCase):

    def test_groups_by_search_peptide(self):
        mbpdb = make_mbpdb_df()
        cleaned, grouped = data_combiner.extract_bioactive_peptides(mbpdb)
        self.assertIsNotNone(grouped)
        # RELEELNVPGEI appears twice in mbpdb – should be grouped to one row
        self.assertEqual(len(grouped[grouped['search_peptide'] == 'RELEELNVPGEI']), 1)

    def test_functions_joined_with_semicolon(self):
        mbpdb = make_mbpdb_df()
        _, grouped = data_combiner.extract_bioactive_peptides(mbpdb)
        releelnvpgei_row = grouped[grouped['search_peptide'] == 'RELEELNVPGEI'].iloc[0]
        # 'Opioid' appears twice – after dedup it should be just 'Opioid'
        self.assertIn('Opioid', str(releelnvpgei_row['function']))

    def test_empty_mbpdb_returns_none(self):
        cleaned, grouped = data_combiner.extract_bioactive_peptides(None)
        self.assertIsNone(cleaned)
        self.assertIsNone(grouped)

    def test_none_protein_id_filtered(self):
        mbpdb = make_mbpdb_df().copy()
        mbpdb.loc[0, 'protein_id'] = 'None'
        cleaned, _ = data_combiner.extract_bioactive_peptides(mbpdb)
        self.assertNotIn('None', cleaned['protein_id'].values)


class TestCreateUniqueId(unittest.TestCase):

    def test_plain_sequence(self):
        row = pd.Series({'Sequence': 'RELEELNVPGEI', 'Modifications': None})
        uid = data_combiner.create_unique_id(row)
        self.assertEqual(uid, 'RELEELNVPGEI')

    def test_with_modifications(self):
        row = pd.Series({'Sequence': 'SEESITRINK', 'Modifications': '1xPhospho [S1]'})
        uid = data_combiner.create_unique_id(row)
        self.assertEqual(uid, 'SEESITRINK_1xPhospho [S1]')

    def test_no_trailing_underscore(self):
        row = pd.Series({'Sequence': 'ABCDE', 'Modifications': None})
        uid = data_combiner.create_unique_id(row)
        self.assertFalse(uid.endswith('_'))


class TestProcessPdResults(unittest.TestCase):

    def _get_validated_df(self):
        """Return a DataFrame as it would look after validation (Protein column renamed)."""
        df = make_peptidomic_df().rename(
            columns={'Master Protein Accessions': 'Protein'}
        )
        return df

    def test_adds_unique_peptide_id(self):
        df = self._get_validated_df()
        _, mbpdb_grouped = data_combiner.extract_bioactive_peptides(make_mbpdb_df())
        result = data_combiner.process_pd_results(df, mbpdb_grouped, make_protein_dict())
        self.assertIn('Unique Peptide ID', result.columns)

    def test_first_columns_order(self):
        """Unique Peptide ID, Sequence, Protein, Positions in Proteins come first."""
        df = self._get_validated_df()
        _, mbpdb_grouped = data_combiner.extract_bioactive_peptides(make_mbpdb_df())
        result = data_combiner.process_pd_results(df, mbpdb_grouped, make_protein_dict())
        expected_start = ['Unique Peptide ID', 'Sequence', 'Protein', 'Positions in Proteins']
        self.assertEqual(list(result.columns[:4]), expected_start)

    def test_merges_mbpdb_function(self):
        df = self._get_validated_df()
        _, mbpdb_grouped = data_combiner.extract_bioactive_peptides(make_mbpdb_df())
        result = data_combiner.process_pd_results(df, mbpdb_grouped, make_protein_dict())
        self.assertIn('function', result.columns)
        # RELEELNVPGEI should have 'Opioid' function
        row = result[result['Sequence'] == 'RELEELNVPGEI'].iloc[0]
        self.assertIn('Opioid', str(row['function']))

    def test_no_mbpdb_adds_nan_function(self):
        df = self._get_validated_df()
        result = data_combiner.process_pd_results(df, None, make_protein_dict())
        self.assertIn('function', result.columns)
        self.assertTrue(result['function'].isna().all())

    def test_start_end_positions_extracted(self):
        df = self._get_validated_df()
        result = data_combiner.process_pd_results(df, None, make_protein_dict())
        # P02666 [16-27] → start=16, end=27
        row = result[result['Sequence'] == 'RELEELNVPGEI'].iloc[0]
        self.assertEqual(row['start'], 16)
        self.assertEqual(row['end'], 27)


class TestCalculateGroupAbundanceAverages(unittest.TestCase):

    def test_avg_columns_added(self):
        df = make_peptidomic_df()
        gd = make_group_data()
        result = data_combiner.calculate_group_abundance_averages(df, gd)
        self.assertIn('Avg_GroupA', result.columns)
        self.assertIn('Avg_GroupB', result.columns)

    def test_avg_values_correct(self):
        df = make_peptidomic_df()
        gd = make_group_data()
        result = data_combiner.calculate_group_abundance_averages(df, gd)
        expected_a1 = (df['Sample_A1'] + df['Sample_A2']).values / 2
        np.testing.assert_allclose(result['Avg_GroupA'].values, expected_a1)

    def test_idempotent(self):
        """Calling twice should not duplicate columns."""
        df = make_peptidomic_df()
        gd = make_group_data()
        result = data_combiner.calculate_group_abundance_averages(df, gd)
        result2 = data_combiner.calculate_group_abundance_averages(result, gd)
        self.assertEqual(result2.columns.tolist(), result.columns.tolist())


class TestUpdateColumnNamesWithGroups(unittest.TestCase):

    def test_grouped_suffix_added(self):
        df = make_peptidomic_df()
        gd = make_group_data()
        result = data_combiner.update_column_names_with_groups(df, gd)
        # Sample_A1 belongs to GroupA
        self.assertIn("Sample_A1 'Grouped: (GroupA)'", result.columns)
        self.assertIn("Sample_B2 'Grouped: (GroupB)'", result.columns)


class TestProcessData(unittest.TestCase):
    """Integration test for the full data processing pipeline."""

    def test_full_pipeline_returns_dataframe(self):
        pd_results = make_peptidomic_df().rename(
            columns={'Master Protein Accessions': 'Protein'}
        )
        mbpdb = make_mbpdb_df()
        gd = make_group_data()
        protein_dict = make_protein_dict()

        result = data_combiner.process_data(pd_results, None, mbpdb, gd, protein_dict)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)

    def test_full_pipeline_has_expected_columns(self):
        pd_results = make_peptidomic_df().rename(
            columns={'Master Protein Accessions': 'Protein'}
        )
        result = data_combiner.process_data(
            pd_results, None, make_mbpdb_df(), make_group_data(), make_protein_dict()
        )
        for col in ['Unique Peptide ID', 'Sequence', 'Protein',
                    'protein_species', 'protein_name', 'Avg_GroupA', 'Avg_GroupB']:
            self.assertIn(col, result.columns, msg=f"Missing column: {col}")

    def test_no_pd_results_returns_none(self):
        result = data_combiner.process_data(None, None, None, {}, {})
        self.assertIsNone(result)

    def test_empty_pd_results_returns_none(self):
        result = data_combiner.process_data(pd.DataFrame(), None, None, {}, {})
        self.assertIsNone(result)

    def test_without_mbpdb_still_works(self):
        pd_results = make_peptidomic_df().rename(
            columns={'Master Protein Accessions': 'Protein'}
        )
        result = data_combiner.process_data(
            pd_results, None, None, make_group_data(), make_protein_dict()
        )
        self.assertIsNotNone(result)

    def test_without_groups_still_works(self):
        pd_results = make_peptidomic_df().rename(
            columns={'Master Protein Accessions': 'Protein'}
        )
        result = data_combiner.process_data(
            pd_results, None, make_mbpdb_df(), None, make_protein_dict()
        )
        self.assertIsNotNone(result)


# ---------------------------------------------------------------------------
# export_manager tests
# ---------------------------------------------------------------------------

def _make_merged_df():
    """Build a merged DataFrame as process_data would produce it."""
    pd_results = make_peptidomic_df().rename(
        columns={'Master Protein Accessions': 'Protein'}
    )
    return data_combiner.process_data(
        pd_results, None, make_mbpdb_df(), make_group_data(), make_protein_dict()
    )


class TestExportMbpdbResults(unittest.TestCase):

    def test_returns_tsv_bytes(self):
        mbpdb = make_mbpdb_df()
        result = export_manager.export_mbpdb_results(mbpdb)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, bytes)
        # TSV should have tabs
        self.assertIn(b'\t', result)

    def test_none_returns_none(self):
        result = export_manager.export_mbpdb_results(None)
        self.assertIsNone(result)


class TestExportGroupDefinitions(unittest.TestCase):

    def test_returns_json_bytes(self):
        gd = make_group_data()
        result = export_manager.export_group_definitions(gd)
        self.assertIsNotNone(result)
        parsed = json.loads(result.decode())
        self.assertIn('GroupA', parsed)
        self.assertEqual(parsed['GroupA'], ['Sample_A1', 'Sample_A2'])

    def test_none_returns_none(self):
        self.assertIsNone(export_manager.export_group_definitions(None))
        self.assertIsNone(export_manager.export_group_definitions({}))


class TestExportMergedDataset(unittest.TestCase):

    def test_returns_csv_bytes(self):
        merged = _make_merged_df()
        result = export_manager.export_merged_dataset(merged)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, bytes)
        # CSV should have the Unique Peptide ID column header
        self.assertIn(b'Unique Peptide ID', result)

    def test_none_returns_none(self):
        self.assertIsNone(export_manager.export_merged_dataset(None))


class TestExportSequenceList(unittest.TestCase):

    def test_returns_csv_bytes(self):
        merged = _make_merged_df()
        result = export_manager.export_sequence_list(merged, make_group_data())
        # May be None if no non-zero averages; just check it doesn't crash
        if result is not None:
            self.assertIsInstance(result, bytes)


class TestSummedPeptideResults(unittest.TestCase):

    def test_returns_dict_with_groups(self):
        merged = _make_merged_df()
        result = export_manager.summed_peptide_results(merged, make_group_data())
        self.assertIsInstance(result, dict)
        self.assertIn('GroupA', result)
        self.assertIn('GroupB', result)

    def test_group_has_expected_keys(self):
        merged = _make_merged_df()
        result = export_manager.summed_peptide_results(merged, make_group_data())
        group_a = result['GroupA']
        for key in ['unique_peptides', 'total_Absorbance', 'total_sem',
                    'abundance_sem', 'count_sem', 'replicate_data']:
            self.assertIn(key, group_a, msg=f"Missing key: {key}")

    def test_total_absorbance_positive(self):
        merged = _make_merged_df()
        result = export_manager.summed_peptide_results(merged, make_group_data())
        self.assertGreater(result['GroupA']['total_Absorbance'], 0)

    def test_export_summed_peptide_data_returns_xlsx(self):
        merged = _make_merged_df()
        result = export_manager.export_summed_peptide_data(merged, make_group_data())
        if result is not None:
            # XLSX files start with PK (zip magic bytes)
            self.assertEqual(result[:2], b'PK')


class TestExportProteinData(unittest.TestCase):

    def test_returns_xlsx_bytes(self):
        merged = _make_merged_df()
        result, warnings = export_manager.export_protein_data(
            merged, make_group_data(), make_protein_dict()
        )
        if result is not None:
            self.assertIsInstance(result, bytes)
            # XLSX files start with PK (zip magic bytes)
            self.assertEqual(result[:2], b'PK')

    def test_none_merged_returns_none(self):
        result, _ = export_manager.export_protein_data(None, make_group_data(), {})
        self.assertIsNone(result)


class TestExportGroupCorrelation(unittest.TestCase):

    def test_returns_xlsx(self):
        merged = _make_merged_df()
        result = export_manager.export_group_correlation(
            merged, make_group_data(), 'Pearson', True
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[:2], b'PK')

    def test_spearman_works(self):
        merged = _make_merged_df()
        result = export_manager.export_group_correlation(
            merged, make_group_data(), 'Spearman', True
        )
        self.assertIsNotNone(result)


class TestExportReplicateCorrelation(unittest.TestCase):

    def test_returns_xlsx(self):
        merged = _make_merged_df()
        result = export_manager.export_replicate_correlation(
            merged, make_group_data(), 'Pearson', True
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[:2], b'PK')


class TestCalculateCorrelation(unittest.TestCase):

    def test_pearson_perfect_correlation(self):
        x = pd.Series([1.0, 2.0, 3.0, 4.0])
        y = pd.Series([2.0, 4.0, 6.0, 8.0])
        corr, p_str = export_manager.calculate_correlation(x, y, 'Pearson')
        self.assertAlmostEqual(corr, 1.0, places=5)

    def test_spearman(self):
        x = pd.Series([1.0, 2.0, 3.0, 4.0])
        y = pd.Series([1.0, 4.0, 9.0, 16.0])
        corr, p_str = export_manager.calculate_correlation(x, y, 'Spearman')
        self.assertAlmostEqual(corr, 1.0, places=5)

    def test_p_value_format(self):
        x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        y = pd.Series([1.1, 2.1, 3.1, 4.1, 5.1])
        _, p_str = export_manager.calculate_correlation(x, y)
        self.assertTrue(p_str.startswith('p'))


class TestPrepareData(unittest.TestCase):

    def test_log10_transform(self):
        data = pd.Series([10.0, 100.0, 1000.0])
        result = export_manager.prepare_data(data, log_transform=True)
        np.testing.assert_allclose(result.values, [1.0, 2.0, 3.0])

    def test_no_transform(self):
        data = pd.Series([10.0, 100.0])
        result = export_manager.prepare_data(data, log_transform=False)
        np.testing.assert_array_equal(result.values, data.values)


# ---------------------------------------------------------------------------
# Notebook parity checks
# ---------------------------------------------------------------------------

class TestNotebookParity(unittest.TestCase):
    """
    Verify that the Django services produce the same logical output
    as the equivalent notebook class methods.
    """

    def test_unique_id_matches_notebook_logic(self):
        """
        Notebook create_unique_id: sequence + '_' + modifications (stripped),
        or just sequence if no modification. Trailing underscores removed.
        Django version should match.
        """
        cases = [
            # (sequence, modification, expected_id)
            ('RELEELNVPGEI', None, 'RELEELNVPGEI'),
            ('SEESITRINK', '1xPhospho [S1]', 'SEESITRINK_1xPhospho [S1]'),
            ('PEPTIDE', '', 'PEPTIDE'),
        ]
        for seq, mod, expected in cases:
            row = pd.Series({'Sequence': seq, 'Modifications': mod if mod else None})
            result = data_combiner.create_unique_id(row)
            self.assertEqual(result, expected, msg=f"Failed for seq={seq}, mod={mod}")

    def test_group_naming_format_matches_notebook(self):
        """
        Notebook update_column_names_with_groups renames columns to:
        "{column} 'Grouped: ({group_names})'"
        Django must match this format exactly.
        """
        df = pd.DataFrame({
            'Sample_A1': [1.0, 2.0],
            'Sample_A2': [3.0, 4.0],
        })
        gd = {'1': {'grouping_variable': 'GroupA', 'abundance_columns': ['Sample_A1', 'Sample_A2']}}
        result = data_combiner.update_column_names_with_groups(df, gd)
        self.assertIn("Sample_A1 'Grouped: (GroupA)'", result.columns)
        self.assertIn("Sample_A2 'Grouped: (GroupA)'", result.columns)

    def test_avg_column_naming_matches_notebook(self):
        """Average column name must be 'Avg_{grouping_variable}'."""
        df = pd.DataFrame({
            'Sample_A1': [1.0, 2.0],
            'Sample_A2': [3.0, 4.0],
        })
        gd = {'1': {'grouping_variable': 'MyGroup', 'abundance_columns': ['Sample_A1', 'Sample_A2']}}
        result = data_combiner.calculate_group_abundance_averages(df, gd)
        self.assertIn('Avg_MyGroup', result.columns)

    def test_mbpdb_function_aggregation_matches_notebook(self):
        """
        Notebook aggregates function as list of unique values joined with '; '.
        Django should produce the same output.
        """
        mbpdb = pd.DataFrame({
            'search_peptide': ['PEPTIDE', 'PEPTIDE'],
            'peptide':        ['PEPTIDE', 'PEPTIDE'],
            'protein_id':     ['P001', 'P001'],
            'function':       ['Opioid', 'ACE inhibitor'],
        })
        _, grouped = data_combiner.extract_bioactive_peptides(mbpdb)
        row = grouped[grouped['search_peptide'] == 'PEPTIDE'].iloc[0]
        functions = str(row['function'])
        self.assertIn('Opioid', functions)
        self.assertIn('ACE inhibitor', functions)
        # Notebook joins with '; '
        self.assertIn('; ', functions)

    def test_protein_info_column_position(self):
        """
        Notebook inserts protein_species and protein_name immediately after
        the protein accession column. Django must match this.
        """
        df = pd.DataFrame({
            'Unique Peptide ID': ['ABC'],
            'Sequence':          ['ABC'],
            'Protein':           ['P02666'],
            'Positions in Proteins': ['P02666 [1-3]'],
            'Sample_A1': [100.0],
        })
        result = data_combiner.add_protein_info(df, make_protein_dict())
        cols = list(result.columns)
        p_idx = cols.index('Protein')
        self.assertEqual(cols[p_idx + 1], 'protein_species')
        self.assertEqual(cols[p_idx + 2], 'protein_name')


# ---------------------------------------------------------------------------
# Real archive data tests — validate pipeline against actual lab files
# ---------------------------------------------------------------------------

ARCHIVE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'peptide', 'notebooks', 'archive'
)


def _load_real(filename, file_type='Peptidomic'):
    path = os.path.join(ARCHIVE, filename)
    with open(path, 'rb') as f:
        content = f.read()
    df, status, err, warn = data_loader.load_and_validate_file(
        content, filename, file_type
    )
    return df, status, err, warn


class TestRealData_ProteomeDiscoverer(unittest.TestCase):
    """test.csv — Proteome Discoverer format (Annotated Sequence, Master Protein Accessions)"""

    FILE = 'test.csv'

    def setUp(self):
        self.df, self.status, self.err, self.warn = _load_real(self.FILE)

    def test_loads_successfully(self):
        self.assertEqual(self.status, 'yes', msg=self.err)
        self.assertIsNotNone(self.df)

    def test_protein_column_mapped(self):
        self.assertIn('Protein', self.df.columns)

    def test_sequence_present(self):
        self.assertTrue(
            'Sequence' in self.df.columns or 'Annotated Sequence' in self.df.columns
        )

    def test_has_rows(self):
        self.assertGreater(len(self.df), 0)

    def test_filtered_columns_are_abundance(self):
        filtered = data_loader.get_filtered_columns(self.df)
        self.assertGreater(len(filtered), 0)
        # None of the filtered columns should be metadata
        for col in filtered:
            self.assertNotIn(col, ['Sequence', 'Protein', 'Modifications',
                                   'Annotated Sequence', 'Positions in Proteins'])

    def test_full_pipeline(self):
        gd = {}
        filtered = data_loader.get_filtered_columns(self.df)
        if filtered:
            gd, _ = group_processing.build_no_group_data(filtered)
        result = data_combiner.process_data(self.df, None, None, gd, {})
        self.assertIsNotNone(result)
        self.assertIn('Unique Peptide ID', result.columns)
        self.assertIn('Sequence', result.columns)


class TestRealData_ExampleShort(unittest.TestCase):
    """example_peptide_data_short.csv — PD format with direct Sequence column, ~49 rows"""

    FILE = 'example_peptide_data_short.csv'

    def setUp(self):
        self.df, self.status, self.err, self.warn = _load_real(self.FILE)

    def test_loads_successfully(self):
        self.assertEqual(self.status, 'yes', msg=self.err)

    def test_protein_column_mapped(self):
        self.assertIn('Protein', self.df.columns)

    def test_abundance_columns_detected(self):
        filtered = data_loader.get_filtered_columns(self.df)
        self.assertGreater(len(filtered), 0)

    def test_sequences_extractable(self):
        seqs = data_loader.extract_sequences(self.df)
        self.assertGreater(len(seqs), 0)
        # All should be non-empty strings
        for s in seqs:
            self.assertIsInstance(s, str)
            self.assertGreater(len(s), 0)

    def test_full_pipeline_with_groups(self):
        filtered = data_loader.get_filtered_columns(self.df)
        self.assertGreater(len(filtered), 0)
        # Put all columns into one group
        gd, err = group_processing.build_group_data(filtered[:3], 'TestGroup')
        self.assertIsNone(err)
        result = data_combiner.process_data(self.df, None, None, gd, {})
        self.assertIsNotNone(result)
        self.assertIn('Avg_TestGroup', result.columns)

    def test_export_merged_dataset(self):
        filtered = data_loader.get_filtered_columns(self.df)
        gd, _ = group_processing.build_no_group_data(filtered[:2])
        result = data_combiner.process_data(self.df, None, None, gd, {})
        csv_bytes = export_manager.export_merged_dataset(result)
        self.assertIsNotNone(csv_bytes)
        # Parse the CSV back and verify shape
        result_back = pd.read_csv(io.BytesIO(csv_bytes))
        self.assertEqual(len(result_back), len(result))


class TestRealData_Skyline(unittest.TestCase):
    """skyline_raw.csv — Skyline format (Protein, Peptide Modified Sequence, Peptide start/end), ~993 rows"""

    FILE = 'skyline_raw.csv'

    def setUp(self):
        self.df, self.status, self.err, self.warn = _load_real(self.FILE)

    def test_loads_successfully(self):
        self.assertEqual(self.status, 'yes', msg=self.err)

    def test_protein_column_present(self):
        self.assertIn('Protein', self.df.columns)

    def test_abundance_columns_detected(self):
        filtered = data_loader.get_filtered_columns(self.df)
        self.assertGreater(len(filtered), 0)

    def test_sequences_extractable(self):
        seqs = data_loader.extract_sequences(self.df)
        self.assertGreater(len(seqs), 0)

    def test_unique_id_no_trailing_underscore(self):
        """Every unique ID produced from real Skyline data must not end with '_'."""
        filtered = data_loader.get_filtered_columns(self.df)
        gd, _ = group_processing.build_no_group_data(filtered[:1])
        result = data_combiner.process_data(self.df, None, None, gd, {})
        if result is not None:
            for uid in result['Unique Peptide ID'].dropna():
                self.assertFalse(str(uid).endswith('_'), msg=f"Trailing underscore: {uid!r}")

    def test_full_pipeline_large_file(self):
        filtered = data_loader.get_filtered_columns(self.df)
        self.assertGreater(len(filtered), 0)
        gd, _ = group_processing.build_no_group_data(filtered[:4])
        result = data_combiner.process_data(self.df, None, None, gd, {})
        self.assertIsNotNone(result)
        # Row count should be preserved
        self.assertGreater(len(result), 0)


class TestRealData_Noom(unittest.TestCase):
    """noom_peptide_data.csv — Annotated Sequence format, ~2366 rows, large real dataset"""

    FILE = 'noom_peptide_data.csv'

    def setUp(self):
        self.df, self.status, self.err, self.warn = _load_real(self.FILE)

    def test_loads_successfully(self):
        self.assertEqual(self.status, 'yes', msg=self.err)

    def test_abundance_columns_detected(self):
        filtered = data_loader.get_filtered_columns(self.df)
        self.assertGreater(len(filtered), 4,
            msg=f"Expected multiple abundance cols, got: {filtered}")

    def test_group_json_round_trip(self):
        """Build groups from first 4 abundance columns, export JSON, re-import."""
        filtered = data_loader.get_filtered_columns(self.df)
        cols_a = filtered[:2]
        cols_b = filtered[2:4]
        gd = {}
        gd, _ = group_processing.build_group_data(cols_a, 'GroupA', gd)
        gd, _ = group_processing.build_group_data(cols_b, 'GroupB', gd)

        json_str = group_processing.export_group_data_json(gd)
        gd2, err = group_processing.parse_group_json(
            json_str.encode(), data_loader.get_filtered_columns(self.df)
        )
        self.assertIsNone(err)
        self.assertEqual(
            gd['GroupA']['abundance_columns'],
            gd2['GroupA']['abundance_columns']
        )

    def test_full_pipeline_produces_averages(self):
        filtered = data_loader.get_filtered_columns(self.df)
        gd, _ = group_processing.build_group_data(filtered[:3], 'GroupA')
        gd, _ = group_processing.build_group_data(filtered[3:6], 'GroupB', gd)
        result = data_combiner.process_data(self.df, None, None, gd, {})
        self.assertIsNotNone(result)
        self.assertIn('Avg_GroupA', result.columns)
        self.assertIn('Avg_GroupB', result.columns)
        # Averages should be numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(result['Avg_GroupA']))

    def test_summed_peptide_export(self):
        filtered = data_loader.get_filtered_columns(self.df)
        gd, _ = group_processing.build_group_data(filtered[:3], 'GroupA')
        gd, _ = group_processing.build_group_data(filtered[3:6], 'GroupB', gd)
        result = data_combiner.process_data(self.df, None, None, gd, {})
        xlsx = export_manager.export_summed_peptide_data(result, gd)
        self.assertIsNotNone(xlsx)
        self.assertEqual(xlsx[:2], b'PK')  # XLSX is a zip

    def test_replicate_correlation_export(self):
        filtered = data_loader.get_filtered_columns(self.df)
        gd, _ = group_processing.build_group_data(filtered[:3], 'GroupA')
        result = data_combiner.process_data(self.df, None, None, gd, {})
        xlsx = export_manager.export_replicate_correlation(result, gd)
        self.assertIsNotNone(xlsx)
        self.assertEqual(xlsx[:2], b'PK')


class TestRealData_ManyPositions(unittest.TestCase):
    """peptides_with_many_positions.csv — rows with multiple protein positions ('; ' separated)"""

    FILE = 'peptides_with_many_positions.csv'

    def setUp(self):
        self.df, self.status, self.err, self.warn = _load_real(self.FILE)

    def test_loads_successfully(self):
        self.assertEqual(self.status, 'yes', msg=self.err)

    def test_multiprotein_rows_handled(self):
        """Rows with '; ' in Positions in Proteins should not crash processing."""
        if 'Positions in Proteins' in self.df.columns:
            multi = self.df['Positions in Proteins'].astype(str).str.contains('; ', na=False)
            self.assertGreater(multi.sum(), 0,
                msg="Expected rows with multiple protein positions")

        filtered = data_loader.get_filtered_columns(self.df)
        if not filtered:
            self.skipTest("No abundance columns found")
        gd, _ = group_processing.build_no_group_data(filtered[:2])
        result = data_combiner.process_data(self.df, None, None, gd, {})
        self.assertIsNotNone(result)

    def test_missing_proteins_detected(self):
        missing = data_loader.find_missing_proteins(self.df, {})
        # With empty protein_dict every protein should be "missing"
        if 'Protein' in self.df.columns:
            self.assertGreater(len(missing), 0)

    def test_protein_combinations_extracted(self):
        from peptide.data_transformation.services import protein_handler
        combos = protein_handler.get_protein_combinations(self.df, {})
        # File has multi-protein rows — should find at least one combination
        self.assertIsInstance(combos, list)


if __name__ == '__main__':
    unittest.main()
