# 📻 DI.fm & AudioAddict to Navidrome Radio Sync

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Navidrome](https://img.shields.io/badge/Navidrome-OpenSubsonic-00bcd4.svg)](https://www.navidrome.org/)
[![Audio Quality](https://img.shields.io/badge/Audio-320kbps%20MP3-brightgreen.svg)](#audio-quality)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A lightweight CLI tool to automatically sync **300+ DI.fm and AudioAddict sister network stations** directly into **Navidrome** (or any OpenSubsonic server) in pristine **320 kbps MP3** audio quality.

No manual database editing, no risk of SQLite file locks, and no clicking through hundreds of stations by hand.

---

## 🌟 Supported Networks (337 Channels Total)

| Network | Domain | Channels | Audio Quality |
| :--- | :--- | :---: | :--- |
| **DI.FM** | `di.fm` | 101 | 🚀 **320 kbps MP3** (`_hi`) |
| **RadioTunes** | `radiotunes.com` | 99 | 🚀 **320 kbps MP3** (`_hi`) |
| **ClassicalRadio** | `classicalradio.com` | 56 | 🚀 **320 kbps MP3** |
| **JazzRadio** | `jazzradio.com` | 44 | 🚀 **320 kbps MP3** |
| **RockRadio** | `rockradio.com` | 37 | 🚀 **320 kbps MP3** |

---

## ✨ Features

- **🚀 Maximum Audio Quality (320 kbps MP3)**: Automatically maps streams to AudioAddict's highest bitrate 320 kbps MP3 feeds (`_hi` stream alias) instead of default 128 kbps AAC.
- **🔄 In-Place Upgrades**: If stations already exist in Navidrome at lower bitrates, running the tool updates their stream URLs in-place via the Subsonic API without deleting or duplicating them.
- **🛡️ Duplicate Prevention**: Queries existing internet radio stations from Navidrome before import, making re-runs fast and idempotent.
- **👀 Dry-Run Mode**: Preview exactly what stations and URLs will be added or updated with `--dry-run` before touching your server.
- **🎵 Real-Time ICY Metadata**: Streams pass real-time track and artist info (`StreamTitle`) directly to Navidrome and Subsonic client apps (Symfonium, Feishin, DSub, etc.).
- **🔒 Secure**: Uses `.env` configuration for credentials so passwords and listen keys are never hardcoded or committed to git.

---

## 📋 Prerequisites

- **Python 3.8+**
- A running **Navidrome** (or Subsonic-compatible) server with admin access
- A **DI.fm Premium / AudioAddict** subscription and your 32-character **Hardware Listen Key** (obtainable from [di.fm/apps/hardware-players](https://www.di.fm/apps/hardware-players))

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/hswilson/DI_x_Navidrome.git
cd DI_x_Navidrome
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure `.env`
Copy the template and fill in your credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```ini
# Navidrome connection details
NAVIDROME_URL=http://localhost:4533
NAVIDROME_USER=your_navidrome_username
NAVIDROME_PASSWORD=your_navidrome_password

# Your 32-character DI.fm Premium Listen Key
DI_LISTEN_KEY=your_32_character_listen_key

# Networks to sync (optional, defaults to all 5)
NETWORKS=di,radiotunes,jazzradio,rockradio,classicalradio
```

### 4. Preview with Dry-Run
```bash
python sync_difm.py --dry-run
```

### 5. Run the Live Sync
```bash
python sync_difm.py
```

All 337 stations will be loaded into Navidrome in ~15-20 seconds!

---

## ⚙️ CLI Options

You can override any `.env` setting directly from the command line:

```bash
python sync_difm.py [OPTIONS]
```

| Flag | Description | Default |
| :--- | :--- | :--- |
| `--dry-run` | Preview additions and upgrades without modifying Navidrome | `False` |
| `--networks` | Comma-separated list of networks to sync (`di,radiotunes,jazzradio,rockradio,classicalradio`) | All 5 |
| `--url` | Base URL of your Navidrome instance | `$NAVIDROME_URL` or `http://localhost:4533` |
| `--user` | Navidrome admin username | `$NAVIDROME_USER` |
| `--password` | Navidrome admin password | `$NAVIDROME_PASSWORD` |
| `--listen-key`| 32-character DI.fm hardware listen key | `$DI_LISTEN_KEY` |

### Examples

Sync only DI.FM and JazzRadio:
```bash
python sync_difm.py --networks di,jazzradio
```

Target a remote Navidrome server:
```bash
python sync_difm.py --url http://192.168.1.100:4533
```

---

## 🔍 How It Works

1. **Subsonic Token Authentication**: Connects using Subsonic salt/token MD5 authentication (`ping.view`), verifying API reachability without sending plaintext credentials.
2. **Channel Directory Retrieval**: Queries AudioAddict's public directory endpoints (`https://listen.{domain}/public3`) for current channel listings, keys, and names.
3. **URL Resolution**: Correctly resolves AudioAddict domain variations (`radiotunes.com`, `jazzradio.com`, `rockradio.com`, `classicalradio.com` vs. `di.fm`) and points to Icecast port 80 with the `_hi` alias.
4. **Subsonic Radio Injection**: Uses `createInternetRadioStation.view` and `updateInternetRadioStation.view` to create and update entries cleanly over HTTP.

---

## ❓ Frequently Asked Questions

#### Will song titles and artist names show up while playing?
**Yes.** AudioAddict's Icecast servers embed standard ICY metadata frames every 16 KB. Navidrome and Subsonic client players (Symfonium, Feishin, DSub, etc.) read this metadata in real-time.

#### Can I organize stations into folders?
The Subsonic internet radio specification (`getInternetRadioStations`) is a flat list. However, this script automatically prefixes stations with their network name (`DI.FM: ...`, `RadioTunes: ...`), so they are naturally sorted and grouped alphabetically. Client apps like **Symfonium** also allow client-side favorites, playlists, and custom tags.

#### Are on-demand mix shows and past episode archives included?
Scheduled mix shows that broadcast live on the linear channels *will* play over these streams. However, past on-demand episode archives and custom user playlists are only available via DI.fm's official web/mobile apps or API streaming controllers (such as Music Assistant).

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
