"""Render a macOS-style "Music" card (SVG) from a Last.fm profile.

Usage: LASTFM_API_KEY=... python3 scripts/music_card.py dist/music.svg
"""
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

API = "https://ws.audioscrobbler.com/2.0/"
UA = {"User-Agent": "github-profile-music-card"}
PLACEHOLDER = "2a96cbd8b46e442fc41c2b86b821562f"  # Last.fm's grey star image
UI = "-apple-system, 'SF Pro Text', 'Segoe UI', Helvetica, Arial, sans-serif"
W = 680


def parse(recent, top, info):
    for payload in (recent, top, info):
        if "error" in payload:
            raise ValueError(f"Last.fm error {payload['error']}: {payload.get('message', '')}")

    tracks = recent.get("recenttracks", {}).get("track", [])
    tracks = [tracks] if isinstance(tracks, dict) else tracks
    track = None
    if tracks:
        t = tracks[0]
        images = {i.get("size"): i.get("#text", "") for i in t.get("image", [])}
        cover = images.get("extralarge") or images.get("large") or ""
        track = {
            "name": t.get("name", ""),
            "artist": t.get("artist", {}).get("#text", ""),
            "now_playing": t.get("@attr", {}).get("nowplaying") == "true",
            "cover_url": cover if cover and PLACEHOLDER not in cover else None,
        }

    artists = top.get("topartists", {}).get("artist", [])
    artists = [artists] if isinstance(artists, dict) else artists
    return {
        "track": track,
        "top": [{"name": a["name"], "plays": int(a["playcount"])} for a in artists[:5]],
        "scrobbles": int(info.get("user", {}).get("playcount", 0)),
    }


def cut(text, limit):
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def esc(text):
    return escape(text, {'"': "&quot;"})


def render(data, cover):
    track, top = data["track"], data["top"]
    playing = bool(track and track["now_playing"])
    label = "Now playing" if playing else "Recently played"
    name = cut(track["name"], 40) if track else "Nothing played yet"
    artist = cut(track["artist"], 48) if track else ""
    title = f"Last.fm: {label} {name}" + (f" by {artist}" if artist else "")

    rows_y = 184
    rows = max(len(top), 1)
    height = rows_y + (rows - 1) * 26 + 24
    best = max((a["plays"] for a in top), default=1) or 1

    if cover:
        art = f'<image href="{esc(cover)}" x="20" y="44" width="72" height="72" preserveAspectRatio="xMidYMid slice" clip-path="url(#cov)"/>'
    else:
        art = ('<rect x="20" y="44" width="72" height="72" rx="8" fill="url(#ph)"/>'
               '<text x="56" y="88" text-anchor="middle" font-size="26" fill="#8e8e93">♪</text>')

    label_x = 108
    eq = ""
    if playing:
        bars = "".join(f'<rect x="{108 + i * 4}" y="53" width="2" height="10" rx="1"/>' for i in range(4))
        eq = f'<g class="eq" fill="#ff9f0a">{bars}</g>'
        label_x = 130

    if top:
        lines = []
        for i, a in enumerate(top):
            y = rows_y + i * 26
            bar = max(4, round(340 * a["plays"] / best))
            lines.append(
                f'<text x="20" y="{y}" class="dim">{i + 1}</text>'
                f'<text x="44" y="{y}" class="fg">{esc(cut(a["name"], 28))}</text>'
                f'<rect x="260" y="{y - 6}" width="{bar}" height="4" rx="2" fill="#ff9f0a" opacity=".85"/>'
                f'<text x="660" y="{y}" class="dim" text-anchor="end">{a["plays"]:,}</text>'
            )
        stat_rows = "".join(lines)
    else:
        stat_rows = f'<text x="20" y="{rows_y}" class="dim">No top artists yet</text>'

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-labelledby="t">
<title id="t">{esc(title)}</title>
<style>
  text {{ font-family: {UI}; }}
  .fg {{ fill: #ececec; font-size: 13px; }}
  .dim {{ fill: #8e8e93; font-size: 13px; font-variant-numeric: tabular-nums; }}
  .cap {{ font-size: 10px; font-weight: 600; letter-spacing: 1px; }}
  .eq rect {{ transform-box: fill-box; transform-origin: 50% 100%; animation: eq 1s ease-in-out infinite; }}
  .eq rect:nth-child(2) {{ animation-delay: -.3s; }}
  .eq rect:nth-child(3) {{ animation-delay: -.6s; }}
  .eq rect:nth-child(4) {{ animation-delay: -.15s; }}
  @keyframes eq {{ 0%, 100% {{ transform: scaleY(.3); }} 50% {{ transform: scaleY(1); }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>
<defs>
  <clipPath id="win"><rect width="{W}" height="{height}" rx="10"/></clipPath>
  <clipPath id="cov"><rect x="20" y="44" width="72" height="72" rx="8"/></clipPath>
  <linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3a3a"/><stop offset="1" stop-color="#2e2e2e"/></linearGradient>
  <linearGradient id="ph" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3a3a3c"/><stop offset="1" stop-color="#6e6e73"/></linearGradient>
</defs>
<g clip-path="url(#win)">
  <rect width="{W}" height="{height}" fill="#1e1e1e"/>
  <rect width="{W}" height="28" fill="url(#bar)"/>
  <line x1="0" y1="28.5" x2="{W}" y2="28.5" stroke="#3d3d3d"/>
  <circle cx="20" cy="14" r="6" fill="#ff5f57"/><circle cx="40" cy="14" r="6" fill="#febc2e"/><circle cx="60" cy="14" r="6" fill="#28c840"/>
  <text x="{W // 2}" y="18" text-anchor="middle" font-size="12" font-weight="500" fill="#a1a1a6">Music</text>
  {art}
  {eq}
  <text x="{label_x}" y="62" class="cap" fill="{'#ff9f0a' if playing else '#8e8e93'}">{label.upper()}</text>
  <text x="108" y="87" font-size="16" font-weight="600" fill="#f5f5f7">{esc(name)}</text>
  <text x="108" y="108" font-size="13" fill="#8e8e93">{esc(artist)}</text>
  <line x1="20" y1="136.5" x2="{W - 20}" y2="136.5" stroke="#3d3d3d"/>
  <text x="20" y="160" class="cap" fill="#8e8e93">TOP ARTISTS · LAST 30 DAYS</text>
  <text x="660" y="160" class="cap" fill="#8e8e93" text-anchor="end">{data["scrobbles"]:,} SCROBBLES</text>
  {stat_rows}
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{height - 1}" rx="10" fill="none" stroke="#3d3d3d"/>
</svg>
"""


def api(method, key, user, **params):
    query = urllib.parse.urlencode({"method": method, "user": user, "api_key": key, "format": "json", **params})
    with urllib.request.urlopen(urllib.request.Request(f"{API}?{query}", headers=UA), timeout=15) as r:
        return json.load(r)


def cover_data_uri(url):
    if not url:
        return None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
            kind = r.headers.get_content_type() or "image/jpeg"
            return f"data:{kind};base64,{base64.b64encode(r.read()).decode()}"
    except Exception as e:  # a missing cover must not block the card
        print(f"cover skipped: {e}", file=sys.stderr)
        return None


def main():
    key = os.environ.get("LASTFM_API_KEY")
    if not key:
        sys.exit("LASTFM_API_KEY is not set")
    user = os.environ.get("LASTFM_USER", "AceBreaker420")
    out = sys.argv[1] if len(sys.argv) > 1 else "dist/music.svg"

    data = parse(
        api("user.getrecenttracks", key, user, limit=1),
        api("user.gettopartists", key, user, period="1month", limit=5),
        api("user.getinfo", key, user),
    )
    svg = render(data, cover_data_uri(data["track"] and data["track"]["cover_url"]))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out}: {data['track'] and data['track']['name']!r}")


if __name__ == "__main__":
    main()
