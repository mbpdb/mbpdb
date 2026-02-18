"""
Data loading, validation, and column mapping service.
Extracted from notebook DataTransformation class (Cell 1).
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
        'PG.ProteinGroups': 'Protein',
        'Protein Accession': 'Protein',
        'protein': 'Protein',
        'accessions': 'Protein',
        'Accessions': 'Protein',
        'Proteins': 'Protein',
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
            if len(parts) >= 2:
                protein_id = parts[1].split(';')[0].split('/')[0].strip()
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

    return df['Sequence'].dropna().unique().tolist()


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
