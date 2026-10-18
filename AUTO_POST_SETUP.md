# HarmonyLabs v3 — truly automatic $0 daily posting

**You no longer copy and paste any captions or images.** This folder contains the same 30 HarmonyLabs PNGs and matching captions as v2. A scheduled GitHub Action automatically retrieves the next image and caption, sends them to Buffer, and Buffer publishes at your selected time. **The workflow queues one post per connected HarmonyLabs channel, per day.**

## One-time setup (Windows, no coding required)

1. **Buffer:** Sign up for a free account at https://buffer.com, connect up to three HarmonyLabs social profiles (Instagram, TikTok, Facebook Page). Give the profiles names containing `HarmonyLabs` or `Harmony` (for example `harmonylabs.online`), so this package selects the right accounts automatically. **Do not connect unrelated accounts unless you intend to exclude them by name.**
2. **Set Buffer posting times:** In Buffer, select EACH connected channel > Settings (gear icon) > Posting Schedule. Set timezone `Pacific/Auckland` and **one** recurring posting slot every day (example: **6:00 PM**). Ensure the queue is not paused and use Automatic Publishing where supported. Turn off default "Notify Me" mode. This avoids multiple posts per day and puts each daily generated entry into the next slot.
3. **Get your Buffer API key:** In your Buffer account go to **Settings > API**, create a **personal API key**. Keep it secret; **never put the key inside CSV, Python, repository files or a screenshot**. Buffer Free currently offers one API key and 3,000 requests per 30 days.
4. **Publish this folder to GitHub:** Create a free GitHub account, install [GitHub Desktop](https://desktop.github.com/). Extract this ZIP; in GitHub Desktop choose **File > Add local repository**, select the extracted `HarmonyLabs_Ad_Farm_v3_AUTOMATIC` folder, and choose **Create a repository here** if prompted. Commit the initial files and click **Publish repository**. **Uncheck `Keep this code private`**, so that the images are accessible to Buffer. (The images and captions become public, but the API key stays secret.) The repository should include `.github/workflows/daily-post.yml`, all 30 PNGs, `output/captions.csv`, and `auto_post.py`.
5. **Add the secret:** On GitHub, open your repo > **Settings > Secrets and variables > Actions > New repository secret**. Secret name exactly `BUFFER_API_KEY`; value is your Buffer personal API key. Do not set it in source code. You don't need to provide channel IDs if the social profile names contain Harmony.
6. **Try it once:** Open GitHub repository > **Actions** > **Daily HarmonyLabs Ads** > **Run workflow**. Check the run log and Buffer **Queue**. It should add `ad_01.png` with its exact matching caption/hashtags to the next available time slot on each selected channel. If no HarmonyLabs channel is found, see "Optional channel selection" below.
7. **Done:** It runs every day at **9:13 AM Pacific/Auckland**, using GitHub's timezone-aware scheduler (handles NZ daylight savings). Buffer publishes at the one daily slot you set. Your PC can be switched off. The next day it sends `ad_02.png`, and so on.

**Important:** These are 30 ALREADY GENERATED posts. This package automates sending them and their captions; it does **not** call a free unlimited ChatGPT API to create fresh AI designs each day. After day 30, it cycles to day 1. Review posts and supply fresh posts occasionally to avoid repetitive content. There are no API charges from OpenAI.

## Optional channel selection (if profiles aren't called HarmonyLabs)

On Windows, double-click `RUN_CHANNEL_SETUP.bat` with Python installed, paste the Buffer API key when prompted (typing is hidden). It displays the connected account names and channel IDs, **without saving your key**. In your GitHub repository's **Settings > Secrets and variables > Actions**, create a second secret called `BUFFER_CHANNEL_IDS` containing *only* desired channel IDs separated by commas, e.g. `abc123,def456`. It overrides the profile name filter. Never include personal or unrelated account IDs.

## Stopping or fixing the automation

- **To stop:** GitHub > Actions > Daily HarmonyLabs Ads > `...` > Disable workflow (or remove the API secret).
- **To test without posting:** Run `py auto_post.py --dry-run` locally to preview the next selected ad. Dry-run does not contact Buffer or publish anything.
- **To change captions:** Edit `content/posts.csv`, then run `RUN_GENERATOR.bat` to regenerate `output/captions.csv` and PNGs. Commit/push changes in GitHub Desktop to update your live schedule. Editing `output/captions.csv` by itself is overwritten by regenerate.
- **To add new posts:** Add more sequential rows to `content/posts.csv`, regenerate the ads, and commit/push all changed files. This script reads however many rows exist, not just 30.
- **If workflow fails:** GitHub > Actions > select latest run > view error. Most failures are private image URLs, paused Buffer queues, wrong API key, or different profile names.
- **If repo must be private:** Host the PNGs separately on a public stable HTTPS image host and provide a `MEDIA_BASE_URL` Actions secret pointing to the directory containing `ad_01.png` etc. The image URL itself still has to be PUBLIC. Private Github repo raw image links do not work with Buffer.
- **Avoid duplicates:** The automation commits `state/posting_history.json` after queueing. Running it a second time on the same New Zealand date skips channels already queued. State is stored by channel, so partial failures only retry channels that failed.

## Platform limitations and costs

- Buffer Free: up to **3 channels**, **10 pending posts per channel**; the automation adds a new post each day so you never need to refill manually. Keep queue at <= 9 pending posts if testing. Buffer API Free: **3,000 calls / 30 days** (at 1–3 connected channels, our calls are far below this limit).
- Buffer itself has platform-specific publishing restrictions; some TikTok music/effects or special features require a **Notify Me** manual confirmation. These are plain single-image ads, which Buffer supports for TikTok, but confirm the first post publishes automatically for each account. Instagram typically requires a professional/eligible account for auto-publishing.
- GitHub Actions schedule delivery can be delayed or sometimes skipped during high load, so treat it as reliable for routine posting, not a hard real-time SLA. Future runs will still continue the sequence.
- GitHub public repositories and GitHub Actions have free usage subject to published terms and limits. No ChatGPT/OpenAI paid API is used.
- The ads and any captions uploaded to a PUBLIC repository are visible to everyone. Your API key must be in GitHub **Secrets**, never in source files.

**Documentation:** https://developers.buffer.com/examples/create-image-post.html · https://developers.buffer.com/examples/get-channels.html · https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
