# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tools/crawler_util.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 12:53
# @Desc    : Crawler utility functions

import asyncio
import base64
import json
import logging
import random
import re
import urllib
import urllib.parse
from io import BytesIO
from typing import Dict, List, Optional, Tuple, cast

import httpx
from PIL import Image, ImageDraw, ImageShow
from playwright.async_api import BrowserContext, Cookie, Page

import config
from .httpx_util import make_async_client


logger = logging.getLogger("MediaCrawler")
_crawl_sleep_counter = 0


def _non_negative_float(value, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    if number < 0:
        return 0.0
    return number


def _non_negative_int(value, fallback: int = 0) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = fallback
    if number < 0:
        return 0
    return number


def _sleep_bounds() -> Tuple[float, float]:
    min_sleep = _non_negative_float(
        getattr(config, "CRAWLER_MIN_SLEEP_SEC", getattr(config, "CRAWLER_MAX_SLEEP_SEC", 0.0))
    )
    max_sleep = _non_negative_float(getattr(config, "CRAWLER_MAX_SLEEP_SEC", min_sleep), min_sleep)
    if max_sleep < min_sleep:
        min_sleep, max_sleep = max_sleep, min_sleep
    return min_sleep, max_sleep


def _long_pause_bounds() -> Tuple[float, float]:
    min_pause = _non_negative_float(getattr(config, "CRAWLER_LONG_PAUSE_MIN_SEC", 0.0))
    max_pause = _non_negative_float(getattr(config, "CRAWLER_LONG_PAUSE_MAX_SEC", min_pause), min_pause)
    if max_pause < min_pause:
        min_pause, max_pause = max_pause, min_pause
    return min_pause, max_pause


def next_crawl_sleep_seconds() -> Tuple[float, bool, int]:
    """Return the next randomized crawl sleep delay, whether it includes a long pause, and the counter."""

    global _crawl_sleep_counter

    min_sleep, max_sleep = _sleep_bounds()
    base_delay = random.uniform(min_sleep, max_sleep) if max_sleep > min_sleep else max_sleep

    _crawl_sleep_counter += 1
    sleep_count = _crawl_sleep_counter

    long_pause_every = _non_negative_int(getattr(config, "CRAWLER_LONG_PAUSE_EVERY", 0))
    has_long_pause = long_pause_every > 0 and sleep_count % long_pause_every == 0
    if has_long_pause:
        min_pause, max_pause = _long_pause_bounds()
        long_delay = random.uniform(min_pause, max_pause) if max_pause > min_pause else max_pause
        base_delay += long_delay

    return max(0.0, base_delay), has_long_pause, sleep_count


async def random_crawl_sleep(reason: str = "") -> float:
    """Sleep using the configured randomized crawler interval."""

    delay, has_long_pause, sleep_count = next_crawl_sleep_seconds()
    if delay <= 0:
        return 0.0

    pause_kind = "long pause" if has_long_pause else "sleep"
    suffix = f" after {reason}" if reason else ""
    logger.info(
        f"[CrawlerSleep] {pause_kind} {delay:.2f}s{suffix} (step {sleep_count})"
    )
    await asyncio.sleep(delay)
    return delay


async def find_login_qrcode(page: Page, selector: str) -> str:
    """find login qrcode image from target selector"""
    try:
        elements = await page.wait_for_selector(
            selector=selector,
        )
        login_qrcode_img = str(await elements.get_property("src"))  # type: ignore
        if "http://" in login_qrcode_img or "https://" in login_qrcode_img:
            async with make_async_client(follow_redirects=True) as client:
                logger.info(f"[find_login_qrcode] get qrcode by url:{login_qrcode_img}")
                resp = await client.get(login_qrcode_img, headers={"User-Agent": get_user_agent()})
                if resp.status_code == 200:
                    image_data = resp.content
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    return base64_image
                raise Exception(f"fetch login image url failed, response message:{resp.text}")
        return login_qrcode_img

    except Exception as e:
        print(e)
        return ""


async def find_qrcode_img_from_canvas(page: Page, canvas_selector: str) -> str:
    """
    find qrcode image from canvas element
    Args:
        page:
        canvas_selector:

    Returns:

    """

    # Wait for Canvas element to load
    canvas = await page.wait_for_selector(canvas_selector)

    # Take screenshot of Canvas element
    screenshot = await canvas.screenshot()

    # Convert screenshot to base64 format
    base64_image = base64.b64encode(screenshot).decode('utf-8')
    return base64_image


def show_qrcode(qr_code) -> None:  # type: ignore
    """parse base64 encode qrcode image and show it"""
    if "," in qr_code:
        qr_code = qr_code.split(",")[1]
    qr_code = base64.b64decode(qr_code)
    image = Image.open(BytesIO(qr_code))

    # Add a square border around the QR code and display it within the border to improve scanning accuracy.
    width, height = image.size
    new_image = Image.new('RGB', (width + 20, height + 20), color=(255, 255, 255))
    new_image.paste(image, (10, 10))
    draw = ImageDraw.Draw(new_image)
    draw.rectangle((0, 0, width + 19, height + 19), outline=(0, 0, 0), width=1)
    del ImageShow.UnixViewer.options["save_all"]
    new_image.show()


def get_user_agent() -> str:
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.5112.79 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.5060.53 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.4844.84 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5112.79 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5060.53 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.4844.84 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5112.79 Safari/537.36"
    ]
    return random.choice(ua_list)


def get_mobile_user_agent() -> str:
    ua_list = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
    ]
    return random.choice(ua_list)


def convert_cookies(cookies: Optional[List[Cookie]]) -> Tuple[str, Dict]:
    if not cookies:
        return "", {}
    cookies_str = ";".join([f"{cookie.get('name')}={cookie.get('value')}" for cookie in cookies])
    cookie_dict = dict()
    for cookie in cookies:
        cookie_dict[cookie.get('name')] = cookie.get('value')
    return cookies_str, cookie_dict


async def convert_browser_context_cookies(
    browser_context: BrowserContext, urls: Optional[List[str]] = None
) -> Tuple[str, Dict]:
    cookies = (
        await browser_context.cookies(urls=urls)
        if urls
        else await browser_context.cookies()
    )
    return convert_cookies(cookies)


def normalize_cookie_input(cookie_str: str) -> str:
    cookie_dict = parse_cookie_input(cookie_str)
    return "; ".join(f"{name}={value}" for name, value in cookie_dict.items())


def parse_cookie_input(cookie_str: str) -> Dict[str, str]:
    cookie_dict: Dict[str, str] = dict()
    text = (cookie_str or "").strip()
    if not text:
        return cookie_dict

    json_cookie_dict = _parse_cookie_json(text)
    if json_cookie_dict:
        return json_cookie_dict

    table_cookie_dict = _parse_cookie_table(text)
    if table_cookie_dict:
        return table_cookie_dict

    cookie_header = _extract_cookie_header(text)
    for cookie in cookie_header.split(";"):
        cookie = cookie.strip()
        if not cookie or "=" not in cookie:
            continue
        cookie_name, cookie_value = cookie.split("=", 1)
        cookie_name = cookie_name.strip()
        cookie_value = cookie_value.strip()
        if cookie_name:
            cookie_dict[cookie_name] = cookie_value
    return cookie_dict


def _parse_cookie_json(text: str) -> Dict[str, str]:
    try:
        data = json.loads(text)
    except Exception:
        return {}

    cookie_dict: Dict[str, str] = {}
    if isinstance(data, dict):
        if isinstance(data.get("cookies"), list):
            data = data["cookies"]
        else:
            for name, value in data.items():
                if isinstance(value, (str, int, float, bool)):
                    cookie_dict[str(name)] = str(value)
            return cookie_dict

    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            value = item.get("value")
            if name is not None and value is not None:
                cookie_dict[str(name)] = str(value)
    return cookie_dict


def _parse_cookie_table(text: str) -> Dict[str, str]:
    cookie_dict: Dict[str, str] = {}
    for raw_line in text.splitlines():
        columns = [part.strip() for part in raw_line.strip().split("\t")]
        if len(columns) < 2:
            continue
        name, value = columns[0], columns[1]
        if name.lower() == "name" and value.lower() == "value":
            continue
        if name and value:
            cookie_dict[name] = value
    return cookie_dict


def _extract_cookie_header(text: str) -> str:
    for line in text.splitlines():
        match = re.search(r"(?i)\bcookie\s*:\s*(.+)$", line.strip())
        if match:
            return match.group(1).strip().strip("'\"")
    return text.strip().strip("'\"")


def convert_str_cookie_to_dict(cookie_str: str) -> Dict:
    return parse_cookie_input(cookie_str)


def match_interact_info_count(count_str: str) -> int:
    if not count_str:
        return 0

    match = re.search(r'\d+', count_str)
    if match:
        number = match.group()
        return int(number)
    else:
        return 0


def format_proxy_info(ip_proxy_info) -> Tuple[Optional[Dict], Optional[str]]:
    """format proxy info for playwright and httpx"""
    # fix circular import issue
    from proxy.proxy_ip_pool import IpInfoModel
    ip_proxy_info = cast(IpInfoModel, ip_proxy_info)

    # Playwright proxy server should be in format "host:port" without protocol prefix
    server = f"{ip_proxy_info.ip}:{ip_proxy_info.port}"
    
    playwright_proxy = {
        "server": server,
    }
    
    # Only add username and password if they are not empty
    if ip_proxy_info.user and ip_proxy_info.password:
        playwright_proxy["username"] = ip_proxy_info.user
        playwright_proxy["password"] = ip_proxy_info.password
    
    # httpx 0.28.1 requires passing proxy URL string directly, not a dictionary
    if ip_proxy_info.user and ip_proxy_info.password:
        httpx_proxy = f"http://{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"
    else:
        httpx_proxy = f"http://{ip_proxy_info.ip}:{ip_proxy_info.port}"
    return playwright_proxy, httpx_proxy


def extract_text_from_html(html: str) -> str:
    """Extract text from HTML, removing all tags."""
    if not html:
        return ""

    # Remove script and style elements
    clean_html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL)
    # Remove all other tags
    clean_text = re.sub(r'<[^>]+>', '', clean_html).strip()
    return clean_text

def extract_url_params_to_dict(url: str) -> Dict:
    """Extract URL parameters to dict"""
    url_params_dict = dict()
    if not url:
        return url_params_dict
    parsed_url = urllib.parse.urlparse(url)
    url_params_dict = dict(urllib.parse.parse_qsl(parsed_url.query))
    return url_params_dict
