# **Syncing DI.fm Stations to Navidrome**

[https\://gemini.google.com/app/ecbeb5ca3369dd1e](https://gemini.google.com/app/ecbeb5ca3369dd1e)

*User prompt: music assistant could add all of the di.fm stations and sister channels via a plugin which i could log into for my premium access. I'd like to do the same in navidrome, but it seems like I can only really add 'favourites' or have to go through and do it all individually (or add all to favourites). is there no way to use the infomration from one plugin to feed the other?*

Response: There is no built-in sync bridge between Music Assistant and Navidrome, because they handle radio on completely different architectures:

> * **Music Assistant** acts as a streaming aggregation controller. Its DI.fm provider authenticates to the DI/AudioAddict API, dynamically fetches channel metadata, and injects playable streams into its internal queue.  
> * **Navidrome** is a Subsonic media server. It does not have an external streaming plugin engine; it simply maintains a local radio table in its database (navidrome.db) containing individual station names, homepages, and raw stream URLs.

You don't need to manually click through and add dozens of stations in the Navidrome UI, nor do you have to reverse-engineer Music Assistant's cache. AudioAddict/DI.fm exposes a channel list API, and your DI.fm Premium **Listen Key** allows stream URLs to be constructed programmatically and loaded directly into Navidrome.

### **Step 1: Grab Your DI.fm Listen Key**

> 1. Log in to your DI.fm account in a browser.  
> 2. Navigate to your **Account Settings** / **Player Settings** (or [di.fm/apps/hardware-players](https://www.di.fm/apps/hardware-players)).  
> 3. Copy your 32-character **Listen Key** (hardware stream key).

### **Step 2: Bulk-Populate Navidrome**

You can inject all DI.fm and sister network channels (Radio Tunes, ClassicalRadio, JazzRadio, RockRadio) either via Navidrome’s OpenSubsonic API or by direct insertion into its SQLite database.

#### **Method A: Subsonic API Script (Recommended & Cleanest)**

This method talks to Navidrome while it is running and avoids touching raw database files.

Save and run this Python script on any machine that can reach your Navidrome instance:

`import hashlib`  
`import secrets`  
`import string`  
`import requests`

`# --- Configuration ---`  
`NAVIDROME_URL = "http://localhost:4533"  # Your Navidrome URL`  
`ND_USER = "admin_username"`  
`ND_PASSWORD = "admin_password"`  
`DI_LISTEN_KEY = "YOUR_32_CHAR_LISTEN_KEY"`

`# Supported networks: 'di', 'radiotunes', 'classicalradio', 'jazzradio', 'rockradio'`  
`NETWORKS = ["di", "radiotunes", "jazzradio", "rockradio", "classicalradio"]`

`# --- Subsonic Auth Generator ---`  
`def get_auth_params(user, password):`  
    `salt = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))`  
    `token = hashlib.md5((password + salt).encode("utf-8")).hexdigest()`  
    `return {"u": user, "t": token, "s": salt, "v": "1.16.1", "c": "difm-importer", "f": "json"}`

`# --- Fetch & Inject ---`  
`session = requests.Session()`  
`auth = get_auth_params(ND_USER, ND_PASSWORD)`

`for net in NETWORKS:`  
    `print(f"Fetching channels for network: {net}...")`  
    `try:`  
        `# Public directory endpoint for AudioAddict channels`  
        `r = session.get(f"https://listen.{net}.fm/premium_high", timeout=10)`  
        `# Fallback to standard batch API if stream index is structured differently`  
        `api_url = f"https://api.audioaddict.com/v1/{net}/track_history/channel"`  
        `channels_res = session.get(f"https://listen.{net}.fm/public3", timeout=10)`  
        `channels = channels_res.json()`  
    `except Exception as e:`  
        `print(f"Could not fetch directory for {net}: {e}")`  
        `continue`

    `for chan in channels:`  
        `name = f"{net.upper()}: {chan.get('name')}"`  
        `key = chan.get("key")`  
          
        `# AudioAddict Premium AAC/MP3 direct stream syntax`  
        `stream_url = f"https://prem2.{net}.fm:80/{key}?{DI_LISTEN_KEY}"`  
        `homepage = f"https://www.{net}.fm/channels/{key}"`

        `payload = {`  
            `**auth,`  
            `"name": name,`  
            `"streamUrl": stream_url,`  
            `"homepageUrl": homepage`  
        `}`

        `resp = session.get(f"{NAVIDROME_URL}/rest/createInternetRadioStation", params=payload)`  
        `if resp.status_code == 200 and resp.json().get("subsonic-response", {}).get("status") == "ok":`  
            `print(f"Added: {name}")`  
        `else:`  
            `print(f"Failed to add {name}: {resp.text}")`

#### **Method B: Direct SQLite Batch Injection**

If your Navidrome instance runs in Docker or local Linux without remote Subsonic admin write access enabled, you can write directly to navidrome.db while Navidrome is briefly stopped (or live via WAL mode):

`# Verify the radio schema inside your navidrome.db`  
`sqlite3 /path/to/navidrome/data/navidrome.db ".schema radio"`

The table format uses:

`CREATE TABLE radio (`  
    `id TEXT PRIMARY KEY,`  
    `name TEXT NOT NULL,`  
    `stream_url TEXT NOT NULL,`  
    `home_page_url TEXT,`  
    `created_at DATETIME,`  
    `updated_at DATETIME`  
`);`

You can pull the network JSON array from \[https\://listen.di.fm/public3\](https\://listen.di.fm/public3), iterate over each object, generate a UUID4 for id, and execute a batch INSERT OR IGNORE INTO radio ....

### **What to Expect on Clients**

Once loaded into Navidrome:

> 1. All channels will appear under the **Radios** section in Navidrome’s web UI.  
> 2. Subsonic-compatible clients (e.g., Symfonium, Feishin, DSub) will fetch the full list automatically via the Subsonic Radio API.  
> 3. Audio streams will pass metadata (artist, title) straight to the player via standard ICY tags embedded in DI.fm's premium streams.

**Sources**

> 1. [Navidrome Raspberry Pi: Complete Music Streaming Guide](https://pidiylab.com/navidrome-raspberry-pi-multi-client-streaming/)  
> 2. [GitHub \- WB2024/Add-Navidrome-Radios: A Python CLI tool to](https://github.com/WB2024/Add-Navidrome-Radios)  
> 3. [DI staff member here for any questions : r/digitallyimported \- Reddit](https://www.reddit.com/r/digitallyimported/comments/14xsnvc/di_staff_member_here_for_any_questions/)  
> 4. [GitHub \- brunopiras/naviradiomanager: Webapp to search and add](https://github.com/brunopiras/naviradiomanager)

---

