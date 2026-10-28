"""Build offline aviation geometry from the saved Overpass XML, without simplification.

Run with .venv/bin/python scripts/build_aviation.py. Requires osmium.
The query and complete source XML live in data/raw/ for reproducibility.
"""
import collections
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET

import osmium

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
SOURCE = DATA / 'raw/aviation.osm'
KINDS = {'runway', 'taxiway', 'apron'}
DEFAULT_WIDTH = {'runway': 45, 'taxiway': 23}


def kind(tags):
    return tags.get('area:aeroway', tags.get('aeroway', ''))


def is_surface(tags):
    return tags.get('area:aeroway') in KINDS or tags.get('aeroway') == 'apron' or tags.get('area') == 'yes'


def width_meters(value):
    match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(m|metres?|meters?|ft|feet|\')?\s*', value or '')
    if not match:
        return None
    width = float(match[1]) * (.3048 if match[2] in ('ft', 'feet', "'") else 1)
    return width if 0 < width <= 300 else None


def in_ring(point, ring):
    x, y = point
    inside = False
    for (ax, ay), (bx, by) in zip(ring, ring[1:]):
        if min(ax, bx)-1e-10 <= x <= max(ax, bx)+1e-10 and min(ay, by)-1e-10 <= y <= max(ay, by)+1e-10:
            if abs((x-ax)*(by-ay)-(y-ay)*(bx-ax)) < 1e-14:
                return True
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            inside = not inside
    return inside


def mark_covered_lines(features):
    """Keep original centerlines but avoid painting them twice under mapped pavement."""
    surfaces = collections.defaultdict(list)
    for feature in features:
        if feature['geometry']['type'] == 'MultiPolygon':
            surfaces[feature['properties']['group']].extend(feature['geometry']['coordinates'])
    for feature in features:
        if feature['geometry']['type'] != 'LineString':
            continue
        coords = feature['geometry']['coordinates']
        samples = coords + [[(a[0]+b[0])/2, (a[1]+b[1])/2] for a, b in zip(coords, coords[1:])]
        for poly in surfaces[feature['properties']['group']]:
            if all(in_ring(p, poly[0]) and not any(in_ring(p, hole) for hole in poly[1:]) for p in samples):
                feature['properties']['covered_by_area'] = True
                break


class Aviation(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.features = []
        self.factory = osmium.geom.GeoJSONFactory()

    def add(self, entity, geometry, osm_type, osm_id):
        tags = dict(entity.tags)
        group = kind(tags)
        props = {'group': group, 'osm_type': osm_type, 'osm_id': str(osm_id),
                 'name': tags.get('name', ''), 'ref': tags.get('ref', ''),
                 'source_tags': tags}
        if geometry['type'] == 'LineString':
            width = width_meters(tags.get('width'))
            props['width_m'] = width or DEFAULT_WIDTH[group]
            props['width_source'] = 'osm' if width else 'display_default'
            latitude = sum(p[1] for p in geometry['coordinates']) / len(geometry['coordinates'])
            # MapLibre uses a 512 CSS pixel Mercator world at zoom zero.
            props['width_px_z0'] = props['width_m'] * 512 / (40075016.68557849 * math.cos(math.radians(latitude)))
        self.features.append({'type': 'Feature', 'properties': props, 'geometry': geometry})

    def way(self, way):
        if kind(way.tags) not in KINDS or is_surface(way.tags):
            return
        self.add(way, json.loads(self.factory.create_linestring(way)), 'way', way.id)

    def area(self, area):
        if kind(area.tags) not in KINDS:
            return
        if area.from_way() and not is_surface(area.tags):
            return
        self.add(area, json.loads(self.factory.create_multipolygon(area)),
                 'way' if area.from_way() else 'relation', area.orig_id())


def main():
    xml = ET.parse(SOURCE).getroot()
    remark = xml.find('remark')
    if remark is not None:
        raise ValueError('Overpass returned an incomplete response: ' + (remark.text or ''))
    timestamp = xml.find('meta').get('osm_base')
    handler = Aviation()
    handler.apply_file(str(SOURCE), locations=True, idx='flex_mem')
    features = sorted(handler.features, key=lambda f: (f['properties']['group'], f['properties']['osm_type'], int(f['properties']['osm_id'])))
    mark_covered_lines(features)
    if not features or not any(f['properties']['group'] == 'runway' for f in features):
        raise ValueError('No runway geometry found')
    identities = [(f['properties']['osm_type'], f['properties']['osm_id']) for f in features]
    assert len(set(identities)) == len(identities)
    encoded = json.dumps({'type': 'FeatureCollection', 'features': features}, ensure_ascii=False, separators=(',', ':')).encode()
    packed = gzip.compress(encoded, mtime=0)
    (DATA / 'aviation.geojson.gz').write_bytes(packed)
    manifest = {
        'source': 'https://overpass.private.coffee/api/interpreter', 'osmTimestamp': timestamp,
        'bbox': [120.6143053902, 30.77, 122.3330946098, 31.6885676823],
        'featureCount': len(features), 'groups': dict(collections.Counter(f['properties']['group'] for f in features)),
        'geometryTypes': dict(collections.Counter(f['geometry']['type'] for f in features)),
        'linesCoveredByAreas': sum(bool(f['properties'].get('covered_by_area')) for f in features),
        'compressedBytes': len(packed), 'sourceBytes': SOURCE.stat().st_size,
        'sourceSHA256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'attribution': '© OpenStreetMap contributors / ODbL 1.0',
        'widthDefaultsMeters': DEFAULT_WIDTH,
        'notes': ['Original polygons preserve holes. Linear features use tagged width where available; absent or invalid widths use display defaults, not surveyed dimensions.']
    }
    (DATA / 'aviation-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
