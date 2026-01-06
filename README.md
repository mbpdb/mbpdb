# Milk Bioactive Peptide Database (MBPDB)

[![Live Site](https://img.shields.io/badge/Live%20Site-mbpdb.nws.oregonstate.edu-blue)](https://mbpdb.nws.oregonstate.edu/)
[![Django](https://img.shields.io/badge/Django-4.x-green)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)

A comprehensive database and analysis platform for milk protein-derived bioactive peptides from any species. MBPDB enables researchers to search, analyze, and visualize peptide sequences with known bioactivities.

🔗 **Live Application**: [https://mbpdb.nws.oregonstate.edu/](https://mbpdb.nws.oregonstate.edu/)

---

## 📋 Features

### 🔍 Peptide Search
Search the database for bioactive peptides using sequence homology, including results from peptidomics analyses.

### 📊 PeptiLine
Interactive visual mapping of peptides on their parent protein sequences, highlighting regions with high concentrations of bioactive peptides.

### 🧬 PepEx (Peptide Explorer)
Explore and visualize peptide-protein relationships with an interactive interface.

### 🛠️ Analysis Tools
- **Data Transformation** - Transform and prepare peptidomics data
- **Data Analysis** - Statistical analysis of peptide datasets
- **Heatmap Visualization** - Generate heatmaps for peptide abundance and activity patterns

---

## 📊 Database Contents

| Table | Records | Description |
|-------|---------|-------------|
| Peptides | 712 | Bioactive peptide sequences |
| Proteins | 120,538 | Parent protein information |
| Functions | 916 | Documented bioactive functions |
| References | 1,087 | Literature citations |
| Protein Variants | 26 | Protein sequence variants |

---

## 🏗️ Technology Stack

- **Backend**: Django 4.x, Celery, Redis
- **Interactive Notebooks**: Voila (Jupyter)
- **Database**: SQLite
- **Web Server**: Nginx, Gunicorn
- **Containerization**: Docker
- **Deployment**: Azure Container Apps

---

## 🚀 Local Development

### Prerequisites
- Python 3.11+
- Redis server
- Docker (optional)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mbpdb/mbpdb.git
   cd mbpdb
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or .venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   ```bash
   export DJANGO_SECRET_KEY="your-secret-key-here"
   export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1"
   ```

5. **Run migrations**
   ```bash
   cd include/peptide
   python manage.py migrate
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```

### Docker Deployment

```bash
docker build -t mbpdb .
docker run -p 80:80 \
  -e DJANGO_SECRET_KEY="your-secret-key" \
  -e DJANGO_ALLOWED_HOSTS="localhost" \
  mbpdb
```

---

## 📚 Citation

If you use MBPDB in your research, please cite:

> **Nielsen, S.D.**, Beverly, R.L., Qu, Y., & Dallas, D.C. (2017). Milk Bioactive Peptide Database: A Comprehensive Database of Milk Protein-Derived Bioactive Peptides and Novel Visualization. *Food Chemistry*, 232, 673–82. [DOI](http://www.sciencedirect.com/science/article/pii/S0308814617306222)

> **Nielsen, S.D.**, Liang, N., Rathish, H., Kim, B.J., Lueangsakulthai, J., Koh, J., Qu, Y., Schulz, H.J., & Dallas, D.C. (2023). Bioactive milk peptides: an updated comprehensive overview and database. *Critical Reviews in Food Science and Nutrition*. [DOI](https://www.tandfonline.com/doi/full/10.1080/10408398.2023.2240396)

---

## 👥 Contributors

### Data Contributors
- Søren Drud Nielsen
- Robert L. Beverly
- Yunyao Qu
- Ningjian Liang
- Harith Rathish
- Bum Jin Kim
- Jiraporn Lueangsakulthai
- Jeewon Koh
- Russell Kuhfeld
- David C. Dallas ([Dallas Lab](http://www.dallaslab.org))

### Web Development
- Russell Kuhfeld
- Nikhil Joshi
- Adam Schaal
- Søren Drud Nielsen

---

## 📧 Contact

For inquiries, to submit new bioactive peptides, or to add new proteins:

📬 **Email**: [Contact-MBPDB@oregonstate.edu](mailto:Contact-MBPDB@oregonstate.edu)

🔬 **Lab Website**: [www.dallaslab.org](http://www.dallaslab.org)

---

## 🏛️ Affiliation

Developed and maintained by the [Dallas Lab](http://www.dallaslab.org) at **Oregon State University**.

---

## 📄 License

This project is intended for academic and research use. Please contact the maintainers for commercial licensing inquiries.
