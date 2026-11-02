# Funding flows

Starter refactor of the humanitarian funding-flow notebook.

## Install

```bash
python -m pip install -e .
```

## Data layout

Place the existing files under:

- `data/raw/fts/FTS_Sudan_2025.xlsx`
- `data/raw/cerf/CERF_allocations.xlsx`
- `data/raw/cbpf/ProjectSummaryWithLocationAndCluster20260916060903549.csv`
- `data/raw/cbpf/Contribution20260914102012729.csv`
- `data/raw/unicef/UNICEF_Sudan_2025_export.csv`
- `data/raw/agency_totals/funding-flows-agency-totals.xlsx`

Copy the complete dictionaries from the notebook into the matching JSON files in `config/`.

## Run

```bash
python run.py --country Sudan --year 2025
```
