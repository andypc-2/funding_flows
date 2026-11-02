from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from .cleaning import standardise_agency
from pathlib import Path

MECHANISM_LINK_COLOURS = {
    "Bilateral funding": "rgba(68,114,196,0.25)",
    "CERF": "rgba(237,125,49,0.25)",
    "Humanitarian Fund": "rgba(112,173,71,0.25)",
    "World Bank": "rgba(112,48,160,0.25)",
    "African Development Bank": "rgba(197,90,17,0.25)",
    "Asian Development Bank": "rgba(197,90,17,0.25)",
}


def prepare_sankey_edges(
    flows: pd.DataFrame,
    keep_destinations: list[str],
    agency_lookup: dict,
    country: str,
    min_flow_millions: float = 0,
) -> pd.DataFrame:
    
    """
    Prepare mechanism-to-recipient edges for the Sankey.

    Recipient names are standardised using the same agency lookup
    applied during source-data cleaning.
    """

    required = {
        "Source",
        "Target",
        "AmountUSD",
    }

    missing = required - set(flows.columns)

    if missing:
        raise ValueError(
            f"Missing columns required for Sankey: {sorted(missing)}"
        )

    df = flows.copy()

    # ---------------------------------------------------
    # Construct mechanism-level Sankey sources
    # ---------------------------------------------------

    fts_mask = df["Dataset"].eq("FTS")

    # Preserve multilateral development bank flows reported in FTS
    world_bank_mask = (
        fts_mask
        & df["Source"].str.contains(
            "World Bank",
            case=False,
            na=False,
        )
    )

    afdb_mask = (
        fts_mask
        & df["Source"].str.contains(
            "African Development Bank",
            case=False,
            na=False,
        )
    )

    adb_mask = (
        fts_mask
        & df["Source"].str.contains(
            "Asian Development Bank",
            case=False,
            na=False,
        )
    )

    df.loc[
        world_bank_mask,
        "Source",
    ] = "World Bank"

    df.loc[
        afdb_mask,
        "Source",
    ] = "African Development Bank"

    df.loc[
        adb_mask,
        "Source",
    ] = "Asian Development Bank"

    # Collapse all other FTS donors into Bilateral funding
    bilateral_mask = (
        fts_mask
        & ~world_bank_mask
        & ~afdb_mask
        & ~adb_mask
    )

    df.loc[
        bilateral_mask,
        "Source",
    ] = "Bilateral funding"

    # CERF
    df.loc[
        df["Dataset"].eq("CERF"),
        "Source",
    ] = "CERF"

    # Country-specific CBPF display name
    df.loc[
        df["Dataset"].eq("CBPF"),
        "Source",
    ] = f"{country} Humanitarian Fund"   

    # Standardise recipient filter to match cleaned flow targets
    keep_destinations = (
        standardise_agency(
            pd.Series(keep_destinations),
            agency_lookup,
        )
        .tolist()
    )

    # Keep only selected recipient organisations
    df = df.loc[
        df["Target"].isin(keep_destinations)
    ].copy()

    # Keep only mechanism-level sources
    fixed_mechanisms = {
        "Bilateral funding",
        "CERF",
        "World Bank",
        "African Development Bank",
        "Asian Development Bank",
    }

    is_fixed_mechanism = df["Source"].isin(
        fixed_mechanisms
    )

    is_cbpf = (
        df["Source"]
        .str.contains(
            "Humanitarian Fund",
            case=False,
            na=False,
        )
    )

    df = df.loc[
        is_fixed_mechanism | is_cbpf
    ].copy()

    # Aggregate mechanism -> recipient
    df = (
        df.groupby(
            ["Source", "Target"],
            as_index=False,
        )["AmountUSD"]
        .sum()
    )

    # Convert to millions
    df["AmountMillions"] = (
        df["AmountUSD"] / 1_000_000
    )

    # Optional minimum-flow filter
    df = df.loc[
        df["AmountMillions"] >= min_flow_millions
    ].copy()

    return df.reset_index(drop=True)

def build_nodes(edges: pd.DataFrame):
    """
    Build Sankey node labels and lookup dictionary.
    """

    labels = list(
        dict.fromkeys(
            edges["Source"].tolist()
            + edges["Target"].tolist()
        )
    )

    node_lookup = {
        label: i
        for i, label in enumerate(labels)
    }

    return labels, node_lookup    

def build_node_colours(
    labels,
    mechanisms=None,
    agency_colours=None,
):
    """
    Assign colours to Sankey nodes.
    """

    mechanisms = mechanisms or {}
    agency_colours = agency_colours or {}

    colours = []

    for label in labels:

        if label in mechanisms:
            colour = mechanisms[label]

        elif label in agency_colours:
            colour = agency_colours[label]

        else:
            colour = "#BDBDBD"

        colours.append(colour)

    return colours

def create_sankey(
    flows: pd.DataFrame,
    keep_destinations: list[str],
    agency_lookup: dict,
    country: str,
    title: str | None = None,
    min_flow_millions: float = 0,
    mechanism_colours: dict | None = None,
    agency_colours: dict | None = None,
    width: int = 1400,
    height: int = 900,
):
    """
    Create a Sankey chart from canonical funding flows.
    """

    edges = prepare_sankey_edges(
        flows=flows,
        keep_destinations=keep_destinations,
        agency_lookup=agency_lookup,
        country=country,
        min_flow_millions=min_flow_millions,
    )

    if edges.empty:
        raise ValueError(
            "No flows remain after applying Sankey filters."
        )

    labels, node_lookup = build_nodes(edges)

    node_totals = {}

    for node in labels:

        outgoing = edges.loc[
            edges["Source"] == node,
            "AmountMillions",
        ].sum()

        incoming = edges.loc[
            edges["Target"] == node,
            "AmountMillions",
        ].sum()

        node_totals[node] = max(
            outgoing,
            incoming,
        )

    node_labels = [
        f"{node}: ${node_totals[node]:,.1f}M"
        for node in labels
    ]

    link_colours = build_link_colours(edges)

    link_customdata = [
        [source, target, value]
        for source, target, value in zip(
            edges["Source"],
            edges["Target"],
            edges["AmountMillions"],
        )
    ]

    node_colours = build_node_colours(
        labels=labels,
        mechanisms=mechanism_colours or MECHANISM_LINK_COLOURS,
        agency_colours=agency_colours,
    )

    source_indices = (
        edges["Source"]
        .map(node_lookup)
        .tolist()
    )

    target_indices = (
        edges["Target"]
        .map(node_lookup)
        .tolist()
    )

    values = edges[
        "AmountMillions"
    ].tolist()

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",

            node=dict(
                label=node_labels,
                color=node_colours,
                pad=30,
                thickness=28,

                line=dict(
                    color="rgba(0,0,0,0.4)",
                    width=0.5,
                ),

                hovertemplate=(
                    "%{label}"
                    "<extra></extra>"
                ),
            ),

            link=dict(
                source=source_indices,
                target=target_indices,
                value=values,
                color=link_colours,
                customdata=link_customdata,

                hovertemplate=(
                    "%{customdata[0]} → %{customdata[1]}"
                    "<br>US$%{customdata,.2f} million"
                    "<extra></extra>"
                ),
            ),
        )
    )

    fig.update_layout(
        title=dict(
            text=title,
            x=0.01,
            xanchor="left",
        ),
        width=width,
        height=height,
        font=dict(
            size=13,
        ),
        margin=dict(
            l=20,
            r=20,
            t=80,
            b=30,
        ),
    )

    return fig

def save_sankey_html(
    fig: go.Figure,
    country: str,
    year: int,
    output_dir: str | Path = "outputs",
) -> Path:
    """
    Save a Plotly Sankey figure as an interactive HTML file.

    Returns
    -------
    Path
        Path to the saved HTML file.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    country_slug = (
        country
        .strip()
        .lower()
        .replace(" ", "_")
    )

    output_path = (
        output_dir
        / f"{country_slug}_funding_sankey_{year}.html"
    )

    fig.write_html(
        output_path,
        include_plotlyjs="cdn",
        full_html=True,
    )

    return output_path

def build_link_colours(edges: pd.DataFrame) -> list[str]:
    """
    Assign Sankey link colours according to funding mechanism.
    """

    colours = []

    for source in edges["Source"]:

        if source == "Bilateral funding":
            colour = MECHANISM_LINK_COLOURS["Bilateral funding"]

        elif source == "CERF":
            colour = MECHANISM_LINK_COLOURS["CERF"]

        elif "Humanitarian Fund" in source:
            colour = MECHANISM_LINK_COLOURS["Humanitarian Fund"]

        elif source == "World Bank":
            colour = MECHANISM_LINK_COLOURS["World Bank"]

        elif source == "African Development Bank":
            colour = MECHANISM_LINK_COLOURS[
                "African Development Bank"
            ]

        elif source == "Asian Development Bank":
            colour = MECHANISM_LINK_COLOURS[
                "Asian Development Bank"
            ]

        else:
            colour = "rgba(165,165,165,0.35)"

        colours.append(colour)

    return colours