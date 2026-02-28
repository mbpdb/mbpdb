"""
FASTA parsing and validation utilities shared between
heatmap_visualization and (formerly) data_transformation notebooks.
"""

import re
from IPython.display import display, HTML
import _settings as settings


# ---------------------------------------------------------------------------
# UniProt ID extraction
# ---------------------------------------------------------------------------

def extract_uniprot_id(x):
    """
    Extract a bare UniProt accession from a FASTA-style pipe-delimited header.

    Examples
    --------
    ``"sp|P02666|CASB_BOVIN Beta-casein"``  →  ``"P02666"``
    ``"P02666"``                             →  ``"P02666"``  (returned unchanged)
    """
    if isinstance(x, str) and '|' in x:
        m = re.search(r'\|([A-Z0-9]+)\|', x)
        if m:
            return m.group(1)
    return x


# ---------------------------------------------------------------------------
# Species detection
# ---------------------------------------------------------------------------

def find_species(header, spec_translate_list=None):
    """
    Return the common species name for a FASTA header string.

    Searches ``spec_translate_list`` (defaults to ``settings.SPEC_TRANSLATE_LIST``)
    for a matching term.  Returns ``"unknown"`` if no match is found.
    """
    if spec_translate_list is None:
        spec_translate_list = settings.SPEC_TRANSLATE_LIST

    header_lower = header.lower()
    for spec_group in spec_translate_list:
        for term in spec_group[1:]:
            if term.lower() in header_lower:
                return spec_group[0]
    return "unknown"


# ---------------------------------------------------------------------------
# FASTA validation
# ---------------------------------------------------------------------------

def validate_fasta_format(file_data):
    """
    Validate that an uploaded file widget object contains proper FASTA content.

    Returns ``True`` if valid, ``False`` otherwise.  Displays HTML error
    messages on failure (for use inside ipywidgets Output contexts).
    """
    try:
        content = file_data.content.tobytes().decode('utf-8')
        lines = content.strip().split('\n')

        if not lines:
            return False

        if not any(line.strip().startswith('>') for line in lines):
            display(HTML("<b style='color:red'>Improper FASTA header: at least one line must start with '>'</b>"))
            return False

        has_header = False
        has_sequence = False
        current_sequence_length = 0

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            if line.startswith('>'):
                if len(line) <= 1:
                    return False
                has_header = True
                if i > 0 and current_sequence_length == 0:
                    return False
                current_sequence_length = 0
            else:
                if not has_header:
                    return False
                valid_chars = set('ACDEFGHIKLMNPQRSTVWYXBZJOU*-')
                if not all(c.upper() in valid_chars for c in line):
                    nucleotide_chars = set('ATCGRYSWKMBDHVN-')
                    if not all(c.upper() in nucleotide_chars for c in line):
                        return False
                has_sequence = True
                current_sequence_length += len(line)

        return has_header and has_sequence

    except Exception as e:
        display(HTML(f"<b style='color:red'>Validation error: {str(e)}</b>"))
        return False


# ---------------------------------------------------------------------------
# FASTA parsing
# ---------------------------------------------------------------------------

def parse_fasta(file_data, spec_translate_list=None):
    """
    Parse an uploaded FASTA file widget object into a protein dictionary.

    Parameters
    ----------
    file_data : ipywidgets FileInfo
        The file object from a ``widgets.FileUpload`` value entry.
    spec_translate_list : list, optional
        Species translation list.  Defaults to ``settings.SPEC_TRANSLATE_LIST``.

    Returns
    -------
    dict
        ``{protein_id: {"name": str, "sequence": str, "species": str}}``
    """
    if spec_translate_list is None:
        spec_translate_list = settings.SPEC_TRANSLATE_LIST

    fasta_dict = {}
    fasta_text = bytes(file_data.content).decode('utf-8')
    lines = fasta_text.split('\n')

    protein_id = ""
    protein_name = ""
    sequence = ""
    species = ""

    for line in lines:
        line = line.strip()
        if line.startswith('>'):
            if protein_id:
                fasta_dict[protein_id] = {
                    "name": protein_name,
                    "sequence": sequence,
                    "species": species,
                }
            sequence = ""
            header_parts = line[1:].split('|')
            if len(header_parts) > 2:
                protein_id = header_parts[1]
                protein_name_full = re.split(r' OS=', header_parts[2])[0]
                protein_name = protein_name_full
                species = find_species(line, spec_translate_list)
            else:
                # Non-UniProt header: use everything after '>' as the ID
                protein_id = line[1:].split()[0]
                protein_name = line[1:]
                species = find_species(line, spec_translate_list)
        else:
            sequence += line

    if protein_id:
        fasta_dict[protein_id] = {
            "name": protein_name,
            "sequence": sequence,
            "species": species,
        }

    return fasta_dict
