from __future__ import annotations

import re
import pandas as pd


def standardise_agency(series: pd.Series, agency_lookup: dict[str, str]) -> pd.Series:
    cleaned = series.astype('string').str.strip()
    return cleaned.map(agency_lookup).fillna(cleaned)


def standardise_donor(series: pd.Series, donor_aliases: dict[str, str]) -> pd.Series:
    def clean(value):
        if pd.isna(value):
            return pd.NA
        name = str(value).strip()
        match = re.fullmatch(r'(.+?),\s*Government of', name, flags=re.IGNORECASE)
        if match:
            name = f'Government of {match.group(1).strip()}'
        key = re.sub(r'\s+', ' ', name).strip().casefold()
        return donor_aliases.get(key, name)
    return series.map(clean).astype('string')


def standardise_sector(series: pd.Series, sector_aliases: dict[str, str], cluster_lookup: dict[str, str]) -> pd.Series:
    cleaned = series.astype('string').str.strip().str.upper()
    cleaned = cleaned.replace(sector_aliases).replace(cluster_lookup).str.title()
    return cleaned.replace({'Wash': 'WASH', 'Cccm': 'CCCM', 'Nfi': 'NFI', 'Nfis': 'NFIs', 'Etc': 'ETC', 'Aap': 'AAP', 'Gbv': 'GBV'})
