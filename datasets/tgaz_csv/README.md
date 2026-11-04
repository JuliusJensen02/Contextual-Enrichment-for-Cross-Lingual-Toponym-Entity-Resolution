# TGaz CSV files

This directory contains CSV exports and import/support tables for the TGaz place-name data. The descriptions below are based on each file's column names and the records present in this snapshot. Column names are kept as they appear in the files. Empty files contain a header but no data rows.

| File | Description | Columns |
|---|---|---|
| `admin_seat.csv` | Time-bounded relationship between a place and an administrative seat; this file is currently empty. | `id`, `placename_id`, `seat_id`, `begin_date`, `end_date`, `note` |
| `alt_name3.csv` | Alternate place-name records, including romanized and native-script names, feature types, dates, source IDs, and parent names. | `order_id`, `name_py`, `name_utf`, `name_utf_alt`, `type_py`, `type_utf`, `type_id`, `type_eng`, `beg_yr`, `end_yr`, `pgn_id`, `pt_id`, `line_id`, `data_src`, `parent_utf`, `parent_py` |
| `citation_ref.csv` | Citation/reference catalogue containing names, URLs, and explanatory notes. | `ref_handle`, `name`, `uri`, `note` |
| `ck1.csv` | Coordinate records keyed by `name_id`; currently empty. | `id`, `name_id`, `y`, `x` |
| `data_src.csv` | Catalogue of data sources, with organization, URL, and notes. | `id`, `name`, `org`, `uri`, `note` |
| `drule.csv` | Lookup table for rules used to interpret or assign date ranges. | `id`, `name`, `rule`, `ld_vocab`, `ld_uri` |
| `f2.csv` | Supplemental names linked to system IDs and coordinates, with an `auto_id`. | `name`, `sys_id`, `x_coord`, `y_coord`, `auto_id` |
| `ftype.csv` | Place-feature type catalogue, with names/transliterations, English labels, classification, source/citation, and metadata. | `id`, `name_vn`, `name_alt`, `name_tr`, `name_en`, `period`, `adl_class`, `cit_src`, `citation`, `note`, `ld_uri`, `added_on` |
| `ftype_xx.csv` | Additional feature-type entries, including language-specific names and status/creation metadata. | `order_id`, `lang`, `name_py`, `name_ch`, `id`, `name_en`, `name_alt`, `adl_class`, `period`, `cit_src`, `note`, `status`, `ts_added` |
| `geom.csv` | Geometry values associated with place records, with source and update timestamp; currently one record. | `id`, `placename_id`, `g`, `src`, `updated_on` |
| `gis_xx.csv` | GIS/import records with place names, coordinates, feature and date information, source attribution, and compilation details. | `order_id`, `name_py`, `name_utf`, `name_utf_alt`, `sys_id`, `xy_type`, `x_coord`, `y_coord`, `pres_loc`, `type_py`, `type_utf`, `lev_rank`, `beg_yr`, `beg_rule`, `beg_chg_type`, `end_yr`, `end_rule`, `end_chg_type`, `note_id`, `obj_type`, `geo_src`, `compiler`, `geocompiler`, `checker`, `filename`, `src` |
| `link.csv` | External links associated with place records, including link type, source, URI, and language; currently empty. | `id`, `placename_id`, `type`, `source`, `uri`, `lang` |
| `main_xx.csv` | Source-specific place records with names in multiple scripts, source IDs, dates, coordinates, feature types, notes, and source metadata. | `sys_id`, `nm_py`, `nm_simp`, `name_trad`, `orig_ID`, `beg_yr`, `end_yr`, `xy_type`, `x_coord`, `y_coord`, `pres_loc`, `type_py`, `type_utf`, `type_id`, `type_eng`, `lev_rank`, `note_id`, `nt_auto`, `obj_type`, `data_src`, `auto_id` |
| `mv_pn_srch.csv` | Place-name search export containing names/transcriptions, dates, coordinates, feature types, and parent-place details. | `id`, `sys_id`, `data_src`, `name`, `transcription`, `beg_yr`, `end_yr`, `obj_type`, `x_coord`, `y_coord`, `ftype_vn`, `ftype_tr`, `parent_id`, `parent_sys_id`, `parent_vn`, `parent_tr` |
| `mv_pn_srch_new_test.csv` | Test variant of the place-name search export. Its schema is like `mv_pn_srch.csv` but omits `obj_type`. | `id`, `sys_id`, `data_src`, `name`, `transcription`, `beg_yr`, `end_yr`, `x_coord`, `y_coord`, `ftype_vn`, `ftype_tr`, `parent_id`, `parent_sys_id`, `parent_vn`, `parent_tr` |
| `mv_pn_srch_old.csv` | Older variant of the place-name search export. It includes `counter_id` and does not include `obj_type`. | `id`, `sys_id`, `data_src`, `name`, `transcription`, `beg_yr`, `end_yr`, `x_coord`, `y_coord`, `ftype_vn`, `ftype_tr`, `parent_id`, `parent_sys_id`, `parent_vn`, `parent_tr`, `counter_id` |
| `part_of.csv` | Time-bounded parent/child relationships between place records. | `id`, `child_id`, `parent_id`, `begin_year`, `end_year` |
| `partof_xx.csv` | Source-specific/imported parent/child relationships with a year range. | `order_id`, `child_id`, `parent_id`, `beg_yr`, `end_yr` |
| `placename.csv` | Main place-record table: IDs, feature/source references, date rules, geometry/coordinates, rank, and default-parent information. | `id`, `sys_id`, `ftype_id`, `data_src`, `data_src_ref`, `snote_id`, `alt_of_id`, `lev_rank`, `beg_yr`, `beg_rule_id`, `end_yr`, `end_rule_id`, `obj_type`, `xy_type`, `x_coord`, `y_coord`, `geo_src`, `added_on`, `default_parent_id`, `parent_status` |
| `prec_by.csv` | Links place records to predecessor/precursor place IDs. | `id`, `placename_id`, `prec_id` |
| `precby_xx.csv` | Expanded predecessor/precursor records, including current and previous names, feature types, and object types. | `pby_id`, `pby_nmpy`, `pby_nmch`, `pby_nmft`, `pby_obj_type`, `pby_prev_id`, `pby_prev_nmpy`, `pby_prev_nmch`, `pby_prev_nmft`, `pby_uniq_id` |
| `present_loc.csv` | Present-day location descriptions associated with a place, including country code and provenance/attestation fields. | `id`, `placename_id`, `type`, `country_code`, `text_value`, `source`, `attestation`, `source_uri` |
| `script.csv` | Catalogue of writing systems/scripts, languages, dialects, and default-per-language settings. | `id`, `name`, `lang`, `dialect`, `default_per_lang`, `note` |
| `snote.csv` | Source notes and supporting text, with source/compiler, language, topic, URI, and date added. | `id`, `src_note_ref`, `source`, `compiler`, `lang`, `topic`, `uri`, `full_text`, `added_on` |
| `snote_xx.csv` | Source-specific notes with place-name variants, note text, source/compiler, and an automatic ID. | `nts_comp`, `nts_noteid`, `nts_nmpy`, `nts_nmch`, `nts_nmft`, `nts_fullnote`, `nts_autoid` |
| `spatial_system_ref.csv` | References to external spatial systems and location identifiers for places; currently empty. | `id`, `placename_id`, `system_name`, `level`, `location_uri`, `location_id` |
| `spelling.csv` | Written forms associated with place records, including script, exonym language, transcription system, attestation, and notes. | `id`, `placename_id`, `script_id`, `written_form`, `exonym_lang`, `trsys_id`, `default_per_type`, `attested_by`, `note` |
| `tbt_rev.csv` | Coordinate lookup keyed by `name_id`, with `y` and `x` values. | `id`, `name_id`, `y`, `x` |
| `temporal_annotation.csv` | Temporal annotations and supporting calendar, rule, equivalence, language, and attestation details; currently empty. | `id`, `placename_id`, `temporal_type`, `calendar_standard`, `rule_id`, `attested_by`, `equivalent`, `lang`, `note` |
| `trsys.csv` | Catalogue of transcription/romanization systems, their language and subtype, and notes. | `id`, `name`, `lang`, `lang_subtype`, `note` |
| `v5_id.csv` | Identifier mapping for the v5 export, with a flag and system ID. | `id`, `flag`, `sys_id` |
| `v6_id.csv` | Identifier mapping for the v6 export, with a flag and system ID. | `id`, `flag`, `sys_id` |
| `wkt_definition.csv` | Well-Known Text (WKT) geometry definitions associated with place records; currently empty. | `id`, `placename_id`, `object_type`, `object_text_value` |

## Notes

- Names such as `name_py`, `name_utf`, and `name_tr` indicate name/transcription variants; the precise convention can vary by source.
- Fields ending in `_id` generally refer to records in another table or to a source's own identifier. Empty values are common in optional fields.
- The `mv_pn_srch*` files are similarly sized search exports with different schemas; check the intended version before using one in an application.

## Building a combined place file

From the project directory, run:

```powershell
python build_master.py
```

This writes `tgaz_csv/placename_master.csv`, preserving one row per `placename.csv` record. The original place columns are retained; lookup names and source-note text are added, and repeated values (spellings, present locations, parent/child links, predecessors, and administrative seats) are encoded as JSON arrays in individual cells. Pass `--input-dir` or `--output` to use different paths. The script uses only the Python standard library.
