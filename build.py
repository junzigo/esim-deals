# ::ILANG
# [TYPE:code][ROLE:render_static_site_from_ilang_and_observed_data]
# ::BOUNDARY{never:invent_prices_expiry_reviews_or_availability}
import html
import json
import shutil
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from xml.sax.saxutils import escape as xml_escape
from config import ROOT, load_config

def esc(value):
    return html.escape(str(value), quote=True)

def label(value):
    return {'redteago':'RedteaGO', 'airalo':'Airalo', 'holafly':'Holafly', 'nomad':'Nomad', 'saily':'Saily', 'ubigi':'Ubigi'}.get(value, value.title())

def render(name, **values):
    return Template((ROOT/'templates'/name).read_text(encoding='utf-8')).substitute(values)

def parse_date(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=timezone.utc) if len(value) == 10 else datetime.fromisoformat(value.replace('Z', '+00:00'))

def current_offers(data, cfg, now=None):
    now = now or datetime.now(timezone.utc)
    ids = {p['id'] for p in cfg['providers']}
    good_sources = {s['provider'] for s in data.get('sources', []) if s['status'] == 'ok'}
    result=[]
    for offer in data.get('offers', []):
        if offer['provider'] not in ids or offer['provider'] not in good_sources:
            continue
        try:
            age = (now-parse_date(offer['fetched_at'])).total_seconds()/3600
            if age < 0 or age > cfg['stale_after_hours']:
                continue
            if offer.get('valid_until') and parse_date(offer['valid_until']).date() < now.date():
                continue
        except (ValueError, TypeError):
            continue
        result.append(offer)
    return result

def offer_schema(offer):
    result={'@type':'Offer', 'name':offer['title'], 'url':offer['offer_url'], 'description':offer['terms']}
    if 'price' in offer and offer.get('currency'):
        result.update(price=offer['price'], priceCurrency=offer['currency'])
    if offer.get('valid_until'):
        result['priceValidUntil']=offer['valid_until']
    # Coupon presence does not prove stock/availability.
    return result

def social_image(path):
    # Standard-library PNG: branded abstract travel card, no downloaded assets.
    w,h=1200,630
    raw=bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            color=(247,248,241)
            if 670<x<1140 and 70<y<560: color=(223,241,207)
            if 740<x<1070 and 170<y<460: color=(23,62,232)
            if 80<x<570 and (160<y<200 or 235<y<275 or 310<y<350): color=(16,37,36)
            if 80<x<390 and 440<y<485: color=(23,62,232)
            raw.extend(color)
    def chunk(kind, content):
        return struct.pack('!I',len(content))+kind+content+struct.pack('!I',zlib.crc32(kind+content)&0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(raw)))+chunk(b'IEND',b''))

def build(config_path=None, output=None, data_path=None):
    cfg=load_config(config_path)
    out=Path(output or ROOT/'site')
    if out.resolve()==ROOT.resolve() or ROOT.resolve() in out.resolve().parents and out.name!='site':
        raise ValueError('Refusing unsafe output directory')
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(ROOT/'assets',out/'assets')
    social_image(out/'assets/social.png')
    data=json.loads(Path(data_path or ROOT/'data/offers.json').read_text(encoding='utf-8'))
    offers=current_offers(data,cfg)
    provider_map={p['id']:p for p in cfg['providers']}
    source_map={s['provider']:s for s in data.get('sources',[]) if s['provider'] in provider_map}
    domain=cfg['domain'].rstrip('/')
    if not domain.startswith('https://'): raise ValueError('Production HTTPS domain required')
    checked=data['checked_at']; month=parse_date(checked).strftime('%B %Y')
    routes=[]
    def write(route, title, description, content, entities=None, lastmod=None, noindex=False):
        canonical=domain+route
        graph=[{'@type':'WebPage','@id':canonical,'url':canonical,'name':title,'description':description}]
        if route!='/':
            graph.append({'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':cfg['brand'],'item':domain+'/'},{'@type':'ListItem','position':2,'name':title,'item':canonical}]})
        graph.extend(entities or [])
        schema=json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('<','\\u003c')
        page=render('base.html', title=esc(title),description=esc(description),canonical=esc(canonical),domain=esc(domain),content=content,schema=schema,robots_meta='<meta name="robots" content="noindex,follow">' if noindex else '',repo_link=f'<a href="{esc(cfg["repository"])}">Public source code ↗</a>' if cfg.get('repository') else '')
        target=out/route.strip('/')/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(page,encoding='utf-8')
        if not noindex: routes.append((route,lastmod))
    def card(o):
        return f'''<article class="card" data-provider="{esc(o['provider'])}" data-fetched="{esc(o['fetched_at'])}" data-stale-hours="{cfg['stale_after_hours']}"><div class="card-top"><a href="/providers/{esc(o['provider'])}/">{esc(label(o['provider']))}</a><span class="tag">OFFICIAL SOURCE</span></div><div class="saving">{o['discount_percent']}% <span>off</span></div><h3>{esc(o['title'].split(' — ',1)[-1])}</h3><p>{esc(o['terms'])}</p><div class="coupon"><strong>{esc(o['code'])}</strong><button data-code="{esc(o['code'])}" aria-label="Copy {esc(o['code'])}">Copy ↗</button></div><a class="card-link" href="/deals/{esc(o['id'])}/">Conditions &amp; official source <span>↗</span></a></article>'''
    def item_list(items):
        return {'@type':'ItemList','itemListElement':[{'@type':'ListItem','position':i+1,'url':domain+'/deals/'+o['id']+'/','name':o['title']} for i,o in enumerate(items)]}
    def status(p):
        state=source_map.get(p['id'],{})
        if any(o['provider']==p['id'] for o in offers): return 'Official-page offer observed'
        if state.get('status')=='unavailable': return 'Source unavailable at the last check'
        return 'No current offer independently confirmed'
    cards=''.join(card(o) for o in offers) or '<p>No current offers confirmed. Check the official providers below.</p>'
    filters='<button data-filter="all" aria-pressed="true">All offers</button>'+''.join(f'<button data-filter="{esc(p["id"])}" aria-pressed="false">{esc(label(p["id"]))}</button>' for p in cfg['providers'] if any(o['provider']==p['id'] for o in offers))
    providers=''.join((f'<a class="provider-item" href="/providers/{p["id"]}/"><strong>{esc(label(p["id"]))} ↗</strong><span>{esc(status(p))}</span></a>' if any(o['provider']==p['id'] for o in offers) else f'<div class="provider-item"><strong>{esc(label(p["id"]))}</strong><span>{esc(status(p))}</span><a href="{esc(p["home"])}">Official website ↗</a></div>') for p in cfg['providers'])
    content=render('index.html',summary=f'{len(offers)} official-page offers observed across {len(cfg["providers"])} monitored providers. English-language sources for US travelers.',cards=cards,filters=filters,providers=providers,checked=esc(checked))
    write('/',f'eSIM offers & promo codes — {month} | {cfg["brand"]}','Explore source-linked travel eSIM offers with clear eligibility, expiry information and transparent check times.',content,[item_list(offers)],checked)
    for p in cfg['providers']:
        items=[o for o in offers if o['provider']==p['id']]
        if not items:
            continue
        name=label(p['id']); note=source_map.get(p['id'],{})
        content=render('provider.html',provider_name=esc(name),status=esc(status(p)),official=esc(p['home']),cards=''.join(card(o) for o in items) or '<p>No current offer confirmed. We do not fill gaps with invented codes.</p>',source_note=esc('Last attempt: '+note.get('attempted_at','Not yet checked')+'. Source: '+p['source']))
        service={'@type':'Service','name':name+' travel eSIM service','provider':{'@type':'Organization','name':name,'url':p['home']}}
        if items: service['offers']=[offer_schema(o) for o in items]
        priced=[o for o in items if 'price' in o and o.get('currency')]
        if len(priced)==len(items) and priced and len({o['currency'] for o in priced})==1:
            service['offers']={'@type':'AggregateOffer','lowPrice':min(float(o['price']) for o in priced),'highPrice':max(float(o['price']) for o in priced),'priceCurrency':priced[0]['currency'],'offerCount':len(priced)}
        write('/providers/'+p['id']+'/',f'{name} offers & conditions — {month}',f'{name}: {status(p).lower()}. Official source and transparent check status.',content,[service],note.get('fetched_at'),not items)
    for o in offers:
        p=provider_map[o['provider']]
        content=render('deal.html',provider=esc(p['id']),provider_name=esc(label(p['id'])),deal_title=esc(o['title']),terms=esc(o['terms']),expiry=esc(o.get('valid_until','Not published in the extracted offer. Confirm with provider.')),price=esc(str(o['price'])+' '+o['currency'] if 'price' in o and o.get('currency') else 'Plan-dependent. No plan price quoted for this promotion.'),fetched=esc(o['fetched_at']),evidence=esc(o['evidence']),source_url=esc(o['source_url']),code=esc(o['code']),destination=esc(p['affiliate'] or o['offer_url']),rel='sponsored nofollow noopener' if p['affiliate'] else 'noopener')
        write('/deals/'+o['id']+'/',f'{label(p["id"])} {o["discount_percent"]}% offer — {month} | {cfg["brand"]}',o['terms'],content,[offer_schema(o)],o['fetched_at'])
    rows=''.join(f'<tr><td>{esc(label(o["provider"]))}</td><td><a href="/deals/{o["id"]}/">{esc(o["title"])}</a></td><td>{esc(o["terms"])}</td><td>{esc(o.get("valid_until","Not published"))}</td><td><a href="{esc(o["source_url"])}">Official page ↗</a></td></tr>' for o in offers)
    write('/compare/',f'Compare eSIM promotion terms — {month}','Compare eligibility and conditions for source-linked eSIM promotions. No misleading cheapest-plan ranking.',render('compare.html',rows=rows or '<tr><td colspan="5">No current offers confirmed.</td></tr>'),[item_list(offers)],checked)
    pages={
      'about':('About eSIM deals','<h2>Independent help with eSIM promotions.</h2><p>eSIM deals is operated by An independent developer. This independent directory helps travelers compare offers found on official eSIM provider pages, with eligibility conditions and source-check dates alongside each promotion.</p><h2>What we do</h2><p>We organize publicly available promotional information and explain its limits. We do not sell connectivity, activate plans, collect payment details or provide carrier support. An observed coupon is not a guarantee that it will work for every account or destination.</p><h2>How listings are maintained</h2><p>Our checker reads official public sources and excludes offers it cannot confirm in a current check. We do not invent prices, expiry dates, reviews or claims of partnership. Read <a href="/methodology/">our methodology</a> and <a href="/disclosure/">affiliate disclosure</a> for details.</p><p>For corrections or questions about this website, visit <a href="/contact/">Contact</a>.</p>'),
      'contact':('Contact','<h2>Contact the site operator</h2><p>For eSIM deals website feedback, privacy questions or a correction to a listed promotion, email <!--email_off--><a href="mailto:contact@getesimdeals.com">contact@getesimdeals.com</a><!--/email_off-->.</p><h2>Report an offer issue</h2><p>Include the page URL, provider name, coupon code and a brief description of what differs from the official offer. Please do not send passwords, payment card details, passport documents or account recovery codes.</p><h2>Need help with a purchase or activation?</h2><p>Contact the eSIM provider you purchased from. This website cannot access your provider account, activate an eSIM, issue a refund or resolve a network fault.</p>'),
      'methodology':('Our method','<h2>Official pages, explicit limits.</h2><p>Our deterministic Python checker reads the official sources listed below. It checks robots.txt first, uses a named user agent, makes bounded requests and does not bypass access controls. A successful match means the text was observed, not that we tested a purchase.</p><h2>What happens when a source changes?</h2><p>Requests that fail, unavailable pages and unmatched promotions produce no current offer. Previous offers are not silently carried forward. Builds exclude records older than the configured freshness window. Unknown prices, expiry dates and stock status are omitted from structured data.</p><h2>What to check at checkout</h2><p>Account eligibility, destination, plan type, data allowance, activation window, renewal terms and total payment. Discounts across different plans are not a price comparison.</p><h2>Sources</h2><ul>'+''.join(f'<li><a href="{esc(p["source"])}">{esc(label(p["id"]))} official source ↗</a> — {esc(status(p))}</li>' for p in cfg['providers'])+'</ul>'),
      'disclosure':('Affiliate disclosure','<h2>How this site may earn revenue</h2><p>Provider links are direct official links unless specifically marked as sponsored affiliate links. No affiliate commissions are currently claimed by this site. If approved affiliate links are added, we may receive a commission for qualifying purchases. Such links are marked sponsored and do not determine which offers are listed.</p><p>We do not invent commission rates or claim partnership approval. This site does not sell eSIMs, collect payments, or guarantee discounts. Provider trademarks belong to their owners.</p>'),
      'privacy':('Privacy','<h2>What happens when you visit</h2><p>This is a public static eSIM offer directory. There is no account signup, payment form, advertising script or analytics script currently installed. We do not sell eSIMs or collect payment details. Cloudflare hosts and secures the site and may process technical request information to deliver pages and prevent abuse.</p><h2>Cookies and coupon copying</h2><p>Our site code does not set advertising cookies or use local storage. Copying a coupon writes the selected code to your browser clipboard only after you click Copy; we do not receive a coupon-copy event. Hosting security services may use technical mechanisms governed by their own privacy notices.</p><h2>Planned third-party advertising</h2><p>We plan to display third-party advertisements after an advertising network approves this site. No advertising network is active today. Once enabled, an advertising provider may process browser and device information and use cookies or similar technologies to deliver, measure and, where permitted, personalize advertising. Before enabling ads, we will identify the provider here, link its privacy and opt-out information, and implement the consent controls required for that integration. This notice does not mean you have consented to future advertising.</p><h2>Links to other websites</h2><p>Following a provider link takes you to a separate website with its own privacy and cookie policies. Check those policies before providing personal or payment information.</p><h2>Privacy questions</h2><p>Contact the site operator at <!--email_off--><a href="mailto:contact@getesimdeals.com">contact@getesimdeals.com</a><!--/email_off--> about this website.</p><h2>Your choices</h2><p>You can control cookies through your browser settings and choose whether to visit external links. The site does not currently offer an account or newsletter subscription.</p>')}
    for slug,(title,body) in pages.items():
        write('/'+slug+'/',title+' | '+cfg['brand'],title+' for the independent esim-deals directory.',f'<section class="page-head"><div class="eyebrow">GOOD TO KNOW</div><h1>{esc(title)}</h1></section><section class="prose">{body}</section>')
    sitemap='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml_escape(domain+route)+'</loc>'+('<lastmod>'+xml_escape(stamp)+'</lastmod>' if stamp else '')+'</url>' for route,stamp in routes)+'</urlset>'
    (out/'sitemap.xml').write_text(sitemap,encoding='utf-8')
    (out/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+domain+'/sitemap.xml\n',encoding='utf-8')
    (out/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  Content-Security-Policy: default-src \'self\'; script-src \'self\'; style-src \'self\'; img-src \'self\' data:; object-src \'none\'; base-uri \'self\'; frame-ancestors \'none\'\n',encoding='utf-8')
    (out/'404.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="robots" content="noindex"><title>Offer unavailable</title><h1>This offer is no longer listed.</h1><p>It may have expired or could not be confirmed.</p><a href="/">See current source checks</a></html>',encoding='utf-8')
    print(f'Built {len(routes)} indexable pages; {len(offers)} observed offers')
    return offers

if __name__=='__main__': build()
