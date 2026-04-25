import gzip
import json
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("xiuluo_spider", str(ROOT / "修罗.py")).load_module()
Spider = MODULE.Spider


def build_proxy_payload(text):
    return (b"x" * 3354) + gzip.compress(text.encode("utf-8"))


class TestXiuLuoSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_returns_classes_and_filters(self):
        result = self.spider.homeContent(False)
        self.assertEqual(
            result["class"],
            [
                {"type_id": "movie", "type_name": "电影"},
                {"type_id": "tv", "type_name": "电视剧"},
                {"type_id": "zongyi", "type_name": "综艺"},
                {"type_id": "duanju", "type_name": "短剧"},
            ],
        )
        self.assertEqual(result["filters"]["movie"][0]["key"], "genre")
        self.assertEqual(result["filters"]["movie"][0]["value"][0], {"n": "不限", "v": "all"})
        self.assertEqual(result["filters"]["movie"][-1]["key"], "order")
        self.assertEqual(result["filters"]["zongyi"][0]["key"], "area")
        self.assertEqual(result["list"], [])

    def test_category_content_builds_filter_url_and_parses_cards(self):
        html = """
        <div class="row-cards">
          <div class="card card-link">
            <a href="/movie/demo-a.htm">
              <img src="/img/a.jpg" />
            </a>
            <div class="card-title">示例电影A</div>
            <div class="text-muted">HD</div>
          </div>
          <div class="card card-link">
            <a href="/movie/demo-b.htm">
              <img src="//img.example/b.jpg" />
            </a>
            <div class="card-title">示例电影B</div>
            <div class="text-muted">更新至第3集</div>
          </div>
        </div>
        """
        response = Mock(status_code=200, text=html)
        with patch.object(self.spider, "fetch", return_value=response) as mock_fetch:
            result = self.spider.categoryContent(
                "movie",
                "2",
                False,
                {"genre": "dongzuo", "area": "中国大陆", "year": "2025", "order": "1"},
            )

        self.assertEqual(
            mock_fetch.call_args.args[0],
            "https://www.xlys02.com/s/dongzuo/2?type=0&area=%E4%B8%AD%E5%9B%BD%E5%A4%A7%E9%99%86&year=2025&order=1",
        )
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["list"][0]["vod_id"], "movie/demo-a")
        self.assertEqual(result["list"][0]["vod_pic"], "https://www.xlys02.com/img/a.jpg")
        self.assertEqual(result["list"][1]["vod_pic"], "https://img.example/b.jpg")
        self.assertEqual(result["list"][1]["vod_remarks"], "更新至第3集")

    def test_search_content_filters_target_site_and_extracts_vod_items(self):
        mock_json = {
            "data": [
                {
                    "website": "哔滴",
                    "url": "https://foo.example//vod-detail-id-88413-src-1-num-1.htm",
                    "text": "第二十条",
                    "icon": "https://img.example/poster.jpg",
                },
                {
                    "website": "其他站",
                    "url": "https://foo.example//vod-detail-id-1-src-1-num-1.htm",
                    "text": "应被过滤",
                    "icon": "https://img.example/skip.jpg",
                },
            ]
        }
        response = Mock(status_code=200)
        response.json.return_value = mock_json
        with patch.object(self.spider, "fetch", return_value=response) as mock_fetch:
            result = self.spider.searchContent("第二十条", False, "1")

        self.assertEqual(
            result["list"],
            [
                {
                    "vod_id": "/vod-detail-id-88413-src-1-num-1.htm",
                    "vod_name": "第二十条",
                    "vod_pic": "https://img.example/poster.jpg",
                    "vod_remarks": "哔滴",
                }
            ],
        )
        called_url = mock_fetch.call_args.args[0]
        self.assertIn("https://www.ymck.pro/API/v2.php?q=第二十条&size=50", called_url)

    def test_detail_content_builds_single_vod_shell_from_search_id(self):
        html = """
        <html><body>
          <h2>测试影片</h2>
          <img class="cover" src="/poster.jpg" />
          <div id="synopsis">一段剧情简介</div>
          <div id="play-list">
            <a href="/play/alpha-1.htm">正片</a>
            <a href="/play/alpha-2.htm">备用</a>
          </div>
        </body></html>
        """
        response = Mock(status_code=200, text=html)
        with patch.object(self.spider, "fetch", return_value=response) as mock_fetch:
            result = self.spider.detailContent(["movie/test-alpha"])

        self.assertEqual(mock_fetch.call_args.args[0], "https://www.xlys02.com/movie/test-alpha.htm")
        self.assertEqual(
            result["list"],
            [
                {
                    "vod_id": "movie/test-alpha",
                    "vod_name": "测试影片",
                    "vod_pic": "https://www.xlys02.com/poster.jpg",
                    "type_name": "",
                    "vod_class": "",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_lang": "",
                    "vod_remarks": "",
                    "vod_actor": "",
                    "vod_director": "",
                    "vod_douban_score": "",
                    "vod_douban_id": "",
                    "vod_content": "一段剧情简介",
                    "vod_play_from": "修罗直连",
                    "vod_play_url": "正片$play/alpha-1#备用$play/alpha-2",
                }
            ],
        )

    def test_detail_content_skips_watch_history_heading_when_extracting_title(self):
        html = """
        <html><body>
          <section class="history"><h2>观看历史</h2></section>
          <div class="detail">
            <h2>真正片名</h2>
            <img class="cover" src="/poster.jpg" />
            <div id="synopsis">详情简介</div>
            <div id="play-list"><a href="/play/right-1.htm">正片</a></div>
          </div>
        </body></html>
        """
        response = Mock(status_code=200, text=html)
        with patch.object(self.spider, "fetch", return_value=response):
            result = self.spider.detailContent(["movie/right-title"])

        self.assertEqual(result["list"][0]["vod_name"], "真正片名")

    def test_detail_content_parses_labeled_metadata_block(self):
        html = """
        <html><body>
          <div class="detail"><h2>八千里路云和月</h2></div>
          <img class="cover" src="/poster.jpg" />
          <div id="synopsis">大时代里的群像故事</div>
          <div class="col mb-2">
            <p class="mb-0 mb-md-2"><strong>别名：</strong>八千里路雲和月 / 厨子与将军</p>
            <p class="mb-0 mb-md-2 text-truncate-sm"><strong>导演：</strong><a href="/director/张永新">张永新</a></p>
            <p class="mb-0 mb-md-2 text-truncate-sm"><strong>主演：</strong><a href="/performer/王阳">王阳</a><a href="/performer/万茜">万茜</a></p>
            <p class="mb-0 mb-md-2"><strong>类型：</strong><a href="/s/juqing">剧情</a><a href="/s/lishi">历史</a><a href="/s/zhanzheng">战争</a></p>
            <p class="mb-0 mb-md-2"><strong>制片国家/地区：</strong>[中国大陆]</p>
            <p class="mb-0 mb-md-2"><strong>语言：</strong>汉语普通话</p>
            <p class="mb-0 mb-md-2"><strong>豆瓣链接：</strong><a href="https://movie.douban.com/subject/33371937/">33371937</a></p>
            <p class="d-none d-md-block mb-0"><strong>摘要：</strong><span class="text-orange">40集全.HD1080P4K.国语中字</span></p>
          </div>
          <div id="play-list"><a href="/play/8k-1.htm">第1集</a></div>
        </body></html>
        """
        response = Mock(status_code=200, text=html)
        with patch.object(self.spider, "fetch", return_value=response):
            result = self.spider.detailContent(["movie/8klyhy"])

        vod = result["list"][0]
        self.assertEqual(vod["vod_name"], "八千里路云和月")
        self.assertEqual(vod["type_name"], "剧情 / 历史 / 战争")
        self.assertEqual(vod["vod_class"], "剧情 / 历史 / 战争")
        self.assertEqual(vod["vod_area"], "中国大陆")
        self.assertEqual(vod["vod_lang"], "汉语普通话")
        self.assertEqual(vod["vod_director"], "张永新")
        self.assertEqual(vod["vod_actor"], "王阳 / 万茜")
        self.assertEqual(vod["vod_douban_id"], "33371937")
        self.assertEqual(vod["vod_remarks"], "40集全.HD1080P4K.国语中字")

    @patch.object(Spider, "_current_millis", return_value=1713952212345, create=True)
    def test_player_content_requests_lines_and_returns_first_allowed_direct_url(self, _mock_time):
        play_html = '<script>var pid = 9527;</script>'
        play_response = Mock(status_code=200, text=play_html)
        lines_response = Mock(status_code=200)
        lines_response.json.return_value = {
            "code": 0,
            "data": {
                "url3": (
                    "https://media.example.com/direct.mp4,"
                    "https://vip.ffzy/video/index.m3u8,"
                    "https://p3-tt.byteimg.com/byte.mp4"
                )
            }
        }
        with patch.object(self.spider, "fetch", side_effect=[play_response, lines_response]) as mock_fetch:
            result = self.spider.playerContent("修罗直连", "play/alpha-1", {})

        self.assertEqual(
            mock_fetch.call_args_list[1].args[0],
            "https://www.xlys02.com/lines?t=1713952212345&sg=4322A578A3DB6BD0D1936C4F381C9925E2388F66F2DDE5D783B65E2379BE5B56&pid=9527",
        )
        self.assertEqual(mock_fetch.call_args_list[1].kwargs["headers"]["X-Requested-With"], "XMLHttpRequest")
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "https://media.example.com/direct.mp4")
        self.assertEqual(result["header"]["Referer"], "https://www.xlys02.com")

    @patch.object(Spider, "_current_millis", return_value=1713952212345, create=True)
    def test_player_content_uses_tos_fallback_when_no_allowed_url3(self, _mock_time):
        play_html = '<script>var pid = 9527;</script>'
        play_response = Mock(status_code=200, text=play_html)
        lines_response = Mock(status_code=200)
        lines_response.json.return_value = {
            "code": 0,
            "data": {
                "url3": "https://vip.ffzy/video/index.m3u8,https://p3-tt.byteimg.com/byte.mp4",
                "tos": True,
            }
        }
        tos_response = Mock(status_code=200)
        tos_response.json.return_value = {"url": "https://media.example.com/from-tos.mp4"}
        with patch.object(self.spider, "fetch", side_effect=[play_response, lines_response]):
            with patch.object(self.spider, "post", return_value=tos_response) as mock_post:
                result = self.spider.playerContent("修罗直连", "play/alpha-1", {})

        self.assertEqual(mock_post.call_args.args[0], "https://www.xlys02.com/god/9527?type=1")
        self.assertEqual(
            mock_post.call_args.kwargs["data"],
            "t=1713952212345&sg=4322A578A3DB6BD0D1936C4F381C9925E2388F66F2DDE5D783B65E2379BE5B56&verifyCode=888",
        )
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "https://media.example.com/from-tos.mp4")

    def test_player_content_returns_proxy_url_for_real_m3u8(self):
        result = self.spider.playerContent("修罗", "https://cdn.example.com/demo/index.m3u8", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "http://127.0.0.1:9978/proxy?do=py&type=m3u8&url=https%3A%2F%2Fcdn.example.com%2Fdemo%2Findex.m3u8")
        self.assertIn("Mozilla/5.0", result["header"]["User-Agent"])

    def test_player_content_returns_direct_url_for_mp4(self):
        probe = Mock()
        probe.status_code = 206
        probe.headers = {"Content-Type": "video/mp4"}
        with patch.object(self.spider, "_range_probe", return_value=probe):
            result = self.spider.playerContent("修罗", "https://cdn.example.com/demo/video.mp4", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "https://cdn.example.com/demo/video.mp4")

    def test_local_proxy_decodes_rewrites_and_returns_m3u8(self):
        body = build_proxy_payload(
            "#EXTM3U\n"
            "#EXTINF:10,\n"
            "seg-1.ts\n"
            "#EXTINF:10,\n"
            "/seg-2.ts\n"
            "#EXT-X-DISCONTINUITY\n"
            "https://up.example.com/seg-3.ts\n"
            "#EXT-X-ENDLIST\n"
        )
        response = Mock(status_code=200, content=body)
        response.headers = {}
        with patch.object(self.spider, "fetch", return_value=response):
            status, content_type, data = self.spider.localProxy(
                {
                    "type": "m3u8",
                    "url": "https://cdn.example.com/path/master.m3u8",
                }
            )

        text = data.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/vnd.apple.mpegurl")
        self.assertIn("http://127.0.0.1:9978/proxy?do=py&type=m3u8&url=https%3A%2F%2Fcdn.example.com%2Fpath%2Fseg-1.ts", text)
        self.assertIn("http://127.0.0.1:9978/proxy?do=py&type=m3u8&url=https%3A%2F%2Fcdn.example.com%2Fseg-2.ts", text)
        self.assertIn("http://127.0.0.1:9978/proxy?do=py&type=m3u8&url=https%3A%2F%2Fup.example.com%2Fseg-3.ts", text)

    def test_local_proxy_rejects_unsupported_type(self):
        self.assertIsNone(self.spider.localProxy({"type": "other", "url": "https://cdn.example.com/a"}))

    def test_aes_ecb_hex_matches_reference_cipher(self):
        self.assertEqual(
            self.spider._aes_ecb_hex("1234567890abcdef", "hello"),
            "3ae1bf1edbd01914c379e7a9e993bf59",
        )


if __name__ == "__main__":
    unittest.main()
