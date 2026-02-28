"""
Utility modules for peptide notebooks.

Exported symbols
----------------
UniProtClient       — UniProt REST API client with caching
BaseDataTransformation — shared DataTransformation scaffold
EllipsisSelectMultiple — SelectMultiple widget with ellipsis overflow
create_file_download_link  — file-on-disk → widgets.HTML anchor
generate_auto_download_link — content → auto-triggering download HTML
create_help_icon    — question-circle tooltip widget
display_warning     — Bootstrap-styled warning banner
safe_concat         — NA-aware DataFrame concatenation
redact_string_descriptions — truncate long label strings
extract_non_zero_non_nan_values — flatten non-zero DataFrame values
validate_fasta_format — validate an uploaded FASTA file
parse_fasta         — parse FASTA file → protein dict
find_species        — detect species from FASTA header
extract_uniprot_id  — extract UniProt accession from pipe header
"""

from .uniprot_client import UniProtClient
from .base_transformer import BaseDataTransformation
from .ui_helpers import (
    EllipsisSelectMultiple,
    create_file_download_link,
    generate_auto_download_link,
    create_help_icon,
    display_warning,
    safe_concat,
    redact_string_descriptions,
    extract_non_zero_non_nan_values,
)
from .fasta_utils import (
    validate_fasta_format,
    parse_fasta,
    find_species,
    extract_uniprot_id,
)

__all__ = [
    'UniProtClient',
    'BaseDataTransformation',
    'EllipsisSelectMultiple',
    'create_file_download_link',
    'generate_auto_download_link',
    'create_help_icon',
    'display_warning',
    'safe_concat',
    'redact_string_descriptions',
    'extract_non_zero_non_nan_values',
    'validate_fasta_format',
    'parse_fasta',
    'find_species',
    'extract_uniprot_id',
]
