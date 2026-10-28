// Optional developer check: npm install --no-save playwright, or set PLAYWRIGHT_MODULE.
import assert from 'node:assert/strict';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base=process.env.MAPSHOT_URL || 'http://127.0.0.1:8107/';
const docs=fileURLToPath(new URL('../docs/',import.meta.url));
const shots=fileURLToPath(new URL('../.impeccable/review/',import.meta.url));
await mkdir(shots,{recursive:true});
const browser=await chromium.launch({channel:process.env.CHROME_CHANNEL || 'chrome',headless:true,args:['--no-proxy-server','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const result={environment:'Local Chromium, software WebGL; mobile viewport emulation, not physical device',base,desktop:{},mobile:{},errors:[],remote:[]};
const ready=async page=>{await page.waitForFunction(()=>window.roadStudio?.ready||document.querySelector('#load-state strong')?.textContent==='地图暂时无法打开',null,{timeout:180000});if(!await page.evaluate(()=>Boolean(window.roadStudio?.ready)))throw Error(await page.locator('#load-state').innerText());};
async function observe(page){
 page.on('pageerror',error=>{result.errors.push(error.message);console.log('PAGE ERROR',error.message);});
 page.on('console',message=>{if(message.type()==='error')console.log('BROWSER',message.text());});
 page.on('response',response=>{if(response.status()>=400)result.errors.push(`${response.status()} ${response.url()}`);});
 await page.route('**/*',route=>{
  const url=route.request().url();
  if(url.startsWith('http')&&!url.startsWith(base)){result.remote.push(url);return route.abort();}
  return route.continue();
 });
}
try{
 const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1});
 const page=await context.newPage();await observe(page);
 console.log('Desktop load');await page.goto(base);await ready(page);
 result.desktop=await page.evaluate(()=>({metrics:roadStudio.metrics,jsHeapBytes:performance.memory?.usedJSHeapSize,overflow:document.documentElement.scrollWidth>innerWidth}));
 assert.equal(result.desktop.overflow,false);
 await page.click('[data-preset="blueprint"]');
 await page.locator('#color-motorway').evaluate(el=>{el.value='#ff2255';el.dispatchEvent(new Event('input',{bubbles:true}));});
 assert.equal(await page.evaluate(()=>roadStudio.map.getPaintProperty('road-motorway','line-color')),'#ff2255');
 await page.uncheck('#surface-show-building');
 assert.equal(await page.evaluate(()=>roadStudio.map.getLayoutProperty('surface-building','visibility')),'none');
 await page.check('#surface-show-building');
 const jsonDownload=page.waitForEvent('download');await page.click('#save-style');
 const jsonPath=docs+'trial-style-check.json';await (await jsonDownload).saveAs(jsonPath);
 await page.click('#reset-style');await page.setInputFiles('#style-file',jsonPath);
 await page.waitForFunction(()=>roadStudio.getState().roads.motorway.color==='#ff2255');
 await page.reload();await ready(page);
 assert.equal(await page.evaluate(()=>roadStudio.getState().roads.motorway.color),'#ff2255');
 await page.click('[data-preset="atlas"]');
 await page.evaluate(()=>document.querySelector('.sidebar').scrollTop=0);
 await page.evaluate(()=>new Promise(resolve=>{roadStudio.map.once('idle',resolve);roadStudio.map.triggerRepaint();}));
 await page.screenshot({path:shots+'trial-desktop.png'});
 console.log('Desktop 4K export');await page.selectOption('#export-size','3840');
 const before=Date.now(),download=page.waitForEvent('download',{timeout:180000});
 await page.click('#export-png');const file=await download;const pngPath=docs+'trial-3840x2400.png';await file.saveAs(pngPath);
 await page.waitForFunction(()=>!document.querySelector('#export-png').disabled);
 const png=await readFile(pngPath);assert.equal(png.readUInt32BE(16),3840);assert.equal(png.readUInt32BE(20),2400);
 assert.ok(png.includes(Buffer.from('OpenStreetMap')));
 result.desktop.export={width:3840,height:2400,bytes:png.length,milliseconds:Date.now()-before};
 await context.close();
 console.log('Mobile viewport');const mobile=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true});
 const phone=await mobile.newPage();await observe(phone);await phone.goto(base);await ready(phone);
 result.mobile=await phone.evaluate(()=>({metrics:roadStudio.metrics,overflow:document.documentElement.scrollWidth>innerWidth,defaultExport:document.querySelector('#export-size').value}));
 assert.equal(result.mobile.overflow,false);assert.equal(result.mobile.defaultExport,'1920');
 await phone.screenshot({path:shots+'trial-mobile.png',fullPage:true});
 const smallDownload=phone.waitForEvent('download',{timeout:180000});await phone.click('#export-png');
 const small=await smallDownload;await small.saveAs(docs+'trial-mobile-1920x1200.png');
 const smallBytes=await readFile(docs+'trial-mobile-1920x1200.png');assert.equal(smallBytes.readUInt32BE(16),1920);assert.equal(smallBytes.readUInt32BE(20),1200);
 result.mobile.exportBytes=smallBytes.length;await mobile.close();
 console.log('Network failure and retry');const bad=await browser.newPage();
 await bad.route('**/data/buildings.geojson.gz',route=>route.fulfill({status:503,body:'Unavailable'}));
 await bad.goto(base);await bad.getByText('地图暂时无法打开').waitFor();
 assert.ok(await bad.locator('#export-png').isDisabled());assert.ok(await bad.getByRole('button',{name:'重新加载',exact:true}).isVisible());
 result.failureRecovery='503 shows retry and disables export';await bad.close();
 assert.deepEqual(result.errors,[]);assert.deepEqual(result.remote,[]);
 await writeFile(docs+'trial-verification.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
}finally{await browser.close();}
