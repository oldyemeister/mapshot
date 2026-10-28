import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'data'
r=json.loads((D/'roads-manifest.json').read_text());s=json.loads((D/'surfaces-manifest.json').read_text())
print('roads manifest keys:',list(r))
m=json.loads((D/'manifest.json').read_text())
m.update({'bbox':r['bbox'],'osmTimestamp':'2026-10-27T21:23:59Z','roadCount':r['roadCount'],'waterwayCount':r['waterwayCount'],'coordinateCount':r['coordinateCount'],'geometryBytes':(D/'roads.geojson.gz').stat().st_size,'geometryUncompressedBytes':95523511,'surfaceBytes':sum((D/f'{n}.geojson.gz').stat().st_size for n in ['buildings','landuse','water']),'surfaceCounts':{n:s['layers'][n]['featureCount'] for n in ['buildings','landuse','water']},'source':'Geofabrik Shanghai GeoPackage + Jiangsu / Zhejiang OSM PBF','sourceArchiveBytes':220108426,'historicalOverpassBytes':149553811,'downloadTransferBytes':369662237,'rawBytes':369662237,'waterSource':'Detailed OSM inland polygons 2026-10-27; OpenFreeMap 2026-10-25 ocean/coast baseline','groups':r.get('groups',{})})
m['tileBytes']=sum(p.stat().st_size for p in (D/'tiles').rglob('*.pbf'))
m['codeBytes']=sum(p.stat().st_size for p in (R/'vendor').rglob('*') if p.is_file())+sum((R/p).stat().st_size for p in ('index.html','style.css','app.js'))
a=json.loads((D/'aviation-manifest.json').read_text())
m.update({'aviationBytes':(D/'aviation.geojson.gz').stat().st_size,'aviationCount':a['featureCount'],'aviationTimestamp':a['osmTimestamp'],'aviationDownloadBytes':a['sourceBytes']})
m['downloadTransferBytes']+=a['sourceBytes']
m['rawBytes']+=a['sourceBytes']
m['runtimeBytes']=m['geometryBytes']+m['surfaceBytes']+m['tileBytes']+m['codeBytes']+m['aviationBytes']
(D/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
print(json.dumps(m,ensure_ascii=False,indent=2))
