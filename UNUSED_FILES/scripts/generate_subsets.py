#!/usr/bin/env python3
"""Write the 100%-coverage language subsets for Pleiades and Trismegistos and copy the original files.

Coverage rule: a record is included only when every required field is non-empty and not whitespace.
This preserves the original columns and avoids silently dropping records without documenting them.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / 'project'
SOURCE_DIR = ROOT / 'final_datasets' / 'Pleades_Trismegistos'


def clean_text(value):
    if value is None:
        return ''
    text = str(value).strip()
    return '' if text == 'nan' else text


def valid_mask(df: pd.DataFrame, required_columns):
    mask = pd.Series(True, index=df.index)
    for col in required_columns:
        mask &= df[col].map(clean_text).ne('')
    return mask


def write_subset(df: pd.DataFrame, path: Path, subset_name: str, required_columns):
    subset = df.loc[valid_mask(df, required_columns)].copy()
    subset.to_csv(path, sep='\t', index=False, encoding='utf-8')
    print(f'{subset_name}: {len(subset)} rows -> {path}')


def main() -> None:
    PROJECT.mkdir(exist_ok=True)
    PLEIADES_ORIG = PROJECT / 'pleiades' / 'original' / 'pleiades.tsv'
    TM_ORIG = PROJECT / 'trismegistos' / 'original' / 'trismegistos.tsv'
    EM_ORIG = PROJECT / 'cross_matching' / 'original' / 'em.tsv'
    PLEIADES_ORIG.parent.mkdir(parents=True, exist_ok=True)
    TM_ORIG.parent.mkdir(parents=True, exist_ok=True)
    EM_ORIG.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(SOURCE_DIR / 'pleiades.tsv', PLEIADES_ORIG)
    shutil.copy2(SOURCE_DIR / 'trismegistos.tsv', TM_ORIG)
    shutil.copy2(SOURCE_DIR / 'em.tsv', EM_ORIG)

    pleiades = pd.read_csv(PLEIADES_ORIG, sep='\t', dtype=str, encoding='utf-8', keep_default_na=False)
    trismegistos = pd.read_csv(TM_ORIG, sep='\t', dtype=str, encoding='utf-8', keep_default_na=False)

    pleiades_rules = {
        'greek': ['title', 'names_greek'],
        'latin': ['title', 'names_latin'],
        'romanized': ['title', 'names_romanized'],
    }
    trismegistos_rules = {
        'greek': ['name_standard', 'names_greek'],
        'latin': ['name_standard', 'names_latin'],
        'romanized': ['name_standard'],
        'egyptian': ['name_standard', 'names_egyptian'],
        'coptic': ['name_standard', 'names_coptic'],
    }

    for language, columns in pleiades_rules.items():
        write_subset(pleiades, PROJECT / 'pleiades' / 'subsets' / f'pleiades_{language}_100pct.csv', f'pleiades_{language}', columns)

    for language, columns in trismegistos_rules.items():
        write_subset(trismegistos, PROJECT / 'trismegistos' / 'subsets' / f'trismegistos_{language}_100pct.csv', f'trismegistos_{language}', columns)


if __name__ == '__main__':
    main()
