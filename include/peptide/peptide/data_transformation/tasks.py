"""
Celery tasks for long-running data transformation operations.
"""
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

    client = UniProtClient()
    results = {}

    for i, protein_id in enumerate(missing_protein_ids):
        elapsed = time.time() - start_time
        cache.set(f'progress_{task_id}', i)
        cache.set(f'elapsed_time_{task_id}', elapsed)

        try:
            info = client.fetch_protein_info(protein_id)
            if info:
                results[protein_id] = info
        except Exception:
            pass

    cache.set(f'progress_{task_id}', total)
    cache.set(f'elapsed_time_{task_id}', time.time() - start_time)
    cache.set(f'status_{task_id}', 'complete')

    return results
