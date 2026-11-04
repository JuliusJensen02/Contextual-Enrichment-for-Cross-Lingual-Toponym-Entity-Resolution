#!/usr/bin/env python3
"""Convert the CHGIS RAS spreadsheets and Access database to CSV or TSV.

ODS files are read with the standard library. Converting the MDB file requires
the mdb-tables and mdb-export commands from mdbtools to be on PATH.
"""
import argparse
import csv
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'datasets' / 'chgis_ras'
NS = {
    'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
}
CELL_TAGS = {
    f'{{{NS["table"]}}}table-cell',
    f'{{{NS["table"]}}}covered-table-cell',
}
VALUE_ATTRIBUTES = (
    'value',
    'date-value',
    'time-value',
    'boolean-value',
    'string-value',
)


def _text_content(element):
    if element.tag == f'{{{NS["text"]}}}s':
        return ' ' * int(element.get(f'{{{NS["text"]}}}c', '1'))
    if element.tag == f'{{{NS["text"]}}}tab':
        return '\t'
    if element.tag == f'{{{NS["text"]}}}line-break':
        return '\n'

    parts = [element.text or '']
    for child in element:
        parts.extend((_text_content(child), child.tail or ''))
    return ''.join(parts)


def _cell_value(cell):
    for attribute in VALUE_ATTRIBUTES:
        value = cell.get(f'{{{NS["office"]}}}{attribute}')
        if value is not None:
            return value

    paragraphs = cell.findall('text:p', NS)
    return '\n'.join(_text_content(paragraph) for paragraph in paragraphs)


def _repeat_count(element, attribute):
    return int(element.get(f'{{{NS["table"]}}}{attribute}', '1'))


def _ods_rows(sheet):
    pending_empty_rows = 0
    for row in sheet.findall('table:table-row', NS):
        values = []
        for cell in row:
            if cell.tag not in CELL_TAGS:
                continue
            value = _cell_value(cell)
            values.extend([value] * _repeat_count(cell, 'number-columns-repeated'))

        while values and values[-1] == '':
            values.pop()

        repeat_count = _repeat_count(row, 'number-rows-repeated')
        if not values:
            pending_empty_rows += repeat_count
            continue

        for _ in range(pending_empty_rows):
            yield []
        pending_empty_rows = 0
        for _ in range(repeat_count):
            yield values


def _safe_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .')
    return name or 'table'


def _output_path(out_dir, stem, extension, used):
    base = _safe_name(stem)
    candidate = out_dir / f'{base}.{extension}'
    suffix = 2
    while candidate.name.casefold() in used:
        candidate = out_dir / f'{base}_{suffix}.{extension}'
        suffix += 1
    used.add(candidate.name.casefold())
    return candidate


def _write_rows(path, rows, delimiter):
    with path.open('w', encoding='utf-8', newline='') as output:
        writer = csv.writer(output, delimiter=delimiter, lineterminator='\n')
        writer.writerows(rows)


def convert_ods(path, out_dir, extension, delimiter, used):
    with zipfile.ZipFile(path) as archive:
        content = ET.fromstring(archive.read('content.xml'))

    spreadsheet = content.find('office:body/office:spreadsheet', NS)
    if spreadsheet is None:
        raise ValueError(f'{path} does not contain a spreadsheet')

    sheets = spreadsheet.findall('table:table', NS)
    if not sheets:
        raise ValueError(f'{path} contains no sheets')

    outputs = []
    for index, sheet in enumerate(sheets, 1):
        sheet_name = sheet.get(f'{{{NS["table"]}}}name', f'Sheet{index}')
        output = _output_path(out_dir, f'{path.stem}_{sheet_name}', extension, used)
        _write_rows(output, _ods_rows(sheet), delimiter)
        outputs.append(output)
    return outputs


def _run_mdb_command(command, *args):
    result = subprocess.run(
        [command, *map(str, args)],
        check=False,
        capture_output=True,
        encoding='utf-8',
    )
    if result.returncode:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f'{command} failed ({result.returncode}): {details}')
    return result.stdout


def _convert_mdb_with_windows_odbc(path, out_dir, extension, delimiter, used, shell):
    script = r"""
param([string]$DatabasePath, [string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$connection = [System.Data.Odbc.OdbcConnection]::new(
    "Driver={Microsoft Access Driver (*.mdb, *.accdb)};Dbq=$DatabasePath;"
)
try {
    $connection.Open()
    $tables = @(
        $connection.GetSchema('Tables').Rows |
            Where-Object { $_['TABLE_TYPE'] -eq 'TABLE' } |
            ForEach-Object { [string]$_['TABLE_NAME'] }
    )
    for ($i = 0; $i -lt $tables.Count; $i++) {
        $tableName = $tables[$i]
        $escapedName = $tableName.Replace(']', ']]')
        $command = $connection.CreateCommand()
        $command.CommandText = "SELECT * FROM [$escapedName]"
        $adapter = [System.Data.Odbc.OdbcDataAdapter]::new($command)
        $data = [System.Data.DataTable]::new()
        [void]$adapter.Fill($data)

        $records = [System.Collections.Generic.List[object]]::new()
        $header = [ordered]@{}
        foreach ($column in $data.Columns) {
            $header[$column.ColumnName] = ''
        }
        $records.Add([pscustomobject]$header)

        foreach ($row in $data.Rows) {
            $record = [ordered]@{}
            foreach ($column in $data.Columns) {
                $value = $row[$column]
                if ($value -is [DBNull]) {
                    $record[$column.ColumnName] = ''
                } elseif ($value -is [IFormattable]) {
                    $record[$column.ColumnName] = $value.ToString(
                        $null, [Globalization.CultureInfo]::InvariantCulture
                    )
                } else {
                    $record[$column.ColumnName] = [string]$value
                }
            }
            $records.Add([pscustomobject]$record)
        }

        $csvPath = Join-Path $OutputDirectory "$i.csv"
        $records | ConvertTo-Csv -NoTypeInformation |
            Set-Content -LiteralPath $csvPath -Encoding UTF8
        $adapter.Dispose()
        $command.Dispose()
    }
    ConvertTo-Json -InputObject @($tables) -Compress
} finally {
    $connection.Dispose()
}
"""
    with tempfile.TemporaryDirectory(prefix='chgis_ras_') as temporary_dir:
        temporary_path = Path(temporary_dir)
        script_path = temporary_path / 'export_mdb.ps1'
        script_path.write_text(script, encoding='utf-8-sig')
        result = subprocess.run(
            [
                shell,
                '-NoProfile',
                '-NonInteractive',
                '-ExecutionPolicy',
                'Bypass',
                '-File',
                str(script_path),
                str(path.resolve()),
                str(temporary_path),
            ],
            check=False,
            capture_output=True,
            encoding='utf-8',
        )
        if result.returncode:
            details = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f'Windows Access ODBC export failed: {details}')

        try:
            table_names = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f'Windows Access ODBC returned invalid table metadata: {result.stdout!r}'
            ) from error
        if not table_names:
            raise ValueError(f'{path} contains no user tables')

        outputs = []
        for index, table_name in enumerate(table_names):
            output = _output_path(
                out_dir, f'{path.stem}_{table_name}', extension, used
            )
            with (temporary_path / f'{index}.csv').open(
                encoding='utf-8-sig', newline=''
            ) as source:
                _write_rows(output, csv.reader(source), delimiter)
            outputs.append(output)
        return outputs


def convert_mdb(path, out_dir, extension, delimiter, used):
    tables_command = shutil.which('mdb-tables')
    export_command = shutil.which('mdb-export')
    if not tables_command or not export_command:
        powershell = shutil.which('powershell') or shutil.which('pwsh')
        if powershell:
            return _convert_mdb_with_windows_odbc(
                path, out_dir, extension, delimiter, used, powershell
            )
        raise RuntimeError(
            f'{path.name} requires mdbtools (mdb-tables and mdb-export) or '
            'Windows PowerShell with the Microsoft Access ODBC driver'
        )

    table_names = _run_mdb_command(tables_command, '-1', path).splitlines()
    if not table_names:
        raise ValueError(f'{path} contains no tables')

    outputs = []
    for table_name in table_names:
        exported = _run_mdb_command(export_command, path, table_name)
        rows = csv.reader(io.StringIO(exported, newline=''))
        output = _output_path(
            out_dir, f'{path.stem}_{table_name}', extension, used
        )
        _write_rows(output, rows, delimiter)
        outputs.append(output)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        '--format',
        choices=('csv', 'tsv'),
        default='tsv',
        help='output format (default: tsv)',
    )
    parser.add_argument(
        '--out',
        type=Path,
        default=DATA_DIR / 'converted',
        help='output directory (default: datasets/chgis_ras/converted)',
    )
    args = parser.parse_args()

    inputs = sorted(
        [*DATA_DIR.glob('*.ods'), *DATA_DIR.glob('*.mdb')],
        key=lambda path: path.name.casefold(),
    )
    if not inputs:
        parser.error(f'no ODS or MDB files found in {DATA_DIR}')

    args.out.mkdir(parents=True, exist_ok=True)
    delimiter = ',' if args.format == 'csv' else '\t'
    used = set()
    failed = False

    for path in inputs:
        try:
            if path.suffix.casefold() == '.ods':
                outputs = convert_ods(path, args.out, args.format, delimiter, used)
            else:
                outputs = convert_mdb(path, args.out, args.format, delimiter, used)
            for output in outputs:
                print(f'Wrote {output}')
        except (OSError, UnicodeError, ValueError, RuntimeError, zipfile.BadZipFile, ET.ParseError) as error:
            print(f'Error converting {path.name}: {error}', file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
