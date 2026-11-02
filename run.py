import argparse
from pathlib import Path

from funding_flows import (
    build_flows,
    create_sankey,
    export_run,
    load_json,
    standardise_agency,
    save_sankey_html,    
)

parser = argparse.ArgumentParser()
parser.add_argument("--country", required=True)
parser.add_argument("--year", required=True, type=int)
parser.add_argument("--output-dir", default="outputs")
args = parser.parse_args()


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config"


sankey_recipients_raw = load_json(
    CONFIG_DIR / "sankey_recipients.json"
)

agency_lookup = load_json(
    CONFIG_DIR / "agency_lookup.json"
)

# Build canonical flows
flows, components = build_flows(
    args.country,
    args.year,
)


# Create Sankey
fig = create_sankey(
    flows=flows,
    keep_destinations=sankey_recipients_raw,
    agency_lookup=agency_lookup,
    country=args.country,
    title=(
        f"{args.country} humanitarian funding flows, "
        f"{args.year}"
    ),
)


# Export outputs
out = export_run(
    fig,
    flows,
    args.country,
    args.year,
    args.output_dir,
)

print(f"Created outputs and saved html in {out}")