from pathlib import Path
import os
import argparse
import asyncio
import base64 as b64

import aiohttp
import ffmpeg

import hls_tools
import kaido_tools

# just a simple ansi terminal color here, it's rather crude
COLORS: dict = {
    "BLACK": "\033[0;30m",
    "RED": "\033[0;31m",
    "GREEN": "\033[0;32m",
    "BROWN": "\033[0;33m",
    "BLUE": "\033[0;34m",
    "PURPLE": "\033[0;35m",
    "CYAN": "\033[0;36m",
    "LIGHT_GRAY": "\033[0;37m",
    "DARK_GRAY": "\033[1;30m",
    "LIGHT_RED": "\033[1;31m",
    "LIGHT_GREEN": "\033[1;32m",
    "YELLOW": "\033[1;33m",
    "LIGHT_BLUE": "\033[1;34m",
    "LIGHT_PURPLE": "\033[1;35m",
    "LIGHT_CYAN": "\033[1;36m",
    "LIGHT_WHITE": "\033[1;37m",
    "BOLD": "\033[1m",
    "FAINT": "\033[2m",
    "ITALIC": "\033[3m",
    "UNDERLINE": "\033[4m",
    "BLINK": "\033[5m",
    "NEGATIVE": "\033[7m",
    "CROSSED": "\033[9m",
    "END": "\033[0m",
}

BASE_LINK = kaido_tools.BASE_LINK

MAX_CONCURRENT_DOWNLOADS: int = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

MAX_RETRIES: int = 100
TIMEOUT_DURATION: int = 2

async def download_segment(session, url: str, filename: str) -> None:
    async with semaphore:
        for attempt in range(1, MAX_RETRIES+1):
            try:
                async with session.get(url,
                                       timeout=aiohttp.ClientTimeout(total=TIMEOUT_DURATION*10,
                                                                     connect=TIMEOUT_DURATION),
                                       headers={"referer":"https://megacloud.blog/"}) as resp:
                    if resp.status != 200:
                        raise Exception(f"Server return bad status : {resp.status}")
                    data = await resp.read()
                    
                    # it probably a good idea to separate this writing part and just return the data. we'll see.
                    try:
                        with open(filename, 'wb') as f:
                            f.write(data)
                        print(f"Done writing data to {filename}")
                        return
                    except OSError as e:
                        if e.errno == errno.ENOSPC:  # No space left on device
                            raise RuntimeError(f"Disk full! Cannot write {filename}") from e
                        else:
                            raise  # re-raise other OSErrors
                        
            except asyncio.TimeoutError:
                print(f"{COLORS['YELLOW']}[{attempt}/{MAX_RETRIES} Timeout] {filename}{COLORS['END']}")
            except Exception as err:
                print(f"{COLORS['YELLOW']}[{attempt}/{MAX_RETRIES} Retrying...] {filename}: {err}{COLORS['END']}")
    
                await asyncio.sleep(attempt) # crude backoff
                
        print(f"{COLORS['RED']}FAILED TO DOWNLOAD {filename}{COLORS['END']}")

async def async_fetch_json(url, **kwargs):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, **kwargs) as resp:
            if resp.status != 200:
                raise Exception(f"Server return bad status : {resp.status}")
            return await resp.json(content_type=None) # I'll fix this later

# I hard-coded the referer here, probably not a good practice there
async def async_fetch_http(url, **kwargs):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"referer":"https://megacloud.blog/"}, **kwargs) as resp:
            if resp.status != 200:
                raise Exception(f"Server return bad status : {resp.status}")
            return await resp.read() # I'll fix this later



async def test() -> None:
    m3u8 = open("../samples/index-f3-v1-a1.m3u8").read()
    localized_m3u8 = hls_tools.localize_m3u8(m3u8, os.getcwd())
    with open("./local.m3u8",'w') as f:
        f.write(localized_m3u8)
        
    segment_links =  hls_tools.get_segment_links(m3u8)
    segment_filenames = hls_tools.get_segment_filenames_fixed_extension(m3u8)
    async with aiohttp.ClientSession() as session:
        tasks = [download_segment(session, url, filename) for url, filename in zip(segment_links, segment_filenames)]
        await asyncio.gather(*tasks)

async def main() -> None:
    parser = argparse.ArgumentParser(prog="kaido-dl")
    parser.add_argument("link")
    parser.add_argument("-q", "--quality", type=int, default=2)
    #parser.add_argument("episode", type=int)


    # For now, I'll make it only take the episode link as argument, download Vidstreaming and eng subs.
    # I'll add more stuff later on (or never)
    args = parser.parse_args()
    episode_url = args.link
    quality = args.quality

    episodeId = episode_url[episode_url.find('=')+1:] # crude way of getting the episodeId from link

    servers_html = await async_fetch_json(BASE_LINK+'/ajax/episode/servers?episodeId='+str(episodeId))
    servers_html = servers_html.get("html")
    servers, episode  = kaido_tools.parse_servers(servers_html)
    episode = "EP"+str('{:02d}'.format(int(episode))) # episode count, like EP12
    
    SUB = servers.get("SUB")
    if SUB == None:
        SUB = servers.get("RAW")
    vidstreaming = SUB.get("Vidstreaming")
    
    if vidstreaming == None:
        print("Vidstreaming is not available, it's probably a new upload. HD-2 are slow and often block auto download. Please wait a while, Vidstreaming might get uploaded soon")
        exit()
    
    embed_link = await async_fetch_json(BASE_LINK+"/ajax/episode/sources?id="+str(vidstreaming))
    embed_link = embed_link.get("link")
    embed_link = embed_link[len("https://rapid-cloud.co/embed-2/v2/e-1/"):embed_link.find('?')]
    embed_link = "https://rapid-cloud.co/embed-2/v2/e-1/getSources?id=" + embed_link
    print(embed_link)



    rapidcloud_source    = await async_fetch_json(embed_link, headers={"referer":"https://rapid-cloud.co/"})
    m3u8_link    = rapidcloud_source.get("sources")[0].get("file")
    print(m3u8_link)
    
    #eng_sub_link = rapidcloud_source.get("tracks")[0].get("file") # overhauled
    eng_sub_link = None

    rapidcloud_subs_dict = rapidcloud_source.get("tracks")
    for i in rapidcloud_subs_dict:
        if("English" in i.get("label")):
            eng_sub_link = i.get("file")
            break
    if(eng_sub_link == None):
        print(f"{COLORS['YELLOW']}No English subtitle were found! Skipping subtitle download.{COLORS['END']}")

    print("downloading episode: "+episode)
    print("selected quality   : "+str(quality))
    print("fetching m3u8...")
    #m3u8_link = m3u8_link[:m3u8_link.rfind('/')]+f"/index-f{args.quality}-v1-a1.m3u8" # this need to be fixed later, some show doesn't have format, only index-v1-a1.m3u8
    m3u8_link = m3u8_link[:m3u8_link.rfind('/')+1]+b64.b64encode(bytes(f"index-f{args.quality}-v1-a1.m3u8",'utf-8')).decode("utf-8")+".m3u8"
    m3u8 = await async_fetch_http(m3u8_link)
    m3u8 = m3u8.decode()

    # download eng sub
    if(eng_sub_link != None):
        print("downloading sub...")
        with open(episode+".vtt",'wb') as f:
            data = await async_fetch_http(eng_sub_link)
            f.write(data)

    # generate and save local m3u8 on working directory
    localized_m3u8 = hls_tools.localize_m3u8(m3u8, os.getcwd())
    with open("./local.m3u8",'w') as f:
        f.write(localized_m3u8)

    # download the segment
    segment_links =  hls_tools.get_segment_links(m3u8)
    segment_filenames = hls_tools.get_segment_filenames_fixed_extension(m3u8)
    async with aiohttp.ClientSession() as session:
        tasks = [download_segment(session, url, filename) for url, filename in zip(segment_links, segment_filenames)]
        await asyncio.gather(*tasks)

    out = (
        ffmpeg
        .input("local.m3u8", fflags="+genpts")
        .output(episode+".mp4", c="copy", avoid_negative_ts="make_zero")
    )
    try:
        ffmpeg.run(out, quiet=False)
    except ffmpeg.Error as e:
        print("FFmpeg failed!")
        print(e.stderr.decode())   # Full FFmpeg output
        exit(1)
        return

    # delete local.m3u8 and segments after ffmpeg done merging (only if ffmpeg exited successfully)
    for file in Path().glob("c2VnL*"):
        print("Deleting "+str(file))
        file.unlink()
    print("Deleting local.m3u8")
    os.unlink("./local.m3u8")


if __name__ == "__main__":
    asyncio.run(main())
