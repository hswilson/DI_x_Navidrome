# Changelog: 2026-10-27 22:55 - AudioAddict Station Artwork Sync

## Part 1: Importer Core (`sync_difm.py`)

- **Issue**: Internet radio stations displayed generic blue vinyl disc placeholder icons in Navidrome because the Subsonic API does not support artwork parameters.
- **Previous State**: Stations were created via Subsonic API only, with no cover artwork attached. `public3` was queried without channel image metadata.
- **Fix Applied**:
  - Implemented `extract_channel_image_url` to parse and format 300x300 PNG image URLs from AudioAddict API metadata.
  - Updated `fetch_network_channels` to fetch the curated channel catalog and enrich each channel with CDN image URLs from `api.audioaddict.com/v1/{net}/channels`.
  - Added native Navidrome authentication via `get_navidrome_jwt` (`POST /auth/login`).
  - Added `upload_station_artwork` to download the channel PNG from AudioAddict's CDN and upload to Navidrome's native `POST /api/radio/{station_id}/image` multipart endpoint.
  - Integrated artwork checks into the main loop (uploading missing artwork automatically, with `--no-artwork` and `--force-artwork` CLI switches).
- **Rationale**: Navidrome natively supports radio station artwork via its `/api/radio/{id}/image` endpoint and assigns Subsonic-compatible `coverArt` IDs (`ra-<id>_<hash>`) so that all web UI and Subsonic clients display official station branding.
- **Relevant working docs**: [docs/working/2026-10-27_station_artwork_sync.md](file:///z:/Coding/DI_x_Navidrome/docs/working/2026-10-27_station_artwork_sync.md)
- **Files / symbols touched**:
  - `sync_difm.py` (`extract_channel_image_url`, `fetch_network_channels`, `get_navidrome_jwt`, `upload_station_artwork`, `main`)
- **Symptom keywords**: radio artwork, coverArt, station thumbnail, vinyl disc placeholder, /api/radio/{id}/image, audioaddict cdn

## Part 2: Documentation (`README.md`)

- **Issue**: Documentation did not mention artwork synchronization capabilities or CLI options.
- **Previous State**: `README.md` described stream URL syncing only.
- **Fix Applied**:
  - Added official station artwork bullet to Key Behaviors.
  - Added `--no-artwork` and `--force-artwork` flags to CLI Reference table.
- **Rationale**: Keeps user documentation aligned with the new capabilities.
- **Relevant working docs**: [docs/working/2026-10-27_station_artwork_sync.md](file:///z:/Coding/DI_x_Navidrome/docs/working/2026-10-27_station_artwork_sync.md)
- **Files / symbols touched**:
  - `README.md` (`Key Behaviors`, `CLI Reference`)
- **Symptom keywords**: artwork docs, --no-artwork, --force-artwork
