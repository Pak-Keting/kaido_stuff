import sys
import requests as r
from kaido_tools import parse_episode_list, BASE_LINK

# parse the anime id from the argument
anime_url = sys.argv[1]
if (BASE_LINK not in anime_url) and anime_url.isdigit():
    anime_id = anime_url
elif BASE_LINK in anime_url:
    start = anime_url.rfind('-')+1
    if "?ep=" in anime_url:
        end = anime_url.rfind("?ep=")
    else:
        end = len(anime_url)
    anime_id = anime_url[start:end]
else:
    print("Invalid input!")
    exit()


html = r.get(BASE_LINK+"/ajax/episode/list/"+str(anime_id)).json().get("html")
episode_list = parse_episode_list(html)

for i in episode_list:
    print(i.get("episode")+"    "+i.get("link"))
