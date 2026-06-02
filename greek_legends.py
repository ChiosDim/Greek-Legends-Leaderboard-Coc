import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json
import time

print("=== SCRIPT START ===")

# ========= CONFIG =========
URL = "https://coc-stats.net/en/locations/32000097/players/"
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
HEALTHCHECK_URL = os.environ.get("HEALTHCHECK_URL")

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
# Leaderboard resets at 05:00 UTC
# Greece summer time = UTC+3
#
# We want snapshot between:
# 04:00 UTC -> 07:00 Greece
# 05:00 UTC -> 08:00 Greece
# ======================================================
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
max_attempts = 3
response = None

for attempt in range(1, max_attempts + 1):
    try:
        print(f"Fetch attempt {attempt}...")

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

        if attempt == max_attempts:
            print("All fetch attempts failed. Exiting safely.")
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

if not players:
    print("No players found. Exiting safely.")
    exit(0)

if len(players) < 5:
    print("Too few players found. Something is wrong.")
    exit(0)
    
# ---- Discord embed ----
embed = {
    "title": f"Greece Legends Leaderboard for {date_title}",
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


# ---- SAVE STATE ONLY ON SUCCESS ----
if resp.status_code in (200, 204):

    print("Discord post successful. Saving daily state.")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            today_data,
            f,
            ensure_ascii=False,
            indent=2
        )

    with open(DAILY_LOCK, "w") as f:
        f.write(today_str)

else:
    print("Discord failed.")
    print(resp.text)
    exit(0)


# ---- Healthcheck ----
if HEALTHCHECK_URL:
    try:
        requests.get(
            HEALTHCHECK_URL,
            timeout=10
        )

        print("Healthcheck ping sent")

    except Exception as e:
        print("Healthcheck failed:", e)


print("=== SCRIPT END ===")
