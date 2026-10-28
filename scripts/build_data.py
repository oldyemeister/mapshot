"""Rebuild compact, clipped OSM geometry from the retained Overpass response."""
import collections, gzip, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BBOX=(120.6143053902,30.77,122.3330946098,31.6885676823)
def clip_segment(a,b):
    x,y=a; dx=b[0]-x;dy=b[1]-y;t0=0;t1=1
    for p,q in [(-dx,x-BBOX[0]),(dx,BBOX[2]-x),(-dy,y-BBOX[1]),(dy,BBOX[3]-y)]:
        if p==0:
            if q<0:return None
        else:
            r=q/p
            if p<0:t0=max(t0,r)
            else:t1=min(t1,r)
            if t0>t1:return None
    return [[round(x+t0*dx,6),round(y+t0*dy,6)],[round(x+t1*dx,6),round(y+t1*dy,6)]]
def clip_line(coords):
    parts=[];current=[]
    for a,b in zip(coords,coords[1:]):
        pair=clip_segment(a,b)
        if pair and pair[0]!=pair[1]:
            if current and current[-1]==pair[0]:current.append(pair[1])
            else:
                if len(current)>1:parts.append(current)
                current=pair
        elif current:
            if len(current)>1:parts.append(current)
            current=[]
    if len(current)>1:parts.append(current)
    return parts
raw=ROOT/'data/raw/roads-waterways.json'
data=json.loads(raw.read_text())
if data.get('remark'):raise RuntimeError(data['remark'])
extra_paths=[ROOT/f'data/raw/extra-{n}.json' for n in ['west','east','south','north','farwest','fareast']]
for path in extra_paths:
    extra=json.loads(path.read_text())
    if extra.get('remark'):raise RuntimeError(extra['remark'])
    data['elements'].extend(extra['elements'])
extra_bytes=sum(p.stat().st_size for p in extra_paths)
features=[];counts=collections.Counter();points=0;seen=set()
for e in data['elements']:
    if e['type']!='way' or e['id'] in seen:continue
    seen.add(e['id']);tags=e.get('tags',{});h=tags.get('highway','')
    group=h.removesuffix('_link')
    if group=='living_street':group='residential'
    if group in ('footway','path','cycleway','pedestrian','steps'):group='path'
    if not h:group='waterway'
    if group not in ('motorway','trunk','primary','secondary','tertiary','residential','unclassified','service','path','track','waterway'):continue
    parts=clip_line([[p['lon'],p['lat']] for p in e.get('geometry',[]) if p])
    if not parts:continue
    geometry={'type':'LineString','coordinates':parts[0]} if len(parts)==1 else {'type':'MultiLineString','coordinates':parts}
    p={'group':group,'osm_id':e['id'],'highway':h or tags.get('waterway')}
    name=tags.get('name:zh') or tags.get('name') or tags.get('ref')
    if name:p['name']=name
    features.append({'type':'Feature','properties':p,'geometry':geometry});counts[group]+=1;points+=sum(len(x) for x in parts)
result={'type':'FeatureCollection','name':'Shanghai roads and waterways','attribution':'© OpenStreetMap contributors, ODbL 1.0 https://www.openstreetmap.org/copyright','features':features}
encoded=json.dumps(result,ensure_ascii=False,separators=(',',':')).encode()
out=ROOT/'data/roads.geojson.gz'
with out.open('wb') as f:
    with gzip.GzipFile(fileobj=f,mode='wb',mtime=0,compresslevel=9) as z:z.write(encoded)
tile_bytes=sum(p.stat().st_size for p in (ROOT/'data/tiles').rglob('*.pbf'))
code_bytes=sum(p.stat().st_size for p in (ROOT/'vendor').iterdir())+sum((ROOT/p).stat().st_size for p in ('index.html','style.css','app.js'))
manifest={'bbox':list(BBOX),'center':[121.4737,31.2304],'osmTimestamp':data['osm3s']['timestamp_osm_base'],'rawBytes':raw.stat().st_size+extra_bytes,'geometryBytes':out.stat().st_size,'geometryUncompressedBytes':len(encoded),'tileBytes':tile_bytes,'codeBytes':code_bytes,'runtimeBytes':out.stat().st_size+tile_bytes+code_bytes,'roadCount':len(features)-counts['waterway'],'waterwayCount':counts['waterway'],'groups':dict(counts),'coordinateCount':points,'source':'https://overpass.kumi.systems/api/interpreter','waterSource':'OpenFreeMap 20261025_080012_pt (z7–11 cache)','license':'ODbL-1.0','downloadTransferBytes':raw.stat().st_size+extra_bytes}
(ROOT/'data/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps(manifest,ensure_ascii=False,indent=2))
