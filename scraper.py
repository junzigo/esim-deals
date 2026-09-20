# ::ILANG
# [TYPE:code][ROLE:fetch_official_public_offers]
# ::BOUNDARY{never:bypass_robots_or_invent_fields}
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser
from config import ROOT, load_config

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'template'):
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'template') and self.skip:
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def request(url, cfg):
    req = Request(url, headers={'User-Agent': cfg['user_agent'], 'Accept-Language': 'en-US,en;q=0.9'})
    with build_opener(NoRedirect).open(req, timeout=cfg['request_timeout_seconds']) as response:
        raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise ValueError('Source exceeds size limit')
        return raw.decode('utf-8-sig', errors='replace'), response.headers.get_content_type()

def allowed_fetch(url, cfg):
    # Fail closed on unavailable robots; HTTP 404/410 means no robots file.
    origin = urlsplit(url)
    robots_url = f'{origin.scheme}://{origin.netloc}/robots.txt'
    try:
        robots_text, kind = request(robots_url, cfg)
        if '<html' in robots_text[:500].lower():
            raise ValueError('Robots endpoint returned HTML')
    except HTTPError as exc:
        if exc.code in (404, 410):
            robots_text = ''
        else:
            raise
    parser = RobotFileParser(); parser.parse(robots_text.splitlines())
    if not parser.can_fetch(cfg['user_agent'], url):
        raise PermissionError('Disallowed by robots.txt')
    delay = parser.crawl_delay(cfg['user_agent']) or 1
    if delay > 60:
        raise ValueError('Crawl delay exceeds pipeline budget')
    time.sleep(max(1, delay))
    html, kind = request(url, cfg)
    if kind not in ('text/html', 'application/xhtml+xml'):
        raise ValueError('Expected public HTML')
    return html

def extract(provider, html, cfg, fetched_at):
    parser = VisibleText(); parser.feed(html)
    text = ' '.join(' '.join(parser.parts).split())
    offers = []; seen = set()
    for rule in cfg['extractors'].get(provider['id'], []):
        for match in re.finditer(rule['pattern'], text):
            fields = match.groupdict()
            code = fields['code']
            if code in seen:
                continue
            seen.add(code)
            percent = int(fields['discount'])
            if not 0 < percent < 100:
                continue
            label = fields.get('label') or rule['label']
            record = {
                'id': provider['id'] + '-' + hashlib.sha256(code.encode()).hexdigest()[:10],
                'provider': provider['id'],
                'title': f'{percent}% off — {label}',
                'code': code, 'discount_percent': percent,
                'terms': rule['terms'], 'offer_url': provider['source'],
                'source_url': provider['source'], 'fetched_at': fetched_at,
                'evidence': ' '.join(match.group().split()[:22]),
                'source_sha256': hashlib.sha256(html.encode()).hexdigest(),
                'status': 'observed',
            }
            # No product price, stock assertion or expiry is inferred from a coupon.
            offers.append(record)
    return offers

def run():
    cfg = load_config()
    result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'offers': [], 'sources': []}
    for provider in cfg['providers']:
        stamp = datetime.now(timezone.utc).isoformat()
        state = {'provider': provider['id'], 'source_url': provider['source'], 'attempted_at': stamp}
        try:
            html = allowed_fetch(provider['source'], cfg)
            found = extract(provider, html, cfg, stamp)
            result['offers'].extend(found)
            state.update(status='ok' if found else 'no_verified_offer', count=len(found), fetched_at=stamp)
        except HTTPError as exc:
            state.update(status='unavailable', reason=f'HTTP {exc.code}')
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            state.update(status='unavailable', reason=type(exc).__name__)
        result['sources'].append(state)
        print(provider['id'] + ': ' + state['status'], flush=True)
    target = ROOT / 'data/offers.json'; target.parent.mkdir(exist_ok=True)
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(target)
    return result

if __name__ == '__main__':
    run()
