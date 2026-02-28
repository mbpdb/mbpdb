class DynamicVisualizationHandler:
    def __init__(self, data_transformer):
        self.data_transformer = data_transformer
        self.selector = HeatmapDataHandler(data_transformer)
        self.app = None
        self.initialize_instructions()

        
        # Add a flag to track if the label/order section has been created
        self.label_order_section_created = False
        
        # Add flags to track visualization state
        self._protein_selected = False
        self._variable_selected = False

        # Initialize the visualization components immediately
        self._initialize_visualization()
        # Add observers to data transformer's file uploaders
        self.data_transformer.merged_uploader.observe(self._on_file_change, names='value')
        self.data_transformer.fasta_uploader.observe(self._on_file_change, names='value')
        self.data_transformer.uniprot_search.observe(self._on_file_change, names='value')
    
    def _register_plot_handler_observers(self):
        """Register observers to refresh specific options when data changes."""
        if hasattr(self, 'app') and self.app and hasattr(self.app, '_data_change_observer_registered'):
            if not self.app._data_change_observer_registered:
                # Register observers for protein and group selection changes
                if hasattr(self, 'selector'):
                    if hasattr(self.selector, 'protein_selector'):
                        self.selector.protein_selector.observe(self.app.on_data_change_observer, names='value')
                    if hasattr(self.selector, 'var_key_dropdown'):
                        self.selector.var_key_dropdown.observe(self.app.on_data_change_observer, names='value')
                
                self.app._data_change_observer_registered = True
                
    def initialize_instructions(self):
        """Initialize the instructions for the user"""
        self.stepone_output_html_message = """
            <div style='padding: 10px; background-color: #f8f9fa; border-left: 5px solid #007bff; margin: 10px 0;'>
                <h3>Step 1: Upload Data</h3>
                <p>Please upload your data files to begin:</p>
                <ul style='list-style-type: circle;'>
                    <li>Upload a merged data file (.csv/.txt/.tsv/.xlsx) exported from the Data Transformation module</li>
                    <li>Upload FASTA files for non-uniprot proteins (optional)</li>
                    <li>Enable UniProt search to automatically add UniProt sequences to your plot (default)</li>
                </ul>
            </div>
            """
        self.stepone_status_output = widgets.Output(
            layout=widgets.Layout(
                max_width='1000px',  # Set your desired maximum width here
                width='100%'        # This makes it fill the available space up to the max-width
            )
        )        
        with self.stepone_status_output:
            clear_output(wait=True)
            display(HTML(self.stepone_output_html_message))    

        # Status message for Plot Controls step
        self.steptwo_output_html_message = """
            <div style='padding: 10px; background-color: #f8f9fa; border-left: 5px solid #007bff; margin: 10px 0;'>
                <h3>Step 2: Select Data to Visualize</h3>
                <p>Choose which data to include in your visualization:</p>
                <ul style='list-style-type: circle;'>
                    <li> Required: Select a protein from the dropdown</li>
                    <li> Required: Choose a grouping variable</li>
                    <li> Optional: Customize your plot using the Update Labels and Reorder Samples options</li>
                </ul>
            </div>
            """
        # Create Plot Controls status output
        self.steptwo_status_output = widgets.Output(
            layout=widgets.Layout(
                max_width='1000px',  # Set your desired maximum width here
                width='100%'        # This makes it fill the available space up to the max-width
            )
        )        
        with self.steptwo_status_output:
            clear_output(wait=True)
            display(HTML(self.steptwo_output_html_message))
            
        # Status message for Plotting Options step
        # Define the collapsible HTML message
        self.stepthree_output_html_message = """
        <div style='padding: 10px; background-color: #f8f9fa; border-left: 5px solid #007bff; margin: 10px 0;'>
            <h3>Step 3: Visualization Options</h3>
            <p>Choose how to visualize your protein peptide data:</p>
            
            <details>
                <summary style="font-weight: bold; cursor: pointer; padding: 5px; border-bottom: 1px solid #eee;">Plot Filter</summary>
                <ul style='list-style-type: none; margin-left: 20px;'>
                    <li><b>All Peptides:</b> Display data for all detected peptides across your protein sequence</li>
                    <li><b>All Functional Peptides:</b> Display only peptides that have assigned bioactive functions</li>
                    <li><b>Selected Functional Peptides:</b> Display only peptides with specific functions chosen in the "Specific Options" dropdown</li>
                </ul>
            </details>
            
            <details>
                <summary style="font-weight: bold; cursor: pointer; padding: 5px; border-bottom: 1px solid #eee;">Plot Averaged Data</summary>
                <ul style='list-style-type: none; margin-left: 20px;'>
                    <li><b>Yes:</b> Display both individual peptide data and the average Abundance across the protein</li>
                    <li><b>No:</b> Display only individual peptide data without averaging</li>
                    <li><b>Only:</b> Display only the averaged data as a line plot, hiding individual peptide data</li>
                </ul>
            </details>
            
            <details>
                <summary style="font-weight: bold; cursor: pointer; padding: 5px; border-bottom: 1px solid #eee;">Plot Specific Peptides</summary>
                <ul style='list-style-type: none; margin-left: 20px;'>
                    <li><b>None:</b> Display data for all peptides according to the Plot Filter selection</li>
                    <li><b>Peptide Intervals:</b> Highlight specific peptide segments selected from the "Specific Options" dropdown</li>
                    <li><b>Bioactive Functions:</b> Highlight peptides with specific bioactive functions selected from the "Specific Options" dropdown</li>
                </ul>
            </details>
            
            <details>
                <summary style="font-weight: bold; cursor: pointer; padding: 5px; border-bottom: 1px solid #eee;">Specific Options</summary>
                <ul style='list-style-type: none; margin-left: 20px;'>
                    <li>Multi-select dropdown that changes based on your "Plot Specific Peptides" selection:</li>
                    <li style="margin-left: 20px;"><b>When "Peptide Intervals" is selected:</b> Choose specific peptide segments by their position (e.g., "1-20", "21-40")</li>
                    <li style="margin-left: 20px;"><b>When "Bioactive Functions" is selected:</b> Choose specific biological functions to highlight (e.g., "ACE Inhibitor", "Antioxidant")</li>
                </ul>
            </details>

            <details>
                <summary style="font-weight: bold; cursor: pointer; padding: 5px; border-bottom: 1px solid #eee;">Log Transform</summary>
                <ul style='list-style-type: none; margin-left: 20px;'>
                    <li>Apply a log transformation to the abundnace data (Y-axis) to improve visualization of low Abundance data</li>
                </ul>
            </details>

            <details>
                <summary style="font-weight: bold; cursor: pointer; padding: 5px; border-bottom: 1px solid #eee;">Appearance Settings</summary>
                <ul style='list-style-type: none; margin-left: 20px;'>
                    <li>Customize the appearance of your plot using the following settings:</li>
                    <li style="margin-left: 20px;"><b>Heatmap:</b> Choose a color scheme for your heatmap (default: RdYlGn_r)</li>
                    <li style="margin-left: 20px;"><b>Line Plot:</b> Select line plot color scheme (default:  Set3)</li>
                    <li style="margin-left: 20px;"><b>Avg Line Plot:</b> Choose average line color scheme (default:  Dark2)</li>
                    <li style="margin-left: 20px;"><b>x-axis label:</b> Set the horizontal axis label (e.g., Beta-casein Sequence)</li>
                    <li style="margin-left: 20px;"><b>y-axis label:</b> Set the vertical axis label (e.g., Averaged Peptide Abundance)</li>
                    <li style="margin-left: 20px;"><b>y-axis title position:</b> Adjust the position of the y-axis title</li>
                    <li style="margin-left: 20px;"><b>Legend titles:</b> Customize labels for Sample Type, Peptide Counts, and Average Abundance</li>
                </ul>
            </details>
            <details>
                <summary style="font-weight: bold; cursor: pointer; padding: 5px; border-bottom: 1px solid #eee;">Display and Export</summary>
                <ul style='list-style-type: none; margin-left: 20px;'>
                    <li>Choose your display options and export your visualization:</li>
                    <li style="margin-left: 20px;"><b>Plot Orientation:</b>
                        <ul style="list-style-type: none; margin-left: 10px;">
                            <li>☐ Plot Portrait Graph</li>
                            <li>☑ Plot Landscape Graph</li>
                        </ul>
                    </li>
                    <li style="margin-left: 20px;"><b>Actions:</b>
                        <ul style="list-style-type: none; margin-left: 10px;">
                            <li style="display: inline-block; margin-right: 10px;"><button style="background-color: #28a745; color: white; border: none; padding: 5px 10px; border-radius: 3px;">🔄 Generate/Update</button></li>
                            <li style="display: inline-block;"><button style="background-color: #17a2b8; color: white; border: none; padding: 5px 10px; border-radius: 3px;">💾 Save Plot</button></li>
                        </ul>
                    </li>
                </ul>
            </details>

            <p style="margin-top: 10px;">Select your desired visualization options below and click "Generate/Update" to create your plots.</p>
        """
        # Create Plotting Options status output
        self.stepthree_status_output = widgets.Output(            
            layout=widgets.Layout(
                max_width='1000px',  # Set your desired maximum width here
                width='100%'        # This makes it fill the available space up to the max-width
            )
        )        
        with self.stepthree_status_output:
            clear_output(wait=True)
            display(HTML(self.stepthree_output_html_message))
    
    def _initialize_visualization(self):
        """Initialize the visualization with widgets in disabled state"""
        # Create the selector even if we don't have data yet
        self.selector = HeatmapDataHandler(self.data_transformer)
        
        # Create the app with the selector
        self.app = HeatmapPlotHandler(self.data_transformer)
        
        # Set up bidirectional references properly
        self.app.set_data_handler(self)  # Set the visualization handler as the data handler
        self.app.selector = self.selector  # Explicitly connect the app to the selector
        
    
        self.selector.protein_selector.observe(self.app.add_group_change, names='value')
        # Add observer for plot controls status
        self.selector.protein_selector.observe(self._update_plot_controls_status, names='value')

        self.selector.var_key_dropdown.observe(self.app.add_group_change, names='value')
        # Add observer for plot controls status
        self.selector.var_key_dropdown.observe(self._update_plot_controls_status, names='value')
    
        # Disable widgets that require data
        self._update_widget_states(enabled=False)

        # Set the label_order_section_created flag to True
        self.label_order_section_created = True
        
        # Set up event handlers for the visualization handler
        self.selector.protein_selector.observe(self._on_selector_data_change)
        
        # Initialize the selector's label/order widgets
        self.selector.initialize_empty_label_order_widgets()
        
        # Ensure event handlers are attached for label/order widgets
        if hasattr(self.selector, "update_label_button"):
            self.selector.update_label_button.on_click(self._on_selector_data_change)
        if hasattr(self.selector, "update_order_button"):
            self.selector.update_order_button.on_click(self._on_selector_data_change)

        # Set up the selector's data changed callback
        self.selector._on_data_changed_callback = self._on_selector_data_change

        if hasattr(self, 'app') and self.app:
                self.selector._on_data_changed_callback = self.app.refresh_specific_options_external

    def _update_widget_states(self, enabled=True):
        """Update the enabled/disabled state of all widgets without redisplaying"""
        if self.selector:
            # Essential selector widgets
            widgets_to_update = [
                'protein_selector', 
                'var_key_dropdown',
                'plot_filter'
            ]
            
            for widget_name in widgets_to_update:
                if hasattr(self.selector, widget_name):
                    widget = getattr(self.selector, widget_name)
                    if hasattr(widget, 'disabled'):
                        widget.disabled = not enabled
            
            # Also check if there's a label_order_button_box with children
            if hasattr(self.selector, 'label_order_button_box') and hasattr(self.selector.label_order_button_box, 'children'):
                for child in self.selector.label_order_button_box.children:
                    if hasattr(child, 'disabled'):
                        child.disabled = not enabled
            
            # Update widgets in button_box if it exists
            if hasattr(self.selector, 'button_box') and hasattr(self.selector.button_box, 'children'):
                for child in self.selector.button_box.children:
                    if hasattr(child, 'disabled'):
                        child.disabled = not enabled
                        
            # Check for any nested VBox or HBox that might contain the buttons
            if hasattr(self.selector, 'label_order_output'):
                # Try to find buttons inside this output
                for widget in self.selector.label_order_output.outputs:
                    if hasattr(widget, 'children'):
                        for child in widget.children:
                            if isinstance(child, widgets.Button):
                                child.disabled = not enabled
                            # Check for nested containers
                            if hasattr(child, 'children'):
                                for nested_child in child.children:
                                    if isinstance(nested_child, widgets.Button):
                                        nested_child.disabled = not enabled
            
            # Label and order widgets
            for widget_dict_name in ['label_widgets', 'order_widgets']:
                if hasattr(self.selector, widget_dict_name):
                    widget_dict = getattr(self.selector, widget_dict_name)
                    if isinstance(widget_dict, dict):
                        for widget in widget_dict.values():
                            if hasattr(widget, 'disabled'):
                                widget.disabled = not enabled                

    def _populate_selectors(self):
        """Populate the protein and group selectors with available data"""
        if not self.selector:
            return
        
        # Check if we have the necessary data
        if not hasattr(self.data_transformer, 'merged_df') or self.data_transformer.merged_df is None:
            return
            
        if not hasattr(self.data_transformer, 'protein_dict') or not self.data_transformer.protein_dict:
            return
        
        # 1. Populate the protein dropdown
        if hasattr(self.selector, 'protein_selector'):
            # Count occurrences of each protein
            protein_counts = self.data_transformer.merged_df['Protein'].value_counts()
            sorted_proteins = protein_counts.index.tolist()
            
            # Create dropdown options with protein names
            dropdown_options = [(f"{protein} - {self.data_transformer.protein_dict.get(protein, {'name': 'Unknown'})['name']}", protein) 
                            for protein in sorted_proteins]
            
            # Update the dropdown
            self.selector.protein_selector.options = dropdown_options
            
            # Important fix: For SelectMultiple widget, value must be a tuple
            if dropdown_options and hasattr(self.selector.protein_selector, 'value'):
                # Create a tuple with the first protein as its only element
                self.selector.protein_selector.value = (sorted_proteins[0],)  # Note the comma to create a tuple
                
                # Set protein_name_short on selector from the default protein
                default_protein_id = sorted_proteins[0]
                default_protein_name = self.data_transformer.protein_dict.get(default_protein_id, {'name': 'Unknown'})['name']
                self.selector.protein_name_short = str(default_protein_name)
                
                # Update the plot handler's x-axis label with the default protein name
                if hasattr(self, 'app') and hasattr(self.app, 'xaxis_label_input'):
                    self.app.xaxis_label_input.value = f"{default_protein_name} Sequence"
        
        # 2. Populate the grouping variables
        if hasattr(self.data_transformer, 'group_data_dict') and hasattr(self.selector, 'available_grouping_vars'):
            self.selector.available_grouping_vars = [
                group['grouping_variable'] 
                for group in self.data_transformer.group_data_dict.values()
            ]
            
            # If we have col_order, make sure it's set in the selector
            if hasattr(self.data_transformer, 'col_order'):
                self.selector.col_order = self.data_transformer.col_order
        
        # 3. Force update of the var_key dropdown based on selected protein
        if hasattr(self.selector, 'update_var_keys') and hasattr(self.selector.protein_selector, 'value') and self.selector.protein_selector.value:
            # Create a simulated change event with the first value from the tuple
            # Extracting the first element from the tuple for the change event
            first_selected = self.selector.protein_selector.value[0] if self.selector.protein_selector.value else None
            
            change_event = {
                'name': 'value',
                'new': first_selected,  # This will be a string, not a tuple
                'type': 'change'
            }
            
            self.selector.update_var_keys(change_event)
        
    def _on_file_change(self, change):
        """Handle file upload changes without recreating the UI"""
        # Debounce rapid successive calls to prevent multiple displays
        current_time = time.time()
        if hasattr(self, '_last_file_change_update') and (current_time - self._last_file_change_update) < 0.1:
            return
        self._last_file_change_update = current_time
        
        # Check if we now have all required data
        #has_required_data = self._check_required_data()
        has_merged, has_groups, has_proteins, has_fasta_files, has_uniprot_search = self._check_required_data()
        has_required_data = has_merged and has_groups# and has_proteins# and has_fasta_files and has_uniprot_search
        if has_required_data and has_fasta_files and has_uniprot_search:
            # We have all necessary data, so populate the selectors and enable widgets
            self._populate_selectors()
            self._update_widget_states(enabled=True)
            self.stepone_output_html_message = f"""
            <div style='padding: 10px; background-color: #e8f5e9; border-left: 5px solid #4caf50; margin: 10px 0;'>
                <h3>Step 1: Upload Data</h3>
                <p>Data successfully loaded:</p>
                <ul style="list-style-type: none;">
                    <li>✅ <b>{self.data_transformer.pd_filename}</b> successfully upload as a merged data file</li> 
                    <li>✅ <b>{self.data_transformer.fasta_filename}</b> successfully upload as a FASTA files for non-uniprot proteins</li>
                    <li>✅ UniProt API successfully connected and enabled</li>
                </ul>
                <p>All required data has been loaded. You can now proceed to step 2.</p>
            </div>
            """       
        if has_required_data and has_fasta_files and not has_uniprot_search:
            # We have all necessary data, so populate the selectors and enable widgets
            self._populate_selectors()
            self._update_widget_states(enabled=True)
            self.stepone_output_html_message = f"""
            <div style='padding: 10px; background-color: #e8f5e9; border-left: 5px solid #4caf50; margin: 10px 0;'>
                <h3>Step 1: Upload Data</h3>
                <p>Data successfully loaded:</p>
                <ul style="list-style-type: none;">
                    <li>✅ <b>{self.data_transformer.pd_filename}</b> successfully upload as a merged data file</li> 
                    <li>✅ <b>{self.data_transformer.fasta_filename}</b> successfully upload as a FASTA files for non-uniprot proteins</li>
                    <li>➤ Enable UniProt search to automatically add UniProt sequences to your plot (optional)</li>
                </ul>
                <p>All required data has been loaded. You can now proceed to step 2.</p>
            </div>
            """
        elif has_required_data and not has_fasta_files and has_uniprot_search:
            # We have all necessary data, so populate the selectors and enable widgets
            self._populate_selectors()
            self._update_widget_states(enabled=True)
            self.stepone_output_html_message = f"""
            <div style='padding: 10px; background-color: #e8f5e9; border-left: 5px solid #4caf50; margin: 10px 0;'>
                <h3>Step 1: Upload Data</h3>
                <p>Data successfully loaded:</p>
                <ul style="list-style-type: none;">
                    <li>✅ <b>{self.data_transformer.pd_filename}</b> successfully upload as a merged data file (.csv/.txt/.tsv/.xlsx)</li> 
                    <li>➤ Upload FASTA files for non-uniprot proteins (optional)</li>
                    <li>✅ UniProt API successfully connected and enabled</li>
                </ul>
                <p>All required data has been loaded. You can now proceed to step 2.</p>
            </div>
            """        
        elif has_required_data and not (has_fasta_files and has_uniprot_search):
            # We have all necessary data, so populate the selectors and enable widgets
            self._populate_selectors()
            self._update_widget_states(enabled=True)
            self.stepone_output_html_message = f"""
            <div style='padding: 10px; background-color: #e8f5e9; border-left: 5px solid #4caf50; margin: 10px 0;'>
                <h3>Step 1: Upload Data</h3>
                <p>Additional actions are required:</p>
                <ul style="list-style-type: none;">
                    <li>✅ <b>{self.data_transformer.pd_filename}</b> successfully upload as a merged data file (.csv/.txt/.tsv/.xlsx)</li> 
                    <li>➤ Upload FASTA files for non-uniprot proteins (optional)</li>
                    <li>➤ Enable UniProt search to automatically add UniProt sequences to your plot (optional)</li>
                </ul>
                <p>Pleaase upload a Fasta File containing protein data or enable UniProt Searching.</p>
            </div>
            """
        elif has_fasta_files and not has_uniprot_search:
            self._populate_selectors()
            self._update_widget_states(enabled=True)
            self.stepone_output_html_message = f"""
            <div style='padding: 10px; background-color: #e8f5e9; border-left: 5px solid #4caf50; margin: 10px 0;'>
                <h3>Step 1: Upload Data</h3>
                <p>Data successfully loaded:</p>
                <ul style="list-style-type: none;">
                    <li>✅ Upload a merged data file (.csv/.txt/.tsv/.xlsx)</li>
                    <li>✅ Upload FASTA files for non-uniprot proteins (optional)</li>
                    <li>➤ Enable UniProt search to automatically add UniProt sequences to your plot (default)</li>
                </ul>
                <p>All required data has been loaded. You can now use the interface.</p>
            </div>
            """
        elif not has_required_data and not (has_fasta_files or has_uniprot_search):
            # Still missing data, update the message
            self.stepone_output_html_message = f"""
            <div style='padding: 10px; background-color: #fff3e0; border-left: 5px solid #ff9800; margin: 10px 0;'>
               <h3>Step 1: Upload Data</h3>
                <p>Additional actions are required:</p>
                <ul style="list-style-type: none;">
                    <li>➤ Upload a merged data file (.csv/.txt/.tsv/.xlsx)</li>
                    <li>➤ Upload FASTA files for non-uniprot proteins (optional)</li>
                    <li>➤ Enable UniProt search to automatically add UniProt sequences to your plot (default)</li>
                </ul>
                <p>Pleaase upload peptidomic data and either a Fasta File containing protein data or enable UniProt Searching.</p>

            </div>
            """
        if has_required_data:
            # Register plot handler observers after data is available
            self._register_plot_handler_observers()
            
            # CRITICAL: Refresh specific options when files are uploaded
            if hasattr(self, 'app') and self.app and hasattr(self.app, 'refresh_specific_options_external'):
                self.app.refresh_specific_options_external()
        
        # Always update the display at the end of the method
        if hasattr(self, 'stepone_status_output'):
            with self.stepone_status_output:
                clear_output(wait=True)
                display(HTML(self.stepone_output_html_message))

    def _update_selector_data(self):
        """Update the selector with new data from data_transformer"""
        if self.selector is None:
            return
            
        # Update proteins dictionary
        self.selector.protein_dict = self.data_transformer.protein_dict
        
        # Update available proteins
        if hasattr(self.data_transformer, 'merged_df'):
            self.selector.available_proteins = set(
                self.data_transformer.merged_df['Protein'].str.split(';').str[0].unique()
            )
        
        # Update available grouping variables
        if hasattr(self.data_transformer, 'group_data_dict'):
            self.selector.available_grouping_vars = [
                group['grouping_variable'] 
                for group in self.data_transformer.group_data_dict.values()
            ]
            
            # Ensure col_order is set
            if hasattr(self.data_transformer, 'col_order'):
                self.selector.col_order = self.data_transformer.col_order
        
        # Set callback for data changes
        self.selector._on_data_changed_callback = self._on_selector_data_change
    
    def _on_selector_data_change(self, change=None):
        """Handle changes in selector data"""

        if self.app:
            self.app.update_data(self.selector)
    
        # Then update the status message based on the current state
        self._update_plot_controls_status(change)
        
    def _update_plot_controls_status(self, change=None):
        """Update the plot controls status message based on current selections"""
        # Debounce rapid successive calls to prevent multiple displays
        current_time = time.time()
        if hasattr(self, '_last_status_update') and (current_time - self._last_status_update) < 0.1:
            return
        self._last_status_update = current_time
        
        # Check if a protein is selected
        if hasattr(self.selector, 'protein_selector') and self.selector.protein_selector.value:
            self._protein_selected = True
        else:
            self._protein_selected = False
        
        # Check if a variable is selected
        if hasattr(self.selector, 'var_key_dropdown') and self.selector.var_key_dropdown.value:
            self._variable_selected = True
        else:
            self._variable_selected = False
        
        # Update the status message based on current state
        if self._protein_selected and self._variable_selected:
            # Both protein and variable are selected
            self.steptwo_output_html_message = """
                <div style='padding: 10px; background-color: #e8f5e9; border-left: 5px solid #4caf50; margin: 10px 0;'>
                    <h3>Step 2: Plot Controls</h3>
                    <p>Selections complete! You can now:</p>
                    <ul style="list-style-type: none;">
                        <li>✅ Required: Protein selected</li>
                        <li>✅ Required: Variable selected</li>
                        <li>➤ Optional: Use the Update Labels option to customize label text or remove samples (optional)</li>
                        <li>➤ Optional: Use the Reorder Samples option to change sample display order (optional)</li>
                    </ul>
                """
        elif self._protein_selected:
            # Only protein is selected
            self.steptwo_output_html_message = """
                <div style='padding: 10px; background-color: #fff3e0; border-left: 5px solid #ff9800; margin: 10px 0;'>
                    <h3>Step 2: Plot Controls</h3>
                    <p>Protein selected! Next steps:</p>
                    <ul style="list-style-type: none;">
                        <li>✅ Protein selected</li>
                        <li>➤ Required: Select a grouping variable from the dropdown</li>
                        <li>➤ Optional: Update Labels and Reorder Samples will be available after selecting a variable (optional)</li>
                    </ul>
                </div>
                """
        else:
            # Neither protein nor variable is selected
            self.steptwo_output_html_message = """
                <div style='padding: 10px; background-color: #fff3e0; border-left: 5px solid #ff9800; margin: 10px 0;'>
                    <h3>Step 2: Plot Controls</h3>
                    <p>Please make selections to continue:</p>
                    <ul style="list-style-type: none;">
                        <li>➤ Required: Select a protein from the dropdown</li>
                        <li>➤ Required: Then select a grouping variable</li>
                        <li>➤ Optional: Update Labels and Reorder Samples options will become available after selecting protein and variable</li>
                    </ul>
                </div>
                """
        
        # Update the display with proper cleanup
        if hasattr(self, 'steptwo_status_output'):
            with self.steptwo_status_output:
                clear_output(wait=True)
                display(HTML(self.steptwo_output_html_message))
     
    def consolidate_and_display_errors(self, errors):
        """
        Consolidate duplicate errors and display them in a clean, organized format.
        
        Args:
            errors (list): List of error messages from plotting functions
        """
        if not errors:
            return
            
        # Debug: Print errors being processed (can be removed later)
        #print(f"[DEBUG] Processing {len(errors)} errors:")
        #for i, error in enumerate(errors):
        #    print(f"  {i+1}. {error}")
            
        # Parse and categorize errors
        error_categories = {
            'missing_peptides': {},
            'missing_functions': {},
            'empty_dataframes': [],
            'processing_errors': [],
            'other_errors': []
        }
        
        for error in errors:
            try:
                if 'peptide columns not found' in error.lower():
                    # Extract variable name and missing peptides
                    if 'variable:' in error:
                        var_part = error.split('variable:')[1]
                        var_name = var_part.split('.')[0].strip()
                        
                        # Handle both "Missing:" and "Non-matching peptides:" formats
                        if 'Missing:' in error:
                            missing_part = error.split('Missing:')[1].strip()
                        elif 'Non-matching peptides:' in error:
                            missing_part = error.split('Non-matching peptides:')[1].strip()
                        else:
                            continue  # Skip if we can't find the missing items part
                            
                        # Parse the list of missing items
                        missing_items = missing_part.strip("[]").replace("'", "").split(", ")
                        missing_items = [item.strip() for item in missing_items]
                        
                        if 'Some peptide columns' in error:
                            category_key = 'partial_missing_peptides'
                        else:
                            category_key = 'all_missing_peptides'
                            
                        if category_key not in error_categories:
                            error_categories[category_key] = {}
                            
                        error_categories[category_key][var_name] = missing_items
                            
                elif 'selected functions not found' in error.lower():
                    # Extract variable name and missing functions
                    if 'variable:' in error:
                        var_part = error.split('variable:')[1]
                        var_name = var_part.split('.')[0].strip()
                        
                        if 'Missing:' in error:
                            missing_part = error.split('Missing:')[1].strip()
                            # Parse the list of missing items
                            missing_items = missing_part.strip("[]").replace("'", "").split(", ")
                            missing_items = [item.strip() for item in missing_items]
                            
                            if 'Some selected functions' in error:
                                category_key = 'partial_missing_functions'
                            else:
                                category_key = 'all_missing_functions'
                                
                            if category_key not in error_categories:
                                error_categories[category_key] = {}
                                
                            error_categories[category_key][var_name] = missing_items
                            
                elif 'dataframe is empty' in error.lower():
                    error_categories['empty_dataframes'].append(error)
                elif ('error' in error.lower() and any(keyword in error.lower() for keyword in ['processing', 'plotting', 'filtering', 'function filtering'])):
                    error_categories['processing_errors'].append(error)
                elif any(keyword in error.lower() for keyword in ['invalid', 'reselect', 'plotting options', 'variable options', 'too few peptides', 'checkbox must be selected']):
                    error_categories['other_errors'].append(error)
                elif 'dataframe is empty' in error.lower() or 'empty' in error.lower():
                    error_categories['empty_dataframes'].append(error)
                else:
                    error_categories['other_errors'].append(error)
            except Exception as e:
                #print(f"[DEBUG] Error processing error message: {error} - Exception: {str(e)}")
                error_categories['other_errors'].append(error)
        
        # Generate consolidated display
        html_content = []
        
        # Handle missing functions (most common case from your example)
        if 'partial_missing_functions' in error_categories and error_categories['partial_missing_functions']:
            html_content.append(self._create_missing_items_table(
                error_categories['partial_missing_functions'], 
                "Bioactive Functions Not Found", 
                "The following bioactive functions were not found in the data for the specified variables:",
                "warning"
            ))
            
        if 'all_missing_functions' in error_categories and error_categories['all_missing_functions']:
            html_content.append(self._create_missing_items_table(
                error_categories['all_missing_functions'], 
                "No Bioactive Functions Found", 
                "None of the selected bioactive functions were found in the data for these variables:",
                "error"
            ))
        
        # Handle missing peptides
        if 'partial_missing_peptides' in error_categories and error_categories['partial_missing_peptides']:
            html_content.append(self._create_missing_items_table(
                error_categories['partial_missing_peptides'], 
                "Peptide Intervals Not Found", 
                "The following peptide intervals were not found in the data for the specified variables:",
                "warning"
            ))
            
        if 'all_missing_peptides' in error_categories and error_categories['all_missing_peptides']:
            html_content.append(self._create_missing_items_table(
                error_categories['all_missing_peptides'], 
                "No Peptide Intervals Found", 
                "None of the selected peptide intervals were found in the data for these variables:",
                "error"
            ))
        
        # Handle other errors
        if error_categories['empty_dataframes']:
            html_content.append(self._create_simple_error_list(
                error_categories['empty_dataframes'], 
                "Data Issues", 
                "warning"
            ))
            
        if error_categories['processing_errors']:
            html_content.append(self._create_simple_error_list(
                error_categories['processing_errors'], 
                "Processing Errors", 
                "error"
            ))
            
        if error_categories['other_errors']:
            html_content.append(self._create_simple_error_list(
                error_categories['other_errors'], 
                "Other Issues", 
                "info"
            ))
        
        # Debug: Show categorization results
        #print(f"[DEBUG] Error categorization results:")
        #for category, items in error_categories.items():
        #    if items:
        #        if isinstance(items, dict):
        #            print(f"  {category}: {len(items)} variables with missing items")
        #            for var, missing in items.items():
        #                print(f"    {var}: {missing}")
        #        else:
        #            print(f"  {category}: {len(items)} errors")
        #            for error in items:
        #                print(f"    - {error}")
                        
        # Display consolidated errors
        if html_content:
            final_html = "<div style='margin: 15px 0; max-width: 1200px;'>" + "".join(html_content) + "</div>"
            display(HTML(final_html))
        else:
            print("[DEBUG] No HTML content generated - check if errors are being categorized correctly")
    
    def _create_missing_items_table(self, missing_data, title, description, error_type):
        """Create a table showing missing items by variable"""
        # Determine styling based on error type
        if error_type == "error":
            border_color = "#dc3545"
            bg_color = "#f8d7da"
            icon = "❌"
        elif error_type == "warning":
            border_color = "#ffc107"
            bg_color = "#fff3cd"
            icon = "⚠️"
        else:
            border_color = "#17a2b8"
            bg_color = "#d1ecf1"
            icon = "ℹ️"
        
        # Get all unique missing items across all variables
        all_missing_items = set()
        for items in missing_data.values():
            all_missing_items.update(items)
        all_missing_items = sorted(list(all_missing_items))
        
        html = f"""
        <div style='margin: 10px 0; padding: 15px; background-color: {bg_color}; border-left: 4px solid {border_color}; border-radius: 5px; max-width: 100%; overflow-x: auto;'>
            <h4 style='margin: 0 0 10px 0; color: {border_color};'>{icon} {title}</h4>
            <p style='margin: 0 0 15px 0;'>{description}</p>
            <table style='width: auto; min-width: 60%; max-width: 100%; border-collapse: collapse; background-color: white; border-radius: 3px; margin: 0;'>
                <thead>
                    <tr style='background-color: #f8f9fa;'>
                        <th style='padding: 10px 15px; text-align: left; border-bottom: 2px solid #dee2e6; font-weight: bold; width: 20%; min-width: 100px;'>Variable</th>
                        <th style='padding: 10px 15px; text-align: left; border-bottom: 2px solid #dee2e6; font-weight: bold; width: 80%;'>Missing Items</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for var_name, missing_items in missing_data.items():
            items_str = ", ".join(missing_items)
            html += f"""
                    <tr>
                        <td style='padding: 10px 15px; border-bottom: 1px solid #dee2e6; vertical-align: top; font-weight: 500; white-space: nowrap;'>{var_name}</td>
                        <td style='padding: 10px 15px; border-bottom: 1px solid #dee2e6; line-height: 1.4; word-wrap: break-word;'>{items_str}</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        """
        
        return html
    
    def _create_simple_error_list(self, errors, title, error_type):
        """Create a simple list for other types of errors"""
        if error_type == "error":
            border_color = "#dc3545"
            bg_color = "#f8d7da"
            icon = "❌"
        elif error_type == "warning":
            border_color = "#ffc107"
            bg_color = "#fff3cd"
            icon = "⚠️"
        else:
            border_color = "#17a2b8"
            bg_color = "#d1ecf1"
            icon = "ℹ️"
        
        html = f"""
        <div style='margin: 10px 0; padding: 15px; background-color: {bg_color}; border-left: 4px solid {border_color}; border-radius: 5px;'>
            <h4 style='margin: 0 0 10px 0; color: {border_color};'>{icon} {title}</h4>
            <ul style='margin: 0; padding-left: 20px;'>
        """
        
        for error in errors:
            html += f"<li style='margin: 5px 0;'>{error}</li>"
        
        html += """
            </ul>
        </div>
        """
        
        return html
                   
    def display(self):
        """Display the visualization interface"""
        # Get widgets from selector - this returns a tuple of widgets
        input_widgets_tuple = self.selector.display_widgets()
        
        # Create a proper VBox to contain the input widgets
        # This ensures they render as widgets rather than as text representation
        sel_input_widget = widgets.VBox(
            children=input_widgets_tuple,
            layout=widgets.Layout(
                height='400px',
                margin='0px',
                overflow='hidden',
                padding='0px',
                width='375px'
            )
        )
            
        # Create label and update section
        label_box = widgets.VBox([
                widgets.HTML(value="<u>Update Labels (optional):</u>"),
                self.selector.label_widgets_container,
                self.selector.update_label_button,
                self.selector.message_output_label],
            layout=widgets.Layout(
                width='620px',
                max_height='400px',
                max_width = "620px",
                overflow='auto',
                padding='0px',
                margin='0px 0'
            )
        )
        """
        # Display Step 1: Upload Data
        display(self.stepone_status_output)
        display(self.data_transformer.upload_widgets)
        
        # Display Step 2: Plot Controls
        display(self.steptwo_status_output)
        display(widgets.HTML("<h3><u>Plot Controls:</u></h3>"))
        display(widgets.HBox([sel_input_widget, label_box],
            layout=widgets.Layout(width='1000px',
                                   height='400px',
                                   overflow='auto',
                                   padding='0px',
                                   margin='0px 0px')
        ))
        
        # Display reorder samples section (part of Step 2)
        display(self.selector.update_order_initial_layout)
        
        # Display Step 3: Plotting Options
        display(self.stepthree_status_output)
        
        # Display plot layout and output
        display(self.app.get_layout())
        display(self.app.plot_output)"""
        # Create the VBox container with your widgets
        vbox_container = widgets.VBox([
            self.stepone_status_output,
            self.data_transformer.upload_widgets,
            self.steptwo_status_output,
            widgets.HBox(
                [sel_input_widget, label_box],
                layout=widgets.Layout(
                    width='1000px',
                    height='400px',
                    overflow='auto',
                    padding='0px',
                    margin='0px 0px'
                )
            ),
            self.selector.update_order_initial_layout,
            self.stepthree_status_output,
            self.app.get_layout()
        ], layout=widgets.Layout(
            width='1000px',
            max_width='1000px',
            height='auto',
            overflow='hidden'
        ))

        # Display the VBox container
        display(vbox_container)
        
        display(self.app.plot_output)

    def _check_required_data(self):
        """Check if we have the minimum required data to proceed"""
        has_merged = (hasattr(self.data_transformer, 'merged_df') and 
                     isinstance(self.data_transformer.merged_df, pd.DataFrame) and 
                     not self.data_transformer.merged_df.empty)
        
        has_groups = (hasattr(self.data_transformer, 'group_data_dict') and 
                     isinstance(self.data_transformer.group_data_dict, dict) and 
                     len(self.data_transformer.group_data_dict) > 0)
        
        has_proteins = (hasattr(self.data_transformer, 'protein_dict') and 
                       isinstance(self.data_transformer.protein_dict, dict) and 
                       len(self.data_transformer.protein_dict) > 0)
        has_fasta_files = self.data_transformer.fasta_file_uploaded_placeholder

        has_uniprot_search = self.data_transformer.uniprot_search.value

        return has_merged, has_groups, has_proteins, has_fasta_files, has_uniprot_search