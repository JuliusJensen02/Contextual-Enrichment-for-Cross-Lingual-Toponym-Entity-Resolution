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

## Plot CHGIS and TGaz coordinates

From the project directory, create a map with CHGIS RAS points in blue and TGaz
GIS points in red:

```powershell
python scripts\plot_chgis_tgaz_map.py
```

By default, this creates the interactive OpenStreetMap-based
`datasets/chgis_ras/converted/chgis_tgaz_map.html`. Open the HTML file in a
browser with an internet connection to see the map tiles. Use the layer control
to show or hide either dataset, and click a point for its name and ID.

To create the previous static PNG instead, run
`python scripts\plot_chgis_tgaz_map.py --format png`. PNG output requires
Matplotlib and GeoPandas; `--no-borders` omits country outlines. Use
`--output PATH` to choose a different output file.
