'use strict';
const CENTER=[121.4737,31.2304], LAKE=[121.9295,30.9025];
const BOUNDS=[[120.6143053902,30.77],[122.3330946098,31.6885676823]], STORAGE='shanghai-road-studio-v1';
const GROUPS=[
 ['motorway','高速公路',1.7],['trunk','快速路 / 干道',1.4],['primary','主干路',1.1],['secondary','次干路',.85],['tertiary','支路',.65],['residential','居住街道',.45],['unclassified','其他普通道路',.4],['service','内部 / 服务道路',.35],['path','步行 / 骑行小路',.3],['track','乡间小路',.3]
];
const PRESETS={
 atlas:{name:'清绘',base:['#f5f7f8','#bad8e7','#91bfd5','#739bb1'],roads:['#c26c42','#d39158','#c7a37c','#98a8a5','#8ca5b3','#b6c0c6','#aab9c3','#c4cbd0','#b1beb5','#b9bba4']},
 blueprint:{name:'蓝图',base:['#19364e','#102a3d','#306581','#3f7e9b'],roads:['#fff2ce','#e1d7af','#bed3df','#9dbbd0','#789fb9','#577e9c','#638ca6','#52768f','#557c85','#627e82']},
 ink:{name:'墨色',base:['#f7f7f5','#d9dedf','#c7cdce','#b2bbbf'],roads:['#27343e','#3d4b55','#53616a','#6c7880','#859097','#a8b0b4','#969fa4','#bdc3c6','#a5b2ad','#b6b8ae']},
 night:{name:'夜航',base:['#17212d','#20364a','#294b60','#385e70'],roads:['#efbd77','#d79b68','#b8b3a4','#8a9fae','#6a8295','#4b6174','#556d80','#3f5263','#46655f','#5a6655']}
};
const SURFACES=[['building','建筑轮廓',.6],['park','公园与休闲绿地',.7],['forest','树林',.65],['grass','草地与灌木',.6],['residential_land','住宅用地',.4],['industrial','工业用地',.4],['farmland','农田与果园',.4],['other_land','商业与其他用地',.35]];
const SURFACE_PALETTES={atlas:['#9daeb7','#afd0b4','#97bb9a','#c1d7b6','#e2e7e9','#d3d8df','#d8debb','#dfd9d1'],blueprint:['#40637a','#345c59','#2c504b','#3b625e','#214157','#32485e','#3e5149','#3d4c60'],ink:['#a6aeaf','#d0d8ce','#becbbd','#d7dfd1','#e5e8e5','#d9dcdf','#e0e3d4','#e2dfdb'],night:['#3d5061','#2b4942','#254037','#355249','#1e2b38','#303440','#3c4436','#35323e']};
const LIBRARY_THEME_NAMES={noir:'黑白',midnight_blue:'午夜蓝',japanese_ink:'日式墨绘',copper_patina:'铜绿',pastel_dream:'柔彩',terracotta:'陶土'};
function mixColor(a,b,t){const x=[1,3,5].map(i=>Math.round(parseInt(a.slice(i,i+2),16)*(1-t)+parseInt(b.slice(i,i+2),16)*t).toString(16).padStart(2,'0'));return '#'+x.join('');}
for(const [key,t] of Object.entries(window.MAPTOPOSTER_THEMES||{})){const k='mtp_'+key;PRESETS[k]={name:LIBRARY_THEME_NAMES[key]||t.name,originalName:t.name,source:'maptoposter',base:[t.bg,t.water,t.water,t.water],roads:[t.road_motorway,t.road_primary,t.road_primary,t.road_secondary,t.road_tertiary,t.road_residential,t.road_residential,t.road_default,t.road_default,t.road_default]};SURFACE_PALETTES[k]=[mixColor(t.bg,t.road_residential,.32),t.parks,t.parks,t.parks,mixColor(t.bg,t.parks,.5),mixColor(t.bg,t.road_tertiary,.12),t.parks,mixColor(t.bg,t.road_secondary,.08)];}
const AVIATION=[['runway','跑道',1],['taxiway','滑行道',1],['apron','停机坪',.85]];
const BASE=[['background','背景'],['water','江河与湖泊'],['ocean','海域'],['waterway','细小河道']];
const $=s=>document.querySelector(s);let map,manifest,ready=false,currentPreset='atlas',autoSave=true,noticeTimer,activeView='full';
let state=makePreset('atlas');
let loadFailed=false,loadTimer;
const loadController=new AbortController(),geometryURLs=[];
const loadMetrics={startedAt:performance.now(),geometryBytes:0,readyMs:null};
function makePreset(key){const p=PRESETS[key];return {version:3,preset:key,aviation:Object.fromEntries(AVIATION.map(([k,n,o],i)=>[k,{color:[p.roads[2],p.roads[4],mixColor(p.base[0],p.roads[3],.35)][i],visible:true,opacity:o}])),surfaces:Object.fromEntries(SURFACES.map(([k,n,o],i)=>[k,{color:SURFACE_PALETTES[key][i],visible:true,opacity:p.source&&['park','forest','grass','farmland'].includes(k)?1:o}])),detailWater:true,base:Object.fromEntries(BASE.map(([k],i)=>[k,p.base[i]])),roads:Object.fromEntries(GROUPS.map(([k,n,w],i)=>[k,{color:p.roads[i],width:w,visible:true}])),labels:false};}
function validateStyle(s){if(!s||![1,2,3].includes(s.version)||!s.base||!s.roads||typeof s.labels!=='boolean')throw Error('配色文件格式不正确');const clean=makePreset(Object.hasOwn(PRESETS,s.preset)?s.preset:'atlas');clean.preset=Object.hasOwn(PRESETS,s.preset)?s.preset:null;clean.labels=s.labels;const hex=x=>typeof x==='string'&&/^#[0-9a-f]{6}$/i.test(x);for(const [k] of BASE){if(!hex(s.base[k]))throw Error('配色文件包含无效颜色');clean.base[k]=s.base[k];}for(const [k] of GROUPS){const r=s.roads[k];if(!r||!hex(r.color)||typeof r.visible!=='boolean'||typeof r.width!=='number'||!Number.isFinite(r.width)||r.width<.1||r.width>5)throw Error('配色文件包含无效道路设置');clean.roads[k]={color:r.color,width:r.width,visible:r.visible};}if(s.version>=2){if(!s.surfaces||typeof s.detailWater!=='boolean')throw Error('图层设置不完整');clean.detailWater=s.detailWater;for(const [k] of SURFACES){const r=s.surfaces[k];if(!r||!hex(r.color)||typeof r.visible!=='boolean'||typeof r.opacity!=='number'||!Number.isFinite(r.opacity)||r.opacity<0||r.opacity>1)throw Error('建筑或土地用途设置无效');clean.surfaces[k]={color:r.color,visible:r.visible,opacity:r.opacity};}}if(s.version>=3){if(!s.aviation)throw Error('航空设施设置不完整');for(const [k] of AVIATION){const r=s.aviation[k];if(!r||!hex(r.color)||typeof r.visible!=='boolean'||typeof r.opacity!=='number'||!Number.isFinite(r.opacity)||r.opacity<0||r.opacity>1)throw Error('航空设施设置无效');clean.aviation[k]={color:r.color,visible:r.visible,opacity:r.opacity};}}return clean;}
try{const stored=localStorage.getItem(STORAGE);if(stored)state=validateStyle(JSON.parse(stored));}catch{autoSave=false;}
currentPreset=state.preset;
function notify(message){$('#notice').textContent=message;$('#notice').hidden=false;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>$('#notice').hidden=true,3600);}
function persist(){try{localStorage.setItem(STORAGE,JSON.stringify(state));autoSave=true;$('#save-status').textContent='已自动保存到此浏览器';}catch{autoSave=false;$('#save-status').textContent='浏览器无法保存，请使用“保存配色”';}}
function markCustom(){state.preset=null;currentPreset=null;syncPresets();}
function syncPresets(){document.querySelectorAll('.preset').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.preset===currentPreset)));const p=PRESETS[currentPreset];$('#theme-description').textContent=p?.source?`${p.originalName} · 原版道路、水域与公园配色；建筑、航空设施及其他用地为适配色。`:currentPreset?'选择预设后仍可逐层调色。':'自定义配色 · 可保存为 JSON 文件';}
function buildControls(){
 const presetButton=([k,p])=>`<button class="preset" data-preset="${k}" aria-label="使用${p.name}配色" aria-pressed="${k===currentPreset}" title="${p.originalName||p.name}"><div class="swatch">${[p.base[0],p.base[1],p.roads[0],p.roads[3]].map(c=>`<i style="background:${c}"></i>`).join('')}</div><span>${p.name}</span></button>`;
 $('#presets').innerHTML=Object.entries(PRESETS).filter(([k,p])=>!p.source).map(presetButton).join('');
 $('#library-presets').innerHTML=Object.entries(PRESETS).filter(([k,p])=>p.source).map(presetButton).join('');
 $('#base-controls').innerHTML=BASE.map(([k,n])=>`<div class="base-row"><label for="base-${k}">${n}</label><div class="color-pair"><input class="hex" id="hex-${k}" aria-label="${n}十六进制颜色" value="${state.base[k]}" pattern="#[0-9A-Fa-f]{6}" maxlength="7" spellcheck="false"><input id="base-${k}" type="color" aria-label="${n}颜色" value="${state.base[k]}"></div></div>`).join('');
 $('#surface-controls').innerHTML=SURFACES.map(([k,n])=>`<div class="surface-row"><input type="color" id="surface-color-${k}" aria-label="${n}颜色" value="${state.surfaces[k].color}"><label for="surface-show-${k}">${n}<input id="surface-show-${k}" type="checkbox" ${state.surfaces[k].visible?'checked':''}></label><input type="range" id="surface-opacity-${k}" min="0" max="1" step=".05" value="${state.surfaces[k].opacity}" aria-label="${n}不透明度" title="${n}不透明度"></div>`).join('');
 for(const [k] of SURFACES){$(`#surface-color-${k}`).oninput=e=>{state.surfaces[k].color=e.target.value;surfaceChanged(k);};$(`#surface-show-${k}`).onchange=e=>{state.surfaces[k].visible=e.target.checked;surfaceChanged(k);};$(`#surface-opacity-${k}`).oninput=e=>{state.surfaces[k].opacity=Number(e.target.value);surfaceChanged(k);};}
 $('#aviation-controls').innerHTML=AVIATION.map(([k,n])=>`<div class="surface-row"><input type="color" id="aviation-color-${k}" aria-label="${n}颜色" value="${state.aviation[k].color}"><label for="aviation-show-${k}">${n}<input id="aviation-show-${k}" type="checkbox" ${state.aviation[k].visible?'checked':''}></label><input type="range" id="aviation-opacity-${k}" min="0" max="1" step=".05" value="${state.aviation[k].opacity}" aria-label="${n}不透明度" title="${n}不透明度"></div>`).join('');
 for(const [k] of AVIATION){for(const [field,event,property] of [['color','input','color'],['show','change','visible'],['opacity','input','opacity']])$(`#aviation-${field}-${k}`).addEventListener(event,e=>{state.aviation[k][property]=field==='show'?e.target.checked:field==='opacity'?Number(e.target.value):e.target.value;markCustom();applyAviation(k);persist();});}
 $('#detail-water').checked=state.detailWater;
 $('#road-controls').innerHTML=GROUPS.map(([k,n])=>`<div class="road-row ${state.roads[k].visible?'':'off'}" data-road="${k}"><div class="road-row-top"><input type="color" id="color-${k}" aria-label="${n}颜色" value="${state.roads[k].color}"><label class="road-name" for="show-${k}"><span>${n}</span><input id="show-${k}" type="checkbox" ${state.roads[k].visible?'checked':''}></label></div><div class="road-range"><input type="range" id="width-${k}" aria-label="${n}线宽" min="0.1" max="5" step="0.05" value="${state.roads[k].width}"><output for="width-${k}" id="out-${k}">${state.roads[k].width.toFixed(2)}</output></div></div>`).join('');
 for(const [k] of BASE){$(`#base-${k}`).addEventListener('input',e=>{state.base[k]=e.target.value;$(`#hex-${k}`).value=e.target.value;markCustom();applyBase();persist();});$(`#hex-${k}`).addEventListener('change',e=>{if(!e.target.checkValidity()){e.target.reportValidity();return;}state.base[k]=e.target.value;$(`#base-${k}`).value=e.target.value;markCustom();applyBase();persist();});}
 for(const [k] of GROUPS){$(`#color-${k}`).addEventListener('input',e=>{state.roads[k].color=e.target.value;changed(k);});$(`#show-${k}`).addEventListener('change',e=>{state.roads[k].visible=e.target.checked;changed(k);});$(`#width-${k}`).addEventListener('input',e=>{state.roads[k].width=Number(e.target.value);changed(k);});}
 document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>{state=makePreset(b.dataset.preset);currentPreset=state.preset;buildControls();applyAll();persist();});$('#show-labels').checked=state.labels;updateToggle();syncPresets();
}
function changed(k){markCustom();$(`#out-${k}`).textContent=state.roads[k].width.toFixed(2);document.querySelector(`[data-road="${k}"]`).classList.toggle('off',!state.roads[k].visible);applyRoad(k);updateToggle();persist();}
function updateToggle(){$('#toggle-roads').textContent=GROUPS.some(([k])=>state.roads[k].visible)?'全部隐藏':'全部显示';}
function widthExpression(w){return ['interpolate',['exponential',1.4],['zoom'],8,w*.45,11,w,14,w*2.5,17,w*6];}
function applyRoad(k){if(!ready)return;map.setPaintProperty('road-'+k,'line-color',state.roads[k].color);map.setPaintProperty('road-'+k,'line-width',widthExpression(state.roads[k].width));map.setLayoutProperty('road-'+k,'visibility',state.roads[k].visible?'visible':'none');}
function surfaceChanged(k){markCustom();applySurface(k);persist();}
function applySurface(k){if(!ready)return;const r=state.surfaces[k];map.setPaintProperty('surface-'+k,'fill-color',r.color);map.setPaintProperty('surface-'+k,'fill-opacity',r.opacity);map.setLayoutProperty('surface-'+k,'visibility',r.visible?'visible':'none');if(k==='building'){map.setPaintProperty('building-outline','line-color',r.color);map.setPaintProperty('building-outline','line-opacity',r.opacity);map.setLayoutProperty('building-outline','visibility',r.visible?'visible':'none');}if(k==='grass'){map.setPaintProperty('wetland','fill-color',r.color);map.setPaintProperty('wetland','fill-opacity',r.opacity);map.setLayoutProperty('wetland','visibility',r.visible&&state.detailWater?'visible':'none');}}
function applyAviation(k){if(!ready)return;const r=state.aviation[k];for(const type of ['fill','line']){const id='aviation-'+k+'-'+type;map.setPaintProperty(id,type+'-color',r.color);map.setPaintProperty(id,type+'-opacity',r.opacity);map.setLayoutProperty(id,'visibility',r.visible?'visible':'none');}}
function aviationWidth(){const stops=[];for(let z=7;z<=17;z++)stops.push(z,['max',.55,['*',['get','width_px_z0'],2**z]]);return ['interpolate',['exponential',2],['zoom'],...stops];}
function applyBase(){if(!ready)return;map.setPaintProperty('background','background-color',state.base.background);map.setPaintProperty('water','fill-color',state.base.water);map.setPaintProperty('ocean','fill-color',state.base.ocean);map.setPaintProperty('waterway','line-color',state.base.waterway);map.setPaintProperty('detailed-water','fill-color',state.base.water);map.setLayoutProperty('water','visibility',state.detailWater?'none':'visible');map.setLayoutProperty('detailed-water','visibility',state.detailWater?'visible':'none');map.setLayoutProperty('wetland','visibility',state.detailWater&&state.surfaces.grass.visible?'visible':'none');}
const markers=[];
function applyLabels(){markers.forEach(m=>m.getElement().style.display=state.labels?'':'none');}
function applyAll(){applyBase();AVIATION.forEach(([k])=>applyAviation(k));SURFACES.forEach(([k])=>applySurface(k));GROUPS.forEach(([k])=>applyRoad(k));applyLabels();}
function resizeSheet(){if(exporting)return;const area=$('.paper-area'),sheet=$('.map-sheet');const css=getComputedStyle(area),sc=getComputedStyle(sheet);const horizontal=parseFloat(sc.paddingLeft)+parseFloat(sc.paddingRight);const vertical=94;const width=Math.max(180,Math.min(area.clientWidth-parseFloat(css.paddingLeft)-parseFloat(css.paddingRight),((area.clientHeight-parseFloat(css.paddingTop)-parseFloat(css.paddingBottom)-vertical)*1.6)+horizontal));sheet.style.width=(Math.floor((width-horizontal)/16)*16+horizontal)+'px';if(map){map.resize();if(activeView==='full')fullView(false);}}
function setView(key){activeView=key;for(const [k,id] of [['full','full-view'],['city','city-view'],['lake','lake-view']])$('#'+id).classList.toggle('selected',key===k);}
function fullView(animate=true){if(!map)return;setView('full');const cam=map.cameraForBounds(BOUNDS,{padding:0});map.easeTo({...cam,center:CENTER,bearing:0,pitch:0,duration:animate&&!matchMedia('(prefers-reduced-motion: reduce)').matches?450:0});}
function moveView(key,center,zoom){setView(key);map.easeTo({center,zoom,bearing:0,pitch:0,duration:matchMedia('(prefers-reduced-motion: reduce)').matches?0:550});}
function download(blob,name){const a=document.createElement('a'),u=URL.createObjectURL(blob);a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);}
function mb(bytes){return (bytes/1e6).toFixed(1)+' MB';}
function showManifest(m){$('#data-summary').textContent=`${m.roadCount.toLocaleString('zh-CN')} 段道路 · ${m.surfaceCounts.buildings.toLocaleString('zh-CN')} 个建筑 · 资源 ${mb(m.runtimeBytes)}`;$('#data-details').innerHTML=`<h3>数据与下载量</h3><table><tr><td>现用三个地区的源数据包</td><td>${mb(m.sourceArchiveBytes)}</td></tr><tr><td>本次累计下载（含早期提取）</td><td>${mb(m.downloadTransferBytes)}</td></tr><tr><td>离线道路 / 河道文件</td><td>${mb(m.geometryBytes)}</td></tr><tr><td>建筑、土地用途与精细水域</td><td>${mb(m.surfaceBytes)}</td></tr><tr><td>跑道、滑行道与停机坪</td><td>${mb(m.aviationBytes||0)}</td></tr><tr><td>复用的海域 / 基础水域缓存</td><td>${mb(m.tileBytes)}</td></tr><tr><td>地图组件与界面</td><td>${mb(m.codeBytes)}</td></tr><tr><td>离线运行资源合计</td><td>${mb(m.runtimeBytes)}</td></tr></table><p>16:10 视野：120.6143–122.3331°E，30.7700–31.6886°N，约 164 × 102 公里。人民广场居中，包含青浦西部及临港周边；宽屏两侧包含江苏、浙江部分地区。</p><p>OSM 快照：${m.osmTimestamp}。道路 ${m.roadCount.toLocaleString()} 段、河道 ${m.waterwayCount.toLocaleString()} 段；建筑 ${m.surfaceCounts.buildings.toLocaleString()} 个、土地用途 / 绿地 ${m.surfaceCounts.landuse.toLocaleString()} 个、水域 ${m.surfaceCounts.water.toLocaleString()} 个。</p><p>航空设施 ${m.aviationCount||0} 个，快照 ${m.aviationTimestamp||"未记录"}。面轮廓保持原样；中心线优先使用 OSM 宽度，无标注时跑道按 45 m、滑行道按 23 m 显示，远景保留最小可见线宽。默认宽度仅用于绘图。</p><p>建筑、绿地与内陆水域使用原始矢量轮廓，保留多边形孔洞。湿地按草地颜色绘制。OSM 记录可能不完整，图层没有覆盖的地方不代表现实中没有该要素。海域与海岸线仍使用 2026-10-25 的 z7–11 缓存；提升导出像素不会增加缺失地物或海岸线细节。</p><p>首次打开会读取地图数据；加载完成后调色在浏览器中进行。配色保存在当前浏览器，也可下载 JSON 备份。此前保留的原始 JSON 不再用于当前路网。1 MB = 1,000,000 字节。图片中无署名文字，来源保存在 PNG 元数据和随附说明中。</p><p><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap contributors / ODbL</a> · <a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> · <a href="https://download.geofabrik.de/asia/china/shanghai.html" target="_blank" rel="noopener">Geofabrik 数据来源</a></p>`;}

function releaseGeometryURLs(){geometryURLs.splice(0).forEach(url=>URL.revokeObjectURL(url));}
function showError(error){
 console.error(error);loadFailed=true;ready=false;clearTimeout(loadTimer);loadController.abort();releaseGeometryURLs();
 if(window.roadStudio)window.roadStudio.ready=false;
 $('#export-png').disabled=true;const box=$('#load-state');box.replaceChildren();
 const title=document.createElement('strong');title.textContent='地图暂时无法打开';
 const message=document.createElement('span');message.textContent=error.name==='AbortError'?'连接超时，请检查网络后重试。':error.message||'请检查网络后重试。';
 const button=document.createElement('button');button.textContent='重新加载';button.onclick=()=>location.reload();
 box.append(title,message,button);box.hidden=false;$('#data-summary').textContent='数据载入失败 · 配色仍保留在此浏览器';
}
async function start(){try{
 if(location.protocol==='file:')throw Error('请先运行启动脚本，再打开 http://127.0.0.1:8097');
 if(!window.maplibregl)throw Error('地图组件未能读取，请检查网络并重新加载。');
 if(!window.WebGL2RenderingContext)throw Error('此浏览器无法使用 WebGL 2，请更新浏览器并启用硬件加速。');
 if(!('DecompressionStream' in window))throw Error('请更新 Chrome、Edge、Firefox 或 Safari 后重试。');
 loadTimer=setTimeout(()=>showError(Error('地图加载超过三分钟，请检查网络后重新加载。')),180000);
 resizeSheet();const res=await fetch('data/manifest.json',{signal:loadController.signal});
 if(!res.ok)throw Error('地图清单读取失败，请稍后重试或联系网站提供者。');
 manifest=await res.json();showManifest(manifest);
 const totalBytes=manifest.geometryBytes+manifest.surfaceBytes+(manifest.aviationBytes||0);
 const updateProgress=()=>{if(loadFailed)return;$('#load-progress').value=Math.min(100,loadMetrics.geometryBytes/totalBytes*100);$('#load-message').textContent=`已读取 ${mb(loadMetrics.geometryBytes)} / 约 ${mb(totalBytes)}，随后绘制地图`;};
 updateProgress();
 const names={roads:'道路',buildings:'建筑',landuse:'绿地与土地用途',water:'水域',aviation:'机场设施'};
 const loadGeometry=async name=>{
  const response=await fetch(`data/${name}.geojson.gz`,{signal:loadController.signal});
  if(!response.ok)throw Error(`${names[name]}数据读取失败（${response.status}），请重新加载。`);
  const measured=response.body.pipeThrough(new TransformStream({transform(chunk,controller){loadMetrics.geometryBytes+=chunk.byteLength;updateProgress();controller.enqueue(chunk);}}));
  // Some static hosts apply HTTP gzip decoding themselves. Do not decode twice.
  const stream=response.headers.get('Content-Encoding')==='gzip'?measured:measured.pipeThrough(new DecompressionStream('gzip'));
  const blob=await new Response(stream).blob();
  if(loadFailed)throw new DOMException('Loading cancelled','AbortError');
  const url=URL.createObjectURL(new Blob([blob],{type:'application/json'}));geometryURLs.push(url);return url;
 };
 const [geometryURL,buildingURL,landuseURL,waterURL,aviationURL]=await Promise.all(['roads','buildings','landuse','water','aviation'].map(loadGeometry));
 $('#load-progress').removeAttribute('value');$('#load-title').textContent='正在绘制地图';$('#load-message').textContent='数据已读取，首次绘制需要一点时间';
 const layers=[{id:'background',type:'background',paint:{'background-color':state.base.background}},
 {id:'water',source:'water-tiles','source-layer':'water',type:'fill',filter:['!=',['get','class'],'ocean'],paint:{'fill-color':state.base.water}},
 {id:'ocean',source:'water-tiles','source-layer':'water',type:'fill',filter:['==',['get','class'],'ocean'],paint:{'fill-color':state.base.ocean}},
 {id:'waterway',source:'roads',type:'line',filter:['==',['get','group'],'waterway'],paint:{'line-color':state.base.waterway,'line-width':['interpolate',['linear'],['zoom'],8,.4,12,1,16,2.5]}}];
 // Water surfaces cover river centerlines, preventing artificial lines across broad water.
 layers.splice(1,0,layers.splice(3,1)[0]);
 layers.find(l=>l.id==='water').layout={visibility:state.detailWater?'none':'visible'};
 const landLayers=['other_land','residential_land','industrial','farmland','grass','forest','park'].map(k=>({id:'surface-'+k,type:'fill',source:'landuse',filter:['==',['get','group'],k],layout:{visibility:state.surfaces[k].visible?'visible':'none'},paint:{'fill-color':state.surfaces[k].color,'fill-opacity':state.surfaces[k].opacity}}));
 layers.splice(1,0,...landLayers);
 layers.push({id:'detailed-water',type:'fill',source:'detailed-water',filter:['in',['get','fclass'],['literal',['water','riverbank','reservoir','dock']]],layout:{visibility:state.detailWater?'visible':'none'},paint:{'fill-color':state.base.water}});
 layers.push({id:'wetland',type:'fill',source:'detailed-water',filter:['==',['slice',['coalesce',['get','fclass'],''],0,7],'wetland'],layout:{visibility:state.detailWater&&state.surfaces.grass.visible?'visible':'none'},paint:{'fill-color':state.surfaces.grass.color,'fill-opacity':state.surfaces.grass.opacity}});
 // Aviation pavement sits above land/water and below buildings and road access.
 for(const [k] of [...AVIATION].reverse())for(const type of ['fill','line'])layers.push({id:'aviation-'+k+'-'+type,type,source:'aviation',filter:['all',['==',['get','group'],k],['==',['geometry-type'],type==='fill'?'Polygon':'LineString'],...(type==='line'?[['!=',['get','covered_by_area'],true]]:[])],layout:{visibility:state.aviation[k].visible?'visible':'none',...(type==='line'?{'line-cap':'butt','line-join':'round'}:{})},paint:{[type+'-color']:state.aviation[k].color,[type+'-opacity']:state.aviation[k].opacity,...(type==='line'?{'line-width':aviationWidth()}:{})}});
 layers.push({id:'surface-building',type:'fill',source:'buildings',layout:{visibility:state.surfaces.building.visible?'visible':'none'},paint:{'fill-color':state.surfaces.building.color,'fill-opacity':state.surfaces.building.opacity}});
 layers.push({id:'building-outline',type:'line',source:'buildings',minzoom:12,layout:{visibility:state.surfaces.building.visible?'visible':'none'},paint:{'line-color':state.surfaces.building.color,'line-opacity':state.surfaces.building.opacity,'line-width':['interpolate',['linear'],['zoom'],12,.3,16,.7]}});
 for(const [k] of [...GROUPS].reverse())layers.push({id:'road-'+k,type:'line',source:'roads',filter:['==',['get','group'],k],layout:{'line-cap':'round','line-join':'round',visibility:state.roads[k].visible?'visible':'none'},paint:{'line-color':state.roads[k].color,'line-width':widthExpression(state.roads[k].width)}});
 map=new maplibregl.Map({container:'map',style:{version:8,sources:{aviation:{type:'geojson',data:aviationURL,tolerance:.05,maxzoom:18},'water-tiles':{type:'vector',tiles:[new URL('data/tiles/{z}/{x}/{y}.pbf',location.href).href.replaceAll('%7B','{').replaceAll('%7D','}')],minzoom:7,maxzoom:11,bounds:[120.60,30.48,122.35,32.02],attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap contributors</a> · OpenFreeMap'},buildings:{type:'geojson',data:buildingURL,tolerance:.1,maxzoom:16},landuse:{type:'geojson',data:landuseURL,tolerance:.1,maxzoom:16},'detailed-water':{type:'geojson',data:waterURL,tolerance:.08,maxzoom:16},roads:{type:'geojson',data:geometryURL,tolerance:.15,maxzoom:16}},layers},center:CENTER,zoom:9,minZoom:7,maxZoom:17,maxBounds:BOUNDS,dragRotate:false,pitchWithRotate:false,renderWorldCopies:false,maxCanvasSize:[8192,8192],canvasContextAttributes:{preserveDrawingBuffer:true},attributionControl:false});
 map.touchZoomRotate.disableRotation();map.addControl(new maplibregl.AttributionControl({compact:false}),'bottom-right');map.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-right');map.addControl(new maplibregl.ScaleControl({maxWidth:80,unit:'metric'}),'bottom-left');fullView(false);
 for(const [point,label,cls,anchor] of [[CENTER,'人民广场','','left'],[LAKE,'滴水湖','lake','right']]){const el=document.createElement('div');el.className='marker '+cls;el.textContent=label;markers.push(new maplibregl.Marker({element:el,anchor}).setLngLat(point).addTo(map));}applyLabels();
 map.on('dragstart',()=>setView('custom'));map.on('zoomstart',e=>{if(e.originalEvent)setView('custom');});map.on('moveend',()=>{$('#map-scale-text').textContent=`WGS 84 · z${map.getZoom().toFixed(1)}`;});
 map.on('load',()=>{if(loadFailed)return;ready=true;applyAll();releaseGeometryURLs();});map.once('idle',()=>{if(loadFailed)return;clearTimeout(loadTimer);ready=true;$('#load-state').hidden=true;$('#export-png').disabled=false;window.roadStudio.ready=true;loadMetrics.readyMs=Math.round(performance.now()-loadMetrics.startedAt);});
 map.on('error',e=>{if(e.error&&/fetch|404|load|AJAX/i.test(e.error.message)){if(!window.roadStudio?.ready){if(!loadFailed)showError(Error('部分地图数据读取失败，请检查网络并重新加载。'));}else notify('部分地图数据未能读取，请检查网络后重试。');}});
 map.on('click',e=>{const f=map.queryRenderedFeatures(e.point,{layers:[...AVIATION.flatMap(([k])=>['aviation-'+k+'-fill','aviation-'+k+'-line']),...GROUPS.map(([k])=>'road-'+k)]})[0];if(!f)return;const p=f.properties,wrap=document.createElement('div'),name=document.createElement('strong'),desc=document.createElement('p'),a=document.createElement('a');name.textContent=p.name||p.ref||(AVIATION.some(([k])=>k===p.group)?'航空设施':'未命名道路');desc.textContent=AVIATION.some(([k])=>k===p.group)?(AVIATION.find(([k])=>k===p.group)[1]+' · aeroway='+p.group+(p.width_m?' · '+p.width_m+' m'+(p.width_source==='display_default'?'（显示默认宽度）':''):'')):(GROUPS.find(([k])=>k===p.group)?.[1]||p.group)+' · '+p.highway;a.href='https://www.openstreetmap.org/'+(p.osm_type==='relation'?'relation':'way')+'/'+encodeURIComponent(p.osm_id);a.textContent='查看 OSM 原始记录（需联网）';a.target='_blank';a.rel='noopener';wrap.append(name,desc,a);new maplibregl.Popup({maxWidth:'260px'}).setLngLat(e.lngLat).setDOMContent(wrap).addTo(map);});
 window.roadStudio={map,ready:false,metrics:loadMetrics,getState:()=>structuredClone(state),validateStyle,fullView};
 }catch(e){if(!loadFailed)showError(e);}}
$('#reset-style').onclick=()=>{state=makePreset('atlas');currentPreset='atlas';buildControls();applyAll();persist();notify('已恢复清绘配色');};
$('#toggle-roads').onclick=()=>{const visible=!GROUPS.some(([k])=>state.roads[k].visible);GROUPS.forEach(([k])=>{state.roads[k].visible=visible;applyRoad(k);});markCustom();buildControls();persist();};
$('#detail-water').onchange=e=>{state.detailWater=e.target.checked;markCustom();applyBase();persist();};
$('#show-labels').onchange=e=>{state.labels=e.target.checked;applyLabels();persist();};
$('#full-view').onclick=()=>fullView();$('#city-view').onclick=()=>map&&moveView('city',CENTER,13.4);$('#lake-view').onclick=()=>map&&moveView('lake',LAKE,13.4);
$('#save-style').onclick=()=>{download(new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),'上海路网配色.json');notify('配色文件已导出');};$('#load-style').onclick=()=>$('#style-file').click();
$('#style-file').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>50000)throw Error('配色文件过大，请选择导出的 JSON 文件');state=validateStyle(JSON.parse(await file.text()));currentPreset=state.preset;buildControls();applyAll();persist();notify('已载入配色');}catch(error){notify(error.message||'配色文件无效');}finally{e.target.value='';}};
$('#data-toggle').onclick=()=>{const el=$('#data-details');el.hidden=!el.hidden;$('#data-toggle').setAttribute('aria-expanded',String(!el.hidden));};
function waitForMapIdle(timeout=60000){
 return new Promise((resolve,reject)=>{const done=()=>{clearTimeout(timer);map.off('error',failed);resolve();};const failed=e=>{if(e.error){clearTimeout(timer);map.off('idle',done);map.off('error',failed);reject(e.error);}};const timer=setTimeout(()=>{map.off('idle',done);map.off('error',failed);reject(Error('渲染超时，请降低分辨率后重试'));},timeout);map.once('idle',done);map.on('error',failed);map.triggerRepaint();});
}
function crc32(bytes){let crc=0xffffffff;for(const b of bytes){crc^=b;for(let k=0;k<8;k++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}return (crc^0xffffffff)>>>0;}
async function addPNGMetadata(blob,info){
 const bytes=new Uint8Array(await blob.arrayBuffer()),encoder=new TextEncoder();
 const chunks=Object.entries(info).map(([key,value])=>{const payload=encoder.encode(key+'\0'+value),type=encoder.encode('tEXt'),chunk=new Uint8Array(payload.length+12),v=new DataView(chunk.buffer);v.setUint32(0,payload.length);chunk.set(type,4);chunk.set(payload,8);v.setUint32(chunk.length-4,crc32(chunk.subarray(4,chunk.length-4)));return chunk;});
 return new Blob([bytes.subarray(0,bytes.length-12),...chunks,bytes.subarray(bytes.length-12)],{type:'image/png'});
}
let exporting=false;
$('#export-png').onclick=async()=>{
 if(!ready||exporting)return;
 const button=$('#export-png'),select=$('#export-size'),width=Number(select.value),height=width*10/16,oldRatio=map.getPixelRatio(),oldHTML=button.innerHTML,container=map.getContainer(),cssWidth=container.clientWidth,cssHeight=container.clientHeight;
 const original={center:map.getCenter(),zoom:map.getZoom(),bearing:map.getBearing(),pitch:map.getPitch()},bounds=map.getBounds().toArray(),originalBounds=map.getMaxBounds(),oldWidth=container.style.width,oldHeight=container.style.height;
 exporting=true;button.disabled=true;select.disabled=true;$('main').inert=true;button.textContent='正在渲染…';
 const loadBox=$('#load-state'),savedLoadHTML=loadBox.innerHTML;loadBox.innerHTML='<strong>正在生成壁纸</strong><span>按目标像素重新渲染，请稍候</span>';loadBox.hidden=false;
 try{
  map.stop();const canvas=map.getCanvas(),gl=canvas.getContext('webgl2')||canvas.getContext('webgl');const safeSize=Math.min(4096,gl.getParameter(gl.MAX_TEXTURE_SIZE),gl.getParameter(gl.MAX_RENDERBUFFER_SIZE));
  const parts=Math.ceil(Math.max(width,height)/safeSize),tileWidth=width/parts,tileHeight=height/parts,ratio=width/cssWidth;
  const centers=[];for(let row=0;row<parts;row++)for(let col=0;col<parts;col++)centers.push(map.unproject([cssWidth*(col+.5)/parts,cssHeight*(row+.5)/parts]));
  const output=document.createElement('canvas');output.width=width;output.height=height;const ctx=output.getContext('2d');if(!ctx)throw Error('无法分配图片内存，请降低分辨率');
  map.setMaxBounds(null);container.style.width=cssWidth/parts+'px';container.style.height=cssHeight/parts+'px';map.resize();map.setPixelRatio(ratio);
  for(let row=0;row<parts;row++)for(let col=0;col<parts;col++){
   const n=row*parts+col;button.textContent=parts>1?`渲染 ${n+1}/${parts*parts}`:'正在渲染…';
   const idle=waitForMapIdle(90000);map.jumpTo({...original,center:centers[n]});await idle;
   if(canvas.width!==tileWidth||canvas.height!==tileHeight)throw Error('浏览器限制了输出尺寸，请选择较低分辨率');
   ctx.drawImage(canvas,col*tileWidth,row*tileHeight);
  }
  button.textContent='正在保存…';const blob=await new Promise(resolve=>output.toBlob(resolve,'image/png'));if(!blob)throw Error('PNG 编码失败，请降低分辨率后重试');
  const result=await addPNGMetadata(blob,{Copyright:'Map data (c) OpenStreetMap contributors, ODbL 1.0; https://www.openstreetmap.org/copyright; Geofabrik; water tiles: OpenFreeMap',Description:JSON.stringify({osmTimestamp:manifest.osmTimestamp,aviationTimestamp:manifest.aviationTimestamp,bounds,width,height,tiles:parts*parts,rendering:'native vector render; no labels, markers, border or padding'})});
  download(result,`上海路网-${width}x${height}.png`);notify(`已导出 ${width} × ${height} 纯地图 PNG`);
 }catch(error){notify(error.message||'导出失败，请降低分辨率后重试');}
 finally{map.setPixelRatio(oldRatio);container.style.width=oldWidth;container.style.height=oldHeight;map.resize();map.setMaxBounds(originalBounds);map.jumpTo(original);loadBox.innerHTML=savedLoadHTML;loadBox.hidden=true;button.innerHTML=oldHTML;button.disabled=false;select.disabled=false;$('main').inert=false;exporting=false;}
};

if(matchMedia('(max-width: 700px)').matches)$('#export-size').value='1920';
buildControls();if(!autoSave)$('#save-status').textContent='本地配色未能读取，已使用默认配色';new ResizeObserver(resizeSheet).observe($('.paper-area'));start();
