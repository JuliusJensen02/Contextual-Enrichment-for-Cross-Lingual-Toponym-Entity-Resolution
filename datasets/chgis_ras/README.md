# CHGIS RAS data

Convert the ODS spreadsheets and Microsoft Access database to delimited text:

```powershell
python scripts\convert_chgis_ras.py
```

By default this writes TSV files to `datasets/chgis_ras/converted`, with one
file per spreadsheet sheet or database table. Choose CSV instead with
`--format csv`, or set another output directory with `--out PATH`.

ODS conversion uses only Python's standard library. The MDB is exported with
`mdb-tables` and `mdb-export` from mdbtools when available. On Windows, the
script can instead use Windows PowerShell and the Microsoft Access ODBC driver
(often installed with Microsoft Office or Access Database Engine).
