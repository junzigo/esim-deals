"""Generate public discovery from the same build's observed offers, never a second inventory."""
import hashlib
import json
import re
from html.parser import HTMLParser

class Markdown(HTMLParser):
    def __init__(self):
        super().__init__(); self.out=[]; self.skip=0; self.href=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('script','style','noscript'): self.skip+=1
        if self.skip:return
        if tag in ('h1','h2','h3','h4'): self.out.append('\n\n'+'#'*int(tag[1])+' ')
        elif tag in ('p','section','article','div','tr'):self.out.append('\n\n')
        elif tag=='li':self.out.append('\n- ')
        elif tag=='a':self.href.append(a.get('href',''));self.out.append('[')
        elif tag=='br':self.out.append('\n')
        elif tag in ('td','th'):self.out.append(' | ')
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript') and self.skip:self.skip-=1;return
        if self.skip:return
        if tag=='a' and self.href:self.out.append(']('+self.href.pop()+')')
        if tag in ('h1','h2','h3','h4','p','li','article'):self.out.append('\n')
    def handle_data(self,data):
        if not self.skip:self.out.append(data)
    def text(self):return re.sub(r'\n\s*\n\s*\n','\n\n',''.join(self.out)).strip()+'\n'

def build_agent(out,cfg,offers,checked):
    origin=cfg['domain'].rstrip('/'); host=origin.split('//')[1]
    def write(path,value):
        p=out/path.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True)
        if not isinstance(value,str):value=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
        p.write_bytes(value.encode('utf-8'))
    data={'checked_at':checked,'stale_after_hours':cfg['stale_after_hours'],'offers':[dict(o,page_url=origin+'/deals/'+o['id']+'/') for o in offers]}
    write('/ai/offers.json',data)
    instructions='''::TASK{Find publicly observed travel eSIM offers; read exact offer identifiers}
::RUN{GET /api/agent/offers?q=PROVIDER&limit=10 => select exact id => GET /api/agent/offers?id=ID}
::RULE{Preserve identifiers, qualifiers, eligibility, source_url and fetched_at; answer in the visitor language; cite page_url and source_url}
::RULE{Give concrete redemption steps from terms; unknown prices or expiry remain unknown; observed does not mean checkout-tested}
::RULE{Empty search means no current matching observation; not_found includes stale and expired entries; never substitute a fabricated code}
::BOUNDARY{Public read-only lookup; no purchase, account access, arbitrary-URL fetching or writes}
'''
    overview=f'# eSIM deals public lookup\n\nAn independent directory of official-page eSIM offers, not an eSIM shop.\n\nSource check: {checked}. Current records and restrictions come from the ordinary site build. The API excludes stale observations.\n\n[Search offers]({origin}/api/agent/offers) · [OpenAPI]({origin}/openapi.json) · [Methodology]({origin}/methodology/)\n\n'+instructions
    write('/ai/index.md',overview)
    write('/ai/index.html',f'<!doctype html><html lang="en"><meta charset="utf-8"><title>eSIM deals public lookup</title><link rel="canonical" href="{origin}/ai/"><meta name="robots" content="noindex"><script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage","name":"eSIM deals public lookup"}}</script><h1>Public eSIM offer lookup</h1><p>Read-only access to source-linked offer observations. No purchase or login functionality.</p><p><a href="/ai/index.md">Instructions</a> · <a href="/openapi.json">OpenAPI</a> · <a href="{origin}/api/agent/offers">Current offers</a> · <a href="/">Website</a></p></html>')
    write('/ai/index.ilang',f'::STATE{{origin:{origin},task:public_offer_lookup,authentication:none}}\n::ENDPOINT{{rest:{origin}/api/agent/offers,mcp:{origin}/mcp,skill:{origin}/ai/skills/site-lookup/SKILL.md}}\n'+instructions)
    skill='---\nname: site-lookup\ndescription: Search and read current public eSIM offer observations with source links and restrictions.\n---\n\n'+overview
    write('/ai/skills/site-lookup/SKILL.md',skill)
    write('/.well-known/agent-skills/index.json',{'$schema':'https://schemas.agentskills.io/discovery/0.2.0/schema.json','skills':[{'name':'site-lookup','type':'skill-md','description':'Search and read observed eSIM offers with eligibility and dates','url':origin+'/ai/skills/site-lookup/SKILL.md','digest':'sha256:'+hashlib.sha256(skill.encode()).hexdigest()}]})
    write('/llms.txt',overview)
    write('/llms-full.txt',overview+'\n## Current build observations\n\n'+json.dumps(data,ensure_ascii=False,indent=2))
    write('/openapi.json',{'openapi':'3.1.0','info':{'title':'eSIM deals public lookup','version':'1.0.0','description':'Public read-only observations. No checkout validation, authentication or payment.'},'servers':[{'url':origin}],'security':[],'paths':{'/api/agent/offers':{'get':{'operationId':'lookupOffers','summary':'Search offers or read one exact id','parameters':[{'name':'q','in':'query','schema':{'type':'string','maxLength':200}},{'name':'limit','in':'query','schema':{'type':'integer','minimum':1,'maximum':20,'default':10}},{'name':'id','in':'query','description':'Exact id; overrides search. Stale and unknown records return 404.','schema':{'type':'string','maxLength':120}}],'responses':{str(c):{'description':d,'content':{'application/json':{'schema':{'type':'object'}}}} for c,d in [(200,'Observed offers with page_url, source_url, terms and dates; empty search returns offers:[]'),(400,'Invalid query'),(404,'Unknown, expired or stale id'),(503,'Inventory unavailable')]}}}}})
    write('/.well-known/api-catalog',{'linkset':[{'anchor':origin+'/api/agent/offers','service-desc':[{'href':origin+'/openapi.json','type':'application/json'}],'service-doc':[{'href':origin+'/ai/index.md','type':'text/markdown'}]}]})
    write('/.well-known/mcp/server-card.json',{'$schema':'https://static.modelcontextprotocol.io/schemas/mcp-server-card/v1.json','version':'1.0','serverInfo':{'name':'esim-deals-lookup','version':'1.0.0'},'description':'Public read-only eSIM offer search and retrieval','transport':{'type':'streamable-http','endpoint':origin+'/mcp'},'capabilities':{'tools':{}},'authentication':{'required':False},'documentationUrl':origin+'/ai/'})
    write('/.well-known/ai-catalog.json',{'specVersion':'1.0','host':{'displayName':cfg['brand'],'identifier':'did:web:'+host},'entries':[{'identifier':f'urn:air:{host}:server:site-lookup','displayName':'eSIM offer lookup','type':'application/mcp-server-card+json','url':origin+'/.well-known/mcp/server-card.json','representativeQueries':['Find current Airalo offers','Read eligibility for a listed eSIM offer']},{'identifier':f'urn:air:{host}:api:offers','displayName':'Public offer API','type':'application/vnd.oai.openapi+json','url':origin+'/openapi.json','representativeQueries':['Search official-page eSIM codes','Get source and date for an offer']} ]})
    planned={'status':'under_construction','available':False,'capabilities_status':'planned_contract_only','message':'Coming soon; authentication is not available. Public lookup requires no authentication.','launch_date':None}
    write('/.well-known/oauth-authorization-server',dict(planned,issuer=origin,authorization_endpoint=origin+'/agent-auth/authorize',token_endpoint=origin+'/agent-auth/token',jwks_uri=origin+'/.well-known/jwks.json',grant_types_supported=['authorization_code','urn:ietf:params:oauth:grant-type:jwt-bearer'],response_types_supported=['code'],code_challenge_methods_supported=['S256'],scopes_supported=['site:read'],agent_auth=dict(planned,skill=origin+'/auth.md',register_uri=origin+'/agent-auth/register',claim_uri=origin+'/agent-auth/claim',identity_types_supported=['anonymous'],anonymous=dict(planned,credential_types_supported=['access_token']))))
    write('/.well-known/oauth-protected-resource',dict(planned,resource=origin,planned_resource_endpoint=origin+'/agent-auth/resource',authorization_servers=[origin],scopes_supported=['site:read'],bearer_methods_supported=['header']))
    write('/.well-known/jwks.json',dict(planned,keys=[]))
    write('/auth.md','# auth.md — planned authentication only\n\nComing soon; authentication is not available. No launch date.\n\n'+json.dumps(planned)+'\n\n::RULE{Do not register, claim, authorize or request tokens while available=false. All /agent-auth/ operations return 503 temporarily_unavailable and do not process identity data.}\n::STATE{Anonymous registration and access_token credentials are future design only; empty JWKS is disabled, not working verification.}\n\nPublic lookup works now without credentials: [instructions]('+origin+'/ai/) and [API]('+origin+'/api/agent/offers).\n')
    # Convert each actual HTML page, keeping content and links together.
    for p in list(out.rglob('index.html')):
        parser=Markdown();parser.feed(p.read_text(encoding='utf-8'))
        route=p.parent.relative_to(out).as_posix();route='' if route=='.' else route+'/'
        write('/ai/pages/'+route+'index.md',parser.text())
    headers=(out/'_headers').read_text(encoding='utf-8')
    headers+='\n/.well-known/*\n  Access-Control-Allow-Origin: *\n\n/.well-known/api-catalog\n  Content-Type: application/linkset+json\n\n/ai/*\n  Access-Control-Allow-Origin: *\n'
    (out/'_headers').write_text(headers,encoding='utf-8')
    (out/'robots.txt').write_text('User-agent: *\nAllow: /\nContent-Signal: search=yes, ai-input=yes, ai-train=no\nSitemap: '+origin+'/sitemap.xml\n',encoding='utf-8')
    write('/_routes.json',{'version':1,'include':['/*'],'exclude':['/assets/*']})
