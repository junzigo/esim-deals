import {test} from 'node:test';
import assert from 'node:assert/strict';
import {lookup,readOffer} from './core.js';
import worker from './worker.js';
const stamp=new Date().toISOString();
const data={checked_at:stamp,stale_after_hours:30,offers:[{id:'known-1',provider:'example',title:'First purchase',code:'EXAMPLE',terms:'First purchase only. Monthly plans excluded.',fetched_at:stamp,source_url:'https://example.com/offer',page_url:'https://getesimdeals.com/deals/known-1/'},{id:'stale',provider:'example',fetched_at:'2020-01-01T00:00:00Z'}]};
const env={ASSETS:{fetch:async req=>{const p=new URL(req.url).pathname;return p==='/ai/offers.json'?Response.json(data):p==='/ai/pages/index.md'?new Response('# Actual homepage\n\n[Offer](/deals/known-1/)'):new Response('<h1>Actual homepage</h1>',{headers:{'Content-Type':'text/html'}});}}};
test('query/read preserve restrictions; stale and missing excluded; bounds enforced',()=>{assert.equal(lookup(data,{query:'example'}).offers.length,1);assert.match(readOffer(data,'known-1').offer.terms,/Monthly plans excluded/);assert.equal(readOffer(data,'missing').error,'not_found');assert.equal(readOffer(data,'stale').error,'not_found');assert.throws(()=>lookup(data,{limit:100}));assert.equal(lookup(data,{query:'no match'}).count,0);});
test('real SDK MCP initialize, list and call',async()=>{
  const rpc=async(id,method,params)=>{const r=await worker.fetch(new Request('https://getesimdeals.com/mcp',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json, text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id,method,params})}),env);assert.equal(r.status,200);return r.json();};
  const init=await rpc(1,'initialize',{protocolVersion:'2025-03-26',capabilities:{},clientInfo:{name:'verification',version:'1'}});assert.equal(init.result.serverInfo.name,'esim-deals-lookup');
  const list=await rpc(2,'tools/list',{});assert.equal(list.result.tools.length,2);
  for(const [name,args] of [['search_offers',{query:'example'}],['read_offer',{id:'known-1'}],['read_offer',{id:'missing'}]]){const r=await rpc(3,'tools/call',{name,arguments:args});assert.ok(r.result.content[0].text);if(args.id==='missing')assert.match(r.result.content[0].text,/not_found/);}
});
test('Markdown/HTML alternate without cache contamination',async()=>{for(const accept of ['text/markdown','text/html','text/markdown','text/markdown;q=0,text/html']){const r=await worker.fetch(new Request('https://getesimdeals.com/',{headers:{Accept:accept}}),env);assert.equal(r.headers.get('Vary'),'Accept');assert.equal(r.headers.get('Cache-Control'),'no-store');assert.match(await r.text(),accept==='text/markdown'?/^# Actual/:/^<h1>/);}});
test('planned authentication rejects all operations without parsing identity input',async()=>{for(const name of ['authorize','token','register','claim','resource']){const r=await worker.fetch(new Request('https://getesimdeals.com/agent-auth/'+name,{method:'POST',body:'not JSON'}),env);assert.equal(r.status,503);assert.equal((await r.json()).available,false);}});
