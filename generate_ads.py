"""HarmonyLabs Ad Farm v2 — offline 1080x1350 social ads + captions.

Free, deterministic, editable, Windows/macOS/Linux. Requires Pillow only.
Usage: python generate_ads.py [--only 1,2,3] [--out output]
Change content/posts.csv to change ad copy and captions.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / 'content' / 'posts.csv'
W, H = 1080, 1350
BG = (12, 10, 20)
GRID = (26, 21, 41)
PURPLE = (160, 99, 255)
WHITE = (244, 240, 252)
MUTED = (164, 151, 184)
OUTLINE = (65, 48, 96)
CARD = (76, 64, 1004, 1260)
LEFT = 128                   # One shared left margin for ALL lower text + CTA
RIGHT = 952                  # One shared right boundary
CONTENT_WIDTH = RIGHT - LEFT
META_TOP = 882
HEADLINE_TOP = 945
SUBTITLE_TOP = 1046
FOOTER_LINE_Y = 1205
FOOTER_TOP = 1226
BOTTOM_OF_TEXT = 1179


def font_paths():
    """Find actual OS fonts without shipping font files with the package."""
    win = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts'
    pairs = [
        (win/'segoeuib.ttf', win/'segoeui.ttf'),
        (win/'arialbd.ttf', win/'arial.ttf'),
        (Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
         Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')),
        (Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf'),
         Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf')),
        (Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
         Path('/System/Library/Fonts/Supplemental/Arial.ttf')),
    ]
    for bold, regular in pairs:
        if bold.is_file() and regular.is_file():
            return str(bold), str(regular)
    for name_a, name_b in [('DejaVuSans-Bold.ttf','DejaVuSans.ttf'),
                           ('arialbd.ttf','arial.ttf')]:
        try:
            ImageFont.truetype(name_a, 30)
            ImageFont.truetype(name_b, 30)
            return name_a, name_b
        except OSError:
            pass
    raise RuntimeError('No suitable font found. Install Windows Segoe UI/Arial or Linux DejaVu Sans.')


FONT_BOLD, FONT_REG = font_paths()


def fnt(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def width(d, s, f):
    return d.textlength(s, font=f)


def wrap_pixels(d, s, f, max_width):
    """Break only between words, using actual font metrics; never clip silently."""
    lines = []
    for para in s.split('\n'):
        words = para.split()
        if not words:
            lines.append('')
            continue
        line = words[0]
        for word in words[1:]:
            candidate = line + ' ' + word
            if width(d, candidate, f) <= max_width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def fit_lines(d, text, max_width, max_lines, initial_size, min_size, bold=False):
    """Find the largest font whose measured lines fit inside the text block."""
    for size in range(initial_size, min_size - 1, -1):
        ff = fnt(size, bold)
        lines = wrap_pixels(d, text, ff, max_width)
        if len(lines) <= max_lines and all(width(d, line, ff) <= max_width for line in lines):
            return ff, lines, size
    raise ValueError(f'Text is too long for the poster: {text!r}. Shorten it in content/posts.csv.')


def paint(d: ImageDraw.ImageDraw, x, y, text, ff, fill, align='left'):
    """Use glyph-top anchors for repeatable alignment independent of font ascenders."""
    d.text((x, y), text, font=ff, fill=fill, anchor=('rt' if align=='right' else 'lt'))


def geometry(d, i):
    """Preserves the original five vector motifs and the same day-to-motif mapping."""
    rng = random.Random(i)  # keeps future decorative variation deterministic
    typ = i % 5
    if typ == 0:
        for k in range(6):
            r = 130 + k * 38
            d.ellipse((540-r,515-r,540+r,515+r), outline=(61+k*12,38+k*8,95+k*16), width=3)
        d.line([(250,515),(830,515)],fill=PURPLE,width=4)
        d.line([(540,225),(540,805)],fill=PURPLE,width=4)
    elif typ == 1:
        for k in range(8):
            x = 240+k*84
            height = int(170+120*math.sin(k*.8+i))
            d.rounded_rectangle((x,710-height,x+43,710),radius=14,fill=(78+9*k,47+5*k,120+9*k))
        d.line([(185,725),(905,725)],fill=PURPLE,width=5)
    elif typ == 2:
        pts = [(540+285*math.cos(2*math.pi*k/12),530+285*math.sin(2*math.pi*k/12))
               for k in range(13)]
        d.line(pts,fill=PURPLE,width=7)
        for k in range(0,12,2):
            d.line([pts[k],pts[(k+4)%12]],fill=(92,58,143),width=3)
        for x,y in pts[:12]:
            d.ellipse((x-9,y-9,x+9,y+9),fill=WHITE)
    elif typ == 3:
        for k in range(5):
            off=k*29
            d.rounded_rectangle((200+off,280+off,880-off,770-off),radius=35,
                                outline=PURPLE if k==0 else (73,48,104),width=5)
        for k in range(6):
            d.ellipse((326+k*87,518,337+k*87,529),fill=WHITE)
    else:
        for k in range(4):
            off=k*72
            d.arc((230+off,240+off,850-off,850-off),start=205,end=515,
                  fill=(150,85+k*17,240),width=10)
        d.line([(260,650),(820,350)],fill=WHITE,width=4)
        for x,y in [(260,650),(820,350)]:
            d.ellipse((x-13,y-13,x+13,y+13),fill=PURPLE)


def validate_post(row):
    for key in ('Day','Title','Subtitle','Category','Caption','Hashtags'):
        if not row.get(key, '').strip():
            raise ValueError(f'Day {row.get("Day", "?")}: missing {key}')
    if 'bio' not in row['Caption'].lower():
        raise ValueError(f'Day {row["Day"]}: caption needs a link-in-bio CTA')
    if 'coming soon' in row['Caption'].lower() or '#comingsoon' in row['Hashtags'].lower():
        raise ValueError(f'Day {row["Day"]}: replace coming-soon copy with bio CTA')


def read_posts():
    with CONTENT.open(encoding='utf-8-sig', newline='') as f:
        posts = list(csv.DictReader(f))
    days = []
    for row in posts:
        validate_post(row)
        day = int(row['Day'])
        if day in days:
            raise ValueError(f'Duplicate Day {day}')
        days.append(day)
    if sorted(days) != list(range(1,len(posts)+1)):
        raise ValueError('Day numbers must start at 1 and be consecutive.')
    return posts


def render(row, total, output_dir):
    i = int(row['Day'])
    im = Image.new('RGB',(W,H),BG)
    d = ImageDraw.Draw(im)
    for k in range(14):
        y=160+k*75
        d.line([(0,y),(W,y)],fill=GRID,width=1)
    for k in range(12):
        x=70+k*90
        d.line([(x,0),(x,H)],fill=GRID,width=1)
    geometry(d, i)
    d.rounded_rectangle(CARD,radius=28,outline=OUTLINE,width=3)
    # Header. Icon, label and all lower copy use a considered 52px card inset.
    d.ellipse((LEFT-7,95,LEFT+15,117),fill=PURPLE)
    paint(d, LEFT+37, 94, 'HARMONYLABS', fnt(30,True),WHITE)
    # Metadata: same x as headline and subtitle, consistent baseline spacing.
    paint(d,LEFT,META_TOP, f'{i:02d} / {total:02d}   |   {row["Category"].upper()}',
          fnt(23),MUTED)
    headline_font, headline_lines, title_size = fit_lines(d,row['Title'].upper(),CONTENT_WIDTH,2,61,42,bold=True)
    title_step = round(title_size*1.16)
    for index, line in enumerate(headline_lines):
        paint(d,LEFT,HEADLINE_TOP+title_step*index,line,headline_font,WHITE)
    # Subtitle starts at the same y on 1-line headlines; moves down for 2 lines.
    subtitle_y = max(SUBTITLE_TOP, HEADLINE_TOP+len(headline_lines)*title_step+26)
    available = BOTTOM_OF_TEXT-subtitle_y
    if available < 50:
        raise ValueError(f'Day {i}: headline leaves too little space for subtitle')
    subtitle_font,subtitle_lines,subtitle_size = fit_lines(d,row['Subtitle'],CONTENT_WIDTH,2,29,22)
    subtitle_step = round(subtitle_size*1.32)
    if subtitle_y+(len(subtitle_lines)-1)*subtitle_step+subtitle_size > BOTTOM_OF_TEXT:
        raise ValueError(f'Day {i}: subtitle collides with footer; shorten text')
    for index,line in enumerate(subtitle_lines):
        paint(d,LEFT,subtitle_y+index*subtitle_step,line,subtitle_font,MUTED)
    # Footer: horizontal rule crosses card; text stays inside the same 52px inset.
    d.line([(CARD[0]+2,FOOTER_LINE_Y),(CARD[2]-2,FOOTER_LINE_Y)],fill=(75,50,103),width=3)
    paint(d,LEFT,FOOTER_TOP,'LINK IN BIO',fnt(19,True),PURPLE)
    paint(d,RIGHT,FOOTER_TOP,'@HARMONYLABS',fnt(18),MUTED,align='right')
    dest=output_dir/f'ad_{i:02d}.png'
    im.save(dest,optimize=True)
    return dest


def main():
    parser=argparse.ArgumentParser(description='Generate free HarmonyLabs poster ads + captions CSV')
    parser.add_argument('--only',type=str,default='',help='Render only these days, e.g. 1,4,9')
    parser.add_argument('--out',default='output',help='Output folder (default: output)')
    args=parser.parse_args()
    output_dir=Path(args.out)
    if not output_dir.is_absolute():
        output_dir=ROOT/output_dir
    output_dir.mkdir(parents=True,exist_ok=True)
    posts=read_posts()
    wanted={int(x.strip()) for x in args.only.split(',') if x.strip()} if args.only else set(range(1,len(posts)+1))
    if wanted - {int(p['Day']) for p in posts}:
        raise ValueError('Unknown days in --only')
    for row in posts:
        if int(row['Day']) in wanted:
            render(row,len(posts),output_dir)
    with (output_dir/'captions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.writer(f)
        wr.writerow(['Day','Image','Category','Caption','Hashtags','Status'])
        for row in posts:
            if int(row['Day']) in wanted:
                wr.writerow([row['Day'],f'ad_{int(row["Day"]):02d}.png',row['Category'],
                             row['Caption'],row['Hashtags'],'Ready for review'])
    print(f'Rendered {len(wanted)} PNG posters; exported {len(wanted)} caption rows to {output_dir}')
    print('CTA: LINK IN BIO | Alignment: unified margins, pixel-accurate wrapping')

if __name__=='__main__':
    main()
