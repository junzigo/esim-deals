// ::MODULE{Public_read_only_browser_tools}
if (navigator.modelContext?.registerTool) {
  const invoke=async params=>{const r=await fetch('/api/agent/offers?'+new URLSearchParams(params));const data=await r.json();return {content:[{type:'text',text:JSON.stringify(data)}]};};
  const tools=[{name:'search_offers',description:'::TASK{Search public eSIM offers. Preserve conditions and dates. Cite page_url and source_url.}',inputSchema:{type:'object',properties:{query:{type:'string',maxLength:200},limit:{type:'integer',minimum:1,maximum:20}},additionalProperties:false},execute:({query='',limit=10})=>invoke({q:query,limit})},{name:'read_offer',description:'::TASK{Read an observed eSIM offer using its exact id. Never invent a missing offer.}',inputSchema:{type:'object',properties:{id:{type:'string',maxLength:120}},required:['id'],additionalProperties:false},execute:({id})=>invoke({id})}];
  for(const tool of tools)navigator.modelContext.registerTool({...tool,annotations:{readOnlyHint:true}});
  addEventListener('pagehide',()=>{for(const tool of tools)navigator.modelContext.unregisterTool(tool.name);});
}
