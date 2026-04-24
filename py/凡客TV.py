# coding=utf-8
import json
import sys

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "凡客TV"
        self.host = "https://fktv.me"
        self.cookie = "_did=57nTmEknMZ146xw4KXGHDCHk1MjshRyY"
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
        )
        self.classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "剧集"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "8", "type_name": "短剧"},
            {"type_id": "6", "type_name": "纪录片"},
            {"type_id": "7", "type_name": "解说"},
            {"type_id": "5", "type_name": "音乐"},
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes}

    def _encode_play_id(self, payload):
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _decode_play_id(self, value):
        try:
            decoded = json.loads(str(value or "").strip())
        except Exception:
            decoded = {}
        return decoded if isinstance(decoded, dict) else {}
