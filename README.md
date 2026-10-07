# DI.fm & AudioAddict to Navidrome Radio Sync

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Navidrome](https://img.shields.io/badge/Navidrome-OpenSubsonic-00bcd4.svg)](https://www.navidrome.org/)
[![Audio Quality](https://img.shields.io/badge/Audio-320kbps%20MP3-blue.svg)](#audio-quality)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A command-line script to import DI.fm and sister network stations (RadioTunes, JazzRadio, RockRadio, ClassicalRadio) into Navidrome or any OpenSubsonic-compatible server using 320 kbps MP3 streams.

It communicates with Navidrome via the Subsonic API, avoiding direct SQLite database modifications.

---

## Supported Networks

| Network | Domain | Channels | Audio Format |
| :--- | :--- | :---: | :--- |
| DI.FM | `di.fm` | 101 | 320 kbps MP3 (`_hi` alias) |
| RadioTunes | `radiotunes.com` | 99 | 320 kbps MP3 (`_hi` alias) |
| ClassicalRadio | `classicalradio.com` | 56 | 320 kbps MP3 |
| JazzRadio | `jazzradio.com` | 44 | 320 kbps MP3 |
| RockRadio | `rockradio.com` | 37 | 320 kbps MP3 |
| **Total** | | **337** | |

---

## Key Behaviors

- **320 kbps MP3 Targets**: AudioAddict serves 128 kbps AAC on DI.FM and RadioTunes by default. The script appends the `_hi` alias to target the 320 kbps MP3 feeds across all channels.
- **In-Place Upgrades**: If stations already exist in Navidrome at lower bitrates, running the script updates their stream URLs without duplicating or re-creating them.
- **Duplicate Prevention**: Queries existing internet radio stations from Navidrome prior to injection, allowing safe re-runs.
- **Dry-Run Option**: Pass `--dry-run` to preview additions or upgrades before committing changes.
- **ICY Metadata**: Streams use standard Icecast headers, passing real-time artist and title information directly to player clients.
- **Environment Variable Auth**: Stores credentials in `.env` to prevent accidental commits to version control.

---

## Requirements

- Python 3.8 or higher
- A running Navidrome or Subsonic-compatible server
- A DI.fm Premium / AudioAddict account and hardware listen key (available at [di.fm/apps/hardware-players](https://www.di.fm/apps/hardware-players))

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/hswilson/DI_x_Navidrome.git
   cd DI_x_Navidrome
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create your configuration:
   ```bash
   cp .env.example .env
   ```

4. Edit `.env` with your instance details:
   ```ini
   NAVIDROME_URL=http://localhost:4533
   NAVIDROME_USER=your_navidrome_username
   NAVIDROME_PASSWORD=your_navidrome_password
   DI_LISTEN_KEY=your_32_character_listen_key
   NETWORKS=di,radiotunes,jazzradio,rockradio,classicalradio
   ```

---

## Usage

### Preview Changes (Dry Run)
```bash
python sync_difm.py --dry-run
```

### Run Live Import
```bash
python sync_difm.py
```

### Sync Selected Networks
```bash
python sync_difm.py --networks di,jazzradio
```

---

## CLI Reference

All options can be passed via command line to override `.env` values:

| Argument | Description | Default |
| :--- | :--- | :--- |
| `--dry-run` | Preview changes without modifying Navidrome | `False` |
| `--networks` | Comma-separated list of networks | All 5 networks |
| `--url` | Base URL of the Navidrome instance | `$NAVIDROME_URL` or `http://localhost:4533` |
| `--user` | Navidrome username | `$NAVIDROME_USER` |
| `--password` | Navidrome password | `$NAVIDROME_PASSWORD` |
| `--listen-key`| 32-character AudioAddict hardware listen key | `$DI_LISTEN_KEY` |

---

## Technical Notes

### How It Works
1. Authenticates against Navidrome using Subsonic salt and MD5 token parameters (`ping.view`).
2. Fetches channel keys from AudioAddict's directory endpoint (`https://listen.{domain}/public3`).
3. Maps sister networks to their respective top-level domains (`di.fm` vs `.com` for sister networks) and selects the 320 kbps Icecast stream URLs on port 80.
4. Reads existing stations using `getInternetRadioStations.view`, adding missing stations via `createInternetRadioStation.view` and upgrading existing URLs via `updateInternetRadioStation.view`.

### Station Organization
The Subsonic radio specification provides a flat list structure without folders or categories. Stations are prefixed with their network name (`DI.FM: ...`, `JazzRadio: ...`) to keep them alphabetically grouped in client applications.

---

## License

This project is licensed under the [MIT License](LICENSE).
