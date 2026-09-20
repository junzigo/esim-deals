# ::ILANG
# [TYPE:code][ROLE:parse_site_rules]
# ::BOUNDARY{never:duplicate_provider_list_or_execute_config}
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent

def load_config(path=None):
    text = Path(path or ROOT / '.ilang/site.ilang').read_text(encoding='utf-8-sig')
    if not text.startswith('::ILANG\n'):
        raise ValueError('Missing ILANG header')
    site = re.search(r'::STATE\{@SITE,\s*(.*?)\}', text).group(1)
    result = dict(item.strip().split(':', 1) for item in site.split(','))
    sections = re.split(r'::MODULE\{([^|}]+)[^}]*\}\s*', text)
    modules = dict(zip(sections[1::2], sections[2::2]))
    providers = []
    for line in modules['PROVIDERS'].splitlines():
        if not line.strip():
            continue
        key, home, source, affiliate = [v.strip() for v in line.split('|')]
        if not re.fullmatch('[a-z0-9-]+', key):
            raise ValueError('Invalid provider slug')
        for url in [home, source] + ([affiliate] if affiliate else []):
            if urlsplit(url).scheme != 'https' or not urlsplit(url).hostname:
                raise ValueError('Only HTTPS public URLs allowed')
        providers.append(dict(id=key, home=home, source=source, affiliate=affiliate))
    result['providers'] = providers
    result['fields'] = modules['FIELDS'].strip().split()
    result.update(json.JSONDecoder().raw_decode(modules['RUNTIME'].lstrip())[0])
    return result
