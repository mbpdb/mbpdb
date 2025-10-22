# PeptiLine: An Interactive Platform for Customizable Functional Peptidomic Analysis

## Overview
PeptiLine is a comprehensive software platform for transforming peptidomic mass spectrometry output data into interactive visualizations and statistical summaries. The platform integrates peptide-to-protein mapping, quantitative comparisons, bioactive annotations, and descriptive analyses into a user-friendly interface.

**Publication:** Kuhfeld R, Nielsen SD-H, Dallas DC. (2025) PeptiLine: An Interactive Platform for Customizable Functional Peptidomic Analysis. PLOS Computational Biology. [DOI will be added upon publication]

**Web Application:** https://mbpdb.nws.oregonstate.edu/peptiline/

**License:** MIT

## Features
PeptiLine consists of three integrated modules:
1. **Data Transformation** - Organizes and annotates peptidomic data with automated multi-protein peptide assignment handling and MBPDB bioactivity annotation
2. **Descriptive Analysis** - Exploratory data analysis through interactive visualizations including correlation plots, functional distributions, and protein origin contributions
3. **Heatmap Visualization** - Creates visual maps of peptide density and positioning along protein sequences

## System Requirements
- **Operating Systems:** Windows, macOS, or Linux
- **Python:** Version 3.10 or higher
- **Jupyter Notebook:** Version 7.4.5 or higher
- **Hardware:** Any modern computer with internet connection

## Installation

### Quick Start (Recommended)
```bash
# Clone the repository
git clone https://github.com/Kuhfeldrf/peptiline.git
cd peptiline

# Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r notebook_requirements.txt

# Launch Jupyter Lab
jupyter lab
```

Installation typically takes approximately 5 minutes.

### Web-Based Access (No Installation Required)
Access PeptiLine directly through your web browser at:
https://mbpdb.nws.oregonstate.edu/peptiline/

No local installation is required for the web version.

## Getting Started

### Using the Notebooks Locally
1. After launching Jupyter Lab, navigate to the desired module:
   - `data_transformation.ipynb` - Start here for data processing
   - `data_analysis.ipynb` - For descriptive analysis and visualizations
   - `heatmap_visualization.ipynb` - For sequence-based heatmap generation

2. Run the first cells to initialize the interactive interface

3. Follow the on-screen instructions within each notebook

### Input Data Requirements
PeptiLine accepts common peptidomic file formats:
- **Peptidomic data:** CSV, TSV, TXT, or XLSX files from Proteome Discoverer, MaxQuant, Skyline, FragPipe, or similar platforms
- **Functional annotations (optional):** MBPDB results or custom bioactivity databases
- **Protein sequences (optional):** FASTA files for custom protein variant analysis

See the `examples/` directory for sample datasets.

## Reproducibility

### Quick Start with Example Data
Practice with the included example files before analyzing your own data:

**Module 1: Data Transformation**
1. Open `data_transformation.ipynb` in Jupyter Lab
2. Upload files in the following sections:
   - **Upload Peptidomic Data File:** `examples/example_peptide_data.csv`
   - **Upload Group Definitions (Optional):** `examples/example_group_definition.json`
   - **Upload Functional Data - Option 1: Upload File (Optional):** `examples/example_MBPDB_search.tsv`
   - **Upload Protein FASTA Files (Optional):** `examples/example_fasta.fasta`
3. Complete Step 2: Peptide-to-Protein Mapping (resolve any multi-protein peptides)
4. Execute remaining cells to generate transformed dataset

**Module 2: Descriptive Analysis**
1. Open `data_analysis.ipynb`
2. Upload the merged dataset CSV from Module 1 output
3. Optionally upload group definitions: `examples/example_group_definition.json`
4. Select analysis parameters (transformation method, correlation type, filtering criteria)
5. Generate visualizations and statistical summaries

**Module 3: Heatmap Visualization**
1. Open `heatmap_visualization.ipynb`
2. Upload the merged dataset CSV from Module 1 output
3. Optionally upload group definitions: `examples/example_group_definition.json`
4. Filter by protein of interest and generate sequence-based heatmaps


### Manuscript Case Study - Bitterness in Aged Cheddar Cheese
The manuscript case study analyzed bitter peptide profiles in aged cheddar cheese. Example files in the `examples/` directory provide representative data for testing the workflow.

**Case Study Data Repository:** https://github.com/Kuhfeldrf/Bitterness-in-Aged-Cheddar-Cheese

**Data Processing Workflow:**

**Module 1 (Data Transformation):**
- Processed Proteome Discoverer output from Non-Bitter and Bitter cheese samples
- Applied group definitions to categorize samples
- Integrated MBPDB bioactivity annotations
- Uploaded β-casein variant FASTA files (A1 and A2)
- Resolved multi-protein peptide assignments (Step 2: Peptide-to-Protein Mapping)

**Step 2 Peptide-to-Protein Mapping Decisions:**

| Combination | Occurrences | Protein ID | Decision |
|-------------|-------------|------------|----------|
| 1 | 1 | G9G9X6 | Remove |
| | | P00711 | **Keep** |
| 2 | 2 | A5D974 | Remove |
| | | P02663 | **Keep** |
| 3 | 4 | C6KGD7 | Remove |
| | | C6KGD8 | **Keep** |
| | | C6KGD9 | Remove |
| 4 | 1 | A5D7J7 | Remove |
| | | P02663 | **Keep** |
| 5 | 20 | P31096 | **Keep** |
| | | Q58DM6 | Remove |
| 6 | 1 | A5D980 | Remove |
| | | P02662 | **Keep** |
| 7 | 6 | P02754 | **Keep** |
| | | Q9BDG3 | Remove |
| 8 | 928 | P02666A1 | **Custom: P02666** |
| | | P02666A2 | Remove |
| 9 | 1 | P02754 | **Keep** |
| | | Q9TRB9 | Remove |

**Module 2 (Descriptive Analysis):**
- Uploaded transformed dataset from Module 1
- Parameters: log10 transformation, Pearson correlation, filtering for peptides present in ≥2 samples per group
- Generated correlation analyses, functional distribution plots, and protein contribution figures

**Module 3 (Heatmap Visualization):**
- Uploaded transformed dataset from Module 1
- Filtered for β-casein peptides (P02666)
- Generated sequence-based heatmaps showing merged A1/A2 variants, variant-specific peptides, and bitter-enriched peptide positioning

**Published Outputs:**
- Supplemental Figures 1-5: Statistical analyses and correlations
- Figure 4: β-casein peptide sequence heatmaps
- Figure 6: Bitter peptide enrichment visualization (Peptigram)
- Supplemental Tables: Complete processed datasets

All analysis parameters and filtering criteria are documented in the manuscript methods section and supplementary materials.

## Documentation
- **Installation instructions:** This README
- **Module-specific guides:** See individual notebook markdown cells
- **Dependencies:** `notebook_requirements.txt`
- **Example data:** `examples/` directory
- **API utilities:** `utils/` directory

## Dependencies
Core dependencies include:
- Jupyter Notebook (≥7.4.5)
- pandas
- numpy
- matplotlib
- seaborn
- plotly
- scikit-learn
- ipywidgets
- voila

See `notebook_requirements.txt` for complete list with version specifications.

## Project Structure
```
peptiline/
├── data_transformation.ipynb       # Module 1: Data processing
├── data_analysis.ipynb            # Module 2: Descriptive analysis
├── heatmap_visualization.ipynb    # Module 3: Sequence visualization
├── _settings.py                   # Configuration file
├── notebook_requirements.txt      # Python dependencies
├── utils/                        # UniProt API utilities
├── examples/                     # Case study data
└── README.md                     # This file
```

## Support and Contact
- **Bug reports and feature requests:** Open an issue on GitHub
- **General inquiries:** contact-mbpdb@oregonstate.edu
- **MBPDB Platform:** https://mbpdb.nws.oregonstate.edu

## Troubleshooting

### Widgets not rendering
```bash
pip install --upgrade jupyterlab ipywidgets
# Restart Jupyter Lab
```

### Module import errors
Ensure you're running Jupyter from the `peptiline/` directory root:
```bash
cd peptiline
jupyter lab
```

### BLAST functionality (for MBPDB searches)
Install NCBI BLAST+ tools if using local MBPDB database searches:
```bash
# Ubuntu/Debian
sudo apt-get install ncbi-blast+

# macOS
brew install blast

# Windows
# Download from: https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/
```

## Citation
If you use PeptiLine in your research, please cite:
```
Kuhfeld R, Nielsen SD-H, Dallas DC. (2025) PeptiLine: An Interactive Platform 
for Customizable Functional Peptidomic Analysis. PLOS Computational Biology. 
[DOI will be added upon publication]
```

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Authors
- Russell Kuhfeld (Oregon State University)
- Søren D-H. Nielsen (Arla Foods Ingredients Group P/S)
- David C. Dallas (Oregon State University)

## Acknowledgments
PeptiLine is integrated within the Milk Bioactive Peptide Database (MBPDB) platform. We acknowledge the contributions of the MBPDB development team and the broader peptidomics research community.

## Version History
- **v1.0** (2025) - Initial release accompanying PLOS Computational Biology publication

## Contributing
We welcome community contributions! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with a clear description of changes

For major changes, please open an issue first to discuss proposed modifications.
