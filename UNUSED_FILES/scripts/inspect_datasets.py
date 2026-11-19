#!/usr/bin/env python3
"""Inspect the Pleiades/Trismegistos source tables and report the relevant identifiers and language columns.

This script does not modify the source files. It is intended as a quick audit and a
reproducibility aid before the subset generation and cross-matching scripts run.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PLEIADES_PATH = ROOT / 'final_datasets' / 'Pleades_Trismegistos' / 'pleiades.tsv'
TRISMEGISTOS_PATH = ROOT / 'final_datasets' / 'Pleades_Trismegistos' / 'trismegistos.tsv'
EM_PATH = ROOT / 'final_datasets' / 'Pleades_Trismegistos' / 'em.tsv'


def load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep='\t', dtype=str, encoding='utf-8', keep_default_na=False)


def non_empty_count(df: pd.DataFrame, col: str) -> int:
    return int(df[col].fillna('').astype(str).str.strip().ne('').sum())


def main() -> None:
    pleiades = load(PLEIADES_PATH)
    trismegistos = load(TRISMEGISTOS_PATH)
    em = load(EM_PATH)

    print('Pleiades rows:', len(pleiades))
    print('Pleiades primary key:', 'pleiades_id')
    print('Pleiades language-like columns:', [c for c in pleiades.columns if 'name' in c.lower() or 'language' in c.lower()])
    for c in ['title', 'names_romanized', 'names_greek', 'names_latin', 'names_by_language']:
        if c in pleiades.columns:
            print(f'  {c}: {non_empty_count(pleiades, c)}')

    print('\nTrismegistos rows:', len(trismegistos))
    print('Trismegistos primary key:', 'trismegistos_id')
    print('Trismegistos language-like columns:', [c for c in trismegistos.columns if 'name' in c.lower() or 'language' in c.lower()])
    for c in ['name_standard', 'names_romanized', 'names_greek', 'names_latin', 'names_egyptian', 'names_coptic']:
        if c in trismegistos.columns:
            print(f'  {c}: {non_empty_count(trismegistos, c)}')

    print('\nEM rows:', len(em))
    print('EM columns:', list(em.columns))
    print('EM identifiers:', ['pleiades_id', 'trismegistos_id'])
    print('Distinct Pleiades IDs in EM:', em['pleiades_id'].nunique())
    print('Distinct Trismegistos IDs in EM:', em['trismegistos_id'].nunique())

    duplicate_pleiades = em['pleiades_id'].value_counts()
    duplicate_trismegistos = em['trismegistos_id'].value_counts()
    print('Pleiades IDs with >1 TM match:', int((duplicate_pleiades > 1).sum()))
    print('Trismegistos IDs with >1 Pleiades match:', int((duplicate_trismegistos > 1).sum()))


if __name__ == '__main__':
    main()
