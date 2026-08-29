"""Regression tests for the bulk-upload / search query-shape fixes.

Run: DJANGO_SETTINGS_MODULE=peptide.settings python3 manage.py test peptide
"""
import io

from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection

from .models import ProteinInfo, ProteinVariant, PeptideInfo, Function, Reference, Submission
from . import toolbox


def _tsv(rows):
    header = ('proteinID\tpeptide\tfunction\tadditional_details\tic50\tinhibition_type\t'
              'inhibited_microorganisms\tptm\ttitle\tauthors\tabstract\tdoi')
    lines = [header]
    for r in rows:
        lines.append('\t'.join(r.get(c, '') for c in [
            'proteinID', 'peptide', 'function', 'additional_details', 'ic50',
            'inhibition_type', 'inhibited_microorganisms', 'ptm', 'title',
            'authors', 'abstract', 'doi']))
    data = ('\n'.join(lines) + '\n').encode('utf-8')
    f = io.BytesIO(data)
    f.name = 'entries.tsv'
    return f


class _FakeUpload:
    """Enough of an UploadedFile for handle_uploaded_file()."""
    def __init__(self, bytes_io):
        self._b = bytes_io
        self.name = bytes_io.name

    def chunks(self):
        self._b.seek(0)
        yield self._b.read()


class PepdbAddCsvBulkTest(TestCase):
    def setUp(self):
        self.p1 = ProteinInfo.objects.create(header='h', pid='PROT1',
                                             seq='MKVLILACLVALARELEELN', desc='d', species='Bovine')
        self.p2 = ProteinInfo.objects.create(header='h', pid='PROT2',
                                             seq='AAAKKKPEPTIDEHERE', desc='d', species='Bovine')

    def _run(self, rows):
        msgs = []
        return toolbox.pepdb_add_csv(_FakeUpload(_tsv(rows)), msgs), msgs

    def test_valid_rows_bulk_created(self):
        rows = [
            {'proteinID': 'PROT1', 'peptide': 'ARELEELN', 'function': 'ACE-inhibitory',
             'title': 't', 'authors': 'a', 'doi': '10.1/a'},
            {'proteinID': 'PROT2', 'peptide': 'PEPTIDEHERE', 'function': 'Antioxidant',
             'title': 't', 'authors': 'a', 'doi': '10.1/b'},
        ]
        _, msgs = self._run(rows)
        self.assertEqual(Submission.objects.count(), 2)
        self.assertTrue(any('Successfully added 2' in m for m in msgs))
        sub = Submission.objects.get(peptide='ARELEELN')
        self.assertTrue(sub.intervals)             # located in the sequence
        self.assertEqual(sub.length, len('ARELEELN'))

    def test_query_count_does_not_grow_with_rows(self):
        # The per-row protein/variant lookups are gone: a 2-row and a 20-row file
        # issue the same number of queries.
        small = [{'proteinID': 'PROT1', 'peptide': 'ARELEELN', 'function': 'F',
                  'title': 't', 'authors': 'a', 'doi': f'10/{i}'} for i in range(2)]
        big = [{'proteinID': 'PROT1', 'peptide': 'ARELEELN', 'function': 'F',
                'title': 't', 'authors': 'a', 'doi': f'10/{i}'} for i in range(20)]

        with CaptureQueriesContext(connection) as c_small:
            self._run(small)
        Submission.objects.all().delete()
        with CaptureQueriesContext(connection) as c_big:
            self._run(big)

        self.assertEqual(len(c_small.captured_queries), len(c_big.captured_queries))
        self.assertEqual(Submission.objects.count(), 20)

    def test_missing_protein_and_blank_fields_skipped_with_line_numbers(self):
        rows = [
            {'proteinID': 'NOPE', 'peptide': 'ARELEELN', 'function': 'F',
             'title': 't', 'authors': 'a', 'doi': '10/x'},               # line 2: unknown protein
            {'proteinID': 'PROT1', 'peptide': '', 'function': 'F',
             'title': 't', 'authors': 'a', 'doi': '10/y'},               # line 3: blank peptide
            {'proteinID': 'PROT1', 'peptide': 'ARELEELN', 'function': 'F',
             'title': 't', 'authors': 'a', 'doi': '10/z'},               # line 4: ok
        ]
        _, msgs = self._run(rows)
        self.assertEqual(Submission.objects.count(), 1)
        self.assertTrue(any('Line 2' in m for m in msgs))
        self.assertTrue(any('Line 3' in m for m in msgs))

    def test_peptide_with_regex_metacharacters_is_matched_literally(self):
        # A '.' in the peptide must not act as a regex wildcard.
        ProteinInfo.objects.create(header='h', pid='PROT3', seq='XXA.BYY', desc='d', species='Bovine')
        rows = [{'proteinID': 'PROT3', 'peptide': 'A.B', 'function': 'F',
                 'title': 't', 'authors': 'a', 'doi': '10/m'}]
        _, msgs = self._run(rows)
        self.assertEqual(Submission.objects.filter(peptide='A.B').count(), 1)
        self.assertEqual(Submission.objects.get(peptide='A.B').intervals, '3-5')
