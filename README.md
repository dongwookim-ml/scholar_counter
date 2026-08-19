# Scholar Citation Tracker

Tracks the citation counts on a Google Scholar profile over time and publishes
a dashboard of the history: totals, per-paper trends, and change between
snapshots.

**Dashboard: <https://dongwookim-ml.github.io/scholar_counter/>**

A GitHub Actions workflow scrapes the profile once a day, commits the snapshot
to this repository, and redeploys the dashboard. No machine of yours needs to
be running.

## How it works

```
GitHub Actions (daily)
  └─ scrape profile ─→ data/snapshots/YYYYMMDDTHHMMSS.json ─→ commit
                                   │
                                   └─→ build static site ─→ GitHub Pages
```

`data/snapshots/` is the source of truth: one small JSON file per scrape,
committed to the repo so the history survives the ephemeral runner. Keys are
sorted, so a day's diff shows exactly which papers moved.

`scholar.db` is a **derived cache**, rebuilt from those JSON files whenever the
two disagree. It is never committed. Aggregation runs in SQL, which is why the
dashboard stays fast as the history grows.

## Local use

```bash
pip install -e ".[dev]"
scholar-counter serve
```

Then open <http://127.0.0.1:8080>. On a fresh clone the cache is built
automatically from the committed JSON.

| Command | Purpose |
| --- | --- |
| `scholar-counter serve` | Run the dashboard locally (default command) |
| `scholar-counter build` | Generate the static site into `site/` |
| `scholar-counter update` | Scrape once and record a snapshot |
| `scholar-counter status` | Print what is currently stored |
| `scholar-counter sync` | Force-rebuild the cache from JSON |
| `scholar-counter export` | Write the cache back out as JSON |

Every command also works as `python -m scholar_counter.cli <command>`.

Local scraping is **off by default** — GitHub owns the daily crawl, and a
second scheduler would write competing snapshots. Set `SCHOLAR_AUTO_UPDATE=1`
if you want a local instance to scrape as well.

## The daily workflow

`.github/workflows/daily-update.yml` runs at 18:00 UTC (03:00 KST) and on
demand from the Actions tab. It:

1. Scrapes the profile, retrying up to three times two minutes apart, because
   Google rate-limits automated clients intermittently.
2. Commits the new snapshot, and skips the commit when nothing changed.
3. Rebuilds the static site and deploys it to Pages.

A scrape that fails every attempt fails the workflow rather than committing
anything, so the history never gains a bogus point and you get a notification.
Pushes that touch `scholar_counter/**` redeploy the site without scraping.

## Configuration

All settings come from the environment; there is no config file to edit.

| Variable | Default | Meaning |
| --- | --- | --- |
| `SCHOLAR_USER_ID` | `RkspD6IAAAAJ` | Google Scholar profile id |
| `SCHOLAR_HOST` | `127.0.0.1` | Bind address |
| `SCHOLAR_PORT` | `8080` | Port |
| `SCHOLAR_DEBUG` | `0` | Flask debug mode |
| `SCHOLAR_DATA_DIR` | `./data/snapshots` | Committed JSON snapshots |
| `SCHOLAR_DATABASE` | `./scholar.db` | Derived SQLite cache |
| `SCHOLAR_AUTO_UPDATE` | `0` | Enable the local daily scheduler |
| `SCHOLAR_UPDATE_HOUR` | `3` | Hour of the local scheduled update |
| `SCHOLAR_UPDATE_MINUTE` | `0` | Minute of the local scheduled update |
| `SCHOLAR_STALE_AFTER_HOURS` | `24` | Age at which startup triggers a catch-up |
| `SCHOLAR_RETRY_AFTER_MINUTES` | `60` | Delay before retrying a failed update |
| `SCHOLAR_TIMEOUT` | `30` | HTTP timeout in seconds |
| `SCHOLAR_USER_AGENT` | Chrome UA | Request user agent |

`SCHOLAR_HOST` defaults to localhost deliberately. The app has no
authentication and its update endpoint triggers outbound scraping, so bind it
to `0.0.0.0` only on a trusted network, and never together with
`SCHOLAR_DEBUG=1` — that combination exposes the Werkzeug debugger.

## Chart granularity

The trend chart groups snapshots into calendar buckets: `daily`, `monthly`, or
`yearly`. Because scrapes are irregular, each bucket is represented by its
*last* snapshot, and the change shown is the movement since the previous
bucket. A bucket with no snapshots is absent rather than zero, so a gap is
visible instead of being drawn as a flat stretch.

## API

The Flask server exposes these; the static build writes each one to a file
under `api/` so the published dashboard needs no backend.

| Endpoint | Static file | Returns |
| --- | --- | --- |
| `GET /api/summary` | `api/summary.json` | Totals, recent change, top papers |
| `GET /api/trends?granularity=…` | `api/trends/<g>.json` | Totals and change, bucketed |
| `GET /api/papers` | `api/papers.json` | Every paper with its trend |
| `GET /api/analytics` | `api/analytics.json` | Aggregate metrics |
| `GET /api/status` | `api/status.json` | Snapshot count and last update |
| `GET /api/export/citations.csv` | same path | History as CSV |
| `GET /api/export/papers.csv` | same path | Per-paper history as CSV |
| `GET /api/paper?title=…` | — | One paper's detail (server only) |
| `POST /api/update` | — | Scrape now (server only) |

The static files are generated by calling these endpoints through Flask's test
client, so the published site cannot drift from the live API.

## Development

```bash
pytest        # 105 tests, no network access
ruff check .
ruff format .
```

CI runs both on Python 3.11 and 3.12.

`.claude/launch.json` defines two preview servers: `scholar-dev` (Flask on
8090) and `pages-preview` (the built static site on 8099).

## History

Earlier versions stored one pickle per snapshot in `history/` and one CSV of
changes in `difference/`, and ran as a launchd service on a Mac. Those folders
are gitignored and remain untouched as a backup; `scholar-counter migrate`
imports them. Two bugs were fixed in the move:

- **Change ignored removed papers.** The old CSVs summed per-paper increases
  among papers *currently* listed. When Scholar merged an entry away, its
  citations left the total but not the reported growth — on 2026-05-18 that
  read `+80` against a real `+46`. Change is now derived from totals.
- **Titles containing commas corrupted the CSV**, which was written with a bare
  `"%s, %s"` format.
