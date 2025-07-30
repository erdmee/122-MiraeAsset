# Playwright Tool 래퍼 (사이트 전체 내용 수집)
from playwright.sync_api import sync_playwright


class PlaywrightTool:
    def __init__(self):
        pass

    def scrape(self, url):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            content = page.content()
            browser.close()
            return content


# 사용 예시:
# tool = PlaywrightTool()
# tool.scrape('https://finance.naver.com/')
