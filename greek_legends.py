import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json
import time

TEST_MODE = False
print("=== SCRIPT START ===")

# ========= CONFIG =========
URL = "https://coc-stats.net/en/locations/32000097/players/"

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

DATA_FILE = "previous_day.json"

MAX_PLAYERS = 100

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
# ==========================

# ---- Greece time ----
greece_tz = ZoneInfo("Europe/Athens")
now_gr = datetime.now(greece_tz)

today_str = now_gr.strftime("%Y-%m-%d")
current_time_str = now_gr.strftime("%H:%M")

date_title = now_gr.strftime("%B %d")
time_footer = current_time_str

print("Greece time:", now_gr.strftime("%Y-%m-%d %H:%M:%S"))

# ======================================================
# PRE-RESET WINDOW
#
# Reset = 05:00 UTC
#
# Greece:
# Winter  = UTC+2 -> 07:00
# Summer  = UTC+3 -> 08:00
#
# Workflow runs:
# 04:00, 04:15, 04:30, 04:45 UTC
#
# Therefore we allow:
# 07:00 - 08:00 Greece time
# ======================================================
if not TEST_MODE:
    if not ("07:00" <= current_time_str < "08:00"):
        print("Outside pre-reset window. Exiting.")
        exit(0)

# ---- Load yesterday data ----
previous = {}

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            previous = json.load(f)

    except Exception as e:
        print("Could not load previous_day.json:", e)

# ---- Fetch page with retries ----
response = None

for attempt in range(1, 4):
    try:
        print(f"Fetch attempt {attempt}")

        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        print("Page fetched successfully")
        break

    except requests.exceptions.RequestException as e:
        print(f"Attempt {attempt} failed:", e)

        if attempt == 3:
            print("All attempts failed.")
            exit(0)

        time.sleep(5)

# ---- Parse page ----
soup = BeautifulSoup(response.text, "html.parser")
rows = soup.select("table tr")

print("Rows found:", len(rows))

players = []
today_data = {}
seen_tags = set()

for row in rows:

    cols = row.find_all("td")

    if len(cols) < 3:
        continue

    raw_text = cols[1].get_text(" ", strip=True)

    if "#" not in raw_text:
        continue

    tag = raw_text.split("#")[-1].strip()

    if tag in seen_tags:
        continue

    seen_tags.add(tag)

    try:
        name_tag = cols[1].find("a")

        if not name_tag:
            continue

        rank = cols[0].get_text(strip=True).split(".")[0]

        name = name_tag.text.strip()

        trophies_text = cols[2].get_text(strip=True)

        trophies = int(
            "".join(c for c in trophies_text if c.isdigit())
        )

    except Exception as e:
        print("Skipping row:", e)
        continue

    change = ""

    if tag in previous:

        diff = trophies - previous[tag]

        if diff > 0:
            change = f" 🟢 ▲{diff}"

        elif diff < 0:
            change = f" 🔴 ▼{abs(diff)}"

        else:
            change = " ⚪ ▬"

    players.append(
        f"{rank}. {name} | {trophies}🏆{change}"
    )

    today_data[tag] = trophies

    if len(players) >= MAX_PLAYERS:
        break

print("Players found:", len(players))

# ---- Safety check ----
if len(players) < 10:
    print("Too few players found.")
    exit(0)

# ---- Discord embed ----
embed = {
    "title": f"Greece Legend 1 Leaderboard for {date_title}",
    "description": "\n".join(players),
    "color": 0xF1C40F,
    "footer": {
        "text": f"Posted at {time_footer} (Greece time)"
    }
}

payload = {
    "embeds": [embed]
}

# ---- Send to Discord ----
try:

    resp = requests.post(
        DISCORD_WEBHOOK,
        json=payload,
        timeout=20
    )

    print("Discord status:", resp.status_code)

except Exception as e:
    print("Discord request failed:", e)
    exit(0)

# ---- Save state ONLY if Discord succeeded ----
if resp.status_code in (200, 204):

    print("Discord post successful")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            today_data,
            f,
            ensure_ascii=False,
            indent=2
        )

else:

    print("Discord failed")
    print(resp.text)
    exit(0)

print("=== SCRIPT END ===")
