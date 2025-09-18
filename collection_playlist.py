import sys
import re
import requests
from ipytv import playlist
from ipytv.playlist import M3UPlaylist
from ipytv.channel import IPTVAttr, IPTVChannel

g_source_m3u_list = [
    # see https://t.me/feiyangofficalchannel/1371, # https://github.com/mursor1985/LIVE
    "https://github.com/Kimentanm/aptv/raw/refs/heads/master/m3u/jsyd.m3u",  # https://github.com/Kimentanm/aptv/
    "https://github.com/Kimentanm/aptv/raw/refs/heads/master/m3u/iptv.m3u",
    "https://github.com/suxuang/myIPTV/raw/refs/heads/main/ipv6.m3u",  # https://github.com/suxuang/myIPTV
    "https://github.com/suxuang/myIPTV/raw/refs/heads/main/ipv4.m3u",
    # "https://tv-1.iill.top/m3u/Gather",  # YanG/Gather
    # "https://tv-1.iill.top/m3u/Sport",  # YanG/Sport
    "https://raw.githubusercontent.com/YueChan/Live/main/APTV.m3u",  # https://github.com/YueChan/Live
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u",  # https://github.com/fanmingming/live
    "https://github.com/vbskycn/iptv/raw/refs/heads/master/tv/iptv4.m3u",  # https://github.com/vbskycn/iptv
    # "https://github.com/vbskycn/iptv/raw/refs/heads/master/tv/iptv6.m3u",
]

g_source_m3u_list_ua = {
    # 'url': 'user-agent'
}

s_epg_urls = [
    "https://11.112114.xyz/pp.xml",
    "https://epg.aptv.app/pp.xml.gz",
    "http://epg.51zmt.top:8000/e.xml",
]

g_static_medias = [
    # (name, url, attributes)
    ("五星体育", "https://cdn3.163189.xyz/163189/wxty", {
        "tvg-logo": "https://live.fanmingming.cn/tv/五星体育.png"
    }),
    # copy from mursor
    ("五星体育", "https://gdcucc.v1.mk/gdcucc/wxty.m3u8", {
        "tvg-logo": "https://live.fanmingming.cn/tv/五星体育.png",
        "http-user-agent": "okHttp/Mod-1.4.0.0"
    }),
]

g_target_channels_tuple = [
    # (search regex, name)
    (r"^\s*CCTV-?5\s*(体育)?\s*$", "CCTV5"),
    (r"^\s*CCTV-?5(\+|p|plus)+\s*(体育赛事)?\s*$", "CCTV5+"),
    ("五星体育", "五星体育"),
    ("广东体育", "广东体育"),
    (r"Sky\s*Sports\s*F1", "Sky Sports F1"),
]

g_black_keywords = ["广播", "伴音", "Radio"]

g_normal_attrs_keys = [
    IPTVAttr.GROUP_TITLE.value,  # group-title
    IPTVAttr.TVG_NAME.value,  # tvg-name
    IPTVAttr.TVG_ID.value,  # tvg-id
    IPTVAttr.TVG_LOGO.value,  # tvg-logo
]


def create_iptv_channel(media):
    (name, url, attrs) = media if len(media) == 3 else (media[0], media[1], {})
    channel = IPTVChannel(
        name=name,
        url=url,
        duration="-1",
        attributes={
            IPTVAttr.GROUP_TITLE.value: name,
            IPTVAttr.TVG_ID.value: name,
        },
    )
    channel.attributes.update(attrs)
    return channel


def get_static_channels():
    return list(map(create_iptv_channel, g_static_medias))


def get_m3u_raw_from_url(url):
    try:
        response = requests.get(url)
        print(response.request.headers)
        # print(response.headers)
        return response.text
    except Exception as e:
        print(f"Error occurred while downloading {url}: {e}")
    return None


def is_black_channel(name):
    for bn in g_black_keywords:
        if bn in name:
            return True
    return False


def find_target_channels(m3u_raw, ua=None):
    # fix m3u defind
    m3u_raw = re.sub(r"#EXTINF:-1([,:;])", "#EXTINF:-1 ", m3u_raw, flags=re.M)
    channels = []
    try:
        pl = playlist.loads(m3u_raw)
    except Exception as e:
        print(f"Error occurred while parsing M3U: {e}, {m3u_raw[:100]}")
        return channels

    epg_url = pl.get_attributes().get('x-tvg-url', None)
    print(f"EPG URL: {epg_url}")
    if epg_url:
        epg_urls = epg_url.split(',') if epg_url else []
        s_epg_urls.extend(epg_urls)

    for regex, t_name in g_target_channels_tuple:
        new_pl = pl.search(
            regex,
            where=[
                "name",
                "attributes.tvg-id",
                #    "attributes.tvg-name",# some channels have wrong tvg-name
                #    "attributes.group-title",
            ],
            case_sensitive=False)
        for media in new_pl:
            if is_black_channel(media.name):
                continue
            print(
                f"Found target channel: {media}, regex: {regex}, name: {t_name}"
            )
            media.name = t_name
            media.attributes[IPTVAttr.GROUP_TITLE.value] = t_name
            media.attributes[IPTVAttr.TVG_ID.value] = t_name
            media.attributes.pop(IPTVAttr.TVG_NAME.value, None)
            if ua:
                media.attributes["http-user-agent"] = ua
            # sort attributes
            media.attributes = {
                k: media.attributes[k]
                for k in sorted(media.attributes.keys())
            }
            # remove extras
            media.extras = []
            channels.append(media)
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
        result = find_target_channels(m3u_raw,
                                      ua=g_source_m3u_list_ua.get(url))
        channel_list.extend(result)
        print(f"Finished processing source: {url}\n")

    print(f"Adding static channels, total: {len(g_static_medias)}")
    channel_list.extend(get_static_channels())

    # remove duplicate channels
    channel_list = list({
        (c.url, get_channel_extend_attributes(c)): c
        for c in channel_list
    }.values())
    # sort by group and name
    channel_list.sort(key=lambda c: (c.attributes.get(
        IPTVAttr.GROUP_TITLE.value, c.name), c.name))

    print(f"Create playlist, total: {len(channel_list)}")

    # deduplicate and sort epg urls
    epg_urls = list(set(s_epg_urls))
    epg_urls.sort()
    print(f"EPG URLs: {epg_urls}")

    m3u_pl = M3UPlaylist()
    m3u_pl.add_attributes({"x-tvg-url": ",".join(epg_urls)})
    m3u_pl.append_channels(channel_list)

    with open('f1tv.m3u', 'w', encoding='utf-8') as out_file:
        content = m3u_pl.to_m3u_plus_playlist()
        out_file.write(content)
    print(f"Playlist saved to f1tv.m3u")


if __name__ == "__main__":
    main(sys.argv[1:])
