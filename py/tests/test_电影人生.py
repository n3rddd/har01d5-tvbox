import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("dyrs_spider", str(ROOT / "电影人生.py")).load_module()
Spider = MODULE.Spider

SAMPLE_LIST_HTML = """
<a data-url="/dyrscom-foo.html" href="/dyrscom-foo.html" title="片名A">
  <img data-src="/cover/a.jpg" />
  <div class="text-[10px]">更新至10集</div>
</a>
<div class="items-center flex mt-1"><span>2025</span><span>剧情</span></div>
<a data-url="/dyrscom-bar.html" href="/dyrscom-bar.html" title="片名B">
  <img src="https://img.example/b.jpg" />
</a>
"""

DETAIL_HTML = """
<meta property="og:image" content="/poster.jpg" />
<meta name="description" content="简介描述" />
<h1>电影人生示例</h1>
<div><span>年份</span><span>2025</span></div>
<div><span>地区</span><span>大陆</span></div>
<div><span>语言</span><span>国语</span></div>
<h3>导演</h3><div><a><span>张三</span></a></div>
<h3>主演</h3><div><a><span>李四</span></a><a><span>王五</span></a></div>
<h3>标签</h3><div><a><span>#剧情</span></a><a><span>#悬疑</span></a></div>
<h3>剧情简介</h3><div><div class="text-sm">这是一段剧情。</div></div>
<div id="originTabs">
  <a href="/dyrscom-foo.html?origin=line1"><button data-origin="线路一">线路一</button></a>
  <a href="/dyrscom-foo.html?origin=line2"><button data-origin="线路二">线路二</button></a>
</div>
"""

LINE1_HTML = """
<div class="seqlist">
  <a href="/dyrscom-foo.html?origin=line1&play=1" data-title="第1集" data-origin="线路一">第1集</a>
  <a href="/dyrscom-foo.html?origin=line1&play=2" data-title="第2集" data-origin="线路一">第2集</a>
</div>
"""

LINE2_HTML = """
<div class="seqlist">
  <a href="/dyrscom-foo.html?origin=line2&play=1" data-title="正片" data-origin="线路二">正片</a>
</div>
"""

SEARCH_HTML = """
<a data-url="/dyrscom-c.html" href="/dyrscom-c.html" title="繁花2023"></a>
<a data-url="/dyrscom-a.html" href="/dyrscom-a.html" title="繁花"></a>
<a data-url="/dyrscom-b.html" href="/dyrscom-b.html" title="阿凡达"></a>
"""


class TestDYRSSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_classes_and_filters(self):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [item["type_id"] for item in content["class"]],
            ["dianying", "dianshiju", "dongman", "zongyi"],
        )
        self.assertEqual(
            [item["key"] for item in content["filters"]["dianying"]],
            ["class", "sort_field"],
        )

    def test_parse_cards_extracts_short_id_title_pic_and_remarks(self):
        cards = self.spider._parse_vod_cards(SAMPLE_LIST_HTML)
        self.assertEqual(cards[0]["vod_id"], "dyrscom-foo.html")
        self.assertEqual(cards[0]["vod_name"], "片名A")
        self.assertEqual(cards[0]["vod_pic"], "https://dyrsok.com/cover/a.jpg")
        self.assertEqual(cards[0]["vod_year"], "2025")
        self.assertEqual(cards[0]["type_name"], "剧情")
        self.assertEqual(cards[0]["vod_remarks"], "更新至10集")

    @patch.object(Spider, "_request_html")
    def test_category_content_builds_query_string(self, mock_html):
        mock_html.return_value = SAMPLE_LIST_HTML
        result = self.spider.categoryContent(
            "dianying",
            "2",
            False,
            {"class": "动作", "sort_field": "update_time"},
        )
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["list"][0]["vod_id"], "dyrscom-foo.html")
        mock_html.assert_called_with(
            "https://dyrsok.com/dianying.html?class=%E5%8A%A8%E4%BD%9C&sort_field=update_time&page=2"
        )

    @patch.object(Spider, "_request_html")
    def test_home_video_content_reads_home_page(self, mock_html):
        mock_html.return_value = SAMPLE_LIST_HTML
        result = self.spider.homeVideoContent()
        self.assertEqual(len(result["list"]), 2)
        mock_html.assert_called_with("https://dyrsok.com/")

    @patch.object(Spider, "_request_html")
    def test_detail_content_extracts_meta_and_lines(self, mock_html):
        mock_html.side_effect = [DETAIL_HTML, LINE1_HTML, LINE2_HTML]
        result = self.spider.detailContent(["dyrscom-foo.html"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "dyrscom-foo.html")
        self.assertEqual(vod["vod_name"], "电影人生示例")
        self.assertEqual(vod["vod_pic"], "https://dyrsok.com/poster.jpg")
        self.assertEqual(vod["vod_year"], "2025")
        self.assertEqual(vod["vod_area"], "大陆")
        self.assertEqual(vod["vod_lang"], "国语")
        self.assertEqual(vod["vod_director"], "张三")
        self.assertEqual(vod["vod_actor"], "李四,王五")
        self.assertEqual(vod["type_name"], "剧情 / 悬疑")
        self.assertEqual(vod["vod_play_from"], "线路一$$$线路二")
        self.assertIn("第1集$", vod["vod_play_url"])
        self.assertIn("正片$", vod["vod_play_url"])

    @patch.object(Spider, "_request_html")
    def test_search_content_refines_exact_match_first(self, mock_html):
        mock_html.return_value = SEARCH_HTML
        result = self.spider.searchContent("繁花", False, "1")
        self.assertEqual([item["vod_name"] for item in result["list"][:2]], ["繁花", "繁花2023"])
        mock_html.assert_called_with("https://dyrsok.com/s.html?name=%E7%B9%81%E8%8A%B1")

    @patch.object(Spider, "_request_html")
    @patch.object(Spider, "_request_response")
    def test_player_content_resolves_api_m3u8_and_raw_playlist(self, mock_response, mock_html):
        mock_html.side_effect = [
            '<script>fetch("/api/m3u8?origin=line1&url=abc123")</script>',
            "#EXTM3U\n/api/m3u8?id=xyz&raw=1\n",
        ]

        class FakeResponse:
            status_code = 302
            headers = {"Location": "https://media.example/master.m3u8"}
            text = ""

        mock_response.return_value = FakeResponse()
        play_id = (
            '{"title":"第1集","origin":"线路一","page":"https://dyrsok.com/dyrscom-foo.html?play=1",'
            '"vodName":"电影人生示例","pic":"https://dyrsok.com/poster.jpg"}'
        )
        result = self.spider.playerContent("线路一", play_id, {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "https://media.example/api/m3u8?id=xyz&raw=1")

    @patch.object(Spider, "_request_html")
    def test_player_content_falls_back_to_parse_when_no_api_link(self, mock_html):
        mock_html.return_value = "<html><body>empty</body></html>"
        result = self.spider.playerContent("线路一", '{"page":"https://dyrsok.com/dyrscom-foo.html?play=1"}', {})
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["url"], "https://dyrsok.com/dyrscom-foo.html?play=1")


if __name__ == "__main__":
    unittest.main()
