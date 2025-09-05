import sys
import re
import difflib
import requests
from ipytv import playlist
from ipytv.playlist import M3UPlaylist
from ipytv.channel import IPTVAttr, IPTVChannel

g_source_m3u_list = [
    "https://github.com/mursor1985/LIVE/raw/refs/heads/main/iptv.m3u",  # https://github.com/mursor1985/LIVE, https://sub.ottiptv.cc/iptv.m3u
    "https://raw.githubusercontent.com/Kimentanm/aptv/master/m3u/iptv.m3u",  # https://github.com/Kimentanm/aptv/
    "https://github.com/suxuang/myIPTV/raw/refs/heads/main/ipv6.m3u",  # https://github.com/Kimentanm/aptv/
    "https://github.com/suxuang/myIPTV/raw/refs/heads/main/ipv4.m3u",  # https://github.com/suxuang/myIPTV
    "https://tv-1.iill.top/m3u/Gather",  # YanG/Gather
    "https://tv-1.iill.top/m3u/Sport",  # YanG/Sport
    "https://raw.githubusercontent.com/YueChan/Live/main/APTV.m3u",  # https://github.com/YueChan/Live
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u",  # https://github.com/fanmingming/live
]

g_epg_urls = [
    "https://11.112114.xyz/pp.xml", "https://epg.aptv.app/pp.xml.gz",
    "https://epg.aptv.app/xml", "https://live.fanmingming.cn/e.xml"
]

g_static_medias = [
    # (name, url, attributes)
    ("五星体育", "https://cdn3.163189.xyz/163189/wxty"),
]

g_channel_group_mapper = [
    # [group_name, media_name1, media_name2, ...]
    ["CCTV5+", "CCTV5PLUS", "CCTV5p"],
    ["Sky Sports F1", "SkySportsF1"],
]

g_target_channel_names = [
    "五星体育",
    "广东体育",
] + g_channel_group_mapper[0] + g_channel_group_mapper[1] + ["CCTV5"]

g_black_keywords = ["广播", "伴音"]

g_key_group_title = IPTVAttr.GROUP_TITLE.value

g_normal_attrs_keys = [
    IPTVAttr.GROUP_TITLE.value,
    IPTVAttr.TVG_NAME.value,
    IPTVAttr.TVG_ID.value,
    IPTVAttr.TVG_LOGO.value,
]


def create_iptv_channel(media):
    (name, url, attrs) = media if len(media) == 3 else (media[0], media[1], {})
    channel = IPTVChannel(
        name=name,
        url=url,
        duration="-1",
        attributes={g_key_group_title: find_channel_group(name)},
    )
    channel.attributes.update(attrs)
    return channel


def get_static_channels():
    return list(map(create_iptv_channel, g_static_medias))


def get_m3u_raw_from_url(url):
    try:
        response = requests.get(url, headers={"User-Agent": "iPlayTV/3.3.9"})
        return response.text
    except Exception as e:
        print(f"Error occurred while downloading {url}: {e}")
    return None


def find_channel_group(name):
    for mapper in g_channel_group_mapper:
        for n in mapper[1:]:
            if n in name:
                return mapper[0]
    return name


def get_standard_channel_name(name):
    for tn in g_target_channel_names:
        if tn in name:
            return tn
    return name


def is_target_channel(name):
    for tn in g_target_channel_names:
        if tn in name:
            return True
    return False


def is_black_channel(name):
    for bn in g_black_keywords:
        if bn in name:
            return True
    return False


def find_target_channels(m3u_raw):
    # fix m3u defind
    m3u_raw = re.sub(r"#EXTINF:-1([,:;])", "#EXTINF:-1 ", m3u_raw, flags=re.M)
    channels = []
    try:
        pl = playlist.loads(m3u_raw)
    except Exception as e:
        print(f"Error occurred while parsing M3U: {e}, {m3u_raw[:100]}")
        return channels

    for media in pl:
        name = media.attributes.get(
            IPTVAttr.TVG_NAME.value,
            media.attributes.get(IPTVAttr.TVG_ID.value, media.name)).strip()
        # print(f"Checking channel: {name}")
        if is_target_channel(name) and not is_black_channel(name):
            name = get_standard_channel_name(name)
            media.name = name
            media.attributes[g_key_group_title] = find_channel_group(name)
            channels.append(media)
            print(f"Found target channel: {media}")
            continue
    return channels


def get_channel_extend_attributes(channel):
    attrs = channel.attributes.copy()
    for k in g_normal_attrs_keys:
        attrs.pop(k, None)
    return frozenset(attrs.items())


def main(args):
    channel_list = []
    for url in g_source_m3u_list:
        print(f"Processing source: {url}")
        m3u_raw = get_m3u_raw_from_url(url)
        if m3u_raw is None:
            continue
        # print(m3u_raw)
        result = find_target_channels(m3u_raw)
        channel_list.extend(result)
        print(f"Finished processing source: {url}")
        print("\n")

    print(f"Adding static channels")
    channel_list.extend(get_static_channels())

    # remove duplicate channels
    channel_list = list({
        (c.url, get_channel_extend_attributes(c)): c
        for c in channel_list
    }.values())
    # sort by group and name
    channel_list.sort(
        key=lambda c: (c.attributes.get(g_key_group_title, c.name), c.name))

    m3u_pl = M3UPlaylist()
    m3u_pl.add_attributes({"x-tvg-url": ",".join(g_epg_urls)})
    m3u_pl.append_channels(channel_list)

    with open('f1tv.m3u', 'w', encoding='utf-8') as out_file:
        content = m3u_pl.to_m3u_plus_playlist()
        out_file.write(content)


if __name__ == "__main__":
    main(sys.argv[1:])
