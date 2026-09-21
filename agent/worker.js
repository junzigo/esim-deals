import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import {WebStandardStreamableHTTPServerTransport} from '@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js';
import {z} from 'zod';
import {lookup,readOffer} from './core.js';
const links='</.well-known/api-catalog>; rel="api-catalog", </openapi.json>; rel="service-desc", </ai/>; rel="service-doc", </.well-known/ai-catalog.json>; rel="ai-catalog"';
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','Access-Control-Allow-Origin':'*'}});
async function inventory(request,env){const r=await env.ASSETS.fetch(new Request(new URL('/ai/offers.json',request.url)));if(!r.ok) throw new Error('inventory_unavailable');return r.json();}
function wantsMarkdown(accept=''){
  const parts=accept.split(',').map(s=>{const [type,...params]=s.trim().toLowerCase().split(';');const q=params.find(p=>p.trim().startsWith('q='));return {type,q:q?Number(q.trim().slice(2)):1};});
  const md=parts.find(p=>p.type==='text/markdown')?.q??0;
  const html=parts.find(p=>p.type==='text/html')?.q??0;
  return md>0 && md>=html;
}
export default {async fetch(request,env){
  const url=new URL(request.url), path=url.pathname;
  if(path.startsWith('/agent-auth/')) return json({status:'under_construction',available:false,capabilities_status:'planned_contract_only',error:'temporarily_unavailable',error_description:'Coming soon. Authentication is not available. Use the public read-only service.',launch_date:null},503);
  if(request.method==='OPTIONS' && (path==='/mcp'||path.startsWith('/api/'))) return new Response(null,{status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type, Accept, MCP-Protocol-Version','Access-Control-Max-Age':'600'}});
  if(path==='/mcp'){
    if(request.method!=='POST')return json({error:'method_not_allowed'},405);
    // No state, accounts, outbound fetch URLs or write tools. Bound body before SDK parsing.
    if(Number(request.headers.get('Content-Length')||0)>16384)return json({error:'payload_too_large'},413);
    const reader=request.body?.getReader();let size=0;const chunks=[];
    if(reader){while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>16384){await reader.cancel();return json({error:'payload_too_large'},413);}chunks.push(value);}}
    const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}const body=new TextDecoder().decode(bytes);
    const data=await inventory(request,env);
    const server=new McpServer({name:'esim-deals-lookup',version:'1.0.0'});
    const reply=value=>({content:[{type:'text',text:JSON.stringify(value)}]});
    server.registerTool('search_offers',{description:'::TASK{Search observed public eSIM offers. Preserve dates and restrictions; cite page_url and source_url. No checkout guarantee.}',inputSchema:{query:z.string().max(200).optional(),limit:z.number().int().min(1).max(20).optional()},annotations:{readOnlyHint:true,destructiveHint:false,idempotentHint:true,openWorldHint:false}},async args=>reply(lookup(data,args)));
    server.registerTool('read_offer',{description:'::TASK{Read a current offer by exact id. Unknown or stale identifiers return not_found. Do not invent missing values.}',inputSchema:{id:z.string().min(1).max(120)},annotations:{readOnlyHint:true,destructiveHint:false,idempotentHint:true,openWorldHint:false}},async args=>reply(readOffer(data,args.id)));
    const transport=new WebStandardStreamableHTTPServerTransport({sessionIdGenerator:undefined,enableJsonResponse:true});
    await server.connect(transport);
    const response=await transport.handleRequest(new Request(request,{body}));
    const result=new Response(response.body,response);result.headers.set('Access-Control-Allow-Origin','*');result.headers.set('Cache-Control','no-store');return result;
  }
  if(path==='/api/agent/offers'){
    if(request.method!=='GET')return json({error:'method_not_allowed'},405);
    try{const data=await inventory(request,env);const id=url.searchParams.get('id');if(id!==null){const value=readOffer(data,id);return json(value,value.error?404:200);}return json(lookup(data,{query:url.searchParams.get('q')??'',limit:url.searchParams.has('limit')?Number(url.searchParams.get('limit')):10}));}catch(e){return json({error:e.message},e.message==='inventory_unavailable'?503:400);}
  }
  if(!['GET','HEAD'].includes(request.method))return json({error:'method_not_allowed'},405);
  let response=await env.ASSETS.fetch(request);
  if(response.ok && response.headers.get('Content-Type')?.includes('text/html') && wantsMarkdown(request.headers.get('Accept'))){
    const route=path.endsWith('/')?path:path+'/';
    const md=await env.ASSETS.fetch(new Request(new URL('/ai/pages'+route+'index.md',url)));
    if(md.ok)response=new Response(md.body,{status:200,headers:{'Content-Type':'text/markdown; charset=utf-8'}});
  }
  const out=new Response(response.body,response);
  out.headers.set('Link',links);out.headers.set('Vary','Accept');
  // Prevent CDN/browser variant contamination rather than relying on CDN Vary support.
  out.headers.set('Cache-Control','no-store');
  if(path.startsWith('/ai/')||path.startsWith('/.well-known/')||path==='/openapi.json'||path.endsWith('.md'))out.headers.set('Access-Control-Allow-Origin','*');
  if(path.endsWith('.md'))out.headers.set('Content-Type','text/markdown; charset=utf-8');
  if(path.endsWith('.ilang'))out.headers.set('Content-Type','text/plain; charset=utf-8');
  if(path==='/.well-known/api-catalog')out.headers.set('Content-Type','application/linkset+json');
  if(path.startsWith('/.well-known/oauth-'))out.headers.set('Content-Type','application/json');
  if(path==='/auth.md'||path.startsWith('/.well-known/oauth-'))out.headers.set('X-Robots-Tag','noindex');
  return out;
}};
