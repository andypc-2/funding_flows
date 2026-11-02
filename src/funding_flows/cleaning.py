from __future__ import annotations

import pandas as pd

from .mappings import (
    standardise_agency,
    standardise_donor,
    standardise_sector,
)

def clean_amount(series: pd.Series) -> pd.Series:
    """
    Convert funding amounts to numeric values.

    Non-numeric values become NaN.
    """

    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    return pd.to_numeric(
        series
        .astype("string")
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.strip(),
        errors="coerce",
    )

def clean_fts(
    df,
    country,
    year,
    unicef_df,
    unicef_donor_map,
    agency_lookup,
    donor_aliases,
    sector_aliases,
    cluster_lookup,
    top20=False,
):
    """
    Clean raw FTS data for use in the funding-flow pipeline.
    """

    df = df.reset_index().copy()

    duplicated = df.columns[df.columns.duplicated()].tolist()

    if duplicated:
        raise ValueError(
            f"Duplicate FTS columns: {duplicated}"
        )

    # --------------------------------------------------
    # UNICEF substitution
    # --------------------------------------------------    
    
    df, removed_unicef, inserted_unicef = (
        substitute_unicef_donor_data(
            fts_df=df,
            unicef_df=unicef_df,
            country=country,
            unicef_donor_map=unicef_donor_map,
        )
    )

    # --------------------------------------------------
    # Clean amounts
    # --------------------------------------------------

    df["Amount (US$)"] = clean_amount(
        df["Amount (US$)"]
    )

    # --------------------------------------------------
    # Replace blank text fields
    # --------------------------------------------------

    text_cols = [
        "Source org.",
        "Destination org.",
        "Sector",
    ]

    for col in text_cols:

        blank = (
            df[col].isna()
            | df[col].astype(str).str.strip().eq("")
        )

        df.loc[blank, col] = "Unreported"

    # --------------------------------------------------
    # Standardise organisations
    # --------------------------------------------------

    df["Destination org."] = standardise_agency(
        df["Destination org."],
        agency_lookup,
    )

    df["Source org."] = standardise_donor(
        df["Source org."],
        donor_aliases,
    )

    # --------------------------------------------------
    # Standardise sectors
    # --------------------------------------------------

    df["Sector"] = standardise_sector(
        df["Sector"],
        sector_aliases,
        cluster_lookup,
    )

    # --------------------------------------------------
    # Keep government/institutional donors
    # --------------------------------------------------

    donor_pattern = (
        r"government|echo|sida|european commission|"
        r"world bank|development bank"
    )

    keep = df["Source org."].str.contains(
        donor_pattern,
        case=False,
        na=False,
        regex=True,
    )

    df = df.loc[keep].copy()

    # --------------------------------------------------
    # Optionally restrict to largest 20 donors
    # --------------------------------------------------

    if top20:

        top_donors = (
            df.groupby("Source org.")["Amount (US$)"]
            .sum()
            .nlargest(20)
            .index
        )

        df = df.loc[
            df["Source org."].isin(top_donors)
        ].copy()

    return df, removed_unicef, inserted_unicef 

def clean_cerf(
    df,
    country,
    year,
    agency_lookup,
    cerf_lookup,
    sector_aliases,
    cluster_lookup,
):

    df = df.copy()

    # Standardise country/fund names
    df["Fund"] = (
        df["Fund"]
        .replace(cerf_lookup)
        .astype("string")
        .str.strip()
    )

    # Country/year
    country_mask = (
        df["Fund"]
        .str.casefold()
        .eq(country.strip().casefold())
    )

    year_mask = df["Year"].eq(year)

    df = df.loc[
        country_mask & year_mask
    ].copy()

    # Agency
    df["Agency"] = standardise_agency(
        df["Agency"],
        agency_lookup,
    )

    # Sector
    df["Sector"] = standardise_sector(
        df["Cluster"],
        sector_aliases,
        cluster_lookup,
    )

    # Amount
    df["Amount"] = clean_amount(
        df["Budget"]
    )

    return df


def clean_cbpf(
    allocations,
    contributions,
    fund_name,
    year,
    agency_lookup,
    donor_aliases,
    check_duplicates=False,
):

    # ------------------------------------------
    # Allocations
    # ------------------------------------------

    alloc = allocations.loc[
        allocations["PooledFundName"]
        .astype("string")
        .str.casefold()
        .eq(fund_name.casefold())
        &
        allocations["AllocationYear"].eq(year)
    ].copy()

    duplicate_mask = alloc.duplicated(
        ["ChfProjectCode", "Cluster"],
        keep=False,
    )

    if check_duplicates and duplicate_mask.any():

        print(
            alloc.loc[
                duplicate_mask,
                ["ChfProjectCode", "Cluster"],
            ]
        )

    alloc = alloc.drop_duplicates(
        ["ChfProjectCode", "Cluster"]
    ).copy()

    alloc["Agency"] = standardise_agency(
        alloc["OrganizationName"],
        agency_lookup,
    )

    alloc["Amount"] = (
        clean_amount(alloc["Budget"])
        * clean_amount(alloc["ClusterPercentage"])
        / 100
    )

    # ------------------------------------------
    # Contributions
    # ------------------------------------------

    contrib = contributions.loc[
        contributions["PooledFundName"]
        .astype("string")
        .str.casefold()
        .eq(fund_name.casefold())
        &
        contributions["FiscalYear"].eq(year)
    ].copy()

    contrib["Donor"] = standardise_donor(
        contrib["DonorName"],
        donor_aliases,
    )

    contrib["Amount"] = clean_amount(
        contrib["PaidAmt"]
    )

    return alloc, contrib

def collapse_agency(
    agency,
    country,
    nngo_lookup,
    ingo_lookup,
    other_un,
):
    if pd.isna(agency):
        return agency

    agency = str(agency).strip()

    # Organisations/categories we want to preserve
    keep = {
        "UNICEF",
        "WFP",
        "UNHCR",
        "IOM",
        "ICRC",
        "IFRC",
        "UN Agency",
        "UN Agencies (Confidential)",
    }

    if agency in keep:
        return agency

    # International NGOs
    if (
        agency in ingo_lookup
        or agency.lower() in {
            "ingo",
            "international ngo",
        }
    ):
        return "INGO"

    # National NGOs
    if (
        agency in nngo_lookup.get(country, [])
        or agency.lower() in {
            "nngo",
            "national ngo",
        }
    ):
        return "NNGO"

    # Other UN agencies
    if agency in other_un:
        return "Other UN"

    return agency    

def clean_agency_totals(df, chf_to_usd=1.2):
    out = df.copy()
    out['Agency'] = out['Agency'].astype('string').str.strip().str.upper()
    out['ReportedTotal'] = pd.to_numeric(out['ReportedTotal'], errors='coerce')
    out = out.dropna(subset=['Agency', 'ReportedTotal'])
    out['ReportedTotalMillions'] = out['ReportedTotal'] / 1_000_000
    out.loc[out['Agency'].eq('ICRC'), 'ReportedTotalMillions'] *= chf_to_usd
    return out

def substitute_unicef_donor_data(
    fts_df,
    unicef_df,
    country,
    unicef_donor_map,
):
    """
    Replace UNICEF rows in FTS with UNICEF-reported donor totals.

    Returns
    -------
    combined : pd.DataFrame
        FTS data with UNICEF rows replaced.

    removed_rows : pd.DataFrame
        Original UNICEF rows removed from FTS.

    replacement : pd.DataFrame
        UNICEF-reported rows inserted into FTS.
    """

    fts_df = fts_df.copy()
    unicef = unicef_df.copy()

    # --------------------------------------------------
    # Standardise UNICEF donor names
    # --------------------------------------------------

    unicef["Partner"] = (
        unicef["Partner"]
        .replace(unicef_donor_map)
    )

    # --------------------------------------------------
    # Clean contribution amount
    # --------------------------------------------------

    unicef["Total contribution"] = clean_amount(
        unicef["Total contribution"]
    )

    # Keep only positive contributions
    unicef = unicef.loc[
        unicef["Total contribution"] > 0
    ].copy()

    # --------------------------------------------------
    # Remove existing UNICEF rows from FTS
    # --------------------------------------------------

    remove_mask = (
        fts_df["Destination org."]
        .astype("string")
        .str.contains(
            "United Nations Children's Fund",
            case=False,
            na=False,
        )
    )

    removed_rows = (
        fts_df.loc[remove_mask]
        .copy()
    )

    remaining = (
        fts_df.loc[~remove_mask]
        .copy()
    )

    # --------------------------------------------------
    # Build replacement rows matching FTS structure
    # --------------------------------------------------

    replacement = pd.DataFrame({
        "Source org.": unicef["Partner"],
        "Destination org.": "United Nations Children's Fund",
        "Description": "UNICEF reported funding",
        "Sector": "Unreported",
        "Amount (US$)": unicef["Total contribution"],
        "Amount shared on boundary": 0,
        "Total Contribution (US$)": unicef["Total contribution"],
        "Funding status": "Paid Contribution",
        "Boundary": "",
        "Source org. type": "Donor",
        "Destination org. type": "UN Agency",
        "Destination country": country,
        "Earmarking": "Unreported",
        "Modality": "UNICEF substitute",
    })

    # --------------------------------------------------
    # Recombine FTS
    # --------------------------------------------------

    combined = pd.concat(
        [remaining, replacement],
        ignore_index=True,
    )

    return combined, removed_rows, replacement