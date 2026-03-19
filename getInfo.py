#<span data-value="2025-11-16 15:00:00" id="schedule-date"></span>

import sys
from datetime import datetime, timezone

from bs4 import BeautifulSoup
import requests as r



# crude argument handling
if(len(sys.argv) != 2):
    print(sys.argv[0]+" requires 1 argument!\nexiting..")
    exit()
link: str = sys.argv[1]
if not ("https://kaido.to/watch/" in link):
    print("Make sure the provided link are as followed: https://kaido.to/watch/<your_show_here>\nexiting..")
    exit()

html = r.get(link).text
soup = BeautifulSoup(html, "html.parser")

title = soup.find("div", class_="anisc-detail").find("a").get("title")
print(f"\n{title}\n")

span_schedule_date = soup.find("span", id="schedule-date")
if(span_schedule_date == None):
    print("This show is not being aired currently!\nexiting..")
    exit()
raw_time_str = span_schedule_date.get("data-value")


dt = datetime.strptime(raw_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
local_dt = dt.astimezone()
now = datetime.now(timezone.utc).astimezone()

day_name = local_dt.strftime("%A")
time_str = local_dt.strftime("%I:%M %p").lstrip("0")
date_str = local_dt.strftime("%d %B %Y")

print(f"Uploaded every {day_name} at {time_str}")
print(f"Next upload is on {date_str}")
delta = local_dt - now
if delta.total_seconds() > 0:
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes = remainder // 60

    print(f"Time until next upload: {days} Days, {hours} Hours, {minutes} Minutes\n")
else:
    print("The next upload time has already passed.") # redundant stuff