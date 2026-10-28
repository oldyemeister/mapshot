"""Merge current Shanghai roads with adjoining provincial OSM ways, offline.

Requires the completed Geofabrik Shanghai GeoPackage extraction plus Jiangsu
and Zhejiang PBF downloads. Keeps full line detail and clips every segment to
the application's expanded rectangle. No downloads or main-manifest edits.
"""
import collections
import datetime
import gzip
import json
import sqlite3
from pathlib import Path

import osmium

from build_surfaces import read_gpkg, road_group

ROOT = Path(__file__).resolve().parents[1]
BBOX = (120.6143053902, 30.77, 122.3330946098, 31.6885676823)
GROUPS = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary',
          'residential', 'unclassified', 'service', 'path', 'track', 'waterway'}


def clip_segment(a, b):
    x, y = a
    dx, dy = b[0] - x, b[1] - y
    t0, t1 = 0, 1
    for p, q in [(-dx, x-BBOX[0]), (dx, BBOX[2]-x),
                 (-dy, y-BBOX[1]), (dy, BBOX[3]-y)]:
        if p == 0:
            if q < 0:
                return None
        else:
            r = q / p
            if p < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 > t1:
                return None
    # Keep source precision, and guard against a floating point boundary error.
    return [[min(BBOX[2], max(BBOX[0], x+t*dx)),
             min(BBOX[3], max(BBOX[1], y+t*dy))] for t in (t0, t1)]


def clip_line(coords):
    parts, current = [], []
    for a, b in zip(coords, coords[1:]):
        pair = clip_segment(a, b)
        if pair and pair[0] != pair[1]:
            if current and current[-1] == pair[0]:
                current.append(pair[1])
            else:
                if len(current) > 1:
                    parts.append(current)
                current = pair
        elif current:
            if len(current) > 1:
                parts.append(current)
            current = []
    if len(current) > 1:
        parts.append(current)
    return parts


def line_parts(geometry):
    if geometry['type'] == 'LineString':
        return [geometry['coordinates']]
    if geometry['type'] == 'MultiLineString':
        return geometry['coordinates']
    raise ValueError(f"Unexpected road geometry: {geometry['type']}")


def feature(properties, parts):
    geometry = {'type': 'LineString', 'coordinates': parts[0]} if len(parts) == 1 else {
        'type': 'MultiLineString', 'coordinates': parts}
    properties = dict(properties)
    properties['osm_id'] = str(properties['osm_id'])
    return {'type': 'Feature', 'properties': properties, 'geometry': geometry}


class RegionalWays(osmium.SimpleHandler):
    def __init__(self, features):
        super().__init__()
        self.features = features
        self.selected = collections.Counter()
        self.duplicates = 0

    def way(self, way):
        highway = way.tags.get('highway', '')
        waterway = way.tags.get('waterway', '')
        if not highway and not waterway:
            return
        group = road_group(highway) if highway else 'waterway'
        if group not in GROUPS:
            return
        coords = [[n.lon, n.lat] for n in way.nodes]
        parts = clip_line(coords)
        if not parts:
            return
        props = {'osm_id': str(way.id), 'group': group,
                 'highway': highway or waterway}
        name = way.tags.get('name:zh') or way.tags.get('name') or way.tags.get('ref')
        if name:
            props['name'] = name
        key = str(way.id)
        self.duplicates += key in self.features
        # PBF complete ways supersede a possibly split GeoPackage feature.
        self.features[key] = feature(props, parts)
        self.selected[group] += 1


def main():
    features = {}
    sources = []
    shanghai = ROOT / 'data/shanghai-roads.geojson.gz'
    with gzip.open(shanghai, 'rt') as source:
        for item in json.load(source)['features']:
            props = item['properties']
            if props['group'] not in GROUPS:
                continue
            parts = [p for line in line_parts(item['geometry']) for p in clip_line(line)]
            if not parts:
                continue
            key = str(props['osm_id'])
            if key in features:
                parts = line_parts(features[key]['geometry']) + parts
            features[key] = feature(props, parts)
    core_roads = len(features)
    db = sqlite3.connect(f"file:{ROOT / 'data/raw/shanghai.gpkg'}?mode=ro", uri=True)
    core_waterways = 0
    for blob, osm_id, fclass, name in db.execute(
            'SELECT geom, osm_id, fclass, name FROM gis_osm_waterways_free'):
        geometry = read_gpkg(blob)
        if geometry is None:
            continue
        parts = [p for line in line_parts(geometry) for p in clip_line(line)]
        if not parts:
            continue
        props = {'osm_id': str(osm_id), 'group': 'waterway', 'highway': fclass}
        if name:
            props['name'] = name
        key = str(osm_id)
        if key in features:
            parts = line_parts(features[key]['geometry']) + parts
        features[key] = feature(props, parts)
        core_waterways += 1
    db.close()
    surfaces = json.loads((ROOT / 'data/surfaces-manifest.json').read_text())
    sources.append({'name': 'Shanghai GeoPackage', 'path': 'data/raw/shanghai.gpkg',
                    'url': 'https://download.geofabrik.de/asia/china/shanghai-latest-free.gpkg.zip',
                    'osmTimestamp': surfaces.get('osmTimestamp'),
                    'selectedRoadCount': core_roads, 'selectedWaterwayCount': core_waterways})
    for province in ('jiangsu', 'zhejiang'):
        path = ROOT / f'data/raw/{province}-latest.osm.pbf'
        with osmium.io.Reader(str(path)) as reader:
            header = reader.header()
            timestamp = header.get('osmosis_replication_timestamp')
        handler = RegionalWays(features)
        print(f'Reading {province}: {path.stat().st_size:,} bytes', flush=True)
        handler.apply_file(str(path), locations=True, idx='flex_mem')
        sources.append({'name': f'{province.title()} PBF', 'path': str(path.relative_to(ROOT)),
                        'url': f'https://download.geofabrik.de/asia/china/{province}-latest.osm.pbf',
                        'osmTimestamp': timestamp, 'sourceBytes': path.stat().st_size,
                        'selectedGroups': dict(handler.selected), 'replacedDuplicateIDs': handler.duplicates})
        print(f'{province}: {sum(handler.selected.values()):,} selected ways', flush=True)
    ordered = [features[key] for key in sorted(features, key=int)]
    counts = collections.Counter(f['properties']['group'] for f in ordered)
    coordinate_count = 0
    coverage = collections.Counter()
    for item in ordered:
        for line in line_parts(item['geometry']):
            assert len(line) >= 2
            for x, y in line:
                assert BBOX[0] <= x <= BBOX[2] and BBOX[1] <= y <= BBOX[3]
                coordinate_count += 1
                if x < 121.1:
                    coverage['westOf121.1'] += 1
                if y < 30.9:
                    coverage['southOf30.9'] += 1
    result = {'type': 'FeatureCollection', 'name': 'Shanghai region roads and waterways',
              'attribution': '© OpenStreetMap contributors, ODbL 1.0 https://www.openstreetmap.org/copyright; extracts by Geofabrik',
              'features': ordered}
    encoded = json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    out = ROOT / 'data/roads.geojson.gz'
    temporary = out.with_suffix('.gz.tmp')
    with temporary.open('wb') as target, gzip.GzipFile(filename='', fileobj=target, mode='wb', mtime=0, compresslevel=9) as archive:
        archive.write(encoded)
    temporary.replace(out)
    manifest = {'bbox': list(BBOX), 'createdAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'path': str(out.relative_to(ROOT)), 'featureCount': len(ordered),
                'roadCount': len(ordered)-counts['waterway'], 'waterwayCount': counts['waterway'],
                'groups': dict(counts), 'coordinateCount': coordinate_count,
                'geometryBytes': out.stat().st_size, 'geometryUncompressedBytes': len(encoded),
                'sources': sources, 'license': 'ODbL-1.0',
                'validation': {'duplicateIDs': 0, 'allCoordinatesInsideBBox': True,
                               'coverageCoordinateCounts': dict(coverage)},
                'limitations': ['OSM completeness varies by location; extract boundaries follow provincial coverage.',
                                'Geofabrik Shanghai road classes are normalized; adjoining PBFs retain original highway values.']}
    (ROOT / 'data/roads-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
