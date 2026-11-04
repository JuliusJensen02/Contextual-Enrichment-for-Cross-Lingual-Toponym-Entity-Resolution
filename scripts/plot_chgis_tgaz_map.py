#!/usr/bin/env python3
"""Plot CHGIS and TGaz coordinates on a Central Asia map."""
import argparse
import csv
import json
import math
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHGIS_FILE = ROOT / 'datasets' / 'chgis_ras' / 'converted' / 'ras_centralasia_gazetteer_Sheet1.tsv'
TGAZ_FILE = ROOT / 'datasets' / 'tgaz_csv' / 'gis_xx.csv'
BOUNDARIES_URL = (
    'https://naturalearth.s3.amazonaws.com/110m_cultural/'
    'ne_110m_admin_0_countries.zip'
)
OSM_ATTRIBUTION = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">'
    'OpenStreetMap contributors</a>'
)


def read_coordinates(
    path,
    delimiter,
    longitude_field,
    latitude_field,
    label,
    property_fields=(),
):
    features = []
    skipped = 0

    with path.open(encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(f'{path} is empty or has no header row')
        missing_fields = {
            longitude_field,
            latitude_field,
        }.difference(reader.fieldnames)
        if missing_fields:
            raise ValueError(
                f'{path} is missing coordinate columns: '
                f'{", ".join(sorted(missing_fields))}'
            )

        for row in reader:
            try:
                longitude = float(row[longitude_field])
                latitude = float(row[latitude_field])
            except (TypeError, ValueError):
                skipped += 1
                continue
            if (
                not math.isfinite(longitude)
                or not math.isfinite(latitude)
                or not -180 <= longitude <= 180
                or not -90 <= latitude <= 90
            ):
                skipped += 1
                continue
            properties = {
                name: row.get(field, '')
                for name, field in property_fields
            }
            features.append(
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [longitude, latitude],
                    },
                    'properties': properties,
                }
            )

    if not features:
        raise ValueError(f'No valid coordinates found in {path}')
    if skipped:
        print(f'{label}: skipped {skipped} rows without valid coordinates', file=sys.stderr)
    return features


def _safe_json(value):
    return (
        json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        .replace('<', '\\u003c')
        .replace('>', '\\u003e')
        .replace('&', '\\u0026')
        .replace('\u2028', '\\u2028')
        .replace('\u2029', '\\u2029')
    )


def write_interactive_map(output, chgis_features, tgaz_features):
    geojson = _safe_json(
        {
            'chgis': {
                'type': 'FeatureCollection',
                'features': chgis_features,
            },
            'tgaz': {
                'type': 'FeatureCollection',
                'features': tgaz_features,
            },
        }
    )
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CHGIS RAS and TGaz locations</title>
  <link rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
        crossorigin="">
  <style>
    html, body, #map { height: 100%; margin: 0; }
    .map-title {
      padding: 8px 12px;
      background: rgba(255, 255, 255, .94);
      border-radius: 4px;
      box-shadow: 0 1px 5px rgba(0, 0, 0, .35);
      font: 600 16px/1.3 sans-serif;
    }
    .place-popup { line-height: 1.5; overflow-wrap: anywhere; }
    .place-popup strong { font-size: 1.05em; }
  </style>
</head>
<body>
<div id="map" aria-label="Map of CHGIS RAS and TGaz locations"></div>
<script
  src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
  integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
  crossorigin=""></script>
<script>
const datasets = __GEOJSON__;
const map = L.map('map', {preferCanvas: true});
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '__OSM_ATTRIBUTION__'
}).addTo(map);

const chgis = L.geoJSON(datasets.chgis, {
  pointToLayer: (_, latlng) => L.circleMarker(latlng, {
    radius: 4, color: '#0645d8', fillColor: '#0645d8',
    fillOpacity: 0.78, weight: 1
  }),
  onEachFeature: (feature, layer) => addPlaceDetails(feature, layer, 'blue')
}).addTo(map);
const tgaz = L.geoJSON(datasets.tgaz, {
  pointToLayer: (_, latlng) => L.circleMarker(latlng, {
    radius: 4, color: '#dc2626', fillColor: '#dc2626',
    fillOpacity: 0.78, weight: 1
  }),
  onEachFeature: (feature, layer) => addPlaceDetails(feature, layer, 'red')
}).addTo(map);

function addPlaceDetails(feature, layer, color) {
  const properties = feature.properties;
  const name = properties.name || properties.alternate_name || 'Unnamed place';
  layer.bindTooltip(name);

  const content = document.createElement('div');
  content.className = 'place-popup';
  const title = document.createElement('strong');
  title.style.color = color;
  title.textContent = name;
  content.appendChild(title);
  for (const [label, value] of Object.entries(properties)) {
    if (!value || label === 'name' || label === 'alternate_name') continue;
    const line = document.createElement('div');
    line.textContent = label.replaceAll('_', ' ') + ': ' + value;
    content.appendChild(line);
  }
  const [longitude, latitude] = feature.geometry.coordinates;
  const coordinates = document.createElement('div');
  coordinates.textContent = 'Coordinates: ' + latitude + ', ' + longitude;
  content.appendChild(coordinates);
  layer.bindPopup(content);
}

L.control.layers(null, {
  'CHGIS RAS (blue)': chgis,
  'TGaz GIS (red)': tgaz
}, {collapsed: false}).addTo(map);
L.control.scale().addTo(map);
const titleControl = L.control({position: 'topright'});
titleControl.onAdd = function() {
  const title = L.DomUtil.create('div', 'map-title');
  title.textContent = 'CHGIS RAS + TGaz Gazetteer';
  return title;
};
titleControl.addTo(map);
map.fitBounds(chgis.getBounds().extend(tgaz.getBounds()).pad(0.04));
</script>
</body>
</html>
""".replace('__GEOJSON__', geojson).replace(
        '__OSM_ATTRIBUTION__', OSM_ATTRIBUTION
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding='utf-8')


def country_boundaries():
    import geopandas as gpd

    cache_root = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    cache_dir = cache_root / 'chgis_tgaz_map'
    cache_dir.mkdir(parents=True, exist_ok=True)
    archive_path = cache_dir / 'ne_110m_admin_0_countries.zip'
    if not archive_path.exists():
        print('Downloading Natural Earth country boundaries...', file=sys.stderr)
        request = urllib.request.Request(
            BOUNDARIES_URL,
            headers={'User-Agent': 'CHGIS-TGaz-map-script/1.0'},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            archive_path.write_bytes(response.read())

    return gpd.read_file(f'zip://{archive_path.as_posix()}')


def write_static_map(output, chgis_features, tgaz_features, no_borders):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 9), constrained_layout=True)
    ax.set_facecolor('#eaf3f8')
    if not no_borders:
        countries = country_boundaries()
        countries.plot(
            ax=ax,
            facecolor='#f4f1e8',
            edgecolor='#8a8a8a',
            linewidth=0.55,
            zorder=1,
        )

    for features, color, label, zorder in (
        (chgis_features, 'blue', 'CHGIS RAS', 2),
        (tgaz_features, 'red', 'TGaz GIS', 3),
    ):
        coordinates = [
            feature['geometry']['coordinates']
            for feature in features
        ]
        longitudes = [coordinate[0] for coordinate in coordinates]
        latitudes = [coordinate[1] for coordinate in coordinates]
        ax.scatter(
            longitudes,
            latitudes,
            color=color,
            s=13,
            alpha=0.62,
            linewidths=0,
            label=f'{label} ({len(coordinates):,})',
            zorder=zorder,
        )

    all_features = chgis_features + tgaz_features
    all_lon = [feature['geometry']['coordinates'][0] for feature in all_features]
    all_lat = [feature['geometry']['coordinates'][1] for feature in all_features]
    lon_margin = max((max(all_lon) - min(all_lon)) * 0.04, 0.5)
    lat_margin = max((max(all_lat) - min(all_lat)) * 0.04, 0.5)
    ax.set_xlim(min(all_lon) - lon_margin, max(all_lon) + lon_margin)
    ax.set_ylim(min(all_lat) - lat_margin, max(all_lat) + lat_margin)
    ax.set_aspect(1 / math.cos(math.radians(sum(ax.get_ylim()) / 2)))
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('CHGIS RAS and TGaz Gazetteer Locations')
    ax.grid(color='#777777', linestyle=':', linewidth=0.45, alpha=0.55)
    ax.legend(loc='best', framealpha=0.95)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--format',
        choices=('html', 'png'),
        default='html',
        help='interactive OpenStreetMap HTML or static PNG (default: html)',
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='output file (default: datasets/chgis_ras/converted/chgis_tgaz_map.html)',
    )
    parser.add_argument(
        '--no-borders',
        action='store_true',
        help='for --format png, plot without downloading country boundaries',
    )
    args = parser.parse_args()

    output = args.output or (
        ROOT
        / 'datasets'
        / 'chgis_ras'
        / 'converted'
        / f'chgis_tgaz_map.{args.format}'
    )
    chgis_features = read_coordinates(
        CHGIS_FILE,
        '\t',
        'LONG',
        'LAT',
        'CHGIS',
        (('name', 'NAME_ROM'), ('alternate_name', 'NAME_RUS'), ('MAPID', 'MAPID')),
    )
    tgaz_features = read_coordinates(
        TGAZ_FILE,
        ',',
        'x_coord',
        'y_coord',
        'TGaz',
        (
            ('name', 'name_py'),
            ('alternate_name', 'name_utf'),
            ('transliterated_name', 'name_utf_alt'),
            ('id', 'sys_id'),
        ),
    )

    if args.format == 'html':
        write_interactive_map(output, chgis_features, tgaz_features)
    else:
        write_static_map(output, chgis_features, tgaz_features, args.no_borders)

    print(
        f'Wrote map with {len(chgis_features):,} CHGIS and '
        f'{len(tgaz_features):,} TGaz points to {output.resolve()}'
    )


if __name__ == '__main__':
    main()
