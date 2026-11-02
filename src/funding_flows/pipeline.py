from __future__ import annotations

from .loaders import (
    load_fts,
    load_unicef,
    load_cerf,
    load_cbpf_allocations,
    load_cbpf_contributions,
    load_lookup,
    load_json,
)

from .cleaning import (
    clean_fts,
    clean_cerf,
    clean_cbpf,
    collapse_agency
)

from .flows import (
    prepare_fts_flows,
    prepare_cerf_flows,
    prepare_cbpf_allocation_flows,
    prepare_cbpf_contribution_flows,
    combine_flows,
)

from .validation import validate_flows

def build_flows(
    country: str,
    year: int,
    top20: bool = False,
    check_duplicates: bool = False,
):
    """
    Build the complete canonical funding-flow dataset
    for a country and year.

    Returns
    -------
    flows
        Combined canonical flow dataframe.

    components
        Dictionary containing the individual flow tables
        and useful intermediate datasets.
    """

    # --------------------------------------------------
    # Load configuration
    # --------------------------------------------------

    agency_lookup = load_lookup(
        "agency_lookup.json"
    )

    nngo_lookup = load_lookup(
        "ngos.json"
    )

    ingo_lookup = load_lookup(
        "ingos.json"
    )    

    other_un = load_lookup(
        "other_un.json"
    )

    donor_aliases = load_lookup(
        "donor_aliases.json"
    )

    unicef_donor_map = load_lookup(
        "unicef_donor_map.json"
    )

    sector_aliases = load_lookup(
        "sector_aliases.json"
    )

    cluster_lookup = load_lookup(
        "cluster_lookup.json"
    )

    cerf_lookup = load_lookup(
        "cerf_lookup.json"
    )

    cbpf_lookup = load_lookup(
        "cbpf_lookup.json"
    )

    # --------------------------------------------------
    # Load raw data
    # --------------------------------------------------

    fts_raw = load_fts(
        country=country,
        year=year,
    )

    unicef_raw = load_unicef(
        country=country,
        year=year,
    )

    cerf_raw = load_cerf()

    cbpf_alloc_raw = load_cbpf_allocations()

    cbpf_contrib_raw = load_cbpf_contributions()

    # --------------------------------------------------
    # Clean FTS + substitute UNICEF data
    # --------------------------------------------------

    (
        fts,
        removed_unicef,
        inserted_unicef,
    ) = clean_fts(
        df=fts_raw,
        country=country,
        year=year,
        unicef_df=unicef_raw,
        unicef_donor_map=unicef_donor_map,
        agency_lookup=agency_lookup,
        donor_aliases=donor_aliases,
        sector_aliases=sector_aliases,
        cluster_lookup=cluster_lookup,
        top20=top20,
    )

    # --------------------------------------------------
    # Clean CERF
    # --------------------------------------------------

    cerf = clean_cerf(
        df=cerf_raw,
        country=country,
        year=year,
        agency_lookup=agency_lookup,
        cerf_lookup=cerf_lookup,
        sector_aliases=sector_aliases,
        cluster_lookup=cluster_lookup,
    )

    # --------------------------------------------------
    # Clean CBPF
    # --------------------------------------------------

    if country not in cbpf_lookup:
        raise ValueError(
            f"No CBPF mapping configured for {country}"
        )

    fund_name = cbpf_lookup[country]

    (
        cbpf_alloc,
        cbpf_contrib,
    ) = clean_cbpf(
        allocations=cbpf_alloc_raw,
        contributions=cbpf_contrib_raw,
        fund_name=country,
        year=year,
        agency_lookup=agency_lookup,
        donor_aliases=donor_aliases,
        check_duplicates=check_duplicates,
    )

    # --------------------------------------------------
    # Construct canonical flows
    # --------------------------------------------------

    fts_flows = prepare_fts_flows(
        df=fts,
        country=country,
        year=year,
    )

    cerf_flows = prepare_cerf_flows(
        df=cerf,
        country=country,
        year=year,
    )

    cbpf_alloc_flows = prepare_cbpf_allocation_flows(
        df=cbpf_alloc,
        country=country,
        year=year,
        fund_name=country,
    )

    cbpf_contrib_flows = prepare_cbpf_contribution_flows(
        df=cbpf_contrib,
        country=country,
        year=year,
        fund_name=fund_name,
    )

    # --------------------------------------------------
    # Combine
    # --------------------------------------------------

    flows = combine_flows(
        fts_flows,
        cerf_flows,
        cbpf_alloc_flows,
        cbpf_contrib_flows,
    )

    # --------------------------------------------------
    # Collapse nngos and ingos and map UN other
    # --------------------------------------------------

    flows["Target"] = flows["Target"].apply(
        lambda agency: collapse_agency(
            agency,
            country=country,
            nngo_lookup=nngo_lookup,
            ingo_lookup=ingo_lookup,
            other_un=other_un,
        )
    )


    # flows = (
    #     flows
    #     .groupby(
    #         ["Dataset", "Source", "Target"],
    #         as_index=False,
    #     )["AmountUSD"]
    #     .sum()
    # )    

    # --------------------------------------------------
    # Validate
    # --------------------------------------------------

    validate_flows(flows)

    # --------------------------------------------------
    # Keep source components available for inspection
    # --------------------------------------------------

    components = {
        "fts": fts,
        "cerf": cerf,
        "cbpf_allocations": cbpf_alloc,
        "cbpf_contributions": cbpf_contrib,

        "fts_flows": fts_flows,
        "cerf_flows": cerf_flows,
        "cbpf_allocation_flows": cbpf_alloc_flows,
        "cbpf_contribution_flows": cbpf_contrib_flows,

        "removed_unicef": removed_unicef,
        "inserted_unicef": inserted_unicef,
    }

    return flows, components