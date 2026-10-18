#!/usr/bin/env python3
"""Post one existing HarmonyLabs PNG + its caption/hashtags to each Buffer channel.

No paid AI API. Uses only Python standard library and Buffer's Free API.
When run by GitHub Actions each day, sends one post/channel into Buffer's queue.
Public GitHub raw links supply media to Buffer; a private repository needs a
public MEDIA_BASE_URL host (Cloudinary etc.). Never put API keys in this file.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from urllib import request, error, parse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
CAPTIONS = ROOT / 'output' / 'captions.csv'
STATE = ROOT / 'state' / 'posting_history.json'
API_ENDPOINT = 'https://api.buffer.com'
TZ = ZoneInfo('Pacific/Auckland')
# This deliberately selects only social accounts with HarmonyLabs/Harmony in the display name.
# Override using BUFFER_CHANNEL_IDS if your account uses a different display name.
NAME_FILTER = os.getenv('CHANNEL_NAME_FILTER', 'harmony').casefold()


class PostingError(RuntimeError):
    pass


def read_posts():
    with CAPTIONS.open('r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise PostingError('No ad captions found: output/captions.csv')
    days = [int(row['Day']) for row in rows]
    if days != list(range(1, len(rows)+1)):
        raise PostingError('Captions must have sequential Day values starting at 1.')
    for row in rows:
        if not (ROOT/'output'/row['Image']).is_file():
            raise PostingError(f'Missing ad image: {row["Image"]}')
        if not row['Caption'].strip():
            raise PostingError(f'Day {row["Day"]} has no caption.')
    return rows


def load_state():
    if not STATE.is_file():
        return {'channels': {}}
    state = json.loads(STATE.read_text('utf-8'))
    if not isinstance(state.get('channels'), dict):
        raise PostingError('Invalid state/posting_history.json')
    return state


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    tmp.replace(STATE)


def graphql(query: str, api_key: str):
    payload = json.dumps({'query':query}, ensure_ascii=False).encode('utf-8')
    req = request.Request(API_ENDPOINT, data=payload, headers={
        'Content-Type':'application/json', 'Authorization': f'Bearer {api_key}',
        'User-Agent': 'HarmonyLabs-Free-Daily-AutoPost/1.0'}, method='POST')
    try:
        with request.urlopen(req, timeout=30) as res:
            response = json.load(res)
    except error.HTTPError as exc:
        # Do not print the Authorization header or API key.
        raise PostingError(f'Buffer API HTTP {exc.code}: check the API key and quotas.') from exc
    except error.URLError as exc:
        raise PostingError(f'Buffer is unreachable: {exc.reason}') from exc
    if response.get('errors'):
        messages='; '.join(x.get('message','GraphQL error') for x in response['errors'])
        raise PostingError(f'Buffer GraphQL: {messages}')
    return response.get('data') or {}


def discover_channels(api_key):
    accounts = graphql('query { account { organizations { id name } } }', api_key)
    orgs = ((accounts.get('account') or {}).get('organizations') or [])
    if not orgs:
        raise PostingError('No Buffer organization found. Connect your social channels in Buffer first.')
    channels=[]
    for org in orgs:
        org_id=json.dumps(org['id'])
        data=graphql('query { channels(input: { organizationId: '+org_id+' }) { id name displayName service isQueuePaused } }',api_key)
        for channel in data.get('channels') or []:
            if channel['id'] not in {x['id'] for x in channels}:
                channels.append(channel)
    return channels


def select_channels(channels):
    selected_ids = [x.strip() for x in os.getenv('BUFFER_CHANNEL_IDS','').split(',') if x.strip()]
    if selected_ids:
        found = {c['id']:c for c in channels}
        missing = [i for i in selected_ids if i not in found]
        if missing:
            raise PostingError('BUFFER_CHANNEL_IDS contains IDs not found in your connected Buffer channels.')
        selected = [found[x] for x in selected_ids]
    else:
        selected = [c for c in channels if NAME_FILTER in (' '.join(str(c.get(k) or '') for k in ('name','displayName'))).casefold()]
    if not selected:
        names=', '.join(f'{c.get("service")}: {c.get("displayName") or c.get("name")}' for c in channels)
        raise PostingError('No HarmonyLabs channels were selected! Connected: '+names+'. Rename your accounts to contain HarmonyLabs, or set the optional BUFFER_CHANNEL_IDS secret.')
    paused = [c.get('displayName') or c['id'] for c in selected if c.get('isQueuePaused')]
    if paused:
        raise PostingError('Buffer queue is paused for: '+', '.join(paused)+'. Resume it before posting.')
    return selected


def media_url(image_name: str):
    # Trusted image names always come from validated local CSV, never user-provided URL.
    if Path(image_name).name != image_name or not image_name.lower().endswith('.png'):
        raise PostingError('Image filename in CSV must be a plain PNG filename.')
    custom = os.getenv('MEDIA_BASE_URL','').strip()
    if custom:
        if not custom.startswith('https://'):
            raise PostingError('MEDIA_BASE_URL must start with https://')
        return custom.rstrip('/') + '/' + parse.quote(image_name)
    repo = os.getenv('GITHUB_REPOSITORY','')
    branch = os.getenv('GITHUB_REF_NAME','main')
    if not repo or '/' not in repo:
        raise PostingError('No GITHUB_REPOSITORY found; run this through GitHub Actions or set MEDIA_BASE_URL.')
    return f'https://raw.githubusercontent.com/{repo}/{parse.quote(branch,safe="")}/output/{parse.quote(image_name)}'


def check_public_url(url: str):
    req=request.Request(url, method='GET', headers={'User-Agent':'HarmonyLabs-AdPoster/1.0', 'Range':'bytes=0-99'})
    try:
        with request.urlopen(req, timeout=25) as resp:
            ct=resp.headers.get('Content-Type','')
            if 'image/' not in ct and 'application/octet-stream' not in ct:
                raise PostingError('Public image URL did not return an image; got '+ct)
    except (error.HTTPError,error.URLError) as exc:
        raise PostingError('Cannot fetch public image URL: '+url+' (confirm your repo is PUBLIC and PNGs were uploaded)') from exc


def make_mutation(channel_id, text, url):
    # json.dumps creates valid quoted GraphQL string literals with escaping.
    channel_json=json.dumps(channel_id,ensure_ascii=False)
    text_json=json.dumps(text,ensure_ascii=False)
    url_json=json.dumps(url,ensure_ascii=False)
    return ("""mutation { createPost(input: {
        text: %s
        channelId: %s
        schedulingType: automatic
        mode: addToQueue
        assets: [{ image: { url: %s } }]
    }) {
        __typename
        ... on PostActionSuccess { post { id dueAt text } }
        ... on MutationError { message }
    } }""" % (text_json,channel_json,url_json))


def create_post(api_key, channel, row, url):
    text = row['Caption'].strip()+'\n\n'+row['Hashtags'].strip()
    result = graphql(make_mutation(channel['id'],text,url),api_key).get('createPost')
    if not result:
        raise PostingError('Buffer returned no createPost result')
    if result.get('__typename') == 'MutationError' or result.get('message'):
        raise PostingError('Buffer refused post: '+str(result.get('message','unknown error')))
    if result.get('__typename') != 'PostActionSuccess' or not result.get('post',{}).get('id'):
        raise PostingError('Unexpected response from Buffer: '+str(result.get('__typename')))
    return result['post']


def run(dry_run=False, date_override=None):
    now = datetime.now(TZ)
    today = date_override or now.date().isoformat()
    posts = read_posts()
    state = load_state()
    key = os.getenv('BUFFER_API_KEY','').strip()
    if not dry_run and not key:
        raise PostingError('Missing BUFFER_API_KEY. Create this secret under GitHub repository Settings > Secrets and variables > Actions.')
    if dry_run:
        print('DRY RUN: no API calls, no posts, no state changes')
        channels=[{'id':'example','displayName':'HarmonyLabs demo','service':'instagram'}]
    else:
        channels=select_channels(discover_channels(key))
    errors=[]
    checked_images=set()
    for channel in channels:
        cid = str(channel['id'])
        name = channel.get('displayName') or channel.get('name') or cid
        chstate = state['channels'].setdefault(cid, {'next_day':1,'last_queued_date':'','history':[]})
        if chstate.get('last_queued_date') == today:
            print(f'Already queued for {name} on {today}; skipping duplicate')
            continue
        number=int(chstate.get('next_day',1))
        if number < 1 or number > len(posts):
            number=1
        row=posts[number-1]
        try:
            url = media_url(row['Image']) if not dry_run else 'https://example.com/output/'+row['Image']
            print(f'{name}: day {number}/{len(posts)} -> {row["Image"]}')
            if dry_run:
                print('  Caption: '+row['Caption'])
                print('  Hashtags: '+row['Hashtags'])
                print('  No upload performed.')
                continue
            if url not in checked_images:
                check_public_url(url)
                checked_images.add(url)
            posted=create_post(key,channel,row,url)
            chstate['next_day']=1 if number==len(posts) else number+1
            chstate['last_queued_date']=today
            history=chstate.setdefault('history',[])
            history.append({'date':today, 'day':number, 'image':row['Image'], 'buffer_post_id':posted['id'], 'due_at':posted.get('dueAt')})
            chstate['history']=history[-90:]
            save_state(state)  # checkpoint successful channels even if a later channel fails
            print(f'  Queued successfully. Buffer post ID {posted["id"]}; scheduled {posted.get("dueAt") or "next queue slot"}')
        except PostingError as exc:
            errors.append(f'{name}: {exc}')
            print('ERROR '+errors[-1],file=sys.stderr)
    if errors:
        raise PostingError(str(len(errors))+' channel(s) failed; successful channels were saved to posting history')
    return state


def main():
    parser=argparse.ArgumentParser(description='Auto-queue one HarmonyLabs ad per Buffer channel each day')
    parser.add_argument('--dry-run',action='store_true',help='Preview without API calls or state changes')
    args=parser.parse_args()
    try:
        run(dry_run=args.dry_run)
    except PostingError as exc:
        print('POSTING ERROR: '+str(exc),file=sys.stderr)
        sys.exit(1)

if __name__=='__main__':
    main()
