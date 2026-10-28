"""Extend Shanghai surfaces with explicitly supplied neighboring Geofabrik PBFs.

Usage: .venv/bin/python scripts/extend_surfaces.py jiangsu [zhejiang]
Only complete, parent-confirmed local PBF files should be supplied. This performs
real multipolygon assembly with libosmium and never downloads network resources.
"""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys

import osmium
from build_surfaces import ATTRIBUTION, BBOX, LAND_GROUPS, intersects, points

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/raw/shanghai-surface-base'
KEYS = ('buildings', 'landuse', 'water')


def classifications(tags):
    result = []
    if tags.get('building') not in (None, 'no', 'demolished'):
        result.append(('buildings', 'building', 'building'))
    landuse, natural, leisure = (tags.get(k) for k in ('landuse', 'natural', 'leisure'))
    if landuse and landuse not in ('reservoir', 'basin'):
        result.append(('landuse', landuse, LAND_GROUPS.get(landuse, 'grass' if landuse == 'village_green' else 'other_land')))
    elif leisure in ('park', 'garden', 'recreation_ground', 'nature_reserve'):
        result.append(('landuse', leisure, 'park'))
    elif natural in ('wood', 'scrub', 'grassland', 'heath'):
        fclass = {'wood': 'forest', 'grassland': 'grass'}.get(natural, natural)
        result.append(('landuse', fclass, LAND_GROUPS[fclass]))
    if natural in ('water', 'wetland', 'glacier') or tags.get('waterway') == 'riverbank' or landuse in ('reservoir', 'basin'):
        if natural == 'wetland':
            fclass = 'wetland_' + tags['wetland'] if tags.get('wetland') else 'wetland'
        elif landuse == 'reservoir' or tags.get('water') == 'reservoir':
            fclass = 'reservoir'
        elif tags.get('waterway') == 'riverbank':
            fclass = 'riverbank'
        elif natural == 'glacier':
            fclass = 'glacier'
        else:
            fclass = 'water'
        result.append(('water', fclass, 'water'))
    elif tags.get('waterway') == 'dock':
        result.append(('water', 'dock', 'water'))
    return result


def normalize(geometry):
    """Keep all vertices and holes, imposing RFC 7946 winding."""
    polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
    for poly in polygons:
        for index, ring in enumerate(poly):
            if len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError('Invalid area ring')
            area = sum(a[0]*b[1] - b[0]*a[1] for a, b in zip(ring, ring[1:]))
            if (area > 0) != (index == 0):
                ring.reverse()
    return geometry


def fingerprint(geometry):
    def ring_key(ring):
        coords = [tuple(round(v, 7) for v in p[:2]) for p in ring[:-1]]
        minimum = min(coords)
        variants = []
        for sequence in (coords, list(reversed(coords))):
            for i, point in enumerate(sequence):
                if point == minimum:
                    variants.append(tuple(sequence[i:] + sequence[:i]))
        return min(variants)
    polys = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
    canonical = sorted((ring_key(p[0]), tuple(sorted(ring_key(r) for r in p[1:]))) for p in polys)
    return hashlib.sha256(repr(canonical).encode()).hexdigest()


class Areas(osmium.SimpleHandler):
    def __init__(self, region, handles):
        super().__init__()
        self.region, self.handles = region, handles
        self.factory = osmium.geom.GeoJSONFactory()
        self.counts = collections.Counter()
        self.errors = []

    def area(self, area):
        tags = dict(area.tags)
        classes = classifications(tags)
        if not classes:
            return
        # Iterate outer coordinates before materializing nested GeoJSON outside
        # the viewport. Envelope intersection also keeps surrounding polygons.
        left = bottom = float('inf')
        right = top = float('-inf')
        try:
            for ring in area.outer_rings():
                for node in ring:
                    x, y = node.lon, node.lat
                    left, bottom, right, top = min(left, x), min(bottom, y), max(right, x), max(top, y)
            if not intersects((left, bottom, right, top)):
                return
            geometry = normalize(json.loads(self.factory.create_multipolygon(area)))
        except (RuntimeError, ValueError) as error:
            self.errors.append({'osm_type': 'way' if area.from_way() else 'relation', 'osm_id': str(area.orig_id()), 'error': str(error)})
            return
        for layer, fclass, group in classes:
            props = {'group': group, 'fclass': fclass, 'osm_id': str(area.orig_id()),
                     'osm_type': 'way' if area.from_way() else 'relation', 'source_region': self.region}
            if tags.get('name:zh') or tags.get('name'):
                props['name'] = tags.get('name:zh') or tags['name']
            if layer == 'buildings':
                props['building_type'] = tags['building']
            props['source_tags'] = {k: tags[k] for k in ('building', 'landuse', 'leisure', 'natural', 'water', 'waterway', 'wetland') if k in tags}
            feature = {'type': 'Feature', 'properties': props, 'geometry': geometry}
            self.handles[layer].write(json.dumps(feature, ensure_ascii=False, separators=(',', ':')) + '\n')
            self.counts[layer] += 1


def extract_region(region):
    source = ROOT / f'data/raw/{region}-latest.osm.pbf'
    reader = osmium.io.Reader(str(source))
    timestamp = reader.header().get('osmosis_replication_timestamp')
    reader.close()
    handles = {k: gzip.open(ROOT / f'data/raw/{region}-{k}.jsonl.gz', 'wt', encoding='utf-8') for k in KEYS}
    handler = Areas(region, handles)
    try:
        handler.apply_file(str(source), locations=True, idx='flex_mem')
    finally:
        for handle in handles.values():
            handle.close()
    result = {'region': region, 'source': f'https://download.geofabrik.de/asia/china/{region}-latest.osm.pbf',
              'osmTimestamp': timestamp, 'sourceArchiveBytes': source.stat().st_size,
              'candidateFeatures': dict(handler.counts), 'geometryErrors': handler.errors}
    (ROOT / f'data/raw/{region}-surface-extraction.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print('extracted', json.dumps(result, ensure_ascii=False), flush=True)
    if handler.errors:
        raise RuntimeError(f'{region}: {len(handler.errors)} geometry errors; see extraction report')
    return result


def merge_layer(key, regions, original_stats):
    with gzip.open(BASE / f'{key}.geojson.gz', 'rt') as z:
        baseline = json.load(z)
    signatures = {(str(f['properties']['osm_id']), fingerprint(f['geometry'])) for f in baseline['features']}
    base_ids = {str(f['properties']['osm_id']) for f in baseline['features']}
    primitive_ids = set()
    stats = {'sourceTable': original_stats['sourceTable'], 'sourceFeatureCount': original_stats['sourceFeatureCount'],
             'shanghaiBaseFeatureCount': len(baseline['features']), 'featureCount': 0,
             'groups': collections.Counter(), 'classes': collections.Counter(), 'coordinateCount': 0,
             'polygonCount': 0, 'holeCount': 0, 'uncompressedBytes': 0,
             'regionalAdded': collections.Counter(), 'regionalDuplicateSkipped': collections.Counter(),
             'sameIdDifferentGeometryKept': collections.Counter()}
    out = ROOT / f'data/{key}.geojson.gz'
    with out.open('wb') as file, gzip.GzipFile(filename='', fileobj=file, mode='wb', mtime=0, compresslevel=9) as z:
        def write(text):
            encoded = text.encode('utf-8'); stats['uncompressedBytes'] += len(encoded); z.write(encoded)
        def add(feature):
            if stats['featureCount']:
                write(',')
            write(json.dumps(feature, ensure_ascii=False, separators=(',', ':')))
            stats['featureCount'] += 1
            props, geom = feature['properties'], feature['geometry']
            stats['groups'][props['group']] += 1; stats['classes'][props['fclass']] += 1
            stats['coordinateCount'] += sum(1 for _ in points(geom['coordinates']))
            polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
            stats['polygonCount'] += len(polys); stats['holeCount'] += sum(len(p) - 1 for p in polys)
        write(json.dumps({'type': 'FeatureCollection', 'name': f'Shanghai viewport {key}', 'attribution': ATTRIBUTION}, ensure_ascii=False)[:-1] + ',"features":[')
        for feature in baseline['features']:
            add(feature)
        del baseline
        for region in regions:
            with gzip.open(ROOT / f'data/raw/{region}-{key}.jsonl.gz', 'rt') as source:
                for line in source:
                    feature = json.loads(line); props = feature['properties']
                    identity = (props['osm_type'], props['osm_id'], props['fclass'])
                    signature = (props['osm_id'], fingerprint(feature['geometry']))
                    if identity in primitive_ids or signature in signatures:
                        stats['regionalDuplicateSkipped'][region] += 1
                        primitive_ids.add(identity)
                        continue
                    if props['osm_id'] in base_ids:
                        stats['sameIdDifferentGeometryKept'][region] += 1
                    primitive_ids.add(identity); signatures.add(signature)
                    stats['regionalAdded'][region] += 1
                    add(feature)
        write(']}')
    stats['compressedBytes'] = out.stat().st_size; stats['path'] = f'data/{out.name}'
    stats['sha256'] = hashlib.sha256(out.read_bytes()).hexdigest()
    stats['sourceLayerLastChange'] = original_stats['sourceLayerLastChange']
    print('merged', key, json.dumps(stats, ensure_ascii=False), flush=True)
    return stats


def main():
    regions = sys.argv[1:]
    if not regions or any(region not in ('jiangsu', 'zhejiang') for region in regions):
        raise SystemExit('Supply confirmed complete local regions: jiangsu [zhejiang]')
    BASE.mkdir(exist_ok=True)
    if not (BASE / 'surfaces-manifest.json').exists():
        shutil.copy2(ROOT / 'data/surfaces-manifest.json', BASE / 'surfaces-manifest.json')
        for key in KEYS:
            shutil.copy2(ROOT / f'data/{key}.geojson.gz', BASE / f'{key}.geojson.gz')
    original = json.loads((BASE / 'surfaces-manifest.json').read_text())
    sources = [extract_region(region) for region in regions]
    manifest = json.loads((ROOT / 'data/surfaces-manifest.json').read_text())
    for key in KEYS:
        manifest['layers'][key] = merge_layer(key, regions, original['layers'][key])
    manifest['surfaceCompressedBytes'] = sum(manifest['layers'][k]['compressedBytes'] for k in KEYS)
    manifest['landuseClassToGroup'] = {
        fclass: LAND_GROUPS.get(fclass, 'park' if fclass in ('garden', 'nature_reserve') else 'grass' if fclass == 'village_green' else 'other_land')
        for fclass in manifest['layers']['landuse']['classes']
    }
    manifest['regionalSources'] = sources
    manifest['surfaceSourceArchiveBytes'] = original['sourceArchiveBytes'] + sum(s['sourceArchiveBytes'] for s in sources)
    manifest['surfaceCoverage'] = 'Shanghai, Jiangsu, and Zhejiang source extracts filtered to the viewport bbox' if len(regions) == 2 else 'Shanghai and ' + ', '.join(regions) + ' source extracts filtered to viewport bbox'
    manifest['mergeStrategy'] = 'All original Shanghai features preserved. Neighbor area geometries assembled by libosmium with holes. Regional duplicates use (OSM primitive type, ID, class); comparisons against Shanghai GPKG require ID and canonical polygon geometry, because GPKG lacks primitive type. Canonicalization ignores ring direction/start and polygon order at OSM 1e-7 coordinate precision. Different-geometry ID collisions retained and counted.'
    manifest['limitations'] = [item for item in original['limitations'] if not item.startswith('Only features in the Geofabrik Shanghai')]
    manifest['limitations'].extend([
        'Neighboring PBF data improves coverage across administrative boundaries, but feature completeness depends on OpenStreetMap mapping; absence is not a claim of no real-world feature.',
        'Geofabrik free-layer classification and raw OSM tag classification differ. Regional additions retain source_tags and fclass; all Shanghai base classifications remain unchanged.',
    ])
    (ROOT / 'data/surfaces-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
