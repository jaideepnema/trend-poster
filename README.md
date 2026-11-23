# Trend poster for WordPress

Every hour, a scheduled Claude session (on your Claude plan, so no API key is needed):

1. reads Google Trends' real-time trending list for India and drops anything already covered,
2. picks up to 2 trends that have a real news story behind them,
3. researches each one across at least 2 credible publishers,
4. writes an original 800 to 1,200 word article and makes 1 or 2 infographics from the facts,
5. fact-checks the article against its sources, then saves it to WordPress (as a **draft** by default) with a Sources section.

There's a cap of 8 posts a day so the site never looks mass-produced. The full instructions the session follows are in `PLAYBOOK.md`.

## Files
- `tp/trends.py`: fetches trending searches and filters out covered ones
- `tp/state.py`: remembers covered or skipped trends (`state/covered.json`, committed each run)
- `tp/infographic.py`: renders stat cards, bar charts and timelines as PNGs
- `tp/wp.py`: WordPress REST API (connection check, recent posts, publish with media, tags and sources)

## Settings (cloud environment)
| Name | Example | Notes |
|---|---|---|
| `WP_URL` | `https://example.com` | environment variable |
| `SITE_NAME` | `example.com` | shown on infographics |
| `POST_STATUS` | `draft` | switch to `publish` once you trust the quality |
| WordPress login | Application Password | as a Network secret for your site's host (preferred), or as `WP_USER` and `WP_APP_PASSWORD` variables |

The environment's allowed hosts must include `trends.google.com` and your site's host.
