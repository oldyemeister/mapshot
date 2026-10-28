"""Extract locally cached Geofabrik Shanghai polygons and roads using stdlib only.

The source is an administrative Shanghai extract, not complete coverage of the
rectangular viewport. Bounding-box intersection selects whole source geometries;
the map/export viewport clips their display. No simplification is applied.
"""
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sqlite3
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BBOX = (120.6143053902, 30.77, 122.3330946098, 31.6885676823)
SOURCE = 'https://download.geofabrik.de/asia/china/shanghai-latest-free.gpkg.zip'
ATTRIBUTION = '© OpenStreetMap contributors, ODbL 1.0 https://www.openstreetmap.org/copyright; extract by Geofabrik'
LAND_GROUPS = {
    'park': 'park', 'recreation_ground': 'park',
    'forest': 'forest',
    'grass': 'grass', 'meadow': 'grass', 'heath': 'grass', 'scrub': 'grass',
    'residential': 'residential_land', 'industrial': 'industrial',
    'farmland': 'farmland', 'farmyard': 'farmland', 'orchard': 'farmland',
    'vineyard': 'farmland', 'allotments': 'farmland',
}


class WKBReader:
    """Parse OGC WKB and ISO/EWKB dimensional variants; return XY GeoJSON."""

    def __init__(self, blob, offset=0):
        self.blob = blob
        self.offset = offset

    def take(self, fmt):
        size = struct.calcsize(fmt)
        values = struct.unpack_from(fmt, self.blob, self.offset)
        self.offset += size
        return values

    def geometry(self):
        byte_order, = self.take('B')
        if byte_order not in (0, 1):
            raise ValueError('Invalid WKB byte order')
        endian = '<' if byte_order else '>'
        raw_type, = self.take(endian + 'I')
        has_z, has_m = bool(raw_type & 0x80000000), bool(raw_type & 0x40000000)
        if raw_type & 0x20000000:
            self.take(endian + 'I')  # EWKB embedded SRID
        kind = raw_type & 0x0fffffff
        dimension_variant, kind = divmod(kind, 1000)
        has_z |= dimension_variant in (1, 3)
        has_m |= dimension_variant in (2, 3)
        dims = 2 + int(has_z) + int(has_m)

        def count():
            return self.take(endian + 'I')[0]

        def point():
            coords = self.take(endian + 'd' * dims)[:2]
            if not all(math.isfinite(v) for v in coords):
                raise ValueError('Nonfinite coordinate')
            return list(coords)

        if kind == 1:
            return {'type': 'Point', 'coordinates': point()}
        if kind == 2:
            return {'type': 'LineString', 'coordinates': [point() for _ in range(count())]}
        if kind == 3:
            rings = []
            for index in range(count()):
                ring = [point() for _ in range(count())]
                if len(ring) < 4 or ring[0] != ring[-1]:
                    raise ValueError('Invalid/unclosed polygon ring')
                # RFC 7946: exterior counterclockwise, holes clockwise.
                area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
                if (area > 0) != (index == 0):
                    ring.reverse()
                rings.append(ring)
            return {'type': 'Polygon', 'coordinates': rings}
        if kind in (4, 5, 6, 7):
            children = [self.geometry() for _ in range(count())]
            if kind == 7:
                return {'type': 'GeometryCollection', 'geometries': children}
            child_type, geometry_type = {
                4: ('Point', 'MultiPoint'), 5: ('LineString', 'MultiLineString'),
                6: ('Polygon', 'MultiPolygon'),
            }[kind]
            if any(child['type'] != child_type for child in children):
                raise ValueError('Incorrect WKB child type')
            return {'type': geometry_type, 'coordinates': [c['coordinates'] for c in children]}
        raise ValueError(f'Unsupported WKB geometry {kind}')


def read_gpkg(blob):
    if blob[:3] != b'GP\x00':
        raise ValueError('Invalid GeoPackage header/version')
    flags = blob[3]
    if flags & 0x20:
        raise ValueError('Extended GeoPackage geometry is unsupported')
    endian = '<' if flags & 1 else '>'
    srs_id, = struct.unpack_from(endian + 'i', blob, 4)
    if srs_id not in (100000, 4326):
        raise ValueError(f'Unexpected coordinate system {srs_id}')
    envelope_id = (flags >> 1) & 7
    envelope_size = {0: 0, 1: 4, 2: 6, 3: 6, 4: 8}[envelope_id]
    envelope = struct.unpack_from(endian + 'd' * envelope_size, blob, 8) if envelope_size else None
    if flags & 0x10:
        return None
    if envelope and not intersects((envelope[0], envelope[2], envelope[1], envelope[3])):
        return None
    reader = WKBReader(blob, 8 + envelope_size * 8)
    geometry = reader.geometry()
    if reader.offset != len(blob):
        raise ValueError('Trailing bytes after WKB geometry')
    if not envelope:
        coords = list(points(geometry['coordinates']))
        if not coords or not intersects((min(p[0] for p in coords), min(p[1] for p in coords),
                                         max(p[0] for p in coords), max(p[1] for p in coords))):
            return None
    return geometry


def intersects(bounds):
    return bounds[2] >= BBOX[0] and bounds[0] <= BBOX[2] and bounds[3] >= BBOX[1] and bounds[1] <= BBOX[3]


def points(coords):
    if coords and isinstance(coords[0], (int, float)):
        yield coords
    else:
        for child in coords:
            yield from points(child)


def road_group(fclass):
    group = fclass.removesuffix('_link')
    if group == 'living_street':
        return 'residential'
    if group in ('footway', 'cycleway', 'path', 'pedestrian', 'steps', 'bridleway'):
        return 'path'
    if group.startswith('track'):
        return 'track'
    if group == 'unknown':
        return 'unclassified'
    return group


def extract(db, key, table):
    out = ROOT / 'data' / f'{key}.geojson.gz'
    stats = {'sourceTable': table, 'sourceFeatureCount': db.execute(f'SELECT count(*) FROM {table}').fetchone()[0],
             'featureCount': 0, 'groups': collections.Counter(), 'classes': collections.Counter(),
             'coordinateCount': 0, 'polygonCount': 0, 'holeCount': 0, 'uncompressedBytes': 0}
    extras = ', type' if key == 'buildings' else (', ref' if key == 'shanghai-roads' else '')
    with out.open('wb') as file, gzip.GzipFile(filename='', fileobj=file, mode='wb', mtime=0, compresslevel=9) as z:
        def write(value):
            data = value.encode('utf-8')
            stats['uncompressedBytes'] += len(data)
            z.write(data)

        head = {'type': 'FeatureCollection', 'name': f'Shanghai {key}', 'attribution': ATTRIBUTION}
        write(json.dumps(head, ensure_ascii=False, separators=(',', ':'))[:-1] + ',"features":[')
        for row in db.execute(f'SELECT geom, osm_id, fclass, name{extras} FROM {table} ORDER BY fid'):
            blob, osm_id, fclass, name, *extra = row
            if not blob:
                continue
            geometry = read_gpkg(blob)
            if geometry is None:
                continue
            group = ('building' if key == 'buildings' else 'water' if key == 'water'
                     else road_group(fclass) if key == 'shanghai-roads' else LAND_GROUPS.get(fclass, 'other_land'))
            properties = {'group': group, 'osm_id': osm_id, 'fclass': fclass}
            if name:
                properties['name'] = name
            if extra and extra[0]:
                properties['building_type' if key == 'buildings' else 'ref'] = extra[0]
            if key == 'shanghai-roads':
                properties['highway'] = fclass
            feature = {'type': 'Feature', 'properties': properties, 'geometry': geometry}
            if stats['featureCount']:
                write(',')
            write(json.dumps(feature, ensure_ascii=False, separators=(',', ':'), allow_nan=False))
            stats['featureCount'] += 1
            stats['groups'][group] += 1
            stats['classes'][fclass] += 1
            stats['coordinateCount'] += sum(1 for _ in points(geometry['coordinates']))
            polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']] if geometry['type'] == 'Polygon' else []
            stats['polygonCount'] += len(polygons)
            stats['holeCount'] += sum(max(0, len(poly) - 1) for poly in polygons)
        write(']}')
    stats['compressedBytes'] = out.stat().st_size
    stats['path'] = f'data/{out.name}'
    stats['sha256'] = hashlib.sha256(out.read_bytes()).hexdigest()
    stats['sourceLayerLastChange'] = db.execute('SELECT last_change FROM gpkg_contents WHERE table_name=?', (table,)).fetchone()[0]
    return stats


def main():
    archive = ROOT / 'data/raw/shanghai-latest-free.gpkg.zip'
    gpkg = ROOT / 'data/raw/shanghai.gpkg'
    with zipfile.ZipFile(archive) as z:
        readme = z.read('README').decode('utf-8')
        timestamp = re.search(r'data as of (\d{4}-\d{2}-\d{2}T[0-9:]+Z)', readme).group(1)
        member = next(n for n in z.namelist() if n.endswith('.gpkg'))
        # Re-extract to avoid accidentally mixing old and new cached snapshots.
        with z.open(member) as source, gpkg.open('wb') as target:
            shutil.copyfileobj(source, target)
        (ROOT / 'data/raw/shanghai-geofabrik-README.txt').write_text(readme)
    db = sqlite3.connect(f'file:{gpkg}?mode=ro', uri=True)
    definition = db.execute('SELECT definition FROM gpkg_spatial_ref_sys WHERE srs_id=100000').fetchone()[0]
    if 'CRS84' not in definition:
        raise ValueError('The source must use WGS84 longitude/latitude')
    layers = {}
    for key, table in [('buildings', 'gis_osm_buildings_a_free'), ('landuse', 'gis_osm_landuse_a_free'),
                       ('water', 'gis_osm_water_a_free'), ('shanghai-roads', 'gis_osm_roads_free')]:
        layers[key] = extract(db, key, table)
        print(key, json.dumps(layers[key], ensure_ascii=False), flush=True)
    db.close()
    manifest = {
        'bbox': list(BBOX), 'source': SOURCE, 'osmTimestamp': timestamp,
        'license': 'ODbL-1.0', 'attribution': ATTRIBUTION,
        'sourceArchiveBytes': archive.stat().st_size,
        'sourceArchiveSha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'sourceGeoPackageBytes': gpkg.stat().st_size,
        'sourceCrs': 'OGC:CRS84 (WGS84 longitude, latitude)',
        'layers': layers,
        'surfaceCompressedBytes': sum(layers[k]['compressedBytes'] for k in ('buildings', 'landuse', 'water')),
        'landuseClassToGroup': {k: LAND_GROUPS.get(k, 'other_land') for k in layers['landuse']['classes']},
        'limitations': [
            'Only features in the Geofabrik Shanghai administrative extract are available. The full viewport also includes areas outside Shanghai; these surface layers do not fill those areas.',
            'Whole features intersecting the requested bbox are retained; polygons are not clipped or simplified. The renderer must clip display to the viewport.',
            'OpenStreetMap is community mapped and does not guarantee complete building, park, land-use, or water coverage.',
            'Water group preserves every polygon class in the Geofabrik water layer, including wetlands and the source glacier classification; fclass records the original category.',
            'Geofabrik free layers provide selected tags only. Building type is available where mapped, but building height/floors are not included in this archive.',
            'Road unknown class is styled as unclassified; bridleways as paths; track grades as tracks. Original fclass is retained.',
        ],
    }
    (ROOT / 'data/surfaces-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
