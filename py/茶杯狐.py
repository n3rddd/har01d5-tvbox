# coding=utf-8
import base64
import random
import re
import sys
from urllib.parse import urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "茶杯狐"
        self.host = "https://www.cupfox.ai"
        self.page_limit = 20
        self.firewall_chars = "PXhw7UT1B0a9kQDKZsjIASmOezxYG4CHo5Jyfg2b8FLpEvRr3WtVnlqMidu6cN"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3_2 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3.1 "
                "Mobile/15E148 Safari/604.1"
            ),
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def _build_url(self, path):
        return urljoin(self.host + "/", str(path or "").strip())

    def _encode_detail_id(self, href):
        matched = re.search(r"/movie/([^/?#]+)\.html", self._build_url(href))
        return f"detail/{matched.group(1)}" if matched else ""

    def _decode_detail_id(self, vod_id):
        matched = re.search(r"^detail/([^/?#]+)$", str(vod_id or "").strip())
        return self._build_url(f"/movie/{matched.group(1)}.html") if matched else ""

    def _encode_play_id(self, href):
        matched = re.search(r"/play/([^/?#]+)\.html", self._build_url(href))
        return f"play/{matched.group(1)}" if matched else ""

    def _decode_play_id(self, play_id):
        matched = re.search(r"^play/([^/?#]+)$", str(play_id or "").strip())
        return self._build_url(f"/play/{matched.group(1)}.html") if matched else ""

    def _merge_set_cookie(self, cookie_jar, headers):
        values = headers if isinstance(headers, list) else [headers]
        for item in values:
            first = str(item or "").split(";")[0]
            if "=" not in first:
                continue
            name, value = first.split("=", 1)
            if name.strip():
                cookie_jar[name.strip()] = value.strip()

    def _cookie_header(self, cookie_jar):
        return "; ".join([f"{key}={value}" for key, value in cookie_jar.items()])

    def _extract_firewall_token(self, html_text):
        matched = re.search(r'var\s+token\s*=\s*encrypt\("([^"]+)"\)', str(html_text or ""))
        return matched.group(1) if matched else ""

    def _cupfox_firewall_encrypt(self, value):
        encoded = ""
        for char in str(value or ""):
            index = self.firewall_chars.find(char)
            mapped = char if index == -1 else self.firewall_chars[(index + 3) % 62]
            encoded += (
                self.firewall_chars[random.randint(0, 61)]
                + mapped
                + self.firewall_chars[random.randint(0, 61)]
            )
        return base64.b64encode(encoded.encode("utf-8")).decode("utf-8")
