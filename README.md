# DI.fm & AudioAddict to Navidrome Radio Sync

Script to sync DI.fm and sister network channels (RadioTunes, JazzRadio, RockRadio, ClassicalRadio) directly into Navidrome via the OpenSubsonic API.

## Features

- **Maximum Audio Quality**: Automatically targets AudioAddict's highest quality 320 kbps MP3 streams across all channels.
- **In-Place Upgrades**: Safely updates existing stations to higher quality streams without duplicates.
- **Duplicate Prevention**: Queries existing internet radio stations before adding to avoid duplicate entries.
- **Dry-run Mode**: Preview stations before modifying your Navidrome instance.
- **Multi-network Support**: Covers all AudioAddict sister networks (`di.fm`, `radiotunes.com`, `jazzradio.com`, `rockradio.com`, `classicalradio.com`).
- **Secure**: Keeps credentials in `.env` and masks listen keys in logs.

## Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Fill in your details in `.env`:
   - `NAVIDROME_URL`: Default is `http://localhost:4533` (your Navidrome instance URL).
   - `NAVIDROME_USER`: Your Navidrome admin username.
   - `NAVIDROME_PASSWORD`: Your Navidrome admin password.
   - `DI_LISTEN_KEY`: Your 32-character DI.fm hardware listen key from [di.fm/apps/hardware-players](https://www.di.fm/apps/hardware-players).
   - `NETWORKS`: Comma-separated list of networks (e.g., `di,radiotunes,jazzradio,rockradio,classicalradio`).

## Usage

### 1. Dry Run (Preview)
```bash
python sync_difm.py --dry-run
```

### 2. Live Sync
```bash
python sync_difm.py
```

### 3. Sync Specific Networks
```bash
python sync_difm.py --networks di
python sync_difm.py --networks di,jazzradio
```
