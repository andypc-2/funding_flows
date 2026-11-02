from __future__ import annotations
import pandas as pd
from .flows import FLOW_COLUMNS


def validate_flows(df: pd.DataFrame) -> None:
    missing = sorted(set(FLOW_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f'Missing canonical flow columns: {missing}')
    if df.empty:
        raise ValueError('Flow table is empty')
    if df[['Source', 'Target', 'AmountUSD']].isna().any().any():
        raise ValueError('Flow table contains null Source, Target or AmountUSD values')
    if not pd.api.types.is_numeric_dtype(df['AmountUSD']):
        raise TypeError('AmountUSD must be numeric')
    if (df['AmountUSD'] <= 0).any():
        raise ValueError('AmountUSD must be positive')
