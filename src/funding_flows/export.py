from __future__ import annotations
import json
from pathlib import Path


def export_run(fig, flows, country, year, output_dir):
    out = Path(output_dir) / f'{country.lower().replace(" ", "_")}_{year}'
    out.mkdir(parents=True, exist_ok=True)
    stem = f'{country.lower().replace(" ", "_")}_{year}'
    fig.write_html(out / f'{stem}_sankey.html')
    flows.to_csv(out / f'{stem}_flows.csv', index=False)
    metadata = {'country': country, 'year': year, 'datasets': sorted(flows['Dataset'].dropna().unique().tolist())}
    (out / 'run_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return out
