import requests
import json
import os
from datetime import datetime, timezone

# ===== CONFIG =====
CLASH_API_TOKEN = os.environ.get("CLASH_API_TOKEN")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

if not CLASH_API_TOKEN or not DISCORD_WEBHOOK_URL:
    raise RuntimeError("Missing environment variables")

LOCATION_ID = "32000097"  # Greece
LEGEND_TROPHIES = 4700
MAX_PLAYERS = 100
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "previous_ranks.json")
dt = datetime.now(timezone.utc)
today = f"{dt.strftime('%B')} {dt.day}, {dt.year}"
# ==================

headers = {
    "Authorization": f"Bearer {CLASH_API_TOKEN}"
}

# --- Load yesterday's data ---
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        previous_data = json.load(f)
else:
    previous_data = {}

# --- Fetch Greek players ---
url = f"https://api.clashofclans.com/v1/locations/{LOCATION_ID}/rankings/players"
response = requests.get(url, headers=headers)
response.raise_for_status()

items = response.json().get("items", [])

# --- Filter Legend League players ---
legend_players = [p for p in items if p.get("trophies", 0) >= LEGEND_TROPHIES]
players = legend_players[:MAX_PLAYERS]

lines = []
current_data = {}

MAX_NAME_LEN = 20

for index, p in enumerate(players, start=1):
    tag = p["tag"]
    name = p["name"]
    trophies = p["trophies"]
    clan = p["clan"]["name"] if "clan" in p else "No Clan"
    if len(name) > MAX_NAME_LEN:
        name = name[:MAX_NAME_LEN]

    current_data[tag] = index

    # --- Rank change logic ---
    if tag not in previous_data:
        change = "🆕"
    else:
        diff = previous_data[tag] - index
        if diff > 0:
            change = f"↑{diff}"
        elif diff < 0:
            change = f"↓{abs(diff)}"
        else:
            change = "→"

    rank = str(index).rjust(3)  # pads to width 3

    lines.append(
        f"{rank}- {name} | {trophies}"
    )

# --- Save today's data for tomorrow ---
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(current_data, f, ensure_ascii=False, indent=2)

# Embdeds
fields = []

# Safe chunk size for short lines
CHUNK_SIZE = 20

for i in range(0, len(lines), CHUNK_SIZE):
    fields.append({
        "name": "\u200b",  # invisible title
        "value": "\n".join(lines[i:i + CHUNK_SIZE]),
        "inline": False
    })

embed = {
    "title": f"🏆 Greece Legends Leaderboard for {today} 🇬🇷",
    "color": 0x1ABC9C,
    "fields": fields,
    "timestamp": datetime.now(timezone.utc).isoformat()
}

payload = {"embeds": [embed]}
response = requests.post(DISCORD_WEBHOOK_URL, json=payload)

print("Discord status:", response.status_code)
print("Discord response:", response.text)

print("Total players processed:", len(players))

