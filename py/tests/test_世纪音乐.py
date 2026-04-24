import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("sjmusic_spider", str(ROOT / "世纪音乐.py")).load_module()
Spider = MODULE.Spider


HOME_HTML = """
<html>
  <body>
    <ul id="datalist">
      <li>
        <div class="name"><a class="url" href="/mp3/123.html">夜曲</a></div>
        <div class="singer">周杰伦</div>
        <div class="pic"><img src="/img/song.jpg"></div>
      </li>
    </ul>
    <ul class="video_list">
      <li>
        <div class="name"><a href="/mp4/456.html">稻香MV</a></div>
        <div class="pic"><img src="/img/mv.jpg"></div>
      </li>
    </ul>
  </body>
</html>
"""

PLAYLIST_HTML = """
<html><body>
  <ul class="video_list">
    <li>
      <div class="name"><a href="/playlist/gedan001.html">华语经典</a></div>
      <div class="pic"><img src="/img/list.jpg"></div>
    </li>
  </ul>
</body></html>
"""

SINGER_HTML = """
<html><body>
  <ul class="singer_list">
    <li>
      <div class="pic"><a href="/singer/zhoujielun.html"><img src="/img/singer.jpg"></a></div>
      <div class="name"><a>周杰伦</a></div>
    </li>
  </ul>
</body></html>
"""

MV_HTML = """
<html><body>
  <ul class="video_list">
    <li>
      <div class="name"><a href="/mp4/999.html">晴天MV</a></div>
      <div class="pic"><img src="/img/mv2.jpg"></div>
    </li>
  </ul>
</body></html>
"""

SEARCH_HTML = """
<html><body>
  <ul class="play_list">
    <li><div class="name"><a href="/mp3/777.html">七里香</a></div><img src="/img/1.jpg"></li>
    <li><div class="name"><a href="/mp4/778.html">七里香MV</a></div><img src="/img/2.jpg"></li>
    <li><div class="name"><a href="/playlist/top777.html">周董精选</a></div><img src="/img/3.jpg"></li>
    <li><div class="name"><a href="/singer/jay.html">周杰伦</a></div><img src="/img/4.jpg"></li>
  </ul>
</body></html>
"""

RANK_HTML = """
<html><body>
  <ul class="play_list">
    <li><div class="name"><a href="/mp3/321.html">搁浅</a></div></li>
    <li><div class="name"><a href="/mp3/322.html">简单爱</a></div></li>
  </ul>
</body></html>
"""

SONG_HTML = """
<html><head><title>夜曲_世纪音乐</title></head><body>
  <h1>夜曲</h1>
  <div class="play_singer"><div class="name"><a>周杰伦</a></div></div>
  <div class="playhimg"><img src="/img/song_detail.jpg"></div>
</body></html>
"""

MV_DETAIL_HTML = """
<html><head><title>晴天MV_世纪音乐</title></head><body>
  <h1>晴天MV</h1>
  <div class="play_singer"><div class="name"><a>周杰伦</a></div></div>
  <div class="playhimg"><img src="/img/mv_detail.jpg"></div>
</body></html>
"""

PLAYLIST_DETAIL_HTML = """
<html><body>
  <h1>周董歌单</h1>
  <div class="pic"><img src="/img/playlist.jpg"></div>
  <ul class="play_list">
    <li><div class="name"><a href="/mp3/401.html">安静</a></div></li>
    <li><div class="name"><a href="/mp3/402.html">晴天</a></div></li>
  </ul>
</body></html>
"""

SINGER_DETAIL_HTML = """
<html><body>
  <h1>周杰伦</h1>
  <div class="singer_info"><div class="info"><p>华语男歌手</p></div></div>
  <div class="pic"><img src="/img/singer_detail.jpg"></div>
  <ul class="play_list">
    <li><div class="name"><a href="/mp3/501.html">青花瓷</a></div></li>
    <li><div class="name"><a href="/mp3/502.html">稻香</a></div></li>
  </ul>
</body></html>
"""


class TestSJMusicSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    @patch.object(Spider, "fetch")
    def test_home_content_returns_classes_filters_and_home_items(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(status_code=200, text=HOME_HTML)
        result = self.spider.homeContent(False)
        self.assertEqual(
            [item["type_id"] for item in result["class"]],
            ["home", "rank_list", "playlist", "singer", "mv"],
        )
        self.assertIn("singer", result["filters"])
        self.assertEqual(result["list"][0]["vod_id"], "song:123")
        self.assertEqual(result["list"][0]["vod_name"], "周杰伦 - 夜曲")
        self.assertEqual(result["list"][1]["vod_id"], "mv:456")

    @patch.object(Spider, "fetch")
    def test_home_video_content_reuses_home_list(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(status_code=200, text=HOME_HTML)
        result = self.spider.homeVideoContent()
        self.assertEqual([item["vod_id"] for item in result["list"]], ["song:123", "mv:456"])

    @patch.object(Spider, "fetch")
    def test_category_content_supports_rank_playlist_singer_and_mv(self, mock_fetch):
        mock_fetch.side_effect = [
            SimpleNamespace(status_code=200, text=PLAYLIST_HTML),
            SimpleNamespace(status_code=200, text=SINGER_HTML),
            SimpleNamespace(status_code=200, text=MV_HTML),
        ]
        rank_result = self.spider.categoryContent("rank_list", "1", False, {})
        playlist_result = self.spider.categoryContent("playlist", "1", False, {"lang": "index"})
        singer_result = self.spider.categoryContent(
            "singer",
            "1",
            False,
            {"sex": "girl", "area": "huayu", "char": "index"},
        )
        mv_result = self.spider.categoryContent(
            "mv",
            "1",
            False,
            {"area": "index", "type": "index", "sort": "new"},
        )
        self.assertTrue(rank_result["list"][0]["vod_id"].startswith("rank:"))
        self.assertEqual(playlist_result["list"][0]["vod_id"], "playlist:gedan001")
        self.assertEqual(singer_result["list"][0]["vod_id"], "singer:zhoujielun")
        self.assertEqual(mv_result["list"][0]["vod_id"], "mv:999")

    @patch.object(Spider, "fetch")
    def test_search_content_maps_link_types_and_blank_keyword(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(status_code=200, text=SEARCH_HTML)
        result = self.spider.searchContent("周杰伦", False, "1")
        self.assertEqual(
            [item["vod_id"] for item in result["list"]],
            ["song:777", "mv:778", "playlist:top777", "singer:jay"],
        )
        self.assertEqual(
            self.spider.searchContent("", False, "1"),
            {"page": 1, "limit": 0, "total": 0, "list": []},
        )

    def test_category_content_returns_empty_for_unknown_tid(self):
        self.assertEqual(
            self.spider.categoryContent("unknown", "1", False, {}),
            {"page": 1, "limit": 0, "total": 0, "list": []},
        )

    @patch.object(Spider, "fetch")
    def test_detail_content_builds_rank_song_mv_playlist_and_singer(self, mock_fetch):
        mock_fetch.side_effect = [
            SimpleNamespace(status_code=200, text=RANK_HTML),
            SimpleNamespace(status_code=200, text=SONG_HTML),
            SimpleNamespace(status_code=200, text=MV_DETAIL_HTML),
            SimpleNamespace(status_code=200, text=PLAYLIST_DETAIL_HTML),
            SimpleNamespace(status_code=200, text=SINGER_DETAIL_HTML),
        ]
        rank_vod = self.spider.detailContent(["rank:rise"])["list"][0]
        song_vod = self.spider.detailContent(["song:123"])["list"][0]
        mv_vod = self.spider.detailContent(["mv:456"])["list"][0]
        playlist_vod = self.spider.detailContent(["playlist:top100"])["list"][0]
        singer_vod = self.spider.detailContent(["singer:jay"])["list"][0]
        self.assertEqual(rank_vod["vod_play_url"], "搁浅$music:321#简单爱$music:322")
        self.assertEqual(song_vod["vod_play_url"], "周杰伦 - 夜曲$music:123")
        self.assertEqual(mv_vod["vod_play_url"], "晴天MV$vplay:456:1080")
        self.assertEqual(playlist_vod["vod_play_url"], "安静$music:401#晴天$music:402")
        self.assertEqual(singer_vod["vod_play_url"], "青花瓷$music:501#稻香$music:502")


if __name__ == "__main__":
    unittest.main()
