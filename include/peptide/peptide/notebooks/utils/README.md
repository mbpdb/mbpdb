# Utils Package

This package contains utility modules for the peptide analysis toolkit.

## UniProt Client

The `uniprot_client.py` module provides functionality to fetch protein information from UniProt.

### Features

- Fetch protein information for a single protein ID
- Batch fetch information for multiple protein IDs at once
- Automatic caching of results to avoid redundant requests
- Robust error handling and retry logic for API rate limits
- Fallback mechanisms for different UniProt API endpoints

### Usage Examples

#### Basic Usage

```python
from peptide.utils.uniprot_client import UniProtClient

# Create a client instance
client = UniProtClient()

# Fetch information for a single protein
protein_name, species = client.fetch_protein_info("P12345")

# Fetch information for multiple proteins
protein_info = client.fetch_proteins_batch(["P12345", "Q98765", "O54321"])

# protein_info is a dictionary with protein IDs as keys
# and (name, species) tuples as values
for protein_id, (name, species) in protein_info.items():
    print(f"{protein_id}: {name} ({species})")
```

#### Using the Functions Directly

You can also use the underlying functions directly if you don't need caching:

```python
from peptide.utils.uniprot_client import fetch_uniprot_info, fetch_uniprot_info_batch

# Fetch a single protein
name, species = fetch_uniprot_info("P12345")

# Fetch multiple proteins
results = fetch_uniprot_info_batch(["P12345", "Q98765"])
```

### Implementation Details

The client uses the following strategies to fetch protein information:

1. First attempts to use UniProt's REST API
2. Falls back to XML API if needed
3. Implements exponential backoff for rate limits
4. Prioritizes common/short names for proteins and species
5. Cleans up protein names (removing "precursor" and similar suffixes)

### How to Update Notebooks

The package includes scripts to update existing notebooks to use the new UniProt client:

- `update_data_viz.py` - Updates the Data_Visualization.ipynb notebook
- `update_protein_plot.py` - Updates the Protein_Bar_Plot.ipynb notebook

Run these scripts to automatically replace the embedded UniProt fetching functions with calls to the new client. 