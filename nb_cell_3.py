class HeatmapDataHandler():
    def __init__(self, data_transformer):    
        # Add filter_type to the existing initialization
        self.data_transformer = data_transformer
        self.filter_type = 'all-peptides'  # Set default value
        self.protein_name_short = ''
        # Initialize UI widgets
        self.protein_selector = widgets.SelectMultiple(description='Protein:')
        self.var_key_dropdown = widgets.SelectMultiple(description='Variable Key:')
        self.button_box = HBox([widgets.Button(description='Submit')])
        
        # Initialize data structures
        self.available_data_variables_dict = {}
        self.label_widgets = {}
        self.data_variables = {}
        
        # Extract protein information
        self.protein_mapping = {
            key.split('_')[0]: value['protein_name']
            for key, value in self.data_variables.items()
        } if self.data_variables else {}
        
        self.available_proteins = set([key.split('_')[0] for key in self.data_variables.keys()]) if self.data_variables else set()
        
        # Get available grouping variables from data transformer
        if self.data_transformer.group_data_dict:
            self.available_grouping_vars = [group['grouping_variable'] for group in self.data_transformer.group_data_dict.values()]
        else:
            self.available_grouping_vars = []
            
        self.selected_var_keys_list = set()
        if self.data_transformer.col_order:
            self.col_order = self.data_transformer.col_order
            
        # Initialize filtered variables
        self.filtered_data_variables = {}
        self.available_data_variables_dict = {}
        self.label_widgets = {}
        self.order_widgets = {}
        self.default_label_values = {}
        self.default_order_values = {}

        # Create widgets
        self.create_widgets()
        
        # Initialize variables for plotting (just the defaults, actual widgets created by PlotHandler)
        self.bio_or_pep = None  # Default: None
        self.ms_average_choice = 'yes'  # Default: Plot averaged data
        self.filter_type = 'all-peptides'  # Default: Show all peptides
        self.selected_peptides = []
        self.selected_functions = []
       
        self.initialize_empty_label_order_widgets()
    
    def _notify_data_change(self):
        """Notify plot handler when available_data_variables_dict changes"""
        if hasattr(self, '_on_data_changed_callback') and self._on_data_changed_callback:
            try:
                self._on_data_changed_callback()
            except Exception as e:
                # Silently handle callback errors
                # print(f"Data change callback error: {e}")  # Uncomment for debugging
                pass

    def add_group_with_notification(self):
        """Enhanced add_group that notifies observers of data changes"""
        # Call the original add_group logic
        self.add_group()
        # Notify observers that data has changed
        self._notify_data_change()

    def initialize_empty_label_order_widgets(self):
        """Create and display the label/order widgets"""
        # Create buttons if they don't already exist
        if not hasattr(self, 'update_label_button'):
            self.update_label_button = widgets.Button(
                description="Update Labels",
                button_style='success',
                disabled = True,
                layout=widgets.Layout(width='125px', height='30px', min_height='30px')
            )
            self.update_order_button = widgets.Button(
                description="Update Order",
                button_style='success',
                disabled= True,
                layout=widgets.Layout(width='125px', height='30px')
            )


            # Attach click event handlers
            self.update_label_button.on_click(self.on_update_label_click)
            self.update_order_button.on_click(self.on_update_order_click)

            # Display buttons
            self.label_order_button_box = widgets.HBox([self.update_order_button], 
                                      layout=widgets.Layout(width='500px', justify_content='flex-start'))
           
            
        # Create container for label widgets if it doesn't exist
        if not hasattr(self, 'label_widgets_container'):
            self.label_widgets_container = widgets.VBox([
                widgets.HTML("<p>Labels will appear here when protein and variable selection is made.</p>")
            ], layout=widgets.Layout( width='620px',
                                      height='340px',
                                      overflow='hidden',
                                      margin='0px'  # Remove any margins
                                      ))
        
        # Create text area for order input if it doesn't exist
        if not hasattr(self, 'new_order_input'):
            self.new_order_input = widgets.Textarea(
                value="",
                placeholder="Sample labels will appear here protein and variable selection is made.",
                disabled=True,
                layout=widgets.Layout(width='90%', height='75px')
            )
        
        # Create message output area if it doesn't exist
        if not hasattr(self, 'message_output_order'):
            self.message_output_order = widgets.Output()
        if not hasattr(self, 'message_output_label'):
            self.message_output_label = widgets.Output()
        
        # Create the complete layout
        self.update_order_initial_layout = widgets.VBox([

            widgets.HTML("<u>Re-order Samples (optional):</u>"),
            self.new_order_input,
            self.label_order_button_box,
            self.message_output_order
        ],layout=widgets.Layout(width='800px'))

    def update_label_order_widgets(self):
        """Update existing label/order widgets with current data in a grid layout"""
        # Only proceed if we have data
        if not hasattr(self, 'available_data_variables_dict') or not self.available_data_variables_dict:
            return
        
        # Initialize label_widgets dictionary if it doesn't exist
        if not hasattr(self, 'label_widgets'):
            self.label_widgets = {}
        
        # Create new list of widget rows
        widgets_list = []
        
        # Populate rows - each available_data_variables_dict becomes a row
        for i, (var, info) in enumerate(self.available_data_variables_dict.items(), 1):
            # Create editable text field with current label
            label_text_widget = widgets.Text(
                value=info['label'],
                layout=widgets.Layout(width='150px')
            )
            
            # Store the text widget in label_widgets dictionary
            self.label_widgets[var] = label_text_widget
            
            # Create row with HTML text for all except the input field
            # Set fixed widths and use ellipsis for overflow
            row_widgets = [
                # Number - smaller width
                widgets.HTML(f"<div style='width:20px; padding:2px;'>{i})</div>"),
                
                # Label - use ellipsis for overflow
                widgets.HTML(f"<div style='width:90px; padding:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{info['label']}'>{info['label']}</div>"),
                
                # Protein Species - use ellipsis for overflow
                widgets.HTML(f"<div style='width:90px; padding:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{info.get('protein_species', '')}'>{info.get('protein_species', '')}</div>"),
                
                # Protein Name - use ellipsis for overflow
                widgets.HTML(f"<div style='width:200px; padding:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{info.get('protein_name', '')}'>{info.get('protein_name', '')}</div>"),
                
                # Editable text field
                label_text_widget
            ]
            
            # Create row with horizontal box - no horizontal overflow
            row = widgets.HBox(
                children=row_widgets, 
                layout=widgets.Layout(
                    width='600px',
                    margin='2px 0',
                    overflow='hidden',
                    min_height='30px'
                )
            )
            
            widgets_list.append(row)
        
        # Create a VBox with the list of rows - explicitly pass children
        label_container = widgets.VBox(
            children=widgets_list,
            layout=widgets.Layout(
                width='610px',  # Slightly wider than rows to prevent horizontal scroll
                height='340px',
                padding='0px',
                overflow='auto'  # Standard overflow property - will scroll vertically when needed
            )
        )
        
        # Update the container - this avoids the previous potential TraitError
        self.label_widgets_container.children = (label_container,)

        # Update order input with current labels
        label_list = [info['label'] for info in self.available_data_variables_dict.values()]
        self.new_order_input.value = ', '.join(label_list)
  
    def create_filtered_data_variables(self):
        return {key: self.data_variables[key] 
                for key in self.selected_var_keys_list
                if key in self.data_variables}
         
    def update_protein_info(self, protein_name):
        self.protein_name_short = protein_name
        # Update plot handler if it exists
        if hasattr(self, 'plot_handler'):
            self.plot_handler.update_protein_name(protein_name)
  
    def process_export(self):       
        # Dictionary to hold all data for saving
        self.complete_data = {}

        # Get unique proteins from selected_var_keys_list
        selected_proteins = set()
        for key in self.selected_var_keys_list:
            # Handle the case where key might be a tuple or a string
            if isinstance(key, tuple):
                # If it's a tuple, extract the first element and then split
                for item in key:
                    protein_id = item.split('_')[0] if '_' in item else item
                    selected_proteins.add(protein_id)
            else:
                # If it's a string, process as before
                protein_id = key.split('_')[0] if '_' in key else key
                selected_proteins.add(protein_id)
        # Process each selected protein
        for protein_id in selected_proteins:
            protein_df = data_transformer.merged_df[data_transformer.merged_df['Protein'] == protein_id]
            is_all_null = 'function' in protein_df.columns and protein_df['function'].isna().all()


            if protein_id in data_transformer.protein_dict:
                species ='unknown'
                name = protein_id
                # Check if we need to fetch sequence from UniProt
                if 'sequence' not in data_transformer.protein_dict[protein_id] or not data_transformer.protein_dict[protein_id]['sequence']:
                    # Check if UniProt search is enabled
                    uniprot_search_widget = getattr(data_transformer, 'uniprot_search', None)
                    if not uniprot_search_widget or not uniprot_search_widget.value:
                        with self.message_output_label:
                            self.message_output_label.clear_output(wait=True)
                            display(HTML(f"<b style='color:orange;'>Sequence for {protein_id} not found in local data.</b>"))
                            display(HTML(f"<b style='color:orange;'>UniProt search is disabled. Please provide a FASTA file containing {protein_id}'s sequence to continue visualization or enable UniProt search.</b>"))
                        self.update_label_button.disabled = True
                        self.update_order_button.disabled = True
                        return
                    try:
                        # Initialize UniProt client if not already available
                        if not hasattr(data_transformer, 'uniprot_client'):
                            data_transformer.uniprot_client = UniProtClient()
                        
                        # Fetch the protein info with sequence
                        name, species, sequence = data_transformer.uniprot_client.fetch_protein_info_with_sequence(protein_id)
                        # Update the protein_dict with the sequence
                        if sequence:
                            data_transformer.protein_dict[protein_id]['sequence'] = sequence
                            
                            with self.message_output_label:
                                self.message_output_label.clear_output(wait=True)
                                display(HTML(f"<b style='color:green;'>Sequence for {protein_id} fetched from UniProt with a legnth of {len(data_transformer.protein_dict[protein_id]['sequence'])} AAs.</b>"))
                                display(HTML("<p><strong>Update Labels Tip:</strong> To remove selected sample(s), type <code>remove</code> in the update label field and click \"Update Labels\".</p>")) if len(selected_proteins) > 1 and len(selected_proteins) != len(self.available_data_variables_dict) else None

                                self.update_label_button.disabled = False 
                                self.update_order_button.disabled = False
                        else:
                            with self.message_output_label:
                                self.message_output_label.clear_output(wait=True)
                                display(HTML(f"<b style='color:orange;'>Sequence for {protein_id} not found in UniProt.</b>"))
                                display(HTML(f"<b style='color:orange;'>Please provide a FASTA file containing {protein_id}'s sequence to continue visualization or select a different protein.</b>"))
                            self.update_label_button.disabled = True
                            self.update_order_button.disabled = True
                            return
                    except Exception as e:
                        with self.message_output_label:
                            self.message_output_label.clear_output(wait=True)
                            display(HTML(f"<b style='color:red;'>Error fetching sequence for {protein_id}: {str(e)}</b>"))
                else:
                    with self.message_output_label:
                        self.message_output_label.clear_output(wait=True)
                        display(HTML(f"<b style='color:green;'>Sequence for {protein_id} retrived from protein dictionary with a legnth of {len(data_transformer.protein_dict[protein_id]['sequence'])} AAs.</b>")); 
                        display(HTML("<p><strong>Update Labels Tip:</strong> To remove selected sample(s), type <code>remove</code> in the update label field and click \"Update Labels\".</p>")) if len(selected_proteins) > 1 and len(selected_proteins) != len(self.available_data_variables_dict) else None
                    self.update_label_button.disabled = False
                    self.update_order_button.disabled = False

                # Get protein data - now with sequence if available
                protein_sequence = data_transformer.protein_dict[protein_id].get('sequence', '')
                protein_species = data_transformer.protein_dict[protein_id].get('species', species)
                protein_name = data_transformer.protein_dict[protein_id].get('name', name)

                protein_data = {}

                # Process each group for this protein
                for group_key, group_info in data_transformer.group_data_dict.items():
                    grouping_var_name = group_info['grouping_variable']
                    
                    # Only process if this combination exists in selected_var_keys_list
                    if f"{protein_id}_{grouping_var_name}" in self.selected_var_keys_list:
                        heatmap_data = export_heatmap_data_to_dict(
                            protein_id, grouping_var_name, group_info,
                            protein_sequence, protein_species, protein_name,
                            protein_df, is_all_null
                        )
                        protein_data[grouping_var_name] = heatmap_data

                # Only add to complete_data if we have data for this protein
                if protein_data:
                    self.complete_data[protein_id] = protein_data
            else:
                display(HTML(f"<b style='color:red;'>Data for {protein_id} not found in protein dictionary.</b>"))
        
    def update_filter_type(self, new_filter_type):
        """Update the filter type and reprocess data"""
        self.filter_type = new_filter_type
        self.process_export()
        if hasattr(self, '_on_data_changed_callback'):
            self._on_data_changed_callback()
    
    def extract_and_format_data(self):
        # Load the data from the saved directory
        self.process_export()  # Remove the self argument
        self.loaded_data = self.complete_data
        lenofdict = len(self.loaded_data.keys())
        # Initialize the new dictionary
        data_variables = {}

        # Iterate over the loaded data to extract and reorganize it
        for protein_id, protein_data in self.loaded_data.items():
            protein_sequence = protein_data.get('protein_sequence')

            for grouping_var_name, group_info in protein_data.items():
                # Extract the required DataFrames and other information
                func_df = group_info.get('func_heatmap_df')
                abs_df = group_info.get('heatmap_df')
                filtered_abs_df = group_info.get('filtered_heatmap_df')

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
                    'label': label if lenofdict == 1 else var_key,
                    'is_func_df_all_none': is_func_df_all_none,
                    'filtered_heatmap_df': filtered_abs_df
                }

        return data_variables
    
    def process_data_variables(self):
        """
        Minimal processing to pass essential data from filtered to available data variables
        """
        # Dynamically generate the list of variable names based on loaded data
        variables = list(self.filtered_data_variables.keys())
        protein_id_list = []
        protein_name_list = []
        
        # Pass through only essential data to available_data_variables_dict
        self.available_data_variables_dict = {}
        
        for var in variables:
            if var in self.filtered_data_variables:
                # Create new dict for this variable
                self.available_data_variables_dict[var] = {
                    # Core data frames
                    'heatmap_df': self.filtered_data_variables[var]['heatmap_df'],
                    'function_heatmap_df': self.filtered_data_variables[var]['function_heatmap_df'],
                    'filtered_heatmap_df': self.filtered_data_variables[var]['filtered_heatmap_df'],
    
                    # Essential metadata
                    'protein_id': self.filtered_data_variables[var]['protein_id'],
                    'protein_name': self.filtered_data_variables[var]['protein_name'],
                    'protein_sequence': self.filtered_data_variables[var]['protein_sequence'],
                    'label': self.filtered_data_variables[var]['label'],
                    
                    # Track if function data is all null
                    'is_func_df_all_none': self.filtered_data_variables[var]['function_heatmap_df'].isnull().all().all() 
                        if self.filtered_data_variables[var]['function_heatmap_df'] is not None else True
                }
                
                protein_id_list.append(self.filtered_data_variables[var]['protein_id'])
                protein_name_list.append(self.filtered_data_variables[var]['protein_name'])
    
        # Set protein ID and name
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
            
        self.protein_name_short = str(self.protein_name_short)
                
    def create_widgets(self):
        if data_transformer:
            if not data_transformer.merged_df.empty:
                # Create widgets for protein selection
                # Count occurrences of each protein
                protein_counts = data_transformer.merged_df['Protein'].value_counts()
                sorted_proteins = protein_counts.index.tolist()
                
                # Create dropdown options list with first protein selected by default
                dropdown_options = [(f"{protein} - {data_transformer.protein_dict.get(protein, {'name': 'Unknown'})['name']}", protein) 
                                for protein in sorted_proteins]
            else: 
                sorted_proteins = None
                dropdown_options = [('No proteins available', '')]
        else:
            sorted_proteins = None
            dropdown_options = [('No proteins available', '')]
        
        # Create a custom class for SelectMultiple with text-overflow ellipsis
        class EllipsisSelectMultiple(widgets.SelectMultiple):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self._dom_classes = ['ellipsis-select']
                
        # Apply CSS styling for ellipsis
        display(HTML("""
        <style>
        .ellipsis-select select option {
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
        }
        </style>
        """))
        
        self.protein_selector = EllipsisSelectMultiple(
            options=dropdown_options,
            value=(sorted_proteins[0]) if sorted_proteins else ('',),  # Empty tuple for no initial selection
            #description='Protein ID:',
            disabled=False,
            style={'description_width': 'initial'},
            layout=widgets.Layout(
                width='325px',
                height='150px',
            )
        )

        self.var_key_dropdown = widgets.SelectMultiple(
            #description='Select Groups',
            style={'description_width': 'initial'},
            disabled=False,
            layout=widgets.Layout(
                width='325px',
                height='150px',
            )
        )

        if sorted_proteins:
            self.update_var_keys({'new': sorted_proteins[0], 'type': 'change', 'name': 'value'})
            # Set protein_name_short for the default selected protein
            default_protein_id = sorted_proteins[0]
            default_protein_name = data_transformer.protein_dict.get(default_protein_id, {'name': 'Unknown'})['name']
            self.protein_name_short = str(default_protein_name)
       
        # Set widget events
        self.protein_selector.observe(self.update_var_keys, names='value')
        self.protein_selector.observe(self.on_group_selection_change, names='value')  # Add this line
        self.var_key_dropdown.observe(self.on_group_selection_change, names='value')  # Add this line

    def on_group_selection_change(self, change):
        # Auto-trigger add_group functionality if both protein and group selections exist
        if (self.protein_selector.value and len(self.protein_selector.value) > 0 and 
            self.var_key_dropdown.value and len(self.var_key_dropdown.value) > 0):
            self.reset_selection()
            self.add_group()

    def update_var_keys(self, change):
        self.selected_protein = change['new']
        
        # Handle case when dropdown hasn't been populated yet
        if not hasattr(self.var_key_dropdown, 'value'):
            return
            
        current_selection = set(self.var_key_dropdown.value)
        
        # Use col_order to maintain the same order, but only include available grouping vars
        if hasattr(self, 'col_order') and self.col_order:
            new_options = [str(col) for col in self.col_order 
                        if str(col) in map(str, self.available_grouping_vars)]
        else:
            # Fallback if col_order isn't available
            new_options = [str(col) for col in self.available_grouping_vars]
        
        # Update options while preserving order from col_order
        self.var_key_dropdown.options = new_options
        
        # Keep selected values that are still valid and return as tuple
        valid_selections = [val for val in current_selection if val in new_options]
        self.var_key_dropdown.value = tuple(valid_selections) 
            
    def add_group(self):
        """
        Add grouping variables to the current selection.
        
        Handles single and multiple protein selections with corresponding grouping variables.
        Updates selected proteins, group variables, and combined lists.
        """
        # Enable relevant buttons
        self.new_order_input.disabled = False
        self.update_label_button.disabled = False
        self.update_order_button.disabled = False
        
        # Extract the protein value, handling both single values and tuples
        protein_value = self.protein_selector.value
        if isinstance(protein_value, tuple):
            current_proteins = list(protein_value)
        else:
            current_proteins = [protein_value] if protein_value else []
        
        # Get selected grouping variables
        selected_keys = list(self.var_key_dropdown.value)
        
       
        # Generate and manage keys
        generated_keys = set()
        
        # Generate individual and combined protein keys
        for i, protein in enumerate(current_proteins):
            for group_var in selected_keys:
                # Individual protein keys
                generated_keys.add(f"{protein}_{group_var}")
              
        # Ensure selected_protein is a list 
        if not hasattr(self, 'selected_protein'):
            self.selected_protein = []
        
        # Convert to list if it's a tuple
        if isinstance(self.selected_protein, tuple):
            self.selected_protein = list(self.selected_protein)
        
        # Update selected proteins list
        for protein in current_proteins:
            if protein not in self.selected_protein:
                self.selected_protein.append(protein)
        
        # Update group variables list
        if not hasattr(self, 'selected_group_vars'):
            self.selected_group_vars = []
        
        for group_var in selected_keys:
            if group_var not in self.selected_group_vars:
                self.selected_group_vars.append(group_var)
        
        # Add new keys
        self.selected_var_keys_list.update(generated_keys)


        self.data_variables = self.extract_and_format_data()
        self.filtered_data_variables = self.create_filtered_data_variables()
        self.process_data_variables()
        self.available_data_variables_dict = self.filtered_data_variables.copy()

        # Update widgets and display
        self.default_label_values = {key: self.label_widgets[key].value for key in self.label_widgets}
        self.default_order_values = [info['label'] for info in self.available_data_variables_dict.values()]
        with self.message_output_label:
            self.message_output_label.clear_output(wait=True)
            #display(HTML(''))
        with self.message_output_order:
            self.message_output_order.clear_output(wait=True)
            display(HTML(''))
        self.update_label_order_widgets()
        
        # CRITICAL: Trigger specific options refresh after data is ready
        if hasattr(self, '_on_data_changed_callback') and self._on_data_changed_callback:
            self._on_data_changed_callback()

    #Function to reset the selection
    def reset_selection(self):
        # Preserve loaded data
        preserved_data = {
            'data_variables': self.data_variables,
            'loaded_data': getattr(self, 'loaded_data', None),
            'complete_data': getattr(self, 'complete_data', None)
        }
        
        # Reset selection-related attributes
        self.selected_var_keys_list = set()
        #self.protein_selector.value = ('',)
        #self.var_key_dropdown.options = []
        
        # Reset visualization-related attributes
        self.filtered_data_variables = {}
        self.available_data_variables_dict = {}
        
        # Reset widgets
        #self.label_widgets = {}
        #self.order_widgets = {}
        #self.default_label_values = {}
        #self.default_order_values = []
        

        
        # Clear plots if plot handler exists
        if hasattr(self, '_plot_handler') and self._plot_handler:
            with self._plot_handler.plot_output:
                self._plot_handler.plot_output.clear_output()
                plt.close('all')  # Close all matplotlib figures
            
            # Reset plot-related attributes in plot handler
            self._plot_handler.fig_port = None
            self._plot_handler.fig_land = None
        
        # Restore preserved data
        self.data_variables = preserved_data['data_variables']
        if preserved_data['loaded_data'] is not None:
            self.loaded_data = preserved_data['loaded_data']
        if preserved_data['complete_data'] is not None:
            self.complete_data = preserved_data['complete_data']
        
        # Update available grouping variables if they exist
        if hasattr(data_transformer, 'group_data_dict') and data_transformer.group_data_dict:
            self.available_grouping_vars = [
                group['grouping_variable'] 
                for group in data_transformer.group_data_dict.values()
            ]
        
        # Trigger any necessary UI updates
        if hasattr(self, '_on_data_changed_callback'):
            self._on_data_changed_callback()

        self._notify_data_change()
    # Function to update order based on new order input
    def update_order(self, order_labels):
        """
        Updates the order of available_data_variables_dict based on provided labels.
        The order of items in the dictionary will match the order of labels in order_labels.
        
        Args:
            order_labels (list): List of labels in the desired order
        """
        # Clean the input labels - strip whitespace and empty strings
        order_labels = [label.strip() for label in order_labels if label.strip()]
        
        # Get current label to key mapping
        label_to_key = {info['label']: key for key, info in self.available_data_variables_dict.items()}
        
        # Validate input
        if len(order_labels) != len(self.available_data_variables_dict):
            raise ValueError(f"Number of labels provided ({len(order_labels)}) does not match number of variables ({len(self.available_data_variables_dict)})")
        
        if len(set(order_labels)) != len(order_labels):
            raise ValueError("Duplicate labels found in input")
        
        if not all(label in label_to_key for label in order_labels):
            invalid_labels = [label for label in order_labels if label not in label_to_key]
            raise ValueError(f"Invalid labels found: {invalid_labels}")
        
        # Create a new ordered dictionary with items in the specified order
        ordered_data = {}
        for new_label in order_labels:
            key = label_to_key[new_label]
            ordered_data[key] = self.available_data_variables_dict[key]
            
            # Update the label in the data to match the new order
            ordered_data[key]['label'] = new_label
        
        # Replace the available_data_variables_dict with the new ordered dictionary
        self.available_data_variables_dict = ordered_data
        

        
        # Update the text input to show the new order
        current_labels = [info['label'] for info in self.available_data_variables_dict.values()]
        self.new_order_input.value = ', '.join(current_labels)
        
        return self.available_data_variables_dict
    
    # Event handler for updating labels
    def on_update_label_click(self, b):
        try:
            update_info = self.update_labels()
            
            # Create success message based on what was updated/removed
            if update_info['removed_count'] > 0:
                removed_text = ', '.join(update_info['removed_labels'])
                if update_info['removed_count'] == 1:
                    message = f'<b style="color:green;">Labels updated successfully! Removed 1 sample: {removed_text}. {update_info["remaining_count"]} samples remaining.</b>'
                else:
                    message = f'<b style="color:green;">Labels updated successfully! Removed {update_info["removed_count"]} samples: {removed_text}. {update_info["remaining_count"]} samples remaining.</b>'
            else:
                message = '<b style="color:green;">Labels updated successfully!</b>'
            
            # Display success message
            with self.message_output_label:
                self.message_output_label.clear_output(wait=True)
                display(HTML(message))
            
            # Trigger data changed callback if it exists
            if hasattr(self, '_on_data_changed_callback'):
                self._on_data_changed_callback()
            
        except Exception as e:
            with self.message_output_label:
                self.message_output_label.clear_output(wait=True)
                display(HTML(f'<b style="color:red;">Error updating labels: {str(e)}</b>'))

            # Trigger data changed callback if it exists
            if hasattr(self, '_on_data_changed_callback'):
                self._on_data_changed_callback()

    # Event handler for updating order
    def on_update_order_click(self, b):
        """Event handler for updating order"""
        try:
            # Get the order input and split it into a list
            order_input = self.new_order_input.value
            order_list = [label.strip() for label in order_input.split(',')]
            
            # Update the order
            self.update_order(order_list)
            
            # Update the label widgets with the new order
            for i, (key, info) in enumerate(self.available_data_variables_dict.items()):
                if key in self.label_widgets:
                    self.label_widgets[key].value = info['label']
            
            self.update_label_order_widgets()
            
            # Display success message
            with self.message_output_order:
                self.message_output_order.clear_output(wait=True)
                display(HTML('<b style="color:green;">Order updated successfully!</b>'))
            
            # Trigger data changed callback if it exists
            if hasattr(self, '_on_data_changed_callback'):
                self._on_data_changed_callback()
                
        except Exception as e:
            with self.message_output_order:
                self.message_output_order.clear_output(wait=True)
                display(HTML(f'<b style="color:red;">Error updating order: {str(e)}</b>'))
  
    def update_labels(self):
        # Update labels in available_data_variables_dict based on label_widgets
        # Track keys to remove to avoid modifying dict during iteration
        keys_to_remove = []
        removed_labels = []
        
        for key in self.available_data_variables_dict:
            label_value = self.label_widgets[key].value.strip()
            
            # Check if user wants to remove this sample (case-insensitive)
            if label_value.lower() == 'remove':
                keys_to_remove.append(key)
                # Store the original label for reporting
                removed_labels.append(self.available_data_variables_dict[key]['label'])
            else:
                # Update the label normally
                self.available_data_variables_dict[key]['label'] = label_value
        
        # Remove the keys that were marked for removal
        for key in keys_to_remove:
            if key in self.available_data_variables_dict:
                del self.available_data_variables_dict[key]
            if key in self.label_widgets:
                del self.label_widgets[key]
        
        # If any keys were removed, update the display widgets
        if keys_to_remove:
            self.update_label_order_widgets()
        
        # Return information about what was updated/removed
        return {
            'removed_count': len(keys_to_remove),
            'removed_labels': removed_labels,
            'remaining_count': len(self.available_data_variables_dict)
        }

    # Function to display the initial selection widgets         
    def display_widgets(self):
        # Create a grid layout with 3 rows and 2 columns
    
        # Input widgets
        # Make sure it's added like this
        input_widgets = VBox([
            widgets.HTML("<u>Select Groups (Required):</u>"), 
            self.var_key_dropdown,
            widgets.HTML("<u>Select Proteins (Required):</u>"),
            self.protein_selector],
            layout=widgets.Layout(height = '400px', width = '90%', max_width ='1000px', margin='0px', padding='0px', overflow='hidden',))  # Minimize widget margins

        
        return input_widgets, #vert_button_box#, update_label_box, update_order_box