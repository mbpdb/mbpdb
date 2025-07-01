# Notebook Update Scripts

This directory contains scripts to update the Jupyter notebooks to use the new UniProt client module.

## Available Scripts

- `update_data_viz.py` - Updates the Data_Vizualization.ipynb notebook
- `update_protein_plot.py` - Updates the Protein_Bar_Plot.ipynb notebook

## How to Run

Simply execute the scripts from the command line:

```bash
# Make the scripts executable first
chmod +x update_data_viz.py
chmod +x update_protein_plot.py

# Run the scripts
./update_data_viz.py
./update_protein_plot.py
```

## What the Scripts Do

These scripts make the following changes to the notebooks:

1. Add an import statement for the UniProtClient class
2. Add initialization of the UniProtClient in the DataTransformation.__init__ method
3. Replace calls to self.fetch_uniprot_info with self.uniprot_client.fetch_protein_info
4. Replace calls to self.fetch_uniprot_info_batch with self.uniprot_client.fetch_proteins_batch
5. Remove the original UniProt functions from the notebooks

## Backing Up Your Notebooks

If you want to back up your notebooks before running the scripts, you can modify the scripts to output to a different path:

1. Open the script in a text editor
2. Find the line that specifies the output_path
3. Change it to a new path, for example:
   ```python
   output_path = notebook_path.replace('.ipynb', '_updated.ipynb')
   ```

## Troubleshooting

If you encounter any issues, make sure:

1. The script has execute permissions
2. The notebook files exist at the expected paths
3. You have write permission to the notebook files
4. The notebooks have the expected structure (class names, method names, etc.)

If you need to revert to the original notebook, you can restore from your backup or use the version control system if you have one in place. 