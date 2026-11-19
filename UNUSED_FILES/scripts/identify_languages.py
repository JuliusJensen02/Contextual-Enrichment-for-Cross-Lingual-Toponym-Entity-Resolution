#!/usr/bin/env python3
"""Identify language-specific coverage and decide which language subsets are valid for matching.

The Pleiades and Trismegistos tables record names in ancient Greek, Latin, and in some cases
Romanized/Latinized renderings. For strict linguistically controlled matching we treat the
language-specific subsets as same-language only, and excluding cross-language comparisons from
matching unless they are explicitly marked as diagnostic rather than valid matches.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PLEIADES_PATH = ROOT / 'final_datasets' / 'Pleades_Trismegistos' / 'pleiades.tsv'
TRISMEGISTOS_PATH = ROOT / 'final_datasets' / 'Pleades_Trismegistos' / 'trismegistos.tsv'


def clean_value(value):
    if value is None:
        return ''
    text = str(value).strip()
    return '' if text == '' else text


def valid_mask(df: pd.DataFrame, required_columns):
    mask = pd.Series(True, index=df.index)
    for col in required_columns:
        mask &= df[col].map(clean_value).ne('')
    return mask


def coverage_report(df: pd.DataFrame, dataset_name: str, language_map):
    rows = []
    total = len(df)
    for language, fields in language_map.items():
        mask = valid_mask(df, fields)
        count = int(mask.sum())
        rows.append({
            'dataset': dataset_name,
            'language': language,
            'relevant_columns': ' | '.join(fields),
            'total_records': total,
            'records_with_complete_coverage': count,
            'coverage_pct': round((count / total) * 100, 2) if total else 0.0,
        })
    return pd.DataFrame(rows)


def main() -> None:
    pleiades = pd.read_csv(PLEIADES_PATH, sep='\t', dtype=str, encoding='utf-8', keep_default_na=False)
    trismegistos = pd.read_csv(TRISMEGISTOS_PATH, sep='\t', dtype=str, encoding='utf-8', keep_default_na=False)

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

    report = pd.concat([
        coverage_report(pleiades, 'Pleiades', pleiades_rules),
        coverage_report(trismegistos, 'Trismegistos', trismegistos_rules),
    ], ignore_index=True)
    print(report.to_string(index=False))


if __name__ == '__main__':
    main()
