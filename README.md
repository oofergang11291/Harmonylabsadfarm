# HarmonyLabs Ad Farm v3: zero-cost daily auto-poster

**START HERE:** Read [AUTO_POST_SETUP.md](AUTO_POST_SETUP.md). It has the precise free Buffer + GitHub setup process.

No daily caption copy/paste. GitHub Actions queues one predesigned HarmonyLabs image with the matching caption and hashtags each morning; Buffer publishes at the time you set.

Files:
- `auto_post.py` — daily Buffer API publisher (Python 3.10+, standard library only).
- `.github/workflows/daily-post.yml` — free GitHub Actions daily scheduler.
- `state/posting_history.json` — records posts/avoids same-day repeats.
- `show_channels.py` and `RUN_CHANNEL_SETUP.bat` — optional account ID finder.
- `output/ad_01.png` through `output/ad_30.png`, `output/captions.csv` — original v2 ads + copy.
- `generate_ads.py`, `content/posts.csv`, `RUN_GENERATOR.bat` — original offline ad generator; requires Pillow if regenerating.

This schedules your existing 30 ads and cycles through them. It does NOT programmatically generate fresh ChatGPT content indefinitely, which would need an additional model API/provider.
