"""
Data loading, validation, and column mapping service.
Extracted from notebook DataTransformation class (Cell 1).

Supported peptidomics input formats
------------------------------------
The loader accepts peptide/protein report exports from several proteomics
software packages.  Column names are harmonised via
``get_comprehensive_column_mapping()`` and multi-protein accession strings are
split by ``extract_protein_id()``.  Example files for each format live in
``peptide/notebooks/examples/additional_peptidomic_input_formats/``.

    Software              Protein column       Multi-protein separator
    --------------------  -------------------  --------------------------
    Proteome Discoverer   Master Protein       "; "  (semicolon)
                          Accessions
    MaxQuant              Proteins             ";"   (semicolon)
    PEAKS                 Accession            ";"   (accession|name pairs)
    Spectronaut           PG.ProteinGroups     ";" / "," (protein groups)
    Skyline               Protein              (usually one per row)

``extract_protein_id`` splits on ``;``, ``/`` and ``,`` and unwraps the
UniProt ``db|ACCESSION|NAME`` pipe format, so accessions from any of the above
reduce to bare UniProt IDs.  ``strip_inline_modifications`` removes PTM
annotations embedded in the peptide string (e.g. PEAKS ``PEP(+57.02)TIDE``,
bracketed ``PEPTIDE[DN]``) so sequences remain BLAST-compatible.
"""
import io
import re
import ast
import pandas as pd
import numpy as np
from django.conf import settings


def find_species(header):
    """Search for a species in the header and return the first element (species name)."""
    header_lower = header.lower()
    for spec_group in settings.SPEC_TRANSLATE_LIST:
        for term in spec_group[1:]:
            if term.lower() in header_lower:
                return spec_group[0]
    return "unknown"


def parse_fasta_headers_file(filepath):
    """Parse the protein_headers.txt file to build protein_dict."""
    fasta_dict = {}
    try:
        with open(filepath, 'r') as file:
            protein_id = ""
            protein_name = ""
            species = ""
            for line in file:
                line = line.strip()
                if line.startswith('>'):
                    if protein_id:
                        fasta_dict[protein_id] = {
                            "name": protein_name,
                            "species": species
                        }
                    header_parts = line[1:].split('|')
                    if len(header_parts) > 2:
                        protein_id = header_parts[1]
                        protein_name_full = re.split(r' OS=', header_parts[2])[0]
                        protein_name = protein_name_full
                        species = find_species(line)
                    else:
                        protein_id = ""
            if protein_id:
                fasta_dict[protein_id] = {
                    "name": protein_name,
                    "species": species
                }
    except FileNotFoundError:
        pass
    return fasta_dict


def parse_uploaded_fasta(file_content, filename=''):
    """Parse uploaded FASTA file content bytes into a protein dictionary."""
    fasta_dict = {}
    if isinstance(file_content, bytes):
        fasta_text = file_content.decode('utf-8')
    else:
        fasta_text = file_content
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
                    "species": species
                }
            sequence = ""
            header_parts = line[1:].split('|')
            if len(header_parts) > 2:
                protein_id = header_parts[1]
                protein_name_full = re.split(r' OS=', header_parts[2])[0]
                protein_name = protein_name_full
                species = find_species(line)
            else:
                protein_id = ""
        else:
            sequence += line

    if protein_id:
        fasta_dict[protein_id] = {
            "name": protein_name,
            "sequence": sequence,
            "species": species
        }

    return fasta_dict


def validate_fasta_format(file_content):
    """Validate that file content follows proper FASTA format."""
    try:
        if isinstance(file_content, bytes):
            content = file_content.decode('utf-8')
        else:
            content = file_content
        lines = content.strip().split('\n')

        if not lines:
            return False, "File is empty"

        if not any(line.strip().startswith('>') for line in lines):
            return False, "No FASTA headers found (lines starting with '>')"

        has_header = False
        has_sequence = False
        current_sequence_length = 0

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            if line.startswith('>'):
                if len(line) <= 1:
                    return False, "Header with no identifier"
                has_header = True
                if i > 0 and current_sequence_length == 0 and has_sequence:
                    return False, "Empty sequence found"
                current_sequence_length = 0
            else:
                if not has_header:
                    return False, "Sequence without preceding header"
                valid_chars = set('ACDEFGHIKLMNPQRSTVWYXBZJOU*-')
                if not all(c.upper() in valid_chars for c in line):
                    nucleotide_chars = set('ATCGRYSWKMBDHVN-')
                    if not all(c.upper() in nucleotide_chars for c in line):
                        return False, f"Invalid characters in sequence at line {i+1}"
                has_sequence = True
                current_sequence_length += len(line)

        if not (has_header and has_sequence):
            return False, "Must have at least one header and one sequence"
        return True, ""
    except Exception as e:
        return False, str(e)


def get_comprehensive_column_mapping():
    """Comprehensive column mapping for different proteomics software."""
    return {
        'Position.in.Proteins': 'Positions in Proteins',
        'Position in Protein': 'Positions in Proteins',
        'Positions in Protein': 'Positions in Proteins',
        'Positions.in.Proteins': 'Positions in Proteins',
        'Position': 'Positions in Proteins',
        'PEP.PeptidePosition': 'Positions in Proteins',
        'Position in Master Protein': 'Positions in Proteins',
        'Positions in Master Proteins': 'Positions in Proteins',
        'Position in Master Proteins': 'Positions in Proteins',
        'Positions in Master Protein': 'Positions in Proteins',
        'Peptide Sequence': 'Sequence',
        'pep_seq': 'Sequence',
        'PEP.StrippedSequence': 'Sequence',
        'Peptide': 'Sequence',
        'peptide': 'Sequence',
        'sequence': 'Sequence',
        'Stripped Sequence': 'Sequence',
        'Annotated.Sequence': 'Annotated Sequence',
        'Modified sequence': 'Annotated Sequence',
        'Modified Sequence': 'Annotated Sequence',
        'EG.ModifiedPeptide': 'Annotated Sequence',
        'modified_peptide': 'Annotated Sequence',
        'Master.Protein.Accessions': 'Protein',
        'Master.Protein.Accession': 'Protein',
        'Master Protein Accession': 'Protein',
        'Master Protein Accessions': 'Protein',
        'Leading proteins': 'Protein',
        'Protein Name': 'Protein',
        'prot_acc': 'Protein',
        'Accession Number': 'Protein',
        'Accession': 'Protein',            # PEAKS
        'accession': 'Protein',
        'PG.ProteinGroups': 'Protein',     # Spectronaut
        'Protein Accession': 'Protein',
        'protein': 'Protein',
        'accessions': 'Protein',
        'Accessions': 'Protein',
        'Proteins': 'Protein',             # MaxQuant
        'Protein': 'Protein',
        'Protein.Accessions': 'Protein',
        'Protein.Accession': 'Protein',
        'Protein IDs': 'Protein',
        'Protein ID': 'Protein',
        'UniProt IDs': 'Protein',
        'UniProt ID': 'Protein',
        'Gene Names': 'Protein',
        'Gene Name': 'Protein',
    }


def strip_inline_modifications(sequence):
    """Remove inline modification annotations from a peptide sequence.

    Several peptidomics tools embed PTM/modification information directly in
    the peptide string rather than in a separate column, which leaves the
    sequence with non-amino-acid characters that break BLAST and exact
    matching.  Examples handled:

        PEAKS        'ADYEKHKVYAC(+57.02)EVTHQG'  -> 'ADYEKHKVYACEVTHQG'
        bracket      'NILREKQTDEIK[DN]'           -> 'NILREKQTDEIK'
        brace/UniMod 'PEP{Oxidation}TIDE'         -> 'PEPTIDE'
        flanks       'K.PEPTIDE.R'                -> 'PEPTIDE'

    Already-clean sequences pass through unchanged.  Non-string / NaN values
    are returned untouched so pandas missing values are preserved.
    """
    if not isinstance(sequence, str):
        return sequence
    s = sequence.strip()
    if not s:
        return sequence

    # Strip enzymatic flanking residues "X.PEPTIDE.Y" -> "PEPTIDE"
    dot_parts = s.split('.')
    if len(dot_parts) == 3 and len(dot_parts[0]) <= 2 and len(dot_parts[2]) <= 2:
        s = dot_parts[1]

    # Remove bracketed / parenthesised / braced modification annotations
    s = re.sub(r'\([^)]*\)', '', s)
    s = re.sub(r'\[[^\]]*\]', '', s)
    s = re.sub(r'\{[^}]*\}', '', s)

    # Drop any residual non-letter characters (digits, +, ., etc.)
    cleaned = re.sub(r'[^A-Za-z]', '', s)

    # If stripping removed everything, fall back to the original so we never
    # silently blank out a peptide we did not understand.
    return cleaned if cleaned else sequence


def extract_protein_id(protein_string, protein_dict=None):
    """
    Extract clean protein ID(s) from accession string.
    Returns single string for one protein, list for multiple, or [] for empty.
    Also updates protein_dict with info extracted from accession strings.
    """
    try:
        if hasattr(protein_string, '__len__') and not isinstance(protein_string, str):
            if pd.isna(protein_string).any():
                return []
        else:
            if pd.isna(protein_string):
                return []
    except (ValueError, TypeError):
        pass

    if protein_string == '' or str(protein_string).strip() == '':
        return []

    protein_str = str(protein_string).strip()

    # Handle malformed list strings
    if protein_str.startswith('[') and protein_str.endswith(']'):
        try:
            parsed = ast.literal_eval(protein_str)
            if isinstance(parsed, list):
                flattened = []
                for item in parsed:
                    if isinstance(item, str):
                        if item.startswith('[') and item.endswith(']'):
                            try:
                                nested = ast.literal_eval(item)
                                if isinstance(nested, list):
                                    flattened.extend([str(x) for x in nested if x])
                                else:
                                    flattened.append(str(item))
                            except (ValueError, SyntaxError):
                                flattened.append(str(item))
                        else:
                            flattened.append(str(item))
                    else:
                        flattened.append(str(item))
                if flattened:
                    protein_str = ';'.join(flattened)
        except (ValueError, SyntaxError):
            pass

    split_pattern = r'\s*;\s*|\s*/\s*|\s*,\s*'
    protein_entries = re.split(split_pattern, protein_str)
    protein_ids = []

    for entry in protein_entries:
        entry = entry.strip()
        protein_id = None

        if '|' in entry:
            parts = entry.split('|')
            if len(parts) >= 3:
                # UniProt-style db|ACCESSION|NAME (e.g. sp|P02666|CASB_BOVIN)
                protein_id = parts[1].split(';')[0].split('/')[0].strip()
            elif len(parts) == 2:
                # PEAKS-style ACCESSION|NAME (e.g. A0A087WWV8|A0A087WWV8_HUMAN)
                protein_id = parts[0].split(';')[0].split('/')[0].strip()
            else:
                protein_id = entry
        elif entry.startswith('CON__'):
            protein_id = entry[5:]
        elif entry.startswith('REV__'):
            protein_id = entry[5:]
        else:
            for prefix in ['CONT_', 'REV_', 'CON_']:
                if entry.startswith(prefix):
                    protein_id = entry[len(prefix):]
                    break
            else:
                protein_id = entry

        if protein_dict is not None and protein_id not in protein_dict:
            name = ""
            species = ""
            if "|" in entry:
                parts = entry.split("|")
                if len(parts) == 3:
                    name_species = parts[2]
                    if "_" in name_species:
                        name, species = name_species.split("_", 1)
                    else:
                        name = name_species
                elif len(parts) == 2:
                    # PEAKS-style ACCESSION|NAME — second field is the name
                    name = parts[1]
            protein_dict[protein_id] = {
                "name": name,
                "species": species
            }

        protein_ids.append(protein_id)

    clean_protein_ids = [pid for pid in protein_ids if pid and str(pid).strip()]

    if not clean_protein_ids:
        return []
    elif len(clean_protein_ids) == 1:
        return clean_protein_ids[0]
    else:
        return clean_protein_ids


def handle_separate_position_columns(df):
    """Handle software that provides separate protein, start, and end columns."""
    position_patterns = [
        {'protein': ['Protein', 'Proteins', 'Leading proteins'], 'start': ['Start position'], 'end': ['End position']},
        {'protein': ['Protein', 'Protein'], 'start': ['Peptide start'], 'end': ['Peptide end']},
        {'protein': ['Protein', 'Protein'], 'start': ['Start'], 'end': ['End'], 'sequence': ['Peptide Sequence']},
        {'protein': ['Protein', 'prot_acc'], 'start': ['pep_res_before'], 'end': ['pep_res_after']},
        {'protein': ['Protein', 'Protein Accession'], 'start': ['Start'], 'end': ['End']},
        {'protein': ['Protein', 'protein'], 'start': ['protein_start'], 'end': ['protein_end']},
        {'protein': ['Protein', 'accessions'], 'start': ['start'], 'end': ['end']},
        {'protein': ['Protein', 'Accessions'], 'start': ['Start'], 'end': ['End']},
    ]

    created_start = False
    created_stop = False

    for pattern in position_patterns:
        start_col = None
        end_col = None

        if pattern.get('start'):
            for col_name in pattern['start']:
                if col_name in df.columns:
                    start_col = col_name
                    break

        if pattern.get('end'):
            for col_name in pattern['end']:
                if col_name in df.columns:
                    end_col = col_name
                    break

        if start_col and 'start' not in df.columns:
            df['start'] = pd.to_numeric(df[start_col], errors='coerce')
            created_start = True

        if end_col and 'end' not in df.columns:
            df['end'] = pd.to_numeric(df[end_col], errors='coerce')
            created_stop = True

        if (created_start or 'start' in df.columns) and (created_stop or 'end' in df.columns):
            break

    return df


def load_and_validate_file(file_content, filename, file_type, protein_dict=None):
    """
    Load and validate uploaded data files.

    Args:
        file_content: bytes OR a file-like object (Django UploadedFile, BytesIO, etc.)
        filename: original filename
        file_type: 'Peptidomic' or 'MBPDB'
        protein_dict: optional dict to populate with protein info

    Returns:
        tuple: (DataFrame or None, status 'yes'/'no', error_msg, warning_msg)
    """
    try:
        error_msg = ""
        warning_msg = ""
        extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

        # Accept either bytes or a seekable file-like object.
        # Passing the file object directly avoids loading the whole file into
        # memory (important for large Excel files already streamed to disk by
        # Django's TemporaryFileUploadHandler).
        if isinstance(file_content, (bytes, bytearray)):
            file_stream = io.BytesIO(file_content)
        else:
            # File-like object — seek to start in case it was already read
            file_content.seek(0)
            file_stream = file_content

        # Load data based on file extension
        if extension == 'csv':
            df = _try_delimiters(file_stream, [',', ';', '|', '\t'])
            if df is None:
                return None, 'no', (
                    "Could not parse CSV file with any common delimiter "
                    "(tried: comma, semicolon, pipe, tab). "
                    "Check that the file is not corrupt and uses a standard delimiter."
                ), ""
        elif extension in ['txt', 'tsv']:
            df = _try_delimiters(file_stream, ['\t', ',', ';', '|'])
            if df is None:
                return None, 'no', (
                    "Could not parse TXT/TSV file with any common delimiter "
                    "(tried: tab, comma, semicolon, pipe)."
                ), ""
        elif extension in ['xlsx', 'xls']:
            try:
                engine = 'openpyxl' if extension == 'xlsx' else 'xlrd'
                df = pd.read_excel(file_stream, engine=engine)
            except ImportError as e:
                missing_lib = 'openpyxl' if extension == 'xlsx' else 'xlrd'
                return None, 'no', (
                    f"Cannot read {extension.upper()} file: the '{missing_lib}' library is not installed. "
                    f"Run: pip install {missing_lib}"
                ), ""
            except Exception as e:
                return None, 'no', (
                    f"Could not read Excel file '{filename}': {type(e).__name__}: {str(e)}. "
                    "Ensure the file is a valid Excel workbook and is not password-protected or corrupted."
                ), ""
        else:
            return None, 'no', (
                f"Unsupported file format '.{extension}'. "
                "Please upload a .csv, .txt, .tsv, .xlsx, or .xls file."
            ), ""

        # Clean
        df.columns = df.columns.str.strip()
        df = _normalize_duplicate_column_names(df)
        df = df.dropna(how='all')
        df = df[~df.astype(str).apply(lambda row: row.str.strip().eq('').all(), axis=1)]

        if file_type == 'MBPDB':
            return _validate_mbpdb_file(df, filename)
        else:
            return _validate_peptidomic_file(df, filename, protein_dict)

    except Exception as e:
        import traceback
        tb_line = traceback.format_exc().strip().split('\n')[-1]
        return None, 'no', f"{file_type} File Error: {type(e).__name__}: {str(e)} [{tb_line}]", ""


def _try_delimiters(file_stream, delimiters):
    """Try different delimiters to parse a CSV/TSV file."""
    for delimiter in delimiters:
        try:
            file_stream.seek(0)
            temp_df = pd.read_csv(file_stream, sep=delimiter)
            if len(temp_df.columns) > 1:
                return temp_df
        except Exception:
            continue
    return None


def _normalize_duplicate_column_names(df):
    """
    Rename pandas auto-generated duplicate column suffixes to _repN notation.

    When a file has duplicate column names, pandas appends .1, .2, etc. to make
    them unique (e.g., Sample1, Sample1 → Sample1, Sample1.1).  This function
    converts the .N-suffixed variants to _rep{N+1} so they are detected as
    technical replicates downstream (e.g., Sample1.1 → Sample1_rep2).

    The original base column (Sample1) keeps its name and implicitly acts as
    rep1; each suffixed duplicate is renamed to rep{suffix+1}.  Only columns
    whose base name also exists in the DataFrame are touched.
    """
    cols = list(df.columns)
    base_to_suffixed = {}  # base → [(col_name, numeric_suffix)]

    for col in cols:
        m = re.match(r'^(.*?)\.(\d+)$', col)
        if m:
            base, n = m.group(1), int(m.group(2))
            if base in cols:  # base column must also exist
                base_to_suffixed.setdefault(base, []).append((col, n))

    rename_map = {}
    for base, entries in base_to_suffixed.items():
        for col_name, n in entries:
            rename_map[col_name] = f"{base}_rep{n + 1}"

    return df.rename(columns=rename_map) if rename_map else df


def _validate_mbpdb_file(df, filename):
    """Validate MBPDB functional data file."""
    required_columns_info = {
        'search_peptide': {
            'aliases': [
                'Search peptide', 'search peptide', 'Search_Peptide', 'search_peptide',
                'SEARCH_PEPTIDE', 'Search peptides', 'search peptides'
            ],
        },
        'peptide': {
            'aliases': ['Peptide', 'peptide'],
        },
        'function': {
            'aliases': ['Function', 'function', 'FUNCTION', 'Functions', 'functions', 'Func', 'func'],
        }
    }

    # Check for missing required columns
    missing_explanations = []
    for std_col, info in required_columns_info.items():
        found = any(alias in df.columns for alias in info['aliases'])
        if not found:
            missing_explanations.append(f"'{std_col}' (tried: {', '.join(info['aliases'][:4])})")

    if missing_explanations:
        found_cols = ', '.join(df.columns[:20].tolist())
        return None, 'no', (
            f"MBPDB File Error: Missing required columns: {'; '.join(missing_explanations)}. "
            f"Columns found in file: {found_cols}"
            + (f" ... ({len(df.columns)} total)" if len(df.columns) > 20 else "")
        ), ""

    # Check for empty required columns
    for std_col, info in required_columns_info.items():
        for alias in info['aliases']:
            if alias in df.columns:
                if df[alias].isna().all() or (df[alias].astype(str).str.strip() == '').all():
                    return None, 'no', f"MBPDB File Error: Required column '{std_col}' exists but is completely empty", ""
                break

    # Rename to standard names
    df.rename(columns={
        'Search peptide': 'search_peptide',
        'Protein ID': 'protein_id',
        'Peptide': 'peptide',
        'Protein description': 'protein_description',
        'Species': 'species',
        'Intervals': 'intervals',
        'Function': 'function',
        'Additional details': 'additional_details',
        'IC50 (μM)': 'ic50',
        'Inhibition type': 'inhibition_type',
        'Inhibited microorganisms': 'inhibited_microorganisms',
        'PTM': 'ptm',
        'Title': 'title',
        'Authors': 'authors',
        'Abstract': 'abstract',
        'DOI': 'doi',
        'Search type': 'search_type',
        'Scoring matrix': 'scoring_matrix',
    }, inplace=True)

    return df, 'yes', "", ""


def _validate_peptidomic_file(df, filename, protein_dict=None):
    """Validate peptidomic data file."""
    warning_msg = ""
    required_columns = ['Positions in Proteins', 'Sequence', 'Protein']

    # Apply comprehensive column mapping
    column_mapping = get_comprehensive_column_mapping()
    for original_col in list(df.columns):
        if original_col in column_mapping:
            new_col_name = column_mapping[original_col]
            if new_col_name not in df.columns:
                if new_col_name == 'Protein':
                    df[new_col_name] = df[original_col].apply(
                        lambda x: extract_protein_id(x, protein_dict)
                    )
                else:
                    df[new_col_name] = df[original_col].copy()

    # Normalize the Protein column to clean accession IDs regardless of the
    # source column name.  The mapping loop above extracts IDs when it renames
    # a differently-named column (e.g. MaxQuant 'Proteins', PEAKS 'Accession'),
    # but it skips the identity 'Protein' -> 'Protein' case.  Tools that name
    # their column literally 'Protein' (e.g. Skyline) therefore arrive
    # with full 'sp|ACC|NAME' accessions or separator-joined multi-protein
    # strings still intact — normalize those raw string cells here so protein
    # splitting is consistent across software.  Cells already reduced to a bare
    # ID or a list are idempotent / skipped.
    if 'Protein' in df.columns:
        df['Protein'] = df['Protein'].apply(
            lambda x: extract_protein_id(x, protein_dict) if isinstance(x, str) else x
        )

    # Strip inline modification annotations from the peptide sequence so tools
    # that embed PTMs in the sequence string (e.g. PEAKS 'PEP(+57.02)TIDE' or
    # bracketed 'PEPTIDE[DN]') yield clean amino-acid sequences usable for
    # BLAST / exact matching.  Already-clean sequences are unaffected.
    if 'Sequence' in df.columns:
        df['Sequence'] = df['Sequence'].apply(strip_inline_modifications)

    # Handle separate position columns if needed
    if 'Positions in Proteins' not in df.columns:
        df = handle_separate_position_columns(df)

    # Check for essential column
    missing = set(required_columns) - set(df.columns)
    if missing:
        if 'Sequence' not in df.columns:
            alt_sequence_cols = ['Annotated Sequence', 'Peptide Sequence', 'peptide']
            has_alt = any(col in df.columns for col in alt_sequence_cols)
            if not has_alt:
                found_cols = ', '.join(df.columns[:20].tolist())
                suffix = f" ... ({len(df.columns)} total)" if len(df.columns) > 20 else ""
                return None, 'no', (
                    "Missing required sequence column. Expected one of: 'Sequence', "
                    "'Annotated Sequence', 'Peptide Sequence', 'peptide'. "
                    f"Columns found in file: {found_cols}{suffix}"
                ), ""

        missing_msgs = []
        if 'Protein' in missing:
            missing_msgs.append("'Protein' (protein identification will be limited)")
        if 'Positions in Proteins' in missing:
            missing_msgs.append("'Positions in Proteins' (position-based analysis unavailable)")

        if missing_msgs:
            warning_msg = "Missing optional columns: " + "; ".join(missing_msgs)

    return df, 'yes', "", warning_msg


def extract_sequences(df):
    """Extract unique peptide sequences from peptidomic data."""
    if 'Sequence' not in df.columns:
        df = df.copy()
        df['Sequence'] = pd.NA

        def extract_sequence(annotated_seq):
            if pd.isna(annotated_seq):
                return pd.NA
            if ',' in str(annotated_seq):
                sequences = []
                for seq in str(annotated_seq).split(','):
                    seq = seq.strip()
                    if '.' in seq:
                        parts = seq.split('.')
                        if len(parts) > 1:
                            sequences.append(parts[1])
                    else:
                        sequences.append(seq)
                return sequences
            if '.' in str(annotated_seq):
                parts = str(annotated_seq).split('.')
                if len(parts) > 1:
                    return parts[1]
            return annotated_seq

        if 'Annotated Sequence' in df.columns:
            df['Sequence'] = df['Annotated Sequence'].apply(extract_sequence)
            df = df.explode('Sequence')

    seqs = df['Sequence'].dropna().apply(strip_inline_modifications)
    return seqs.dropna().unique().tolist()


def find_invalid_peptide_sequences(sequences):
    """Return peptide sequences containing non-alphabetic characters.

    BLAST only accepts amino-acid letters; a single sequence with digits,
    punctuation, or whitespace causes blastp to fail and the entire batch
    silently returns zero matches.
    """
    invalid = []
    for seq in sequences:
        s = str(seq).strip()
        if not s:
            continue
        if not s.isalpha():
            invalid.append(s)
    return invalid


def find_missing_proteins(df, protein_dict):
    """Find proteins in the data that are not in the protein dictionary."""
    if df is None or df.empty or 'Protein' not in df.columns:
        return set()

    # Use a separate dict for extraction to avoid side-effect of extract_protein_id
    # adding proteins to the dict, which would make them appear as "not missing"
    extraction_dict = dict(protein_dict) if protein_dict else {}
    protein_accessions = df['Protein'].dropna().apply(lambda x: extract_protein_id(x, extraction_dict))

    unique_protein_list = set()
    for item in protein_accessions:
        if isinstance(item, list):
            unique_protein_list.update(item)
        elif isinstance(item, str) and item.strip():
            unique_protein_list.add(item.strip())

    # Clean up
    clean_protein_list = set()
    for protein in unique_protein_list:
        if protein and protein != 'Unknown' and protein != 'nan':
            protein_str = str(protein).strip()
            if protein_str.startswith('[') and protein_str.endswith(']'):
                try:
                    parsed_list = ast.literal_eval(protein_str)
                    if isinstance(parsed_list, list):
                        for p in parsed_list:
                            if p and str(p).strip() and str(p) != 'Unknown' and str(p) != 'nan':
                                clean_protein_list.add(str(p).strip())
                    else:
                        clean_protein_list.add(protein_str)
                except (ValueError, SyntaxError):
                    clean_protein_list.add(protein_str)
            else:
                clean_protein_list.add(protein_str)

    return {p for p in clean_protein_list if p not in protein_dict}


def _build_merge_key(df):
    """Build a composite key for merging peptidomic datasets.

    Key = Sequence (or Annotated Sequence) + Modifications.
    Protein and position columns are NOT part of the key — the same peptide
    identified from different proteins across datasets is still the same
    peptide and should be merged into one row.
    """
    # Prefer Sequence; fall back to Annotated Sequence
    if 'Sequence' in df.columns:
        seq = df['Sequence'].fillna('').astype(str).str.strip().str.lower()
    elif 'Annotated Sequence' in df.columns:
        # Strip flanking residues like "[K].PEPTIDE.[R]" → "PEPTIDE" so the
        # same peptide with different flanks across datasets merges to one
        # row. Mirrors the dot-split logic used by extract_sequences() and
        # process_pd_results().
        def _strip_flanks(s):
            if '.' in s:
                parts = s.split('.')
                if len(parts) > 1:
                    return parts[1]
            return s
        seq = (df['Annotated Sequence'].fillna('').astype(str).str.strip()
               .apply(_strip_flanks).str.lower())
    else:
        seq = pd.Series('', index=df.index)

    mods = (df['Modifications'].fillna('').astype(str).str.strip().str.lower()
            if 'Modifications' in df.columns
            else pd.Series('', index=df.index))

    return seq + '||' + mods


def merge_peptidomic_datasets(dataframes):
    """Merge multiple peptidomic DataFrames on a composite peptide key.

    - Shared metadata columns (non-numeric identifiers) are coalesced.
    - Numeric/abundance columns are kept from every dataset (renamed with a
      file-index suffix when names collide).
    - Peptides unique to one dataset appear as new rows with NaN in the
      abundance columns of the other datasets.
    - The temporary merge key column is removed before returning.

    Args:
        dataframes: list of (filename, DataFrame) tuples

    Returns:
        merged DataFrame
    """
    if len(dataframes) < 2:
        raise ValueError('At least two datasets are required for merging.')

    KEY_COL = '__merge_key__'

    # Columns that form the peptide identity — never suffixed, coalesced (prefer left)
    identity_cols = {
        'Sequence', 'Annotated Sequence', 'Modifications',
        'Peptide Modified Sequence', 'Modified sequence', 'Modified Sequence',
        'Number of Missed Cleavages', 'Confidence', 'Sequence Length',
        'Marked as', 'Checked',
    }

    # Metadata columns — kept as a single column; differing values are
    # concatenated with "; " so the user can see which dataset contributed what
    # (matching Proteome Discoverer's convention for multi-protein peptides).
    # Same values across datasets are not duplicated.
    metadata_cols = {
        'Master Protein Accessions', 'Positions in Proteins', 'Protein',
        'Positions in Master Proteins', 'Modifications in Master Proteins',
        'Master Protein Descriptions', 'Protein Groups',
        'Top Apex RT in min', 'Peptide Groups Peptide Group ID',
        'Theo MHplus in Da', 'Quan Info', 'PSMs',
        'Confidence by Search Engine', 'q-Value by Search Engine',
        'XCorr by Search Engine', 'PEP', 'q-Value', 'RT in min',
        'Precursor', 'Precursor Charge', 'Precursor Mz',
    }

    def _normalize_val(val):
        """Convert a value to a clean string, dropping trailing .0 from floats
        that are really integers (e.g. 392.0 → '392').  Also converts Python
        list representations like ['P1', 'P2'] to 'P1; P2'."""
        try:
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return ''
            # Actual Python list or array — join elements
            if isinstance(val, (list, np.ndarray)):
                parts = [str(v).strip() for v in val if str(v).strip()]
                return '; '.join(parts) if parts else ''
            is_na = pd.isna(val)
            if isinstance(is_na, (bool, np.bool_)) and is_na:
                return ''
        except (ValueError, TypeError):
            pass
        s = str(val).strip()
        # Detect string representation of a Python list, e.g. "['P1', 'P2']"
        if s.startswith('[') and s.endswith(']'):
            try:
                import ast
                parsed = ast.literal_eval(s)
                if isinstance(parsed, list):
                    parts = [str(v).strip() for v in parsed if str(v).strip()]
                    return '; '.join(parts) if parts else ''
            except (ValueError, SyntaxError):
                pass
        # If it looks like a float that is really an integer, drop the .0
        try:
            f = float(s)
            if f == int(f):
                s = str(int(f))
        except (ValueError, OverflowError):
            pass
        return s

    def _semicolon_coalesce(left_series, right_series):
        """Merge two series into one: identical values kept as-is,
        differing values joined with '; '.  Both sides may already
        contain semicolon-separated parts — each part is compared
        individually so duplicates are never introduced."""
        def _combine(left_val, right_val):
            l_str = _normalize_val(left_val)
            r_str = _normalize_val(right_val)
            if not l_str and not r_str:
                return np.nan
            if not l_str:
                return r_str
            if not r_str:
                return l_str
            # Split both sides into individual parts for comparison
            existing = [_normalize_val(p) for p in l_str.split(';') if _normalize_val(p)]
            right_parts = [_normalize_val(p) for p in r_str.split(';') if _normalize_val(p)]
            existing_set = set(existing)
            new_parts = [p for p in right_parts if p not in existing_set]
            if new_parts:
                return '; '.join(existing + new_parts)
            return '; '.join(existing)
        return pd.Series(
            [_combine(l, r) for l, r in zip(left_series, right_series)],
            index=left_series.index,
        )

    # Columns that may contain Python lists — normalize to '; '-separated strings
    list_prone_cols = {
        'Protein', 'Master Protein Accessions', 'Positions in Proteins',
        'Positions in Master Proteins', 'Master Protein Descriptions',
        'Protein Groups',
    }

    def _normalize_list_cells(df):
        """Convert list-valued cells to '; '-joined strings."""
        for col in list_prone_cols & set(df.columns):
            mask = df[col].apply(lambda v: isinstance(v, (list, np.ndarray)))
            if mask.any():
                df.loc[mask, col] = df.loc[mask, col].apply(
                    lambda v: '; '.join(str(x).strip() for x in v if str(x).strip())
                )
            # Also fix string representations of lists, e.g. "['P1', 'P2']"
            str_mask = df[col].astype(str).str.match(r"^\[.*\]$", na=False)
            if str_mask.any():
                def _parse_list_str(v):
                    try:
                        parsed = ast.literal_eval(str(v))
                        if isinstance(parsed, list):
                            return '; '.join(str(x).strip() for x in parsed if str(x).strip())
                    except (ValueError, SyntaxError):
                        pass
                    return v
                df.loc[str_mask, col] = df.loc[str_mask, col].apply(_parse_list_str)
        return df

    # ---- Step 1: build merge keys and tag each frame --------------------
    keyed_frames = []
    for _fname, df in dataframes:
        df = df.copy()
        df = _normalize_list_cells(df)
        df[KEY_COL] = _build_merge_key(df)
        keyed_frames.append(df)

    # ---- Step 2: iterative outer merge ----------------------------------
    merged = keyed_frames[0]
    for idx in range(1, len(keyed_frames)):
        right = keyed_frames[idx]

        # Determine which columns overlap (excluding the key)
        left_cols = set(merged.columns) - {KEY_COL}
        right_cols = set(right.columns) - {KEY_COL}
        common = left_cols & right_cols

        # Identity columns: silently coalesced (prefer left, fill from right)
        id_overlap = common & identity_cols
        # Metadata columns: semicolon-coalesced into a single column
        meta_overlap = common & metadata_cols
        # Remaining overlapping columns: need _ds# suffixing (abundance data)
        data_overlap = common - identity_cols - metadata_cols

        # Rename right-side data-overlap columns with a dataset index suffix
        rename_map = {}
        for col in data_overlap:
            new_name = col + '_ds' + str(idx + 1)
            while new_name in merged.columns or new_name in right.columns:
                new_name += '_'
            rename_map[col] = new_name
        right_renamed = right.rename(columns=rename_map)

        merged = merged.merge(right_renamed, on=KEY_COL, how='outer',
                              suffixes=('', '_right'))

        # Coalesce identity columns (prefer left, fill from right)
        for col in id_overlap:
            right_col = col + '_right'
            if right_col in merged.columns:
                merged[col] = merged[col].combine_first(merged[right_col])
                merged.drop(columns=[right_col], inplace=True)

        # Semicolon-coalesce metadata columns
        for col in meta_overlap:
            right_col = col + '_right'
            if right_col in merged.columns:
                merged[col] = _semicolon_coalesce(merged[col], merged[right_col])
                merged.drop(columns=[right_col], inplace=True)

    # ---- Step 3: drop the merge key ------------------------------------
    merged.drop(columns=[KEY_COL], inplace=True)

    # ---- Step 4: reorder columns — identity & metadata first, then abundance
    # Preferred leading column order (present columns only)
    leading_order = [
        'Sequence', 'Annotated Sequence', 'Protein',
        'Master Protein Accessions', 'Master Protein Descriptions',
        'Protein Groups', 'Positions in Proteins',
        'Positions in Master Proteins', 'Modifications',
        'Modifications in Master Proteins',
        'Peptide Modified Sequence', 'Modified sequence', 'Modified Sequence',
        'Number of Missed Cleavages', 'Sequence Length',
        'Confidence', 'Marked as', 'Checked',
        'Peptide Groups Peptide Group ID',
        'Theo MHplus in Da', 'Quan Info', 'Top Apex RT in min',
        'PSMs', 'Confidence by Search Engine', 'q-Value by Search Engine',
        'XCorr by Search Engine', 'PEP', 'q-Value', 'RT in min',
        'Precursor', 'Precursor Charge', 'Precursor Mz',
    ]
    leading = [c for c in leading_order if c in merged.columns]
    remaining = [c for c in merged.columns if c not in leading]
    merged = merged[leading + remaining]

    return merged


def get_filtered_columns(df):
    """Get abundance columns by filtering out known non-abundance columns."""
    columns_to_exclude = [
        'Marked as', 'Marked.as', 'Number of Missed Cleavages', 'Number.of.Missed.Cleavages',
        'Missed Cleavages', 'Missed.Cleavages', 'Checked', 'Confidence',
        'Annotated Sequence', 'Annotated.Sequence', 'Unnamed: 3', 'Unnamed:.3',
        'Modifications', 'Modifications.in.Proteins', 'Modifications.in.Master.Proteins',
        'Protein Groups', 'Protein.Groups', 'Proteins', 'PSMs',
        'Protein', 'Master.Protein.Accessions',
        'Master Protein Descriptions', 'Master.Protein.Descriptions', 'Description',
        'Positions in Master Proteins', 'Positions.in.Master.Proteins',
        'Positions in Proteins', 'Positions.in.Proteins',
        'Modifications in Master Proteins', 'Modifications.in.Master.Proteins',
        'Modifications in Master Proteins all Sites', 'Modifications.in.Master.Proteins.all.Sites',
        'Theo MHplus in Da', 'Theo.MHplus.in.Da', 'Quan Info', 'Quan.Info',
        "Theo. MH+ [Da]", "Theo.MH+.[Da]",
        'Confidence by Search Engine', 'Confidence.by.Search.Engine',
        'q-Value by Search Engine', 'q-Value.by.Search.Engine',
        'XCorr by Search Engine', 'XCorr.by.Search.Engine',
        'PEP', 'q-Value', 'RT in min', 'RT.in.min',
        'Sequence', 'Sequence Length', 'Sequence.Length',
        'search_peptide', 'Peptide', 'protein_id', 'protein_description',
        'Alignment', 'Species', 'Intervals', 'function', 'Unique Peptide ID', 'unique.ID',
        'SVM_Score', 'start', 'end',
        'Abundance Ratio', 'Abundance.Ratio',
        'Reverse', 'Potential contaminant', 'id', 'Protein group IDs',
        'N-term cleavage window', 'C-term cleavage window',
        'Amino acid before', 'First amino acid', 'Second amino acid',
        'Second last amino acid', 'Last amino acid', 'Amino acid after',
        'A Count', 'R Count', 'N Count', 'D Count', 'C Count', 'Q Count', 'E Count', 'G Count',
        'H Count', 'I Count', 'L Count', 'K Count', 'M Count', 'F Count', 'P Count', 'S Count',
        'T Count', 'W Count', 'Y Count', 'V Count', 'U Count', 'Length', 'Missed cleavages',
        'Mass', 'Leading razor protein', 'Start position', 'End position',
        'Unique (Groups)', 'Unique (Proteins)', 'Charges', 'Score',
        'Mod. peptide IDs', 'Evidence IDs', 'MS/MS IDs', 'Best MS/MS',
        'Oxidation (M) site IDs', 'MS/MS Count', ' Intensity',
        'Precursor', 'Precursor Charge', 'Precursor Mz',
        'Peptide Modified Sequence', 'Peptide start', 'Pept', 'Library Name',
        'Precursor m/z', 'Precursor Intensity', 'Precursor Isotope',
    ]

    exclude_substrings = [
        'Abundances by Bio Rep', 'Abundances.by.Bio.Rep',
        'Count', 'count', 'Origin', 'origin',
        'Average_Abundance', 'Average.Abundance', 'Avg_', 'Avg.',
        'PEP by Search Engine', 'PEP.by.Search.Engine',
        'SVM Score by Search Engine', 'SVM.Score.by.Search.Engine',
        'XCorr by Search Engine', 'XCorr.by.Search.Engine',
        'Top Apex RT', 'Top.Apex.RT'
    ]

    filtered_columns = []
    for col in df.columns:
        should_exclude = any(excl.lower() in col.lower() for excl in columns_to_exclude)
        has_excluded_substring = any(sub.lower() in col.lower() for sub in exclude_substrings)
        if not should_exclude and not has_excluded_substring:
            filtered_columns.append(col)

    return filtered_columns


def get_filtered_columns_fallback(df):
    """
    Fallback column detection when the primary filter is too aggressive.
    Uses a looser exclusion set — removes only definitively non-abundance columns.
    Returns all remaining columns so the user can manually choose.
    """
    # Only exclude columns whose entire name (lowercased) exactly matches
    # or starts with clearly non-abundance identifiers
    hard_exclude_prefixes = [
        'protein', 'sequence', 'position', 'modification', 'annotated',
        'checked', 'confidence', 'marked', 'peptide groups', 'unique', 'peptide_id',
        'search_peptide', 'protein_id', 'protein_description', 'species', 'intervals',
        'function', 'alignment', 'svm', 'xcorr', 'pep', 'q-value', 'rt in',
        'theo', 'quan', 'reverse', 'contaminant', 'unnamed', 'index',
    ]
    hard_exclude_substrings = [
        'modification', 'missed cleavage', 'amino acid', 'gene name',
        'protein group', 'protein accession', 'protein description',
    ]
    fallback_columns = []
    for col in df.columns:
        col_l = col.lower().strip()
        if any(col_l.startswith(p) for p in hard_exclude_prefixes):
            continue
        if any(s in col_l for s in hard_exclude_substrings):
            continue
        fallback_columns.append(col)
    return fallback_columns
