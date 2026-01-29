import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json

print("=== SCRIPT START ===")

# ========= CONFIG =========
URL = "https://coc-stats.net/en/locations/32000097/players/"
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
HEALTHCHECK_URL = os.environ.get("HEALTHCHECK_URL")

DATA_FILE = "previous_day.json"
DAILY_LOCK = "posted_today.txt"
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


# ---- TIME WINDOW GUARD ----
if not ("06:00" <= current_time_str <= "07:05"):
    print("Outside posting window. Exiting.")
    exit(0)


# ---- DAILY LOCK GUARD ----
if os.path.exists(DAILY_LOCK):
    with open(DAILY_LOCK) as f:
        if f.read().strip() == today_str:
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

    rank = cols[0].get_text(strip=True).split(".")[0]
    name = cols[1].find("a").text.strip()

    trophies_text = cols[2].get_text(strip=True)
    trophies = int("".join(c for c in trophies_text if c.isdigit()))

    change = ""
    if tag in previous:
        diff = trophies - previous[tag]
        if diff > 0:
            change = f" 🟢 ▲{diff}"
        elif diff < 0:
            change = f" 🔴 ▼{abs(diff)}"
        else:
            change = " ⚪ ▬"

    players.append(f"{rank}. {name} | {trophies}🏆{change}")
    today_data[tag] = trophies

    if len(players) >= MAX_PLAYERS:
        break


# ---- Discord embed ----
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


# ---- SAVE STATE ONLY ON SUCCESS ----
if resp.status_code in (200, 204):
    print("Discord post successful. Saving daily state.")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(today_data, f, ensure_ascii=False, indent=2)

    with open(DAILY_LOCK, "w") as f:
        f.write(today_str)

else:
    print("Discord failed. NOT saving state.")


# ---- Healthcheck ----
if HEALTHCHECK_URL:
    try:
        requests.get(HEALTHCHECK_URL, timeout=10)
        print("Healthcheck ping sent")
    except Exception as e:
        print("Healthcheck failed:", e)

print("=== SCRIPT END ===")

