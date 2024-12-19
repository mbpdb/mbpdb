# Import necessary libraries for the script to function.
import pandas as pd
import re, os, json
import numpy as np
from IPython.display import display, HTML,clear_output, display_html

import warnings
import ipywidgets as widgets
from functools import partial
import _settings as settings
spec_translate_list = settings.SPEC_TRANSLATE_LIST
# Declare global variables and assign the settings values to them

global pd_results, mbpdb_results, mbpdb_check, filtered_heatmap_export_option
mbpdb_check = merged_df = filtered_heatmap_export_option = None  
pd_results = pd.DataFrame()
mbpdb_results = pd.DataFrame()


def check_sequence_alignment(protein_id, merged_df, proteins_dic):
    error_records = []  # List to store error details

    # Filter the DataFrame for the specified protein ID
    protein_df = merged_df[merged_df['Master Protein Accessions'] == protein_id]

    if protein_df.empty:
        print(f"No data found for protein ID {protein_id}.")
        return []

    # Get the protein sequence
    protein_sequence = proteins_dic[protein_id]['sequence']

    # Iterate over the DataFrame and perform the sequence alignment checks
    for idx, row in protein_df.iterrows():
        try:
            start_idx = int(row['start']) - 1  # Adjust for zero-based indexing
            stop_idx = int(row['stop'])

            # Extract the subsequence from the protein sequence based on start and stop positions
            subsequence = protein_sequence[start_idx:stop_idx]

            # Compare with the 'Sequence' column
            peptide_sequence = row['Sequence']

            # Check if the subsequence matches the peptide sequence
            if subsequence != peptide_sequence:
                # Prepare the error record
                peptide_interval = (int(row['start']), int(row['stop']))
                start_idx_adjusted = start_idx + 1  # Adjusting for 1-based indexing

                # Search the full protein sequence for the peptide sequence
                match_intervals = []
                match_start_idx = protein_sequence.find(peptide_sequence)
                if match_start_idx != -1:
                    match_start_idx += 1  # Adjusting to 1-based indexing
                    match_stop_idx = match_start_idx + len(peptide_sequence) - 1
                    match_intervals.append(f"{match_start_idx}-{match_stop_idx}")
                    start_discrepancy = match_start_idx - peptide_interval[0]
                else:
                    match_intervals.append("Not found in protein sequence")
                    start_discrepancy = "No Match"

                error_records.append({
                    'Positions in Proteins': row["Positions in Proteins"],
                    'Peptide': peptide_sequence,
                    'Protein Segment': subsequence,
                    'Peptide Interval': f"{peptide_interval[0]}-{peptide_interval[1]}",
                    'Found Intervals in Protein': ", ".join(match_intervals),
                    'Start Discrepancy': start_discrepancy,
                    'Master Protein Accessions': row["Master Protein Accessions"]
                })

        except KeyError as e:
            error_message = f'KeyError: {e} - Skipping this row'
            print(error_message)
            continue  # Skip this row
        except ValueError as e:
            error_message = f'ValueError: {e} - Skipping this row'
            print(error_message)
            continue  # Skip this row

    if error_records:
        # Create a DataFrame from error_records
        error_df = pd.DataFrame(error_records)

        # Show a summary
        total_mismatches = len(error_df)
        unique_peptides = error_df['Peptide'].nunique()

        # Separate the integer misalignments and count the 'No Match' entries
        mismatch_int = set(error_df['Start Discrepancy'])
        misaligned_intervals = sorted([x for x in mismatch_int if isinstance(x, int)])
        no_match_count = error_df['Start Discrepancy'].value_counts().get('No Match', 0)

        # Convert misaligned_intervals to a string
        misaligned_intervals_str = ', '.join(map(str, misaligned_intervals))

        # Create the summary HTML
        summary_html = f"""
        <h3 style="color:red;">Sequence Alignment Mismatches Detected for Protein {protein_id}</h3>
        <p>Total mismatches: <b>{total_mismatches}</b></p>
        <p>Sequences are misaligned by: <b>{misaligned_intervals_str}</b></p>
        <p>Count of sequences that have no matches between samples: <b>{no_match_count}</b></p>
        """

        # Assuming you are using this summary in a web context or within a display function

        display_html(summary_html, raw=True)

        # Display the unique peptides involved
        unique_peptides_df = error_df[['Peptide', 'Start Discrepancy']].drop_duplicates()

        # Optionally, display detailed mismatches
        detailed_html = f"""
        <h4>Detailed Mismatch Information:</h4>
        """
        display_html(detailed_html, raw=True)
        display_html(error_df.to_html(index=False), raw=True)

        return error_records  # or return error_df if you prefer
    else:
        display(HTML(f"<h3  style='color:green;'>Sequence alignment matches for protein {protein_id}.</h3>"))

        return []


def adjust_sequence_interval(user_protein_id, protein_df):
    # Create a deep copy of the original dataframe to reset later
    original_protein_df = protein_df.copy(deep=True)

    # Clear any existing output
    clear_output()

    # Create the header
    header_html = HTML("<h3><u>Adjust Peptide Intervals to Match Protein Sequence</u></h3>")

    # Dropdown for selecting a protein
    protein_dropdown = widgets.Dropdown(
        options=["Select Protein"] + user_protein_id,  # Add a placeholder option
        description='Protein:'
    )

    # Dropdown for selecting a peptide sequence, including "All Peptides"
    peptide_dropdown = widgets.Dropdown(
        options=["All Peptides"],  # Will be populated based on the selected protein
        description='Peptide:'
    )

    # Numeric input for adjusting start and stop values
    adjust_value = widgets.IntText(
        value=0,
        description='Adjustment:'
    )

    # Buttons
    apply_button = widgets.Button(
        description='Apply Adjustment',
        button_style='primary'
    )
    reset_button = widgets.Button(
        description='Reset to Default',
        button_style='warning'  # Changed to 'warning' as per your note
    )

    # Output widget to display the DataFrame after adjustments
    output = widgets.Output()

    # Function to update peptide dropdown when a protein is selected
    def update_peptide_dropdown(change):
        selected_protein = protein_dropdown.value
        if selected_protein != "Select Protein":
            # Populate the peptide dropdown with sequences from the selected protein, plus "All Peptides"
            peptides = ["All Peptides"] + protein_df[protein_df['Master Protein Accessions'] == selected_protein][
                'Sequence'].unique().tolist()
            peptide_dropdown.options = peptides
        else:
            peptide_dropdown.options = ["All Peptides"]  # Reset to default if no protein is selected

    # Function to apply adjustments when 'Apply Adjustment' button is clicked
    def apply_adjustment(b):
        selected_protein = protein_dropdown.value
        selected_peptide = peptide_dropdown.value
        adjustment = adjust_value.value

        if selected_protein == "Select Protein":
            with output:
                output.clear_output()
                display(HTML(f"<b style='color:red;'>Please select a protein.</b>"))
            return

        if adjustment == 0:
            with output:
                output.clear_output()
                display(HTML(f"<b style='color:red;'>Adjustment value is zero. No changes made.</b>"))
            return

        # Get indices of rows to adjust
        if selected_peptide == "All Peptides":
            idx = protein_df['Master Protein Accessions'] == selected_protein
        else:
            idx = (protein_df['Master Protein Accessions'] == selected_protein) & (
                        protein_df['Sequence'] == selected_peptide)

        # Check if any rows match
        if not idx.any():
            with output:
                output.clear_output()
                display(HTML(f"<b style='color:red;'>No matching peptides found.</b>"))
            return

        # Apply adjustments directly to protein_df
        protein_df.loc[idx, 'start'] += adjustment
        protein_df.loc[idx, 'stop'] += adjustment

        # Update 'Positions in Proteins'
        protein_df.loc[idx, 'Positions in Proteins'] = protein_df.loc[idx].apply(
            lambda row: f"{row['Master Protein Accessions']} [{row['start']}-{row['stop']}]", axis=1
        )

        # Display the adjusted rows
        adjusted_rows = protein_df.loc[
            idx, ['Master Protein Accessions', 'Positions in Proteins', 'start', 'stop', 'Sequence']]
        with output:
            output.clear_output()
            display(HTML(f"<b style='color:green;'>Adjustment applied to {selected_protein}:</b>"))
            display(adjusted_rows.head(5))

        # Reset adjustment value to zero
        adjust_value.value = 0

    # Set up event listeners for changes
    protein_dropdown.observe(update_peptide_dropdown, names='value')
    apply_button.on_click(apply_adjustment)

    # Display the widgets and output
    display(header_html, protein_dropdown, peptide_dropdown, adjust_value, apply_button, output)


def replace_protein_accessions(pd_results_cleaned):
    # Check for 'P02666A1' and 'P02666A2' in 'Master Protein Accessions'
    counts_a1_accession = pd_results_cleaned['Master Protein Accessions'].str.contains('P02666A1').sum()
    counts_a2_accession = pd_results_cleaned['Master Protein Accessions'].str.contains('P02666A2').sum()

    # Check for 'P02666A1' and 'P02666A2' in 'Positions in Proteins'
    counts_a1_positions = pd_results_cleaned['Positions in Proteins'].str.contains('P02666A1').sum()
    counts_a2_positions = pd_results_cleaned['Positions in Proteins'].str.contains('P02666A2').sum()

    # Total counts
    total_counts_a1 = counts_a1_accession + counts_a1_positions
    total_counts_a2 = counts_a2_accession + counts_a2_positions

    # Display the number of occurrences with formatting
    display(HTML("<h3><u>Unique a1/a2 β-casein genetic variants peptides )</u></h3>"))
    display(HTML(f"These are unique peptides which overlap the H/P in position '67' or '82' separate from the peptides labels 'PO02666A1; P02666A2' addressed earlier."))
    display(HTML(f"<p style=font-weight:bold; margin-left:20px;'>Number of occurrences of 'P02666A1': {total_counts_a1}</p>"))
    display(HTML(f"<p style=font-weight:bold; margin-left:20px;'>Number of occurrences of 'P02666A2': {total_counts_a2}</p>"))

    if total_counts_a1 > 0 or total_counts_a2 > 0:
        # Explanatory text with updated content and formatting
        display(HTML("<h3>Options</h3>"))
        html_content = """
        1. <b>'Replace Variants'</b> - This option is ideal if you are only interested in all β-casein peptides labeled as β-casein ('P02666'). Selecting this will replace all occurrences of 'P02666A1' and 'P02666A2' with 'P02666'.<br>
        2. <b>'Do Not Replace'</b> - Choose this if you are interested in the differences between the variants 'P02666A1' and 'P02666A2'. Be cautious that any comparison involving 'P02666' alone will not include these variant peptides if you do not replace them.
        """
        display(HTML(html_content))

        # Create buttons
        replace_button = widgets.Button(description='Replace Variants', button_style='success')
        cancel_button = widgets.Button(description='Do Not Replace', button_style='warning')
        buttons = widgets.HBox([replace_button, cancel_button])
        output = widgets.Output()

        def on_replace_clicked(b):
            with output:
                output.clear_output()
                # Perform the replacement
                pd_results_cleaned['Master Protein Accessions'] = pd_results_cleaned['Master Protein Accessions'].replace({'P02666A1': 'P02666', 'P02666A2': 'P02666'})
                pd_results_cleaned['Positions in Proteins'] = pd_results_cleaned['Positions in Proteins'].str.replace(r'P02666A[12]', 'P02666', regex=True)
                # Confirm the changes
                counts_a1_accession_after = pd_results_cleaned['Master Protein Accessions'].str.contains('P02666A1').sum()
                counts_a2_accession_after = pd_results_cleaned['Master Protein Accessions'].str.contains('P02666A2').sum()
                counts_a1_positions_after = pd_results_cleaned['Positions in Proteins'].str.contains('P02666A1').sum()
                counts_a2_positions_after = pd_results_cleaned['Positions in Proteins'].str.contains('P02666A2').sum()
                total_counts_a1_after = counts_a1_accession_after + counts_a1_positions_after
                total_counts_a2_after = counts_a2_accession_after + counts_a2_positions_after

                display(HTML("<p style='color:green; font-weight:bold;'>Replacement done.</p>"))
                display(HTML(f"<p style='font-weight:bold; margin-left:20px;'>Number of occurrences of 'P02666A1' after replacement: {total_counts_a1_after}</p>"))
                display(HTML(f"<p style='font-weight:bold; margin-left:20px;'>Number of occurrences of 'P02666A2' after replacement: {total_counts_a2_after}</p>"))

        def on_cancel_clicked(b):
            with output:
                output.clear_output()
                display(HTML("<p style='color:green; font-weight:bold;'>No changes made.</p>"))
                display(HTML("<p style='font-weight:bold; margin-left:20px;'>Remember, peptides from 'P02666A1' and 'P02666A2' will not be included in analyses involving 'P02666' alone.</p>"))

        replace_button.on_click(on_replace_clicked)
        cancel_button.on_click(on_cancel_clicked)

        display(buttons, output)
    else:
        display(HTML("<p style='color:green; font-weight:bold;'>No occurrences of 'P02666A1' or 'P02666A2' found. No action needed.</p>"))


def update_labels(available_data_variables, label_widgets):
    """
    Update labels in available_data_variables based on widget values.
    """
    for var in available_data_variables:
        available_data_variables[var]['label'] = label_widgets[var].value
    display(HTML(f"<br><p>Labels updated successfully.</p>"))


def check_and_create_folder(directory, folder_name):
    folder_path = os.path.join(directory, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        #print(f"The folder '{folder_name}' was created in {directory}.")
    #else:
    #    print(f"The folder '{folder_name}' already exists in {directory}.")
    return folder_path


def create_unique_id(row):
    if pd.notna(row['Modifications']):
        unique_id = row['Sequence'] + "_" + row['Modifications'].strip()
    else:
        unique_id = row['Sequence']
    return unique_id.rstrip('_')


def find_species(header, spec_translate_list):
    """Search for a species in the header and return the first element (species name) from the list."""
    header_lower = header.lower()
    for spec_group in spec_translate_list:
        for term in spec_group[1:]:  # Iterate over possible species names/terms except the first element
            if term.lower() in header_lower:
                return spec_group[0]  # Return the first element of the list (main species name)
    return "unknown"  # Return unknown if no species match is found


def parse_fasta(filenames):
    fasta_dict = {}
    for filename in filenames:
        with open(filename, 'r') as file:
            protein_id = ""
            protein_name = ""
            sequence = ""
            species = ""
            for line in file:
                line = line.strip()
                if line.startswith('>'):
                    if protein_id:
                        # Save the previous protein entry in the dictionary
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
                        if ' ' in protein_name_full:

                            protein_name = protein_name_full#.split()[1]
                        else:
                            protein_name = protein_name_full
                        # Find species in the header
                        species = find_species(line, spec_translate_list)
                else:
                    sequence += line
            if protein_id:
                # Save the last protein entry in the dictionary
                fasta_dict[protein_id] = {
                    "name": protein_name,
                    "sequence": sequence,
                    "species": species
                }
    return fasta_dict


"""def extract_prot_files(heatmap_directory, proteins_dic):
    prot_files = [file for file in os.listdir(heatmap_directory) 
                  if file.endswith('absorbance_heatmap_data.csv') 
                  and any(protein in file for protein in proteins_dic)]
    processed_prot_files = [file.split('_')[0] for file in prot_files]
    return sorted(set(processed_prot_files))"""

def initialize_settings():
    global images_folder_name, vp_directory, current_directory, heatmap_directory

    current_directory = os.getcwd()
    heatmap_directory = check_and_create_folder(current_directory,'heatmap_data_files')
    images_folder_name = check_and_create_folder(current_directory, 'heatmap_images')
    vp_directory = check_and_create_folder(current_directory, 'volcano_plot')
    #fasta_dir = 'fasta_files/'
    #fasta_files = [f for f in os.listdir(fasta_dir) if f.endswith('.fasta')]
    #proteins_dic = parse_fasta([os.path.join(fasta_dir, f) for f in fasta_files])
    
    return {
        'current_directory': current_directory,
        'heatmap_directory': heatmap_directory,
        'images_folder_name': images_folder_name,
        #'fasta_dir': fasta_dir,
        #'fasta_files': fasta_files,
        #'proteins_dic': proteins_dic
    }

def get_protein_details(protein_id, proteins_dic):
    if protein_id in proteins_dic:
        display(HTML(f"Details for protein ID '<b>{protein_id}</b>':"))
        display(HTML(f"<b>{proteins_dic[protein_id]}</b>"))
        protein_name_full = proteins_dic[protein_id]['name']
        if ' ' in protein_name_full:
            protein_name_short = protein_name_full.split()[1]
        else:
            protein_name_short = protein_name_full
        return protein_name_short
    else:
        display(HTML(f"Protein ID '<b>{protein_id}</b>' not found in the parsed data."))
        return protein_name_short

    csv_abs_files = sorted([file for file in os.listdir(heatmap_directory) if file.endswith('absorbance_heatmap_data.csv') and file.startswith(user_protein_id)])
    return csv_abs_files

def display_file_selection(csv_abs_files, heatmap_directory, user_protein_id):
    if len(csv_abs_files) < 1:
        display(HTML(f"<b>No files</b> are available in the <b>{heatmap_directory}</b> directory that match the selected protein ID: <b>{user_protein_id}</b><br>"))
        display(HTML(f"Please select a different Protein ID from the cell above, or upload the correct files to the {heatmap_directory} directory. <br>"))
        return False
    else:
        display(HTML(f"<b>List of available absorbance data heatmap files:</b>"))
        for index, file in enumerate(csv_abs_files):
            display(HTML(f"<b>{index + 1}</b>: {file}"))
        return True

def process_user_file_selection(selected_indices, csv_abs_files):
    indices = [index.strip() for index in selected_indices.split(',')]
    try:
        indices = [int(index) for index in indices]
        if all(1 <= index <= len(csv_abs_files) for index in indices):
            selected_abs_filenames = [csv_abs_files[index - 1] for index in indices]
            return selected_abs_filenames, True
        else:
            display(HTML(f'<span style="color:red;">Error: All indices must be between 1 and {len(csv_abs_files)}. Please try again.</span>'))
            return [], False
    except ValueError:
        display(HTML('<span style="color:red;">Error: Please enter valid integer indices separated by commas. Example: 1, 3</span>'))
        return [], False

def select_proteins(df, proteins_dic):
    """
    Creates a dropdown widget to select proteins from the DataFrame, sorted by frequency of occurrences.
    
    Parameters:
    - df (pd.DataFrame): The DataFrame containing protein data.
    - proteins_dic (dict): Dictionary mapping protein IDs to descriptions.
    
    Returns:
    - widgets.SelectMultiple: The SelectMultiple widget for protein selection.
    - list: List of selected protein IDs.
    """
    # Count occurrences of each protein
    protein_counts = df['Master Protein Accessions'].value_counts()
    sorted_proteins = protein_counts.index.tolist()
    
    display(HTML("<h3><u>Available Protein IDs (sorted by frequency):</u></h3>"))

    # Create a dropdown widget for protein selection
    protein_dropdown = widgets.SelectMultiple(
        options=[(f"{protein} - {proteins_dic.get(protein, {'name': 'Unknown'})['name']}", protein) for protein in sorted_proteins],
        description='Select Proteins:',
        layout=widgets.Layout(width='50%', height='300px')
    )
    
    # Create buttons for confirmation and reset
    confirm_button = widgets.Button(
        description='Confirm Selection',
        button_style='success'
    )
    
    reset_button = widgets.Button(
        description='Reset Selection',
        button_style='warning'
    )

    # Output widget to display the selected proteins
    output = widgets.Output()

    selected_proteins = []

    # Define the event handler for the confirm button click
    def on_confirm_button_clicked(b):
        with output:
            # Add a button to proceed to the next step if 'Unknown' is in selected proteins
            
            next_step_button = widgets.Button(
                description='Next Step',
                button_style='info',
                layout=widgets.Layout(display='none')  # Initially hidden
            )
            
            output.clear_output()
            selected_proteins.clear()
            selected_proteins.extend(protein_dropdown.value)
            protein_display_list = []  # List to store formatted protein information


            known_protein_count = 0  # To count the number of known proteins

            for protein in selected_proteins:
                protein_info = proteins_dic.get(protein, {'species': 'Unknown', 'name': 'Unknown'})

                # Check if the protein has a known sequence
                if protein_info['name'] != 'Unknown':
                    known_protein_count += 1

                # Display each protein with species and name in blue
                protein_display_list.append(
                    f"&nbsp;<b>{protein}</b><span style='color:blue'> ({protein_info['species']} - {protein_info['name']})</span>"
                )
            unkouwn_protein_count =  len(selected_proteins) - known_protein_count
            # Display the number of selected proteins with known sequences in green
            if known_protein_count:
                display(HTML(f"<p style='color:green;'><b>{known_protein_count} Recognized protein(s) in the fasta files were selected</b></p>"))
            if unkouwn_protein_count:
                display(HTML(f"<p style='color:red;'><b>{unkouwn_protein_count} Protein(s) are unrecognized in the protein fasta files.</b></p>"))

            display(HTML("<h3>Selected Proteins:</h3>"))

            # Display the list of proteins
            display(HTML("<br>".join(protein_display_list)))

            # Logic to show or hide the next step button based on unknown protein names
            if any(proteins_dic.get(protein, {'name': 'Unknown'})['name'] == 'Unknown' for protein in
                   selected_proteins):
                next_step_button.layout.display = 'inline-block'
            else:
                next_step_button.layout.display = 'none'

    # Define the event handler for the reset button click
    def on_reset_button_clicked(b):
        with output:
            output.clear_output()
        protein_dropdown.value = []
    
    # Attach the event handlers to the buttons
    confirm_button.on_click(on_confirm_button_clicked)
    reset_button.on_click(on_reset_button_clicked)
    
    # Display the dropdown, buttons, and output widget
    buttons = widgets.HBox([confirm_button, reset_button])
    display(protein_dropdown)
    display(buttons)
    display(output)

    return protein_dropdown, selected_proteins

def add_protein_manually(proteins_dic, protein_id):
    """
    Manually adds a protein to a dictionary based on user input and saves it to a FASTA file.

    Parameters:
    - proteins_dic (dict): Dictionary to which the protein details will be added.
    - protein_id (str): The protein ID to add.
    """
    protein_name = input("Enter the protein name: ")
    sequence = input("Enter the protein sequence: ")
    proteins_dic[protein_id] = {"name": protein_name, "sequence": sequence}

    # Write the new protein to a FASTA file
    fasta_path = 'fasta_files/new_protein.fasta'
    with open(fasta_path, 'a') as fasta_file:  # 'a' to append if you might add multiple entries over time
        fasta_file.write(f">sp|{protein_id}|{protein_name}|newly added\n{sequence}\n")
    
    display(HTML(f"Protein <b>{protein_id}</b> added successfully and saved to <b>{fasta_path}</b>."))

def check_and_add_protein(user_protein_ids, proteins_dic):
    """
    Checks if each protein ID in a list exists in a dictionary.
    If a protein ID is found, it prints the details. If not found, it offers the user
    the option to manually add the protein to the dictionary.

    Parameters:
    - user_protein_ids (list): A list of protein IDs to check against the proteins_dic dictionary.
    - proteins_dic (dict): Dictionary of existing proteins.
    """
    for pid in user_protein_ids:
        if pid in proteins_dic:
            display(HTML(f"Details for protein ID '<b>{pid}</b>':"))
            display(proteins_dic[pid])
        else:
            display(HTML(f'<b style="color:red;">Protein ID \'{pid}\' not found in the imported protein FASTA files.</b>'))
            add_protein_button = widgets.Button(
                description='Add Protein Manually',
                button_style='warning'
            )

            def on_add_protein_button_clicked(b, pid=pid):
                add_protein_manually(proteins_dic, pid)
                add_protein_button.close()  # Remove the button after clicking

            add_protein_button.on_click(on_add_protein_button_clicked)
            display(add_protein_button)

# Function to fetch protein names from the dictionary
def fetch_protein_names(accession_str):
    names = []
    for acc in accession_str.split('; '):

        if acc in proteins_dic:
            names.append(f"{acc}<span style='color:blue'> ({proteins_dic[acc]['species']} - {proteins_dic[acc]['name']})</span>")
        else:
            names.append(acc)
    return ' - '.join(names)

def process_protein_combinations(pd_results):
    df = pd_results.copy()
    # Display introductory information
    display(HTML("<h3>Peptides Mapped to Multiple Proteins</h3>"))
    display(HTML("Peptides that have been identified and <b>mapped to multiple proteins</b> and the '<b>Master Protein Accessions</b>' and '<b>Positions in Proteins</b>' columns have multiple entries for a single peptide require special attention."))

    # Count peptides with multiple protein accessions
    num_multiple_entries = len(pd_results[pd_results['Master Protein Accessions'].str.contains(';')])
    display(HTML(f"In your dataset, you have <b>{num_multiple_entries}</b> peptides mapped to multiple Master Protein Accessions."))

    unique_proteins = pd_results['Master Protein Accessions'].dropna().unique()
    multi_protein_combinations = [up for up in unique_proteins if ';' in up]

    # Instructions for user actions
    display(HTML("<h3>Options</h3>"))
    html_content = """
    For each protein combination with multiple entries, you have two options:<br>
    1. <b>'new'</b> - Create a new row for each protein listed in the 'Master Protein Accessions' column and their corresponding 'Positions in Proteins'.<br>
    2. <b>Enter a Protein ID</b> - Replace the current protein combination with a custom Protein ID of your choice, updating 'Positions in Proteins' accordingly.
    """
    #    2. <b>'remove'</b> - Remove all but the first listed protein in the 'Master Protein Accessions' column and its corresponding position in 'Positions in Proteins'.<br>

    display(HTML(html_content))
    user_decisions = {}
    decision_inputs = []

    for combo in multi_protein_combinations:
        named_combo = fetch_protein_names(combo)
        occurrences = pd_results[pd_results['Master Protein Accessions'].str.contains(combo, regex=False)].shape[0]
        display(HTML(f"<b>{occurrences}</b> occurrences of <b>'{named_combo}'</b>."))

        decision_input = widgets.Text(
            placeholder="Enter 'new', or a custom Protein ID",
            description='Decision:',
            layout=widgets.Layout(width='50%')
        )
        decision_inputs.append(decision_input)
        display(decision_input)


    
    def on_submit(button, df):
        with output_area:
            output_area.clear_output()
            for combo, decision_input in zip(multi_protein_combinations, decision_inputs):
                user_decisions[combo] = decision_input.value.strip().upper()

            # Iterate over each row in the DataFrame
            for index, row in df.iterrows():
                proteins_row = row['Master Protein Accessions']
                positions_row = row['Positions in Proteins']

                if proteins_row in user_decisions:
                    decision = user_decisions[proteins_row]
                    # Split accessions and positions
                    accessions = proteins_row.split('; ')
                    positions = positions_row.split('; ')

                    # Create a dictionary to map each accession to its corresponding position
                    accession_position_map = {}
                    for acc in accessions:
                        for pos in positions:
                            if acc in pos:
                                accession_position_map[acc] = pos
                                positions.remove(pos)
                                break
                    acc_pos_pairs = list(accession_position_map.items())
            
                    if decision == 'NEW':
                        # Update the current row
                        df.at[index, 'Master Protein Accessions'] = acc_pos_pairs[0][0]
                        df.at[index, 'Positions in Proteins'] = acc_pos_pairs[0][1]
                        
                        # Create new rows for each additional accession and position
                        for acc, pos in acc_pos_pairs[1:]:
                            new_row = row.copy()  # Make a copy of the current row
                            new_row['Master Protein Accessions'] = acc
                            new_row['Positions in Proteins'] = pos
                            df.loc[len(df)] = new_row
                     
                    #If user inputs new protein ID
                    else:
                        new_accession = decision
                        new_positions = []
                        for pos in positions_row.split('; '):
                            num_range = pos[pos.index('['):] if '[' in pos else ''
                            new_positions.append(f"{new_accession} {num_range}")

                        df.at[index, 'Master Protein Accessions'] = new_accession
                        df.at[index, 'Positions in Proteins'] = '; '.join(new_positions)

            # Filter positions if any entry still contains ';'
            #if len(df[df['Positions in Proteins'].str.contains(';')]) > 0:
            #    df['Positions in Proteins'] = df.apply(filter_positions, axis=1)

            # Display output
            display(HTML("<hr style='border: 1px solid grey;'>"))
            display(HTML("<h3>Output:</h3>"))
            for combo, decision in user_decisions.items():
                if decision == 'NEW':
                    display(HTML(f'<b>{combo}</b> <b style="color:green;">has been successfully processed.</b>'))
                    display(HTML(
                        '&nbsp;&nbsp;&nbsp;&nbsp;Shared occurrences of the peptide have been separated, with each now assigned a unique protein ID in a new row.'))
                else:
                    display(HTML(f'<b>{combo}</b> <b style="color:green;">has been successfully processed.</b>'))
                    display(HTML(
                        f'&nbsp;&nbsp;&nbsp;&nbsp;The occurrences of the peptide with the shared combined protein ID "{combo}" have been replaced with "{decision}".'))
        return df
    
    def on_reset_button_clicked(b, df):
        with output_area:
            output_area.clear_output()
            display(HTML('<span style="color:red;">To reset "Mapped to Multiple Proteins" selection after hitting the submitt button, <b>rerun the cell</b> and make the correct selections. This button <b>only</b> display instructions</span>'))

    submit_button = widgets.Button(description="Submit", button_style='success')
    reset_button = widgets.Button(description="Reset Selection", button_style='warning')

    button_box_protein = widgets.HBox([submit_button, reset_button])
    display(button_box_protein)
    output_area = widgets.Output()
    display(output_area)



    reset_button.on_click((partial(on_reset_button_clicked, df=pd_results)))

    submit_button.on_click((partial(on_submit, df=df)))
    return df

def setup_data_loading_ui():
    reset_file_button = widgets.Button(
        description='Reset Selection',
        button_style='warning')

    # Define the event handler for the reset button click
    def on_reset_file_button_clicked(b):
        with output_area:
            output_area.clear_output()
        mbpdb_dropdown.value = 'Select a MBPDB file'
        pd_dropdown.value = 'Select a Peptidomic data file'
        
    reset_file_button.on_click(on_reset_file_button_clicked)
   
    files =  sorted([f for f in os.listdir(os.getcwd())if f.endswith(('.csv', '.txt', '.tsv', '.xlsx'))])
    if not files:
        display(HTML('<b>No files found in the directory.</b>'))
        return

    # Setup dropdowns
    submit_button = widgets.Button(description="Submit", button_style='success')

    mbpdb_dropdown = widgets.Dropdown(options=['Select a MBPDB file'] + files,
                                      description='MBPDB File:',
                                      layout=widgets.Layout(width='300px'),  # Adjust dropdown width
                                      style={'description_width': '100px'}  # Adjust the description label width
                                      )
    pd_dropdown = widgets.Dropdown(options=['Select a Peptidomic data file'] + files,
                                   description='Peptidomic File:',
                                   layout=widgets.Layout(width='300px'),  # Adjust dropdown width
                                   style={'description_width': '100px'}  # Adjust the description label width
                                   )
    output_area = widgets.Output()
    file_button_row = widgets.HBox([submit_button, reset_file_button])

    display(mbpdb_dropdown, pd_dropdown, file_button_row, output_area)

    def on_mbpdb_change(change):
        global mbpdb_results, mbpdb_check
        if change['type'] == 'change' and change['name'] == 'value':
            with output_area:
                output_area.clear_output()
                mbpdb_check = None
                mbpdb_results = pd.DataFrame()
                if change['new'] == 'Not Interested':
                    mbpdb_check = 'none'
                elif change['new'] != 'Select a MBPDB file':
                    mbpdb_check = 'yes'
                    required_columns = ['Search peptide', 'Protein ID', 'Peptide']
                    mbpdb_results, _ = load_data(change['new'], required_columns, 'MBPDB')
                #if mbpdb_results is not None:
                #    display(HTML('<b>MBPDB Results:</b>'))
                #    display(mbpdb_results.head(n=5))

    def on_pd_change(change):
        global pd_results
        if change['type'] == 'change' and change['name'] == 'value':
            with output_area:
                output_area.clear_output()
                pd_results = None
                if change['new'] != 'Select a Peptidomic data file':
                    required_columns = ['Positions in Proteins']
                    pd_results, _ = load_data(change['new'], required_columns, 'Peptidomic')
                #if pd_results is not None:
                #    display(HTML('<b>Peptidomic Data Results:</b>'))
                #    display(pd_results.head(n=5))

    mbpdb_dropdown.observe(on_mbpdb_change)
    pd_dropdown.observe(on_pd_change)
    
    def on_submit_button_clicked(b):
        global pd_results, mbpdb_results
        with output_area:
            clear_output()
            # Checking if data was loaded and display results
            try:
                if pd_results is not None:
                    display(HTML(f'<b style="color:green;">Peptidomic data imported with {pd_results.shape[0]} rows and {pd_results.shape[1]} columns.</b>'))
                    # Access the global variables for further processing
                    if not mbpdb_results.empty:
                        display(HTML(f'<b style="color:green;">MBPDB file imported with {mbpdb_results.shape[0]} rows and {mbpdb_results.shape[1]} columns</b>'))
                    else:
                        display(HTML(f'<b style="color:orange;">No bioactivity data uploaded.</b>'))

            except Exception as e:
                display(HTML(f'<b style="color:red;">No data to display or error: {str(e)}.</b>'))

    submit_button.on_click(on_submit_button_clicked)
    
def load_data(file_name, required_columns, file_type):
    try:
        extension = file_name.split('.')[-1]
        if extension == 'csv':
            df = pd.read_csv(file_name)
        elif extension in ['txt', 'tsv']:
            df = pd.read_csv(file_name, delimiter='\t')
        elif extension == 'xlsx':
            df = pd.read_excel(file_name)
        else:
            raise ValueError("Unsupported file format.")
        
        df.columns = df.columns.str.strip()  # Strip whitespace from column names

        # General required column check
        if not set(required_columns).issubset(df.columns):
            missing = set(required_columns) - set(df.columns)
            display(HTML(f'<b style="color:red;">{file_type} File Error: Missing required columns: {", ".join(missing)}</b>'))
            return None, 'no'
        
        return df, 'yes'
    except pd.errors.ParserError:
        display(HTML(f'<b style="color:red;">{file_type} File Error: Error tokenizing data. Check the file format and consistency.</b>'))
        return None, 'no'
    except ValueError as e:
        display(HTML(f'<b style="color:red;">{file_type} File Error: {str(e)}</b>'))
        return None, 'no'


def calculate_group_abundance_std_averages(df, group_data):
    """
    Calculates the mean and standard deviation of specified 'abundance_columns' for each group in the group_data,
    storing the result in new columns named after each 'grouping_variable'.

    Parameters:
    - df (pd.DataFrame): DataFrame containing the abundance data.
    - group_data (dict): Dictionary containing group numbers as keys, and dictionaries with
      'grouping_variable' and 'abundance_columns' as values.

    Returns:
    - pd.DataFrame: The updated DataFrame with additional columns for each group's average abundance and standard deviation.
    """

    new_columns = {}

    for group_number, details in group_data.items():
        grouping_variable = details['grouping_variable']
        abundance_columns = details['abundance_columns']

        # Convert 'abundance_columns' to numeric, treating non-convertible values as NaN
        for col in abundance_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Calculate the mean and standard deviation across these columns for each row, skipping NaN values
        average_column_name = f"Average_Abundance_{grouping_variable}"
        #standev_column_name = f"SD_Abundance_{grouping_variable}"

        #new_columns[standev_column_name] = df[abundance_columns].std(axis=1, skipna=True)
        new_columns[average_column_name] = df[abundance_columns].mean(axis=1, skipna=True)

    # Add all new columns to the DataFrame at once
    df = pd.concat([df, pd.DataFrame(new_columns)], axis=1)
    if not df.empty:
        display(HTML(
            '<b style="color:green;">Group average abundance columns have been successfully added to the DataFrame.</b>'))
    return df


# Create an output area for messages or further actions
gd_output_area = widgets.Output()


def display_grouping_dictionary_selector(gd_files):
    """
    Display a dropdown menu for selecting a JSON grouping dictionary file and a submit button.
    If no valid file is selected, it shows an error message.
    """

    if not gd_files:
        display(HTML('<b>No JSON dictionary files found in the directory.</b>'))
    else:
        # Create a dropdown for selecting the JSON file
        gd_dropdown = widgets.Dropdown(
            options=['Select an existing grouping dictionary file'] + gd_files,
            description='Defined groups:',
            disabled=False,
            layout=widgets.Layout(width='450px'),  # Adjust the width as needed
            style={'description_width': '100px'}  # Adjust the description label width
        )

        # Create a submit button
        gd_submit_button = widgets.Button(
            description="Submit",
            button_style='success',
            icon='check'  # Add a check icon (optional)
        )


        # Define what happens when the submit button is clicked
        def on_gd_submit_button_clicked(b):
            selected_file = gd_dropdown.value
            with gd_output_area:
                clear_output()  # Clear any previous output

                if selected_file == 'Select an existing grouping dictionary file':
                        print("Please select a valid file.")
                else:
                    display(HTML(f'<b style="color:green;">Successfully uploaded: {selected_file}</b>'))

                    try:
                        # Load the selected JSON file
                        with open(selected_file, 'r') as file:
                            data = json.load(file)
                        global group_data,group_number
                        group_data = {}  # Initialize an empty dictionary to store group data

                        # Iterate through each group in the JSON file
                        for group_number, group_info in data.items():
                            group_name = group_info.get('grouping_variable')
                            selected_columns = group_info.get('abundance_columns')

                            # Store the data in the group_data dictionary
                            group_data[group_number] = {
                                'grouping_variable': group_name,
                                'abundance_columns': selected_columns
                            }
                            with output:
                                # Display the group information
                                display(HTML(
                                    f"<b>Group {group_number}</b> created with <b>{len(selected_columns)} columns assigned</b>."))
                                display(HTML(f"<b>Grouping Variable:</b> {group_name}"))
                                display(HTML(f"<b>Selected Columns:</b> {', '.join(selected_columns)}"))
                                display(HTML("<hr style='border: 1px solid black;'>"))

                    except Exception as e:
                        # Handle errors (e.g., file read errors or invalid JSON format)
                        display(
                            HTML(f"<b style='color:red;'>An error occurred while processing the file: {str(e)}</b>"))

                    except Exception as e:
                        # Handle errors (e.g., file read errors or invalid JSON format)
                        display(HTML(f"<b style='color:red;'>An error occurred while processing the file: {str(e)}</b>"))
                    return data
        # Attach the function to the submit button click event
        gd_submit_button.on_click(on_gd_submit_button_clicked)

        display(HTML("<h3><u>Upload Existing Group Dictionary:</u></h3>"))

        # Display the dropdown, button, and output area
        display(gd_dropdown, gd_submit_button, gd_output_area)

# Widgets for selection
column_dropdown = widgets.SelectMultiple(
    description='Absorbance',
    disabled=False,
    layout=widgets.Layout(width='50%', height='300px')
)

grouping_variable_text = widgets.Text(
    description='Group Name',
    layout=widgets.Layout(width='50%')
)

search_button = widgets.Button(
    description='Search',
    button_style='info',
    layout=widgets.Layout(margin='10px 10px 0 0')  # Add margin-right for spacing
)

add_group_button = widgets.Button(
    description='Add Group',
    button_style='success',
    layout=widgets.Layout(margin='10px 10px 0 0')  # Add margin-right for spacing
)


reset_file_button = widgets.Button(
    description='Reset Selection',
    button_style='warning',
    layout=widgets.Layout(margin='10px 10px 0 75px')  # Add margin-right for spacing
)

# Define the event handler for the reset button click
def on_reset_file_button_clicked(b):
    global group_data
    group_data = {}
    with gd_output_area:
        clear_output()  # Clear any previous output

    with output:
        output.clear_output()
    #display_grouping_dictionary_selector(gd_files)
    #setup_widgets(pd_results_cleaned)


reset_file_button.on_click(on_reset_file_button_clicked)

output = widgets.Output()



def setup_widgets(pd_results_cleaned):
    global filtered_columns, group_data, group_number

    # Define the list of columns to exclude and the substrings to filter out
    columns_to_exclude = ['Marked as', 'Number of Missed Cleavages', 'Number of PSMs',
                          'Checked', 'Confidence', 'Annotated Sequence', 'Unnamed: 3', 'Modifications',
                          '# Protein Groups', '# Proteins', '# PSMs', 'Master Protein Accessions',
                          'Positions in Proteins', 'Modifications in Proteins', '# Missed Cleavages',
                          'Theo. MH+ [Da]', 'Quan Info', 'Confidence (by Search Engine): Sequest HT',
                          'q-Value (by Search Engine): Sequest HT', 'PEP (by Search Engine): Sequest HT',
                          'SVM Score (by Search Engine): Sequest HT', 'XCorr (by Search Engine): Sequest HT',
                          'PEP', 'q-Value', 'Top Apex RT [min]', 'Top Apex RT in min',
                          'Confidence by Search Engine Sequest HT',
                          'Peptide Groups Peptide Group ID', 'Sequence', 'Number of Protein Groups',
                          'Number of Proteins', 'Sequence Length', 'Theo MHplus in Da',
                          'q-Value by Search Engine Sequest HT',
                          'PEP by Search Engine Sequest HT', 'SVM Score by Search Engine Sequest HT',
                          'XCorr by Search Engine Sequest HT', 'PEP', 'q-Value', 'Top Apex RT in min'
                          ]
    exclude_substrings = ['Abundances by Bio Rep', 'Count', 'Origin']

    filtered_columns = []
    group_data = {}
    group_number = 1

    filtered_columns = [
        col for col in pd_results.columns 
        if col not in columns_to_exclude and not any(substring in col for substring in exclude_substrings)
    ]

    column_dropdown.options = filtered_columns
    grouping_variable_text.value = ''
    column_dropdown.value = ()
    group_data.clear()
    group_number = 1

# Function to search and select columns based on the grouping variable
def search_columns(b):
    group_name = grouping_variable_text.value
    if group_name:
        matching_columns = [col for col in filtered_columns if group_name in col]
        column_dropdown.value = matching_columns
    else:
        with output:
            display(HTML('<b style="color:red;">Please enter a group name to search.</b>'))

# Function to add a group
def add_group(b):
    global group_number
    global group_data  # Ensure we are modifying the global group_data dictionary if it was imported earlier

    group_name = grouping_variable_text.value
    selected_columns = list(column_dropdown.value)

    if group_name and selected_columns:
        # If group_data was imported earlier, append the new group to it
        if group_data is None:
            group_data = {}  # Initialize if group_data is not already present
        else:
            group_number = len(group_data) + 1
        # Add new group data to the dictionary
        group_data[group_number] = {
            'grouping_variable': group_name,
            'abundance_columns': selected_columns
        }

        # Display output for the added group
        with output:
            clear_output()  # Clear any previous output
            display(HTML(f"<b>Group {group_number}</b> created with <b>{len(selected_columns)} columns assigned</b>."))
            display(HTML(f"<b>Grouping Variable:</b> {group_name}"))
            display(HTML(f"<b>Selected Columns:</b> {', '.join(selected_columns)}"))
            display(HTML("<hr style='border: 1px solid black;'>"))

        # Increment the group_number for the next group
        group_number += 1

        # Reset the input fields after adding the group
        grouping_variable_text.value = ''
        column_dropdown.value = ()

    else:
        # Show an error message if group_name or selected_columns are not provided
        with output:
            clear_output()  # Clear any previous output
            display(HTML('<b style="color:red;">Please enter a group name and select at least one column.</b>'))

search_button.on_click(search_columns)
add_group_button.on_click(add_group)

# Layout for search and add group buttons
button_row = widgets.HBox([search_button, add_group_button])

# Layout for the centered rest button
resest_row = widgets.HBox([reset_file_button])

# Combine everything in a vertical box
button_box = widgets.VBox([button_row, resest_row])

def display_widgets():
    display(HTML("<h3><u>Select New Grouping of Data:</u></h3>"))
    display(HTML('Now select the <b>absorbance columns</b> and assign the name of the <b>grouping variable</b>:'))
    display(column_dropdown)
    display(grouping_variable_text)
    display(button_box)
    display(output)


def extract_bioactive_peptides(mbpdb_results, mbpdb_check=True):
    """
    Extracts the list of bioactive peptide matches from the imported MBPDB search,
    filters the PD results, and creates two new dataframes:
    - mbpdb_results_cleaned: Contains only peptide matches.
    - mbpdb_results_grouped: Handles cases of duplicate peptide entries with different functions.
    
    Parameters:
    - mbpdb_results (pd.DataFrame): The MBPDB search results dataframe.
    - mbpdb_check (bool): A flag to indicate if the MBPDB check should be performed.
    
    Returns:
    - Tuple[pd.DataFrame, pd.DataFrame]: The cleaned and grouped dataframes.
    """
    if mbpdb_check:
        #mbpdb_set = set(mbpdb_results['Search peptide'])
        #print("Number of unique peptides from MBPDB Search:", len(mbpdb_set))

        # Drop rows where 'Protein ID' is NaN or 'None'
        mbpdb_results_cleaned = mbpdb_results.copy()
        mbpdb_results_cleaned.dropna(subset=['Protein ID'], inplace=True)
        mbpdb_results_cleaned = mbpdb_results_cleaned[mbpdb_results_cleaned['Protein ID'] != 'None']

        # Check if '% Alignment' column exists in mbpdb_results
        if '% Alignment' in mbpdb_results_cleaned.columns:
            agg_dict = {
                'Peptide': 'first', 
                'Protein ID': 'first',  # Assuming 'Protein ID' is the same for each peptide
                'Protein description': 'first',
                '% Alignment': 'first',
                'Species': 'first',
                'Intervals': 'first',
                'Function': lambda x: list(x.dropna().unique())  # Collect unique non-null functions into a list
            }
        else:
            agg_dict = {
                'Peptide': 'first', 
                'Protein ID': 'first',  # Assuming 'Protein ID' is the same for each peptide
                'Protein description': 'first',
                'Species': 'first',
                'Intervals': 'first',
                'Function': lambda x: list(x.dropna().unique())  
            }

        # Perform the groupby and aggregation
        mbpdb_results_grouped = mbpdb_results_cleaned.groupby('Search peptide').agg(agg_dict).reset_index()

        # Flatten the 'Function' list into a string if it has only one item, or join multiple items with a semicolon
        mbpdb_results_grouped['Function'] = mbpdb_results_grouped['Function'].apply(lambda x: '; '.join(x) if isinstance(x, list) else x)
        return mbpdb_results_cleaned, mbpdb_results_grouped
    else:
        return None, None


def process_pd_results(pd_results_cleaned, mbpdb_results_grouped, mbpdb_check):
    """
    Processes the PD results DataFrame by:
    - Removing multiple proteins from 'Positions in Proteins' and 'Master Protein Accessions' columns.
    - Removing leading and trailing amino acids from 'Annotated Sequence' to create a new 'Sequence' column.
    - Creating a unique ID for each peptide.
    - Extracting start and stop positions from 'Positions in Proteins'.
    - Merging with MBPDB results if provided.
    
    Parameters:
    - pd_results_cleaned (pd.DataFrame): The PD results DataFrame.
    - mbpdb_results_grouped (pd.DataFrame): The grouped MBPDB results DataFrame.
    - mbpdb_check (bool): A flag to indicate if the MBPDB check should be performed.
    
    Returns:
    - pd.DataFrame: The processed and optionally merged PD results DataFrame.
    """
    # Remove multiple positions in 'Positions in Proteins'
    pd_results_cleaned['Positions in Proteins'] = pd_results_cleaned['Positions in Proteins'].str.split(';', expand=False).str[0]

    # Remove multiple proteins in 'Master Protein Accessions'
    pd_results_cleaned['Master Protein Accessions'] = pd_results_cleaned['Master Protein Accessions'].str.split(';', expand=False).str[0]

    # If 'Sequence' column is not present, create it by stripping leading and trailing amino acids
    if 'Sequence' not in pd_results_cleaned.columns:
        pd_results_cleaned['Sequence'] = pd_results_cleaned['Annotated Sequence'].str.split('.', expand=False).str[1]

    # Create a unique ID for each peptide
    pd_results_cleaned['unique ID'] = pd_results_cleaned.apply(create_unique_id, axis=1)

    # Extract start and stop positions from 'Positions in Proteins'
    try:
        # Extract start and stop, allowing for NaN values
        extracted = pd_results_cleaned['Positions in Proteins'].str.extract(r'\[(\d+)-(\d+)\]')
        # Convert to integers where possible, but keep NaN as is
        pd_results_cleaned[['start', 'stop']] = extracted.astype(float).astype('Int64')
    except Exception as e:
        print(f"Error: {e}")

    # Reorder columns to make 'start' and 'stop' the 2nd and 3rd columns
    columns_order = ['Master Protein Accessions', 'Positions in Proteins', 'start', 'stop'] + \
                    [col for col in pd_results_cleaned.columns if col not in ['Master Protein Accessions', 'Positions in Proteins', 'start', 'stop']]
    pd_results_cleaned = pd_results_cleaned[columns_order]

    # Merge with MBPDB results if provided
    if mbpdb_check and mbpdb_results_grouped is not None:
        merged_df = pd.merge(pd_results_cleaned, mbpdb_results_grouped, right_on='Search peptide', left_on='unique ID', how='left')
        display(HTML(f"<b style='color:green;'>The MBPDB was succesfully merged with the peptidomic data matching the Search Peptide and Unique ID columns.</b>"))

    else:
        merged_df = pd_results_cleaned.copy()
        merged_df['Function'] = np.nan
        display(HTML(f"<b style='color:orange;'>No MBPDB was uploaded.</b>"))
        display(HTML(f"<b style='color:orange;'>The merged Dataframe contains only peptidomic data.</b>"))

    return merged_df


def impute_missing_values(df, abundance_cols):
    # Combine all values from the abundance columns into a single series
    all_values = df[abundance_cols].stack()

    # Calculate the 5th percentile value
    fifth_percentile_value = np.percentile(all_values.dropna(), 5)

    # Calculate the minimum value in the abundance columns
    min_value = all_values.min()
    print("fifth_percentile_value:", fifth_percentile_value)
    print("min_value:", min_value)

    # Function to impute missing values
    def impute_value(x):
        if pd.isna(x):
            return np.random.uniform(min_value, fifth_percentile_value)
        return x

    # Apply the imputation function to the abundance columns
    df[abundance_cols] = df[abundance_cols].applymap(impute_value)

    return df

"""_________________________________________Data Export Functions_________________________________"""


def calculate_abundance(protein_sequence, peptide_dataframe, grouping_variable):
    # Initialize the array with zeros
    protein_sequence_length = len(protein_sequence)

    # Create a list to hold the data for the new DataFrame
    data = []

    # Column name for average abundance based on the grouping variable
    average_abundance_column = f'Average_Abundance_{grouping_variable}'

    # Iterate over the DataFrame and fill the data list
    for idx, row in peptide_dataframe.iterrows():
        try:
            start_idx = int(row['start']) - 1  # Adjust for zero-based indexing
            stop_idx = int(row['stop'])

            abundance_value = row[average_abundance_column]  # Use dynamic column name

            # Create a list with zeros for the length of the sequence
            values = [0] * protein_sequence_length

            # Set the abundance value for the specified range
            values[start_idx:stop_idx] = [abundance_value] * (stop_idx - start_idx)

            # Append the values list to the data list
            data.append(values)

        except KeyError as e:
            # Handle missing keys in the row
            print(f'KeyError: {e} - Skipping this row')
            continue  # Skip this row
        except ValueError as e:
            # Handle invalid values in the row
            print(f'ValueError: {e} - Skipping this row')
            continue  # Skip this row

    # If no valid data was processed, return an empty DataFrame
    if not data:
        print("No valid data to process. Returning empty DataFrame.")
        return pd.DataFrame()

    # Create a new DataFrame with the data
    abundance_df = pd.DataFrame(data).T

    # Name the columns based on the 'start' and 'stop' positions
    abundance_df.columns = [f'{int(row["start"])}-{int(row["stop"])}' for _, row in peptide_dataframe.iterrows()]

    # Add an 'AA' column associated with the amino acid in the sequence
    abundance_df['AA'] = list(protein_sequence)

    # Count non-zero values for each row and save as a new column 'count'
    abundance_df['count'] = abundance_df.drop('AA', axis=1).gt(0).sum(axis=1)

    # Calculate the average of non-zero values for each row and save as a new column 'average'
    abundance_df['average'] = abundance_df.drop('AA', axis=1).replace(0, np.nan).mean(axis=1)

    return abundance_df


def calculate_function(protein_sequence, peptide_dataframe, grouping_variable):
    """
    Creates a DataFrame that maps peptide function across the length of a specified protein sequence.

    Parameters:
    - protein_sequence (str): The amino acid sequence of the protein.
    - peptide_dataframe (pd.DataFrame): DataFrame containing peptide information including start and stop indices,
      and the function values for a specific grouping variable.
    - grouping_variable (str): The grouping variable to select the correct function column.

    Returns:
    - pd.DataFrame: A new DataFrame where each row represents an amino acid position in the protein sequence,
      columns represent peptide ranges, and cell values reflect the function value for that peptide if it
      overlaps with the amino acid position.
    """
    # Initialize the array with zeros
    protein_sequence_length = len(protein_sequence)
    function_array = np.zeros(protein_sequence_length)

    # Create a list to hold the data for the new DataFrame
    data = []

    # Iterate over the DataFrame and fill the data list
    for _, row in peptide_dataframe.iterrows():
        start_idx = int(row['start'] - 1)
        stop_idx = int(row['stop'])
        if stop_idx > protein_sequence_length:
            stop_idx -= 1
        if mbpdb_check:
            function_value = row['Function']  # Use dynamic column name
        else:
            function_value = np.nan
        # Create a list with zeros for the length of the sequence
        values = [None] * protein_sequence_length

        # Set the function value for the specified range
        for i in range(start_idx, stop_idx):
            values[i] = function_value

        # Append the values list to the data list
        data.append(values)

    # Create a new DataFrame with the data
    function_df = pd.DataFrame(data).T

    # Name the columns based on the 'start' and 'stop' positions
    function_df.columns = [f'{int(row["start"])}-{int(row["stop"])}' for _, row in peptide_dataframe.iterrows()]

    return function_df

"""-----------------Export_Function---------------------------------"""
def export_group_data(group_data, current_directory):
    """
    Exports the given DataFrame to a CSV file based on user input.

    Parameters:
    - df (pd.DataFrame): The DataFrame to be exported.
    - current_directory (str): The directory where the file will be saved.

    Returns:
    - str: The name of the exported CSV file.
    """
    display(HTML("<h3><u>Export Group Data</u></h3>"))

    display(HTML(
        f"Would you like to <b>export the catagoical grouping data</b> in a dictionary format as a .json file for later user?<br>"))

    group_data_widget = widgets.Text(
        value='',
        placeholder='Enter file name',
        description='File name:',
        disabled=False
    )

    save_button = widgets.Button(
        description='Save',
        button_style='success'
    )

    output = widgets.Output()

    def on_save_group_data_button_clicked(b):
        with output:
            output.clear_output()
            new_name = group_data_widget.value
            if new_name:
                file_name = f'{new_name}'
                file_name = os.path.join(current_directory, file_name)
            if not file_name.endswith('.json'):
                file_name += '.json'
            try:
                with open(file_name, 'w') as json_file:
                    json.dump(group_data, json_file, indent=4)
                output_html = "<h4>Group Data Export:</h4><hr style='border:1px solid grey;'>"
                display(
                HTML(f"{output_html}<b>{file_name}</b> was saved in the <b>{current_directory}</b><br><br>"))
            except Exception as e:
                print(f"An error occurred: {e}")

            if not file_name:
                display(HTML(f"<b style='color:red;'>No file name provided.</b>"))

    save_button.on_click(on_save_group_data_button_clicked)

    display(group_data_widget)
    display(save_button)
    display(output)

def export_dataframe(df, current_directory):
    """
    Exports the given DataFrame to a CSV file based on user input.

    Parameters:
    - df (pd.DataFrame): The DataFrame to be exported.
    - current_directory (str): The directory where the file will be saved.

    Returns:
    - str: The name of the exported CSV file.
    """
    display(HTML("<h3><u>Export Full Dataset</u></h3>"))

    display(HTML(
        f"Would you like to <b>export the full dataframe</b> to a .csv file including all proteins, peptides, bioactivity data and the newly created statistics columns<br>"))

    new_name_widget = widgets.Text(
        value='',
        placeholder='Enter file name',
        description='File name:',
        disabled=False
    )

    save_button = widgets.Button(
        description='Save',
        button_style='success'
    )

    output = widgets.Output()

    def on_save_button_clicked(b):
        with output:
            output.clear_output()
            new_name = new_name_widget.value
            if new_name:
                csv_file_name = f'{new_name}.csv'
                csv_file_path = os.path.join(current_directory, csv_file_name)
                df.to_csv(csv_file_path, index=False)
                output_html = "<h4>Dataframe export:</h4><hr style='border:1px solid grey;'>"
                display(
                    HTML(f"{output_html}<b>{csv_file_name}</b> was saved in the <b>{current_directory}</b><br><br>"))
            else:
                display(HTML(f"<b style='color:red;'>No file name provided.</b>"))

    save_button.on_click(on_save_button_clicked)

    display(new_name_widget)
    display(save_button)
    display(output)


def prompt_export_options(proteins_dic, merged_df, group_data, heatmap_directory, user_protein_id):
    """
    Prompts the user to select export options using ipywidgets and processes the export.

    Parameters:
    - proteins_dic (dict): Dictionary of proteins.
    - merged_df (pd.DataFrame): DataFrame of merged data.
    - group_data (dict): Group data.
    - heatmap_directory (str): Directory to save the heatmaps.

    Returns:
    - None
    """

    # Prepare options based on the condition
    if not pd.isna(merged_df['Function']).all():
        options = [('Export all peptides (without filtering by bioactive functions)', 'all-peptides'),
                   ('Filtered by bioactive functions from the MBPDB match, Exporting only functional peptides',
                    'bioactive-only')]
    else:
        options = [('Export all peptides', 'all-peptides')]

    # Create dropdown widget for options
    dropdown_options = widgets.Dropdown(
        options=options,
        description='Options:',
        layout=widgets.Layout(width='70%')
    )

    save_button = widgets.Button(
        description='Save',
        button_style='success'
    )

    output = widgets.Output()

    def on_save_button_clicked(b):
        global filtered_heatmap_export_option
        with output:
            output.clear_output()
            selected_option = dropdown_options.value
            display(HTML("<h4>Selected option:</h4>"))
            display(HTML(f"<p><b>{selected_option}</b></p>"))

            # Assign selected option to the global variable
            filtered_heatmap_export_option = selected_option
            process_export(proteins_dic, merged_df, group_data, heatmap_directory, user_protein_id)

    save_button.on_click(on_save_button_clicked)
    display(HTML("<h3><u>Heatmap Plot Exporting Options</u></h3>"))
    display(dropdown_options)
    display(save_button)
    display(output)

def process_export(proteins_dic, merged_df, group_data, heatmap_directory, user_protein_id):
    """
    Processes the export of heatmap data based on user-selected options and saves them to files.

    Parameters:
    - proteins_dic (dict): Dictionary of proteins.
    - merged_df (pd.DataFrame): DataFrame of merged data.
    - group_data (dict): Group data.
    - heatmap_directory (str): Directory to save the heatmaps.
    """
    export_messages = {
        'all-peptides': {'absorbance': [], 'function': []},
        'bioactive-only': {'absorbance': [], 'function': []}
    }

    # Dictionary to hold all data for saving
    complete_data = {}

    for protein_id in user_protein_id:
        protein_df1 = merged_df[merged_df['Master Protein Accessions'] == protein_id]
        is_all_null = 'Function' in protein_df1.columns and protein_df1['Function'].isnull().all()

        if protein_id in proteins_dic:
            protein_sequence = proteins_dic[protein_id]['sequence']
            protein_species = proteins_dic[protein_id]['species']
            protein_name = proteins_dic[protein_id]['name']

            protein_data = {}  # Dictionary to hold data for this protein

            for group_key, group_info in group_data.items():
                grouping_var_name = group_info['grouping_variable']  # Use grouping variable name instead of key
                if filtered_heatmap_export_option == 'all-peptides':
                    heatmap_data = export_heatmap_data_to_dict(protein_id, grouping_var_name, group_info,
                                                               protein_sequence, protein_species, protein_name,
                                                               protein_df1, is_all_null, 'all-peptides',
                                                               export_messages, heatmap_directory)

                elif filtered_heatmap_export_option == 'bioactive-only':
                    protein_df2 = protein_df1[protein_df1['Function'].notna()]
                    heatmap_data = export_heatmap_data_to_dict(protein_id, grouping_var_name, group_info,
                                                               protein_sequence, protein_species, protein_name,
                                                               protein_df2, is_all_null, 'bioactive-only',
                                                               export_messages, heatmap_directory)

                # Add the heatmap data to the protein's data dictionary with grouping variable name
                protein_data[grouping_var_name] = heatmap_data

            # Store the protein's data in the complete data dictionary
            complete_data[protein_id] = protein_data

        else:
            display(HTML(f"<b style='color:red;'>Sequence for {protein_id} not found.</b>"))

    # Save the complete data using the save_complex_dict function
    save_complex_dict(complete_data, os.path.join(heatmap_directory, 'exported_heatmap_data'))

    # Display accumulated messages
    output_html = "<h4>Heatmap Exports:</h4><hr style='border:1px solid grey;'>"
    output_html += f"<p>File location of exported files: <b>{heatmap_directory}</b></p>"

    for filter_type, types in export_messages.items():
        for data_type, messages in types.items():
            # Filter out messages that are just the protein ID
            filtered_messages = list(set([message for message in messages if message not in user_protein_id]))

            if filtered_messages:
                output_html += f"<h4>{filter_type.replace('_', ' ').title()} - {data_type.title()}:</h4><ul>"
                for message in filtered_messages:
                    output_html += f"<li>{message}</li>"
                output_html += "</ul>"

    display(HTML(output_html))


def pivot_and_save(df, grouping_var, abundance_columns, file_prefix, output_dir, label):
    file_prefix = str(file_prefix)
    melted_df = df.melt(
        id_vars=['unique ID'],
        value_vars=abundance_columns,
        var_name='Sample',
        value_name='Abundance'
    )
    pivoted_df = melted_df.pivot_table(
        index='Sample',
        columns='unique ID',
        values='Abundance'
    )
    if pivoted_df.empty:
        print(
            f"No data available to create {grouping_var}___{label}___pivoted_df_for_volcano_plot.csv. Skipping file creation.")
        return
    csv_file_name = f'{grouping_var}___{label}___pivoted_df_for_volcano_plot.csv'
    pivoted_df.to_csv(os.path.join(output_dir, csv_file_name), index=False)
    return f"{csv_file_name} has been successfully saved."


# Widget setup with a Save button
def setup_widgets_vp(merged_df, group_data, user_protein_id):
    # Dictionary for options
    options_dict = {
        'all_peptides': "Export all peptides associated with each grouping variable",
        'selected_proteins': "Filtered by selected proteins creating a separate file for each protein ID associated with each grouping variable",
    }

    dropdown = widgets.Dropdown(
        options=[(value, key) for key, value in options_dict.items()],
        description='Options:',
        disabled=False,
    )

    button = widgets.Button(description='Save', button_style='success')
    output = widgets.Output()
    # Generate HTML content for displaying options
    html_content = "<h3><u>Volcano Plot Exporting Options</u></h3>"
    display(HTML(html_content))
    display(dropdown, button, output)

    def on_button_clicked(b):
        with output:
            output.clear_output()
            export_option = dropdown.value
            export_messages = {'all-peptides': [], 'protein-id-only': []}
            if export_option:
                if export_option == 'all_peptides':
                    for group_key, group_info in group_data.items():
                        message = pivot_and_save(merged_df, group_info['grouping_variable'],
                                                 group_info['abundance_columns'], group_key, vp_directory,
                                                 'all-peptides')
                        if message:
                            export_messages['all-peptides'].append(message)

                elif export_option == 'selected_proteins':
                    for protein_id in user_protein_id:
                        if protein_id not in merged_df['Master Protein Accessions'].values:
                            display(HTML(
                                f"<span style='color: red;'>Invalid input. Protein ID {protein_id} not found.</span>"))
                            continue
                        protein_df = merged_df[merged_df['Master Protein Accessions'] == protein_id]
                        for group_key, group_info in group_data.items():
                            message = pivot_and_save(protein_df, group_info['grouping_variable'],
                                                     group_info['abundance_columns'], protein_id, vp_directory,
                                                     f'{protein_id}-only')
                            if message:
                                export_messages['protein-id-only'].append(message)
                output_html = (
                    "<h4>Volcano Plot Exports:</h4>"
                    "<hr style='border:1px solid grey;'>"

                )

                display_export_messages(output_html, export_messages, vp_directory)

    button.on_click(on_button_clicked)


def display_export_messages(output_html, export_messages, directory):
    output_html += f"<p>File location of exported files: <b>{directory}</b></p>"
    output_html += f"<h4>Selected option:</h4>"
    if export_messages['all-peptides']:
        output_html += "<h4>All-Peptides:</h4><ul>"
        for message in export_messages['all-peptides']:
            output_html += f"<li>{message}</li>"
        output_html += "</ul>"
    if export_messages['protein-id-only']:
        output_html += "<h4>Protein ID-Only:</h4><ul>"
        for message in export_messages['protein-id-only']:
            output_html += f"<li>{message}</li>"
        output_html += "</ul>"
    display(HTML(output_html))


def adjust_sequence_interval(user_protein_id, protein_df):
    # Clear any existing output
    clear_output()

    # Create the header
    header_html = HTML("<h3><u>Adjust Peptide Intervals to Match Protein Sequence</u></h3>")

    # Dropdown for selecting a protein
    protein_dropdown = widgets.Dropdown(
        options=user_protein_id,
        description='Protein:'
    )

    # Numeric input for adjusting start and stop values
    adjust_value = widgets.IntText(
        value=0,
        description='Adjustment:'
    )

    # Save button to save changes
    save_button = widgets.Button(
        description='Save',
        button_style='success'
    )

    # Output widget to display the DataFrame after adjustments
    output = widgets.Output()

    # Variable to store the updated dataframe
    updated_df = None

    # Function to adjust start/stop values and update 'Positions in Proteins' column
    def update_intervals(change):
        nonlocal updated_df
        selected_protein = protein_dropdown.value
        adjustment = adjust_value.value

        # Get the dataframe for the selected protein
        updated_df = protein_df[protein_df['Master Protein Accessions'] == selected_protein].copy()

        # Adjust start/stop values and update 'Positions in Proteins' column
        updated_df['start'] = updated_df['start'] + adjustment
        updated_df['stop'] = updated_df['stop'] + adjustment
        updated_df['Positions in Proteins'] = updated_df.apply(
            lambda row: f"{row['Master Protein Accessions']} [{row['start']}-{row['stop']}]", axis=1
        )

        # Display the updated DataFrame
        with output:
            output.clear_output()  # Clear previous output
            display(updated_df[['Master Protein Accessions', 'Positions in Proteins', 'start', 'stop']])

    # Function to handle saving the updated DataFrame
    def save_adjusted_df(b):
        if updated_df is not None:
            protein_df.update(updated_df)
            with output:
                output.clear_output()
                display(HTML(f"<b style='color:green;'>DataFrame updated and saved successfully.</b>"))
        else:
            with output:
                output.clear_output()
                display(HTML(f"<b style='color:red;'>No updates available to save.</b>"))

    # Set up event listeners for changes
    adjust_value.observe(update_intervals, names='value')
    save_button.on_click(save_adjusted_df)

    # Display the widgets and output
    display(header_html, protein_dropdown, adjust_value, save_button, output)

    return protein_df

def export_heatmap_data_to_dict(protein_id, group_key, group_info, protein_sequence, protein_species, protein_name,
                                protein_df, is_all_null, filter_type, export_messages, heatmap_directory):
    """
    Exports the heatmap data to a dictionary based on filter type.
    """
    grouping_var = group_info['grouping_variable']
    relevant_columns = group_info['abundance_columns']

    # Filter the DataFrame based on the filter_type
    if filter_type == 'all-peptides':
        filtered_df = protein_df[['start', 'stop', 'Function']]
    elif filter_type == 'bioactive-only':
        filtered_df = protein_df[protein_df['Function'].notna()][['start', 'stop', 'Function']]

    # Calculate the heatmap data
    func_heatmap_df = calculate_function(protein_sequence, filtered_df, grouping_var)
    heatmap_df = calculate_abundance(protein_sequence, protein_df, grouping_var)

    # Create the dictionary to store the results
    heatmap_data = {
        'protein_id': protein_id,
        'protein_sequence': protein_sequence,
        'protein_name': protein_name,
        'protein_species': protein_species,
        'func_heatmap_df': func_heatmap_df,
        'heatmap_df': heatmap_df
    }

    # Ensure that the dictionary has lists to append messages
    if filter_type not in export_messages:
        export_messages[filter_type] = {'absorbance': [], 'function': []}

    # Check if the absorbance message for this protein has already been added
    if protein_id not in export_messages[filter_type]['absorbance']:
        export_messages[filter_type]['absorbance'].append(
            f"<span style='color:green; font-weight:bold;'>Absorbance heatmap data for {protein_id} has been successfully stored in the dictionary.</span>"
        )

        # Mark the message as added for this protein
        export_messages[filter_type]['absorbance'].append(protein_id)

    # Only add the function data message once per protein
    if not is_all_null and protein_id not in export_messages[filter_type]['function']:
        export_messages[filter_type]['function'].append(
            f"Function heatmap data for {protein_id} has been successfully stored in the dictionary.")
    elif is_all_null and protein_id not in export_messages[filter_type]['function']:
        export_messages[filter_type]['function'].append(
        f"<span style='color:orange; font-weight:bold;'>No bioactive functions found for {protein_id}"
        )
    # Ensure that protein ID is only printed once by checking export_messages
    if protein_id in export_messages[filter_type]['absorbance'] and protein_id in export_messages[filter_type][
        'function']:
        export_messages[filter_type]['absorbance'].remove(protein_id)

    return heatmap_data

# Your existing save_complex_dict function
def save_complex_dict(data, base_filename):
    metadata = {}

    # Create a directory to store all files
    os.makedirs(base_filename, exist_ok=True)

    for key, value in data.items():
        if isinstance(value, dict):
            # Recursively handle nested dictionaries
            nested_metadata = save_complex_dict(value, os.path.join(base_filename, key))
            metadata[key] = {'type': 'nested', 'path': key}
        elif isinstance(value, pd.DataFrame):
            # Save DataFrame to CSV
            df_filename = f"{key}.csv"
            value.to_csv(os.path.join(base_filename, df_filename), index=False)
            metadata[key] = {'type': 'dataframe', 'filename': df_filename}
        else:
            # For other types, store directly in metadata
            metadata[key] = {'type': 'direct', 'value': value}

    # Save metadata
    with open(os.path.join(base_filename, 'metadata.json'), 'w') as f:
        json.dump(metadata, f)

    return metadata