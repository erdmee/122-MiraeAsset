#!/usr/bin/env python3
"""
디버깅용 Playwright 뉴스 크롤러
"""

import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright


class DebugPlaywrightCrawler:
    def __init__(self):
        self.cache_dir = "./cache"
        os.makedirs(self.cache_dir, exist_ok=True)

    async def debug_naver_news(self):
        """네이버 뉴스 페이지 구조 디버깅"""
        print(">>> 네이버 뉴스 페이지 구조 분석 시작")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # 브라우저 창 보이게
                slow_mo=1000,  # 동작을 천천히 (1초씩 대기)
            )

            page = await browser.new_page()

            try:
                # 여러 URL 시도
                urls_to_test = [
                    "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258",
                    "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=259",
                    "https://finance.naver.com/news/mainnews.naver",
                ]

                for i, url in enumerate(urls_to_test, 1):
                    print(f"\n>> URL {i} 테스트: {url}")

                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)  # 3초 대기

                    print(f"> 페이지 로딩 완료")

                    # 페이지 제목 확인
                    title = await page.title()
                    print(f"> 페이지 제목: {title}")

                    # 다양한 셀렉터 시도
                    selectors_to_test = [
                        "td.title a",
                        "dd.articleSubject a",
                        "dl.newsList dt a",
                        "li a[href*='news']",
                        "a[href*='article']",
                        "table.type_1 a",
                        "div.mainNewsList a",
                        "a",  # 모든 링크
                    ]

                    for j, selector in enumerate(selectors_to_test, 1):
                        try:
                            elements = await page.query_selector_all(selector)
                            print(
                                f"- 셀렉터 {j} '{selector}': {len(elements)}개 요소 발견"
                            )

                            # 상위 3개 요소의 텍스트 확인
                            if elements:
                                for k, element in enumerate(elements[:3]):
                                    try:
                                        text = await element.inner_text()
                                        href = await element.get_attribute("href")
                                        print(f"  {k+1}. 텍스트: '{text[:50]}...'")
                                        print(f"     링크: {href}")
                                    except:
                                        print(f"  {k+1}. 텍스트 추출 실패")

                        except Exception as e:
                            print(f"- 셀렉터 {j} 오류: {e}")

                    # 페이지 HTML 일부 저장 (디버깅용)
                    html_content = await page.content()
                    html_file = os.path.join(self.cache_dir, f"debug_page_{i}.html")
                    with open(html_file, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    print(f"> HTML 저장: {html_file}")

                    # 스크린샷 찍기
                    screenshot_file = os.path.join(
                        self.cache_dir, f"debug_page_{i}.png"
                    )
                    await page.screenshot(path=screenshot_file, full_page=True)
                    print(f"> 스크린샷 저장: {screenshot_file}")

                    print(f">> URL {i} 분석 완료\n")

                    # 다음 URL로 넘어가기 전 잠시 대기
                    await page.wait_for_timeout(2000)

            finally:
                await browser.close()

        print(">>> 디버깅 완료")

    async def test_specific_selector(self, url: str, selector: str):
        """특정 셀렉터 테스트"""
        print(f">>> 특정 셀렉터 테스트: {selector}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                elements = await page.query_selector_all(selector)
                print(f"> 발견된 요소: {len(elements)}개")

                results = []
                for i, element in enumerate(elements[:10]):  # 상위 10개만
                    try:
                        text = await element.inner_text()
                        href = await element.get_attribute("href")

                        result = {
                            "index": i + 1,
                            "text": text.strip(),
                            "href": href,
                            "is_news": bool(
                                href and ("news" in href or "article" in href)
                            ),
                        }
                        results.append(result)

                        print(f"{i+1}. {text[:60]}...")
                        print(f"   링크: {href}")
                        print(f"   뉴스 링크?: {result['is_news']}")
                        print()

                    except Exception as e:
                        print(f"{i+1}. 요소 처리 오류: {e}")

                # 결과 JSON 저장
                result_file = os.path.join(self.cache_dir, "selector_test_result.json")
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "url": url,
                            "selector": selector,
                            "total_elements": len(elements),
                            "results": results,
                            "test_time": datetime.now().isoformat(),
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )

                print(f">>> 결과 저장: {result_file}")

            finally:
                await browser.close()


async def main():
    """메인 디버깅 함수"""
    crawler = DebugPlaywrightCrawler()

    print("1. 전체 페이지 구조 분석")
    print("2. 특정 셀렉터 테스트")
    choice = input("선택 (1 or 2): ")

    if choice == "1":
        await crawler.debug_naver_news()
    elif choice == "2":
        url = "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258"
        selector = input("테스트할 CSS 셀렉터 입력: ")
        await crawler.test_specific_selector(url, selector)
    else:
        print("자동으로 전체 분석 실행")
        await crawler.debug_naver_news()


if __name__ == "__main__":
    asyncio.run(main())
