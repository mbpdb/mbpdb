"""
Heatmap rendering functions for heatmap_visualization.ipynb.

Importing this module does NOT trigger matplotlib or seaborn loading.
Those heavy libraries are imported lazily inside the rendering functions
that actually use them — on the first plot call, not on notebook startup.
"""

import logging
import pandas as pd
import numpy as np
import re
import copy
import warnings
from itertools import cycle

import _settings as settings

logger = logging.getLogger(__name__)


def _log_validation(message: str, level: str = "warning") -> None:
    """Log validation/warning messages (replaces legacy IPython display)."""
    if level == "error":
        logger.error(message)
    elif level == "info":
        logger.info(message)
    else:
        logger.warning(message)

# ---------------------------------------------------------------------------
# Constants from settings (safe to load — no matplotlib)
# ---------------------------------------------------------------------------
plot_heatmap     = settings.plot_heatmap
plot_zero        = settings.plot_zero
port_hm_settings = settings.port_hm_settings
chuck_size       = settings.chuck_size
legend_title     = settings.legend_title

# ---------------------------------------------------------------------------
# State globals — set by process_available_data()/update_plot() at runtime,
# read by visualize_* functions in this same module.
# ---------------------------------------------------------------------------
axis_number      = 0
total_plots      = 0
y_ticks          = []
max_sequence_length = 0
max_count        = 0
num_unique_count = 0
num_colors       = 0
style_map        = {}


# Define functions outside of class
def update_filenames(input_filename_port, input_filename_land):
    # Append directory and .png only when necessary
    #updated_filename_port = f'{images_folder_name}/{input_filename_port}.png' if input_filename_port else None
    #updated_filename_land = f'{images_folder_name}/{input_filename_land}.png' if input_filename_land else None
    updated_filename_port = f'{input_filename_port}' if input_filename_port else None
    updated_filename_land = f'{input_filename_land}' if input_filename_land else None

    return updated_filename_land, updated_filename_port

def proceed_with_label_specific_options(selected_bio_or_pep, bio_or_pep):
    # Initialize selected_peptides and selected_functions to ensure they are always defined
    selected_peptides = []
    selected_functions = []

    # Check and handle different cases based on bio_or_pep value
    if bio_or_pep == '1':  # Assuming '1' indicates selection of peptides
        selected_peptides = list(selected_bio_or_pep) if isinstance(selected_bio_or_pep, (list, tuple)) else [
            selected_bio_or_pep]
    elif bio_or_pep == '2':  # Assuming '2' indicates selection of functions
        selected_functions = list(selected_bio_or_pep) if isinstance(selected_bio_or_pep, (list, tuple)) else [
            selected_bio_or_pep]
    # Optional: handle unexpected bio_or_pep values
    else:
        error_message = f"Unexpected value for bio_or_pep: {bio_or_pep}"
        _log_validation(error_message)
    #print(f" DEBUG: selected_peptides: {selected_peptides}")
    return selected_peptides, selected_functions

def get_interval_start(peptide_label):
    """
    Extract numeric start from labels like '193-207' or '193-207 (Oxidation)'.
    """
    base = peptide_label.split()[0]  # take '193-207' from '193-207 (Oxidation)'
    return int(base.split('-')[0])

"""-----------------Export_Function---------------------------------"""

def calculate_centralized_y_limits(available_data_variables_dict, selected_peptides, selected_functions,
                                   ms_average_choice, bio_or_pep, filter_type, log_transform,
                                   manual_y_axis=False, y_min_manual=None, y_max_manual=None):
    """
    Centralized function to calculate y_min and y_max from all data sources (individual peptides and averaged data)
    Supports manual y-axis scaling override
    Returns: (y_min, y_max, all_min_values, all_max_values)
    """
    all_min_values = []
    all_max_values = []

    for var in available_data_variables_dict:
        # Get MS average data if needed
        if ms_average_choice in ['yes', 'only']:
            var_ms_data = available_data_variables_dict[var]['ms_data_list']
            if isinstance(var_ms_data, (pd.DataFrame, pd.Series)):
                ms_values = var_ms_data.values
            else:
                ms_values = var_ms_data

            # Remove NaN and zero values
            ms_values = [val for val in ms_values if not pd.isna(val) and val > 0]
            if ms_values:
                all_min_values.extend(ms_values)
                all_max_values.extend(ms_values)

        # Get individual peptide data if needed
        if bio_or_pep != 'no' and ms_average_choice != 'only':
            bp_abs = available_data_variables_dict[var]['bioactive_peptide_abs_df']
            bp_func = available_data_variables_dict[var]['bioactive_peptide_func_df']
            var_name = available_data_variables_dict[var]['label']


            # Filter data based on selection
            try:
                filtered_bp_abs, filtered_bp_func, _ = filter_data_by_selection(
                    bp_abs, bp_func, selected_peptides, selected_functions,
                    bio_or_pep, filter_type, ms_average_choice, var_name,
                    )

                # Extract values from filtered data
                for col in filtered_bp_abs.columns:
                    if col != 'average':
                        y_values = pd.to_numeric(filtered_bp_abs[col], errors='coerce')
                        y_values = y_values[y_values > 0].dropna()
                        if not y_values.empty:
                            all_min_values.extend(y_values.tolist())
                            all_max_values.extend(y_values.tolist())

            except Exception as e:
                # If filtering fails, continue without this data
                continue

    # Override min/max values with manual settings if enabled (same logic as original process_available_data)
    if manual_y_axis:
        min_values = [y_min_manual]
        max_values = [y_max_manual]
    else:
        min_values = all_min_values
        max_values = all_max_values

    # Calculate final y_min and y_max
    if min_values and max_values:
        y_min = min(min_values)
        y_max = max(max_values) * 1.1  # Add 10% padding

        # Handle log transform constraints
        if log_transform:
            y_min = max(y_min, 0.1)
    else:
        # Fallback defaults
        y_min = 0.1 if log_transform else 0
        y_max = 1.0

    return y_min, y_max, min_values, max_values


def round_sig(x, sig=2):
    if x == 0:
        return 0
    exponent = int(np.floor(np.log10(abs(x))))
    factor = 10**(exponent - sig + 1)
    return round(x / factor) * factor


def round_sig_ceil(x, sig=2):
    if x == 0:
        return 0
    exponent = int(np.floor(np.log10(abs(x))))
    factor = 10**(exponent - sig + 1)
    return np.ceil(x / factor) * factor


def round_sig_floor(x, sig=2):
    if x == 0:
        return 0
    exponent = int(np.floor(np.log10(abs(x))))
    factor = 10**(exponent - sig + 1)
    return np.floor(x / factor) * factor


# Function to calculate y-ticks based on the min and max values of datasets
def calculate_y_ticks(min_values, max_values, log_transform):
    """
    Calculate y-ticks with proper handling of zero/negative values
    """
    # Check for empty lists or all zeros
    if not min_values or not max_values:
        return [0, 1, 10]  # Default scale if no data

    # Filter out zeros and negative values, keep valid positives
    valid_mins = [x for x in min_values if x > 0]
    valid_maxs = [x for x in max_values if x > 0]

    # If no valid values after filtering
    if not valid_mins or not valid_maxs:
        return [0, 1, 10]

    try:
        overall_min = np.nanmin(valid_mins)
        overall_max = np.nanmax(valid_maxs)

        # If min or max are zero or negative after nanmin/nanmax


        if log_transform:
            if overall_min <= 0 or overall_max <= 0:
                return [0, 1, 10]
            # Apply log transformation for log scale
            min_power = 10 ** np.floor(np.log10(overall_min))
            max_power = 10 ** np.ceil(np.log10(overall_max))

            # Calculate midpoint in log space
            mid_point = np.sqrt(min_power * max_power)
            mid_point_rounded = 10 ** np.round(np.log10(mid_point))

            return [min_power, mid_point_rounded, max_power]
        else:
            # For linear scale, return min, mid, max rounded to 2 sigfigs
            mid_point = (overall_min + overall_max) / 2
            overall_min_rounded = round_sig_floor(overall_min, 2)
            overall_max_rounded = round_sig(overall_max, 2)
            mid_point_rounded = round_sig_floor(mid_point, 2)
            return [overall_min_rounded, mid_point_rounded, overall_max_rounded]

    except (ValueError, RuntimeWarning):
        return [0, 1, 10]  # Fallback for any calculation errors

def calculate_abundance(protein_sequence, peptide_dataframe, grouping_variable):
    protein_sequence_length = len(protein_sequence)
    data = []
    col_names = []
    Avg_column = f'Avg_{grouping_variable}'

    for idx, row in peptide_dataframe.iterrows():
        try:
            start_val = int(row['start'])
            end_val = int(row['end'])
            start_idx = start_val - 1
            stop_idx = end_val
            abundance_value = row[Avg_column]

            values = [0] * protein_sequence_length
            if abundance_value > 0:
                values[start_idx:stop_idx] = [abundance_value] * (stop_idx - start_idx)
            data.append(values)

            # Build column name in the same loop to guarantee alignment
            uid_suffix = ''
            if 'Unique Peptide ID' in row and not pd.isnull(row['Unique Peptide ID']):
                uid = str(row['Unique Peptide ID']).strip()
                if uid:
                    uid_suffix = f' {uid}'
            col_names.append(f"{start_val}-{end_val}{uid_suffix}")

        except (KeyError, ValueError) as e:
            error_message = f'{type(e).__name__}: {e} - Skipping this row'
            _log_validation(error_message)
            continue

    if not data:
        _log_validation("No valid data to process. Returning empty DataFrame.")
        return pd.DataFrame()

    # Create the initial DataFrame
    abundance_df = pd.DataFrame(data).T
    abundance_df.columns = col_names


    # Initialize count list
    count_list = []

    # Check if abundance_df is empty or has no non-zero values
    if abundance_df.empty or abundance_df.eq(0).all().all():
        # Create all zeros for counts and averages
        count_list = [0] * len(protein_sequence)
        abundance_df['average'] = 0
    else:
        # Calculate counts and averages normally
        count_list = abundance_df.gt(0).sum(axis=1)
        abundance_df['average'] = abundance_df.replace(0, np.nan).mean(axis=1)

    # Assign the counts and amino acids
    abundance_df['count'] = count_list
    abundance_df['AA'] = list(protein_sequence)
    return abundance_df

def calculate_function(protein_sequence, peptide_dataframe, grouping_variable):
    protein_sequence_length = len(protein_sequence)
    data = []
    col_names = []

    for _, row in peptide_dataframe.iterrows():
        start_val = int(row['start'])
        end_val = int(row['end'])
        start_idx = start_val - 1
        stop_idx = end_val
        if stop_idx > protein_sequence_length:
            stop_idx -= 1

        function_value = row['function'] if 'function' in peptide_dataframe.columns else np.nan

        values = [None] * protein_sequence_length
        for i in range(start_idx, stop_idx):
            values[i] = function_value

        data.append(values)

        uid_suffix = ''
        if 'Unique Peptide ID' in row and not pd.isnull(row['Unique Peptide ID']):
            uid = str(row['Unique Peptide ID']).strip()
            if uid:
                uid_suffix = f' {uid}'
        col_names.append(f"{start_val}-{end_val}{uid_suffix}")

    function_df = pd.DataFrame(data).T
    function_df.columns = col_names
    return function_df

def export_heatmap_data_to_dict(protein_id, group_key, group_info, protein_sequence,
                               protein_species, protein_name, protein_df, is_all_null):
    """
    Exports the heatmap data to a dictionary based on filter type.
    """
    grouping_var = group_info['grouping_variable']
    relevant_columns = group_info['abundance_columns']

    # Check if required columns exist, if not create default DataFrame
    required_columns = ['function', 'start', 'end']
    if not all(col in protein_df.columns for col in required_columns):
        filtered_df = pd.DataFrame({
            'start': [0],
            'end': [1],
            'function': ['0']
        })
        filtered_protein_df = filtered_df.copy()
    else:
        filtered_protein_df = protein_df.dropna(subset=['function', 'start', 'end'])
        if 'Unique Peptide ID' in filtered_protein_df.columns:
            filtered_df = filtered_protein_df[['start', 'end', 'function', 'Unique Peptide ID']]
        else:
            filtered_df = filtered_protein_df[['start', 'end', 'function']]

    # Calculate the heatmap data
    func_heatmap_df = calculate_function(protein_sequence, filtered_df, grouping_var)
    heatmap_df = calculate_abundance(protein_sequence, protein_df, grouping_var)
    filtered_heatmap_df = calculate_abundance(protein_sequence, filtered_protein_df, grouping_var)

    # Create the dictionary to store the results
    heatmap_data = {
        'protein_id': protein_id,
        'protein_sequence': protein_sequence,
        'protein_name': protein_name,
        'protein_species': protein_species,
        'func_heatmap_df': func_heatmap_df,
        'heatmap_df': heatmap_df,
        'filtered_heatmap_df': filtered_heatmap_df
    }

    return heatmap_data

def chunk_dataframe(df, chunk_size, exclude_columns=3):
    # Select all rows and all but the last 'exclude_columns' columns
    df_subset = df.iloc[:, :-exclude_columns] if exclude_columns else df

    # Check if df_subset is empty or all zeros
    if df_subset.empty or (df_subset == 0).all().all():
        # Return a single chunk with the default structure
        default_chunk = pd.DataFrame(
            np.zeros((chunk_size, df_subset.shape[1])),
            columns=df_subset.columns
        )
        return [default_chunk]

    # Calculate the number of rows needed to make the last chunk exactly 'chunk_size'
    total_rows = df_subset.shape[0]
    remainder = total_rows % chunk_size

    if remainder != 0:
        # Rows needed to complete the last chunk
        rows_to_add = chunk_size - remainder
        # Create a DataFrame with zero values for the missing rows
        additional_rows = pd.DataFrame(
            np.zeros((rows_to_add, df_subset.shape[1])),
            columns=df_subset.columns
        )
        # Append these rows to df_subset
        df_subset = pd.concat(
            [df_subset, additional_rows],
            ignore_index=True,
            copy=False,
            verify_integrity=True
        )

    # Create chunks of the DataFrame
    max_index = df_subset.index.max() + 1
    return [df_subset.iloc[i:i + chunk_size] for i in range(0, max_index, chunk_size)]

def process_available_data(available_data_variables_dict, filter_type, selected_functions, selected_peptides, bio_or_pep, log_transform, manual_y_axis=False, y_min_manual=None, y_max_manual=None):
    """
    Process data for visualization when update_plot is called
    Returns: dict with data and 'errors' key containing list of error messages
    """
    errors = []
    if not available_data_variables_dict:
        return {'errors': ["No data available for processing"]}

    count_list = []
    min_values = []
    max_values = []
    seq_len_list = []
    chunk_size = 78

    # Process each variable's data for visualization
    for var in available_data_variables_dict:
        if filter_type == 'all-peptides':
            df = available_data_variables_dict[var]['heatmap_df']
        elif filter_type == 'bioactive-only':
            df = available_data_variables_dict[var]['filtered_heatmap_df']
        elif filter_type == 'functional-only':
            if not selected_functions and bio_or_pep == '2':
                errors.append(f'Invalid menu selection or there are no results available to display for {var}. Please select "Bioactive Functions" for "Plot Specific Peptides", with at least one function containing data from the "Specific Options" dropdown menu selected.')
            if not selected_peptides and bio_or_pep == '1':
                errors.append(f'Invalid menu selection or there are no results available to display for {var}. Please select "Peptide Intervals" for "Plot Specific Peptides", with at least one peptide interval containing data from the "Specific Options" dropdown menu selected.')

            # Filter both functional and Abundance data for specific functions
            func_df = available_data_variables_dict[var]['function_heatmap_df']
            if func_df is not None and not func_df.empty:
                # Get list of columns that contain any of the selected functions
                functional_positions = []
                for col in func_df.columns:
                    # Check if any selected function appears in any cell of this column
                    if any(any(func in str(cell) for func in selected_functions) for cell in func_df[col]):
                        functional_positions.append(col)

                # Get Abundance data for these positions
                abs_df = available_data_variables_dict[var]['filtered_heatmap_df']
                if abs_df is not None and not abs_df.empty and functional_positions:
                    # Only keep columns that exist in abs_df
                    valid_columns = [col for col in functional_positions if col in abs_df.columns]
                    if valid_columns:
                        # Get the filtered Abundance data for selected columns
                        selected_abs_df = abs_df[valid_columns]

                        # Create DataFrame with sequence and selected columns
                        df = pd.DataFrame({
                            'AA': abs_df['AA'],
                        })

                        # Add the selected columns
                        df = pd.concat([df, selected_abs_df], axis=1)

                        # Now calculate count and average from all data
                        non_zero_mask = df.drop('AA', axis=1) > 0
                        df['count'] = non_zero_mask.sum(axis=1)
                        df['average'] = df.drop('AA', axis=1).where(non_zero_mask).mean(axis=1)
                    else:
                        df = None
                else:
                    df = None
            else:
                df = None

        # Get counts and MS data
        if df is None or df.empty or 'count' not in df.columns or 'average' not in df.columns:
            # Create default DataFrame with zero values
            protein_length = len(available_data_variables_dict[var]['protein_sequence'])
            df = pd.DataFrame({
                'count': [0] * protein_length,
                'average': [0] * protein_length,
                'AA': list(available_data_variables_dict[var]['protein_sequence'])
            })

        # Get counts and MS data
        peptide_counts = df['count']
        ms_data = df['average']
        count_list.append(peptide_counts)

        # Calculate min/max MS values
        min_ms = ms_data[ms_data > 0].min()
        max_ms = ms_data.max()
        min_values.append(min_ms)
        max_values.append(max_ms)

        # Add computed properties to the variable data
        available_data_variables_dict[var].update({
            'peptide_counts': peptide_counts,
            'ms_data': ms_data,
            'ms_data_list': list(ms_data),
            'AA_list': df['AA'].tolist(),
            'max_peptide_counts': peptide_counts.max(),
            'min_peptide_counts': peptide_counts.min(),
            'max_ms_data': max_ms,
            'min_ms_data': min_ms,

            # Generate chunks
            'amino_acids_chunks': [
                available_data_variables_dict[var]['protein_sequence'][i:i + chunk_size]
                for i in range(0, len(available_data_variables_dict[var]['protein_sequence']), chunk_size)
            ],
            'peptide_counts_chunks': [
                peptide_counts[i:i + chunk_size]
                for i in range(0, len(peptide_counts), chunk_size)
            ],
            'ms_data_chunks': [
                ms_data[i:i + chunk_size]
                for i in range(0, len(ms_data), chunk_size)
            ]
        })

        # Process bioactive peptide data
        columns_to_include = df.columns.difference(['AA', 'count'])
        df_filtered = df[columns_to_include]

        available_data_variables_dict[var].update({
            'bioactive_peptide_abs_df': df_filtered,
            #'bioactive_peptide_chunks': chunk_dataframe(df_filtered, chunk_size),
            #'bioactive_function_chunks': chunk_dataframe(available_data_variables_dict[var]['function_heatmap_df'], chunk_size),
            'bioactive_peptide_func_df': available_data_variables_dict[var]['function_heatmap_df']
        })

        seq_len_list.append(len(available_data_variables_dict[var]['amino_acids_chunks'][0]))

    # Calculate global values
    global axis_number, total_plots, y_ticks
    max_sequence_length = max(seq_len_list)
    axis_number = len(available_data_variables_dict) + 2
    num_sets = len(next(iter(available_data_variables_dict.values()))['amino_acids_chunks'])
    total_plots = num_sets * axis_number
    style_map = assign_line_styles(available_data_variables_dict)

    # Process counts
    if len(set([item for sublist in count_list for item in sublist])) >= 1:
        flat_list = [item for sublist in count_list for item in sublist]
        # Check if there are any non-zero values before filtering
        non_zero_values = [item for item in flat_list if item != 0]
        if non_zero_values:  # If there are non-zero values
            list_of_counts = set(non_zero_values)
            max_count = max(non_zero_values)
            num_unique_count = len(set(non_zero_values))
        else:  # If all values are zero
            list_of_counts = {0}
            max_count = 0
            num_unique_count = 1
    else:
        max_count = 0
        num_unique_count = 0
        list_of_counts = set()
    # Calculate number of colors
    num_colors = 6 if num_unique_count >= 6 else num_unique_count

    # Override min/max values with manual settings if enabled
    if manual_y_axis:
        min_values = [y_min_manual]
        max_values = [y_max_manual]
    # Calculate global values
    if min_values and max_values:
        y_ticks = calculate_y_ticks(min_values, max_values, log_transform)
        y_ticks_str = ', '.join(f'{tick:.2e}' for tick in y_ticks)
        y_ticks_html = f'<b>Max/Min of MS data (y-ticks):</b> {y_ticks_str}'
    else:
        y_ticks = [0.1, 1, 10]  # Default log scale values
        y_ticks_html = '<span style="color:red;">Insufficient data to calculate MS data y-ticks.</span>'
        y_ticks_html += f'<b>Protein Sequence Length:</b> {max_sequence_length}'


    return {
        'list_of_counts': list_of_counts,
        'min_values': min_values,
        'max_values': max_values,
        'seq_len_list': seq_len_list,
        'max_sequence_length': max_sequence_length,
        'y_ticks': y_ticks,
        'max_count': max_count,
        'num_unique_count': num_unique_count,
        'num_colors': num_colors,
        'total_plots': total_plots,
        'style_map': style_map,
        'errors': errors

    }

# Update plot function
def update_plot(available_data_variables_dict, ms_average_choice, bio_or_pep, selected_peptides, selected_functions,
                hm_selected_color, lp_selected_color, avglp_selected_color,
                xaxis_label, yaxis_label, yaxis_position, legend_title_input_1, legend_title_input_2,
                legend_title_input_3, plot_land, plot_port, filter_type, log_transform,
                manual_y_axis, y_min_manual, y_max_manual):
    import matplotlib.pyplot as plt
    all_errors = []

    if not available_data_variables_dict:  # Check if data is available
        all_errors.append('No data is available for plotting.')
        return (None, None, all_errors, [])  # Return tuple with errors

    result = process_available_data(available_data_variables_dict, filter_type, selected_functions,  selected_peptides, bio_or_pep, log_transform, manual_y_axis, y_min_manual, y_max_manual)
    # Initialize fig_port and fig_land to None
    fig_port_return = None
    fig_land_return = None

    # Unpack the dictionary into individual global variables
    import _settings as settings
    if result:
        # Check for processing errors
        if 'errors' in result and result['errors']:
            all_errors.extend(result['errors'])

        # Unpack the dictionary into individual global variables
        global list_of_counts, min_values, max_values, seq_len_list, max_sequence_length
        global max_count, num_unique_count, num_colors, total_plots, style_map, y_ticks

        lineplot_height, scale_factor = port_hm_settings.get(len(available_data_variables_dict), (20, 0.1))
        list_of_counts = result['list_of_counts']
        min_values = result['min_values']
        max_values = result['max_values']
        seq_len_list = result['seq_len_list']
        max_sequence_length = result['max_sequence_length']
        y_ticks = result['y_ticks']
        max_count = result['max_count']
        num_unique_count = result['num_unique_count']
        num_colors = result['num_colors']
        total_plots = result['total_plots']
        style_map = result['style_map']

        yaxis_position_land = yaxis_position_port = 0.0 - 0.01 * yaxis_position
        if log_transform or (y_ticks[1] - y_ticks[0] > 9999):
            yaxis_position_land = -0.01 - 0.01 * yaxis_position
        selected_legend_title = [legend_title_input_1, legend_title_input_2, legend_title_input_3, legend_title[4]]

        # Your plotting code here, using the widget values as inputs

        cmap = plt.get_cmap(hm_selected_color)
        avg_cmap = plt.get_cmap(avglp_selected_color)

        # Comprehensive validation of plotting configuration
        config_errors = []

        # Scenario 1: No averaged data + no specific peptides selected
        if ms_average_choice == 'no' and (not bio_or_pep or bio_or_pep == 'no'):
            config_errors.append('Invalid configuration: "Plot Averaged Data" is set to "No" and "Plot Specific Peptides" is not selected. Please enable at least one data source for plotting.')

        # Scenario 2: Peptide intervals selected but no actual intervals provided
        elif bio_or_pep == '1' and (not selected_peptides or len(selected_peptides) == 0):
            config_errors.append('Invalid configuration: "Plot Specific Peptides" is set to "Peptide Intervals" but no peptide intervals are selected. Please select peptide intervals from the "Specific Options" dropdown or change the plotting configuration.')

        # Scenario 3: Bioactive functions selected but no actual functions provided
        elif bio_or_pep == '2' and (not selected_functions or len(selected_functions) == 0):
            config_errors.append('Invalid configuration: "Plot Specific Peptides" is set to "Bioactive Functions" but no bioactive functions are selected. Please select bioactive functions from the "Specific Options" dropdown or change the plotting configuration.')

        # Scenario 4: Only averaged data but filter is set to selected peptides/functions
        elif ms_average_choice == 'only' and filter_type in ['peptide-only', 'functional-only']:
            if filter_type == 'peptide-only':
                config_errors.append('Invalid configuration: "Plot Averaged Data" is set to "Only" but "Plot Filter" is set to "Selected Peptides Only". When plotting only averaged data, use "All Peptides" or "All Functional Peptides" filter.')
            else:
                config_errors.append('Invalid configuration: "Plot Averaged Data" is set to "Only" but "Plot Filter" is set to "Selected Functions Only". When plotting only averaged data, use "All Peptides" or "All Functional Peptides" filter.')

        # Scenario 5: Additional edge case - no data will be available for plotting
        elif ms_average_choice == 'no' and bio_or_pep != 'no' and filter_type in ['peptide-only', 'functional-only']:
            if bio_or_pep == '1' and filter_type == 'functional-only':
                config_errors.append('Invalid configuration: "Plot Specific Peptides" is set to "Peptide Intervals" but "Plot Filter" is set to "Selected Functions Only". These settings are incompatible. Either change to "Selected Peptides Only" filter or switch to "Bioactive Functions" for specific peptides.')
            elif bio_or_pep == '2' and filter_type == 'peptide-only':
                config_errors.append('Invalid configuration: "Plot Specific Peptides" is set to "Bioactive Functions" but "Plot Filter" is set to "Selected Peptides Only". These settings are incompatible. Either change to "Selected Functions Only" filter or switch to "Peptide Intervals" for specific peptides.')

        # Scenario 6: All Functional Peptides filter with Peptide Intervals selection
        elif bio_or_pep == '1' and filter_type == 'all-functional':
            config_errors.append('Invalid configuration: "Plot Specific Peptides" is set to "Peptide Intervals" but "Plot Filter" is set to "All Functional Peptides". These settings are incompatible. Either change to "All Peptides" filter or switch to "Bioactive Functions" for specific peptides.')

        # Scenario 7: All Peptides filter with Bioactive Functions selection (opposite case)
        #elif bio_or_pep == '2' and filter_type == 'all-peptides':
        #    config_errors.append('Invalid configuration: "Plot Specific Peptides" is set to "Bioactive Functions" but "Plot Filter" is set to "All Peptides". These settings are incompatible. Either change to "All Functional Peptides" filter or switch to "Peptide Intervals" for specific peptides.')

        if config_errors:
            all_errors.extend(config_errors)
            return None, None, all_errors, []

        else:
            """ #                                       Function Call to Generate Plot
            #---------------------------------------------------------------------------------------------------------------------------------------------
            """

            if plot_port and bio_or_pep:
                # Temporarily suppress specific warning
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    if ms_average_choice in ['yes', 'only']:
                        fig_port = visualize_sequence_heatmap_portrait(
                            available_data_variables_dict,
                            0.001,
                            lineplot_height,
                            1,
                            xaxis_label,
                            yaxis_label,
                            selected_legend_title,
                            yaxis_position_port,
                            cmap,
                            avg_cmap,
                            lp_selected_color,
                            avglp_selected_color,
                            selected_functions,
                            ms_average_choice,
                            bio_or_pep,
                            log_transform,
                            y_ticks,
                            78)  # removed chunk_size= to make it a positional argument
                    else:
                        all_errors.append('No was selected earlier regarding the plotting of averaged Abundances, preventing the plotting of the averaged plot.')
                    if max_count <= 1:
                        # Check if this is due to missing function data
                        if bio_or_pep == '2' and selected_functions:
                            missing_functions = []
                            for func in selected_functions:
                                func_found = False
                                for var in available_data_variables_dict:
                                    bp_func = available_data_variables_dict[var]['bioactive_peptide_func_df']
                                    # Check if this function exists in any data
                                    for col in bp_func.columns:
                                        func_values = bp_func[col].dropna()
                                        if not func_values.empty:
                                            for val in func_values:
                                                sub_vals = [s.strip() for s in str(val).split(';')]
                                                if any(func.lower().replace(" ", "") == sub_val.lower().replace(" ", "") for sub_val in sub_vals):
                                                    func_found = True
                                                    break
                                        if func_found:
                                            break
                                    if func_found:
                                        break
                                if not func_found:
                                    missing_functions.append(func)

                            if missing_functions:
                                if len(missing_functions) == 1:
                                    all_errors.append(f'No data available for the selected function "{missing_functions[0]}". Please select a different function or check your data.')
                                else:
                                    all_errors.append(f'No data available for the selected functions: {", ".join(missing_functions)}. Please select different functions or check your data.')
                            else:
                                all_errors.append('You have too few peptides for proper heatmapping.')
                        # Check if this is due to missing peptide data
                        elif bio_or_pep == '1' and selected_peptides:
                            missing_peptides = []
                            for peptide in selected_peptides:
                                peptide_found = False
                                for var in available_data_variables_dict:
                                    bp_abs = available_data_variables_dict[var]['bioactive_peptide_abs_df']
                                    # Check if this peptide interval exists as a column
                                    if peptide in bp_abs.columns:
                                        # Check if the column has any non-zero, non-NaN data
                                        peptide_data = pd.to_numeric(bp_abs[peptide], errors='coerce')
                                        if not peptide_data.dropna().empty and (peptide_data > 0).any():
                                            peptide_found = True
                                            break
                                if not peptide_found:
                                    missing_peptides.append(peptide)

                            if missing_peptides:
                                if len(missing_peptides) == 1:
                                    all_errors.append(f'No data available for the selected peptide interval "{missing_peptides[0]}". Please select a different peptide interval or check your data.')
                                else:
                                    all_errors.append(f'No data available for the selected peptide intervals: {", ".join(missing_peptides)}. Please select different peptide intervals or check your data.')
                            else:
                                all_errors.append('You have too few peptides for proper heatmapping.')
                        else:
                            all_errors.append('You have too few peptides for proper heatmapping.')
            else:
                fig_port = None
            """_____________________________________________________EXECUTING CODE TO PLOT W/ UPDATES_________________________________________________________________"""

            # Plotting code
            if plot_land:
                amino_acid_height = 0.25 + 0.1 * (
                    len(available_data_variables_dict) // 4 if len(available_data_variables_dict) >= 8 else 0)
                indices_height = amino_acid_height + 0.08
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    fig_land, land_errors = visualize_sequence_heatmap_lanscape(
                        available_data_variables_dict,
                        amino_acid_height,
                        7.5,
                        indices_height,
                        xaxis_label,
                        yaxis_label,
                        selected_legend_title,
                        yaxis_position_land,
                        cmap,
                        avg_cmap,
                        lp_selected_color,
                        avglp_selected_color,
                        selected_peptides,
                        selected_functions,
                        ms_average_choice,
                        bio_or_pep,
                        log_transform,
                        y_ticks,
                        filter_type,
                        manual_y_axis,
                        y_min_manual,
                        y_max_manual)

                # Collect landscape plotting errors
                all_errors.extend(land_errors)

                if max_count <= 1:
                    # Check if this is due to missing function data
                    if bio_or_pep == '2' and selected_functions:
                        missing_functions = []
                        for func in selected_functions:
                            func_found = False
                            for var in available_data_variables_dict:
                                bp_func = available_data_variables_dict[var]['bioactive_peptide_func_df']
                                # Check if this function exists in any data
                                for col in bp_func.columns:
                                    func_values = bp_func[col].dropna()
                                    if not func_values.empty:
                                        for val in func_values:
                                            sub_vals = [s.strip() for s in str(val).split(';')]
                                            if any(func.lower().replace(" ", "") == sub_val.lower().replace(" ", "") for sub_val in sub_vals):
                                                func_found = True
                                                break
                                    if func_found:
                                        break
                                if func_found:
                                    break
                            if not func_found:
                                missing_functions.append(func)

                        if missing_functions:
                            if len(missing_functions) == 1:
                                all_errors.append(f'No data available for the selected function "{missing_functions[0]}". Please select a different function or check your data.')
                            else:
                                all_errors.append(f'No data available for the selected functions: {", ".join(missing_functions)}. Please select different functions or check your data.')
                        else:
                            all_errors.append('You have too few peptides for proper heatmapping.')
                    # Check if this is due to missing peptide data
                    elif bio_or_pep == '1' and selected_peptides:
                        missing_peptides = []
                        for peptide in selected_peptides:
                            peptide_found = False
                            for var in available_data_variables_dict:
                                bp_abs = available_data_variables_dict[var]['bioactive_peptide_abs_df']
                                # Check if this peptide interval exists as a column
                                if peptide in bp_abs.columns:
                                    # Check if the column has any non-zero, non-NaN data
                                    peptide_data = pd.to_numeric(bp_abs[peptide], errors='coerce')
                                    if not peptide_data.dropna().empty and (peptide_data > 0).any():
                                        peptide_found = True
                                        break
                            if not peptide_found:
                                missing_peptides.append(peptide)

                        if missing_peptides:
                            if len(missing_peptides) == 1:
                                all_errors.append(f'No data available for the selected peptide interval "{missing_peptides[0]}". Please select a different peptide interval or check your data.')
                            else:
                                all_errors.append(f'No data available for the selected peptide intervals: {", ".join(missing_peptides)}. Please select different peptide intervals or check your data.')
                        else:
                            all_errors.append('You have too few peptides for proper heatmapping.')
                    else:
                        all_errors.append('You have too few peptides for proper heatmapping.')
            else:
                fig_land = None
        # Fixed return statement logic to check if the variables exist and have valid axes
        if plot_port:
            if bio_or_pep != 'no':
                all_errors.append('The portrait plot only supports plotting averaged Abundance of peptides which is not formatted to be combined with specified peptide intervals or functions.')
                fig_port_return = None
            else:
                # Check if fig_port is defined and has axes
                if fig_port is not None and hasattr(fig_port, 'axes') and len(fig_port.axes) > 0:
                    fig_port_return = fig_port

        if plot_land:
            # Check if fig_land is defined and has axes
            if fig_land is not None and hasattr(fig_land, 'axes') and len(fig_land.axes) > 0:
                fig_land_return = fig_land

        if not plot_port and not plot_land:
            all_errors.append("One or both of the create plot checkbox must be selected to generate a plot.")

        # Collect missing data notifications for user feedback
        missing_data_notifications = collect_missing_data_notifications(
            available_data_variables_dict, selected_peptides, selected_functions, bio_or_pep
        )

        return fig_port_return, fig_land_return, all_errors, missing_data_notifications  # Return the figures with errors and notifications
    else:
        all_errors.append('Reselect "Variable Options", no data is available for plotting.')
        return None, None, all_errors, []  # Return None values with errors if no result

"""_________________________________________Data Visualization Functions_________________________________"""
# Function to plot rows of amino acids with backgrounds colored
def plot_row_color(ax, amino_acids, colors):
    import matplotlib.colors as mcolors
    ax.axis('off')
    ax.set_xlim(0, max_sequence_length)
    ax.set_xlabel('')
    for j, (aa, color) in enumerate(zip(amino_acids, colors)):
        ax.text(j + 0.5, 0.5, aa, color='black', ha='center', va='center', fontsize=14,
                backgroundcolor=mcolors.rgb2hex(color))

# Assigns line type for landscape plot if plotting individual peptides
def assign_line_styles(data_variables):
    # Define a set of line styles you find visually distinct
    line_styles = cycle(['-', '--', ':', '-.'])
    #line_styles = cycle(['-'])

    # Extract unique labels from your data variables
    unique_labels = set(data['label'] for data in data_variables.values())

    # Map each unique label to a line style
    style_map = {label: next(line_styles) for label in unique_labels}

    # Map each unique label to a line style
    #style_map = {'Gastric IVT': '--',
    #             'Intestinal IVT': ':',
    #             'J1H': '-', 'J2H': '-', 'J3H': '-', 'J4H': '-',}
    return style_map

# Function to plot rows of amino acids with NO backgrounds colored
def plot_row(ax, amino_acids):
    ax.axis('off')
    ax.set_xlim(0, max_sequence_length)
    ax.set_xlabel('')
    for j, (aa) in enumerate(amino_acids):
        ax.text(j + 0.5, 0.5, aa, color='black', ha='center', va='center', fontsize=8)  # backgroundcolor='white')

def sci_notation(x, pos):
    if x == 0:
        return "0"
    exponent = int(np.floor(np.log10(abs(x))))
    coeff = x / 10**exponent
    return r"${:.1f}\times10^{{{}}}$".format(coeff, exponent)

def plot_average_ms_data(ax, ms_data, label, var_index, y_ticks, i, chunk_size, avg_cmap, log_transform, line_style, sci_threshold=9999):
    import matplotlib.ticker as mticker
    start_limit = i * chunk_size
    end_limit = (i + 1) * chunk_size - 1
    ax.set_xlim(start_limit, end_limit)

    if isinstance(ms_data, (pd.DataFrame, pd.Series)):
        x_values = ms_data.index.tolist()
        y_values = ms_data.values.tolist() if hasattr(ms_data.values, 'tolist') else list(ms_data.values)
    else:
        x_values = list(range(len(ms_data)))
        y_values = list(ms_data) if not isinstance(ms_data, list) else ms_data

    num_colors = avg_cmap.N
    color = avg_cmap(var_index % num_colors)

    try:
        line, = ax.plot(x_values, y_values, label=label, color=color, linestyle=line_style)
    except Exception as e:
        # If plotting fails, create a dummy line and log the error
        print(f"Error in plot_average_ms_data for {label}: {str(e)}")
        print(f"x_values type: {type(x_values)}, length: {len(x_values) if hasattr(x_values, '__len__') else 'N/A'}")
        print(f"y_values type: {type(y_values)}, length: {len(y_values) if hasattr(y_values, '__len__') else 'N/A'}")
        # Create a dummy line to prevent further errors
        line, = ax.plot([], [], label=label, color=color, linestyle=line_style)

    if log_transform:
        ax.set_yscale('log')
        # Force matplotlib to use only our custom y_ticks for log scale
        if y_ticks:
            ax.yaxis.set_major_locator(mticker.FixedLocator(y_ticks))
            ax.yaxis.set_minor_locator(mticker.NullLocator())  # Remove minor ticks
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(sci_notation))
    else:
        ax.set_yscale('linear')
        if y_ticks:
            y_range = max(y_ticks) - min(y_ticks)
            if y_range >= sci_threshold:
                formatter = mticker.FuncFormatter(sci_notation)
            else:
                formatter = mticker.StrMethodFormatter("{x:.2f}")
            ax.yaxis.set_major_formatter(formatter)

    # Set y-ticks and y-axis limits (restored original formatting)
    if y_ticks:
        ax.set_yticks(y_ticks)
        ax.set_ylim(min(y_ticks), max(y_ticks))

    #ax.tick_params(axis='y', labelsize=12)
    ax.yaxis.tick_left()
    ax.set_xticks([])
    ax.set_xticklabels([])

    # Return y_values for centralized y-axis limit calculation
    return line, label, var_index, y_values

# Function to extract non-zero, non-NaN values
def extract_non_zero_non_nan_values(df):
    unique_functions = set()
    # Iterate over each value in the DataFrame
    for value in df.stack().values:  # df.stack() stacks the DataFrame into a Series
        if value != 0 and not pd.isna(value):  # Check if value is non-zero and not NaN
            if isinstance(value, str):
                # If the value is a string, it could contain multiple delimited entries
                entries = value.split('; ')
                unique_functions.update(entries)
            else:
                unique_functions.add(value)
    return unique_functions

    # This function is used in plotting to filter the data to only plot selected peptides or bioactive peptides, independent of averaged data


def safe_str(value):
    """Safely convert any value to string, handling None, NaN, and Series objects"""
    try:
        if value is None:
            return ""

        # For Series objects, just return empty string to avoid truth value errors
        if hasattr(value, 'iloc'):
            return ""

        # Convert to string
        return str(value)
    except:
        return ""


def filter_data_by_selection(bp_abs, bp_func, selected_peptides, selected_functions, bio_or_pep, filter_type, ms_average_choice, var_name):
    """
    Final simplified version that uses a completely different approach to avoid Series truth value issues.
    Returns: (filtered_bp_abs, filtered_bp_func, errors)
    """
    errors = []

    # ---------- Handle peptide intervals selection (bio_or_pep = '1') ----------
    if bio_or_pep == '1' and selected_peptides:
        # Find our selected peptide columns that exist in the DataFrame
        if bp_abs is None or not isinstance(bp_abs, pd.DataFrame) or bp_abs.empty:
            errors.append(f"Abundance DataFrame is empty for variable: {var_name}")
            return pd.DataFrame(), pd.DataFrame(), errors

        peptide_columns = [col for col in selected_peptides if col in bp_abs.columns]
        non_matching_peptides = [col for col in selected_peptides if col not in bp_abs.columns]

        if peptide_columns:
            # Add metadata columns if they exist
            meta_columns = ['AA', 'count', 'average']
            keep_columns = [col for col in meta_columns if col in bp_abs.columns]
            all_columns = keep_columns + peptide_columns

            # Create new DataFrames with only the columns we want
            filtered_bp_abs = bp_abs[all_columns].copy()
            filtered_bp_func = pd.DataFrame()

            return filtered_bp_abs, filtered_bp_func, errors
        else:
            # No selected peptides exist in this protein/variable combination — silently skip.
            # This is expected when plotting multiple proteins and a peptide belongs to only one.
            return pd.DataFrame(), pd.DataFrame(), errors

    # ---------- Handle bioactive functions selection (bio_or_pep = '2') ----------
    elif bio_or_pep == '2' and selected_functions:
        if bp_func is None or not isinstance(bp_func, pd.DataFrame) or bp_func.empty:
            errors.append(f"Function DataFrame is empty for variable: {var_name}")
            return pd.DataFrame(), pd.DataFrame(), errors
        try:
            # Simple string-based approach that completely avoids pandas operations
            # This manually scans the DataFrame for columns containing the selected functions
            columns_with_functions = []
            functions_found = set()

            # Get list of column names first
            all_columns = list(bp_func.columns)

            # Iterate through the function DataFrame columns
            for col_name in all_columns:
                # Process a column at a time - get non-NA function values
                func_values = bp_func[col_name].dropna()

                if func_values.empty:
                    continue

                # Track matched functions for this column
                matched_functions = set()

                # Check for matches with selected functions, splitting on ';' like in process_chunk_data
                for val in func_values:
                    # Convert to string (safely)
                    try:
                        value_str = str(val)
                    except:
                        continue

                    # Skip empty strings or 'nan'
                    if not value_str or value_str == 'nan':
                        continue

                    # Split the value on ';' and strip whitespace
                    sub_vals = [s.strip() for s in value_str.split(';')]

                    for sub_val in sub_vals:
                        # Only match if sub_val matches exactly one of the selected_functions (case-insensitive, ignoring whitespace)
                        for func in selected_functions:
                            if func.lower().replace(" ", "") == sub_val.lower().replace(" ", ""):
                                matched_functions.add(func)

                # If we found any matches in this column, add it to the list
                if matched_functions:
                    columns_with_functions.append(col_name)

                # Add matched functions to the global set
                functions_found.update(matched_functions)

            # Remove any duplicates
            columns_with_functions = list(set(columns_with_functions))

            # Identify non-matching functions
            non_matching_functions = [func for func in selected_functions if func not in functions_found]

            if columns_with_functions:
                # Only include columns that are in both DataFrames
                valid_cols_abs = [col for col in columns_with_functions if col in bp_abs.columns]
                valid_cols_func = [col for col in columns_with_functions if col in bp_func.columns]

                # Create filtered DataFrames
                if valid_cols_abs:
                    filtered_bp_abs = bp_abs[valid_cols_abs].copy()
                else:
                    filtered_bp_abs = pd.DataFrame()

                if valid_cols_func:
                    filtered_bp_func = bp_func[valid_cols_func].copy()
                else:
                    filtered_bp_func = pd.DataFrame()

                # Add warning for non-matching functions if any
                if non_matching_functions:
                    errors.append(f'Some selected functions not found in data for variable: {var_name}. Missing: {non_matching_functions}')

                return filtered_bp_abs, filtered_bp_func, errors
            else:
                errors.append(f'No columns found containing any of the selected functions for variable: {var_name}. Non-matching functions: {non_matching_functions}')
                return pd.DataFrame(), pd.DataFrame(), errors

        except Exception as e:
            errors.append(f"Error in function filtering for variable: {var_name}: {str(e)}")
            return pd.DataFrame(), pd.DataFrame(), errors

    else:
        return bp_abs, bp_func, errors

def process_chunk_data(ax2, chunk_abs, chunk_func, chunk_size, i, y_ticks, handles, labels,
                      sample_list, var_name_list, line_style, var_name, var_ms_data,
                      selected_peptides, selected_functions, lp_selected_color, ms_average_choice, log_transform, bio_or_pep):
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    footnote_list = []
    errors = []
    min_values = []
    max_values = []

    # Track peptides already processed to avoid duplicates
    processed_peptides = {}

    start_limit = i * chunk_size
    end_limit = (i + 1) * chunk_size - 1
    ax2.set_xlim(start_limit, end_limit)

    # Set up colormap
    common_columns = []
    colormap = plt.get_cmap(lp_selected_color)

    # Create a dictionary to map functions to colors
    if bio_or_pep == '1':
        num_colors = max(len(selected_peptides), 1)
        items_to_color = selected_peptides
    elif bio_or_pep == '2':
        num_colors = max(len(selected_functions), 1)
        items_to_color = selected_functions
    else:
        num_colors = 1
        items_to_color = []

    # Generate evenly spaced colors
    colors = colormap(np.linspace(0, 1, num_colors))

    # Create a dictionary mapping each function to a specific color
    function_colors = {item: colors[i % len(colors)] for i, item in enumerate(items_to_color)}
    function_colors['Multiple'] = 'black'  # Keep 'Multiple' as black

    # Track which functions we've already plotted
    plotted_functions = set()

    # Process each column in the abundance data
    columns_processed = 0

    for col in chunk_abs.columns:
        if col != 'average':
            try:
                # Force y_values to be numeric and drop NaN/zeros
                y_values = pd.to_numeric(chunk_abs[col], errors='coerce')
                y_values = y_values[y_values > 0]

                if not y_values.empty:
                    columns_processed += 1
                    # Ensure x_values and y_values are proper arrays for matplotlib
                    x_values = list(y_values.index)
                    y_values_list = list(y_values.values)

                    # Additional validation
                    if len(x_values) != len(y_values_list):
                        errors.append(f"Mismatch in data lengths for column {col}: x_values={len(x_values)}, y_values_list={len(y_values_list)}")
                        continue

                    if len(x_values) == 0:
                        errors.append(f"Empty data for column {col}")
                        continue

                    # Get a default label
                    label_value = col

                    # Get function label if available
                    #print(f"[DEBUG] bio_or_pep: {bio_or_pep}")
                    #print(f"[DEBUG] col: {col}")
                    #print(f"[DEBUG] chunk_func.columns: {chunk_func.columns}")
                    #print(f"[DEBUG] selected_functions: {selected_functions}")

                    if bio_or_pep == '2' and col in chunk_func.columns:
                        # Get non-NA function values
                        func_values = chunk_func[col].dropna()
                        if not func_values.empty:
                            # Check for matches with selected functions, splitting on ';'
                            #print(f"[DEBUG] selected_functions: {selected_functions}")
                            found_functions = set()
                            for val in func_values:
                                # Split the value on ';' and strip whitespace
                                sub_vals = [s.strip() for s in str(val).split(';')]
                                for sub_val in sub_vals:
                                    # Only match if sub_val matches exactly one of the selected_functions (case-insensitive, ignoring whitespace)
                                    for func in selected_functions:
                                        if func.lower().replace(" ", "") == sub_val.lower().replace(" ", ""):
                                            found_functions.add(func)
                            if found_functions:
                                if len(found_functions) > 1:
                                    label_value = 'Multiple'
                                    # Check if this peptide was already processed to avoid duplicates
                                    if col not in processed_peptides:
                                        processed_peptides[col] = set()

                                    # Add functions to the existing set for this peptide
                                    processed_peptides[col].update(found_functions)
                                else:
                                    label_value = list(found_functions)[0]
                            else:
                                break
                            #print(f"[DEBUG] label_value: {label_value}")
                            #print(f"[DEBUG] found_functions: {found_functions}")
                        elif bio_or_pep == '1' and col in selected_peptides:
                            label_value = col


                    # Get appropriate color
                    if label_value in function_colors:
                        color = function_colors[label_value]
                    else:
                        color = 'grey'

                    # Use solid lines for better visibility
                    current_line_style = '-'

                    # Plot with increased line width for visibility
                    try:
                        lines = ax2.plot(x_values, y_values_list,
                                    label=label_value,
                                    linestyle=line_style,
                                    color=color)
                    except Exception as e:
                        error_msg = f"Error plotting line for column {col} in variable {var_name}: {str(e)}"
                        error_msg += f" | x_values type: {type(x_values)}, length: {len(x_values) if hasattr(x_values, '__len__') else 'N/A'}"
                        error_msg += f" | y_values_list type: {type(y_values_list)}, length: {len(y_values_list) if hasattr(y_values_list, '__len__') else 'N/A'}"
                        errors.append(error_msg)
                        continue

                    line = lines[0]

                    # Only add to legend if we haven't seen this function before
                    if label_value not in plotted_functions or bio_or_pep == '1':
                        handles.append(line)
                        labels.append(label_value)
                        sample_list.append(current_line_style)
                        var_name_list.append(var_name)
                        plotted_functions.add(label_value)
                        # Update min and max values logic to ignore NaNs and handle empty y_values
                        if len(y_values_list) > 0:
                            y_min_val = np.nanmin(y_values_list)
                            y_max_val = np.nanmax(y_values_list)
                            if not np.isnan(y_min_val):
                                min_values.append(y_min_val)
                            if not np.isnan(y_max_val):
                                max_values.append(y_max_val)

                #else:

            except Exception as e:
                errors.append(f"Error plotting line for column {col} in variable {var_name}: {str(e)}")
                continue

    #print(f"Debug: Total columns processed with data: {columns_processed}")

    # Set up axis properties with original y-axis formatting restored
    if log_transform:
        ax2.set_yscale('log')
        # Force matplotlib to use only our custom y_ticks for log scale
        if y_ticks:
            ax2.yaxis.set_major_locator(mticker.FixedLocator(y_ticks))
            ax2.yaxis.set_minor_locator(mticker.NullLocator())  # Remove minor ticks
            ax2.yaxis.set_major_formatter(mticker.FuncFormatter(sci_notation))
    else:
        ax2.set_yscale('linear')
        formatter = mticker.FuncFormatter(sci_notation)
        ax2.yaxis.set_major_formatter(formatter)

    # Force y-axis limits to ensure data is visible (restored original logic)
    if y_ticks:
        ax2.set_yticks(y_ticks)
        ax2.set_ylim(min(y_ticks), max(y_ticks))

    ax2.tick_params(axis='y', labelsize=16)
    ax2.yaxis.tick_left()
    ax2.set_xticks([])
    ax2.set_xticklabels([])

    # Convert processed_peptides to the format expected by footnote generation
    for peptide_col, functions in processed_peptides.items():
        if len(functions) > 1:  # Only include peptides with multiple functions
            peptide_info = {
                'peptide_column': peptide_col,
                'functions': sorted(list(functions))
            }
            footnote_list.append(peptide_info)

    return footnote_list, errors, min_values, max_values

def get_grouped_colors(counts, max_count, num_groups, plot_zero, cmap):
    from matplotlib.colors import Normalize
    # Initialize colors list with None to maintain length
    colors = [None] * len(counts)

    # Set the start point based on the user's input
    start_point = 0 if plot_zero == 'yes' else 1

    # Group counts into fewer categories if necessary, excluding zeros
    group_bounds = np.linspace(start_point, max_count, num_groups + 1)
    group_labels = np.digitize(counts, bins=group_bounds, right=True)  # Find group labels for counts
    ##print("DEBUG: group_labels", group_labels)
    norm = Normalize(vmin=start_point, vmax=num_groups)  # Normalize based on the number of groups

    # Map each count to a color
    #for i, count in enumerate(counts):
    for i, (count, label) in enumerate(zip(counts, group_labels)):
        if plot_zero == 'no' and count == 0:
            colors[i] = 'white'
        else:
            # Find which group the count belongs to
            group_idx = np.digitize(count, group_bounds) - 1

            if max_count > 20:
                # For large ranges, use continuous color mapping
                colors[i] = cmap(count / max_count)
            else:
                # For smaller ranges, use discrete color groups
                #colors[i] = cmap(norm(group_bounds[min(group_idx, len(group_bounds)-1)]))
                colors[i] = cmap(norm(label))

    #print("DEBUG: label",label)
    return colors

# Function to create legend for heatmap
def create_heatmap_legend_handles(cmap, num_colors, max_count, plot_zero):
    """
    Create color-coded legend handles for the heatmap with proper handling of zero values
    and error cases
    """
    import matplotlib.patches as patches
    from matplotlib.colors import Normalize
    try:
        # Handle case where all values are zero
        if max_count == 0:
           norm = Normalize(vmin=0, vmax=1)
           color = cmap(norm(0))
           return [patches.Patch(color=color, label='0')], ['0']

        # Set the start point based on plot_zero
        start_point = 0 if plot_zero == 'yes' else 1

        # Create group boundaries to match get_grouped_colors
        count_ranges = np.linspace(start_point, max_count, num_colors + 1)

        # Determine interval type based on count vs intervals
        if max_count > num_colors:
           plt_interval = max_count
        else:
           plt_interval = num_colors

        legend_handles = []
        heatmap_labels = []
        norm = Normalize(vmin=start_point, vmax=max_count)

        # For small ranges, start from index 1 to skip the duplicate 1
        start_idx = 1 if plt_interval <= 6 else 0
        for i in range(start_idx, len(count_ranges)):
            color = cmap(norm(count_ranges[i]))
            if plt_interval <= 6 and plot_zero == 'no':
                label = f'{int(count_ranges[i])}'
            elif plt_interval <= 6 and plot_zero == 'yes':
                label = f'{int(count_ranges[i])}'
            elif i + 1 >= len(count_ranges):
                label = f'{int(count_ranges[i])} - {max(count_ranges)}'
                break
            else:
                # Create label showing range
                start_val = int(count_ranges[i])
                end_val = int(count_ranges[i + 1])
                label = f'{start_val} - {end_val}'

            #if i = len(count_ranges):
            #    color = cmap(norm(count_ranges[i]))

            #print("DEBUG: i:",i,"label:",label)
            #legend_handles.append(patches.Patch(color=color, label=label))
            legend_handles.append(patches.Patch(color=color, label=label))
            heatmap_labels.append(label)
        return legend_handles, heatmap_labels

    except Exception as e:
       # Fallback for error cases
       color = cmap(0)
       handle = patches.Patch(color=color, label='0')
       return [handle], ['0']

def create_custom_legends(fig, labels, handles, var_name_list, legend_titles, heatmap_legend_handles,
                          heatmap_legend_labels, ms_average_choice, bio_or_pep, plot_type):
    import matplotlib.pyplot as plt
    import matplotlib.lines as mlines
    import matplotlib.patches as patches

    handles_dict = {}
    sample_handles_dict = {}

    # Modify label if needed and populate dictionaries
    for label, handle, sample_name in zip(labels, handles, var_name_list):
        handles_dict[label] = handle  # Store or update the handle with modified label

        # Store handles for sample types (assuming sample_name correctly aligns with the handles)
        if sample_name not in sample_handles_dict:
            sample_handles_dict[sample_name] = handle

    # Create new handles for the legend with modified properties
    new_handles_func = [copy.copy(handle) for handle in handles_dict.values()]
    new_labels_func = [label for label in handles_dict.keys()]

    # Initial empty lists for combined handles and labels
    combined_handles = []
    combined_labels = []
    # Filter for "Averaged" labels
    averaged_handles = []
    averaged_labels = []
    other_handles = []
    other_labels = []

    for handle, label in zip(new_handles_func, new_labels_func):
        if "Averaged" in label:
            clean_label = label.replace("Averaged ", "")  # Remove 'Averaged ' from the label
            averaged_handles.append(handle)
            averaged_labels.append(clean_label)  # Append the cleaned label

        else:
            handle.set_linestyle('-')  # Set line style to solid
            other_handles.append(handle)
            other_labels.append(label)

    new_handles_samples = []
    if not averaged_handles:
        for handle in sample_handles_dict.values():
            new_handle = copy.copy(handle)
            new_handle.set_color('black')  # Set color to black for sample type handles
            new_handles_samples.append(new_handle)

    # Dummy handles for subtitles
    line_type = mlines.Line2D([], [], color='none', label='Line Type')
    average_color = mlines.Line2D([], [], color='none', label='Average Abundance')
    line_color = mlines.Line2D([], [], color='none', label='Line Color')
    pep_count_placeholder = mlines.Line2D([], [], color='none', label='Line Type')


    #legend_title = [0-'Sample Type:',1-'Peptide Counts:','2-'Bioactivity Function:' or '2-'Peptide Interval:', '3-'Average Abundance:']

    line_type_title = legend_titles[0]
    avgline_color_title = legend_titles[2] if bio_or_pep == 'no' else legend_titles[3]
    color_title = legend_titles[2]

    if ms_average_choice == 'yes':
        if bio_or_pep != 'no':
            combined_handles = [line_color] + other_handles + [average_color] + averaged_handles
            combined_labels = [color_title] + other_labels + [avgline_color_title] + averaged_labels

        else: #if bio_or_pep == 'no':
            combined_handles = [average_color] + averaged_handles
            combined_labels = [avgline_color_title] + averaged_labels

    if ms_average_choice == 'only':
        combined_handles = [average_color] + averaged_handles
        combined_labels = [avgline_color_title] + averaged_labels

    if ms_average_choice == 'no' and bio_or_pep != 'no':
        combined_handles = [line_color] + other_handles + [line_type] + new_handles_samples
        combined_labels = [color_title] + other_labels + [line_type_title] + [key for key in sample_handles_dict.keys()]

    legend_peptide_count = None
    if plot_type == "land":
        # Create the peptide count legend separately
        if plot_heatmap == 'yes':
            legend_peptide_count = fig.legend(handles=heatmap_legend_handles, loc='center',
                                              fontsize=14,
                                              title=legend_titles[1],
                                              title_fontsize=14,
                                              bbox_to_anchor=(0.5, -0.1),
                                              ncol=len(heatmap_legend_handles))

        # Create the combined legend (for other handles/labels)
        combined_legend = fig.legend(handles=combined_handles, labels=combined_labels,
                                     loc='upper left', bbox_to_anchor=(0.99, 0.975),
                                     fontsize=14, handlelength=2)
        plt.tight_layout()
        fig.subplots_adjust(right=0.9)  # Make room for side legend

    # Create a single combined legend
    elif plot_type == "port":

        # Combine heatmap handles with other handles for a single legend
        combined_handles = [line_color] + other_handles + [pep_count_placeholder] + heatmap_legend_handles
        combined_labels = [avgline_color_title] + other_labels + [legend_titles[1]] + heatmap_legend_labels

        # Create a single combined legend with just the combined handles (no need for additional labels)
        combined_legend = fig.legend(handles=combined_handles,
                                     labels=combined_labels,
                                     loc='upper left',
                                     bbox_to_anchor=(0.9025, 0.875),
                                     fontsize=14)

    return combined_legend, legend_peptide_count

def collect_missing_data_notifications(available_data_variables_dict, selected_peptides, selected_functions, bio_or_pep):
    """
    Collect notifications about missing data for specific variables during plotting.
    Returns a list of notification messages for user display.
    """
    notifications = []

    if bio_or_pep == '1' and selected_peptides:  # Peptide intervals selected
        # Track which peptides are missing from which variables
        missing_by_variable = {}

        for var_name, var_data in available_data_variables_dict.items():
            missing_peptides = []
            if 'heatmap_df' in var_data:
                available_columns = var_data['heatmap_df'].columns.tolist()
                for peptide in selected_peptides:
                    if peptide not in available_columns:
                        missing_peptides.append(peptide)

            if missing_peptides:
                missing_by_variable[var_name] = missing_peptides

        # Create notification messages
        for var_name, missing_peptides in missing_by_variable.items():
            if len(missing_peptides) == 1:
                notifications.append(f"⚠️ Variable '{var_name}': Peptide interval '{missing_peptides[0]}' is not available in this dataset.")
            else:
                peptide_list = "', '".join(missing_peptides)
                notifications.append(f"⚠️ Variable '{var_name}': Peptide intervals '{peptide_list}' are not available in this dataset.")

    elif bio_or_pep == '2' and selected_functions:  # Bioactive functions selected
        # Track which functions are missing from which variables
        missing_by_variable = {}

        for var_name, var_data in available_data_variables_dict.items():
            missing_functions = []
            if 'function_heatmap_df' in var_data:
                func_df = var_data['function_heatmap_df']
                if func_df is not None and not func_df.empty:
                    # Extract all functions present in this variable
                    present_functions = set()
                    for col in func_df.columns:
                        for cell in func_df[col]:
                            if pd.notna(cell) and str(cell) != '0':
                                cell_str = str(cell)
                                if ';' in cell_str:
                                    present_functions.update(cell_str.split(';'))
                                else:
                                    present_functions.add(cell_str)

                    # Check which selected functions are missing
                    for function in selected_functions:
                        if function not in present_functions:
                            missing_functions.append(function)
            else:
                # If no function data at all, all selected functions are missing
                missing_functions = selected_functions.copy()

            if missing_functions:
                missing_by_variable[var_name] = missing_functions

        # Create notification messages
        for var_name, missing_functions in missing_by_variable.items():
            if len(missing_functions) == 1:
                notifications.append(f"⚠️ Variable '{var_name}': Bioactive function '{missing_functions[0]}' is not available in this dataset.")
            else:
                function_list = "', '".join(missing_functions)
                notifications.append(f"⚠️ Variable '{var_name}': Bioactive functions '{function_list}' are not available in this dataset.")

    return notifications


"""_________________________________________Landscape Plot________________________________________"""
# Function to plot rows of amino acids with backgrounds colored (landscape version)
def plot_row_color_landscape(ax, amino_acids, colors):
    ax.axis('off')
    ax.set_xlim(0, len(amino_acids))
    ax.set_xlabel('')
    # Height and width for each cell
    cell_width = 1  # Each amino acid is spaced evenly by 1 unit on the x-axis
    cell_height = 1  # Set height of the row

    for j, (aa, color) in enumerate(zip(amino_acids, colors)):
        # Create a rectangle (cell) with the background color
        import matplotlib.patches as patches
        import matplotlib.colors as mcolors
        rect = patches.Rectangle((j, 0), cell_width, cell_height, color=mcolors.rgb2hex(color))
        ax.add_patch(rect)  # Add the colored rectangle to the plot


# Function to plot rows of amino acids with backgrounds colored (landscape version)
def plot_row_landscape(ax, amino_acids):
    seq_len = len(amino_acids)
    ax.axis('off')
    ax.set_xlim(0, seq_len)
    ax.set_xlabel('')
    aa_font_size = 10
    if seq_len > 200:
        aa_font_size -= 0.5
    if seq_len > 250:
        aa_font_size -= 1
    if seq_len > 300:
        return
    for j, aa in enumerate(amino_acids):
        ax.text(j + 0.5, 0.5, aa, color='black', ha='center', va='center',
                fontsize=aa_font_size)


### def visualize_sequence_heatmap_individual_lines(available_data_variables_dict, amino_acid_height, lineplot_height, indices_height, filename, xaxis_label, yaxis_label, legend_title, yaxis_position):
def visualize_sequence_heatmap_lanscape(available_data_variables_dict,
                                                         amino_acid_height,
                                                         lineplot_height,
                                                         indices_height,
                                                         xaxis_label,
                                                         yaxis_label,
                                                         legend_title,
                                                         yaxis_position,
                                                         cmap,
                                                         avg_cmap,
                                                         lp_selected_color,
                                                         avglp_selected_color,
                                                         selected_peptides,
                                                         selected_functions,
                                                         ms_average_choice,
                                                         bio_or_pep, log_transform, y_ticks, filter_type,
                                                         manual_y_axis=False, y_min_manual=None, y_max_manual=None):
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import matplotlib.colors as mcolors
    from matplotlib.colors import Normalize
    import matplotlib.lines as mlines
    import matplotlib.patches as patches
    import seaborn as sns
    all_errors = []
    # Use a list comprehension to find the maximum length of 'AA_list' across all variables
    max_sequence_length = max([len(available_data_variables_dict[var]['AA_list']) for var in available_data_variables_dict])

    # Check if there are multiple distinct protein IDs in available_data_variables_dict
    multiple_proteins = len(set([available_data_variables_dict[var]['protein_id'] for var in available_data_variables_dict])) > 1

    chunk_size = max_sequence_length
    # Create legend handles for the heatmap
    heatmap_legend_handles, heatmap_legend_labels = create_heatmap_legend_handles(cmap, num_colors, max_count, plot_zero)  # You can change the number 5 to have more or fewer color intervals

    axis_number = 3  # Total number of plots per set of data
    if plot_heatmap == 'yes':
        # Define height ratios for each subplot in a set
        height_ratios = (
                    [lineplot_height] + [indices_height] + [amino_acid_height] * len(available_data_variables_dict) + [amino_acid_height])
        axis_number = len(available_data_variables_dict) + 3

    elif plot_heatmap == 'no':
        height_ratios = ([lineplot_height] +[indices_height] + [amino_acid_height] )
        axis_number = 3

    fig, axes = plt.subplots(axis_number, 1, figsize=(25, (lineplot_height + indices_height + amino_acid_height)),
                             gridspec_kw={'height_ratios': height_ratios, 'hspace': 0})



    # Calculate centralized y-axis limits before plotting
    y_min_central, y_max_central, all_min_vals, all_max_vals = calculate_centralized_y_limits(
        available_data_variables_dict, selected_peptides, selected_functions,
        ms_average_choice, bio_or_pep, filter_type, log_transform,
        manual_y_axis, y_min_manual, y_max_manual
    )

    # Use centralized values to calculate proper y_ticks that will be consistently applied
    if all_min_vals and all_max_vals:
        y_ticks = calculate_y_ticks(all_min_vals, all_max_vals, log_transform)

    # Initialize for legend handling
    handles, labels, sample_list, var_name_list = [], [], [], []
    total_count = 0

    # Loop through each set of data and create plots
    for var_index, var in enumerate(available_data_variables_dict):
        ax1 = axes[0]
        ax1.axis('off')
        ax1 = ax1.twinx()  # Create a twin y-axis
        ax1.yaxis.set_minor_locator(plt.NullLocator())

        var_amino_acids = available_data_variables_dict[var]['AA_list']
        var_counts = available_data_variables_dict[var]['peptide_counts']
        var_ms_data = available_data_variables_dict[var]['ms_data_list']
        var_name = available_data_variables_dict[var]['label']
        var_colors = get_grouped_colors(var_counts, max_count, num_colors, plot_zero, cmap)
        bp_abs = available_data_variables_dict[var]['bioactive_peptide_abs_df']
        bp_func = available_data_variables_dict[var]['bioactive_peptide_func_df']
        # Default line style
        line_style = '-'  # Default style if other conditions don't apply

        #if ms_average_choice == 'yes' and bio_or_pep == 'no':
        #   line_style = '-'  # This can stay '-' or change as per your requirement
        #else:
        line_style = style_map[var_name]  # Get assigned line style from the style map

        if bio_or_pep != 'no' and ms_average_choice != 'only':
            filtered_bp_abs, filtered_bp_fun, filter_errors = filter_data_by_selection(bp_abs, bp_func, selected_peptides,
                                                                        selected_functions, bio_or_pep, filter_type, ms_average_choice, var_name)

            footnote_list, process_errors, min_vals, max_vals = process_chunk_data(ax1, filtered_bp_abs, filtered_bp_fun, chunk_size, 0, y_ticks, handles,
                                            labels, sample_list, var_name_list, line_style, var_name, var_ms_data,
                                            selected_peptides, selected_functions, lp_selected_color, ms_average_choice,
                                            log_transform, bio_or_pep)
            # Collect all errors
            all_errors.extend(filter_errors)
            all_errors.extend(process_errors)

        if ms_average_choice in ['yes', 'only']:
            # Ensure that line_style is defined before this point or provide a default value
            line, label, _, avg_y_values = plot_average_ms_data(ax1, var_ms_data, f'Averaged {var_name}', var_index, y_ticks, 0,
                                                  chunk_size, avg_cmap, log_transform, line_style)
            handles.append(line)
            labels.append(f'{label}')
            sample_list.append(line_style)
            var_name_list.append(var_name)
            ax1.tick_params(axis='y', labelsize=14)
        # Plot indices below the MS line plot
        ax2 = axes[1]
        ax2.axis('off')
        ax2.set_xlim(0, max_sequence_length)
        indices = [0]
        if var_index == 0:
            # Add indices at increments of 20, starting from 20 up to the length of the array, but not including the last index if it's less than 20 away
            indices.extend(range(20, max_sequence_length - 5, 20))
            # Always add the last index of the array
            indices.append(max_sequence_length - 1)
            for idx in indices:
                ax2.text(idx + 0.5, 0.5, str(total_count + idx + 1), ha='center', va='center', fontsize=16)
            total_count += max_sequence_length

            # Amino acid plots
            ax3 = axes[2]

            # Check if there's only one distinct protein
            if not multiple_proteins:
                plot_row_landscape(ax3, var_amino_acids)  # Call plot_row_landscape if only 1 protein
            else:
                ax3.axis('off')  # Plot a blank line by turning off the axis

        if plot_heatmap == 'yes':
            # Amino acid plots
            ax = axes[var_index + 3]
            plot_row_color_landscape(ax, var_amino_acids, var_colors)
            ax.text(0, 0.5, var_name, ha='right', va='center', fontsize=14)

    # Create the legend after the plotting loop, using the handles and labels without duplicates
    # This will create a dictionary only with entries where the label is not '0'abs
    create_custom_legends(fig, labels, handles, var_name_list, legend_title, heatmap_legend_handles,
                          heatmap_legend_labels, ms_average_choice, bio_or_pep, plot_type="land")


    if bio_or_pep == '2' and ms_average_choice != 'only':
        # Process the footnote_list which now contains deduplicated peptide info
        if footnote_list:
            # Create header for the detailed table
            footnote_lines = [
                "For peptides with multiple bioactive functions, the label has been changed to 'Multiple'.",
                "The following table shows the affected peptides and their associated functions:",
                "",
                "Peptide Interval/Name → Bioactive Functions:"
            ]

            # Sort footnote_list by peptide column for consistent ordering
            sorted_footnotes = sorted(footnote_list, key=lambda x: x['peptide_column'])

            # Format each peptide entry (already deduplicated during collection)
            for i, item in enumerate(sorted_footnotes, 1):
                peptide_col = item['peptide_column']
                functions = item['functions']

                # Parse peptide column to separate interval from Unique Peptide ID
                if ' ' in peptide_col:
                    interval, unique_id = peptide_col.split(' ', 1)
                    peptide_display = f"{interval} ({unique_id})"
                else:
                    peptide_display = peptide_col

                functions_str = ", ".join(functions)  # Already sorted during collection
                footnote_lines.append(f"     {i}. {peptide_display} → {functions_str}")

            # Join all lines
            footnote = '\n'.join(footnote_lines)
        else:
            footnote = ""



    fig.text(yaxis_position, 0.90, yaxis_label, va='top', rotation='vertical', fontsize=16)
    fig.text(0.5, -0.025, xaxis_label, ha='center', va='center', fontsize=16)
    plt.tight_layout()
    #plt.subplots_adjust(left=0.05)  # Create space on the left for the y-label

    if ms_average_choice == 'only' and bio_or_pep == '1':
        all_errors.append('The selection of Plot Averaged Data option "only" and Plot Specific Peptides option "Peptide Intervals" is invalid. Only the average Abundance will be plotted.')

    if bio_or_pep == '2' and ms_average_choice != 'only':
        if footnote_list and footnote:  # Log footnote content for debugging/reference
            _log_validation(footnote.replace(chr(10), ' '), level="info")
    return fig, all_errors

"""_______________________________Portrait Plot______________________________________________"""
def visualize_sequence_heatmap_portrait(available_data_variables_dict,
                                             amino_acid_height,
                                             lineplot_height,
                                             indices_height,
                                             xaxis_label,
                                             yaxis_label,
                                             legend_title,
                                             yaxis_position,
                                             cmap,
                                             avg_cmap,
                                             lp_selected_color,
                                             avglp_selected_color,
                                             selected_functions,
                                             ms_average_choice,
                                             bio_or_pep,
                                             log_transform,
                                             y_ticks,
                                             chunk_size):
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import matplotlib.colors as mcolors
    import seaborn as sns

    lineplot_height, scale_factor = port_hm_settings.get(
        len(available_data_variables_dict), (20, 0.1))
    plot_zero == 'no'
    handles, labels, sample_list, var_name_list = [], [], [], []

    for var in available_data_variables_dict:
        num_sets = len(available_data_variables_dict[var]['amino_acids_chunks'])
    # Create legend handles for the heatmap
    heatmap_legend_handles, heatmap_legend_labels = create_heatmap_legend_handles(cmap, num_colors, max_count,
                                                                                  plot_zero)  # You can change the number 5 to have more or fewer color intervals

    # Define height ratios for each subplot in a set
    height_ratios = ([lineplot_height] + [indices_height] + [amino_acid_height] * len(available_data_variables_dict)) * num_sets

    # Create a figure and set of subplots
    fig = plt.figure()

    fig, axes = plt.subplots(total_plots, 1, figsize=(20, num_sets * (
            lineplot_height + indices_height + amino_acid_height * len(available_data_variables_dict)) * scale_factor),
                             gridspec_kw={'height_ratios': height_ratios, 'hspace': 1})

    # Initialize for legend handling
    handles, labels = [], []
    total_count = 0



    # Loop through each set of data and create plots
    for i in range(num_sets):

        # Determine the max_var_amino_acids for the current i across all variables
        max_var_amino_acids = max(
            len(available_data_variables_dict[var]['amino_acids_chunks'][i])
            for var in available_data_variables_dict
        )

        for var_index, var in enumerate(available_data_variables_dict):
            ax1 = axes[axis_number * i]
            ax1.axis('off')
            ax2 = ax1.twinx()  # Create a twin y-axis

            # Get data chunks for the current variable
            var_amino_acids = available_data_variables_dict[var]['amino_acids_chunks'][i]
            var_counts = available_data_variables_dict[var]['peptide_counts_chunks'][i]
            var_ms_data = available_data_variables_dict[var]['ms_data_chunks'][i]
            var_name = available_data_variables_dict[var]['label']
            var_colors = get_grouped_colors(var_counts, max_count, num_colors, plot_zero, cmap)
            line_style = '-'

            # Plot MS data using plot_average_ms_data and handle the returned line object
            line, label, _, average_y_values = plot_average_ms_data(ax2, var_ms_data, var_name, var_index, y_ticks, i, chunk_size,
                                                  avg_cmap, log_transform, line_style='-')
            ax1.tick_params(axis='y', labelsize=10)
            handles.append(line)
            labels.append(label)
            var_name_list.append(var_name)

            # Plot indices below the MS line plot
            ax = axes[axis_number * i + 1]
            ax.axis('off')
            ax.set_xlim(0, max_sequence_length)
            indices = [0]
            if var_index == 0:
                # Add indices at increments of 20, starting from 20 up to the length of the array, but not including the last index if it's less than 20 away
                indices.extend(range(20, max_var_amino_acids - 5, 20))
                # Always add the last index of the array
                indices.append(max_var_amino_acids - 1)
                for idx in indices:
                    ax.text(idx + 0.5, 0.5, str(total_count + idx + 1), ha='center', va='center', fontsize=16)
                total_count += max_var_amino_acids

            # Amino acid plots
            ax = axes[axis_number * i + var_index + 2]
            plot_row_color(ax, var_amino_acids, var_colors)
            ax.text(0, 0.5, f'{var_name}  ', ha='right', va='center', fontsize=14)

    # Create the legend after the plotting loop, using the handles and labels without duplicates
    # Create legend handles for the heatmap
    # Initialize for legend handling
    total_count = 0

    # Create the legend after the plotting loop, using the handles and labels without duplicates
    # This will create a dictionary only with entries where the label is not '0'abs
    create_custom_legends(fig, labels, handles, var_name_list, legend_title, heatmap_legend_handles,
                          heatmap_legend_labels, ms_average_choice, bio_or_pep, plot_type="port")

    """
    handles_dict = dict(zip(labels, handles))
    legend_samples = fig.legend(handles_dict.values(), handles_dict.keys(), loc='center left',
                                bbox_to_anchor=(.905, top_legend_pos), fontsize=16, title=legend_title[0], title_fontsize=18)
    legend_peptide_count = fig.legend(handles=heatmap_legend_handles, loc='center left',
                                      bbox_to_anchor=(.905, bot_legend_pos), fontsize=16, title=legend_title[1], title_fontsize=18)
    """
    # Adjust layout and save the figure
    plt.tight_layout()
    #plt.subplots_adjust(left=0.15)  # Create space on the left for the y-label
    fig.text(yaxis_position, 0.5, yaxis_label, va='center', rotation='vertical', fontsize=16)
    fig.text(0.5, 0.05, xaxis_label, ha='center', va='center', fontsize=16)

    # Display the plot inline
    #display(fig)
    #plt.close(fig)  # Close the figure to avoid duplicate display in some environments
    return fig
