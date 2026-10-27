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
from typing import Dict, List, Any, Optional
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
    # see docs/working/2026-10-27_zen_radio_sync.md
    "zenradio": {
        "domain": "zenradio.com",
        "display": "ZenRadio",
        "stream_host": "prem2.zenradio.com",
        "stream_prefix": "zr",
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


def extract_channel_image_url(chan: Dict[str, Any]) -> str:
    """Extract and normalize 300x300 PNG image URL from channel metadata."""
    images = chan.get("images") or {}
    template = images.get("default") or images.get("square") or images.get("compact") or chan.get("asset_url") or ""
    if not template:
        return ""
    clean_url = template.split("{")[0]
    if clean_url.startswith("//"):
        clean_url = "https:" + clean_url
    elif not clean_url.startswith("http"):
        clean_url = "https://" + clean_url
    if "?" not in clean_url:
        clean_url += "?size=300x300"
    return clean_url


def fetch_network_channels(session: requests.Session, net_key: str, domain: str) -> List[Dict[str, Any]]:
    """Fetch public channel directory and enrich with artwork from AudioAddict API."""
    # 1. Fetch official public channel list
    public_url = f"https://listen.{domain}/public3"
    try:
        resp = session.get(public_url, timeout=10)
        resp.raise_for_status()
        channels = resp.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch channel list for {net_key} ({public_url}): {e}")
        return []

    # 2. Enrich with artwork metadata from api.audioaddict.com
    api_url = f"https://api.audioaddict.com/v1/{net_key}/channels"
    try:
        api_resp = session.get(api_url, timeout=10)
        if api_resp.status_code == 200:
            meta_by_key = {c.get("key"): c for c in api_resp.json() if c.get("key")}
            for chan in channels:
                key = chan.get("key")
                meta = meta_by_key.get(key, {})
                chan["image_url"] = extract_channel_image_url(meta)
    except Exception as e:
        print(f"[WARN] Could not fetch artwork metadata from {api_url}: {e}")

    return channels


def get_navidrome_jwt(session: requests.Session, url: str, user: str, password: str) -> Optional[str]:
    """Authenticate to Navidrome native API to obtain a JWT for artwork upload."""
    try:
        resp = session.post(
            f"{url.rstrip('/')}/auth/login",
            json={"username": user, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("token")
        else:
            print(f"[WARN] Native Navidrome auth failed ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"[WARN] Could not connect to Navidrome native auth: {e}")
    return None


def upload_station_artwork(session: requests.Session, url: str, jwt: str, station_id: str, image_url: str) -> bool:
    """Download image from CDN and upload to Navidrome radio station."""
    try:
        img_resp = session.get(image_url, timeout=10)
        img_resp.raise_for_status()
        headers = {"x-nd-authorization": f"Bearer {jwt}"}
        files = {"image": ("cover.png", img_resp.content, "image/png")}
        resp = session.post(
            f"{url.rstrip('/')}/api/radio/{station_id}/image",
            headers=headers,
            files=files,
            timeout=15,
        )
        return resp.status_code in (200, 204)
    except Exception as e:
        print(f"[WARN] Failed to upload artwork for station {station_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Sync DI.fm & sister networks to Navidrome (320 kbps MP3)")
    parser.add_argument("--url", default=os.getenv("NAVIDROME_URL", "http://localhost:4533"), help="Navidrome Base URL")
    parser.add_argument("--user", default=os.getenv("NAVIDROME_USER"), help="Navidrome Admin Username")
    parser.add_argument("--password", default=os.getenv("NAVIDROME_PASSWORD"), help="Navidrome Admin Password")
    parser.add_argument("--listen-key", default=os.getenv("DI_LISTEN_KEY"), help="DI.fm 32-character Listen Key")
    parser.add_argument(
        "--networks",
        default=os.getenv("NETWORKS", "di,radiotunes,jazzradio,rockradio,classicalradio,zenradio"),
        help="Comma-separated networks to sync (di, radiotunes, jazzradio, rockradio, classicalradio, zenradio)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without updating Navidrome")
    parser.add_argument("--no-artwork", action="store_true", help="Skip syncing channel artwork into Navidrome")
    parser.add_argument("--force-artwork", action="store_true", help="Re-upload artwork even if station already has coverArt")
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

    art_status = "NO" if args.no_artwork else ("FORCE ALL" if args.force_artwork else "YES (missing only)")

    print("==================================================")
    print(" AudioAddict (DI.fm) -> Navidrome Importer (320k)")
    print("==================================================")
    print(f"Navidrome URL: {nav_url}")
    print(f"User:          {nav_user}")
    print(f"Listen Key:    {di_key[:4]}...{di_key[-4:]} ({len(di_key)} chars)")
    print(f"Networks:      {', '.join(selected_networks)}")
    print(f"Sync Artwork:  {art_status}")
    print(f"Dry Run:       {'YES (No modifications will be made)' if args.dry_run else 'NO'}")
    print("==================================================\n")

    session = requests.Session()
    auth = get_subsonic_auth(nav_user, nav_pass)

    if not verify_navidrome_connection(session, nav_url, auth):
        sys.exit(1)

    jwt = None
    if not args.no_artwork:
        jwt = get_navidrome_jwt(session, nav_url, nav_user, nav_pass)
        if jwt:
            print("[OK] Connected to Navidrome native API for artwork uploads.")
        else:
            print("[WARN] Could not authenticate to Navidrome native API. Artwork upload will be skipped.")

    existing_stations = get_existing_stations(session, nav_url, auth)

    total_added = 0
    total_upgraded = 0
    total_unchanged = 0
    total_failed = 0
    total_artwork = 0
    total_artwork_failed = 0

    for net in selected_networks:
        cfg = NETWORK_CONFIG[net]
        display_name = cfg["display"]
        domain = cfg["domain"]
        stream_host = cfg["stream_host"]
        stream_prefix = cfg.get("stream_prefix", "")
        stream_suffix = cfg.get("stream_suffix", "")

        print(f"\n--- Processing {display_name} ({domain}) ---")
        channels = fetch_network_channels(session, net, domain)
        print(f"Retrieved {len(channels)} channels from {domain}")

        for chan in channels:
            chan_name = chan.get("name", "").strip()
            chan_key = chan.get("key", "").strip()
            chan_img = chan.get("image_url", "")
            if not chan_name or not chan_key:
                continue

            station_name = f"{display_name}: {chan_name}"
            # 320 kbps MP3 stream on port 80
            stream_url = f"http://{stream_host}:80/{stream_prefix}{chan_key}{stream_suffix}?{di_key}"
            homepage = f"https://www.{domain}/channels/{chan_key}"

            station_item = existing_stations.get(station_name)

            if station_item:
                existing_url = station_item.get("streamUrl", "")
                if existing_url == stream_url:
                    total_unchanged += 1
                else:
                    # Station exists but stream URL needs upgrade to 320k MP3
                    if args.dry_run:
                        print(f"  [DRY-RUN UPGRADE] Would upgrade: {station_name} -> {stream_url}")
                        total_upgraded += 1
                    else:
                        update_payload = {
                            **auth,
                            "id": station_item["id"],
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
                                station_item["streamUrl"] = stream_url
                                total_upgraded += 1
                            else:
                                err_msg = data.get("error", {}).get("message", resp.text)
                                print(f"  [FAILED UPGRADE] {station_name}: {err_msg}")
                                total_failed += 1
                        except Exception as e:
                            print(f"  [FAILED UPGRADE] {station_name}: {e}")
                            total_failed += 1
            else:
                if args.dry_run:
                    print(f"  [DRY-RUN ADD] Would add: {station_name} -> {stream_url}")
                    total_added += 1
                else:
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
                            station_item = {"name": station_name, "streamUrl": stream_url, "coverArt": ""}
                            existing_stations[station_name] = station_item
                            total_added += 1
                        else:
                            err_msg = data.get("error", {}).get("message", resp.text)
                            print(f"  [FAILED] {station_name}: {err_msg}")
                            total_failed += 1
                    except Exception as e:
                        print(f"  [FAILED] {station_name}: {e}")
                        total_failed += 1

            # Artwork synchronization step (see docs/working/2026-10-27_station_artwork_sync.md)
            if jwt and not args.no_artwork and chan_img:
                current_item = existing_stations.get(station_name)
                if current_item:
                    has_cover = bool(current_item.get("coverArt"))
                    if not has_cover or args.force_artwork:
                        if args.dry_run:
                            print(f"  [DRY-RUN ARTWORK] Would upload artwork for: {station_name}")
                            total_artwork += 1
                        else:
                            # Ensure we have the station id
                            sid = current_item.get("id")
                            if not sid:
                                # Re-fetch existing stations if id is missing
                                refreshed = get_existing_stations(session, nav_url, auth)
                                if station_name in refreshed:
                                    existing_stations[station_name] = refreshed[station_name]
                                    current_item = existing_stations[station_name]
                                    sid = current_item.get("id")

                            if sid and upload_station_artwork(session, nav_url, jwt, sid, chan_img):
                                print(f"  [ARTWORK] Uploaded {station_name}")
                                current_item["coverArt"] = "uploaded"
                                total_artwork += 1
                            else:
                                total_artwork_failed += 1

    print("\n==================================================")
    print(" Sync Summary")
    print("==================================================")
    print(f"Added          : {total_added}")
    print(f"Upgraded (320k): {total_upgraded}")
    print(f"Unchanged (320k): {total_unchanged}")
    print(f"Artwork Sync   : {total_artwork}")
    if total_artwork_failed > 0:
        print(f"Artwork Failed : {total_artwork_failed}")
    print(f"Failed         : {total_failed}")
    print("==================================================")


if __name__ == "__main__":
    main()
