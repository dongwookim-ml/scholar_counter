# Scholar Citation Tracker

Tracks the citation counts on a Google Scholar profile over time and serves a
dashboard of the history: totals, per-paper trends, and change between snapshots.

Data is refreshed automatically once a day. The dashboard reads from a local
SQLite database, so it stays fast as the history grows.

## Install

```bash
pip install -e ".[dev]"
```

Python 3.11 or newer. The only runtime dependencies are Flask, requests, and
BeautifulSoup.

## Run

```bash
scholar-counter serve
```

Then open <http://127.0.0.1:8080>. Other commands:

| Command | Purpose |
| --- | --- |
| `scholar-counter serve` | Run the dashboard (default command) |
| `scholar-counter update` | Fetch the profile once and store a snapshot |
| `scholar-counter status` | Print what is currently stored |
| `scholar-counter migrate` | Import legacy `history/*.pkl` files |

Every command also works as `python -m scholar_counter.cli <command>`.

## Automatic updates

`serve` starts a background thread that scrapes the profile once a day at
`SCHOLAR_UPDATE_HOUR` (03:00 by default). Two details make this reliable on a
laptop rather than a server:

- **Catch-up on start.** If the newest snapshot is older than
  `SCHOLAR_STALE_AFTER_HOURS`, an update runs immediately. A machine that was
  asleep at 03:00 refreshes when it wakes instead of waiting another day.
- **One update at a time.** The scheduled run and the *Update now* button share
  a lock, so they can never scrape concurrently.
- **Back off, don't skip.** Google Scholar rate-limits automated clients
  routinely, answering `429` with a bot-check page. A failed run retries after
  `SCHOLAR_RETRY_AFTER_MINUTES` rather than waiting for the next daily slot.
  Failed scrapes never write a snapshot, so the history has no bogus points.

The dashboard header shows when the next automatic update is due.

To drive updates from cron or launchd instead, set `SCHOLAR_AUTO_UPDATE=0` and
schedule `scholar-counter update`.

## Configuration

All settings come from the environment; there is no config file to edit.

| Variable | Default | Meaning |
| --- | --- | --- |
| `SCHOLAR_USER_ID` | `RkspD6IAAAAJ` | Google Scholar profile id |
| `SCHOLAR_HOST` | `127.0.0.1` | Bind address |
| `SCHOLAR_PORT` | `8080` | Port |
| `SCHOLAR_DEBUG` | `0` | Flask debug mode |
| `SCHOLAR_DATABASE` | `./scholar.db` | SQLite file |
| `SCHOLAR_AUTO_UPDATE` | `1` | Enable the daily scheduler |
| `SCHOLAR_UPDATE_HOUR` | `3` | Hour of the daily update (0–23, local time) |
| `SCHOLAR_UPDATE_MINUTE` | `0` | Minute of the daily update |
| `SCHOLAR_STALE_AFTER_HOURS` | `24` | Age at which startup triggers a catch-up |
| `SCHOLAR_RETRY_AFTER_MINUTES` | `60` | Delay before retrying a failed update |
| `SCHOLAR_TIMEOUT` | `30` | HTTP timeout in seconds |
| `SCHOLAR_USER_AGENT` | Chrome UA | Request user agent |

`SCHOLAR_HOST` defaults to localhost deliberately. The app has no
authentication and its update endpoint triggers outbound scraping, so bind it
to `0.0.0.0` only on a trusted network, and never together with
`SCHOLAR_DEBUG=1` — that combination exposes the Werkzeug debugger.

## Running at login

### macOS (launchd)

```bash
cp com.scholar-citation-tracker.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.scholar-citation-tracker.plist
```

The plist in this repository is generated for this checkout's paths and Python
interpreter. Edit those strings if either changes. To apply a code change:

```bash
launchctl unload ~/Library/LaunchAgents/com.scholar-citation-tracker.plist
launchctl load ~/Library/LaunchAgents/com.scholar-citation-tracker.plist
```

Logs land in `logs/scholar-tracker.log` and `logs/scholar-tracker-error.log`.

### Linux (systemd)

Edit the paths and username in `scholar-citation-tracker.service`, then:

```bash
sudo cp scholar-citation-tracker.service /etc/systemd/system/
sudo systemctl enable --now scholar-citation-tracker
```

### Windows

Run `start_scholar_tracker.bat`, or point Task Scheduler at it with an
"at log on" trigger.

## API

| Endpoint | Returns |
| --- | --- |
| `GET /` | Dashboard |
| `GET /api/summary` | Totals, recent change, top papers |
| `GET /api/trends?granularity=…` | Total-citation series and change, bucketed |
| `GET /api/papers` | Every paper with its trend |
| `GET /api/paper?title=…` | One paper's detail |
| `GET /api/analytics` | Aggregate metrics |
| `GET /api/status` | Snapshot count, last update, next scheduled update |
| `GET /api/export/citations.csv` | History as CSV |
| `GET /api/export/papers.csv` | Per-paper history as CSV |
| `POST /api/update` | Scrape now |

Endpoints return `404` with an `{"error": …}` body when no data has been
collected yet, and `POST /api/update` returns `503` when a scrape fails.

## Chart granularity

The trend chart groups snapshots into calendar buckets: `daily`, `monthly`, or
`yearly`. Because scrapes are irregular, each bucket is represented by its
*last* snapshot, and the change shown is the movement since the previous
bucket. A bucket with no snapshots is absent rather than zero, so a gap is
visible instead of being drawn as a flat stretch.

The dashboard remembers the selected view. To query directly:

```bash
curl 'http://127.0.0.1:8080/api/trends?granularity=monthly'
```

## Storage

Everything lives in `scholar.db`:

```sql
snapshot(id, captured_at)
citation(snapshot_id, title, citations)
```

Change between snapshots is derived in SQL rather than stored, so it cannot
drift from the totals.

### Migrating from the pickle layout

Earlier versions wrote one pickle per snapshot into `history/` and one CSV of
changes into `difference/`. To import them:

```bash
scholar-counter migrate
```

`migrate` only reads those folders, so they remain a backup. It is idempotent,
keyed on each file's timestamp, so re-running it will not duplicate snapshots.

Two things changed in the process, both of which fix real bugs:

- **Change is now computed from totals.** The old CSVs summed per-paper
  increases among papers *currently* on the profile. When Scholar merged or
  dropped an entry, those citations vanished from the total but not from the
  reported growth. On 2026-05-18 the old code reported `+80` while the total
  actually moved `+46`, because a 34-citation entry had been merged away.
- **Titles containing commas survive.** The old CSVs were written with a bare
  `"%s, %s"` format, so any comma in a title corrupted the row.

## Development

```bash
pytest        # 80 tests, no network access
ruff check .
ruff format .
```

`.claude/launch.json` defines a dev server on port 8090 with auto-update off,
so it can run alongside an installed service on 8080.
