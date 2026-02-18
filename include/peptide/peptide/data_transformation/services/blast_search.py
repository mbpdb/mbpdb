"""
BLAST search logic and database queries.
Extracted from notebook DataTransformation class (Cell 1).
Converted from raw sqlite3 to Django ORM.
"""
import os
import csv
import subprocess
import time
import shutil
from collections import defaultdict

import pandas as pd
import numpy as np
from django.conf import settings

from peptide.models import PeptideInfo, ProteinInfo, Function, Reference


def create_work_directory(base_dir=None):
    """Create a working directory for BLAST operations."""
    if base_dir is None:
        base_dir = settings.WORK_DIRECTORY
    path = os.path.join(base_dir, f'work_{int(round(time.time() * 1000))}')
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_work_directories(work_directory=None, keep=25):
    """Clean up old work directories, keeping the most recent ones."""
    if work_directory is None:
        work_directory = settings.WORK_DIRECTORY
    try:
        dirs = [f for f in os.scandir(work_directory) if f.is_dir() and f.name.startswith('work_')]
        dirs.sort(key=lambda x: os.path.getmtime(x.path), reverse=True)
        for dir_entry in dirs[keep:]:
            try:
                shutil.rmtree(dir_entry.path)
            except Exception:
                pass
    except Exception:
        pass


def make_blast_db(library_fasta_path):
    """Create BLAST database from FASTA file."""
    subprocess.check_output(
        ['makeblastdb', '-in', library_fasta_path, '-dbtype', 'prot'],
        stderr=subprocess.STDOUT
    )


def run_blast_search(peptides, similarity_threshold=100, work_dir=None,
                     progress_callback=None):
    """
    Search peptides against the MBPDB database using BLAST.

    Args:
        peptides: list of peptide sequences
        similarity_threshold: minimum similarity percentage (0-100)
        work_dir: working directory for temp files
        progress_callback: callable(current, total, status_msg) for progress updates

    Returns:
        pd.DataFrame with search results
    """
    if work_dir is None:
        work_dir = create_work_directory()

    fasta_db_path = os.path.join(work_dir, "db.fasta")
    results = []
    extra_info = defaultdict(list)

    # Build BLAST database from all peptides in the database using Django ORM
    db_peptides = PeptideInfo.objects.values_list('id', 'peptide')

    with open(fasta_db_path, 'w') as f:
        for pep_id, pep_seq in db_peptides:
            f.write(f">{pep_id}\n{pep_seq}\n")

    make_blast_db(fasta_db_path)

    total = len(peptides)
    for idx, peptide in enumerate(peptides):
        if progress_callback:
            progress_callback(idx, total, f"Searching peptide {idx+1}/{total}")

        if similarity_threshold == 100 or len(peptide) < 4:
            # Exact match search using Django ORM
            df = _fetch_exact_match(peptide)
            if not df.empty:
                results.append(df)
        else:
            # BLAST search
            query_path = os.path.join(work_dir, "query.fasta")
            with open(query_path, "w") as query_file:
                query_file.write(f">pep_query\n{peptide}\n")

            output_path = os.path.join(work_dir, "blastp_short.out")
            blast_args = [
                "blastp",
                "-query", query_path,
                "-db", fasta_db_path,
                "-outfmt", "6 std ppos qcovs qlen slen positive",
                "-evalue", "1000",
                "-word_size", "2",
                "-matrix", "IDENTITY",
                "-threshold", "1",
                "-task", "blastp-short",
                "-out", output_path
            ]

            try:
                subprocess.check_output(blast_args, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError:
                continue

            search_ids = _process_blast_results(output_path, similarity_threshold, extra_info)

            if search_ids:
                df = _fetch_peptide_data_by_ids(peptide, search_ids)
                _add_blast_details(df, extra_info)
                if not df.empty:
                    results.append(df)

    if progress_callback:
        progress_callback(total, total, "Search complete")

    cleanup_work_directories()

    return _combine_results(results)


def _fetch_exact_match(peptide):
    """Fetch exact match results using Django ORM."""
    pep_infos = PeptideInfo.objects.filter(peptide=peptide).select_related('protein')

    rows = []
    for p in pep_infos:
        functions = Function.objects.filter(pep=p).prefetch_related('references')
        if functions.exists():
            for func in functions:
                for ref in func.references.all():
                    rows.append({
                        'search_peptide': peptide,
                        'protein_id': p.protein.pid,
                        'peptide_id': p.id,
                        'peptide': p.peptide,
                        'protein_description': p.protein.desc,
                        'species': p.protein.species,
                        'intervals': p.intervals,
                        'function': func.function,
                        'additional_details': ref.additional_details,
                        'ic50': ref.ic50,
                        'inhibition_type': ref.inhibition_type,
                        'inhibited_microorganisms': ref.inhibited_microorganisms,
                        'ptm': ref.ptm,
                        'title': ref.title,
                        'authors': ref.authors,
                        'abstract': ref.abstract,
                        'doi': ref.doi,
                        'search_type': 'sequence',
                        'scoring_matrix': 'IDENTITY',
                    })
        else:
            rows.append({
                'search_peptide': peptide,
                'protein_id': p.protein.pid,
                'peptide_id': p.id,
                'peptide': p.peptide,
                'protein_description': p.protein.desc,
                'species': p.protein.species,
                'intervals': p.intervals,
                'function': None,
                'additional_details': None,
                'ic50': None,
                'inhibition_type': None,
                'inhibited_microorganisms': None,
                'ptm': None,
                'title': None,
                'authors': None,
                'abstract': None,
                'doi': None,
                'search_type': 'sequence',
                'scoring_matrix': 'IDENTITY',
            })

    return pd.DataFrame(rows)


def _process_blast_results(output_path, similarity_threshold, extra_info):
    """Process BLAST results and collect search IDs."""
    search_ids = []
    csv.register_dialect('blast_dialect', delimiter='\t')

    try:
        with open(output_path, "r") as output_file:
            blast_data = csv.DictReader(
                output_file,
                fieldnames=['query', 'subject', 'percid', 'align_len', 'mismatches',
                            'gaps', 'qstart', 'qend', 'sstart', 'send', 'evalue',
                            'bitscore', 'ppos', 'qcov', 'qlen', 'slen', 'numpos'],
                dialect='blast_dialect'
            )

            for row in blast_data:
                tlen = max(float(row['slen']), float(row['qlen']))
                simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / tlen)

                if simcalc >= similarity_threshold:
                    search_ids.append(row['subject'])
                    extra_info[row['subject']] = [
                        f"{simcalc:.2f}", row['qstart'], row['qend'], row['sstart'],
                        row['send'], row['evalue'], row['align_len'], row['mismatches'],
                        row['gaps']
                    ]
    except FileNotFoundError:
        pass

    return search_ids


def _fetch_peptide_data_by_ids(peptide, search_ids):
    """Fetch peptide data by IDs using Django ORM."""
    int_ids = []
    for sid in search_ids:
        try:
            int_ids.append(int(sid))
        except (ValueError, TypeError):
            continue

    pep_infos = PeptideInfo.objects.filter(id__in=int_ids).select_related('protein')

    rows = []
    for p in pep_infos:
        functions = Function.objects.filter(pep=p).prefetch_related('references')
        if functions.exists():
            for func in functions:
                for ref in func.references.all():
                    rows.append({
                        'search_peptide': peptide,
                        'protein_id': p.protein.pid,
                        'peptide_id': p.id,
                        'peptide': p.peptide,
                        'protein_description': p.protein.desc,
                        'species': p.protein.species,
                        'intervals': p.intervals,
                        'function': func.function,
                        'additional_details': ref.additional_details,
                        'ic50': ref.ic50,
                        'inhibition_type': ref.inhibition_type,
                        'inhibited_microorganisms': ref.inhibited_microorganisms,
                        'ptm': ref.ptm,
                        'title': ref.title,
                        'authors': ref.authors,
                        'abstract': ref.abstract,
                        'doi': ref.doi,
                        'search_type': 'sequence',
                        'scoring_matrix': 'IDENTITY',
                    })
        else:
            rows.append({
                'search_peptide': peptide,
                'protein_id': p.protein.pid,
                'peptide_id': p.id,
                'peptide': p.peptide,
                'protein_description': p.protein.desc,
                'species': p.protein.species,
                'intervals': p.intervals,
                'function': None,
                'additional_details': None,
                'ic50': None,
                'inhibition_type': None,
                'inhibited_microorganisms': None,
                'ptm': None,
                'title': None,
                'authors': None,
                'abstract': None,
                'doi': None,
                'search_type': 'sequence',
                'scoring_matrix': 'IDENTITY',
            })

    return pd.DataFrame(rows)


def _add_blast_details(df, extra_info):
    """Add BLAST details to DataFrame."""
    for idx, row in df.iterrows():
        if str(row.get('peptide_id', '')) in extra_info:
            blast_details = extra_info[str(row['peptide_id'])]
            df.at[idx, '% Alignment'] = blast_details[0]
            df.at[idx, 'Query start'] = blast_details[1]
            df.at[idx, 'Query end'] = blast_details[2]
            df.at[idx, 'Subject start'] = blast_details[3]
            df.at[idx, 'Subject end'] = blast_details[4]
            df.at[idx, 'e-value'] = blast_details[5]
            df.at[idx, 'Alignment length'] = blast_details[6]
            df.at[idx, 'Mismatches'] = blast_details[7]
            df.at[idx, 'Gap opens'] = blast_details[8]


def _combine_results(results):
    """Combine and format final results."""
    if not results:
        mbpdb_columns = [
            'search_peptide', 'protein_id', 'peptide', 'protein_description',
            'species', 'intervals', 'function', 'additional_details', 'ic50',
            'inhibition_type', 'inhibited_microorganisms', 'ptm', 'title',
            'authors', 'abstract', 'doi', 'search_type', 'scoring_matrix'
        ]
        return pd.DataFrame(columns=mbpdb_columns)

    final_results = pd.concat(results, ignore_index=True)

    if 'peptide_id' in final_results.columns:
        final_results = final_results.drop('peptide_id', axis=1)

    sort_columns = ['search_peptide']
    if '% Alignment' in final_results.columns:
        sort_columns.append('% Alignment')

    return final_results.sort_values(
        sort_columns,
        ascending=[True] + [False] * (len(sort_columns) - 1)
    )


def format_search_results(final_results):
    """Format search results by aggregating duplicate groups."""
    if final_results.empty:
        return final_results

    if '% Alignment' in final_results.columns:
        final_results['% Alignment'] = pd.to_numeric(
            final_results['% Alignment'], errors='coerce'
        )

    grouped = final_results.groupby(["search_peptide", "function"], as_index=False)
    aggregated_results = []
    processed_indices = set()

    for _, group in grouped:
        if len(group) > 1:
            aggregated_row = _aggregate_group_data(group)
            aggregated_results.append(aggregated_row)
            processed_indices.update(group.index)

    remaining_rows = final_results.loc[~final_results.index.isin(processed_indices)]
    aggregated_df = pd.DataFrame(aggregated_results)

    return pd.concat([aggregated_df, remaining_rows], ignore_index=True)


def _aggregate_group_data(group):
    """Aggregate data for a group of results."""
    def enumerate_field(field):
        if field in group.columns and not group[field].dropna().empty:
            valid_values = set(group[field].dropna().astype(str).str.strip())
            valid_values = {val for val in valid_values if val != ''}
            if len(valid_values) > 1:
                return "; ".join([f"{i + 1}) {val}" for i, val in enumerate(valid_values)])
            elif len(valid_values) == 1:
                return next(iter(valid_values))
            return ''
        return ''

    return {col: enumerate_field(col) for col in group.columns}
