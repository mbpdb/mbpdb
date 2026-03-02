"""
Utility modules for peptide notebooks and Django app.

Exported symbols
----------------
UniProtClient       — UniProt REST API client with caching
validate_fasta_format — validate FASTA file content
parse_fasta         — parse FASTA file → protein dict
find_species        — detect species from FASTA header
extract_uniprot_id  — extract UniProt accession from pipe header
"""

from .uniprot_client import UniProtClient
from .fasta_utils import (
    validate_fasta_format,
    parse_fasta,
    find_species,
    extract_uniprot_id,
)

__all__ = [
    'UniProtClient',
    'validate_fasta_format',
    'parse_fasta',
    'find_species',
    'extract_uniprot_id',
]
