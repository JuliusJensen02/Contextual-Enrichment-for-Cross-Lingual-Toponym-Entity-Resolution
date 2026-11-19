#!/usr/bin/env python3
"""Enumerate all language-specific subset combinations and compute the compatible match counts.

The weathered linguistic rule is simple: same-language comparisons are valid; cross-language
comparisons are excluded from the matching analysis even if they still produce overlaps in the EM
file. This preserves the strictness requested for linguistically controlled matching.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / 'project'
EM_PATH = PROJECT / 'cross_matching' / 'original' / 'em.tsv'

P_LANGS = ['greek', 'latin', 'romanized']
T_LANGS = ['greek', 'latin', 'romanized', 'egyptian', 'coptic']


def load(path):
    return pd.read_csv(path, sep='\t', dtype=str, encoding='utf-8', keep_default_na=False)


def compatibility(p_lang: str, t_lang: str) -> bool:
    return p_lang == t_lang


def main() -> None:
    em = load(EM_PATH)
    results = []
    match_rows = []
    unmatched_rows = []
    coverage_rows = []

    original_p = load(ROOT / 'final_datasets' / 'Pleades_Trismegistos' / 'pleiades.tsv')
    original_t = load(ROOT / 'final_datasets' / 'Pleades_Trismegistos' / 'trismegistos.tsv')

    for dataset_name, df, languages in [
        ('Pleiades', original_p, {'greek': ['title', 'names_greek'], 'latin': ['title', 'names_latin'], 'romanized': ['title', 'names_romanized']}),
        ('Trismegistos', original_t, {'greek': ['name_standard', 'names_greek'], 'latin': ['name_standard', 'names_latin'], 'romanized': ['name_standard'], 'egyptian': ['name_standard', 'names_egyptian'], 'coptic': ['name_standard', 'names_coptic']}),
    ]:
        total = len(df)
        for language, columns in languages.items():
            mask = pd.Series(True, index=df.index)
            for col in columns:
                mask &= df[col].fillna('').astype(str).str.strip().ne('')
            count = int(mask.sum())
            coverage_rows.append({
                'dataset': dataset_name,
                'language': language,
                'relevant_columns': ' | '.join(columns),
                'total_records': total,
                'records_with_complete_coverage': count,
                'coverage_percentage': round((count / total) * 100, 2) if total else 0.0,
            })

    for p_lang in P_LANGS:
        p_df = load(PROJECT / 'pleiades' / 'subsets' / f'pleiades_{p_lang}_100pct.csv')
        p_ids = set(p_df['pleiades_id'].astype(str))
        for t_lang in T_LANGS:
            t_df = load(PROJECT / 'trismegistos' / 'subsets' / f'trismegistos_{t_lang}_100pct.csv')
            t_ids = set(t_df['trismegistos_id'].astype(str))
            subset_matches = em[
                em['pleiades_id'].astype(str).isin(p_ids) &
                em['trismegistos_id'].astype(str).isin(t_ids)
            ].copy()
            unique_pairs = subset_matches[['pleiades_id', 'trismegistos_id']].drop_duplicates()
            result = {
                'pleiades_language': p_lang,
                'trismegistos_language': t_lang,
                'linguistic_compatibility': compatibility(p_lang, t_lang),
                'number_of_matching_pairs': int(len(subset_matches)),
                'number_of_unique_matches': int(len(unique_pairs)),
                'unmatched_pleiades_records': int(len(p_ids - set(subset_matches['pleiades_id'].astype(str)))),
                'unmatched_trismegistos_records': int(len(t_ids - set(subset_matches['trismegistos_id'].astype(str)))),
            }
            results.append(result)

            if compatibility(p_lang, t_lang):
                subset_matches = subset_matches.drop(columns=[c for c in ['pleiades_title', 'trismegistos_name'] if c in subset_matches.columns])
                p_title_map = p_df[['pleiades_id', 'title']].rename(columns={'title': 'pleiades_title'}).drop_duplicates()
                t_name_map = t_df[['trismegistos_id', 'name_standard']].rename(columns={'name_standard': 'trismegistos_name'}).drop_duplicates()
                subset_matches = subset_matches.merge(p_title_map, on='pleiades_id', how='left')
                subset_matches = subset_matches.merge(t_name_map, on='trismegistos_id', how='left')
                subset_matches = subset_matches[['pleiades_id', 'trismegistos_id', 'pleiades_title', 'trismegistos_name', 'sources', 'n_sources']].drop_duplicates()
                match_rows.extend(subset_matches.to_dict('records'))

                unmatched_pleiades = p_df[~p_df['pleiades_id'].astype(str).isin(subset_matches['pleiades_id'].astype(str))]
                unmatched_trismegistos = t_df[~t_df['trismegistos_id'].astype(str).isin(subset_matches['trismegistos_id'].astype(str))]
                for record in unmatched_pleiades.to_dict('records'):
                    unmatched_rows.append({'dataset': 'Pleiades', 'language': p_lang, 'identifier': record['pleiades_id']})
                for record in unmatched_trismegistos.to_dict('records'):
                    unmatched_rows.append({'dataset': 'Trismegistos', 'language': t_lang, 'identifier': record['trismegistos_id']})

    pd.DataFrame(coverage_rows).to_csv(PROJECT / 'cross_matching' / 'results' / 'language_coverage.csv', index=False, encoding='utf-8')
    pd.DataFrame(results).to_csv(PROJECT / 'cross_matching' / 'results' / 'combination_results.csv', index=False, encoding='utf-8')
    pd.DataFrame(match_rows).to_csv(PROJECT / 'cross_matching' / 'results' / 'matched_records.csv', index=False, encoding='utf-8')
    pd.DataFrame(unmatched_rows).to_csv(PROJECT / 'cross_matching' / 'results' / 'unmatched_records.csv', index=False, encoding='utf-8')

    duplicate_rows = []
    for key in ['pleiades_id', 'trismegistos_id']:
        counts = em[key].value_counts()
        for value, count in counts[counts > 1].items():
            duplicate_rows.append({'key': key, 'identifier': value, 'count': int(count)})
    pd.DataFrame(duplicate_rows).to_csv(PROJECT / 'cross_matching' / 'results' / 'duplicate_matches.csv', index=False, encoding='utf-8')

    print('Wrote combination and matching reports to', PROJECT / 'cross_matching' / 'results')


if __name__ == '__main__':
    main()
