#!/usr/bin/env python3
"""
Sync DI.fm & sister network stations to Navidrome via OpenSubsonic API.
Supports 320 kbps MP3 maximum quality streams with auto-upgrading.
"""

import argparse
import hashlib
import os
import secrets
import string
import sys
from typing import Dict, List, Any
import requests
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# AudioAddict Network domains & configuration for 320 kbps MP3
NETWORK_CONFIG = {
    "di": {
        "domain": "di.fm",
        "display": "DI.FM",
        "stream_host": "prem2.di.fm",
        "stream_suffix": "_hi",  # 320 kbps MP3
    },
    "radiotunes": {
        "domain": "radiotunes.com",
        "display": "RadioTunes",
        "stream_host": "prem2.radiotunes.com",
        "stream_suffix": "_hi",  # 320 kbps MP3
    },
    "jazzradio": {
        "domain": "jazzradio.com",
        "display": "JazzRadio",
        "stream_host": "prem2.jazzradio.com",
        "stream_suffix": "",  # Base stream is already 320 kbps MP3
    },
    "rockradio": {
        "domain": "rockradio.com",
        "display": "RockRadio",
        "stream_host": "prem2.rockradio.com",
        "stream_suffix": "",  # Base stream is already 320 kbps MP3
    },
    "classicalradio": {
        "domain": "classicalradio.com",
        "display": "ClassicalRadio",
        "stream_host": "prem2.classicalradio.com",
        "stream_suffix": "",  # Base stream is already 320 kbps MP3
    },
}


def get_subsonic_auth(user: str, password: str) -> Dict[str, str]:
    """Generate Subsonic token-based authentication parameters."""
    salt = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    token = hashlib.md5((password + salt).encode("utf-8")).hexdigest()
    return {
        "u": user,
        "t": token,
        "s": salt,
        "v": "1.16.1",
        "c": "difm-navidrome-sync",
        "f": "json",
    }


def verify_navidrome_connection(session: requests.Session, url: str, auth: Dict[str, str]) -> bool:
    """Check connectivity and credentials with Navidrome ping endpoint."""
    try:
        resp = session.get(f"{url.rstrip('/')}/rest/ping.view", params=auth, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("subsonic-response", {})
        if data.get("status") == "ok":
            server_version = data.get("serverVersion", "unknown")
            print(f"[OK] Connected to Navidrome (v{server_version}) successfully.")
            return True
        else:
            err = data.get("error", {})
            print(f"[ERROR] Navidrome authentication failed: {err.get('message', 'Unknown error')} (code: {err.get('code')})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Could not connect to Navidrome at {url}: {e}")
        return False


def get_existing_stations(session: requests.Session, url: str, auth: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """Retrieve existing stations from Navidrome mapped by name."""
    try:
        resp = session.get(f"{url.rstrip('/')}/rest/getInternetRadioStations.view", params=auth, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("subsonic-response", {})
        if data.get("status") == "ok":
            radio = data.get("internetRadioStations", {})
            stations = radio.get("internetRadioStation") or radio.get("station") or []
            existing = {s.get("name"): s for s in stations if s.get("name")}
            print(f"[INFO] Found {len(existing)} existing internet radio station(s) in Navidrome.")
            return existing
        return {}
    except Exception as e:
        print(f"[WARN] Could not fetch existing stations list: {e}")
        return {}


def fetch_network_channels(session: requests.Session, net_key: str, domain: str) -> List[Dict[str, Any]]:
    """Fetch public channel directory from AudioAddict."""
    url = f"https://listen.{domain}/public3"
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch channel list for {net_key} ({url}): {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Sync DI.fm & sister networks to Navidrome (320 kbps MP3)")
    parser.add_argument("--url", default=os.getenv("NAVIDROME_URL", "http://localhost:4533"), help="Navidrome Base URL")
    parser.add_argument("--user", default=os.getenv("NAVIDROME_USER"), help="Navidrome Admin Username")
    parser.add_argument("--password", default=os.getenv("NAVIDROME_PASSWORD"), help="Navidrome Admin Password")
    parser.add_argument("--listen-key", default=os.getenv("DI_LISTEN_KEY"), help="DI.fm 32-character Listen Key")
    parser.add_argument(
        "--networks",
        default=os.getenv("NETWORKS", "di,radiotunes,jazzradio,rockradio,classicalradio"),
        help="Comma-separated networks to sync (di, radiotunes, jazzradio, rockradio, classicalradio)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without updating Navidrome")
    args = parser.parse_args()

    # Configuration validation
    nav_url = args.url.strip() if args.url else ""
    nav_user = args.user.strip() if args.user else ""
    nav_pass = args.password.strip() if args.password else ""
    di_key = args.listen_key.strip() if args.listen_key else ""

    missing = []
    if not nav_url:
        missing.append("NAVIDROME_URL")
    if not nav_user:
        missing.append("NAVIDROME_USER")
    if not nav_pass:
        missing.append("NAVIDROME_PASSWORD")
    if not di_key:
        missing.append("DI_LISTEN_KEY")

    if missing:
        print("[ERROR] Missing required configuration:")
        for m in missing:
            print(f"  - {m}")
        print("\nPlease define them in .env or pass them as command-line arguments.")
        sys.exit(1)

    selected_networks = [n.strip().lower() for n in args.networks.split(",") if n.strip()]
    invalid_nets = [n for n in selected_networks if n not in NETWORK_CONFIG]
    if invalid_nets:
        print(f"[ERROR] Invalid network(s) specified: {', '.join(invalid_nets)}")
        print(f"Supported networks: {', '.join(NETWORK_CONFIG.keys())}")
        sys.exit(1)

    print("==================================================")
    print(" AudioAddict (DI.fm) -> Navidrome Importer (320k)")
    print("==================================================")
    print(f"Navidrome URL: {nav_url}")
    print(f"User:          {nav_user}")
    print(f"Listen Key:    {di_key[:4]}...{di_key[-4:]} ({len(di_key)} chars)")
    print(f"Networks:      {', '.join(selected_networks)}")
    print(f"Dry Run:       {'YES (No modifications will be made)' if args.dry_run else 'NO'}")
    print("==================================================\n")

    session = requests.Session()
    auth = get_subsonic_auth(nav_user, nav_pass)

    if not verify_navidrome_connection(session, nav_url, auth):
        sys.exit(1)

    existing_stations = get_existing_stations(session, nav_url, auth)

    total_added = 0
    total_upgraded = 0
    total_unchanged = 0
    total_failed = 0

    for net in selected_networks:
        cfg = NETWORK_CONFIG[net]
        display_name = cfg["display"]
        domain = cfg["domain"]
        stream_host = cfg["stream_host"]
        stream_suffix = cfg.get("stream_suffix", "")

        print(f"\n--- Processing {display_name} ({domain}) ---")
        channels = fetch_network_channels(session, net, domain)
        print(f"Retrieved {len(channels)} channels from {domain}")

        for chan in channels:
            chan_name = chan.get("name", "").strip()
            chan_key = chan.get("key", "").strip()
            if not chan_name or not chan_key:
                continue

            station_name = f"{display_name}: {chan_name}"
            # 320 kbps MP3 stream on port 80
            stream_url = f"http://{stream_host}:80/{chan_key}{stream_suffix}?{di_key}"
            homepage = f"https://www.{domain}/channels/{chan_key}"

            if station_name in existing_stations:
                existing_item = existing_stations[station_name]
                existing_url = existing_item.get("streamUrl", "")
                if existing_url == stream_url:
                    total_unchanged += 1
                    continue

                # Station exists but stream URL needs upgrade to 320k MP3
                if args.dry_run:
                    print(f"  [DRY-RUN UPGRADE] Would upgrade: {station_name} -> {stream_url}")
                    total_upgraded += 1
                    continue

                update_payload = {
                    **auth,
                    "id": existing_item["id"],
                    "name": station_name,
                    "streamUrl": stream_url,
                    "homepageUrl": homepage,
                }
                try:
                    resp = session.get(
                        f"{nav_url.rstrip('/')}/rest/updateInternetRadioStation.view",
                        params=update_payload,
                        timeout=10,
                    )
                    data = resp.json().get("subsonic-response", {})
                    if resp.status_code == 200 and data.get("status") == "ok":
                        print(f"  [UPGRADED 320k] {station_name}")
                        existing_stations[station_name]["streamUrl"] = stream_url
                        total_upgraded += 1
                    else:
                        err_msg = data.get("error", {}).get("message", resp.text)
                        print(f"  [FAILED UPGRADE] {station_name}: {err_msg}")
                        total_failed += 1
                except Exception as e:
                    print(f"  [FAILED UPGRADE] {station_name}: {e}")
                    total_failed += 1
                continue

            if args.dry_run:
                print(f"  [DRY-RUN ADD] Would add: {station_name} -> {stream_url}")
                total_added += 1
                continue

            payload = {
                **auth,
                "name": station_name,
                "streamUrl": stream_url,
                "homepageUrl": homepage,
            }

            try:
                resp = session.get(f"{nav_url.rstrip('/')}/rest/createInternetRadioStation.view", params=payload, timeout=10)
                data = resp.json().get("subsonic-response", {})
                if resp.status_code == 200 and data.get("status") == "ok":
                    print(f"  [ADDED] {station_name}")
                    existing_stations[station_name] = {"name": station_name, "streamUrl": stream_url}
                    total_added += 1
                else:
                    err_msg = data.get("error", {}).get("message", resp.text)
                    print(f"  [FAILED] {station_name}: {err_msg}")
                    total_failed += 1
            except Exception as e:
                print(f"  [FAILED] {station_name}: {e}")
                total_failed += 1

    print("\n==================================================")
    print(" Sync Summary")
    print("==================================================")
    print(f"Added          : {total_added}")
    print(f"Upgraded (320k): {total_upgraded}")
    print(f"Unchanged (320k): {total_unchanged}")
    print(f"Failed         : {total_failed}")
    print("==================================================")


if __name__ == "__main__":
    main()
