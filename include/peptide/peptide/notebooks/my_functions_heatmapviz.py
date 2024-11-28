# Import necessary libraries for the script to function.
import pandas as pd
import os, re, copy, json, warnings
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import Normalize
import matplotlib.lines as mlines
import matplotlib.patches as patches
import numpy as np
from itertools import cycle
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
from io import BytesIO

# Declare global variables and assign the settings values to them
global valid_discrete_cmaps, default_hm_color, default_lp_color, default_avglp_color, default_filename_port, default_filename_land, images_folder_name
global active_vars, axis_number, num_sets, total_plots, style_map, cmap, max_sequence_length, chuck_size
global heatmap_legend_handles, lp_selected_color, avg_cmap
global selected_functions, selected_peptides, available_data_variables
global plot_heatmap, plot_zero, valid_discrete_cmaps, default_lp_color, default_avglp_color, default_filename_land

chuck_size = 78
plot_heatmap, plot_zero = 'yes', 'no'
selected_functions = []
selected_peptides = []
available_data_variables = {}

# Import settings from _settings
import _settings as settings
spec_translate_list = settings.SPEC_TRANSLATE_LIST
valid_discrete_cmaps = settings.valid_discrete_cmaps
valid_gradient_cmaps = settings.valid_gradient_cmaps
default_hm_color = settings.default_hm_color
default_lp_color = settings.default_lp_color
default_avglp_color = settings.default_avglp_color
hm_selected_color = settings.hm_selected_color
cmap = settings.cmap
lp_selected_color = settings.lp_selected_color
avglp_selected_color = settings.avglp_selected_color
avg_cmap = settings.avg_cmap
legend_title = settings.legend_title

# my_functions_heatmapviz.py

class ProteinVariableSelector:
    def __init__(self, base_filename, proteins_dic):
        self.base_filename = base_filename
        self.proteins_dic = proteins_dic
        # Initialize variables
        self.data_variables = self.extract_and_format_data()
        self.available_proteins = set([key.split('_')[0] for key in self.data_variables.keys()])
        self.available_grouping_vars = {
            protein: [key.split('_', 1)[1] for key in self.data_variables.keys() if key.startswith(protein)] for protein
            in self.available_proteins}
        self.selected_var_keys_list = []

        # Filtered Data Variables
        self.filtered_data_variables = {}
        self.available_data_variables = {}
        self.label_widgets = {}
        self.order_widgets = {}
        self.default_label_values = {}
        self.default_order_values = {}

        # Widgets
        self.create_widgets()

        # Additional attributes for plotting options
        self.ms_average_choice = None
        self.bio_or_pep = None
        self.selected_peptides = []
        self.selected_functions = []
        self.legend_title = legend_title
        # Initialize variables
        self.bio_or_pep = 'no'  # Default value
        self.plot_heatmap = 'yes'  # Default value
        self.user_protein_id = ''  # Will be set appropriately
        self.protein_name_short = ''  # Will be set appropriately

        # Widgets for plotting options
        self.ms_average_choice_dropdown = None
        self.bio_or_pep_dropdown = None
        self.specific_select_multiple = None

        self.label_order_output = widgets.Output()

    def load_complex_dict(self, base_path=None):
        """
        Recursively load the complex dictionary from a base directory.

        Parameters:
        - base_path (str): The base directory containing the data and metadata.json.
                           If None, uses self.base_filename.

        Returns:
        - result (dict): The loaded complex dictionary.
        """
        if base_path is None:
            base_path = self.base_filename

        with open(os.path.join(base_path, 'metadata.json'), 'r') as f:
            metadata = json.load(f)

        result = {}
        for key, info in metadata.items():
            if info['type'] == 'nested':
                # Recursively load nested dictionaries
                result[key] = self.load_complex_dict(os.path.join(base_path, info['path']))
            elif info['type'] == 'dataframe':
                # Load DataFrame from CSV
                result[key] = pd.read_csv(os.path.join(base_path, info['filename']))
            elif info['type'] == 'direct':
                # Load direct value from metadata
                result[key] = info['value']

        return result

    # Function to extract and format data
    def extract_and_format_data(self):
        """
        Extract and format data from the loaded complex dictionary.

        Returns:
        - data_variables (dict): A dictionary with structured information, using a combination
          of protein_id and grouping_var_name as the key.
        """
        # Load the data from the saved directory
        loaded_data = self.load_complex_dict(self.base_filename)

        # Initialize the new dictionary
        data_variables = {}

        # Iterate over the loaded data to extract and reorganize it
        for protein_id, protein_data in loaded_data.items():
            protein_sequence = protein_data.get('protein_sequence')

            for grouping_var_name, group_info in protein_data.items():
                # Extract the required DataFrames and other information
                func_df = group_info.get('func_heatmap_df')
                abs_df = group_info.get('heatmap_df')
                label = grouping_var_name
                protein_sequence = group_info.get('protein_sequence')
                protein_name = group_info.get('protein_name')
                protein_species = group_info.get('protein_species')

                # Determine if the func_df is all None
                is_func_df_all_none = func_df.isnull().all().all() if func_df is not None else True

                # Create a unique key combining protein_id and grouping_var_name
                var_key = f"{protein_id}_{grouping_var_name}"

                # Populate the data_variables dictionary using the unique key
                data_variables[var_key] = {
                    'protein_id': protein_id,
                    'protein_sequence': protein_sequence,
                    'protein_name': protein_name,
                    'protein_species': protein_species,
                    'heatmap_df': abs_df,
                    'function_heatmap_df': func_df,
                    'label': label,
                    'is_func_df_all_none': is_func_df_all_none
                }

        return data_variables

    def chunk_dataframe(self, df, chunk_size, exclude_columns=3):

        # Select all rows and all but the last 'exclude_columns' columns
        df_subset = df.iloc[:, :-exclude_columns] if exclude_columns else df

        # Calculate the number of rows needed to make the last chunk exactly 'chunk_size'
        total_rows = df_subset.shape[0]
        remainder = total_rows % chunk_size
        if remainder != 0:
            # Rows needed to complete the last chunk
            rows_to_add = chunk_size - remainder

            # Create a DataFrame with zero values for the missing rows
            additional_rows = pd.DataFrame(np.zeros((rows_to_add, df_subset.shape[1])), columns=df_subset.columns)

            # Append these rows to df_subset
            df_subset = pd.concat([df_subset, additional_rows], ignore_index=True)

        # Create chunks of the DataFrame
        max_index = df_subset.index.max() + 1
        return [df_subset.iloc[i:i + chunk_size] for i in range(0, max_index, chunk_size)]

    # Function to process data variables
    def process_data_variables(self):
        chunk_size = 78
        # Print loaded dataframes and their labels
        for var, info in self.filtered_data_variables.items():
            if 'function_heatmap_df' in info:
                if info['is_func_df_all_none']:
                    display(HTML(f"<b>{var} - Label: {info['label']}</b>: Only absorbance data loaded."))
                else:
                    display(HTML(f"<b>{var} - Label: {info['label']}</b>: Absorbance and function data loaded."))

        # Dynamically generate the list of variable names based on loaded data
        variables = list(self.filtered_data_variables.keys())
        protein_id_list = []
        protein_name_list = []
        for var in variables:
            if var in self.filtered_data_variables and 'heatmap_df' in self.filtered_data_variables[var]:
                df = self.filtered_data_variables[var]['heatmap_df']
                df_func = self.filtered_data_variables[var]['function_heatmap_df']

                try:
                    self.filtered_data_variables[var]['peptide_counts'] = df['count']
                    self.filtered_data_variables[var]['ms_data'] = df['average']

                    self.filtered_data_variables[var]['max_peptide_counts'] = self.filtered_data_variables[var][
                        'peptide_counts'].max()
                    self.filtered_data_variables[var]['min_peptide_counts'] = self.filtered_data_variables[var][
                        'peptide_counts'].min()
                    self.filtered_data_variables[var]['max_ms_data'] = self.filtered_data_variables[var][
                        'ms_data'].max()
                    self.filtered_data_variables[var]['min_ms_data'] = self.filtered_data_variables[var]['ms_data'][
                        self.filtered_data_variables[var]['ms_data'] > 0].min()

                    self.filtered_data_variables[var]['amino_acids_chunks'] = [
                        self.filtered_data_variables[var]['protein_sequence'][i:i + chunk_size]
                        for i in range(0, len(self.filtered_data_variables[var]['protein_sequence']), chunk_size)
                    ]

                    self.filtered_data_variables[var]['peptide_counts_chunks'] = [
                        self.filtered_data_variables[var]['peptide_counts'][i:i + chunk_size]
                        for i in range(0, len(self.filtered_data_variables[var]['peptide_counts']), chunk_size)
                    ]

                    self.filtered_data_variables[var]['ms_data_chunks'] = [
                        self.filtered_data_variables[var]['ms_data'][i:i + chunk_size]
                        for i in range(0, len(self.filtered_data_variables[var]['ms_data']), chunk_size)
                    ]
                    self.filtered_data_variables[var]['ms_data_list'] = list(
                        self.filtered_data_variables[var]['ms_data'])
                    self.filtered_data_variables[var]['AA_list'] = df['AA'].tolist()

                    columns_to_include = df.columns.difference(['AA', 'COUNT'])
                    df_filtered = df[columns_to_include]

                    self.filtered_data_variables[var]['bioactive_peptide_abs_df'] = df_filtered
                    self.filtered_data_variables[var]['bioactive_peptide_chunks'] = self.chunk_dataframe(df_filtered,
                                                                                                         chunk_size=chunk_size)
                    self.filtered_data_variables[var]['bioactive_function_chunks'] = self.chunk_dataframe(df_func,
                                                                                                          chunk_size=chunk_size)
                    self.filtered_data_variables[var]['bioactive_peptide_func_df'] = df_func
                    protein_id_list.append(self.filtered_data_variables[var]['protein_id'])
                    protein_name_list.append(self.filtered_data_variables[var]['protein_name'])

                    print(f"All data structures for {var} have been created successfully.")

                except Exception as e:
                    display(HTML(f'<span style="color:red;">Error processing data for {var}: {e}</span>'))
            else:
                display(HTML(f'<span style="color:red;">{var} DataFrame is not loaded or does not exist.</span>'))

        user_protein_id_set = list(set(protein_id_list))
        user_protein_name_set = list(set(protein_name_list))

        if len(user_protein_id_set) > 1 and len(user_protein_name_set) == 1:
            self.user_protein_id = '_'.join(user_protein_id_set)
            self.protein_name_short = user_protein_name_set[0]

        elif len(user_protein_id_set) > 1 and len(user_protein_name_set) > 1:
            self.user_protein_id = '_'.join(user_protein_id_set)
            self.protein_name_short = '_'.join(user_protein_name_set)

        elif len(user_protein_name_set) == 1:
            self.user_protein_id = user_protein_id_set[0]
            self.protein_name_short = user_protein_name_set[0]

        self.available_data_variables = self.filtered_data_variables.copy()
    # Function to create order input widgets
    def create_order_input_widgets(self):
        """
        Create widgets to update the order of labels.
        """
        description_layout_invisible = widgets.Layout(width='400px')

        self.label_widgets = {}
        self.order_widgets = {}
        for i, (var, info) in enumerate(self.available_data_variables.items()):
            self.label_widgets[var] = widgets.Text(
                value=info['label'],
                description='',
                layout=widgets.Layout(width='150px')
            )
            self.order_widgets[var] = widgets.IntText(
                value=i,
                description='',
                layout=description_layout_invisible,
            )
        # Optionally, you can return the widgets if needed
        # return self.label_widgets, self.order_widgets

    # Function to create widgets
    def create_widgets(self):
        # Create widgets for protein selection
        self.protein_dropdown = widgets.Dropdown(
            options=[("Select Protein", None)] + [
                (
                f"{protein} - {self.proteins_dic.get(protein, {'name': 'Unknown', 'species': 'Unknown'})['species']} - {self.proteins_dic.get(protein, {'name': 'Unknown'})['name']}",
                protein)
                for protein in list(self.available_proteins)
            ],
            description='Protein ID:',
            layout=widgets.Layout(width='35%')
        )

        self.grouping_variable_text = widgets.Text(
            description='Search Term',
            layout=widgets.Layout(width='35%')
        )

        self.search_button = widgets.Button(
            description='Search',
            button_style='info',
            layout=widgets.Layout(margin='10px 10px 0 0')
        )

        self.var_key_dropdown = widgets.SelectMultiple(
            description='Groups',
            disabled=False,
            layout=widgets.Layout(width='35%', height='100px')
        )

        self.add_group_button = widgets.Button(
            description='Add Group',
            button_style='success',
            layout=widgets.Layout(margin='10px 10px 0 0')
        )

        self.reset_button = widgets.Button(
            description='Reset Selection',
            button_style='warning',
            layout=widgets.Layout(margin='10px 10px 0 75px')
        )

        self.var_selection_output = widgets.Output()

        # Set widget events
        self.protein_dropdown.observe(self.update_var_keys, names='value')
        self.search_button.on_click(self.search_var_keys)
        self.add_group_button.on_click(self.add_group)
        self.reset_button.on_click(self.reset_selection)

        # Layout for buttons
        self.button_row = widgets.HBox([self.search_button, self.add_group_button])
        self.reset_row = widgets.HBox([self.reset_button])
        self.button_box = widgets.VBox([self.button_row, self.reset_row])

    # Function to update var_key_dropdown based on selected protein
    def update_var_keys(self, change):
        selected_protein = change['new']
        current_selection = set(self.var_key_dropdown.value)

        new_options = []
        if selected_protein in self.available_grouping_vars:
            new_options = [f"{var}" for var in self.available_grouping_vars[selected_protein]]

        self.var_key_dropdown.options = sorted(set(self.var_key_dropdown.options).union(new_options))
        self.var_key_dropdown.value = tuple(current_selection.intersection(self.var_key_dropdown.options))

    # Function to search and filter var_keys based on the grouping variable text input
    def search_var_keys(self, b):
        group_name = self.grouping_variable_text.value
        if group_name:
            matching_keys = [key for key in self.var_key_dropdown.options if group_name in key]
            self.var_key_dropdown.value = matching_keys
        else:
            with self.var_selection_output:
                self.var_selection_output.clear_output()
                display(HTML('<b style="color:red;">Please enter a group name to search.</b>'))

    # Function to add a group of selected var_keys to the list
    def add_group(self, b):
        selected_protein = self.protein_dropdown.value
        selected_keys = list(self.var_key_dropdown.value)

        if selected_keys and selected_protein:
            combined_keys = [f"{selected_protein}_{key}" for key in selected_keys]
            self.selected_var_keys_list.extend(combined_keys)
            self.selected_var_keys_list = list(set(self.selected_var_keys_list))  # Ensure no duplicates

            with self.var_selection_output:
                self.var_selection_output.clear_output()
                #display(HTML("<hr style='border: 1px solid black;'>"))
                display(HTML(f"<b>{len(combined_keys)} variables added.</b>"))
                display(HTML(f"<b>Selected variables:</b> {', '.join(combined_keys)}"))
                display(HTML(f"<b>Total unique variables:</b> {len(self.selected_var_keys_list)}"))
                display(HTML(f"<b>All unique variables:</b> {', '.join(self.selected_var_keys_list)}"))

            self.grouping_variable_text.value = ''
            self.filtered_data_variables = self.create_filtered_data_variables()
            # Process data variables
            self.process_data_variables()
            # Create label and order widgets
            self.create_order_input_widgets()
            self.default_label_values = {key: self.label_widgets[key].value for key in self.label_widgets}
            self.default_order_values = [info['label'] for info in self.available_data_variables.values()]
            self.display_label_order_widgets()

        else:
            with self.var_selection_output:
                self.var_selection_output.clear_output()
                display(HTML('<b style="color:red;">Please select a protein and at least one key.</b>'))

    # Function to reset the selection
    def reset_selection(self, b):
        self.selected_var_keys_list.clear()
        self.protein_dropdown.value = None
        self.var_key_dropdown.options = []
        self.grouping_variable_text.value = ''

        self.filtered_data_variables = {}
        self.available_data_variables = {}
        self.label_widgets = {}
        self.order_widgets = {}
        self.default_label_values = {}
        self.default_order_values = []

        with self.var_selection_output:
            self.var_selection_output.clear_output()
            display(HTML('<b style="color:green;">Selection has been reset.</b>'))

        # Clear the label_order_output as well
        self.label_order_output.clear_output()

    # Function to create a filtered dictionary based on selected_var_keys_list
    def create_filtered_data_variables(self):
        return {key: self.data_variables[key] for key in self.selected_var_keys_list if key in self.data_variables}

    # Function to display messages in the output widget
    def display_message(self, message, is_error=False):
        with self.message_output:
            self.message_output.clear_output()  # Clear previous messages
            if is_error:
                display(HTML(f"<b style='color:red;'>{message}</b>"))  # Error message in red
            else:
                display(HTML(f"<b style='color:green;'>{message}</b>"))  # Success message in green

    # Function to update order based on new order input
    def update_order(self, order_labels):
        """
        Update the order of labels in self.available_data_variables based on the input order_labels.
        The structure of available_data_variables will be preserved, and we will reorder the labels for display purposes.
        """
        vars_list = list(self.available_data_variables.keys())
        labels_list = [info['label'] for info in self.available_data_variables.values()]

        # Check if the provided labels match the available labels
        if len(order_labels) != len(labels_list):
            raise ValueError("Number of labels provided does not match the number of items to reorder.")

        # Check for duplicates in order_labels
        if len(order_labels) != len(set(order_labels)):
            raise ValueError("Duplicate labels found in order_labels. Please provide unique labels.")

        # **New Check**: Check for duplicates in available labels
        if len(labels_list) != len(set(labels_list)):
            raise ValueError("Duplicate labels found in available data variables. Cannot reorder unambiguously.")

        # Ensure all provided labels exist in available_data_variables
        if not all(label in labels_list for label in order_labels):
            raise ValueError("One or more provided labels are invalid.")

        # Build a mapping from label to variable key
        label_to_var = {info['label']: var for var, info in self.available_data_variables.items()}

        # Reorder available_data_variables based on the new order of labels
        ordered_available_data_variables = {
            label_to_var[label]: self.available_data_variables[label_to_var[label]] for label in order_labels
        }

        # Update self.available_data_variables
        self.available_data_variables = ordered_available_data_variables

        # Optionally, return the reordered dictionary
        # return self.available_data_variables

    # Event handler for updating labels
    def on_update_label_click(self, b):
        try:
            self.update_labels()
            self.display_message("Labels updated successfully.")
        except Exception as e:
            self.display_message(f"Error updating labels: {e}", is_error=True)

    # Event handler for updating order
    def on_update_order_click(self, b):
        # Split the entered label string and strip spaces
        order_list = [label.strip() for label in self.new_order_input.value.split(',')]
        try:
            # Update order based on the label input
            self.update_order(order_list)
            self.display_message("Order updated successfully.")
        except Exception as e:
            self.display_message(f"Error updating order: {e}", is_error=True)

    # Event handler for resetting labels and order
    def on_reset_click(self, b):
        try:
            # Reset each label widget to its default value
            for key in self.label_widgets:
                self.label_widgets[key].value = self.default_label_values[key]

            # Reset the order widget to its default value
            self.new_order_input.value = ', '.join(self.default_order_values)

            # Apply the default labels and order
            self.on_update_label_click(b)
            self.on_update_order_click(b)

            self.display_message("Labels and order reset to default.")
        except Exception as e:
            self.display_message(f"Error resetting labels and order: {e}", is_error=True)

    # Function to display label and order widgets
    def display_label_order_widgets(self):
        # Clear the output area
        self.label_order_output.clear_output()
        with self.label_order_output:
            # Output widget for displaying messages
            self.message_output = widgets.Output()

            # Header for the columns
            display(HTML(f"<h3><u>Update Sample Labels & Order (Optional)</u></h3>"))

            # Display update labels section
            display(widgets.HTML(value="<p><b>Update Labels:</b></p>"))
            for i, (var, info) in enumerate(self.available_data_variables.items()):
                display(widgets.HBox([
                    widgets.Label(
                        value=f"{i + 1})  {info['label']}  -  {info.get('protein_species', '')}  -  {info.get('protein_name', '')}",
                        layout=widgets.Layout(width='400px')
                    ),
                    self.label_widgets[var]
                ]))

            # Label above the text input box
            label_above_input = widgets.HTML(
                value="<p><b>Re-order Samples:</b><br>Enter labels in desired order separated by commas (e.g., label_1, label_2, label_3)</p>")

            # Extract labels from available_data_variables for display
            label_list = [info['label'] for info in self.available_data_variables.values()]

            # Text input for new order
            self.new_order_input = widgets.Textarea(
                value=', '.join(label_list),
                layout=widgets.Layout(width='450px', height='60px')
            )

            # Display the label and text input
            display(widgets.VBox([label_above_input, self.new_order_input]))

            # Create buttons
            self.update_label_button = widgets.Button(
                description="Update Labels",
                button_style='success',
                layout=widgets.Layout(width='250px', height='30px')
            )
            self.update_order_button = widgets.Button(
                description="Update Order",
                button_style='success',
                layout=widgets.Layout(width='250px', height='30px')
            )
            self.reset_labelorder_button = widgets.Button(
                description="Reset to Default",
                button_style='warning',
                layout=widgets.Layout(width='250px', height='30px', margin='10px 10px 0 75px')
            )

            # Attach click event handlers
            self.update_label_button.on_click(self.on_update_label_click)
            self.update_order_button.on_click(self.on_update_order_click)
            self.reset_labelorder_button.on_click(self.on_reset_click)

            # Display buttons
            button_box = widgets.HBox([self.update_label_button, self.update_order_button])
            vert_button_box = widgets.VBox([button_box, self.reset_labelorder_button, self.message_output])
            display(vert_button_box)

    def update_labels(self):
        # Update labels in available_data_variables based on label_widgets
        for key in self.available_data_variables:
            self.available_data_variables[key]['label'] = self.label_widgets[key].value

    # Function to display the initial selection widgets
    def display_widgets(self):
        display(HTML("<h3><u>Select Protein and Grouping Variables:</u></h3>"))
        display(self.protein_dropdown)
        display(self.grouping_variable_text)
        display(self.var_key_dropdown)
        display(self.button_box)
        display(self.var_selection_output)

    # Function to handle updates

    # Function to handle updates


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

    def on_selection_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            self.bio_or_pep = self.bio_or_pep_dropdown.value

            # Initialize containers for unique values
            unique_functions = set()
            unique_peptides = set()

            # Aggregate unique functions and peptides from available data
            for var in self.available_data_variables:
                df = self.available_data_variables[var]['bioactive_peptide_func_df']
                df.replace('0', 0, inplace=True)  # Standardize zero representations
                unique_functions.update(self.extract_non_zero_non_nan_values(df))

                abs_df = self.available_data_variables[var]['bioactive_peptide_abs_df']
                unique_peptides.update(col for col in abs_df.columns if col not in ['AA', 'count', 'average'])

            # Convert sets to sorted lists for widget options
            unique_peptides_list = sorted(list(unique_peptides))
            unique_functions_list = sorted(list(unique_functions))

            # Update widget based on dropdown choice
            if self.bio_or_pep == '1':  # Peptide Intervals
                self.specific_select_multiple.options = [(peptide, peptide) for peptide in unique_peptides_list]
                self.specific_select_multiple.layout.display = 'block'
            elif self.bio_or_pep == '2':  # Bioactive Functions
                self.specific_select_multiple.options = [(function, function) for function in unique_functions_list]
                self.specific_select_multiple.layout.display = 'block'
            else:
                self.specific_select_multiple.options = [""]
                self.specific_select_multiple.layout.display = 'none'
    # Function to display plotting options
    """def display_plotting_options(self):
        self.ms_average_choice_dropdown = widgets.Dropdown(
            options=['yes', 'no'],
            description='Plot Averaged Data:',
            disabled=False,
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='50%')
        )
        self.bio_or_pep_dropdown = widgets.Dropdown(
            options=[('None', 'no'), ('Peptide Intervals', '1'), ('Bioactive Functions', '2')],
            description='Plot Specific Peptides:',
            disabled=False,
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='50%')
        )
        self.specific_select_multiple = widgets.SelectMultiple(
            options=[],
            description='Specific Options:',
            disabled=False,
            layout=widgets.Layout(display='none')  # Start hidden
        )

        # Attach the observer only to bio_or_pep_dropdown
        self.bio_or_pep_dropdown.observe(
            lambda change: self.on_selection_change(change),
            names='value'
        )

        # Attach observer functions to other widgets
        self.ms_average_choice_dropdown.observe(self.on_dropdown_change, names='value')
        self.specific_select_multiple.observe(self.on_dropdown_change, names='value')

        # Display the widgets
        display(HTML(f"<br><h3><u>Select Line Plot Options</u></h3>"))
        display(self.ms_average_choice_dropdown)
        display(self.bio_or_pep_dropdown)
        display(self.specific_select_multiple)
        """
    """
    def generate_additional_vars_str(self):
        additional_vars = []

        if self.plot_heatmap == 'yes':
            additional_vars.append('heatmap')
        elif self.plot_heatmap == 'no':
            additional_vars.append('no-heatmap')

        if self.bio_or_pep == '1':
            additional_vars.append('intervals')
        elif self.bio_or_pep == '2':
            additional_vars.append('bioactive-functions')
        elif self.bio_or_pep == 'no':
            additional_vars.append('averages-only')

        # Join the additional_vars list into a single string with underscores
        additional_vars_str = '_'.join(additional_vars)
        return additional_vars_str

    def generate_filenames(self):
        additional_vars_str = self.generate_additional_vars_str()
        xaxis_label = f"{self.protein_name_short.replace('_', ' ')} Sequence"
        yaxis_label = 'Averaged Peptide Abundance'

        protein_filename_short = re.sub(r'[^\w-]', '-', self.protein_name_short)
        display_filename_port = f'portrait_{self.user_protein_id}_{protein_filename_short}_average-only'
        display_filename_land = f'landscape_{self.user_protein_id}_{protein_filename_short}_{additional_vars_str}'

        return display_filename_port, display_filename_land, xaxis_label, yaxis_label

    def create_plotting_widgets(self):
        # Ensure required attributes are available
        if not hasattr(self, 'user_protein_id') or not hasattr(self, 'protein_name_short'):
            # You may need to set these attributes before calling this method
            raise ValueError("user_protein_id and protein_name_short must be set before creating plotting widgets.")

        # Generate filenames
        display_filename_port, display_filename_land, xaxis_label, yaxis_label = self.generate_filenames()

        # Layout configurations
        description_layout_invisible = widgets.Layout(width='400px')
        description_layout = widgets.Layout(width='400px')
        dropdown_layout = widgets.Layout(width='200px')
        dropdown_layout_large = widgets.Layout(width='400px')

        # Color Widgets
        self.hm_selected_color = widgets.Dropdown(
            options=get_valid_gradient_colormaps(),
            value=default_hm_color,
            description='Heatmap:',
            layout=dropdown_layout,
            style={'description_width': 'initial'}
        )

        self.lp_selected_color = widgets.Dropdown(
            options=get_valid_discretecolormaps(),
            value=default_lp_color,
            description='Line Plot:',
            layout=dropdown_layout,
            style={'description_width': 'initial'}
        )

        self.avglp_selected_color = widgets.Dropdown(
            options=valid_discrete_cmaps,
            value=default_avglp_color,
            description='Avg Line Plot:',
            layout=dropdown_layout,
            style={'description_width': 'initial'}
        )

        color_message = widgets.HTML("<h3><u>Color Options:</u></h3>")

        self.color_widget_box = widgets.VBox([
            color_message,
            self.hm_selected_color,
            self.lp_selected_color,
            self.avglp_selected_color
        ])

        # Figure Label Widgets
        self.xaxis_label_input = widgets.Text(
            value=f"{self.protein_name_short} Sequence",
            description='x-axis label:',
            layout=description_layout,
            style={'description_width': 'initial'}
        )

        self.yaxis_label_input = widgets.Text(
            value="Averaged Peptide Abundance",
            description='y-axis label:',
            layout=description_layout,
            style={'description_width': 'initial'}
        )

        self.yaxis_position = widgets.IntSlider(
            value=0,
            min=-10,
            max=10,
            step=1,
            layout=description_layout,
            description='y-axis title position:',
            style={'description_width': 'initial'}
        )

        # Legend Titles
        self.legend_title_input_2 = widgets.Text(
            value=self.legend_title[1],
            description=f'Legend title ({self.legend_title[1]}):',
            layout=description_layout,
            style={'description_width': 'initial'}
        )

        # Conditional Logic for Legend Titles
        if self.ms_average_choice == 'yes' and self.bio_or_pep == '1':
            # ... initialize legend_title_input_1, legend_title_input_3, legend_title_input_4, legend_title_input_5 ...
            pass  # Replace with your adjusted code using self.
        elif self.ms_average_choice == 'yes' and self.bio_or_pep == '2':
            # ... initialize widgets accordingly ...
            pass
        elif self.ms_average_choice == 'yes' and self.bio_or_pep == 'no':
            # ... initialize widgets accordingly ...
            pass
        elif self.ms_average_choice == 'no' and self.bio_or_pep == '1':
            # ... initialize widgets accordingly ...
            pass
        elif self.ms_average_choice == 'no' and self.bio_or_pep == '2':
            # ... initialize widgets accordingly ...
            pass

        # Figure Label Box
        figure_label_message = widgets.HTML("<h3><u>Figure Label Options:</u></h3>")

        self.figure_label_box = widgets.VBox([
            figure_label_message,
            self.xaxis_label_input,
            self.yaxis_label_input,
            self.yaxis_position,
            self.legend_title_input_1,
            self.legend_title_input_2,
            self.legend_title_input_3,
            self.legend_title_input_4,
            self.legend_title_input_5
        ])

        # Plot Widgets
        create_plot_message = widgets.HTML("<h3><u>Create Plot Checkboxes:</u></h3>")

        self.plot_port = widgets.ToggleButton(
            value=True,
            description='Portrait Plot',
            disabled=False,
            button_style='',
            tooltip='Show updated plot',
            icon='check'
        )

        self.plot_land = widgets.ToggleButton(
            value=True,
            description='Landscape Plot',
            disabled=False,
            button_style='',
            tooltip='Show updated plot',
            icon='check'
        )

        plot_toggle_buttons = widgets.HBox([
            self.plot_port,
            self.plot_land
        ])

        filename_label_message = widgets.HTML("<h3><u>Save As Options</u></h3>")

        self.filename_port_input = widgets.Text(
            value=display_filename_port,
            description='Filename (Portrait):',
            layout=dropdown_layout_large,
            style={'description_width': 'initial'}
        )

        self.filename_land_input = widgets.Text(
            value=display_filename_land,
            description='Filename (Landscape):',
            layout=dropdown_layout_large,
            style={'description_width': 'initial'}
        )

        self.plot_widget_box = widgets.VBox([
            create_plot_message,
            plot_toggle_buttons,
            filename_label_message,
            self.filename_port_input,
            self.filename_land_input
        ])

        # Buttons for Update and Save Plot
        self.update_button = widgets.Button(
            description='Show/Update Plot',
            button_style='success',
            tooltip='Click to update the plot',
            icon='refresh'
        )

        self.save_button = widgets.Button(
            description='Save Plot',
            button_style='info',
            tooltip='Click to save the plot',
            icon='save'
        )

        self.button_box = widgets.HBox([self.update_button, self.save_button])

        # Display the widgets
        display(self.color_widget_box)
        display(self.figure_label_box)
        display(self.plot_widget_box)
        display(self.button_box)
    """


def load_complex_dict(base_filename):
    """
    Recursively load the complex dictionary from a base directory.

    Parameters:
    - base_filename (str): The base directory containing the data and metadata.json.

    Returns:
    - result (dict): The loaded complex dictionary.
    """
    with open(os.path.join(base_filename, 'metadata.json'), 'r') as f:
        metadata = json.load(f)

    result = {}
    for key, info in metadata.items():
        if info['type'] == 'nested':
            # Recursively load nested dictionaries
            result[key] = load_complex_dict(os.path.join(base_filename, info['path']))
        elif info['type'] == 'dataframe':
            # Load DataFrame from CSV
            result[key] = pd.read_csv(os.path.join(base_filename, info['filename']))
        elif info['type'] == 'direct':
            # Load direct value from metadata
            result[key] = info['value']

    return result


def extract_and_format_data(base_filename):
    """
    Extract and format data from the loaded complex dictionary.

    Parameters:
    - base_filename (str): Path to the directory containing the saved complex dictionary.

    Returns:
    - data_variables (dict): A dictionary with structured information, using a combination
      of protein_id and grouping_var_name as the key.
    """
    # Load the data from the saved directory
    loaded_data = load_complex_dict(base_filename)

    # Initialize the new dictionary
    data_variables = {}

    # Iterate over the loaded data to extract and reorganize it
    for protein_id, protein_data in loaded_data.items():
        protein_sequence = protein_data.get('protein_sequence')

        for grouping_var_name, group_info in protein_data.items():
            # Extract the required DataFrames and other information
            func_df = group_info.get('func_heatmap_df')
            abs_df = group_info.get('heatmap_df')
            label = grouping_var_name
            protein_sequence = group_info.get('protein_sequence')
            protein_name = group_info.get('protein_name')
            protein_species = group_info.get('protein_species')

            # Determine if the func_df is all None
            is_func_df_all_none = func_df.isnull().all().all() if func_df is not None else True

            # Create a unique key combining protein_id and grouping_var_name
            var_key = f"{protein_id}_{grouping_var_name}"

            # Populate the data_variables dictionary using the unique key
            data_variables[var_key] = {
                'protein_id': protein_id,
                'protein_sequence': protein_sequence,
                'protein_name': protein_name,
                'protein_species': protein_species,
                'heatmap_df': abs_df,
                'function_heatmap_df': func_df,
                'label': label,
                'is_func_df_all_none': is_func_df_all_none
            }

    return data_variables


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
        print(f"Unexpected value for bio_or_pep: {bio_or_pep}")

    return selected_peptides, selected_functions


def on_selection_change(change, ms_average_choice_dropdown, bio_or_pep_dropdown, specific_select_multiple,
                        available_data_variables):
    if change['type'] == 'change' and change['name'] == 'value':
        bio_or_pep = bio_or_pep_dropdown.value

        # Initialize containers for unique values
        unique_functions = set()
        unique_peptides = set()

        # Aggregate unique functions and peptides from available data
        for var in available_data_variables:
            df = available_data_variables[var]['bioactive_peptide_func_df']
            df.replace('0', 0, inplace=True)  # Standardize zero representations
            unique_functions.update(extract_non_zero_non_nan_values(df))

            abs_df = available_data_variables[var]['bioactive_peptide_abs_df']
            unique_peptides.update(col for col in abs_df.columns if col not in ['AA', 'count', 'average'])

        # Convert sets to sorted lists for widget options
        unique_peptides_list = sorted(list(unique_peptides))
        unique_functions_list = sorted(list(unique_functions))

        # Update widget based on dropdown choice
        if bio_or_pep == '1':  # Peptide Intervals
            specific_select_multiple.options = [(peptide, peptide) for peptide in unique_peptides_list]
            specific_select_multiple.layout.display = 'block'
        elif bio_or_pep == '2':  # Bioactive Functions
            specific_select_multiple.options = [(function, function) for function in unique_functions_list]
            specific_select_multiple.layout.display = 'block'
        else:
            specific_select_multiple.options = [""]
            specific_select_multiple.layout.display = 'none'

"""
def display_plotting_options(available_data_variables):
    ms_average_choice_dropdown = widgets.Dropdown(
        options=['yes', 'no'],
        description='Plot Averaged Data:',
        disabled=False,
        style={'description_width': 'initial'},
        layout=widgets.Layout(width='50%')
    )
    bio_or_pep_dropdown = widgets.Dropdown(
        options=[('None', 'no'), ('Peptide Intervals', '1'), ('Bioactive Functions', '2')],
        description='Plot Specific Peptides:',
        disabled=False,
        style={'description_width': 'initial'},
        layout=widgets.Layout(width='50%')
    )
    specific_select_multiple = widgets.SelectMultiple(
        options=[],
        description='Specific Options:',
        disabled=False,
        layout=widgets.Layout(display='none')  # Start hidden
    )

    # Attach the observer only to bio_or_pep_dropdown
    bio_or_pep_dropdown.observe(
        lambda change: on_selection_change(change, ms_average_choice_dropdown, bio_or_pep_dropdown,
                                           specific_select_multiple, available_data_variables),
        names='value'
    )

    return ms_average_choice_dropdown, bio_or_pep_dropdown, specific_select_multiple
"""

# Update plot function
def update_plot(available_data_variables, ms_average_choice, bio_or_pep, selected_peptides, selected_functions,
                hm_selected_color, lp_selected_color, avglp_selected_color,
                xaxis_label, yaxis_label, yaxis_position, legend_title_input_1, legend_title_input_2,
                legend_title_input_3, legend_title_input_4, legend_title_input_5, plot_land, plot_port, filename_port,
                filename_land, save_fig):
    result = process_available_data(available_data_variables)

    # Unpack the dictionary into individual global variables
    global list_of_counts, min_values, max_values, seq_len_list, max_sequence_length, y_ticks_html, max_count, num_unique_count, num_colors, total_plots, style_map
    import _settings as settings
    if result:
        lineplot_height, scale_factor = settings.port_hm_settings.get(len(available_data_variables), (20, 0.1))
        list_of_counts = result['list_of_counts']
        min_values = result['min_values']
        max_values = result['max_values']
        seq_len_list = result['seq_len_list']
        max_sequence_length = result['max_sequence_length']
        y_ticks_html = result['y_ticks_html']
        max_count = result['max_count']
        num_unique_count = result['num_unique_count']
        num_colors = result['num_colors']
        total_plots = result['total_plots']
        style_map = result['style_map']

        yaxis_position_land = yaxis_position_port = 0.0 - 0.01 * yaxis_position
        legend_title = [legend_title_input_1, legend_title_input_2, legend_title_input_3, legend_title_input_4,
                        legend_title_input_5]

        # Your plotting code here, using the widget values as inputs

        cmap = plt.get_cmap(hm_selected_color)
        avg_cmap = plt.get_cmap(avglp_selected_color)
        figs = []  # To store figures

        if ms_average_choice == 'no' and bio_or_pep == 'no':
            display(HTML(f'<br><b>Reslect "Ploting Options", no data is available for plotting.</b><br><br>'))
        else:
            """ #                                       Function Call to Generate Plot
            #---------------------------------------------------------------------------------------------------------------------------------------------
            """
            if plot_port:
                # Temporarily suppress specific warning
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    if ms_average_choice == 'yes':
                        display(HTML(f'<br><h2>Portrait Averaged Plot:</h2>'))
                        fig_port = visualize_sequence_heatmap_portrait(
                            available_data_variables,
                            0.001,
                            # amino_acid_height - positional because it follows the order defined in the function
                            lineplot_height,  # lineplot_height - positional
                            1,  # indices_height - positional
                            filename_port,  # filename - positional
                            xaxis_label,  # xaxis_label - positional
                            yaxis_label,  # yaxis_label - positional
                            legend_title,  # legend_title - positiona
                            yaxis_position_port,  # yaxis_position - positional
                            cmap,
                            avg_cmap,
                            lp_selected_color,
                            avglp_selected_color,
                            selected_functions,
                            ms_average_choice,
                            bio_or_pep,
                            save_fig,
                            chunk_size=78)
                    else:
                        display(HTML(
                            f'<br><b>No was selected earlier regarding the plotting of averaged absorbances, preventing the plotting of the averaged plot.</b><br><br>'))
                    if max_count <= 1:
                        display(
                            HTML(f"<br><br><p><strong>You have to few peptides for proper heatmapping.</strong></p>"))

            """_____________________________________________________EXECUTING CODE TO PLOT W/ UPDATES_________________________________________________________________"""

            # Plotting code
            if plot_land:
                amino_acid_height = 0.25 + 0.1 * (
                    len(available_data_variables) // 4 if len(available_data_variables) >= 8 else 0)
                indices_height = amino_acid_height + 0.08
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    display(HTML(f'<br><h2>Landscape Averaged Plot:</h2>'))
                    fig_land = visualize_sequence_heatmap_lanscape(
                        available_data_variables,
                        amino_acid_height,
                        7.5,
                        indices_height,
                        filename_land,
                        xaxis_label,
                        yaxis_label,
                        legend_title,
                        yaxis_position_land,
                        cmap,
                        avg_cmap,
                        lp_selected_color,
                        avglp_selected_color,
                        selected_peptides,
                        selected_functions,
                        ms_average_choice,
                        bio_or_pep,
                        save_fig)

                if max_count <= 1:
                    display(HTML(f"<br><br><p><strong>You have too few peptides for proper heatmapping.</strong></p>"))

            if plot_port:
                # Create a new figure for the portrait plot
                fig_port = plt.figure()
                figs.append(fig_port)

            if plot_land:
                # Create a new figure for the landscape plot
                fig_land = plt.figure()
                figs.append(fig_land)
        return figs  # Return the list of figures
    else:
        display(HTML(f'<br><b>Reslect "Variable Options", no data is available for plotting.</b><br><br>'))



# List of valid gradient colormaps
def get_valid_gradient_colormaps():
    return settings.valid_gradient_cmaps


# List of valid discrete colormaps
def get_valid_discretecolormaps():
    return settings.valid_discrete_cmaps


# Function to create and return all widgets in a structured layout
"""
def create_plotting_widgets(user_protein_id, ms_average_choice, bio_or_pep, legend_title, protein_name_short):
    display_filename_port, display_filename_land, xaxis_label, yaxis_label = generate_filenames(user_protein_id,
                                                                                                protein_name_short,
                                                                                                bio_or_pep,
                                                                                                legend_title)

    description_layout_invisible = widgets.Layout(width='400px')
    description_layout = widgets.Layout(width='400px')
    dropdown_layout = widgets.Layout(width='200px')
    dropdown_layout_large = widgets.Layout(width='400px')
    # Color Widgets
    hm_selected_color = widgets.Dropdown(
        options=get_valid_gradient_colormaps(),
        value=default_hm_color,
        description='Heatmap:',
        layout=dropdown_layout,
        style={'description_width': 'initial'}
    )

    lp_selected_color = widgets.Dropdown(
        options=get_valid_discretecolormaps(),
        value=default_lp_color,
        description='Line Plot:',
        layout=dropdown_layout,
        style={'description_width': 'initial'}
    )

    avglp_selected_color = widgets.Dropdown(
        options=valid_discrete_cmaps,
        value=default_avglp_color,
        description='Avg Line Plot:',
        layout=dropdown_layout,
        style={'description_width': 'initial'}
    )

    color_message = widgets.HTML("<h3><u>Color Options:</u></h3>")

    color_widget_box = widgets.VBox([
        color_message,
        hm_selected_color,
        lp_selected_color,
        avglp_selected_color
    ])

    # Figure Label Widgets
    xaxis_label_input = widgets.Text(
        value=f"{protein_name_short} Sequence",
        description='x-axis label:',
        layout=description_layout,
        style={'description_width': 'initial'}
    )

    yaxis_label_input = widgets.Text(
        value="Averaged Peptide Abundance",
        description='y-axis label:',
        layout=description_layout,
        style={'description_width': 'initial'}
    )

    yaxis_position = widgets.IntSlider(
        value=0,
        min=-10,
        max=10,
        step=1,
        layout=description_layout,
        description='y-axis title position:',
        style={'description_width': 'initial'}
    )
    legend_title_input_2 = widgets.Text(value=legend_title[1], description=f'Legend title ({legend_title[1]}):',
                                        layout=description_layout,
                                        style={'description_width': 'initial'})  #  'Peptide Counts:',

    if ms_average_choice == 'yes' and bio_or_pep == '1':
        legend_title_input_1 = widgets.Text(value=legend_title[0], description=f'Legend title ({legend_title[0]}):',
                                            layout=description_layout,
                                            style={'description_width': 'initial'})  # 'Sample Type:'
        legend_title_input_3 = widgets.Text(value=legend_title[2], description=f'Legend title ({legend_title[2]}):',
                                            layout=description_layout_invisible,
                                            style={'description_width': 'initial'})  # 'Bioactivity Function:',
        legend_title_input_3.layout.display = 'none'
        legend_title_input_4 = widgets.Text(value=legend_title[3], description=f'Legend title ({legend_title[3]}):',
                                            layout=description_layout,
                                            style={'description_width': 'initial'})  # 'Peptide Interval:',
        legend_title_input_5 = widgets.Text(value=legend_title[4], description=f'Legend title ({legend_title[4]}):',
                                            layout=description_layout,
                                            style={'description_width': 'initial'})  # 'Average Absorbance:'

    if ms_average_choice == 'yes' and bio_or_pep == '2':
        legend_title_input_1 = widgets.Text(value=legend_title[0], description=f'Legend title ({legend_title[0]}):',
                                            layout=description_layout,
                                            style={'description_width': 'initial'})  # 'Sample Type:'
        legend_title_input_3 = widgets.Text(value=legend_title[2], description=f'Legend title ({legend_title[2]}):',
                                            layout=description_layout,
                                            style={'description_width': 'initial'})  # 'Bioactivity Function:',
        legend_title_input_4 = widgets.Text(value=legend_title[3], description=f'Legend title ({legend_title[3]}):',
                                            layout=description_layout_invisible,
                                            style={'description_width': 'initial'})  # 'Peptide Interval:',
        legend_title_input_4.layout.display = 'none'
        legend_title_input_5 = widgets.Text(value=legend_title[4], description=f'Legend title ({legend_title[4]}):',
                                            layout=description_layout,
                                            style={'description_width': 'initial'})  # 'Average Absorbance:'

    if ms_average_choice == 'yes' and bio_or_pep == 'no':
        legend_title_input_1 = widgets.Text(value=legend_title[0], description=f'Legend title ({legend_title[0]}):',
                                            layout=description_layout,
                                            style={'description_width': 'initial'})  # 'Sample Type:'
        legend_title_input_3 = widgets.Text(value=legend_title[2], description=f'Legend title ({legend_title[2]}):',
                                            layout=description_layout_invisible,
                                            style={'description_width': 'initial'})  # 'Bioactivity Function:',
        legend_title_input_3.layout.display = 'none'
        legend_title_input_4 = widgets.Text(value=legend_title[3], description=f'Legend title ({legend_title[3]}):',
                                            layout=description_layout_invisible,
                                            style={'description_width': 'initial'})  # 'Peptide Interval:',
        legend_title_input_4.layout.display = 'none'
        legend_title_input_5 = widgets.Text(value=legend_title[4], description=f'Legend title ({legend_title[4]}):',
                                            layout=description_layout,
                                            style={'description_width': 'initial'})  # 'Average Absorbance:'

    if ms_average_choice == 'no' and bio_or_pep == '1':
        legend_title_input_1 = widgets.Text(value=legend_title[0], description=f'Legend title ({legend_title[0]}):',
                                            layout=description_layout,
                                            style={'description_width': 'initial'})  # 'Sample Type:'
        legend_title_input_3 = widgets.Text(value=legend_title[2], description=f'Legend title ({legend_title[2]}):',
                                            layout=description_layout_invisible,
                                            style={'description_width': 'initial'})  # 'Bioactivity Function:',
        legend_title_input_3.layout.display = 'none'
        legend_title_input_4 = widgets.Text(value=legend_title[3], description=f'Legend title ({legend_title[3]}):',
                                            layout=description_layout,
                                            style={'description_width': 'initial'})  # 'Peptide Interval:',
        legend_title_input_5 = widgets.Text(value=legend_title[4], description=f'Legend title ({legend_title[4]}):',
                                            layout=description_layout_invisible,
                                            style={'description_width': 'initial'})  # 'Average Absorbance:'
        legend_title_input_5.layout.display = 'none'

    if ms_average_choice == 'no' and bio_or_pep == '2':
        legend_title_input_1 = widgets.Text(value=legend_title[0], description=f'Legend title ({legend_title[0]}):',
                                            layout=description_layout,
                                            style={'description_width': 'initial'})  # 'Sample Type:'
        legend_title_input_3 = widgets.Text(value=legend_title[2], description=f'Legend title ({legend_title[2]}):',
                                            layout=description_layout,
                                            style={'description_width': 'initial'})  # 'Bioactivity Function:',
        legend_title_input_4 = widgets.Text(value=legend_title[3], description=f'Legend title ({legend_title[3]}):',
                                            layout=description_layout_invisible,
                                            style={'description_width': 'initial'})  # 'Peptide Interval:',
        legend_title_input_4.layout.display = 'none'
        legend_title_input_5 = widgets.Text(value=legend_title[4], description=f'Legend title ({legend_title[4]}):',
                                            layout=description_layout_invisible,
                                            style={'description_width': 'initial'})  # 'Average Absorbance:'
        legend_title_input_5.layout.display = 'none'

    figure_label_message = widgets.HTML("<h3><u>Figure Label Options:</u></h3>")

    figure_label_box = widgets.VBox([
        figure_label_message,
        xaxis_label_input,
        yaxis_label_input,
        yaxis_position,
        legend_title_input_1,
        legend_title_input_2,
        legend_title_input_3,
        legend_title_input_4,
        legend_title_input_5
    ])

    create_plot_message = widgets.HTML("<h3><u>Create Plot Checkboxs:</u></h3>")

    # Plot Widgets
    plot_port = widgets.ToggleButton(
        value=True,
        description=' Portrait Plot',
        disabled=False,
        button_style='',
        tooltip='Show updated plot',
        icon='check'
    )

    plot_land = widgets.ToggleButton(
        value=True,
        description='Landscape Plot',
        disabled=False,
        button_style='',
        tooltip='Show updated plot',
        icon='check'
    )

    # Plot Toggle Buttons in a Horizontal Layout
    plot_toggle_buttons = widgets.HBox([
        plot_port,
        plot_land
    ])

    filename_label_message = widgets.HTML("<h3><u>Save As Options</u></h3>")

    filename_port_input = widgets.Text(
        value=display_filename_port,
        description='Filename (Portrait):',
        layout=dropdown_layout_large,
        style={'description_width': 'initial'}
    )

    filename_land_input = widgets.Text(
        value=display_filename_land,
        description='Filename (Landscape):',
        layout=dropdown_layout_large,
        style={'description_width': 'initial'}
    )

    plot_widget_box = widgets.VBox([
        create_plot_message,
        plot_toggle_buttons,
        filename_label_message,
        filename_port_input,
        filename_land_input
    ])

    # Add buttons for update and save plot
    update_button = widgets.Button(
        description='Show/Update Plot',
        button_style='success',
        tooltip='Click to update the plot',
        icon='refresh'
    )

    save_button = widgets.Button(
        description='Save Plot',
        button_style='info',
        tooltip='Click to save the plot',
        icon='save'
    )

    button_box = widgets.HBox([update_button, save_button])

    return color_widget_box, figure_label_box, plot_widget_box, button_box, hm_selected_color, lp_selected_color, avglp_selected_color, xaxis_label_input, yaxis_label_input, yaxis_position, legend_title_input_1, legend_title_input_2, legend_title_input_3, legend_title_input_4, legend_title_input_5, plot_port, plot_land, filename_port_input, filename_land_input, update_button, save_button
"""

def update_filenames(input_filename_port, input_filename_land):
    # Append directory and .png only when necessary
    #updated_filename_port = f'{images_folder_name}/{input_filename_port}.png' if input_filename_port else None
    #updated_filename_land = f'{images_folder_name}/{input_filename_land}.png' if input_filename_land else None
    updated_filename_port = f'{input_filename_port}.png' if input_filename_port else None
    updated_filename_land = f'{input_filename_land}.png' if input_filename_land else None

    return updated_filename_land, updated_filename_port


def process_available_data(available_data_variables):
    global list_of_counts, min_values, max_values, seq_len_list, max_sequence_length
    global y_ticks_html, max_count, num_unique_count, num_colors, total_plots, style_map

    count_list = []
    min_values = []
    max_values = []
    seq_len_list = []

    if available_data_variables:
        for var in available_data_variables:
            if 'peptide_counts' in available_data_variables[var]:
                count_list.append(available_data_variables[var]['peptide_counts'])
            global axis_number, total_plots, y_ticks
            axis_number = len(available_data_variables) + 2  # Total number of plots per set of data

            seq_len_list.append(len(available_data_variables[var]['amino_acids_chunks'][0]))
            num_sets = len(available_data_variables[var]['amino_acids_chunks'])

            total_plots = num_sets * axis_number
            style_map = assign_line_styles(available_data_variables)

            if 'ms_data' in available_data_variables[var]:
                min_values.append(available_data_variables[var]['min_ms_data'])
                max_values.append(available_data_variables[var]['max_ms_data'])

        max_sequence_length = max(seq_len_list)

        if min_values and max_values:
            y_ticks = calculate_y_ticks(min_values, max_values)
            y_ticks_str = ', '.join(f'{tick:.2e}' for tick in y_ticks)
            y_ticks_html = f'<b>Max/Min of MS data (y-ticks):</b> {y_ticks_str}'
        else:
            y_ticks_html = '<span style="color:red;">Insufficient data to calculate MS data y-ticks.</span>'
            y_ticks_html += f'<b>Protein Sequence Length:</b> {max_sequence_length}'

        # Check if the count list is not empty
        if count_list:
            # Flatten the list of lists into a single list
            flat_list = [item for sublist in count_list for item in sublist]
            if plot_zero == 'no':
                flat_list = [item for item in flat_list if item != 0]
            list_of_counts = set(flat_list)
            # Find the maximum and minimum values
            max_count = max(flat_list)

            # Find the number of unique counts
            num_unique_count = len(set(flat_list))
        else:
            max_count = None
            num_unique_count = 0

        # Assign number of colors for heatmap colormapping exception when grouping is required
        if num_unique_count >= 6:
            num_colors = 6
        else:
            num_colors = num_unique_count

        return {
            'list_of_counts': list_of_counts,
            'min_values': min_values,
            'max_values': max_values,
            'seq_len_list': seq_len_list,
            'max_sequence_length': max_sequence_length,
            'y_ticks_html': y_ticks_html,
            'max_count': max_count,
            'num_unique_count': num_unique_count,
            'num_colors': num_colors,
            'total_plots': total_plots,
            'style_map': style_map
        }
    else:
        return None


def display_choices(ms_average_choice, bio_or_pep):
    display(HTML(f"You have selected <b>{ms_average_choice}</b> for MS average plot.<br><br>"))
    display(HTML(f"You have selected <b>{bio_or_pep}</b> for line plot option.<br><br>"))


def get_current_directory():
    return os.getcwd()


def define_heatmap_directory(current_directory):
    return os.path.join(current_directory, 'heatmap_data_files')


def check_and_create_folder(directory, folder_name):
    folder_path = os.path.join(directory, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path


def list_fasta_files(fasta_dir):
    fasta_files = [f for f in os.listdir(fasta_dir) if f.endswith('.fasta')]
    #print("Fasta files found in directory:")
    #for f in fasta_files:
    #print(f)
    return fasta_files


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
                            protein_name = protein_name_full.split()[1]
                        else:
                            protein_name = protein_name_full                     # Find species in the header
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


def parse_fasta_files(fasta_dir, fasta_files):
    return parse_fasta([os.path.join(fasta_dir, f) for f in fasta_files])


def extract_prot_files(heatmap_directory, proteins_dic):
    prot_files = [file for file in os.listdir(heatmap_directory)
                  if file.endswith('absorbance_heatmap_data.csv')
                  and any(protein in file for protein in proteins_dic)]
    processed_prot_files = [file.split('_')[0] for file in prot_files]
    return sorted(set(processed_prot_files))


def initialize_settings():
    current_directory = get_current_directory()
    heatmap_directory = define_heatmap_directory(current_directory)
    global images_folder_name
    images_folder_name = 'heatmap_images'
    folder_path = check_and_create_folder(current_directory, images_folder_name)
    fasta_dir = 'fasta_files/'
    fasta_files = list_fasta_files(fasta_dir)
    proteins_dic = parse_fasta_files(fasta_dir, fasta_files)

    return {
        'current_directory': current_directory,
        'heatmap_directory': heatmap_directory,
        'images_folder_name': images_folder_name,
        'folder_path': folder_path,
        'fasta_dir': fasta_dir,
        'fasta_files': fasta_files,
        'proteins_dic': proteins_dic
    }


def generate_filenames(user_protein_id, protein_name_short, bio_or_pep, plot_heatmap='yes'):
    additional_vars_str = generate_additional_vars_str(bio_or_pep, plot_heatmap)
    xaxis_label = f"{protein_name_short.replace('_', ' ')} Sequence"
    yaxis_label = 'Averaged Peptide Abundance'

    protein_filename_short = re.sub(r'[^\w-]', '-', protein_name_short)
    # Generate filenames without path or extension for display
    #display_filename_port = f'portrait-average___{user_protein_id}-{protein_filename_short}___{label_count}-variables-plot'
    #display_filename_land = f'landscape___{user_protein_id}-{protein_filename_short}___{additional_vars_str}___{label_count}-variables-plot'
    display_filename_port = f'portrait_{user_protein_id}_{protein_filename_short}_average-only'
    display_filename_land = f'landscape_{user_protein_id}_{protein_filename_short}_{additional_vars_str}'

    # These will be used for actual file operations (hidden from initial UI)
    #default_filename_port = f'{images_folder_name}/{display_filename_port}.png'
    #default_filename_land = f'{images_folder_name}/{display_filename_land}.png'

    return display_filename_port, display_filename_land, xaxis_label, yaxis_label



def handle_protein_selection(change, proteins_dic):
    user_protein_id = change['new']
    protein_details = get_protein_details(user_protein_id, proteins_dic)
    #if protein_details:
    #print(f"Short name for the protein: {protein_details}")
    return user_protein_id, protein_details

"""

def chunk_dataframe(df, chunk_size, exclude_columns=3):
    # Select all rows and all but the last 'exclude_columns' columns
    df_subset = df.iloc[:, :-exclude_columns] if exclude_columns else df

    # Calculate the number of rows needed to make the last chunk exactly 'chunk_size'
    total_rows = df_subset.shape[0]
    remainder = total_rows % chunk_size
    if remainder != 0:
        # Rows needed to complete the last chunk
        rows_to_add = chunk_size - remainder

        # Create a DataFrame with zero values for the missing rows
        additional_rows = pd.DataFrame(np.zeros((rows_to_add, df_subset.shape[1])), columns=df_subset.columns)

        # Append these rows to df_subset
        df_subset = pd.concat([df_subset, additional_rows], ignore_index=True)

    # Create chunks of the DataFrame
    max_index = df_subset.index.max() + 1
    return [df_subset.iloc[i:i + chunk_size] for i in range(0, max_index, chunk_size)]

def process_data_variables(data_variables):
    chunk_size = 78
    # Print loaded dataframes and their labels
    for var, info in data_variables.items():
        if 'function_heatmap_df' in info:
            if info['is_func_df_all_none']:
                display(HTML(f"<b>{var} - Label: {info['label']}</b>: Only absorbance data loaded."))
            else:
                display(HTML(f"<b>{var} - Label: {info['label']}</b>: Absorbance and function data loaded."))

    # Dynamically generate the list of variable names based on loaded data
    variables = list(data_variables.keys())
    protein_id_list = []
    protein_name_list = []
    for var in variables:
        if var in data_variables and 'heatmap_df' in data_variables[var]:
            df = data_variables[var]['heatmap_df']
            df_func = data_variables[var]['function_heatmap_df']

            try:
                data_variables[var]['peptide_counts'] = df['count']
                data_variables[var]['ms_data'] = df['average']

                data_variables[var]['max_peptide_counts'] = data_variables[var]['peptide_counts'].max()
                data_variables[var]['min_peptide_counts'] = data_variables[var]['peptide_counts'].min()
                data_variables[var]['max_ms_data'] = data_variables[var]['ms_data'].max()
                data_variables[var]['min_ms_data'] = data_variables[var]['ms_data'][
                data_variables[var]['ms_data'] > 0].min()

                data_variables[var]['amino_acids_chunks'] = [data_variables[var]['protein_sequence'][i:i + chunk_size]
                                                             for i in
                                                             range(0, len(data_variables[var]['protein_sequence']),
                                                                   chunk_size)]

                data_variables[var]['peptide_counts_chunks'] = [data_variables[var]['peptide_counts'][i:i + chunk_size]
                                                                for i in
                                                                range(0, len(data_variables[var]['peptide_counts']),
                                                                      chunk_size)]

                data_variables[var]['ms_data_chunks'] = [data_variables[var]['ms_data'][i:i + chunk_size] for i in
                                                         range(0, len(data_variables[var]['ms_data']), chunk_size)]
                data_variables[var]['ms_data_list'] = list(data_variables[var]['ms_data'])
                data_variables[var]['AA_list'] = df['AA'].tolist()

                columns_to_include = df.columns.difference(['AA', 'COUNT'])
                df_filtered = df[columns_to_include]

                data_variables[var]['bioactive_peptide_abs_df'] = df_filtered
                data_variables[var]['bioactive_peptide_chunks'] = chunk_dataframe(df_filtered, chunk_size=chunk_size)
                data_variables[var]['bioactive_function_chunks'] = chunk_dataframe(df_func, chunk_size=chunk_size)
                data_variables[var]['bioactive_peptide_func_df'] = df_func
                data_variables[var]['bioactive_peptide_func_df']
                protein_id_list.append(data_variables[var]['protein_id'])
                protein_name_list.append(data_variables[var]['protein_name'])

                print(f"All data structures for {var} have been created successfully.")

            except Exception as e:
                display(HTML(f'<span style="color:red;">Error processing data for {var}: {e}</span>'))
        else:
            display(HTML(f'<span style="color:red;">{var} DataFrame is not loaded or does not exist.</span>'))
    user_protein_id_set = list(set(protein_id_list))
    user_protein_name_set = list(set(protein_name_list))

    if len(user_protein_id_set) > 1 and len(user_protein_name_set) == 1:
        user_protein_id = '_'.join(user_protein_id_set)
        protein_name_short = user_protein_name_set[0]

    elif len(user_protein_id_set) > 1 and len(user_protein_name_set) > 1:
        user_protein_id = '_'.join(user_protein_id_set)
        protein_name_short = '_'.join(user_protein_name_set)

    elif len(user_protein_name_set) == 1:
        user_protein_id = user_protein_id_set[0]
        protein_name_short = user_protein_name_set[0]

    return data_variables, user_protein_id, protein_name_short


"""

def generate_additional_vars_str(bio_or_pep, plot_heatmap):
    additional_vars = []

    if plot_heatmap == 'yes':
        additional_vars.append('heatmap')
    elif plot_heatmap == 'no':
        additional_vars.append('no-heatmap')

    if bio_or_pep == '1':
        additional_vars.append('intervals')
    elif bio_or_pep == '2':
        additional_vars.append('bioactive-functions')
    elif bio_or_pep == 'no':
        additional_vars.append('averages-only')
    global additional_vars_str
    # Join the additional_vars list into a single string with underscores
    additional_vars_str = '_'.join(additional_vars)
    return additional_vars_str


# Function to calculate y-ticks based on the min and max values of datasets
def calculate_y_ticks(min_values, max_values):
    if not min_values or not max_values:  # Check if lists are empty
        return [0, 1, 10]  # Default scale if no data is available

    overall_min = np.nanmin(min_values)
    overall_max = np.nanmax(max_values)
    min_power = 10 ** np.floor(np.log10(overall_min))
    max_power = 10 ** np.ceil(np.log10(overall_max))
    mid_point = np.sqrt(min_power * max_power)
    mid_point_rounded = 10 ** np.round(np.log10(mid_point))
    #mid_point_rounded = round(mid_point,1)

    return [min_power, mid_point_rounded, max_power]

# Funnctions to handle selecting of individual peptides for plotting
def handle_peptide_selection(unique_peptides_list):
    display(HTML("<br><b>Available peptides:</b>"))
    for i, peptide in enumerate(sorted(unique_peptides_list), 1):
        display(HTML(f"<b>{i}. {peptide}</b>"))
    selected_peptides_input = input("Select peptides by numbers, separated by commas, or type 'all' for all: ")

    if selected_peptides_input.lower() == 'all':
        selected_peptides.extend(unique_peptides_list)
    else:
        try:
            selected_indices = [int(num.strip()) for num in selected_peptides_input.split(',')]
            selected_peptides.extend(
                [peptide for i, peptide in enumerate(sorted(unique_peptides_list), 1) if i in selected_indices])
        except ValueError:
            display(HTML(f'<span style="color:red;">Invalid input. Please enter valid numbers or \'all\'.</span>'))
    return selected_peptides


# Funnctions to handle selecting of bioactive peptides for plotting
def handle_function_selection(unique_functions):
    if unique_functions:
        display(HTML("<br><b>Available bioactive functions:</b>"))
        for i, function in enumerate(sorted(unique_functions), 1):
            display(HTML(f"<b>{i}. {function}</b>"))
        selected_functions_input = input("Select functions by numbers, separated by commas, or type 'all' for all: ")
        if selected_functions_input.lower() == 'all':
            selected_functions.extend(unique_functions)
        else:
            try:
                selected_indices = [int(num.strip()) for num in selected_functions_input.split(',')]
                selected_functions.extend(
                    [func for i, func in enumerate(sorted(unique_functions), 1) if i in selected_indices])
            except ValueError:
                display(HTML(f'<span style="color:red;">Invalid input. Please enter valid numbers or \'all\'.</span>'))
    else:
        display(HTML("<br><b>There are no available bioactive functions, only averaged data will be plotted.</b>"))

    return selected_functions


"""_________________________________________Data Visualization Functions_________________________________"""


# Function to plot rows of amino acids with backgrounds colored
def plot_row_color(ax, amino_acids, colors):
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


# Function to plot continuse averaged lines
def plot_average_ms_data(ax, ms_data, label, var_index, y_ticks, i, chunk_size, avg_cmap, line_style):
    """
    Plot average MS data as a line plot on a twin axis, incorporating a line style, and return the line object and its properties.
    """
    start_limit = i * chunk_size
    end_limit = (i + 1) * chunk_size - 1
    ax.set_xlim(start_limit, end_limit)

    if isinstance(ms_data, (pd.DataFrame, pd.Series)):
        x_values = ms_data.index.tolist()
        y_values = ms_data.values
    else:
        x_values = list(range(len(ms_data)))  # Indices from 0 to len(ms_data)-1
        y_values = ms_data

    num_colors = avg_cmap.N

    # Get the color from the colormap and save it into avglp_selected_color
    color = avg_cmap(var_index % num_colors)
    line, = ax.plot(x_values, y_values, label=label, color=color, linestyle=line_style)
    ax.set_yscale('log')
    ax.set_yticks(y_ticks)
    ax.set_ylim(min(y_ticks), max(y_ticks))
    ax.tick_params(axis='y', labelsize=16)
    ax.yaxis.tick_left()
    ax.set_xticks([])
    ax.set_xticklabels([])

    return line, label, var_index  # Return the line and its label for further processing if needed


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


# This function is used in plotting to filter the data to only plot selected peptides or bioactive peptides, independent of averaged data
def filter_data_by_selection(bp_abs, bp_func, selected_peptides, selected_functions, bio_or_pep):
    """
    Filters the data based on user selection of peptides or functions.

    Args:
    bp_abs (DataFrame): The DataFrame with abundance data.
    bp_func (DataFrame): The DataFrame with function annotations.
    bio_or_pep (str): User choice to filter by '1' for peptides or '2' for functions.
    selected_peptides (list, optional): List of selected peptides if choice '1' is made.
    selected_functions (list, optional): List of selected functions if choice '2' is made.

    Returns:
    tuple: A tuple containing filtered DataFrames for abundance and function.
    """
    # Ensure bp_func is treated as containing strings and convert 'nan' strings back to real NaN
    bp_func = bp_func.astype(str).replace('nan', np.nan).infer_objects(copy=False)

    if bio_or_pep == '1':
        mask = bp_abs.columns.isin(selected_peptides)
        filtered_bp_abs = bp_abs.loc[:, mask]
        filtered_bp_fun = bp_func.copy()
    elif bio_or_pep == '2':
        def apply_mask(col):
            if col.dtype == 'object':
                split_col = col.str.split('; ')
                return split_col.apply(
                    lambda x: any(func in x for func in selected_functions) if isinstance(x, list) else False
                )
            else:
                return pd.Series([False] * len(col), index=col.index)

        mask = bp_func.apply(apply_mask)

        # Ensure that the mask is a DataFrame and then apply the filter
        if isinstance(mask, pd.Series):
            mask = mask.to_frame()

        filtered_bp_abs = bp_abs[mask.any(axis=1)]
        filtered_bp_fun = bp_func[mask.any(axis=1)]
    else:
        filtered_bp_abs = pd.DataFrame(np.zeros(bp_abs.shape))
        filtered_bp_fun = pd.DataFrame(np.zeros(bp_func.shape))

    # Convert any string 'nan' back to real NaN in the filtered data
    filtered_bp_abs = filtered_bp_abs.replace('nan', np.nan)
    filtered_bp_fun = filtered_bp_fun.replace('nan', np.nan)

    return filtered_bp_abs, filtered_bp_fun


# Plots individual lines in the landscape plot
def process_chunk_data(ax2, chunk_abs, chunk_func, chunk_size, i, y_ticks, handles, labels, sample_list, var_name_list,
                       line_style, var_name, var_ms_data, selected_peptides, selected_functions, lp_selected_color,
                       ms_average_choice, bio_or_pep):
    global print_list
    print_list = []
    # Compute xlim dynamically based on i
    start_limit = i * chunk_size
    end_limit = (i + 1) * chunk_size - 1
    ax2.set_xlim(start_limit, end_limit)
    common_columns = []
    colormap = plt.get_cmap(lp_selected_color)

    # Initialize colormap based on the appropriate selected list
    if bio_or_pep == '1':
        num_colors = max(len(selected_peptides), 1)  # Ensure at least one color is generated
        colors = colormap(np.linspace(0, 1, num_colors))
        common_columns = chunk_abs.columns
    elif bio_or_pep == '2':
        num_colors = max(len(selected_functions), 1)
        colors = colormap(np.linspace(0, 1, num_colors))
        common_columns = chunk_abs.columns.intersection(chunk_func.columns)

    else:
        # Default to a basic colormap if neither condition is specifically required
        colors = [colormap(0)]
    #print("common_columns",common_columns)
    # Create a dictionary that maps each function or peptide to a unique color
    items_to_color = selected_peptides if bio_or_pep == '1' else selected_functions
    function_colors = {item: colors[i % len(colors)] for i, item in enumerate(items_to_color)}
    function_colors['Multiple'] = 'black'  # Use black for 'Multiple'
    for col in common_columns:
        y_values = chunk_abs[col].dropna()
        y_values = y_values[y_values > 0]
        if not y_values.empty:
            x_values = y_values.index
            label_value = 'No Label'  # Default labelfiltered_bp_abs = bp_abs[mask
            if bio_or_pep == '1':
                label_value = col  # Use column name as label
            elif bio_or_pep == '2' and col in chunk_func.columns:
                label_values = chunk_func[col].dropna().unique()
                if any(';' in str(value) for value in label_values):
                    print_list.append([str(value) for value in label_values])
                    label_value = 'Multiple'
                else:
                    label_value = ', '.join(str(value).strip("[]'") for value in label_values) if len(
                        label_values) > 0 else 'No Label'
            if label_value != 'No Label':
                # Get color from function_colors based on label_value
                color = function_colors.get(label_value, 'grey')  # Default to 'grey' if no match
                #print(label_value,x_values,y_values)
                line, = ax2.plot(x_values, y_values, label=f'{label_value}', linestyle=line_style, color=color)
                handles.append(line)
                labels.append(f'{label_value}')
                sample_list.append(f'{line_style}')
                var_name_list.append(f'{var_name}')

    ax2.set_yscale('log')
    ax2.set_yticks(y_ticks)
    ax2.set_ylim(min(y_ticks), max(y_ticks))
    ax2.tick_params(axis='y', labelsize=16)
    ax2.yaxis.tick_left()
    return print_list


def get_grouped_colors(counts, max_count, num_groups, plot_zero, cmap):
    # Initialize colors list with None to maintain length
    colors = [None] * len(counts)

    # Set the start point based on the user's input
    start_point = 0 if plot_zero == 'yes' else 1

    # Group counts into fewer categories if necessary, excluding zeros
    group_bounds = np.linspace(0, max_count, num_groups + 1)
    group_labels = np.digitize(counts, bins=group_bounds, right=True)  # Find group labels for counts
    #print("group_labels", group_labels)
    norm = Normalize(vmin=start_point, vmax=num_groups)  # Normalize based on the number of groups

    # Map each group label to a color, assigning white to zeros if needed
    for i, (count, label) in enumerate(zip(counts, group_labels)):
        if plot_zero == 'no' and count == 0:
            colors[i] = 'white'
        else:
            if max_count > 20:
                colors[i] = cmap(count / max_count)
            else:
                colors[i] = cmap(norm(label))

    #print(colors)
    return colors


# Function to create legend for heatmap

# Function to create legend for heatmap
def create_heatmap_legend_handles(cmap, num_colors, max_count, plot_zero):
    # Set the start point based on the user's input
    start_point = 0 if plot_zero == 'yes' else 1
    num_intervals = num_colors

    # Adjust count_ranges to start from start_point
    if plot_zero == 'yes':
        count_ranges = np.linspace(start_point, max_count, num_intervals + 1)
    else:
        count_ranges = np.linspace(start_point, max_count, num_intervals)
    if max_count > num_intervals:
        plt_interval = max_count
    else:
        plt_interval = num_intervals
    legend_handles = []
    heatmap_labels = []
    norm = Normalize(vmin=start_point, vmax=max_count)  # Normalize the range from start_point to max_count
    #print("count_ranges",count_ranges)
    #print("num_intervals",num_intervals)
    for i in range(len(count_ranges)):
        color = cmap(norm(count_ranges[i]))
        if plt_interval <= 6 and plot_zero == 'no':
            label = f'{int(count_ranges[i])}'
        elif plt_interval <= 6 and plot_zero == 'yes':
            label = f'{int(count_ranges[i])}'
        elif i + 1 >= len(count_ranges):
            label = f'{int(count_ranges[i])} - {max(count_ranges)}'
            break
        else:
            label = f'{int(count_ranges[i])} - {int(count_ranges[i + 1])}'
        #print("i:",i,"label:",label)
        legend_handles.append(patches.Patch(color=color, label=label))
        heatmap_labels.append(label)
    # Manually add white color for zero if plot_zero is 'yes'
    #if plot_zero == 'no':
    #    legend_handles.insert(0, patches.Patch(color='white', label='0'))

    return legend_handles, heatmap_labels


def create_custom_legends(fig, labels, handles, var_name_list, legend_titles, heatmap_legend_handles,
                          heatmap_legend_labels, ms_average_choice, bio_or_pep, plot_type):
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
    average_color = mlines.Line2D([], [], color='none', label='Average Absorbance')
    line_color = mlines.Line2D([], [], color='none', label='Line Color')
    pep_count_placeholder = mlines.Line2D([], [], color='none', label='Line Type')

    line_type_title = legend_titles[0]
    avgline_color_title = legend_titles[4]
    if bio_or_pep == '1':
        color_title = legend_titles[3]
    elif bio_or_pep == '2':
        color_title = legend_titles[2]

    if ms_average_choice == 'yes' and bio_or_pep != 'no':
        combined_handles = [line_color] + other_handles + [average_color] + averaged_handles
        combined_labels = [color_title] + other_labels + [avgline_color_title] + averaged_labels

    if ms_average_choice == 'yes' and bio_or_pep == 'no':
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


"""_________________________________________Landscape Plot________________________________________"""


### def visualize_sequence_heatmap_individual_lines(available_data_variables, amino_acid_height, lineplot_height, indices_height, filename, xaxis_label, yaxis_label, legend_title, yaxis_position):
def visualize_sequence_heatmap_lanscape(available_data_variables,
                                                         amino_acid_height,
                                                         lineplot_height,
                                                         indices_height,
                                                         filename,
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
                                                         bio_or_pep,
                                                         save_fig):
    # Use a list comprehension to find the maximum length of 'AA_list' across all variables
    max_sequence_length = max([len(available_data_variables[var]['AA_list']) for var in available_data_variables])

    # Check if there are multiple distinct protein IDs in available_data_variables
    multiple_proteins = len(set([available_data_variables[var]['protein_id'] for var in available_data_variables])) > 1

    chunk_size = max_sequence_length
    # Create legend handles for the heatmap
    heatmap_legend_handles, heatmap_legend_labels = create_heatmap_legend_handles(cmap, num_colors, max_count, plot_zero)  # You can change the number 5 to have more or fewer color intervals

    # Function to plot rows of amino acids with backgrounds colored
    # Function to plot rows of amino acids with backgrounds colored
    def plot_row_color_landscape(ax, amino_acids, colors):
        ax.axis('off')
        ax.set_xlim(0, max_sequence_length)
        ax.set_xlabel('')
        # Height and width for each cell
        cell_width = 1  # Each amino acid is spaced evenly by 1 unit on the x-axis
        cell_height = 1  # Set height of the row

        for j, (aa, color) in enumerate(zip(amino_acids, colors)):
            # Create a rectangle (cell) with the background color
            rect = patches.Rectangle((j, 0), cell_width, cell_height, color=mcolors.rgb2hex(color))
            ax.add_patch(rect)  # Add the colored rectangle to the plot

    # Function to plot rows of amino acids with backgrounds colored
    def plot_row_landscape(ax, amino_acids):
        ax3.axis('off')
        ax3.set_xlim(0, max_sequence_length)
        ax3.set_xlabel('')
        aa_font_size = 10
        if max_sequence_length > 200:
            aa_font_size -= 0.5
        if max_sequence_length > 250:
            aa_font_size -= 1
        if max_sequence_length > 300:
            return
        for j, (aa) in enumerate(amino_acids):
                ax3.text(j + 0.5, 0.5, aa, color='black', ha='center', va='center',
                         fontsize=aa_font_size)

    axis_number = 3  # Total number of plots per set of data
    if plot_heatmap == 'yes':
        # Define height ratios for each subplot in a set
        height_ratios = (
                    [lineplot_height] + [indices_height] + [amino_acid_height] * len(available_data_variables) + [amino_acid_height])
        axis_number = len(available_data_variables) + 3

    elif plot_heatmap == 'no':
        height_ratios = ([lineplot_height] +[indices_height] + [amino_acid_height] )
        axis_number = 3

    fig, axes = plt.subplots(axis_number, 1, figsize=(25, (lineplot_height + indices_height + amino_acid_height)),
                             gridspec_kw={'height_ratios': height_ratios, 'hspace': 0})


    # Initialize for legend handling
    handles, labels, sample_list, var_name_list = [], [], [], []
    total_count = 0

    # Loop through each set of data and create plots
    for var_index, var in enumerate(available_data_variables):
        ax1 = axes[0]
        ax1.axis('off')
        ax1 = ax1.twinx()  # Create a twin y-axis
        ax1.yaxis.set_minor_locator(plt.NullLocator())

        var_amino_acids = available_data_variables[var]['AA_list']
        var_counts = available_data_variables[var]['peptide_counts']
        var_ms_data = available_data_variables[var]['ms_data_list']
        var_name = available_data_variables[var]['label']
        var_colors = get_grouped_colors(var_counts, max_count, num_colors, plot_zero, cmap)
        bp_abs = available_data_variables[var]['bioactive_peptide_abs_df']
        bp_func = available_data_variables[var]['bioactive_peptide_func_df']
        # Default line style
        line_style = '-'  # Default style if other conditions don't apply

        #if ms_average_choice == 'yes' and bio_or_pep == 'no':
        #   line_style = '-'  # This can stay '-' or change as per your requirement
        #else:
        line_style = style_map[var_name]  # Get assigned line style from the style map

        if bio_or_pep != 'no':
            filtered_bp_abs, filtered_bp_fun = filter_data_by_selection(bp_abs, bp_func, selected_peptides,
                                                                        selected_functions, bio_or_pep)
            print_list = process_chunk_data(ax1, filtered_bp_abs, filtered_bp_fun, chunk_size, 0, y_ticks, handles,
                                            labels, sample_list, var_name_list, line_style, var_name, var_ms_data,
                                            selected_peptides, selected_functions, lp_selected_color, ms_average_choice,
                                            bio_or_pep)

        if not ms_average_choice == 'no':
            # Ensure that line_style is defined before this point or provide a default value
            line, label, _ = plot_average_ms_data(ax1, var_ms_data, f'Averaged {var_name}', var_index, y_ticks, 0,
                                                  chunk_size, avg_cmap, line_style)
            handles.append(line)
            labels.append(f'{label}')
            sample_list.append(line_style)
            var_name_list.append(var_name)

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

    if bio_or_pep == '2':
        # Flatten the list of lists into a single list of strings
        print_list = [item for sublist in print_list for item in sublist]

        # Remove duplicates from the list by converting it to a set, then convert it back to a list
        print_list = list(set(print_list))

        # Remove the empty string if it exists
        if '' in print_list:
            print_list.remove('')

        # Enumerate the list and format the output
        print_list = [f"     {i + 1}. {label}" for i, label in enumerate(print_list)]
        print_list.insert(0, "The following labels have been relabeled as 'Multiple':")

        # Join all the elements of the list into a single string with newlines
        footnote = '\n'.join(print_list)
        fig.text(0.15, -0.2, footnote, ha='left', va='center', fontsize=12)



    fig.text(yaxis_position, 0.90, yaxis_label, va='top', rotation='vertical', fontsize=16)
    fig.text(0.5, -0.025, xaxis_label, ha='center', va='center', fontsize=16)
    plt.tight_layout()
    #plt.subplots_adjust(left=0.05)  # Create space on the left for the y-label

    if save_fig == 'yes':
        # Save the figure to a BytesIO buffer
        buffer = BytesIO()
        fig.savefig(buffer, format="png", bbox_inches='tight')
        buffer.seek(0)

        # Generate the download link
        data_url = f"data:image/png;base64,{buffer.getvalue().decode('latin1')}"
        download_html = f"""
        <script>
            var link = document.createElement('a');
            link.href = "{data_url}";
            link.download = "{filename}";
            link.click();
        </script>
        """
        # Display the auto-download script in the browser
        display(HTML(download_html))
        display(HTML(f'An image file of the figure above has been saved as <b>{filename}</b>.'))

    # Display the plot inline
    display(fig)
    plt.close(fig)
    #print(f'\n')
    #print(f'\n')
    if bio_or_pep == '2':
        print(f'Fotenotes:')
        print(footnote)
    return fig


"""_______________________________Portrait Plot______________________________________________"""


def visualize_sequence_heatmap_portrait(available_data_variables,
                                             amino_acid_height,
                                             lineplot_height,
                                             indices_height,
                                             filename,
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
                                             save_fig,
                                             chunk_size):

    lineplot_height, scale_factor = settings.port_hm_settings.get(
        len(available_data_variables), (20, 0.1))
    plot_zero == 'no'
    handles, labels, sample_list, var_name_list = [], [], [], []

    for var in available_data_variables:
        num_sets = len(available_data_variables[var]['amino_acids_chunks'])
    # Create legend handles for the heatmap
    heatmap_legend_handles, heatmap_legend_labels = create_heatmap_legend_handles(cmap, num_colors, max_count,
                                                                                  plot_zero)  # You can change the number 5 to have more or fewer color intervals

    # Define height ratios for each subplot in a set
    height_ratios = ([lineplot_height] + [indices_height] + [amino_acid_height] * len(available_data_variables)) * num_sets

    # Create a figure and set of subplots
    fig, axes = plt.subplots(total_plots, 1, figsize=(20, num_sets * (
            lineplot_height + indices_height + amino_acid_height * len(available_data_variables)) * scale_factor),
                             gridspec_kw={'height_ratios': height_ratios, 'hspace': 1})

    # Initialize for legend handling
    handles, labels = [], []
    total_count = 0



    # Loop through each set of data and create plots
    for i in range(num_sets):

        # Determine the max_var_amino_acids for the current i across all variables
        max_var_amino_acids = max(
            len(available_data_variables[var]['amino_acids_chunks'][i])
            for var in available_data_variables
        )

        for var_index, var in enumerate(available_data_variables):
            ax1 = axes[axis_number * i]
            ax1.axis('off')
            ax2 = ax1.twinx()  # Create a twin y-axis

            # Get data chunks for the current variable
            var_amino_acids = available_data_variables[var]['amino_acids_chunks'][i]
            var_counts = available_data_variables[var]['peptide_counts_chunks'][i]
            var_ms_data = available_data_variables[var]['ms_data_chunks'][i]
            var_name = available_data_variables[var]['label']
            var_colors = get_grouped_colors(var_counts, max_count, num_colors, plot_zero, cmap)
            line_style = '-'

            # Plot MS data using plot_average_ms_data and handle the returned line object
            line, label, _ = plot_average_ms_data(ax2, var_ms_data, var_name, var_index, y_ticks, i, chunk_size,
                                                  avg_cmap, line_style='-')
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
    if save_fig == 'yes':
        fig.savefig(filename, bbox_inches='tight')
        display(HTML(f'An image file of the figure above has been saved as <b>{filename}</b>.'))

    # Display the plot inline
    display(fig)
    plt.close(fig)  # Close the figure to avoid duplicate display in some environments
    return fig

