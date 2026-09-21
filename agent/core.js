export const searchSchema = {type:'object',properties:{query:{type:'string',maxLength:200},limit:{type:'integer',minimum:1,maximum:20}},additionalProperties:false};
export const readSchema = {type:'object',properties:{id:{type:'string',maxLength:120}},required:['id'],additionalProperties:false};
export function available(data, now=Date.now()) {
  return data.offers.filter(o => {
    const age=now-Date.parse(o.fetched_at);
    return age>=0 && age<=data.stale_after_hours*3600000 && (!o.valid_until || o.valid_until.slice(0,10)>=new Date(now).toISOString().slice(0,10));
  });
}
export function lookup(data, args={}, now=Date.now()) {
  const query=args.query??''; const limit=args.limit??10;
  if(typeof query!=='string'||query.length>200||!Number.isInteger(limit)||limit<1||limit>20) throw new Error('invalid_query');
  const words=query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const items=available(data,now).filter(o=>words.every(w=>`${o.provider} ${o.title} ${o.code} ${o.terms}`.toLowerCase().includes(w)));
  return {checked_at:data.checked_at, count:items.length, offers:items.slice(0,limit), limitation:'Observed on official pages, not checkout-tested. Preserve restrictions and dates; no match is not proof that a provider has no deals.'};
}
export function readOffer(data,id,now=Date.now()) {
  if(typeof id!=='string'||id.length>120||!id) throw new Error('invalid_id');
  const offer=available(data,now).find(o=>o.id===id);
  return offer ? {offer} : {error:'not_found',message:'Unknown, expired or stale offer. Search current offers.'};
}
