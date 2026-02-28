class DataTransformation(HasTraits):
    def __init__(self):
        super().__init__()
        self.merged_df = pd.DataFrame()
        self.protein_dict = {}
        self.group_data_dict = {}
        self.output_area = None
        self.merged_uploader = None
        self.fasta_uploader = None
        self.uniprot_client = None
        self.col_order = []
        self.uniprot_client = UniProtClient()  # Add this line
        self.fasta_file_uploaded_placeholder = False
        #self.merged_df = Instance(pd.DataFrame, allow_none=True)
        #self.group_data_dict = Instance(dict, allow_none=True)
        
    def create_download_link(self, file_path, label):
        """Create a download link for a file."""
        if os.path.exists(file_path):
            # Read file content and encode it as base64
            with open(file_path, 'rb') as f:
                content = f.read()
            b64_content = base64.b64encode(content).decode('utf-8')

            # Generate the download link HTML
            return widgets.HTML(f"""
                <a download="{os.path.basename(file_path)}" 
                    href="data:application/octet-stream;base64,{b64_content}" 
                    style="color: #0366d6; text-decoration: none; margin-left: 20px; font-size: 14px;">
                    {label}
                </a>
            """)
        else:
            # Show an error message if the file does not exist
            return widgets.HTML(f"""
                <span style="color: red; margin-left: 20px; font-size: 14px;">
                    File "{file_path}" not found!
                </span>
                """)

    def setup_data_loading_ui(self):
        """Initialize and display the data loading UI."""
        # Create file upload widgets
        self.merged_uploader = widgets.FileUpload(
            accept='.csv,.txt,.tsv,.xlsx',
            multiple=False,
            description='Upload Merged Data File',
            layout=widgets.Layout(width='300px'),
            style={'description_width': 'initial'}
        )

        self.fasta_uploader = widgets.FileUpload(
            accept='.fasta',
            multiple=True,
            disabled=True,
            description='Upload FASTA Files',
            layout=widgets.Layout(width='300px'),
            style={'description_width': 'initial'}
        )
        
        self.uniprot_search = widgets.Checkbox(
            value=True,
            description='Query UniProt for missing protein information',
            layout=widgets.Layout(width='325px'),
            disabled=True,
            style={'description_width': 'initial'}
        )

        self.output_area = widgets.Output()

        # Create individual upload boxes with example links
        merged_box = widgets.HBox([
            self.merged_uploader,
            self.create_download_link("examples/example_merged_dataframe.csv", "Example")
        ], layout=widgets.Layout(align_items='center'))

        fasta_box = widgets.HBox([
            self.fasta_uploader,
            self.create_download_link("examples/example_fasta.fasta", "Example")
        ], layout=widgets.Layout(align_items='center'))
        
        uniprot_box = widgets.VBox([
            widgets.HTML("<h4><u>Option 2: Import from UniProt:</u></h4>"),
            self.uniprot_search
        ])

        combined_box = widgets.HBox([
            widgets.VBox([
            widgets.HTML("<h4><u>Option 1: Upload Protein FASTA Files:</u></h4>"),
            fasta_box]),
            widgets.HTML("<div style='margin: 0 20px; line-height: 100px;'><b>OR</b></div>"),
            uniprot_box
            ], layout=widgets.Layout(
                width='850px',
                margin='0 0 0 0px'
            ))

        # Create left column with upload widgets
        self.upload_widgets  = widgets.VBox([
            widgets.HTML("<h4><u>Upload Peptidomic Data File:</u></h4>"),
            merged_box,
            combined_box,
            self.output_area
        ], layout=widgets.Layout(
            width='800px',
            margin='0 20px 0 0',
            overflow='hidden'
        ))

        # Register observers
        self.merged_uploader.observe(self._on_merged_upload_change, names='value')
        self.fasta_uploader.observe(self._on_fasta_upload_change, names='value')
        self.uniprot_search.observe(self._on_uniprot_search_change, names='value')

    def _clear_error_messages(self):
        """Clear error messages from all associated handlers when checkbox state changes"""
        # Clear main output area
        if hasattr(self, 'output_area'):
            with self.output_area:
                clear_output()
        
        # Clear message output from any associated handlers
        # This is a bit of a hack since we need to find handlers that might have error messages
        # We look for any attributes that might be handlers with message output areas
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, 'message_output_label'):
                try:
                    with attr.message_output_label:
                        attr.message_output_label.clear_output(wait=True)
                    # Re-enable buttons that might have been disabled
                    if hasattr(attr, 'update_label_button'):
                        attr.update_label_button.disabled = False
                    if hasattr(attr, 'update_order_button'):
                        attr.update_order_button.disabled = False
                except:
                    pass  # Ignore errors if output areas don't exist or are not accessible

    def _on_uniprot_search_change(self, change):
        """Handle UniProt search checkbox toggle - simplified version"""
        
        # Only process 'value' changes
        if change['type'] != 'change' or change['name'] != 'value':
            return
        
        # Clear any existing error messages when checkbox state changes
        self._clear_error_messages()
        
        if change['new']:  # When checkbox is checked
            # Initialize UniProt client if needed
            if self.uniprot_client is None:
                try:
                    self.uniprot_client = UniProtClient()
                    with self.output_area:
                        clear_output()
                        display(HTML('<b style="color:green;">UniProt client initialized successfully.</b>'))
                except ImportError as e:
                    with self.output_area:
                        clear_output()
                        display(HTML(f'<b style="color:red;">Error importing UniProt client: {str(e)}</b>'))
                    self.uniprot_search.value = False
                    return
            
            # Only fetch if we have merged data and missing proteins
            if (hasattr(self, 'merged_df') and self.merged_df is not None and 
                not self.merged_df.empty and 'Protein' in self.merged_df.columns):
                
                unique_protein_ids = set(self.merged_df['Protein'].dropna().unique())
                missing_proteins = unique_protein_ids - set(self.protein_dict.keys())
                
                if missing_proteins:
                    with self.output_area:
                        clear_output()
                        success_count = 0
                        for protein_id in missing_proteins:
                            try:
                                name, species, sequence = self.uniprot_client.fetch_protein_info_with_sequence(protein_id)
                                if sequence:
                                    self.protein_dict[protein_id] = {
                                        "name": name if name else protein_id,
                                        "sequence": sequence,
                                        "species": species if species else "Unknown"
                                    }
                                    success_count += 1
                                    display(HTML(f'<span style="color:green;">✓ {protein_id}: {name or "Unknown"} ({species or "Unknown"})</span>'))
                                else:
                                    display(HTML(f'<span style="color:orange;">✗ No sequence found for {protein_id}</span>'))
                            except Exception as e:
                                display(HTML(f'<span style="color:orange;">✗ Error fetching {protein_id}: {str(e)}</span>'))
                        
                        if success_count > 0:
                            display(HTML(f'<b style="color:green;">Successfully fetched {success_count} out of {len(missing_proteins)} missing proteins.</b>'))

    def check_missing_proteins_in_merged_data(self):
        """Check for proteins in merged data that are missing from protein_dict and prompt to fetch from UniProt"""
        if not hasattr(self, 'merged_df') or self.merged_df is None or self.merged_df.empty:
            return
            
        if 'Protein' not in self.merged_df.columns:
            return
            
        # Get unique protein IDs from merged data
        unique_protein_ids = set(self.merged_df['Protein'].dropna().unique())
        
        # Find missing proteins
        missing_proteins = unique_protein_ids - set(self.protein_dict.keys())
        
        if not missing_proteins:
            return
            
        # Initialize UniProt client if needed
        if self.uniprot_search.value and self.uniprot_client is None:
            try:
                self.uniprot_client = UniProtClient()
            except ImportError:
                with self.output_area:
                    display(HTML('<b style="color:red;">Error initializing UniProt client.</b>'))
                return
                
        if self.uniprot_search.value and self.uniprot_client:
            with self.output_area:
                display(HTML(f'<b>Found {len(missing_proteins)} proteins missing sequence information.</b><br>' +
                            f'<b>Attempting to fetch from UniProt...</b>'))
                
                success_count = 0
                for protein_id in missing_proteins:
                    try:
                        name, species, sequence = self.uniprot_client.fetch_protein_info_with_sequence(protein_id)
                        
                        if sequence:
                            self.protein_dict[protein_id] = {
                                "name": name if name else protein_id,
                                "sequence": sequence,
                                "species": species if species else "Unknown"
                            }
                            success_count += 1
                        else:
                            display(HTML(f'<span style="color:orange;">No sequence found for {protein_id}</span>'))
                    except Exception as e:
                        display(HTML(f'<span style="color:orange;">Error fetching {protein_id}: {str(e)}</span>'))
                        
                display(HTML(f'<b style="color:green;">Successfully fetched {success_count} out of {len(missing_proteins)} missing proteins.</b>'))
        else:
            with self.output_area:
                missing_list = ", ".join(list(missing_proteins)[:10])
                if len(missing_proteins) > 10:
                    missing_list += f" and {len(missing_proteins) - 10} more"
                    
                display(HTML(
                    f'<b style="color:orange;">Warning: {len(missing_proteins)} proteins in your data are missing sequences.</b><br>' +
                    f'Missing proteins: {missing_list}<br>' +
                    f'<b>To automatically fetch these proteins, check "Query UniProt for missing protein information" above.</b>'
                ))         
        
    def _on_merged_upload_change(self, change):
        """Simplified merged file upload handler"""
        
        if change['type'] != 'change' or change['name'] != 'value':
            return
        
        with self.output_area:
            self.output_area.clear_output()
            if change['new'] and len(change['new']) > 0:
                file_data = change['new'][0]
                
                # Check if this is the same file
                current_file_name = getattr(self, 'current_merged_file_name', None)
                new_file_name = getattr(file_data, 'name', None)
                
                if current_file_name == new_file_name:
                    display(HTML(f'<b style="color:blue;">File "{new_file_name}" is already loaded.</b>'))
                    return
                
                self.current_merged_file_name = new_file_name
                
                self.merged_df, merged_status = self._load_data(
                    file_data,
                    required_columns=['Protein'],
                    file_type='Merged'
                )

                # Only process protein info if data loading was successful
                if merged_status == 'yes' and self.merged_df is not None:
                    self.process_protein_info(self.merged_df)
                elif merged_status == 'no':
                    display(HTML('<b style="color:red;">Data processing stopped due to validation errors. Please fix the data issues and try again.</b>'))
                    return

                if merged_status == 'yes' and self.merged_df is not None:
                    avg_columns = [col for col in self.merged_df.columns if col.startswith('Avg_')]
                    self.col_order = [col.replace('Avg_', '') for col in avg_columns]

                    if avg_columns:
                        self.group_data_dict = {}
                        for i, col in enumerate(avg_columns, 1):
                            group_name = col[4:]
                            self.group_data_dict[str(i)] = {
                                "grouping_variable": group_name,
                                "abundance_columns": [col]
                            }
                        
                        # Only check for missing proteins if not already handled
                        self.check_missing_proteins_in_merged_data()
                    else:
                        # Handle case where no Avg_ columns exist
                        numerical_cols = list(self.merged_df.select_dtypes(include=['number']).columns)
                        if numerical_cols:
                            # Show column selector (your existing code)
                            pass
            
            # Enable other widgets now that we have merged data
            self.check_missing_proteins_in_merged_data()
            self.fasta_uploader.disabled = False
            self.uniprot_search.disabled = False

    def _on_fasta_upload_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            with self.output_area:
                self.output_area.clear_output()
                if change['new'] and len(change['new']) > 0:
                    for file_data in change['new']:
                        try:
                            if file_data.name.endswith('.fasta'):
                                self.fasta_filename = file_data.name

                                # Validate FASTA format before parsing
                                if not self._validate_fasta_format(file_data):
                                    display(HTML(f"<b style='color:red'>Error: Invalid FASTA format in {file_data.name}</b>"))
                                    self.fasta_file_uploaded_placeholder = False

                                    continue
                                else:
                                    display(HTML(f'<b style="color:green;">Successfully imported {file_data.name}</b>'))
                                    self.fasta_file_uploaded_placeholder = True

                                new_proteins = self._parse_uploaded_fasta(file_data)

                                if self.merged_df is not None:
                                    protein_ids = set(self.merged_df['Protein'].dropna().unique())
                                    match_count = 0

                                    for protein_id, protein_data in new_proteins.items():
                                        if protein_id in protein_ids:
                                            self.protein_dict[protein_id] = protein_data
                                            match_count += 1

                                    display(HTML(
                                        f'<b style="color:green;">Successfully imported FASTA file: {self.fasta_filename} '
                                        f'({len(new_proteins)} proteins, {match_count} matched to dataset)</b>'
                                    ))

                                else:
                                    self.protein_dict.update(new_proteins)
                                    display(HTML(f'<b style="color:green;">Successfully imported Entire FASTA file: {self.fasta_filename} ({len(new_proteins)} proteins)</b>'))
                            else:
                                display(HTML(f'<b style="color:red;">Invalid file format. Please upload FASTA files only.</b>'))
                            self.uniprot_search.value = False
                        except Exception as e:
                            display(HTML(f'<b style="color:red;">Error processing FASTA file: {str(e)}</b>'))

    def _validate_fasta_format(self, file_data):
        """
        Validate that the uploaded file follows proper FASTA format.
        Returns True if valid, False otherwise.
        """
        try:
            # Read file content
            content = file_data.content.tobytes().decode('utf-8')
            lines = content.strip().split('\n')
            
            if not lines:
                return False

            # Check that at least one line starts with '>'
            if not any(line.strip().startswith('>') for line in lines):
                display(HTML("<b style='color:red'>Improper FASTA header: At least one line must start with '>'</b>"))
                return False
            
            # Check basic FASTA format requirements
            has_header = False
            has_sequence = False
            current_sequence_length = 0
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                    
                if line.startswith('>'):
                    # This is a header line
                    if len(line) <= 1:  # Header with no identifier
                        return False
                    has_header = True
                    
                    # If we were reading a sequence, check it had content
                    if i > 0 and current_sequence_length == 0:
                        return False
                    current_sequence_length = 0
                    
                else:
                    # This should be sequence data
                    if not has_header:  # Sequence without preceding header
                        return False
                    
                    # Check for valid sequence characters (amino acids or nucleotides)
                    valid_chars = set('ACDEFGHIKLMNPQRSTVWYXBZJOU*-')  # Extended amino acid alphabet
                    if not all(c.upper() in valid_chars for c in line):
                        # If not amino acids, check if it could be nucleotides
                        nucleotide_chars = set('ATCGRYSWKMBDHVN-')
                        if not all(c.upper() in nucleotide_chars for c in line):
                            return False
                    
                    has_sequence = True
                    current_sequence_length += len(line)
            
            # Must have at least one header and one sequence
            return has_header and has_sequence
            
        except Exception as e:
            display(HTML(f"<b style='color:red'>Validation error: {str(e)}</b>"))
            return False

    def validate_and_standardize_columns(self, df: pd.DataFrame):
        try:
            SOFTWARE_START_STOP_COLUMNS = {
                'Start position': 'start',
                'End position': 'end',
                'Peptide start': 'start',
                'Peptide end': 'end',
                'pep_res_before': 'start',
                'pep_res_after': 'end',
                'Start': 'start',
                'End': 'end',
                'protein_start': 'start',
                'protein_end': 'end',
                'start': 'start',
                'end': 'end',
                'StartPosition': 'start',
                'EndPosition': 'end',
                'Startposition': 'start',
                'Endposition': 'end',
                'Peptide Start': 'start',
                'Peptide End': 'end',
                'Peptide Start Position': 'start',
                'Peptide End Position': 'end',
                'Peptide start position': 'start',
                'Peptide end position': 'end',
            }

            SOFTWARE_PROTEIN_ID_COLUMNS = [
                'Protein', 'Leading proteins', 'Protein Name',
                'Protein Accession', 'Accession Number', 'ProteinGroupId',
                'Protein ID', 'Accession', 'protein_accession', 'Protein'
            ]

            # If 'start' and 'end' columns already exist, skip renaming/mapping
            if 'start' not in df.columns or 'end' not in df.columns:
                # Rename start/stop columns
                for col in df.columns:
                    if col in SOFTWARE_START_STOP_COLUMNS:
                        mapping = SOFTWARE_START_STOP_COLUMNS[col]
                        if isinstance(mapping, tuple):
                            start_col, stop_col = col, col
                        else:
                            if SOFTWARE_START_STOP_COLUMNS[col] == 'start':
                                df.rename(columns={col: 'start'}, inplace=True)
                            elif SOFTWARE_START_STOP_COLUMNS[col] == 'end':
                                df.rename(columns={col: 'end'}, inplace=True)

            # Validate start/stop columns
            if 'start' not in df.columns or 'end' not in df.columns:
                raise ValueError("Missing required columns 'start' or 'end'.")

            # If 'start' or 'end' columns are duplicated, flatten them by keeping only one
            # (e.g., if df['start'] is a DataFrame with duplicate columns, reduce to Series)
            if isinstance(df['start'], pd.DataFrame):
                # If there are multiple 'start' columns, keep the first
                df['start'] = df['start'].iloc[:, 0]
            if isinstance(df['end'], pd.DataFrame):
                df['end'] = df['end'].iloc[:, 0]

            # Check if all values in 'start' and 'end' are NaN
            if df['start'].isna().all() and df['end'].isna().all():
                print("DEBUG: All values in 'start' and 'end' are NaN")
                raise ValueError("All values in 'start' and 'end' columns are NaN. Please provide valid start and end positions.")

            # Warn if any missing values in start or end (but not all)
            if df['start'].isna().any() or df['end'].isna().any():
                print("DEBUG: Some values in 'start' or 'end' are NaN")
                display(HTML(
                    "<b style='color:orange;'>Warning: Some rows have missing values in 'start' or 'end' position columns. "
                    "These peptides will not be plotted properly. Please check your data.</b>"
                ))

            # First check if 'Protein' is already in df
            if 'Protein' not in df.columns:
                # Rename Protein ID column
                for col in SOFTWARE_PROTEIN_ID_COLUMNS:
                    if col in df.columns:
                        df.rename(columns={col: 'Protein'}, inplace=True)
                        break

            if 'Protein' not in df.columns:
                raise ValueError("Missing required column 'Protein'.")

            # Fix: Avoid ambiguous Series truth value error
            # The error can occur if df['Protein'] is not of string type or contains non-string values
            # Ensure 'Protein' is string type before using .str.contains
            df['Protein'] = df['Protein'].astype(str)
            multi_id_rows = df[df['Protein'].str.contains(';', na=False)]

            if not multi_id_rows.empty:
                display(HTML('<b style="color:red;">Rows with multiple protein IDs detected:</b>'))
                display(multi_id_rows)
                raise ValueError(
                    "Multiple protein IDs detected for one or more peptides; either exclude these rows or use another strategy to handle them."
                )
            # Extract UniProt ID from FASTA header
            def extract_uniprot(x):
                if isinstance(x, str) and '|' in x:
                    m = re.search(r'\|([A-Z0-9]+)\|', x)
                    if m:
                        return m.group(1)
                return x
            df['Protein'] = df['Protein'].apply(extract_uniprot)

            return df

        except Exception as e:
            import sys
            tb_str = traceback.format_exc()
            display(HTML(f"<b style='color:red;'>Validation/Standardization error: {str(e)}</b><br><pre>{tb_str}</pre>"))
            raise

    def _load_data(self, file_obj, required_columns, file_type):
        try:
            content = file_obj.content
            self.pd_filename = file_obj.name
            extension = self.pd_filename.split('.')[-1].lower()
            file_stream = io.BytesIO(content)

            if extension == 'csv':
                df = pd.read_csv(file_stream)
            elif extension in ['txt', 'tsv']:
                df = pd.read_csv(file_stream, delimiter='\t')
            elif extension == 'xlsx':
                df = pd.read_excel(file_stream)
            else:
                raise ValueError("Unsupported file format.")

            df.columns = df.columns.str.strip()

            # Standardize columns
            try:
                df = self.validate_and_standardize_columns(df)
            except ValueError as e:
                display(HTML(f'<b style="color:red;">{file_type} File Error: {e}</b>'))
                return None, 'no'

            # Check again for required columns
            if not set(required_columns).issubset(df.columns):
                missing = set(required_columns) - set(df.columns)
                display(HTML(
                    f'<b style="color:red;">{file_type} File Error: Missing required columns after standardization: {", ".join(missing)}</b>'
                ))
                return None, 'no'

            return df, 'yes'
        except Exception as e:
            display(HTML(f'<b style="color:red;">{file_type} File Error: {str(e)}</b>'))
            return None, 'no'
    
    def process_protein_info(self, df):
        # Check if df is None (data loading failed)
        if df is None:
            display(HTML('<b style="color:red;">Error: Cannot process protein info - data loading failed. Please check your data format and fix any errors before proceeding.</b>'))
            return 0
            
        # Check if we need to fetch any data from UniProt
        has_protein_info = all(col in df.columns for col in ['protein_name', 'protein_species'])
        if has_protein_info:
            # Check if we have valid data for all entries
            all_data_present = (
                df['protein_name'].notna().all() and 
                df['protein_species'].notna().all() and
                (df['protein_name'] != '').all() and
                (df['protein_species'] != '').all()
            )
            if all_data_present:
                # If we have all data, just process it silently
                protein_info = df.groupby('Protein').agg({
                    'protein_name': 'first',
                    'protein_species': 'first'
                }).reset_index()
                
                for _, row in protein_info.iterrows():
                    protein_id = row['Protein']
                    self.protein_dict[protein_id] = {
                        "name": row['protein_name'],
                        "species": row['protein_species'],
                        "sequence":''
                    }
                return len(self.protein_dict)

    def _find_species(self, header):
        """Find species in FASTA header"""

        header_lower = header.lower()
        for spec_group in spec_translate_list:
            for term in spec_group[1:]:
                if term.lower() in header_lower:
                    return spec_group[0]
        return "unknown"

    def _parse_uploaded_fasta(self, file_data):
        """Parse uploaded FASTA file content"""
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
                        "species": species
                    }
                sequence = ""
                header_parts = line[1:].split('|')
                if len(header_parts) > 2:
                    protein_id = header_parts[1]
                    protein_name_full = re.split(r' OS=', header_parts[2])[0]
                    protein_name = protein_name_full if ' ' in protein_name_full else protein_name_full
                    species = self._find_species(line)
            else:
                sequence += line
                
        if protein_id:
            fasta_dict[protein_id] = {
                "name": protein_name,
                "sequence": sequence,
                "species": species
            }
        
        return fasta_dict