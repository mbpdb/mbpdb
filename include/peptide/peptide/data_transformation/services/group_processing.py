"""
Group variable assignment logic.
Extracted from notebook GroupProcessing class (Cell 2).
"""
import json

from .data_loader import get_filtered_columns


def parse_group_json(json_content, available_columns):
    """
    Parse a group definition JSON file.

    Args:
        json_content: string or bytes of JSON content
        available_columns: list of column names available in the dataset

    Returns:
        tuple: (group_data dict, error_message or None)
            group_data format: {
                "1": {"grouping_variable": "name", "abundance_columns": ["col1", "col2"]},
                ...
            }
    """
    try:
        if isinstance(json_content, bytes):
            json_content = json_content.decode('utf-8')
        simplified_data = json.loads(json_content)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, f"Invalid JSON file: {str(e)}"

    # Check for missing columns
    available_set = set(available_columns)
    missing_columns = []

    for group_name, columns in simplified_data.items():
        if isinstance(columns, list):
            for column in columns:
                if column not in available_set:
                    missing_columns.append(column)

    if missing_columns:
        missing_unique = sorted(set(missing_columns))
        return None, f"The following columns are not present in the current dataset: {', '.join(missing_unique)}"

    # Use the group name directly as the key (no numeric wrapping)
    group_data = {}
    for group_name, abundance_cols in simplified_data.items():
        if isinstance(abundance_cols, list):
            group_data[group_name] = {
                'grouping_variable': group_name,
                'abundance_columns': abundance_cols
            }
        else:
            return None, f"Invalid format: group '{group_name}' should map to a list of column names"

    return group_data, None


def build_group_data(selected_columns, group_name, existing_group_data=None):
    """
    Add a new group to the group data.

    Args:
        selected_columns: list of column names for this group
        group_name: name for the grouping variable
        existing_group_data: existing group_data dict to add to

    Returns:
        tuple: (updated group_data, error_message or None)
    """
    if not group_name:
        return existing_group_data, "Please enter a group name"
    if not selected_columns:
        return existing_group_data, "Please select at least one column"

    if existing_group_data is None:
        existing_group_data = {}

    existing_group_data[group_name] = {
        'grouping_variable': group_name,
        'abundance_columns': list(selected_columns)
    }

    return existing_group_data, None


def build_no_group_data(selected_columns):
    """
    Create individual groups for each selected column (no grouping).

    Args:
        selected_columns: list of column names

    Returns:
        tuple: (group_data, error_message or None)
    """
    if not selected_columns:
        return None, "Please select at least one absorbance column"

    group_data = {}
    for column in selected_columns:
        group_data[column] = {
            'grouping_variable': column,
            'abundance_columns': [column]
        }

    return group_data, None


def validate_group_data(group_data, df):
    """
    Validate that group data references valid columns in the dataframe.

    Args:
        group_data: group_data dict
        df: pandas DataFrame

    Returns:
        tuple: (is_valid, error_message or None)
    """
    if not group_data:
        return False, "No group data provided"

    df_columns = set(df.columns)
    for group_id, group_info in group_data.items():
        missing = [col for col in group_info['abundance_columns'] if col not in df_columns]
        if missing:
            return False, f"Group '{group_info['grouping_variable']}' references missing columns: {', '.join(missing)}"

    return True, None


def export_group_data_json(group_data):
    """
    Export group data to simplified JSON format for download.

    Returns:
        str: JSON string
    """
    simplified = {}
    for _, group_info in group_data.items():
        simplified[group_info['grouping_variable']] = group_info['abundance_columns']
    return json.dumps(simplified, indent=4)
