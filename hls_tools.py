import re
from pathlib import Path

def localize_m3u8(m3u8: str, video_path: str) -> str:
    lines: list = []
    for i in m3u8.split():
        if "https://" in i:
            filename_fixed: str = Path(i).stem + ".ts"
            lines.append(str(Path(video_path) / filename_fixed))
        else:
            lines.append(i)
    return "\n".join(lines)


def get_segment_links(m3u8: str) -> list:
    return [i for i in m3u8.split() if "https://" in i]

def get_segment_filenames_fixed_extension(m3u8: str) -> list:
    return [Path(i).stem + ".ts" for i in m3u8.split() if "https://" in i]


def is_valid_ts(filename: str) -> bool:
    file_size: int = Path(filename).stat().st_size
    if file_size < 1000: # a segment below 1kb is probably corrupted
        return False;

    with open(filename,'rb') as f:
        data = f.read(1024)

    # checking mpegts sync byte at beginning
    if data[0] != 0x47:
        return False

    # checking the subsequent mpegts sync byte, it presented every 188 bytes
    for offset in (188,188*2,188*3,188*4,188*5):
        if offset < len(data) and data[offset] != 0x47:
            return False

    return True


def parse_master_m3u8(master) -> list:
    # regex to capture STREAM-INF blocks but skip I-FRAME
    pattern = re.compile(
        r'(?<!I-FRAME-)#EXT-X-STREAM-INF:([^\n]+)\n([^\n]+)'
    )

    # regex to extract key=value pairs
    kv_pattern = re.compile(r'(\w+)=(".*?"|[^,]+)')

    results = []

    for attr_str, uri in pattern.findall(master):
        attrs = {}
        for key, val in kv_pattern.findall(attr_str):
            val = val.strip('"')
            if key == "RESOLUTION" and 'x' in val:
                w, h = val.split('x')
                val = (int(w), int(h))
            elif key == "BANDWIDTH":
                val = int(val)
            elif key == "FRAME-RATE":
                val = float(val)
            attrs[key.lower()] = val

        attrs["uri"] = uri.strip()
        results.append(attrs)

    return results
    



if __name__ == "__main__":
    m3u8 = open('./samples/index-f3-v1-a1.m3u8').read()

    a = localize_m3u8(m3u8,'/dsg/ageha/hbwh/jsxdf/')
    b = get_segment_links(m3u8)
    c = get_segment_filenames_fixed_extension(m3u8)
    #print(c)

    print(is_valid_ts("./samples/seg-1-v1-a1.jpg"))
    print(is_valid_ts("./samples/index-f3-v1-a1.m3u8"))
