import json
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Crypto.Cipher import AES


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("tingyoufm_spider", str(ROOT / "听友FM.py")).load_module()
Spider = MODULE.Spider


HOME_HTML = """
<html>
  <body>
    <a href="/categories/46">有声小说</a>
    <a href="/categories/11">武侠小说</a>
    <a href="/albums/1001">
      <img class="cover" src="/cover1.jpg" alt="鬼吹灯">
      <p>鬼吹灯 作者：天下霸唱 播音：周建龙 12期 已完结</p>
    </a>
  </body>
</html>
"""


CATEGORY_HTML_WITH_NUXT = """
<html>
  <body>
    <script id="__NUXT_DATA__" type="application/json">[null,{"data":{"categoryAlbums-46":{"page":2,"pages":9,"data":[{"id":2001,"title":"盗墓笔记","cover_url":"https://img.test/2001.jpg","count":20,"status":1,"teller":"艾宝良"}]}}}]</script>
  </body>
</html>
"""


SEARCH_HTML_WITHOUT_NUXT = """
<html>
  <body>
    <a href="/albums/3001">
      <img class="cover" src="https://img.test/3001.jpg" alt="鬼吹灯之精绝古城">
      <p>鬼吹灯之精绝古城 播音：主播甲</p>
    </a>
  </body>
</html>
"""


DETAIL_HTML = """
<html>
  <head>
    <meta property="og:title" content="鬼吹灯">
    <meta property="og:image" content="https://img.test/detail.jpg">
    <meta name="description" content="摸金校尉探险故事">
  </head>
  <body>
    <section class="album-pannel">
      <div class="album-intro">
        <h1>鬼吹灯</h1>
      </div>
      <div class="pods">
        <span>分类: 有声小说</span>
      </div>
      <img src="https://img.test/detail.jpg">
    </section>
    <ul class="chapter-list">
      <li class="chapter-item">
        <p>1</p>
        <div class="item-content"><span class="title">第1集</span></div>
      </li>
      <li class="chapter-item">
        <p>2</p>
        <div class="item-content"><span class="title">第2集</span></div>
      </li>
    </ul>
  </body>
</html>
"""


class TestTingYouFMSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def _build_v1_payload(self, plain_text):
        key = bytes.fromhex(self.spider.payload_key_hex)
        iv = bytes(range(12))
        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        encrypted, tag = cipher.encrypt_and_digest(plain_text.encode("utf-8"))
        raw = bytes([1]) + iv + encrypted + tag
        return raw.hex()

    @staticmethod
    def _build_v2_payload(reversed_cipher=b"cba"):
        nonce = bytes(range(1, 25))
        raw = bytes([2]) + nonce + reversed_cipher
        return raw.hex()

    @patch.object(Spider, "fetch")
    def test_home_content_extracts_categories_and_album_cards(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(status_code=200, text=HOME_HTML)
        result = self.spider.homeContent(False)
        self.assertEqual(result["class"][:2], [{"type_id": "46", "type_name": "有声小说"}, {"type_id": "11", "type_name": "武侠小说"}])
        self.assertEqual(result["list"][0]["vod_id"], "1001")
        self.assertEqual(result["list"][0]["vod_name"], "鬼吹灯")
        self.assertEqual(result["list"][0]["vod_pic"], "https://tingyou.fm/cover1.jpg")
        self.assertIn("12期", result["list"][0]["vod_remarks"])

    @patch.object(Spider, "fetch")
    def test_category_content_prefers_nuxt_data(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(status_code=200, text=CATEGORY_HTML_WITH_NUXT)
        result = self.spider.categoryContent("46", "2", False, {})
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["list"][0]["vod_id"], "2001")
        self.assertEqual(result["list"][0]["vod_name"], "盗墓笔记")
        self.assertEqual(result["list"][0]["vod_pic"], "https://img.test/2001.jpg")
        self.assertEqual(result["list"][0]["type_id"], "46")
        self.assertEqual(result["limit"], 1)
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "fetch")
    def test_search_content_falls_back_to_dom_and_filters_blank_keyword(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(status_code=200, text=SEARCH_HTML_WITHOUT_NUXT)
        result = self.spider.searchContent("鬼吹灯", False, "1")
        self.assertEqual(result["list"][0]["vod_id"], "3001")
        self.assertIn("鬼吹灯", result["list"][0]["vod_name"])
        self.assertEqual(
            self.spider.searchContent("", False, "1"),
            {"page": 1, "limit": 0, "total": 0, "list": []},
        )

    @patch.object(Spider, "fetch")
    def test_detail_content_extracts_album_and_playlist(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(status_code=200, text=DETAIL_HTML)
        result = self.spider.detailContent(["1001"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "1001")
        self.assertEqual(vod["vod_name"], "鬼吹灯")
        self.assertEqual(vod["type_name"], "有声小说")
        self.assertEqual(vod["vod_play_from"], "听友FM")
        self.assertEqual(vod["vod_play_url"], "第1集$1001|1#第2集$1001|2")

    def test_encrypt_payload_prefixes_version_and_decrypts_v1_payload(self):
        payload = self.spider._encrypt_payload('{"album_id":1001,"chapter_idx":1}')
        self.assertTrue(payload.startswith("01"))
        plain = self.spider._decrypt_payload(self._build_v1_payload('{"url":"https://audio.test/1.m4a"}'))
        self.assertEqual(plain, '{"url":"https://audio.test/1.m4a"}')

    def test_decrypt_v2_payload_reverses_cipher_before_decoder(self):
        calls = {}

        def fake_decrypt(key, nonce, cipher):
            calls["key"] = key
            calls["nonce"] = nonce
            calls["cipher"] = cipher
            return b'{"url":"https://audio.test/2.m4a"}'

        self.spider._xchacha_decrypt = fake_decrypt
        plain = self.spider._decrypt_payload(self._build_v2_payload())
        self.assertEqual(plain, '{"url":"https://audio.test/2.m4a"}')
        self.assertEqual(calls["nonce"], bytes(range(1, 25)))
        self.assertEqual(calls["cipher"], b"abc")

    @patch.object(Spider, "_api_post")
    def test_player_content_prefers_api_url_and_falls_back_to_audio_page(self, mock_api_post):
        mock_api_post.return_value = {"payload": self._build_v1_payload('{"url":"https://audio.test/play.m4a"}')}
        api_result = self.spider.playerContent("听友FM", "1001|1", {})
        self.assertEqual(api_result["parse"], 0)
        self.assertEqual(api_result["url"], "https://audio.test/play.m4a")

        mock_api_post.side_effect = RuntimeError("boom")
        fallback_result = self.spider.playerContent("听友FM", "1001|1", {})
        self.assertEqual(fallback_result["parse"], 1)
        self.assertEqual(fallback_result["url"], "https://tingyou.fm/audios/1001/1")


if __name__ == "__main__":
    unittest.main()
