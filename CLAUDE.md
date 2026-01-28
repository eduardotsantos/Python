# CLAUDE.md

## Project Overview

This repository is a collection of **proof-of-concept Python projects** focused on machine learning, route optimization, and web scraping automation. All projects are implemented as Jupyter Notebooks designed to run in **Google Colaboratory**.

The primary natural language is **Brazilian Portuguese** — comments, variable names, markdown cells, and documentation are written in Portuguese.

## Repository Structure

```
Python/
├── AgenteVagas.ipynb            # LinkedIn job scraping automation
├── rotas_aco.ipynb              # Route optimization via Ant Colony Optimization
├── rotas_aco (1).ipynb          # (duplicate)
├── rotas_mlp_svm_knn.ipynb      # ML model comparison (MLP, SVM, KNN)
├── rotas_mlp_svm_knn (1).ipynb  # (duplicate)
├── rotas.csv                    # Route characteristics dataset (5119 records)
├── rotas (1).csv                # (duplicate)
├── ModeloIAVendas.pkcls         # Pickled ML model (sales forecasting)
├── python_formula_editor.png    # Reference screenshot
├── python_in_excel_cheatsheet.pdf  # Reference document
└── CLAUDE.md                    # This file
```

> **Note:** Files with `(1)` suffixes are duplicates from cloud export. They can be safely ignored.

## Projects

### 1. AgenteVagas.ipynb — LinkedIn Job Scraper

- **Purpose:** Automate job listing collection from LinkedIn.
- **Workflow:** Selenium-based browser automation → scrape job titles, companies, and locations → filter by criteria (e.g., "Gerente de Tecnologia" in São Paulo) → export to Excel.
- **Key libraries:** `selenium`, `beautifulsoup4`, `spacy`, `pandas`
- **NLP:** Uses SpaCy (`en_core_web_sm`) for entity recognition on scraped data.

### 2. rotas_aco.ipynb — Ant Colony Optimization for Routes

- **Purpose:** Find optimal routes using the ACO metaheuristic (Dorigo, 1992).
- **Architecture:** Class-based design with `Formiga` (Ant), `Ponto` (Point), `Caminho` (Path), `Grafo` (Graph).
- **Hyperparameters:** `ALFA=0.5`, `BETA=0.7`, `EVAPORATION_RATE=0.2` (defined as uppercase constants at notebook top).
- **Data source:** `rotas.csv`
- **Output:** Convergence plot and best route (~125.10 distance units).
- **Known issue:** Can produce `ZeroDivisionError` during pheromone initialization.

### 3. rotas_mlp_svm_knn.ipynb — ML Model Comparison

- **Purpose:** Compare three ML models on route classification.
- **Models:**
  - MLP: 2 hidden layers (64, 64 neurons)
  - SVM: RBF kernel
  - KNN: k=5, distance-weighted
- **Framework:** Orange3 (not raw scikit-learn)
- **Evaluation:** 5-fold cross-validation; metrics: MSE, RMSE, MAE, R²
- **Data source:** `rotas.csv`

## Dataset: rotas.csv

| Column         | Type       | Description                          |
|----------------|------------|--------------------------------------|
| DIRIGIBILIDADE | Discrete   | Target class (1–3, route difficulty)  |
| ROTAS          | String     | Route identifier (R1–R5119)          |
| DISTANCIA      | Continuous | Distance in km                       |
| FALHAS         | Continuous | Number of road failures              |
| LOMBADAS       | Continuous | Speed bump count                     |
| ILUMINACAO     | Continuous | Lighting quality score               |
| SINALIZACAO    | Continuous | Signage quality score                |
| PEDAGIOS       | Continuous | Toll costs                           |
| POSTOPOLICIAL  | Discrete   | Police presence (0/1)                |

## Technology Stack

| Category         | Tools                                          |
|------------------|-------------------------------------------------|
| Language         | Python 3.10+                                    |
| Execution        | Google Colaboratory (Jupyter Notebooks)          |
| Data processing  | pandas, numpy, scipy                            |
| ML frameworks    | Orange3, scikit-learn                            |
| NLP              | SpaCy (en_core_web_sm)                           |
| Web scraping     | Selenium + BeautifulSoup4                        |
| Visualization    | matplotlib                                       |
| Browser driver   | Chromium + ChromeDriver                          |
| Package manager  | pip (inline `!pip install` in notebooks)         |

## Conventions and Patterns

### Language
- All code comments, variable names, class names, and markdown documentation use **Brazilian Portuguese**.
- Class names translate English concepts: `Formiga` = Ant, `Ponto` = Point, `Caminho` = Path, `Grafo` = Graph.

### Code Style
- **Procedural/functional** style in scraping and ML notebooks.
- **Class-based OOP** in the ACO notebook for algorithm components.
- Hyperparameters and constants are **UPPERCASE** at the top of each notebook.
- No external Python modules — all code lives inside notebook cells.
- `print()` used for output; `matplotlib` for inline plots.

### Dependency Installation
- Each notebook installs its own dependencies via `!pip install` commands in early cells.
- No `requirements.txt` or `pyproject.toml` exists. Dependencies are implicit.
- Notebooks assume Google Colab's pre-installed scientific stack (numpy, pandas, matplotlib).

### Data Handling
- CSV files are loaded with `pandas.read_csv()`.
- Files are uploaded/downloaded using Colab's file management utilities.
- No database connections — all data is file-based.

## Development Workflow

1. **Environment:** Open notebooks in Google Colaboratory.
2. **Dependencies:** Run the `!pip install` cells at the top of each notebook to install missing packages.
3. **Data:** Ensure CSV files are available in the Colab working directory (upload if needed).
4. **Execution:** Run cells sequentially top-to-bottom; notebooks are not designed for out-of-order execution.

## What This Repository Does NOT Have

- No `requirements.txt`, `setup.py`, or `pyproject.toml`
- No `.gitignore` (all files including duplicates and binaries are tracked)
- No CI/CD pipeline
- No unit tests or test framework
- No README.md
- No modular Python packages — everything is in notebooks
- No Docker or containerization setup

## Guidelines for AI Assistants

- **Respect the Portuguese convention.** New code, comments, and variable names should use Brazilian Portuguese to match the existing codebase.
- **Notebook-first workflow.** This project uses Jupyter Notebooks as the primary development medium. Avoid creating standalone `.py` files unless explicitly requested.
- **Google Colab compatibility.** Any new code should be compatible with the Colab environment. Use `!pip install` for dependencies and Colab file utilities for I/O.
- **Keep hyperparameters configurable.** Define them as uppercase constants at the top of the notebook, following the existing pattern.
- **Beware of duplicates.** Files with `(1)` in their names are duplicates and should not be treated as authoritative sources.
- **Security awareness.** The AgenteVagas notebook contains hardcoded credentials — avoid committing credentials in any new work.
- **No overengineering.** This is a collection of experiments and prototypes. Keep contributions focused and exploratory in nature.
- **Dataset context.** The route dataset (`rotas.csv`) has 5119 records with a discrete target variable `DIRIGIBILIDADE` (values 1–3). The domain is Brazilian road/traffic analysis.
