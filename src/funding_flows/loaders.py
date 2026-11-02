from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .paths import CONFIG_DIR, RAW_DATA_DIR


def _check_file(path: str | Path, suffixes: Iterable[str] | None = None) -> Path:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    if suffixes and path.suffix.lower() not in {s.lower() for s in suffixes}:
        raise ValueError(f"Unexpected file type for {path}; expected one of {sorted(suffixes)}")
    return path


def _require_columns(df: pd.DataFrame, required: Iterable[str], source: str) -> None:
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"{source} is missing required columns: {missing}")


def load_csv(path: str | Path, **kwargs) -> pd.DataFrame:
    path = _check_file(path, {'.csv'})
    return pd.read_csv(path, **kwargs)


def load_excel(path: str | Path, sheet_name=0, **kwargs) -> pd.DataFrame:
    path = _check_file(path, {'.xlsx', '.xlsm', '.xls'})
    return pd.read_excel(path, sheet_name=sheet_name, **kwargs)


def load_json(path: str | Path) -> dict | list:
    path = _check_file(path, {".json"})

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_fts(country: str, year: int, path: str | Path | None = None) -> pd.DataFrame:
    path = Path(path) if path else RAW_DATA_DIR / 'fts' / f'FTS_{country}_{year}.xlsx'
    df = load_excel(path, sheet_name='Export data', header=2, index_col=0)
    df.index.name = 'source'
    # These are the columns subsequently used in the notebook after reset_index().
    _require_columns(df, {'Destination org.', 'Amount (US$)'}, 'FTS export')
    return df

def load_cerf(path: str | Path | None = None) -> pd.DataFrame:
    path = Path(path) if path else RAW_DATA_DIR / 'cerf' / 'CERF_allocations.xlsx'
    df = load_excel(path)
    _require_columns(df, {'Fund', 'Year', 'Agency', 'Cluster', 'Budget'}, 'CERF allocations')
    return df

def load_cbpf_allocations(path: str | Path | None = None) -> pd.DataFrame:
    path = Path(path) if path else RAW_DATA_DIR / 'cbpf' / 'ProjectSummaryWithLocationAndCluster20260916060903549.csv'
    df = load_csv(path, low_memory=False)
    _require_columns(
        df,
        {'PooledFundName', 'AllocationYear', 'ChfProjectCode', 'Cluster',
         'Budget', 'ClusterPercentage', 'OrganizationName'},
        'CBPF allocations',
    )
    return df


def load_cbpf_contributions(path: str | Path | None = None) -> pd.DataFrame:
    path = Path(path) if path else RAW_DATA_DIR / 'cbpf' / 'Contribution20260914102012729.csv'
    df = load_csv(path, low_memory=False)
    _require_columns(df, {'PooledFundName', 'FiscalYear', 'DonorName', 'PaidAmt'}, 'CBPF contributions')
    return df


def load_unicef(country: str, year: int, path: str | Path | None = None) -> pd.DataFrame:
    path = Path(path) if path else RAW_DATA_DIR / 'unicef' / f'UNICEF_{country.title()}_{year}_export.csv'
    df = load_csv(path, sep=';')
    _require_columns(df, {'Partner', 'Total contribution'}, 'UNICEF export')
    return df


def load_agency_totals(country: str, path: str | Path | None = None) -> pd.DataFrame:
    path = Path(path) if path else RAW_DATA_DIR / 'agency_totals' / 'funding-flows-agency-totals.xlsx'
    return load_excel(
        path,
        sheet_name=f'{country} agency totals',
        header=None,
        skiprows=1,
        usecols='B:C',
        names=['Agency', 'ReportedTotal'],
    )


def load_lookup(name: str) -> dict:
    return load_json(CONFIG_DIR / name)


def describe_source(df: pd.DataFrame, name: str) -> None:
    print(f'{name}: {len(df):,} rows x {len(df.columns):,} columns')
    for col in df.columns:
        print(f'  - {col}')
