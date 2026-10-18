import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('auto_post', ROOT/'auto_post.py')
auto=importlib.util.module_from_spec(spec)
spec.loader.exec_module(auto)

class AutomationTests(unittest.TestCase):
    def test_30_matched_ads_and_captions(self):
        rows=auto.read_posts()
        self.assertEqual(len(rows),30)
        for i, row in enumerate(rows, 1):
            self.assertEqual(row['Image'],f'ad_{i:02d}.png')
            self.assertIn('bio',row['Caption'].lower())

    def test_selects_only_harmonylabs(self):
        channels=[
            {'id':'h1','name':'harmonylabs.online','service':'tiktok'},
            {'id':'h2','displayName':'HarmonyLabs NZ','service':'instagram'},
            {'id':'private','name':'my-personal-account','service':'facebook'},
        ]
        with patch.dict(os.environ,{'BUFFER_CHANNEL_IDS':''}):
            self.assertEqual([x['id'] for x in auto.select_channels(channels)],['h1','h2'])

    def test_media_path(self):
        with patch.dict(os.environ,{'GITHUB_REPOSITORY':'owner/harmony-ads','GITHUB_REF_NAME':'main','MEDIA_BASE_URL':''}):
            self.assertEqual(auto.media_url('ad_07.png'),'https://raw.githubusercontent.com/owner/harmony-ads/main/output/ad_07.png')
        with self.assertRaises(auto.PostingError):
            auto.media_url('../secret.png')

    def test_mutation_contains_caption_and_image(self):
        query=auto.make_mutation('chan_A','Hello!\n\n#HarmonyLabs','https://example.org/ad_01.png')
        self.assertIn('addToQueue',query)
        self.assertIn('schedulingType: automatic',query)
        self.assertIn('Hello!\\n\\n#HarmonyLabs',query)
        self.assertIn('https://example.org/ad_01.png',query)

    def test_end_to_end_mock_queue_and_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/'state.json'
            fake_channels=[{'id':'ig123','displayName':'HarmonyLabs','service':'instagram'},
                           {'id':'tt456','displayName':'HarmonyLabs','service':'tiktok'}]
            result={'channels':fake_channels}
            def graphql_mock(query,key):
                if query.startswith('query { account'): return {'account':{'organizations':[{'id':'org','name':'Org'}]}}
                if query.startswith('query { channels'): return result
                if 'createPost' in query: return {'createPost':{'__typename':'PostActionSuccess','post':{'id':str(abs(hash(query))), 'dueAt':'2026-10-19T05:00:00.000Z'}}}
                raise AssertionError('Unexpected query')
            with patch.object(auto,'STATE',state), patch.object(auto,'graphql',side_effect=graphql_mock) as api, patch.object(auto,'check_public_url'), patch.dict(os.environ,{'BUFFER_API_KEY':'fake','GITHUB_REPOSITORY':'test/repo','GITHUB_REF_NAME':'main','BUFFER_CHANNEL_IDS':''}):
                auto.run(date_override='2026-10-19')
                snapshot=auto.load_state()
                self.assertEqual(snapshot['channels']['ig123']['next_day'],2)
                self.assertEqual(snapshot['channels']['tt456']['next_day'],2)
                count=api.call_count
                auto.run(date_override='2026-10-19')
                self.assertEqual(api.call_count,count+2) # account and channels only
                auto.run(date_override='2026-10-20')
                self.assertEqual(auto.load_state()['channels']['ig123']['next_day'],3)
                self.assertEqual(auto.load_state()['channels']['tt456']['next_day'],3)

    def test_partial_failures_save_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/'state.json'
            c1={'id':'ig123','displayName':'HarmonyLabs IG','service':'instagram'}
            c2={'id':'tt456','displayName':'HarmonyLabs TT','service':'tiktok'}
            with patch.object(auto,'STATE',state), patch.object(auto,'discover_channels',return_value=[c1,c2]), patch.object(auto,'check_public_url'), patch.object(auto,'media_url',return_value='https://example.com/ad_01.png'),patch.dict(os.environ,{'BUFFER_API_KEY':'fake','BUFFER_CHANNEL_IDS':''}):
                def make_post(key,channel,row,url):
                    if channel['id']=='tt456':
                        raise auto.PostingError('Temporary failure')
                    return {'id':'success_post','dueAt':'2026-10-19T05:00:00Z'}
                with patch.object(auto,'create_post',side_effect=make_post):
                    with self.assertRaises(auto.PostingError): auto.run(date_override='2026-10-19')
                self.assertEqual(auto.load_state()['channels']['ig123']['last_queued_date'],'2026-10-19')
                self.assertEqual(auto.load_state()['channels']['ig123']['next_day'],2)
                self.assertEqual(auto.load_state()['channels'].get('tt456',{'next_day':1})['next_day'],1)

if __name__=='__main__': unittest.main()
