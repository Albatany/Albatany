import unittest
import xml.etree.ElementTree as ET

from music_card import parse, render

PLACEHOLDER = "https://lastfm.freetls.fastly.net/i/u/300x300/2a96cbd8b46e442fc41c2b86b821562f.png"
COVER = "https://lastfm.freetls.fastly.net/i/u/300x300/abc123.jpg"


def track(name, artist, cover=COVER, playing=False):
    t = {
        "name": name,
        "artist": {"#text": artist},
        "image": [
            {"#text": cover.replace("300x300", "34s"), "size": "small"},
            {"#text": cover, "size": "extralarge"},
        ],
    }
    if playing:
        t["@attr"] = {"nowplaying": "true"}
    return t


def recent(*tracks):
    return {"recenttracks": {"track": list(tracks)}}


TOP = {"topartists": {"artist": [{"name": "Enola", "playcount": "86"}, {"name": "Keep", "playcount": "54"}]}}
INFO = {"user": {"playcount": "1284"}}


def data(name="Does Anyone Else", artist="Enola", playing=True, top=None, scrobbles=1284):
    return {
        "track": {"name": name, "artist": artist, "now_playing": playing, "cover_url": None},
        "top": top if top is not None else [{"name": "Enola", "plays": 86}, {"name": "Keep", "plays": 54}],
        "scrobbles": scrobbles,
    }


class ParseTest(unittest.TestCase):
    def test_parse_now_playing_first_track(self):
        d = parse(recent(track("Now Song", "Enola", playing=True), track("Old Song", "Keep")), TOP, INFO)
        self.assertEqual(d["track"]["name"], "Now Song")
        self.assertIs(d["track"]["now_playing"], True)
        self.assertEqual(d["scrobbles"], 1284)
        self.assertEqual(d["top"][0], {"name": "Enola", "plays": 86})

    def test_parse_ignores_placeholder_cover(self):
        for url in ("", PLACEHOLDER):
            d = parse(recent(track("A", "B", cover=url)), TOP, INFO)
            self.assertIsNone(d["track"]["cover_url"])
        d = parse(recent(track("A", "B")), TOP, INFO)
        self.assertEqual(d["track"]["cover_url"], COVER)

    def test_parse_raises_on_api_error(self):
        err = {"error": 10, "message": "Invalid API key"}
        for args in ((err, TOP, INFO), (recent(), err, INFO), (recent(), TOP, err)):
            with self.assertRaises(ValueError):
                parse(*args)


class RenderTest(unittest.TestCase):
    def test_render_escapes_and_is_valid_xml(self):
        svg = render(data(name='Tom & Jerry <3 "live"'), None)
        ET.fromstring(svg)
        self.assertIn("Tom &amp; Jerry &lt;3", svg)

    def test_render_now_playing_vs_recent(self):
        svg = render(data(playing=True), None)
        self.assertIn("Now playing", svg)
        self.assertIn('class="eq"', svg)
        svg = render(data(playing=False), None)
        self.assertIn("Recently played", svg)
        self.assertNotIn('class="eq"', svg)

    def test_render_truncates_long_names(self):
        long_name = "x" * 120
        svg = render(data(name=long_name), None)
        self.assertIn("…", svg)
        self.assertNotIn(long_name, svg)

    def test_render_empty_account(self):
        svg = render({"track": None, "top": [], "scrobbles": 0}, None)
        ET.fromstring(svg)
        self.assertIn("Nothing played yet", svg)

    def test_render_cover(self):
        self.assertNotIn("<image", render(data(), None))
        svg = render(data(), "data:image/jpeg;base64,AAAA")
        self.assertIn("<image", svg)
        self.assertIn('href="data:image/jpeg;base64,AAAA"', svg)


if __name__ == "__main__":
    unittest.main()
