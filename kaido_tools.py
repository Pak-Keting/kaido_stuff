import re
from bs4 import BeautifulSoup

BASE_LINK = "https://kaido.to"

def parse_episode_list(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    
    episodes: list = []
    
    # find all the <a> tags with class 'ssl-item ep-item'
    for a in soup.find_all("a", class_="ep-item"):
        title: str = a.get("title")
        data_number: str = a.get("data-number")
        data_id: str = a.get("data-id")
        href: str = a.get("href")
    
        episodes.append({
            "title": title,
            "episode": data_number,
            "episodeId": data_id,
            "link": BASE_LINK+href
        })

    return episodes


def parse_servers(html: str) -> tuple:
    soup = BeautifulSoup(html, "html.parser")
    
    # extract episode count
    text = soup.select_one(".server-notice strong b").get_text(strip=True)
    episode = re.search(r'\d+', text).group()

    results: dict = {} # example: results["SUB"] = [{HD-1:dataId}]
    for block in soup.select("div.ps_-block-sub"):
        title_div = block.select_one(".ps__-title")
        language: str = title_div.get_text().replace(':','')
        
        server_dict: dict = {}
        for item in block.select(".server-item"):
            server: str = item.select_one("a").get_text()
            server_dict[server] = item.get("data-id")
        results[language] = server_dict

    return results,episode


def parse_season_data(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    os_item = soup.select("a.os-item")

    season_data: dict = {}
    for i in os_item:
        season_data[i.select_one("div.title").get_text()] = i.get("href")
    return season_data

def parse_search_result(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    
    search_result = {
        title.get_text(strip=True): link["href"]
        for title, link in zip(
            soup.find_all("div", class_="alias-name"),
            soup.find_all("a", class_="nav-item")
        )
    }

    return search_result
    
    




# This test is from hianime, ignore it
def test_episode_list_and_servers() -> None:
    html: str = r.get(BASE_LINK+"/ajax/v2/episode/list/552").json().get("html")
    episodes: list = parse_episode_list(html)
    for ep in episodes:
        print(ep)
    
    
    epId = episodes[3].get("episodeId")
    html = r.get(BASE_LINK+"/ajax/v2/episode/servers?episodeId="+epId).json().get("html")
    servers = parse_servers(html)
    print(servers)
def test_search() -> None:
    parse_search_result(r.get(BASE_LINK + "/ajax/search/suggest?keyword=" + "overlord").json().get("html"))


if __name__ == "__main__":
    import requests as r
    test_search()
