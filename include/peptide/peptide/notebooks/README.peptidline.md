## Peptidline (Local Jupyter Notebook Guide)

### Overview
Peptidline provides interactive notebooks for transforming peptidomics data. You can run:
- Notebook-only locally (recommended)

### Prerequisites
- Python 3.10+
- pip
- git
- Recommended: a virtual environment (venv)

### Installation Options

#### Option 1: Clone from GitHub (Recommended)
Get the latest notebooks directly from the Peptiline repository:

```bash
# Clone the repository
git clone https://github.com/Kuhfeldrf/peptiline.git
cd peptiline

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r notebook_requirements.txt

# Launch Jupyter Lab
jupyter lab
```

#### Option 2: From MBPDB Repository
If you're working within the MBPDB repository:

```bash
# From your home directory (adjust path as needed)
cd ~/mbpdb

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r include/peptide/peptide/notebooks/notebook_requirements.txt

# Launch Jupyter Lab
cd include/peptide/peptide/notebooks
jupyter lab
```

### Getting Started
After launching Jupyter Lab, open `data_transformation.ipynb` (or `Data_Transformation_widget.ipynb` if available) and run the first two cells to initialize the UI.

### Using the Data Transformation UI
In the notebook, after running the setup cell(s), the widget-based UI will appear. If you prefer to instantiate manually:
```python
dt = DataTransformation()
dt.display_widgets()
```

You can now:
- Upload your peptidomic file (CSV/TSV/TXT/XLSX)
- Optionally upload MBPDB results file
- Optionally upload one or more FASTA files

### Data inputs
- Peptidomic groups table exported from Proteome Discoverer or similar
- Optional: MBPDB results file produced elsewhere (TSV/CSV/XLSX)
- Optional: Protein FASTA files used in your search workflow

 

### Notes and tips
- **GitHub installation**: Run Jupyter from the cloned `peptiline` directory root where the notebooks are located.
- **MBPDB installation**: Run Jupyter from `include/peptide/peptide/notebooks` so relative imports (e.g., `utils/uniprot_client.py`) resolve.
- The UI expects typical Proteome Discoverer column names; see the example files referenced in the UI.
- If widget outputs are not visible, ensure JupyterLab supports ipywidgets (the provided requirements include compatible versions).
- **Staying updated**: If using the GitHub repository, pull the latest changes with `git pull origin main`.

### Troubleshooting
- Widgets not rendering: upgrade JupyterLab/ipywidgets and refresh the page.
  ```bash
  pip install --upgrade jupyterlab ipywidgets
  ```
- BLAST not found: install `ncbi-blast+` and restart kernel.
- MBPDB search disabled: verify both the DB file path and BLAST tools availability.

### License and attribution
See the project root `README.md` for license, attribution, and project-wide notes.


