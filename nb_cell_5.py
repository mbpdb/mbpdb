class HeatmapPlotHandler:
    def __init__(self, data_transformer):
        self.data_transformer = data_transformer
        self.selector = None  # Initialize to None, will be set later
        # Initialize other attributes
        self.ms_average_choice = 'yes'
        self.bio_or_pep = 'no'
        self.selected_bio_or_pep = []
        self.selected_functions = []
        self.selected_peptides = []
        self.plot_heatmap = 'yes'
        self.plot_zero = 'no'
        self.plot_output = widgets.Output()

        # Create plotting widgets
        self.create_plotting_widgets()
        self.display_plotting_options()
        
        # Attach observers to its own widgets
        self.peptide_filter_radio.observe(self.on_filter_type_change, names='value')
        self.ms_average_choice_dropdown.observe(self.on_dropdown_change, names='value')
        self.specific_select_multiple.observe(self.on_dropdown_change, names='value')
        self.bio_or_pep_dropdown.observe(self.on_selection_change, names='value')
        self.bio_or_pep_dropdown.observe(self.on_bio_or_pep_change, names='value')
        self.bio_or_pep_dropdown.observe(self.on_dropdown_change, names='value')
        self.log_transform_checkbox.observe(self._on_log_transform_change, names='value')
        # Attach button click events
        self.update_button.on_click(self.on_update_plot_clicked)
        self.save_button.on_click(self.on_save_plot_clicked)

        self._data_change_observer_registered = False
        
        # Initialize callback reference
        self._on_data_changed_callback = None
    
    # 2. Add this new method to HeatmapPlotHandler:

    def _on_log_transform_change(self, change):
        """Handle log transform checkbox changes and update y-axis label automatically"""
        if change['new']:  # Log transform enabled
            # Update y-axis label to include log10 notation
            if hasattr(self, 'yaxis_label_input'):
                current_label = self.yaxis_label_input.value
                # Only add log10 notation if it's not already there
                if "log₁₀" not in current_label and "log10" not in current_label:
                    self.yaxis_label_input.value = f"log₁₀(Averaged Peptide Abundance)"
        else:  # Log transform disabled
            # Reset to default y-axis label
            if hasattr(self, 'yaxis_label_input'):
                self.yaxis_label_input.value = "Averaged Peptide Abundance"
                
    def on_bio_or_pep_change(self, change):
        """Handle bio_or_pep dropdown changes and refresh specific options."""
        if change['type'] == 'change' and change['name'] == 'value':
            self.bio_or_pep = change['new']
            # Immediately refresh the specific options when bio_or_pep changes
            self._refresh_specific_options()    
                
    def _refresh_specific_options(self):
        """Refresh the specific options based on current data and bio_or_pep selection."""
        # Early return if essential components are missing
        if (not hasattr(self, 'available_data_variables_dict') or 
            not self.available_data_variables_dict or
            not hasattr(self, 'specific_select_multiple')):
            return
        
        try:
            # Store current selection to preserve it if still valid
            current_selection = list(self.specific_select_multiple.value) if hasattr(self.specific_select_multiple, 'value') else []
            
            # Initialize containers for unique values
            unique_functions = set()
            unique_peptides = set()

            # Aggregate unique functions and peptides from ALL available data variables
            for var in self.available_data_variables_dict:
                # Process function data for this variable
                if 'function_heatmap_df' in self.available_data_variables_dict[var]:
                    df = self.available_data_variables_dict[var]['function_heatmap_df']
                    if df is not None and not df.empty:
                        df_copy = df.copy()
                        df_copy.replace('0', 0, inplace=True)
                        
                        # Extract all functions
                        for col in df_copy.columns:
                            for cell in df_copy[col]:
                                if pd.notna(cell) and cell != 0:
                                    cell_str = str(cell)
                                    if ';' in cell_str:
                                        unique_functions.update([f.strip() for f in cell_str.split(';')])
                                    else:
                                        unique_functions.add(cell_str)
                
                # Process heatmap data for peptide intervals
                if 'heatmap_df' in self.available_data_variables_dict[var]:
                    heatmap_df = self.available_data_variables_dict[var]['heatmap_df']
                    if heatmap_df is not None and not heatmap_df.empty:
                        columns_with_data = []
                        for col in heatmap_df.columns:
                            if col not in ['AA', 'count', 'average']:  # Skip metadata columns
                                col_data = heatmap_df[col].dropna()
                                if not col_data.empty:
                                    try:
                                        numeric_data = pd.to_numeric(col_data, errors='coerce').dropna()
                                        if not numeric_data.empty and numeric_data.sum() != 0:
                                            columns_with_data.append(col)
                                    except Exception:
                                        if (col_data != 0).any():
                                            columns_with_data.append(col)
                        unique_peptides.update(columns_with_data)
            
            # Get current bio_or_pep value
            current_bio_or_pep = getattr(self, 'bio_or_pep', 'no')
            if hasattr(self, 'bio_or_pep_dropdown'):
                current_bio_or_pep = self.bio_or_pep_dropdown.value
                
            # Update widget based on current dropdown choice
            if current_bio_or_pep == '1':  # Peptide Intervals
                unique_peptides_list = sorted(list(unique_peptides), key=get_interval_start)
                new_options = [(peptide, peptide) for peptide in unique_peptides_list]
                self.specific_select_multiple.options = new_options
                self.specific_select_multiple.disabled = False
                
                # Preserve valid selections
                valid_selection = [item for item in current_selection if item in unique_peptides_list]
                self.specific_select_multiple.value = tuple(valid_selection)
                
            elif current_bio_or_pep == '2':  # Bioactive Functions
                unique_functions_list = sorted(list(unique_functions))
                new_options = [(function, function) for function in unique_functions_list]
                self.specific_select_multiple.options = new_options
                self.specific_select_multiple.disabled = False
                
                # Preserve valid selections
                valid_selection = [item for item in current_selection if item in unique_functions_list]
                self.specific_select_multiple.value = tuple(valid_selection)
                
            else:  # 'no' option
                self.specific_select_multiple.options = []
                self.specific_select_multiple.value = ()
                self.specific_select_multiple.disabled = True
        
            if self.data_transformer.merged_df['function'].isna().all():
                self.peptide_filter_radio.options = [('All Peptides', 'all-peptides')]
                self.peptide_filter_radio.value = 'all-peptides'
                self.bio_or_pep_dropdown.options=[('None', 'no'), ('Peptide Intervals', '1')]
            else:
                self.peptide_filter_radio.options = [('All Peptides', 'all-peptides'), 
                                                    ('All Functional Peptides', 'bioactive-only'),
                                                    ('Selected Functional Peptides', 'functional-only')]
                #self.peptide_filter_radio.value = 'all-peptides'
                self.bio_or_pep_dropdown.options=[('None', 'no'), ('Peptide Intervals', '1'), ('Bioactive Functions', '2')]

        except Exception as e:
            # Handle any errors during option refresh
            print(f"Error refreshing specific options: {e}")  # Enable for debugging
            pass

    def on_data_change_observer(self, change=None):
        """Observer method called when data selections change (groups/proteins)."""
        try:
            # Update the available data reference
            if (hasattr(self, 'data_handler') and self.data_handler and 
                hasattr(self.data_handler, 'selector') and self.data_handler.selector and
                hasattr(self.data_handler.selector, 'available_data_variables_dict')):
                self.available_data_variables_dict = self.data_handler.selector.available_data_variables_dict
            
            # Only refresh if we have the necessary widgets and data
            if (hasattr(self, 'specific_select_multiple') and 
                hasattr(self, 'available_data_variables_dict') and 
                self.available_data_variables_dict):
                # Refresh the specific options based on new data
                self._refresh_specific_options()
        except Exception as e:
            # Silently handle errors to prevent widget update failures
            # You can uncomment the print below for debugging
            # print(f"Observer error: {e}")
            pass

    def refresh_specific_options_external(self):
        """External method to refresh specific options from data handler"""
        if hasattr(self, '_refresh_specific_options'):
            self._refresh_specific_options()

    def set_data_handler(self, data_handler):
        """Set the reference to the data handler"""
        self.data_handler = data_handler
        
        # Set the callback BEFORE updating available_data_variables_dict
        self.available_data_variables_dict = data_handler.selector.available_data_variables_dict
        
        # Set up bidirectional reference
        data_handler._plot_handler = self
        
        # Connect to the selector
        if hasattr(data_handler, 'selector') and data_handler.selector:
            self.selector = data_handler.selector
            
            # IMPORTANT: Set up the callback for data changes
            self.selector._on_data_changed_callback = self.refresh_specific_options_external
            
            # Connect observers for protein and variable selection changes
            if hasattr(self.selector, 'protein_selector'):
                self.selector.protein_selector.observe(self.add_group_change, names='value')
                # ADD: Observer for specific options refresh
                self.selector.protein_selector.observe(self.on_selection_data_change, names='value')
                
            if hasattr(self.selector, 'var_key_dropdown'):
                self.selector.var_key_dropdown.observe(self.add_group_change, names='value')  
                # ADD: Observer for specific options refresh
                self.selector.var_key_dropdown.observe(self.on_selection_data_change, names='value')

    def on_selection_data_change(self, change):
        """Called when protein or variable selections change."""
        
        # Refresh specific options after data has been updated
        if hasattr(self, 'available_data_variables_dict') and self.available_data_variables_dict:
            self._refresh_specific_options()
            
    def add_group_change(self, change=None):
        # Only enable widgets if there are valid selections
        if (hasattr(self.selector, 'protein_selector') and 
            hasattr(self.selector, 'var_key_dropdown') and
            self.selector.protein_selector.value and 
            len(self.selector.protein_selector.value) > 0 and
            self.selector.var_key_dropdown.value and 
            len(self.selector.var_key_dropdown.value) > 0):
            
            # Enable specific widgets
            self.ms_average_choice_dropdown.disabled = False
            self.bio_or_pep_dropdown.disabled = False
            self.specific_select_multiple.disabled = False
            self.log_transform_checkbox.disabled = False
            self.plot_orientation.disabled = False
            self.peptide_filter_radio.disabled = False
            self.update_button.disabled = False
            self.legend_title_input_1.disabled = False
            self.legend_title_input_2.disabled = False
            self.legend_title_input_3.disabled = False
            self.xaxis_label_input.disabled = False
            self.yaxis_label_input.disabled = False
            self.yaxis_position.disabled = False
            self.manual_y_axis_checkbox.disabled = False
            self.hm_selected_color.disabled = False
            self.lp_selected_color.disabled = False
            self.avglp_selected_color.disabled = False

            self.update_button.disabled = False

    def on_selection_change(self, change):
        """Handle changes in selection with numerically sorted peptide intervals."""
        if change['type'] == 'change' and change['name'] == 'value':
            self.bio_or_pep = self.bio_or_pep_dropdown.value
            self._refresh_specific_options()

        
            # Initialize containers for unique values
            unique_functions = set()
            unique_peptides = set()

            # Aggregate unique functions and peptides from ALL available data variables
            for var in self.available_data_variables_dict:
                # Process function data for this variable
                df = self.available_data_variables_dict[var]['function_heatmap_df']
                df.replace('0', 0, inplace=True)  # Standardize zero representations
                unique_functions.update(extract_non_zero_non_nan_values(df))
                
                # Process Abundance data for peptide intervals for this variable
                abs_df = self.available_data_variables_dict[var]['heatmap_df']
                # First, get all non-special columns
                potential_peptide_columns = [col for col in abs_df.columns 
                                            if col not in ['AA', 'count', 'average']]
                
                # Convert all potential columns to numeric at once
                numeric_df = abs_df[potential_peptide_columns].apply(pd.to_numeric, errors='coerce')
                
                # Find columns with any non-zero values for this variable
                columns_with_data = numeric_df.columns[(numeric_df != 0).any()].tolist()
                #print(f" DEBUG: var={var}, columns_with_data: {columns_with_data}")

                # Update unique_peptides with intervals from this variable
                unique_peptides.update(columns_with_data)    
            
            # Update widget based on dropdown choice
            if self.bio_or_pep == '1':  # Peptide Intervals
                # Convert to list and sort by the first number in the interval
                unique_peptides_list = sorted(list(unique_peptides), key=get_interval_start)
                #print(f" DEBUG: unique_peptides_list: {unique_peptides_list}")
                self.specific_select_multiple.options = [(peptide, peptide) for peptide in unique_peptides_list]
                self.specific_select_multiple.disabled = False  # Enable the widget
                #self.specific_select_multiple.layout.display = 'block'  # Make it visible
                
            elif self.bio_or_pep == '2':  # Bioactive Functions
                unique_functions_list = sorted(list(unique_functions))
                self.specific_select_multiple.options = [(function, function) for function in unique_functions_list]
                self.specific_select_multiple.disabled = False  # Enable the widget
                #self.specific_select_multiple.layout.display = 'block'  # Make it visible
                
            else:  # 'no' option
                self.specific_select_multiple.options = [""]
                self.specific_select_multiple.disabled = True  # Disable the widget
                #self.specific_select_multiple.layout.display = 'none'  # Hide it 

    def display_plotting_options(self):
        dropdown_layout = widgets.Layout(width='90%')
        self.plot_message = widgets.HTML("<h3><u>Visualization Settings</u></h3>")

        # Create the description label
        description_label = f'Plot Filter:  \n\n'

        # Add radio buttons for peptide filtering
        self.peptide_filter_radio = widgets.RadioButtons(
            options=[('All Peptides', 'all-peptides'), 
                    ('All Functional Peptides', 'bioactive-only'),
                    ('Selected Functional Peptides', 'functional-only')],
            value='all-peptides',  # default value
            description=description_label,
            disabled=True,  # Start disabled
            style={'description_width': 'initial'},
            layout=dropdown_layout
        )

        self.ms_average_choice_dropdown = widgets.Dropdown(
            options=['yes', 'no', 'only'],
            description='Plot Averaged Data:',
            value='yes',
            disabled=True,  # Start disabled
            style={'description_width': 'initial'},
            layout=dropdown_layout,
        )
        
        self.ms_average_choice = self.ms_average_choice_dropdown.value
        
        self.bio_or_pep_dropdown = widgets.Dropdown(
            options=[('None', 'no'), ('Peptide Intervals', '1'), ('Bioactive Functions', '2')],
            description='Plot Specific Peptides:',
            disabled=True,  # Start disabled
            style={'description_width': 'initial'},
            layout=dropdown_layout,
        )
        
        self.specific_select_multiple = widgets.SelectMultiple(
            options=[],
            description='Specific Options:',
            disabled=True,  # Start disabled
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='90%')  
        )

        self.log_transform_checkbox = widgets.Checkbox(
            value=False,
            description='Log Transform Y-axis:',
            disabled=True,  # Start disabled
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='90%')  
        )

    def update_legend_widget(self):
        # Determine which legend title to use for input 3
        if self.bio_or_pep == '1':  # Peptide intervals
            title_index = 3  # Use legend title for peptide intervals
        elif self.bio_or_pep == '2':  # Bioactive functions
            title_index = 2  # Use legend title for bioactive functions
        else:  # bio_or_pep == 'no' or any other case
            title_index = 4  # Use legend title for average
        
        # Update input 3
        title_text = legend_title[title_index]
        self.legend_title_input_3.value = title_text
        self.legend_title_input_3.description = f'Legend title ({title_text})'

        # Show/hide input 3 based on conditions
        if ((self.ms_average_choice == 'yes' and self.bio_or_pep == 'no') or
            (self.ms_average_choice == 'only')):
            # For average only, show input 3 with average title
            self.legend_title_input_3.value = legend_title[4]  # Average title
            self.legend_title_input_3.description = f'Legend title ({legend_title[4]})'
        elif (self.ms_average_choice == 'no' and self.bio_or_pep == '2'):
            # For bioactive functions only, show input 3 with function title

            self.legend_title_input_3.value = legend_title[2]  # Function title
            self.legend_title_input_3.description = f'Legend title ({legend_title[2]})'
        elif (self.ms_average_choice == 'no' and self.bio_or_pep == '1'):
            # For peptide intervals only, show input 3 with interval title
            self.legend_title_input_3.value = legend_title[3]  # Interval title
            self.legend_title_input_3.description = f'Legend title ({legend_title[3]})'
        elif (self.ms_average_choice == 'yes' and self.bio_or_pep == '1'):
            # For peptide intervals with average
            self.legend_title_input_3.value = legend_title[3]  # Interval title
            self.legend_title_input_3.description = f'Legend title ({legend_title[3]})'
        elif (self.ms_average_choice == 'yes' and self.bio_or_pep == '2'):
            # For bioactive functions with average
            self.legend_title_input_3.value = legend_title[2]  # Function title
            self.legend_title_input_3.description = f'Legend title ({legend_title[2]})'

    def _on_manual_y_axis_change(self, change):
        """Handle manual y-axis checkbox changes"""
        if change['new']:  # Manual scaling enabled
            self.y_min_input.disabled = False
            self.y_max_input.disabled = False
            # Set reasonable default values if available data exists
            self._update_manual_y_axis_defaults()
        else:  # Manual scaling disabled
            self.y_min_input.disabled = True
            self.y_max_input.disabled = True
            
    def _update_manual_y_axis_defaults(self):
        """Update the default values for manual y-axis inputs based on current data"""
        import numpy as np
        try:
            if hasattr(self, 'available_data_variables_dict') and self.available_data_variables_dict:
                # Extract min and max values from the current data
                min_values = []
                max_values = []
                
                for var_data in self.available_data_variables_dict.values():
                    if 'bioactive_peptide_abs_df' in var_data:
                        df = var_data['bioactive_peptide_abs_df']
                        # Get numeric columns only
                        numeric_cols = df.select_dtypes(include=[np.number]).columns
                        if len(numeric_cols) > 0:
                            df_numeric = df[numeric_cols]
                            # Filter out zeros and negative values for better defaults
                            df_positive = df_numeric[df_numeric > 0]
                            if not df_positive.empty:
                                min_values.append(df_positive.min().min())
                                max_values.append(df_positive.max().max())
                
                if min_values and max_values:
                    overall_min = min(min_values)
                    overall_max = max(max_values)
                    
                    # Set defaults with some padding
                    self.y_min_input.value = overall_min * 0.9  # 10% below minimum
                    self.y_max_input.value = overall_max * 1.1  # 10% above maximum
                else:
                    # Fallback defaults
                    self.y_min_input.value = 0.0
                    self.y_max_input.value = 1.0
            else:
                # No data available, use defaults
                self.y_min_input.value = 0.0
                self.y_max_input.value = 1.0
        except Exception as e:
            # In case of any error, use safe defaults
            self.y_min_input.value = 0.0
            self.y_max_input.value = 1.0

    def create_plotting_widgets(self):
        # Generate filenames
        #generate_filenames(self)

        # Layouts
        #description_layout_invisible = widgets.Layout(width='90%', overflow = 'visible')
        description_layout = widgets.Layout(width='80%', overflow = 'visible')
        dropdown_layout = widgets.Layout(width='50%', overflow = 'visible')
        #dropdown_layout_large = widgets.Layout(width='90%', overflow = 'visible')

        # Color Widgets
        self.hm_selected_color = widgets.Dropdown(
            options=valid_gradient_cmaps,
            value=default_hm_color,
            description='Heatmap:',
            disabled=True,  # Start disabled
            layout=dropdown_layout,
            style={'description_width': 'initial'}
        )

        self.lp_selected_color = widgets.Dropdown(
            options=valid_discrete_cmaps,
            value=default_lp_color,
            description='Line Plot:',
            disabled=True,  # Start disabled
            layout=dropdown_layout,
            style={'description_width': 'initial'}
        )

        self.avglp_selected_color = widgets.Dropdown(
            options=valid_discrete_cmaps,
            disabled=True,  # Start disabled
            value=default_avglp_color,
            description='Avg Line Plot:',
            layout=dropdown_layout,
            style={'description_width': 'initial'}
        )

        self.color_message = widgets.HTML("<h3><u>Appearance Settings:</u></h3>")
        
        self.color_widget_box = widgets.VBox([
            self.color_message,
            self.hm_selected_color,
            self.lp_selected_color,
            self.avglp_selected_color
        ])
                
        # Figure Label Widgets - default value will be updated when protein selector is populated
        self.xaxis_label_input = widgets.Text(
            value="Protein Sequence",  # Default, will be updated by _populate_selectors
            description='x-axis label:',
            disabled=True,  # Start disabled
            layout=description_layout,
            style={'description_width': 'initial'}
        )

        def update_x_label():
            if hasattr(self.data_transformer, 'protein_name_short'):
                new_label = f"{self.data_transformer.protein_name_short} Sequence"
                self.xaxis_label_input.value = new_label

        # Set up observer for selector changes
        if hasattr(self.data_transformer, 'observe'):
            self.data_transformer.observe(lambda change: update_x_label(), names=['protein_name_short'])

            
        self.legend_title_input_1 = widgets.Text(
            value=legend_title[0],  # Will be set dynamically
            description=f'Legend title ({legend_title[0]}):',
            layout=description_layout,
            style={'description_width': 'initial'},
            disabled=True  # Start disabled
        )
        
        self.legend_title_input_2 = widgets.Text(
            value=legend_title[1],
            disabled=True,  # Start disabled
            description=f'Legend title ({legend_title[1]}):',
            layout=description_layout,
            style={'description_width': 'initial'}
        )
        
        self.legend_title_input_3 = widgets.Text(
            value=legend_title[4], # avera
            disabled=True,  # Start disabled
            description=f'Legend title ({legend_title[4]}):',
            layout=description_layout,
            style={'description_width': 'initial'}
        )

        self.yaxis_label_input = widgets.Text(
            value="Averaged Peptide Abundance",
            description='y-axis label:',
            disabled=True,  # Start disabled
            layout=description_layout,
            style={'description_width': 'initial'}
        )

        self.yaxis_position = widgets.IntSlider(
            value=0,
            min=-10,
            max=10,
            step=1,
            layout=description_layout,
            disabled=True,  # Start disabled
            description='y-axis title position:',
            style={'description_width': 'initial'}
        )
        
        # Manual Y-axis scaling widgets
        self.manual_y_axis_checkbox = widgets.Checkbox(
            value=False,
            description='Manual Y-axis scaling',
            disabled=True,  # Start disabled
            style={'description_width': 'initial'}
        )
        
        self.y_min_input = widgets.FloatText(
            value=0.0,
            description='Y-axis min:',
            disabled=True,  # Start disabled
            layout=description_layout,
            style={'description_width': 'initial'}
        )
        
        self.y_max_input = widgets.FloatText(
            value=1.0,
            description='Y-axis max:',
            disabled=True,  # Start disabled
            layout=description_layout,
            style={'description_width': 'initial'}
        )
        
        # Set up observer for manual y-axis checkbox
        self.manual_y_axis_checkbox.observe(self._on_manual_y_axis_change, names='value')
        
        self.plot_port = widgets.Checkbox(
            value=False,
            description='Plot Portrait Graph',
            disabled=True,
            icon='check',
            style={'description_width': 'initial'}
        )

        self.plot_land = widgets.Checkbox(
            value=True,
            description='Plot Landscape Graph',
            disabled=False,
            icon='check',
            style={'description_width': 'initial'}
        )
            
        self.plot_orientation = widgets.RadioButtons(
            description='Plot Orientation:',
            options=['Landscape', 'Portrait'],
            value='Landscape',  # Default selection
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='300px', height='auto'),
            disabled=True,
            indent=True  # Keeps options aligned with description instead of appearing below
        )
        self.figure_label_box = widgets.VBox([
            #self.figure_label_message,
            self.xaxis_label_input,
            self.yaxis_label_input,
            self.yaxis_position,
            self.manual_y_axis_checkbox,
            self.y_min_input,
            self.y_max_input,
            self.legend_title_input_1,
            self.legend_title_input_2,
            self.legend_title_input_3,
        ], layout=widgets.Layout(
        width='500px',
        #height='370px', # with plot_toggle_widget
        height='300px',  # Increased height to accommodate new widgets
        margin='0px')
        )

        # Add buttons for update and save plot
        self.update_button = widgets.Button(
            description='Generate/Update',
            button_style='success',
            tooltip='Click to update the plot',
            disabled=True,
            icon='refresh'
        )

        self.save_button = widgets.Button(
            description='Save Plot',
            button_style='info',
            tooltip='Click to save the plot',
            icon='save',
            disabled = True
        )

        self.update_save_box = widgets.HBox([self.update_button, self.save_button], layout=widgets.Layout(width='300px'))

        self.legend_title_input_1.disabled = True
        self.legend_title_input_2.disabled = True
        self.legend_title_input_3.disabled = True

    def on_dropdown_change(self, change):
        self.ms_average_choice = self.ms_average_choice_dropdown.value
        self.bio_or_pep = self.bio_or_pep_dropdown.value
        if self.bio_or_pep != 'no':
            self.selected_bio_or_pep = self.specific_select_multiple.value
        else:
            self.selected_bio_or_pep = []

        if self.bio_or_pep != 'no' and self.selected_bio_or_pep:
            self.selected_peptides, self.selected_functions = proceed_with_label_specific_options(self.selected_bio_or_pep, self.bio_or_pep)
        else:
            self.selected_peptides, self.selected_functions = [], []

        self.update_legend_widget()

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

        # Return infinity for invalid formats to put them at the end

    def on_filter_type_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            # Update the selector's filter type
            self.selector.update_filter_type(change['new'])
        
    def update_data(self, selector):
        """Update the plot handler with new data from selector"""
        if not selector:
            return
                
        # Update only the essential data structures
        essential_attrs = [
            'available_data_variables_dict',
            'user_protein_id',
            'protein_name_short',
            'selected_protein'
        ]
        
        for attr in essential_attrs:
            if hasattr(selector, attr):
                setattr(self, attr, getattr(selector, attr))
                # Update x-axis label when protein name changes
                if attr == 'protein_name_short' and hasattr(self, 'xaxis_label_input'):
                    new_label = f"{getattr(selector, attr)} Sequence"
                    self.xaxis_label_input.value = new_label
                    #print(f"DEBUG: Updated x-axis label to: {new_label}")  # Debug print
                if attr == 'user_protein_id':
                    self.user_protein_id = getattr(selector, attr)
                    
    def update_protein_name(self, new_name):
        """Update the protein name and x-axis label"""
        self.protein_name_short = new_name
        if hasattr(self, 'xaxis_label_input'):
            new_label = f"{new_name} Sequence" if new_name else "Protein Sequence"
            self.xaxis_label_input.value = new_label
            #print(f"DEBUG: Updated x-axis label via update_protein_name to: {new_label}")  # Debug print

    def validate_selected_options(self):
        """
        Validate if selected peptide intervals or bioactive functions are available
        for the current variable selection. Returns (is_valid, error_messages).
        """
        if not hasattr(self, 'available_data_variables_dict') or not self.available_data_variables_dict:
            return True, []  # No validation needed if no data
        
        error_messages = []
        
        # Check peptide intervals (bio_or_pep == '1')
        if self.bio_or_pep == '1' and self.selected_peptides:
            unavailable_peptides = []
            
            for var_name, var_data in self.available_data_variables_dict.items():
                # Check which selected peptides are not available in this variable
                if 'heatmap_df' in var_data:
                    available_columns = var_data['heatmap_df'].columns.tolist()
                    for peptide in self.selected_peptides:
                        if peptide not in available_columns:
                            if peptide not in unavailable_peptides:
                                unavailable_peptides.append(peptide)
            
            if unavailable_peptides:
                peptide_list = ', '.join([f"<b>{p}</b>" for p in unavailable_peptides])
                error_messages.append(
                    f"<b>Peptide Interval Error:</b> The following peptide intervals are not available "
                    f"for the selected variable(s): {peptide_list}.<br>"
                    f"These intervals may be available for other variables but not for your current selection."
                )
        
        # Check bioactive functions (bio_or_pep == '2')
        elif self.bio_or_pep == '2' and self.selected_functions:
            unavailable_functions = []
            
            for var_name, var_data in self.available_data_variables_dict.items():
                # Check which selected functions are not available in this variable
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
                        for function in self.selected_functions:
                            if function not in present_functions:
                                if function not in unavailable_functions:
                                    unavailable_functions.append(function)
            
            if unavailable_functions:
                function_list = ', '.join([f"<b>{f}</b>" for f in unavailable_functions])
                error_messages.append(
                    f"<b>Bioactive Function Error:</b> The following bioactive functions are not available "
                    f"for the selected variable(s): {function_list}.<br>"
                    f"These functions may be available for other variables but not for your current selection."
                )
        
        return len(error_messages) == 0, error_messages
                                                    
    def on_update_plot_clicked(self, b):
        with self.plot_output:
            try:
                # Clear any existing plots and free memory
                self.plot_output.clear_output(wait=True)
                plt.close('all')  
                
                # Reset figure references
                self.fig_port = None
                self.fig_land = None
                self.save_button.disabled = False

                # Force garbage collection
                if self.plot_orientation.value == 'Landscape':
                    self.plot_land.value = True
                    self.plot_port.value = False
                else:
                    self.plot_land.value = False
                    self.plot_port.value = True
                    
                gc.collect()
                

                
                # Validate selected options before plotting
                is_valid, error_messages = self.validate_selected_options()
                # Note: Validation errors are now handled by the plotting functions themselves
                
                # Debug print for all variables being passed to update_plot
                #print(
                #     "DEBUG: Variables being passed to update_plot:\n"
                #     f"available_data_variables_dict: {self.available_data_variables_dict.keys()}\n"
                #     f"ms_average_choice: {self.ms_average_choice}\n"
                #     f"bio_or_pep: {self.bio_or_pep}\n"
                #     f"selected_peptides: {self.selected_peptides}\n"
                #     f"selected_functions: {self.selected_functions}\n"
                #     f"hm_selected_color: {self.hm_selected_color.value}\n"
                #     f"lp_selected_color: {self.lp_selected_color.value}\n"
                #     f"avglp_selected_color: {self.avglp_selected_color.value}\n"
                #     f"xaxis_label: {self.xaxis_label_input.value}\n"
                #     f"yaxis_label: {self.yaxis_label_input.value}\n"
                #     f"yaxis_position: {self.yaxis_position.value}\n"
                #     f"legend_title_1: {self.legend_title_input_1.value}\n"
                #     f"legend_title_2: {self.legend_title_input_2.value}\n"
                #     f"legend_title_3: {self.legend_title_input_3.value}\n"
                #     f"plot_land: {self.plot_land.value}\n"
                #     f"plot_port: {self.plot_port.value}\n"
                #     f"filter_type: {self.selector.filter_type}"
                #)
                
                # Call the update_plot function
                self.fig_port, self.fig_land, plot_errors, missing_notifications = update_plot(
                    self.available_data_variables_dict, 
                    self.ms_average_choice, 
                    self.bio_or_pep, 
                    self.selected_peptides, 
                    self.selected_functions, 
                    self.hm_selected_color.value, 
                    self.lp_selected_color.value, 
                    self.avglp_selected_color.value, 
                    self.xaxis_label_input.value, 
                    self.yaxis_label_input.value, 
                    self.yaxis_position.value, 
                    self.legend_title_input_1.value, 
                    self.legend_title_input_2.value, 
                    self.legend_title_input_3.value, 
                    self.plot_land.value, 
                    self.plot_port.value,
                    self.selector.filter_type,
                    self.log_transform_checkbox.value,
                    self.manual_y_axis_checkbox.value,
                    self.y_min_input.value,
                    self.y_max_input.value
                )
                
                # Display any errors that occurred during plotting using consolidated display
                if plot_errors:
                    # Use the data handler to access the consolidated error method
                    if hasattr(self, 'data_handler') and hasattr(self.data_handler, 'consolidate_and_display_errors'):
                        self.data_handler.consolidate_and_display_errors(plot_errors)
                    else:
                        # Fallback to original display if the method is not available
                        for error in plot_errors:
                            display(HTML(f'<div style="color: red; font-weight: bold; margin: 10px 0; padding: 10px; border: 1px solid red; border-radius: 5px; background-color: #ffe6e6;">'
                                        f'{error}'
                                        f'</div>'))
                # Display only valid figures
                if self.fig_port is not None and len(self.fig_port.axes) > 0:
                    display(HTML(f'<br><h2>Portrait Averaged Plot:</h2>'))
                    display(self.fig_port)

                if self.fig_land is not None and len(self.fig_land.axes) > 0:
                    display(HTML(f'<br><h2>Landscape Averaged Plot:</h2>'))
                    display(self.fig_land)
                if missing_notifications:
                    notification_html = "<div style='margin: 15px 0; padding: 15px; background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px;'>"
                    notification_html += "<h4 style='color: #856404; margin: 0 0 10px 0;'>ℹ️ Data Availability Information</h4>"
                    notification_html += "<p style='margin: 0 0 10px 0; color: #856404;'>The following data is not available for some variables but plotting will continue with available data:</p>"
                    notification_html += "<ul style='margin: 0; color: #856404;'>"
                    for notification in missing_notifications:
                        notification_html += f"<li>{notification}</li>"
                    notification_html += "</ul></div>"
                    display(HTML(notification_html))
            except Exception as e:
                # Display error message
                display(HTML(f'<br><b style="color:red;">Error generating plots: {str(e)}</b>'))
                traceback.print_exc()
                
            finally:
                # Always cleanup
                plt.close('all')

    def create_download_link(self, fig, filename):
        """Create a download button for the figure"""

        
        # Save figure to a temporary buffer.
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        
        # Create the download button
        download_button = widgets.Button(
            description=f'Download {filename}',
            button_style='info',
            icon='download'
        )
        
        # Encode the image
        b64 = base64.b64encode(buf.read()).decode()
        
        def on_button_clicked(b):
            # Create HTML with download link and click it
            download_link = f'<a href="data:image/png;base64,{b64}" download="{filename}" id="download_link_{filename}"></a>'
            display(HTML(download_link))
            display(HTML(f'''<script>
                document.getElementById("download_link_{filename}").click();
            </script>'''))
        
        # Set up the button click handler
        download_button.on_click(on_button_clicked)
        
        # Automatically trigger the click
        on_button_clicked(download_button)
        
        return download_button

    def on_save_plot_clicked(self, b):
        # Disable the save button temporarily to prevent multiple clicks
        b.disabled = True
        
        try:
            with self.plot_output:
                if (self.fig_port is None and self.fig_land is None) or \
                    (self.fig_port is not None and len(self.fig_port.axes) == 0 and 
                    self.fig_land is not None and len(self.fig_land.axes) == 0):
                    self.plot_output.clear_output(wait=True)
                    display(HTML("<div style='display: inline-block; margin: 10px 0;'><b style='color: red'>Please generate plots using the Update/Display button before saving.</b></div>"))
                    b.disabled = False  # Re-enable the button
                    return

                # Store existing figures before clearing
                port_fig = self.fig_port
                land_fig = self.fig_land
                
                # Clear previous output and show loading message
                self.plot_output.clear_output(wait=True)
                display(HTML("<div style='display: inline-block; margin: 10px 0;'><b style='color:blue'>Generating high resolution image for download. Please wait...</b></div>"))
                
                # Create filenames
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
        
                additional_vars_str = '_'.join(additional_vars)
                self.protein_filename_short = re.sub(r'[^\w-]', '-', self.protein_name_short)

                # Create and trigger downloads
                download_buttons = []
                if port_fig is not None and len(port_fig.axes) > 0:
                    self.filename_port = f'portrait_{self.selector.user_protein_id}_{self.protein_filename_short}_average-only'
                    port_button = self.create_download_link(port_fig, f"{self.filename_port}.png")
                    download_buttons.append(port_button)
                    
                if land_fig is not None and len(land_fig.axes) > 0:
                    self.filename_land = f'landscape_{self.selector.user_protein_id}_{self.protein_filename_short}_{additional_vars_str}'
                    land_button = self.create_download_link(land_fig, f"{self.filename_land}.png")
                    download_buttons.append(land_button)
                
                # Display final content
                self.plot_output.clear_output(wait=True)
                if download_buttons:
                    display(HTML("<div style='display: inline-block; margin: 10px 0;'><b style='color:green'>Success! Your plots have been downloaded automatically.</b></div>"))
                    
                    if port_fig is not None and len(port_fig.axes) > 0:
                        #display(HTML(f'<br><h2>Portrait Averaged Plot:</h2>'))
                        display(port_fig)
                        
                    if land_fig is not None and len(land_fig.axes) > 0:
                        #display(HTML(f'<br><h2>Landscape Averaged Plot:</h2>'))
                        display(land_fig)
                else:
                    display(HTML("<div style='display: inline-block; margin: 10px 0;'><p style='color: red;'>No plots were generated to download.</p></div>"))
                
        except Exception as e:
            self.plot_output.clear_output(wait=True)
            error_message = f"An error occurred while saving plots: {str(e)}"
            display(HTML(f"<div style='display: inline-block; margin: 10px 0;'><b style='color: red'>{error_message}</b></div>"))
        
        finally:
            # Always re-enable the button and cleanup
            b.disabled = False
            
    def get_layout(self):
        # Create a grid layout with 2 rows and 2 columns
        grid = GridspecLayout(
            1, 2,  # 2 rows, 2 columns
            width='900px', 
            height='auto',
            overflow='hidden',
            grid_gap='0px',  # Already set to zero
        )
        
        # Left column widgets
        left_column = VBox([
            self.plot_message,
            self.peptide_filter_radio,
            self.ms_average_choice_dropdown,
            self.bio_or_pep_dropdown,
            self.specific_select_multiple,
            widgets.HTML("<h3><u>Display and Export</u></h3>"),            
            widgets.HBox([self.plot_orientation, self.log_transform_checkbox], layout=widgets.Layout(
                max_width='300px',
                overflow='hidden'
            )),
            self.update_save_box
        ], layout=widgets.Layout(
            width='350px',
            margin='0px',
            padding='0px',
            overflow='hidden'
        ))
        
        # Right column widgets
        right_column = VBox([
            self.color_widget_box,
            self.figure_label_box,
        ], layout=widgets.Layout(
            width='450px',
            margin='0px',
            padding='0px',
            overflow='hidden'
        ))
        
        # Bottom row spanning both columns
        """
        bottom_row = VBox([
            widgets.HTML("<h3><u>Display and Export</u></h3>"),            
            widgets.HBox([self.plot_orientation, self.log_transform_checkbox], layout=widgets.Layout(
                max_width='300px',
                overflow='hidden'
            )),
            self.update_save_box
        ], layout=widgets.Layout(
            width='900px',
            height='auto',
            margin='0px',
            padding='0px',
            overflow='hidden'
        ))
        """
        # Place widgets in the grid
        grid[0, 0] = left_column    # First row, first column
        grid[0, 1] = right_column   # First row, second column
        #grid[1, 0:2] = bottom_row   # Second row, span both columns
        
        return grid