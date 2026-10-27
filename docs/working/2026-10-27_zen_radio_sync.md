# Working Document: Zen Radio Network Support

Date: 2026-10-27
Topic: Adding AudioAddict Zen Radio (zenradio.com) to Navidrome sync

## D1: Zen Radio Stations Missing from Navidrome Sync

### Symptom
Zen Radio stations are not present in Navidrome after running the sync script.

### Evidence
1. Navidrome currently reports 338 internet radio stations, with 0 stations matching `zen` (`len([k for k in stations if 'zen' in k.lower()]) == 0`).
2. `sync_difm.py` defines `NETWORK_CONFIG` covering only 5 networks: `di`, `radiotunes`, `jazzradio`, `rockradio`, and `classicalradio`. Zen Radio is omitted from `NETWORK_CONFIG` and default network lists.
3. AudioAddict operates `zenradio.com` with 39 active channels via `https://listen.zenradio.com/public3` and `https://listen.zenradio.com/premium_high`.
4. Live inspection of Zen Radio premium streams confirms:
   - Stream host: `prem2.zenradio.com:80`
   - Mount format: `zr` + `<channel_key>` (e.g., `zrambient`, `zracousticvocalchillout` - all 39 channels follow this pattern)
   - Codec & Bitrate: `audio/mpeg`, `icy-br: 320` (native 320 kbps MP3, no `_hi` suffix needed)

### Prior Art
- `changelogs/`: None found (directory does not exist).
- `docs/working/`: None found (directory does not exist).
- `git log`: No prior references to Zen Radio or zenradio.com across commit history (initial commit 707ce09 only targeted the initial 5 networks).

### Root Cause
Zen Radio was not included in `NETWORK_CONFIG`, CLI defaults, or configuration templates (`.env.example`, `.env`, `README.md`). Furthermore, `sync_difm.py` currently assumes channel stream URLs always match `/{chan_key}{stream_suffix}`, whereas Zen Radio requires a stream prefix `zr` (`/{stream_prefix}{chan_key}{stream_suffix}`).

### Proposed Fix
1. Update `sync_difm.py`:
   - Add optional `stream_prefix` field to `NETWORK_CONFIG` (defaulting to `""`).
   - Add `zenradio` entry:
     ```python
     "zenradio": {
         "domain": "zenradio.com",
         "display": "ZenRadio",
         "stream_host": "prem2.zenradio.com",
         "stream_prefix": "zr",
         "stream_suffix": "",  # Base stream is already 320 kbps MP3
     },
     ```
   - Update `stream_url` construction in `sync_difm.py`:
     ```python
     stream_prefix = cfg.get("stream_prefix", "")
     stream_url = f"http://{stream_host}:80/{stream_prefix}{chan_key}{stream_suffix}?{di_key}"
     ```
   - Add `zenradio` to the default `--networks` CLI argument list.
2. Update config & documentation:
   - Update `.env.example` and local `.env` `NETWORKS` default to include `zenradio`.
   - Update `README.md` network table and channel totals (+39 channels, bringing total to 376).
   - Run the sync (or preview with `--dry-run`) to import the 39 Zen Radio stations into Navidrome.

### Trade-offs
- **Prefix property vs hardcoded check**: Adding `stream_prefix` to `NETWORK_CONFIG` maintains a clean, table-driven design for existing and future networks without branching logic in the channel loop.
- **Navidrome station naming**: Uses `ZenRadio: <Channel Name>` to keep stations cleanly grouped alongside `DI.FM: ...`, `JazzRadio: ...`, etc.

### Status
Deployed (2026-10-27) - Changelog: changelogs/2026-10-27_2235_zen_radio_sync.md
