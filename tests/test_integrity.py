# ::ILANG
# [TYPE:test][ROLE:no_fake_data_and_configuration_behavior]
# ::BOUNDARY{never:publish_synthetic_fixture_data}
import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from config import ROOT, load_config
from scraper import extract
from build import current_offers, offer_schema, build

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.cfg=load_config(); self.now=datetime.now(timezone.utc)
        self.provider=self.cfg['providers'][0]
        self.o=extract(self.provider,'<p>TEST15 – enjoy 15% off your first eSIM</p>',self.cfg,self.now.isoformat())[0]
    def test_no_price_or_expiry_invented(self):
        self.assertNotIn('price',self.o);self.assertNotIn('valid_until',self.o)
        self.assertNotIn('availability',offer_schema(self.o));self.assertNotIn('price',offer_schema(self.o))
    def test_scripts_not_evidence(self):
        self.assertEqual([],extract(self.provider,'<script>TEST15 – enjoy 15% off your first eSIM</script>',self.cfg,self.now.isoformat()))
    def test_stale_failed_expired_excluded(self):
        d={'offers':[self.o],'sources':[{'provider':self.provider['id'],'status':'ok'}]}
        self.assertEqual(1,len(current_offers(d,self.cfg,self.now)))
        self.assertEqual([],current_offers(d,self.cfg,self.now+timedelta(days=3)))
        self.o['valid_until']='2001-01-01'
        self.assertEqual([],current_offers(d,self.cfg,self.now))
        self.o.pop('valid_until');d['sources'][0]['status']='unavailable'
        self.assertEqual([],current_offers(d,self.cfg,self.now))
    def test_ilang_changes_rendered_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);cfg=tmp/'site.ilang';data=tmp/'data.json'
            text=(ROOT/'.ilang/site.ilang').read_text(encoding='utf-8')
            cfg.write_text('\n'.join(x for x in text.splitlines() if not x.startswith('airalo |')),encoding='utf-8')
            data.write_text(json.dumps({'checked_at':self.now.isoformat(),'offers':[self.o],'sources':[{'provider':'airalo','status':'ok'}]}),encoding='utf-8')
            build(cfg,tmp/'site',data)
            self.assertFalse((tmp/'site/providers/airalo').exists())
            self.assertNotIn('TEST15',(tmp/'site/index.html').read_text(encoding='utf-8'))
    def test_schedule_matches_config(self):
        workflow=(ROOT/'.github/workflows/update.yml').read_text(encoding='utf-8')
        self.assertIn(self.cfg['cron'],workflow)

if __name__=='__main__':unittest.main()
