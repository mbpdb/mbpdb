"""
Celery tasks for long-running data transformation operations.
"""
import re
import time
import sys
import os

from celery import shared_task
from django.core.cache import cache
from django.conf import settings

from .services.blast_search import run_blast_search, create_work_directory


@shared_task(bind=True)
def run_blast_search_task(self, work_dir, peptides, threshold):
    """
    Run BLAST search as a Celery task with progress tracking.

    Args:
        work_dir: working directory for temp files
        peptides: list of peptide sequences
        threshold: similarity threshold (0-100)

    Returns:
        dict with 'work_dir' and 'result_path' (parquet file path)
    """
    import pandas as pd

    task_id = self.request.id
    total = len(peptides)
    cache.set(f'size_{task_id}', total)
    start_time = time.time()

    def progress_callback(current, total_count, message):
        elapsed = time.time() - start_time
        cache.set(f'progress_{task_id}', current)
        cache.set(f'elapsed_time_{task_id}', elapsed)

    try:
        results_df = run_blast_search(
            peptides,
            similarity_threshold=threshold,
            work_dir=work_dir,
            progress_callback=progress_callback
        )

        result_path = os.path.join(work_dir, 'mbpdb_results.pkl')
        results_df.to_pickle(result_path)

        cache.set(f'progress_{task_id}', total)
        cache.set(f'elapsed_time_{task_id}', time.time() - start_time)
        cache.set(f'status_{task_id}', 'complete')

        return {
            'work_dir': work_dir,
            'result_path': result_path,
            'count': len(results_df),
        }
    except Exception as e:
        cache.set(f'status_{task_id}', 'failed')
        cache.set(f'error_{task_id}', str(e))
        raise


@shared_task(bind=True)
def fetch_uniprot_task(self, missing_protein_ids):
    """
    Fetch protein info from UniProt in batch as a Celery task.

    Args:
        missing_protein_ids: list of protein ID strings

    Returns:
        dict mapping protein_id -> {name, species, sequence, ...}
    """
    task_id = self.request.id
    total = len(missing_protein_ids)
    cache.set(f'size_{task_id}', total)
    start_time = time.time()

    # Import UniProt client
    notebooks_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'notebooks')
    if notebooks_dir not in sys.path:
        sys.path.insert(0, notebooks_dir)
    from utils.uniprot_client import UniProtClient

    # UniProt accession IDs are 6 or 10 alphanumeric chars.
    # IDs like "P02666A1" (isoform suffixes) are invalid and cause HTTP 400
    # for the entire batch, so filter them out before querying.
    _UNIPROT_ACC_RE = re.compile(
        r'^[A-Z][0-9][A-Z][A-Z0-9]{2}[0-9]([A-Z][A-Z0-9]{2}[0-9])?$'
    )

    def _is_valid_uniprot_id(pid):
        return bool(_UNIPROT_ACC_RE.match(pid.upper())) if pid else False

    client = UniProtClient()
    results = {}
    BATCH_SIZE = 20

    valid_ids = [pid for pid in missing_protein_ids if _is_valid_uniprot_id(pid)]
    skipped = len(missing_protein_ids) - len(valid_ids)
    if skipped:
        print(f'fetch_uniprot_task: skipping {skipped} non-standard IDs')

    for batch_start in range(0, len(valid_ids), BATCH_SIZE):
        batch = valid_ids[batch_start:batch_start + BATCH_SIZE]

        elapsed = time.time() - start_time
        cache.set(f'progress_{task_id}', batch_start)
        cache.set(f'elapsed_time_{task_id}', elapsed)

        try:
            batch_results = client.fetch_proteins_batch(batch)
            for pid, info_tuple in batch_results.items():
                if info_tuple and len(info_tuple) >= 2:
                    name, species = info_tuple[0], info_tuple[1]
                    results[pid] = {'name': name, 'species': species}
        except Exception as exc:
            print(f'fetch_uniprot_task: batch error: {exc}')

    cache.set(f'progress_{task_id}', total)
    cache.set(f'elapsed_time_{task_id}', time.time() - start_time)
    cache.set(f'status_{task_id}', 'complete')

    return results
