from __future__ import annotations
import pandas as pd


FLOW_COLUMNS = [
    "Country",
    "Year",
    "Dataset",
    "Source",
    "Target",
    "Sector",
    "AmountUSD",
]


def _to_canonical(
    df,
    country,
    year,
    dataset,
    source_col,
    target_col,
    amount_col,
    sector_col=None,
):
    """
    Convert a source-specific flow table to the
    canonical funding-flow structure.
    """

    out = pd.DataFrame({
        "Country": country,
        "Year": year,
        "Dataset": dataset,
        "Source": df[source_col],
        "Target": df[target_col],
        "Sector": (
            df[sector_col]
            if sector_col is not None
            else pd.NA
        ),
        "AmountUSD": pd.to_numeric(
            df[amount_col],
            errors="coerce",
        ),
    })

    return out[FLOW_COLUMNS]

def prepare_fts_flows(
    df,
    country,
    year,
):
    """
    Convert cleaned FTS data into canonical flows.
    """

    grouped = (
        df.groupby(
            [
                "Source org.",
                "Destination org.",
                "Sector",
            ],
            dropna=False,
            as_index=False,
        )["Amount (US$)"]
        .sum()
    )

    return _to_canonical(
        df=grouped,
        country=country,
        year=year,
        dataset="FTS",
        source_col="Source org.",
        target_col="Destination org.",
        sector_col="Sector",
        amount_col="Amount (US$)",
    )

def prepare_cerf_flows(
    df,
    country,
    year,
):
    """
    Convert cleaned CERF allocations into canonical flows.
    """

    grouped = (
        df.groupby(
            [
                "Agency",
                "Sector",
            ],
            dropna=False,
            as_index=False,
        )["Amount"]
        .sum()
    )

    grouped["Source"] = "CERF"

    return _to_canonical(
        df=grouped,
        country=country,
        year=year,
        dataset="CERF",
        source_col="Source",
        target_col="Agency",
        sector_col="Sector",
        amount_col="Amount",
    )

def prepare_cbpf_allocation_flows(
    df,
    country,
    year,
    fund_name,
):
    """
    Convert cleaned CBPF allocations into canonical flows.
    """

    grouped = (
        df.groupby(
            [
                "Agency",
                "Cluster",
            ],
            dropna=False,
            as_index=False,
        )["Amount"]
        .sum()
    )

    grouped["Source"] = fund_name

    return _to_canonical(
        df=grouped,
        country=country,
        year=year,
        dataset="CBPF",
        source_col="Source",
        target_col="Agency",
        sector_col="Cluster",
        amount_col="Amount",
    )

def prepare_cbpf_contribution_flows(
    df,
    country,
    year,
    fund_name,
):
    """
    Convert CBPF donor contributions into canonical flows.
    """

    grouped = (
        df.groupby(
            "Donor",
            as_index=False,
        )["Amount"]
        .sum()
    )

    grouped["Target"] = fund_name

    return _to_canonical(
        df=grouped,
        country=country,
        year=year,
        dataset="CBPF contribution",
        source_col="Donor",
        target_col="Target",
        amount_col="Amount",
    )

def combine_flows(*frames):
    """
    Combine canonical funding-flow tables.
    """

    flows = pd.concat(
        frames,
        ignore_index=True,
    )

    flows["AmountUSD"] = pd.to_numeric(
        flows["AmountUSD"],
        errors="coerce",
    )

    flows = flows.dropna(
        subset=[
            "Source",
            "Target",
            "AmountUSD",
        ]
    )

    flows = flows.loc[
        flows["AmountUSD"] > 0
    ].copy()

    return flows.reset_index(drop=True)