# ::ILANG
# [TYPE:code][ROLE:validate_static_outputs]
# ::BOUNDARY{never:claim_google_rich_results_from_local_validation}
import json
from html.parser import HTMLParser
from urllib.parse import urlsplit
from xml.etree import ElementTree
from config import ROOT, load_config

class Check(HTMLParser):
    def __init__(self): super().__init__();self.canon=[];self.links=[];self.schemas=[];self.inside=False;self.buf=''
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='link' and attrs.get('rel')=='canonical': self.canon.append(attrs['href'])
        if tag=='a':self.links.append(attrs.get('href',''))
        if tag=='script' and attrs.get('type')=='application/ld+json':self.inside=True;self.buf=''
    def handle_data(self,data):
        if self.inside:self.buf+=data
    def handle_endtag(self,tag):
        if tag=='script' and self.inside:self.schemas.append(json.loads(self.buf));self.inside=False

def validate():
    cfg=load_config();count=0
    for file in (ROOT/'site').rglob('index.html'):
        check=Check();check.feed(file.read_text(encoding='utf-8'))
        assert len(check.canon)==1,(file,'canonical count')
        assert check.canon[0].startswith(cfg['domain']),file
        assert check.schemas,(file,'missing schema')
        for link in check.links:
            if link.startswith('/'):
                dest=(ROOT/'site'/urlsplit(link).path.strip('/'))
                assert dest.is_file() or (dest/'index.html').is_file(),(file,link)
        count+=1
    ElementTree.parse(ROOT/'site/sitemap.xml')
    print(f'Validated {count} HTML pages, internal links, canonicals and JSON-LD syntax (not a Google rich-result certification)')

if __name__=='__main__': validate()
