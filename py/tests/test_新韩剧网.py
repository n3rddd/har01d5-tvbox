import base64
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("hanju7_spider", str(ROOT / "新韩剧网.py")).load_module()
Spider = MODULE.Spider


def encrypt_player_payload(url):
    iv = b"0123456789abcdef"
    key = MODULE.PLAYER_AES_KEY.encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    body = cipher.encrypt(pad(url.encode("utf-8"), AES.block_size))
    return base64.b64encode(iv + body).decode("utf-8")


HOME_HTML = """
<div class="list">
  <ul>
    <li>
      <a href="/detail/abc123.html" title="苦尽柑来遇见你" data-original="//img.example.com/a.jpg">苦尽柑来遇见你</a>
      <span>更新至第2集</span>
    </li>
    <li>
      <a href="/detail/def456.html" data-original="/upload/b.jpg">机智住院医生生活</a>
      <span>2026-04-24</span>
    </li>
  </ul>
</div>
"""

LIST_HTML = """
<div class="list">
  <ul>
    <li>
      <a class="tu" href="/detail/xyz001.html" title="电影A" data-original="//img.example.com/m1.jpg"></a>
      <span class="tip">HD</span>
    </li>
    <li>
      <a class="tu" href="/detail/xyz002.html" title="电影B"></a>
      <span class="tip">完结</span>
    </li>
  </ul>
</div>
"""

SEARCH_HTML = """
<div class="txt">
  <ul>
    <li id="t">header</li>
    <li>
      <p id="name"><a href="/detail/search001.html">新乌托邦(12)</a></p>
      <p id="actor">朴正民 / 金智秀</p>
    </li>
    <li>
      <p id="name"><a href="/detail/search002.html">协商的技术</a></p>
      <p id="actor">李帝勋</p>
    </li>
  </ul>
</div>
"""

DETAIL_HTML = """
<div class="detail">
  <div class="pic"><img data-original="//img.example.com/poster.jpg" /></div>
  <div class="info">
    <dl><dd>比天堂还美丽</dd></dl>
    <dl><dd>金惠子 / 孙锡久</dd></dl>
    <dl><dd>韩国</dd></dl>
    <dl><dd>剧情</dd></dl>
    <dl><dd>更新至第3集</dd></dl>
    <dl><dd>2026</dd></dl>
  </div>
</div>
<div class="juqing">一段剧情简介</div>
<div id="playlist">新韩剧线路</div>
<div class="play">
  <ul>
    <li><a onclick="bf('p001')">第1集</a></li>
    <li><a onclick="bf('p002')">第2集</a></li>
  </ul>
</div>
"""

HOT_HTML = """
<div class="txt">
  <ul>
    <li><a href="/detail/h1.html" title="热播1">热播1</a><span>Top1</span></li>
    <li><a href="/detail/h2.html" title="热播2">热播2</a><span>Top2</span></li>
    <li><a href="/detail/h3.html" title="热播3">热播3</a><span>Top3</span></li>
  </ul>
</div>
"""


class FakeResponse:
    def __init__(self, text="", status_code=200, headers=None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}
        self.encoding = "utf-8"


class TestHanJu7Spider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_returns_expected_classes(self):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [item["type_id"] for item in content["class"]],
            ["1", "3", "4", "hot", "new"],
        )

    @patch.object(Spider, "_request_html")
    def test_home_video_content_parses_list_cards(self, mock_request_html):
        mock_request_html.return_value = HOME_HTML
        result = self.spider.homeVideoContent()
        self.assertEqual(
            result["list"],
            [
                {
                    "vod_id": "abc123",
                    "vod_name": "苦尽柑来遇见你",
                    "vod_pic": "https://img.example.com/a.jpg",
                    "vod_remarks": "更新至第2集",
                },
                {
                    "vod_id": "def456",
                    "vod_name": "机智住院医生生活",
                    "vod_pic": "https://www.hanju7.com/upload/b.jpg",
                    "vod_remarks": "2026-04-24",
                },
            ],
        )

    @patch.object(Spider, "_request_html")
    def test_category_content_uses_list_path_for_regular_category(self, mock_request_html):
        mock_request_html.return_value = LIST_HTML
        result = self.spider.categoryContent("3", "2", False, {})
        self.assertEqual(mock_request_html.call_args.args[0], "https://www.hanju7.com/list/3---1.html")
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["list"][0]["vod_id"], "xyz001")
        self.assertEqual(result["list"][1]["vod_pic"], "https://pics.hanju7.com/pics/xyz002.jpg")
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_html")
    def test_category_content_paginates_hot_locally(self, mock_request_html):
        mock_request_html.return_value = HOT_HTML
        result = self.spider.categoryContent("hot", "1", False, {})
        self.assertEqual(mock_request_html.call_args.args[0], "https://www.hanju7.com/hot.html")
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["list"][0]["vod_id"], "h1")

    def test_extract_redirect_location_from_native_search_response(self):
        response = FakeResponse(status_code=302, headers={"Location": "/search.php?searchword=test"})
        self.assertEqual(self.spider._extract_redirect_location(response), "/search.php?searchword=test")

    @patch.object(Spider, "_request_html")
    @patch.object(Spider, "_native_post_search")
    def test_search_content_follows_redirect_and_parses_results(self, mock_native_search, mock_request_html):
        mock_native_search.return_value = ("/search.php?page=1&searchword=%E6%96%B0%E4%B9%8C%E6%89%98%E9%82%A6", "k=v")
        mock_request_html.return_value = SEARCH_HTML
        result = self.spider.searchContent("新乌托邦", False, "1")
        self.assertEqual(result["page"], 1)
        self.assertEqual(mock_request_html.call_args.args[0], "https://www.hanju7.com/search.php?page=1&searchword=%E6%96%B0%E4%B9%8C%E6%89%98%E9%82%A6")
        self.assertEqual(mock_request_html.call_args.kwargs["headers"]["Cookie"], "k=v")
        self.assertEqual(
            result["list"],
            [
                {
                    "vod_id": "search001",
                    "vod_name": "新乌托邦",
                    "vod_pic": MODULE.DEFAULT_PIC,
                    "vod_remarks": "朴正民 / 金智秀",
                },
                {
                    "vod_id": "search002",
                    "vod_name": "协商的技术",
                    "vod_pic": MODULE.DEFAULT_PIC,
                    "vod_remarks": "李帝勋",
                },
            ],
        )

    @patch.object(Spider, "_request_html")
    def test_detail_content_parses_metadata_and_playlists(self, mock_request_html):
        mock_request_html.return_value = DETAIL_HTML
        result = self.spider.detailContent(["abc123"])
        vod = result["list"][0]
        self.assertEqual(mock_request_html.call_args.args[0], "https://www.hanju7.com/detail/abc123.html")
        self.assertEqual(vod["vod_name"], "比天堂还美丽")
        self.assertEqual(vod["vod_pic"], "https://img.example.com/poster.jpg")
        self.assertEqual(vod["vod_actor"], "金惠子 / 孙锡久")
        self.assertEqual(vod["vod_remarks"], "更新至第3集")
        self.assertEqual(vod["vod_year"], "2026")
        self.assertEqual(vod["vod_content"], "一段剧情简介")
        self.assertEqual(vod["vod_play_from"], "新韩剧线路")
        self.assertEqual(vod["vod_play_url"], "第1集$p001#第2集$p002")

    def test_decrypt_play_url_decodes_prefixed_iv_payload(self):
        encrypted = encrypt_player_payload("https://cdn.example.com/final.m3u8")
        self.assertEqual(self.spider._decrypt_play_url(encrypted), "https://cdn.example.com/final.m3u8")

    @patch.object(Spider, "_request_text")
    def test_player_content_returns_direct_media(self, mock_request_text):
        mock_request_text.return_value = encrypt_player_payload("https://cdn.example.com/final.m3u8")
        result = self.spider.playerContent("新韩剧线路", "p001", {})
        self.assertEqual(mock_request_text.call_args.args[0], "https://www.hanju7.com/u/u1.php?ud=p001")
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["jx"], 0)
        self.assertEqual(result["url"], "https://cdn.example.com/final.m3u8")
        self.assertEqual(result["header"]["Referer"], "https://www.hanju7.com/")

    @patch.object(Spider, "_request_text")
    def test_player_content_falls_back_to_parser_for_embed_url(self, mock_request_text):
        mock_request_text.return_value = encrypt_player_payload("https://player.example.com/embed?id=1")
        result = self.spider.playerContent("新韩剧线路", "p002", {})
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["jx"], 1)
        self.assertEqual(result["url"], "https://player.example.com/embed?id=1")


if __name__ == "__main__":
    unittest.main()
