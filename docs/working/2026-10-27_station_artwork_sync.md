# Working Document: AudioAddict Station Artwork Sync

Date: 2026-10-27
Topic: Automated Sync of Official AudioAddict Channel Artwork into Navidrome

## D2: AudioAddict Channel Thumbnails / Cover Art Sync into Navidrome

### Symptom
All internet radio stations in Navidrome currently display generic blue vinyl disc placeholder icons instead of official station artwork/logos.

### Evidence
1. Navidrome's Subsonic endpoint (`getInternetRadioStations.view`) returns stations with empty `coverArt` fields (`'coverArt': ''`).
2. AudioAddict provides high-resolution channel thumbnails across all 6 networks via `https://api.audioaddict.com/v1/{net}/channels`, returning CDN template URLs (e.g. `https://cdn-images.audioaddict.com/...png?size=300x300`).
3. While the legacy Subsonic API (`createInternetRadioStation.view`) does not support image uploads, Navidrome exposes a native REST endpoint:
   - `POST /api/radio/{id}/image` accepting multipart form uploads (`files={'image': ('cover.png', bytes, 'image/png')}`).
4. Verified with live API test on `DI.FM: 00s Club Hits` (`vmtKouJZaKAYMpwOEHbcdk`):
   - Uploading official channel image returned HTTP 200 (`{"status": "ok"}`).
   - Navidrome automatically generated and assigned `coverArt: 'ra-vmtKouJZaKAYMpwOEHbcdk_6ae129d9'`.
   - The station now has official artwork in Navidrome web UI and all OpenSubsonic clients.

### Prior Art
- `changelogs/`: None found regarding artwork or cover art.
- `docs/working/`: `docs/working/2026-10-27_zen_radio_sync.md` addressed adding Zen Radio network streams.
- `git log`: No previous attempts or mentions of artwork synchronization.

### Root Cause
`sync_difm.py` previously fetched channels from `https://listen.{domain}/public3` (which only provides channel key and name without image metadata) and only used the Subsonic API endpoint `createInternetRadioStation.view` (which cannot attach artwork).

### Proposed Fix
1. Update `sync_difm.py`:
   - Switch primary channel discovery to `https://api.audioaddict.com/v1/{net}/channels` (with fallback to `https://listen.{domain}/public3`).
   - Extract channel image URL (`images.get('default')` or `asset_url`, appending `?size=300x300`).
   - Add native Navidrome authentication helper (`login_navidrome_native`) calling `/auth/login` to obtain an `x-nd-authorization` Bearer token.
   - Add artwork synchronization routine:
     - For stations missing `coverArt` (or when `--force-artwork` is passed), fetch image bytes from AudioAddict CDN and upload via `POST /api/radio/{station_id}/image`.
   - Add CLI options:
     - `--sync-artwork` (enabled by default; pass `--no-artwork` to skip).
     - `--force-artwork` (re-upload images even if `coverArt` is already set).
2. Update documentation and `.env.example`:
   - Document artwork sync behavior in `README.md`.
3. Execution:
   - Run live sync to populate artwork for all 376 stations in Navidrome.

### Trade-offs
- **API calls & Network traffic**: Uploading 376 images (~50-150 KB each) will take approximately 15-30 seconds during the initial run. To prevent overhead on repeated runs, the script checks if `coverArt` is already populated in Navidrome and skips existing images unless `--force-artwork` is explicitly specified.
- **Native API vs Subsonic**: Requires logging into Navidrome's `/auth/login` endpoint with the existing `NAVIDROME_USER` and `NAVIDROME_PASSWORD`. No extra credentials or configuration required.

### Status
Deployed (2026-10-27) - Changelog: changelogs/2026-10-27_2255_station_artwork_sync.md
