#!/usr/bin/env python3
from playwright.sync_api import sync_playwright


def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 360, "height": 640})
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
        page.on("pageerror", lambda err: print(f"PAGEERROR: {err}"))
        page.on("response", lambda resp: print(f"RESP: {resp.status} {resp.url}"))

        page.goto("http://127.0.0.1:8000/s/Cyc6Ad4o_issuqc4_xnxbd6t8GAS5YXhp80ST-mE9E4")
        page.wait_for_timeout(2000)

        # Check sections
        print("notFoundBox class:", page.locator("#notFoundBox").get_attribute("class"))
        print("otpChallengeBox class:", page.locator("#otpChallengeBox").get_attribute("class"))
        print("briefContentBox class:", page.locator("#briefContentBox").get_attribute("class"))
        browser.close()


if __name__ == "__main__":
    debug()
