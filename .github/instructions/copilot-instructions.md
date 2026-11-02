# GitHub Copilot instructions for `funding_flows`

## Project purpose

This repository contains a Python package for analysing humanitarian funding flows by country and year. It loads and cleans source-specific funding data, converts those sources to a canonical flow schema, validates and combines the flows, and produces presentation-ready Plotly Sankey diagrams and export files.

The current core sources are:

- Financial Tracking Service (FTS)
- UNICEF donor reporting used to substitute selected UNICEF records in FTS
- Central Emergency Response Fund (CERF)
- Country-Based Pooled Funds (CBPF), including allocations and donor contributions

The intended analytical outputs are auditable funding-flow tables and senior-facing visualisations. Correct totals, traceable transformations and avoidance of double counting are more important than clever abstractions.

## How to work in this repository

Before changing code:

1. Inspect the relevant module and its callers.
2. Trace the data from loading through cleaning, canonicalisation, combination, validation and visualisation.
3. Reuse existing functions and configuration rather than duplicating logic.
4. Make the smallest coherent change that satisfies the request.
5. Preserve existing public APIs unless the task explicitly requires an API change.
6. State any assumption about source columns, units, granularity or lookup structure.
7. Add or update tests for behavioural changes.

Do not invent files, functions, columns, configuration keys or datasets. Search the repository first and use the names that actually exist.

## Architecture and ownership

Keep module responsibilities separate.

### `loaders.py`

Owns file discovery, path handling, reading source data and reading JSON lookups. Loading functions should return raw tables or configuration without performing analytical transformations.

### `mappings.py`

Owns reusable name standardisation, including agency, donor and sector mappings. Do not reproduce lookup logic with ad hoc replacements in downstream modules.

### `cleaning.py`

Owns source-specific cleaning and source-specific data corrections.

Current responsibilities include:

- `clean_amount`: parse financial values into numeric form.
- `clean_fts`: filter and clean FTS data, standardise organisations and sectors, and coordinate UNICEF substitution.
- `clean_cerf`: filter and clean CERF allocations.
- `clean_cbpf`: clean CBPF allocations and contributions, including duplicate handling and allocation calculations.
- `collapse_agency`: map standardised recipients into reporting groups such as INGO, NNGO and Other UN.
- `clean_agency_totals`: prepare agency-reported totals.
- `substitute_unicef_donor_data`: replace the relevant FTS UNICEF records with UNICEF donor data.

Source-specific transformations belong here, not in `flows.py`, `pipeline.py` or `sankey.py`.

### `flows.py`

Owns conversion from cleaned source tables to the canonical funding-flow schema.

The canonical columns are exactly:

```python
[
    "Country",
    "Year",
    "Dataset",
    "Source",
    "Target",
    "Sector",
    "AmountUSD",
]
```

Use `_to_canonical` and the existing `prepare_*_flows` functions. Do not introduce alternative schemas or rename canonical columns without updating every consumer and the tests.

Current dataset labels include:

- `FTS`
- `CERF`
- `CBPF`
- `CBPF contribution`

`combine_flows` concatenates canonical frames, coerces `AmountUSD` to numeric, removes records lacking a source, target or amount, and retains positive amounts. Do not silently change these rules.

### `pipeline.py`

Owns orchestration through `build_flows`:

1. Load configuration.
2. Load raw data.
3. Clean FTS and apply the UNICEF substitution.
4. Clean CERF.
5. Clean CBPF allocations and contributions.
6. Convert each source to canonical flows.
7. Combine flows.
8. Collapse recipient agencies into reporting categories.
9. Validate the combined result.
10. Return both `flows` and inspection-ready `components`.

Do not place detailed cleaning or Plotly formatting in the pipeline. Preserve the `components` return value because it supports audit and debugging of intermediate datasets.

### `validation.py`

Owns integrity checks on canonical flows. Prefer explicit failures with actionable messages over silent correction of unexpected data.

### `sankey.py`

Owns Sankey-specific filtering, aggregation, labelling, colours and Plotly figure construction.

`prepare_sankey_edges` converts canonical flows into mechanism-to-recipient edges. It currently:

- collapses ordinary FTS sources to `Bilateral funding`;
- preserves World Bank, African Development Bank and Asian Development Bank as separate mechanisms;
- labels CERF as `CERF`;
- gives CBPF allocations a country-specific humanitarian-fund label;
- filters to configured recipient destinations;
- aggregates `Source` to `Target` values;
- converts values from US dollars to US$ millions;
- optionally filters small flows.

Do not move source-data cleaning into this module. Do not apply agency transformations repeatedly without tracing what `cleaning.py` and `pipeline.py` have already done.

Keep Sankey source labels aligned with `MECHANISM_LINK_COLOURS` and `build_link_colours`. If a mechanism is added or renamed, update all related label and colour logic together.

### `export.py`

Owns run-level export. `export_run` saves:

- the Sankey as HTML;
- canonical flows as CSV;
- run metadata as JSON.

Before adding export functionality, check both `export_run` and `save_sankey_html`. Extend or consolidate an existing route rather than creating a third overlapping implementation.

### `run.py` and `__init__.py`

`run.py` should remain a thin command-line entry point. It may parse arguments and call public package functions, but should not contain cleaning or analytical logic.

`__init__.py` defines the deliberate public API. Do not expose every helper automatically. When adding a public function, update exports intentionally and verify imports still work after package installation.

## Data-quality rules

Treat the following as high-risk changes:

- joins or merges;
- grouping and aggregation;
- duplicate removal;
- UNICEF substitution;
- CBPF project and cluster allocation calculations;
- agency collapsing;
- donor or recipient standardisation;
- conversion between raw currency values and millions;
- combining mechanisms reported at different granularities.

For those changes, check and preferably test:

```python
assert total_before == total_after
```

where totals should be conserved, allowing an explicit numerical tolerance when appropriate.

Also check:

- row counts before and after filtering;
- uniqueness of the intended aggregation keys;
- whether a merge is one-to-one, many-to-one or many-to-many;
- missing values introduced in key fields;
- duplicated financial values;
- unexpected unmapped agencies, donors or sectors;
- whether a mapping or collapse has already been applied;
- whether source tables use project, cluster, transaction, agency or annual-total granularity.

Never resolve a duplication problem by calling `drop_duplicates()` without identifying the correct business key and explaining why discarded rows are duplicates.

Never group together values with incompatible meanings merely because their column names match.

## CBPF rules

CBPF allocation data can contain repeated project values across locations or clusters. Preserve the established business logic in `clean_cbpf`, including the relationship between project budget, cluster percentage and allocated amount.

When modifying CBPF logic:

- identify the project and cluster keys explicitly;
- distinguish allocation records from donor-contribution records;
- verify that location-level repetition does not inflate totals;
- test the aggregate against the expected fund/year total;
- preserve the distinction between the configured fund name and the country display name unless deliberately correcting it across all callers.

Do not infer that all CBPFs report recipients at the same organisational granularity.

## UNICEF substitution rules

The UNICEF substitution is part of FTS cleaning and must remain auditable.

When changing it:

- identify exactly which FTS rows are removed;
- identify exactly which UNICEF rows are inserted;
- preserve `removed_unicef` and `inserted_unicef` inspection outputs;
- standardise donor names using the configured mapping;
- avoid retaining both the replaced FTS amount and its UNICEF replacement;
- compare removed, inserted and final totals by country and year.

Do not implement the substitution a second time in the pipeline or visualisation layer.

## Mapping and configuration rules

Prefer JSON configuration for country-specific or reporting-specific mappings. Do not hard-code long agency, donor, sector, recipient or country lists in Python when an existing lookup file owns that information.

When using lookup dictionaries:

- inspect their actual shape before coding;
- preserve canonical spelling and capitalisation;
- handle missing keys explicitly;
- avoid modifying dictionaries in place unless intentional;
- ensure country-specific mappings use the same country key format as `build_flows`.

Do not silently turn unknown organisations into a known category. Preserve them, label them as genuinely unmapped if that is the established rule, or raise an informative validation error.

## Pandas conventions

Use explicit, readable transformations:

- use `.copy()` after filtering before assignment;
- use `.loc[...]` for conditional assignment;
- use `pd.to_numeric(..., errors="coerce")` where invalid numeric input is expected and subsequently validated;
- specify `dropna=` deliberately in `groupby` operations;
- use named columns rather than positional indexing;
- avoid chained assignment;
- reset indexes only when the index has no analytical meaning;
- keep money in US dollars internally and convert to millions only for display/visualisation fields.

Prefer a sequence of inspectable transformations over a dense method chain when the logic affects financial totals.

## Paths and packaging

Use `pathlib.Path` for filesystem paths. Avoid hard-coded absolute paths and assumptions about the current working directory.

Code must work when the package is installed, not only when run from the repository root. Keep package imports relative within `src/funding_flows` unless there is a clear reason otherwise.

Do not commit or depend on:

- `__pycache__/`;
- virtual environments;
- generated output files;
- raw data that is intentionally excluded from Git;
- local editor settings;
- secrets, tokens or credentials.

Do not assume ignored local data are available to GitHub Copilot or CI. Tests should use small fixtures or synthetic input tables that reproduce the required schema without exposing operational data.

## Testing expectations

Use `pytest` if it is already configured in the repository. Favour small tests around transformations and invariants.

Important test cases include:

- financial-string parsing in `clean_amount`;
- FTS filtering and standardisation;
- removal and replacement of UNICEF rows;
- CERF country/year filtering;
- CBPF duplicate handling and cluster allocation;
- canonical column order and dataset labels;
- preservation of totals during canonicalisation;
- rejection of missing canonical fields;
- removal of non-positive flows by `combine_flows`;
- agency collapsing by country;
- Sankey mechanism classification;
- recipient filtering after standardisation/collapse;
- minimum-flow filtering in millions;
- empty Sankey results raising a clear error;
- export filenames and metadata.

For bug fixes, add a regression test that fails before the fix and passes afterwards.

## Coding style

- Target the Python version declared in `pyproject.toml`.
- Use type hints for public functions and meaningful return types.
- Add concise docstrings that explain purpose, inputs, outputs and non-obvious business rules.
- Keep functions focused and avoid hidden mutation of caller-owned DataFrames.
- Use descriptive names tied to the funding domain.
- Comments should explain why a transformation exists, especially where it prevents double counting.
- Preserve British English in documentation and user-facing text.

Do not perform broad refactors, rename public functions or reformat unrelated files unless explicitly requested.

## How to respond to development requests

When proposing a code change:

1. Name the file and function to change.
2. Explain where the change belongs in the architecture.
3. Provide an exact replacement or patch, not disconnected pseudocode.
4. Identify any affected imports, configuration, tests or public exports.
5. Include a concise command or test demonstrating the change.
6. Flag any possible effect on financial totals or Sankey outputs.

When debugging, reason from the actual traceback, DataFrame columns, dtypes, unique values and intermediate totals supplied by the user. Do not give generic pandas advice when repository-specific code is available.
