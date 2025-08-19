## Peptidline Notebooks (Local Install)

### Overview
Interactive notebooks for transforming peptidomics data (no local database search required).

### Prerequisites
- Python 3.10+
- pip
- Recommended: a virtual environment (venv)

### Quick start (Ubuntu/WSL)
```bash
cd ~/peptidline-notebooks
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r notebook_requirements.txt
jupyter lab
```

### Quick start (Windows, PowerShell)
```powershell
cd $env:USERPROFILE\peptidline-notebooks
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r notebook_requirements.txt
jupyter lab
```

### Quick start (macOS)
```bash
cd ~/peptidline-notebooks
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r notebook_requirements.txt
jupyter lab
```

### Use
- Open Data_Transformation_widget.ipynb and run the first cells to load the UI.
- Upload:
  - Peptidomic file (CSV/TSV/TXT/XLSX)
  - Optional MBPDB results file
  - Optional FASTA files

### Notes
- No BLAST or local DB is needed.
- This repo includes `utils/` and `protein_headers.txt` used by the notebooks.

### Troubleshooting
- If widgets don’t render:
```bash
pip install --upgrade jupyterlab ipywidgets
```
```

### Ensure notebook_requirements.txt is at repo root
- Copy from the original folder if needed:
```bash
# From old repo root
cp include/peptide/peptide/notebooks/notebook_requirements.txt ../peptidline-notebooks/
```

### Optional .gitignore for the new repo
```gitignore
.venv/
__pycache__/
.ipynb_checkpoints/
*.pyc
.DS_Store
```

Summary
- Use Option A to preserve commit history; Option B for a clean start.
- Place the provided README.md in the new repo root.
- Ensure `notebook_requirements.txt` is at the new repo root for simpler install paths.