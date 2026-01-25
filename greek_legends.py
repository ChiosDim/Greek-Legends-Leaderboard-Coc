import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os
import json

print("=== SCRIPT START ===")
print("UTC now:", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
# ---- Daily run lock ----
LOCK_FILE = "last_run_date.txt"

# ========= CONFIG =========
URL = "https://coc-stats.net/en/locations/32000097/players/"
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
DATA_FILE = "previous_day.json"
MAX_PLAYERS = 100

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
# ==========================

# ---- Time (Greece) ----
greece_tz = ZoneInfo("Europe/Athens")
now_gr = datetime.now(greece_tz)
print("Greece time:", now_gr.strftime("%Y-%m-%d %H:%M:%S %Z"))
date_title = now_gr.strftime("%B %d")
time_footer = now_gr.strftime("%H:%M")

today_str = now_gr.strftime("%Y-%m-%d")
current_time_str = now_gr.strftime("%H:%M")

# ---- Time guard: ONLY run at 06:59 Greece time ----
if not ("06:30" <= current_time_str <= "07:05"):
    print(f"Outside allowed window (now: {current_time_str}). Exiting.")
    exit(0)

# ---- Once-per-day guard ----
if os.path.exists(LOCK_FILE):
    with open(LOCK_FILE, "r") as f:
        last_run = f.read().strip()
        if last_run == today_str:
            print("Already posted today. Exiting.")
            exit(0)


# ---- Load yesterday data ----
previous = {}
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        previous = json.load(f)

# ---- Fetch page ----
response = requests.get(URL, headers=HEADERS, timeout=30)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

rows = soup.select("table tr")

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

    rank_tag = cols[0].find("h3")
    name_tag = cols[1].find("a")
    if not rank_tag or not name_tag:
        continue

    rank = rank_tag.text.split(".")[0].strip()
    name = name_tag.text.strip()

    trophies_text = cols[2].get_text(strip=True)
    trophies = int("".join(c for c in trophies_text if c.isdigit()))

    # ---- Compare with yesterday ----
    change = ""
    if tag in previous:
        diff = trophies - previous[tag]
        if diff > 0:
            change = f" 🟢 ▲{diff}"
        elif diff < 0:
            change = f" 🔴 ▼{abs(diff)}"
        else:
            change = " ⚪ ▬"


    players.append(f"{rank}. {name} | {trophies}🏆 | {change}🏆")
    today_data[tag] = trophies

    if len(players) >= MAX_PLAYERS:
        break

# ---- Save today for tomorrow ----
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(today_data, f, ensure_ascii=False, indent=2)

# ---- Build embed ----
embed = {
    "title": f"Greece Legends Leaderboard for {date_title}",
    "description": "\n".join(players),
    "color": 0xF1C40F,
    "footer": {
        "text": f"Posted at {time_footer} (Greece time)"
    }
}

payload = {"embeds": [embed]}

# ---- Send to Discord ----
resp = requests.post(DISCORD_WEBHOOK, json=payload)
print("Discord status:", resp.status_code)
print(resp.text)

# ---- Save successful run date ----
if resp.status_code == 204 or resp.status_code == 200:
    with open(LOCK_FILE, "w") as f:
        f.write(today_str)







