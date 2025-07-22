# app/services/playwright_news_crawler.py
import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict
from playwright.async_api import async_playwright


class PlaywrightNewsCrawler:
    """Playwright 기반 네이버 뉴스 크롤러 (서비스 모듈)"""

    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = cache_dir
        self.collected_data = {
            "collection_time": datetime.now().isoformat(),
            "source": "naver_finance_playwright",
            "news_items": [],
        }

    async def collect_naver_financial_news(self, limit: int = 10) -> List[Dict]:
        """Playwright로 네이버 금융 뉴스 수집"""
        print(">>> Playwright 네이버 뉴스 크롤링 시작")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,  # 서비스에서는 헤드리스 모드
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )

            page = await browser.new_page()

            # User-Agent 설정
            await page.set_extra_http_headers(
                {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )

            try:
                # 여러 URL 시도
                urls_to_try = [
                    "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258",
                    "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=259",
                    "https://finance.naver.com/news/mainnews.naver",
                ]

                collected_count = 0

                for url_index, target_url in enumerate(urls_to_try, 1):
                    if collected_count >= limit:
                        break

                    print(f">> URL {url_index} 처리: {target_url}")

                    await page.goto(
                        target_url, wait_until="domcontentloaded", timeout=30000
                    )
                    await page.wait_for_timeout(2000)

                    # 올바른 셀렉터 사용
                    news_elements = await page.query_selector_all("dd.articleSubject a")
                    print(f"> 발견된 뉴스 링크: {len(news_elements)}개")

                    if not news_elements:
                        continue

                    # 뉴스 처리
                    for element in news_elements:
                        if collected_count >= limit:
                            break

                        try:
                            # 제목과 URL 추출
                            title = await element.inner_text()
                            news_url = await element.get_attribute("href")

                            if not title or len(title.strip()) < 5:
                                continue

                            title = title.strip()

                            # URL 정규화
                            if news_url and not news_url.startswith("http"):
                                if news_url.startswith("/"):
                                    news_url = "https://finance.naver.com" + news_url
                                else:
                                    news_url = "https://finance.naver.com/" + news_url

                            # 본문 내용 수집
                            content = ""
                            article_date = ""
                            article_source = ""

                            if news_url and "naver.com" in news_url:
                                # 새 탭에서 기사 열기
                                article_page = await browser.new_page()

                                try:
                                    await article_page.goto(
                                        news_url,
                                        wait_until="domcontentloaded",
                                        timeout=20000,
                                    )
                                    await article_page.wait_for_timeout(1500)

                                    # 본문 내용 추출
                                    content_selectors = [
                                        "div#newsct_article",
                                        "div.newsct_article._article_body",
                                        "div._article_body_contents",
                                        "div.news_end",
                                        "div.article_body",
                                    ]

                                    for selector in content_selectors:
                                        try:
                                            content_element = (
                                                await article_page.query_selector(
                                                    selector
                                                )
                                            )
                                            if content_element:
                                                content = (
                                                    await content_element.inner_text()
                                                )
                                                break
                                        except:
                                            continue

                                    if not content:
                                        content = "본문을 찾을 수 없습니다."

                                    # 날짜 추출
                                    try:
                                        date_selectors = [
                                            "span.date",
                                            "span.t11",
                                            "div.sponsor span",
                                        ]
                                        for date_sel in date_selectors:
                                            date_element = (
                                                await article_page.query_selector(
                                                    date_sel
                                                )
                                            )
                                            if date_element:
                                                article_date = (
                                                    await date_element.inner_text()
                                                )
                                                break
                                    except:
                                        article_date = datetime.now().strftime(
                                            "%Y-%m-%d"
                                        )

                                    # 출처 추출
                                    try:
                                        source_selectors = [
                                            "div.press_logo img",
                                            "span.source",
                                            "div.sponsor",
                                        ]
                                        for source_sel in source_selectors:
                                            source_element = (
                                                await article_page.query_selector(
                                                    source_sel
                                                )
                                            )
                                            if source_element:
                                                if await source_element.get_attribute(
                                                    "alt"
                                                ):
                                                    article_source = await source_element.get_attribute(
                                                        "alt"
                                                    )
                                                else:
                                                    article_source = (
                                                        await source_element.inner_text()
                                                    )
                                                break
                                    except:
                                        article_source = "네이버금융"

                                except Exception as e:
                                    content = "기사 내용을 가져올 수 없습니다."

                                finally:
                                    await article_page.close()
                            else:
                                content = "외부 링크로 본문 수집 불가"
                                article_source = "네이버금융"
                                article_date = datetime.now().strftime("%Y-%m-%d")

                            # 엔티티 추출
                            entities = self._extract_entities(title + " " + content)

                            # 중요도 계산
                            importance_score = self._calculate_importance(
                                title, content
                            )

                            # 데이터 저장
                            news_item = {
                                "id": f"playwright_news_{datetime.now().strftime('%Y%m%d')}_{collected_count + 1}",
                                "title": title,
                                "url": news_url,
                                "content": content,
                                "summary": (
                                    content[:300] + "..."
                                    if len(content) > 300
                                    else content
                                ),
                                "source": article_source,
                                "published_at": article_date,
                                "entities": entities,
                                "importance_score": importance_score,
                                "collected_at": datetime.now().isoformat(),
                            }

                            self.collected_data["news_items"].append(news_item)
                            collected_count += 1

                            print(f"> 뉴스 {collected_count} 수집 완료")

                            # 요청 간격 조절
                            await asyncio.sleep(1)

                        except Exception as e:
                            print(f"- 뉴스 처리 중 오류: {e}")
                            continue

                print(f">>> 전체 크롤링 완료: {collected_count}개 뉴스 수집")

            except Exception as e:
                print(f">> 크롤링 중 오류 발생: {e}")

            finally:
                await browser.close()

        # JSON 파일 저장
        await self._save_to_json()

        return self.collected_data["news_items"]

    def _extract_entities(self, text: str) -> List[str]:
        """엔티티 추출"""
        known_entities = [
            "삼성전자",
            "SK하이닉스",
            "네이버",
            "카카오",
            "현대차",
            "LG화학",
            "포스코",
            "현대캐피탈",
            "라온시큐어",
            "삼성운용",
            "한투운용",
            "AI",
            "반도체",
            "배터리",
            "전기차",
            "바이오",
            "플랫폼",
            "보안",
            "비트코인",
            "암호화폐",
            "스테이블코인",
            "블록체인",
            "기준금리",
            "환율",
            "코스피",
            "코스닥",
            "실적",
            "배당",
        ]

        found_entities = []
        text_upper = text.upper()

        for entity in known_entities:
            if entity in text or entity.upper() in text_upper:
                found_entities.append(entity)

        return list(set(found_entities))

    def _calculate_importance(self, title: str, content: str) -> float:
        """중요도 계산"""
        high_keywords = [
            "급등",
            "급락",
            "실적",
            "발표",
            "신제품",
            "인수",
            "합병",
            "구조대",
            "플러스",
        ]
        medium_keywords = ["상승", "하락", "투자", "개발", "계획", "출시", "진행"]

        score = 1.0
        title_lower = title.lower()

        for keyword in high_keywords:
            if keyword in title_lower:
                score += 2.0

        for keyword in medium_keywords:
            if keyword in title_lower:
                score += 1.0

        return min(score, 5.0)

    async def _save_to_json(self):
        """JSON 파일로 저장"""
        if not self.collected_data["news_items"]:
            return

        # 저장 디렉토리 생성
        save_dir = os.path.join(self.cache_dir, "playwright_news")
        os.makedirs(save_dir, exist_ok=True)

        # 파일명 생성
        filename = f"playwright_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(save_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.collected_data, f, ensure_ascii=False, indent=2)
            print(f">>> JSON 파일 저장 완료: {filepath}")
            print(f"- 저장된 뉴스 개수: {len(self.collected_data['news_items'])}")
        except Exception as e:
            print(f">>> JSON 파일 저장 실패: {e}")
