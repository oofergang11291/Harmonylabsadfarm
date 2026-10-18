"""Smoke tests for the offline generator. Run: python test_generator.py"""
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

BASE=Path(__file__).resolve().parent

class TestGenerator(unittest.TestCase):
    def test_batch_and_captions(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable,str(BASE/'generate_ads.py'),'--out',tmp],
                           check=True,capture_output=True,text=True)
            out=Path(tmp)
            pngs=sorted(out.glob('ad_*.png'))
            self.assertEqual(len(pngs),30)
            for p in pngs:
                with Image.open(p) as im:
                    self.assertEqual(im.size,(1080,1350))
                    im.verify()
            with (out/'captions.csv').open(newline='',encoding='utf-8-sig') as f:
                data=list(csv.DictReader(f))
            self.assertEqual(len(data),30)
            for i,row in enumerate(data,1):
                self.assertEqual(int(row['Day']),i)
                self.assertEqual(row['Image'],f'ad_{i:02d}.png')
                self.assertIn('bio',row['Caption'].lower())
                self.assertNotIn('coming soon',row['Caption'].lower())
                self.assertNotIn('#comingsoon',row['Hashtags'].lower())

    def test_only_subset(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable,str(BASE/'generate_ads.py'),'--out',tmp,'--only','1,4,30'],
                           check=True,capture_output=True,text=True)
            out=Path(tmp)
            self.assertEqual(sorted(p.name for p in out.glob('ad_*.png')),
                             ['ad_01.png','ad_04.png','ad_30.png'])
            with (out/'captions.csv').open(newline='',encoding='utf-8-sig') as f:
                rows=list(csv.DictReader(f))
            self.assertEqual([int(x['Day']) for x in rows],[1,4,30])

if __name__ == '__main__': unittest.main()
