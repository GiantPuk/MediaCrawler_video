# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/bilibili/login.py
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
# @Time    : 2023/12/2 18:44
# @Desc    : bilibili login implementation class

import asyncio
import base64
import functools
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import (RetryError, retry, retry_if_result, stop_after_attempt,
                      wait_fixed)

import config
from base.base_crawler import AbstractLogin
from tools import utils


class BilibiliLogin(AbstractLogin):
    def __init__(self,
                 login_type: str,
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",
                 cookie_str: str = ""
                 ):
        config.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

    async def begin(self):
        """Start login bilibili"""
        utils.logger.info("[BilibiliLogin.begin] Begin login Bilibili ...")
        if config.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "phone":
            await self.login_by_mobile()
        elif config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError(
                "[BilibiliLogin.begin] Invalid Login Type Currently only supported qrcode or phone or cookie ...")

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self) -> bool:
        """
            Check if the current login status is successful and return True otherwise return False
            retry decorator will retry 20 times if the return value is False, and the retry interval is 1 second
            if max retry times reached, raise RetryError
        """
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        if cookie_dict.get("SESSDATA", "") or cookie_dict.get("DedeUserID"):
            return True
        return False

    async def login_by_qrcode(self):
        """login bilibili website and keep webdriver login state"""
        utils.logger.info("[BilibiliLogin.login_by_qrcode] Begin login bilibili by qrcode ...")
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        if cookie_dict.get("SESSDATA", "") or cookie_dict.get("DedeUserID"):
            utils.logger.info("[BilibiliLogin.login_by_qrcode] Browser context already has Bilibili login cookies")
            return

        clicked = await self._click_login_entry()
        if not clicked:
            utils.logger.warning(
                "[BilibiliLogin.login_by_qrcode] Login entry was not found on homepage; opening passport login page"
            )
            await self.context_page.goto("https://passport.bilibili.com/login")
        await asyncio.sleep(1)
        base64_qrcode_img = await self._find_qrcode_image()
        if not base64_qrcode_img:
            utils.logger.info("[BilibiliLogin.login_by_qrcode] login failed , have not found qrcode please check ....")
            sys.exit()

        # show login qrcode
        partial_show_qrcode = functools.partial(utils.show_qrcode, base64_qrcode_img)
        asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)

        utils.logger.info(f"[BilibiliLogin.login_by_qrcode] Waiting for scan code login, remaining time is 20s")
        try:
            await self.check_login_state()
        except RetryError:
            utils.logger.info("[BilibiliLogin.login_by_qrcode] Login bilibili failed by qrcode login method ...")
            sys.exit()

        wait_redirect_seconds = 5
        utils.logger.info(
            f"[BilibiliLogin.login_by_qrcode] Login successful then wait for {wait_redirect_seconds} seconds redirect ...")
        await asyncio.sleep(wait_redirect_seconds)

    async def _click_login_entry(self) -> bool:
        selectors = [
            "css=.right-entry__outside.go-login-btn",
            "css=.right-entry__outside.go-login-btn div",
            "css=.header-login-entry",
            "css=.login-entry",
            "xpath=//*[contains(@class,'go-login-btn')]",
            "xpath=//*[contains(@class,'header-login-entry')]",
            "xpath=//*[normalize-space()='登录' or normalize-space()='立即登录']",
        ]
        for selector in selectors:
            try:
                locator = self.context_page.locator(selector).first
                await locator.wait_for(state="visible", timeout=5000)
                await locator.click(timeout=5000)
                utils.logger.info(f"[BilibiliLogin.login_by_qrcode] Clicked login entry with selector: {selector}")
                return True
            except Exception:
                continue
        return False

    async def _find_qrcode_image(self) -> str:
        selectors = [
            "xpath=//div[contains(@class,'login-scan-box')]//img",
            "css=.login-scan-box img",
            "css=.bili-mini-login-right-wp img",
            "css=.login-scan-box canvas",
            "css=canvas",
        ]
        for selector in selectors:
            try:
                element = await self.context_page.wait_for_selector(selector, timeout=5000)
                if not element:
                    continue
                if selector.endswith("canvas") or selector == "css=canvas":
                    screenshot = await element.screenshot()
                    return base64.b64encode(screenshot).decode("utf-8")
                qrcode = await utils.find_login_qrcode(self.context_page, selector=selector)
                if qrcode:
                    utils.logger.info(f"[BilibiliLogin.login_by_qrcode] Found qrcode with selector: {selector}")
                    return qrcode
            except Exception:
                continue
        return ""

    async def login_by_mobile(self):
        pass

    async def login_by_cookies(self):
        utils.logger.info("[BilibiliLogin.login_by_qrcode] Begin login bilibili by cookie ...")
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".bilibili.com",
                'path': "/"
            }])
