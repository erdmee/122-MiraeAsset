# app/services/enhanced_data_collector.py (최종 수정 - 동기/비동기 명확 분리)
import requests
import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import re
from pykrx import stock
import OpenDartReader
import pandas as pd
import sqlite3
from app.config import settings
from app.models.responses import NewsItem, DisclosureItem, MarketData
from app.models.user_models import StockPrice
from .playwright_news_crawler import PlaywrightNewsCrawler


class EnhancedDataCollector:
    """향상된 금융 데이터 수집 시스템 (Playwright 통합 - 최종 수정)"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.USER_AGENT})
        self.cache_dir = settings.CACHE_DIR
        self.db_path = settings.DB_PATH
        os.makedirs(self.cache_dir, exist_ok=True)
        self.dart = (
            OpenDartReader(settings.DART_API_KEY) if settings.DART_API_KEY else None
        )

        # Playwright 크롤러 초기화
        self.playwright_crawler = PlaywrightNewsCrawler(self.cache_dir)

        self.init_database()
        print(">>> 데이터 수집기 초기화 완료 (Playwright 통합 - 최종 수정)")

    def init_database(self):
        """SQLite 데이터베이스 및 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS news (id INTEGER PRIMARY KEY, title TEXT UNIQUE, content TEXT, source TEXT, published_at TEXT, entities TEXT, importance_score REAL, sentiment_score REAL)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS disclosures (id INTEGER PRIMARY KEY, company TEXT, title TEXT UNIQUE, date TEXT, type TEXT, importance_score REAL)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS stock_prices (id INTEGER PRIMARY KEY, symbol TEXT UNIQUE, company_name TEXT, price INTEGER, change_amount INTEGER, change_percent REAL, volume INTEGER, market_cap INTEGER, date TEXT)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS user_portfolios (id INTEGER PRIMARY KEY, user_id TEXT, symbol TEXT, company_name TEXT, shares INTEGER, avg_price INTEGER, sector TEXT)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS user_preferences (user_id TEXT PRIMARY KEY, preferred_sectors TEXT, risk_level TEXT, investment_style TEXT, news_keywords TEXT)"
        )
        conn.commit()
        conn.close()

    # === 동기 버전 메서드들 (기존 방식) ===

    def collect_comprehensive_news(
        self, limit: int = 20, use_playwright: bool = True
    ) -> List[NewsItem]:
        """동기 종합 뉴스 수집 (Playwright 스레드 방식)"""
        print(
            f">>> 뉴스 수집 모드: {'Playwright' if use_playwright else 'BeautifulSoup'}"
        )

        if use_playwright:
            try:
                print(">> Playwright 모드로 뉴스 수집 중...")

                # 스레드 방식으로 Playwright 실행 (동기 환경용)
                import concurrent.futures
                import threading

                def run_playwright_in_thread():
                    """별도 스레드에서 Playwright 실행"""
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            self.playwright_crawler.collect_naver_financial_news(limit)
                        )
                    finally:
                        new_loop.close()

                # 스레드에서 실행
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_playwright_in_thread)
                    playwright_data = future.result(timeout=120)  # 2분 타임아웃

                # Playwright 데이터를 NewsItem 객체로 변환
                news_items = []
                for item_data in playwright_data:
                    news_item = NewsItem(
                        title=item_data["title"],
                        summary=item_data["summary"],
                        source=item_data["source"] or "네이버금융",
                        published_at=item_data["published_at"]
                        or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        entities=item_data["entities"],
                        importance_score=item_data["importance_score"],
                    )
                    news_items.append(news_item)

                if news_items:
                    self._save_news_to_db(news_items)
                    print(
                        f">>> Playwright로 뉴스 {len(news_items)}건 수집 및 저장 완료"
                    )
                    return news_items
                else:
                    print(">> Playwright 수집 실패, BeautifulSoup으로 재시도...")

            except Exception as e:
                print(f">> Playwright 오류: {e}")
                print(">> BeautifulSoup 방식으로 폴백...")

        # BeautifulSoup 폴백
        print(">> BeautifulSoup 모드로 뉴스 수집 중...")
        return self._collect_naver_financial_news_fallback(limit)

    def collect_all_data(
        self,
        user_id: Optional[str] = None,
        refresh_cache: bool = False,
        use_playwright: bool = True,
    ) -> Dict:
        """전체 데이터 수집 (동기 버전)"""
        print(
            f">> 실제 금융 데이터 수집 시작 (동기 모드, {'Playwright' if use_playwright else 'BeautifulSoup'})"
        )

        # 뉴스 수집 (동기 버전 사용)
        news = self.collect_comprehensive_news(limit=10, use_playwright=use_playwright)

        # 공시 수집
        disclosures = self.collect_comprehensive_disclosures(limit=10)

        # 사용자별 맞춤 종목 리스트 구성
        all_symbols = ["005930", "000660", "035420"]
        personalized_data = {}

        if user_id:
            personalized_data = self.get_personalized_data(user_id)
            if personalized_data.get("portfolio"):
                portfolio_symbols = {
                    holding[0] for holding in personalized_data["portfolio"]
                }
                all_symbols.extend(list(portfolio_symbols))
                all_symbols = list(set(all_symbols))

        # 주식 데이터 수집
        stock_data = self.collect_comprehensive_stock_data(all_symbols)

        # 데이터 수집 결과 검증
        total_collected = len(news) + len(disclosures) + len(stock_data)
        if total_collected == 0:
            print(">> 경고: 모든 실제 데이터 수집에 실패했습니다.")
        else:
            print(f">> 총 {total_collected}건의 실제 데이터 수집 완료")

        result = {
            "news": news,
            "disclosures": disclosures,
            "stock_data": stock_data,
            "personalized": personalized_data,
            "collected_at": datetime.now().isoformat(),
            "data_sources": {
                "news_count": len(news),
                "disclosures_count": len(disclosures),
                "stock_count": len(stock_data),
                "is_playwright_used": use_playwright,
                "is_real_data_only": True,
                "collection_mode": "synchronous",
            },
        }

        return result

    # === 비동기 버전 메서드들 (FastAPI 전용) ===

    async def collect_comprehensive_news_async(
        self, limit: int = 20, use_playwright: bool = True
    ) -> List[NewsItem]:
        """비동기 종합 뉴스 수집 (FastAPI 환경용)"""
        print(
            f">>> 뉴스 수집 모드: {'Playwright' if use_playwright else 'BeautifulSoup'} (비동기)"
        )

        if use_playwright:
            try:
                print(">> Playwright 모드로 뉴스 수집 중... (비동기)")

                # FastAPI 환경에서는 직접 await 사용
                playwright_data = (
                    await self.playwright_crawler.collect_naver_financial_news(limit)
                )

                # Playwright 데이터를 NewsItem 객체로 변환
                news_items = []
                for item_data in playwright_data:
                    news_item = NewsItem(
                        title=item_data["title"],
                        summary=item_data["summary"],
                        source=item_data["source"] or "네이버금융",
                        published_at=item_data["published_at"]
                        or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        entities=item_data["entities"],
                        importance_score=item_data["importance_score"],
                    )
                    news_items.append(news_item)

                if news_items:
                    self._save_news_to_db(news_items)
                    print(
                        f">>> Playwright로 뉴스 {len(news_items)}건 수집 및 저장 완료 (비동기)"
                    )
                    return news_items
                else:
                    print(">> Playwright 수집 실패, BeautifulSoup으로 재시도...")

            except Exception as e:
                print(f">> Playwright 오류 (비동기): {e}")
                print(">> BeautifulSoup 방식으로 폴백...")

        # BeautifulSoup 폴백
        print(">> BeautifulSoup 모드로 뉴스 수집 중... (비동기)")
        return self._collect_naver_financial_news_fallback(limit)

    async def collect_all_data_async(
        self,
        user_id: Optional[str] = None,
        refresh_cache: bool = False,
        use_playwright: bool = True,
    ) -> Dict:
        """전체 데이터 수집 (비동기 버전 - FastAPI용)"""
        print(
            f">> 실제 금융 데이터 수집 시작 (비동기 모드, {'Playwright' if use_playwright else 'BeautifulSoup'})"
        )

        # 뉴스 수집 (비동기)
        news = await self.collect_comprehensive_news_async(
            limit=10, use_playwright=use_playwright
        )

        # 공시 수집 (동기)
        disclosures = self.collect_comprehensive_disclosures(limit=10)

        # 사용자별 맞춤 종목 리스트 구성
        all_symbols = ["005930", "000660", "035420"]
        personalized_data = {}

        if user_id:
            personalized_data = self.get_personalized_data(user_id)
            if personalized_data.get("portfolio"):
                portfolio_symbols = {
                    holding[0] for holding in personalized_data["portfolio"]
                }
                all_symbols.extend(list(portfolio_symbols))
                all_symbols = list(set(all_symbols))

        # 주식 데이터 수집 (동기)
        stock_data = self.collect_comprehensive_stock_data(all_symbols)

        # 데이터 수집 결과 검증
        total_collected = len(news) + len(disclosures) + len(stock_data)
        if total_collected == 0:
            print(">> 경고: 모든 실제 데이터 수집에 실패했습니다.")
        else:
            print(f">> 총 {total_collected}건의 실제 데이터 수집 완료")

        result = {
            "news": news,
            "disclosures": disclosures,
            "stock_data": stock_data,
            "personalized": personalized_data,
            "collected_at": datetime.now().isoformat(),
            "data_sources": {
                "news_count": len(news),
                "disclosures_count": len(disclosures),
                "stock_count": len(stock_data),
                "is_playwright_used": use_playwright,
                "is_real_data_only": True,
                "collection_mode": "asynchronous",
            },
        }

        return result

    # === 공통 메서드들 ===

    def _collect_naver_financial_news_fallback(self, limit: int) -> List[NewsItem]:
        """BeautifulSoup 기반 뉴스 수집 (폴백용)"""
        from bs4 import BeautifulSoup

        print(">>> BeautifulSoup 폴백 뉴스 수집 시작")

        urls_to_try = [
            "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258",
            "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=259",
            "https://finance.naver.com/news/mainnews.naver",
        ]

        items = []

        for url in urls_to_try:
            try:
                print(f">> BeautifulSoup: {url}")
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")

                # CSS 셀렉터 시도
                selectors = [
                    "dd.articleSubject a",
                    "td.title a",
                    "div.mainNewsList li a",
                ]

                for selector in selectors:
                    news_links = soup.select(selector)
                    if news_links:
                        print(f"- {selector}: {len(news_links)}개 발견")
                        break

                if not news_links:
                    continue

                for link in news_links[:limit]:
                    try:
                        title = link.text.strip()
                        if not title or len(title) < 5:
                            continue

                        news_item = NewsItem(
                            title=title,
                            summary=title[:100],
                            source="네이버금융",
                            published_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            entities=self._extract_entities_from_text(title),
                            importance_score=self._calculate_importance_score(
                                {"title": title}
                            ),
                        )
                        items.append(news_item)

                    except Exception as e:
                        print(f"- BeautifulSoup 뉴스 파싱 오류: {e}")
                        continue

                if items:
                    break

            except Exception as e:
                print(f"- BeautifulSoup URL 실패: {e}")
                continue

        if items:
            self._save_news_to_db(items)
            print(f">>> BeautifulSoup로 뉴스 {len(items)}건 수집 완료")
        else:
            print(">>> BeautifulSoup 뉴스 수집 실패")

        return items

    def collect_comprehensive_disclosures(
        self, limit: int = 50
    ) -> List[DisclosureItem]:
        """공시 수집 (기존 로직 유지)"""
        if not self.dart:
            print(">> DART API 키가 없어 공시 수집을 할 수 없습니다.")
            return []

        print(">> DART 공시 정보 수집 중...")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            disclosures_df = self.dart.list(
                start=start_date.strftime("%Y%m%d"),
                end=end_date.strftime("%Y%m%d"),
                kind="A",
            )

            if disclosures_df.empty:
                print(">> DART에서 공시 데이터를 가져올 수 없습니다.")
                return []

            items = [
                DisclosureItem(
                    company=row["corp_name"],
                    title=row["report_nm"],
                    date=row["rcept_dt"],
                    type=row["corp_cls"],
                    importance_score=self._calculate_disclosure_importance(row),
                )
                for _, row in disclosures_df.head(limit).iterrows()
            ]

            if items:
                self._save_disclosures_to_db(items)
                print(f">> 공시 {len(items)}건 수집 및 저장 완료")
            return items

        except Exception as e:
            print(f">> DART 공시 수집 실패: {e}")
            return []

    def collect_comprehensive_stock_data(
        self, symbols: Optional[List[str]] = None
    ) -> List[StockPrice]:
        """주식 데이터 수집 (개선된 버전)"""
        if not symbols:
            symbols = ["005930", "000660", "035420"]

        print(f">> {len(symbols)}개 종목의 실제 시세 정보 수집 중...")

        # 여러 날짜 시도
        dates_to_try = []
        base_date = datetime.now()

        for i in range(5):
            target_date = base_date - timedelta(days=i)
            if target_date.weekday() < 5:  # 평일만
                dates_to_try.append(target_date.strftime("%Y%m%d"))

        print(f">> 시도할 거래일: {dates_to_try}")

        stock_data = []

        for date_str in dates_to_try:
            print(f"\n>> {date_str} 데이터 수집 시도...")
            successful_count = 0

            try:
                df = stock.get_market_ohlcv(date_str, market="ALL")
                cap_df = stock.get_market_cap(date_str, market="ALL")

                if df.empty:
                    print(f">> {date_str}: 시장 데이터가 없습니다.")
                    continue

                for symbol in symbols:
                    try:
                        name = stock.get_market_ticker_name(symbol)
                        if not name:
                            continue

                        if symbol not in df.index:
                            print(
                                f">> {symbol}({name}): {date_str} 거래 데이터가 없습니다."
                            )
                            continue

                        data = df.loc[symbol]

                        if (
                            data["종가"] == 0
                            or pd.isna(data["종가"])
                            or data["종가"] < 100
                        ):
                            print(
                                f">> {symbol}({name}): 종가가 유효하지 않습니다 (가격: {data['종가']})"
                            )
                            continue

                        market_cap = 0
                        try:
                            if symbol in cap_df.index and not pd.isna(
                                cap_df.loc[symbol]["시가총액"]
                            ):
                                market_cap = int(cap_df.loc[symbol]["시가총액"])
                        except Exception as e:
                            print(f">> {symbol} 시가총액 정보 없음: {e}")

                        change_amount = (
                            int(data["종가"] - data["시가"])
                            if not pd.isna(data["시가"])
                            else 0
                        )
                        change_percent = (
                            float(data["등락률"])
                            if not pd.isna(data["등락률"])
                            else 0.0
                        )

                        stock_price = StockPrice(
                            symbol=symbol,
                            company_name=name,
                            price=int(data["종가"]),
                            change_amount=change_amount,
                            change_percent=change_percent,
                            volume=(
                                int(data["거래량"])
                                if not pd.isna(data["거래량"])
                                else 0
                            ),
                            market_cap=market_cap,
                            date=date_str,
                        )

                        stock_data.append(stock_price)
                        successful_count += 1
                        print(
                            f">> {name}({symbol}): {stock_price.price:,}원 ({stock_price.change_percent:+.2f}%) [{date_str}]"
                        )

                    except Exception as e:
                        print(f">> {symbol} 개별 수집 실패: {e}")
                        continue

                if successful_count > 0:
                    print(
                        f">> {date_str} 데이터로 {successful_count}개 종목 수집 성공!"
                    )
                    break

            except Exception as e:
                print(f">> {date_str} 전체 데이터 수집 실패: {e}")
                continue

        if stock_data:
            self._save_stock_data_to_db(stock_data)
            print(f"\n>> 실제 주식 데이터 {len(stock_data)}건 수집 및 저장 완료")
        else:
            print(f"\n>> 모든 날짜에서 주식 데이터 수집 실패")

        return stock_data

    # 나머지 헬퍼 메서드들은 기존과 동일...
    def _extract_entities_from_text(self, text: str) -> List[str]:
        """텍스트에서 금융 엔티티 추출"""
        known_entities = [
            "삼성전자",
            "SK하이닉스",
            "네이버",
            "카카오",
            "현대차",
            "LG화학",
            "AI",
            "반도체",
            "배터리",
            "전기차",
            "바이오",
            "플랫폼",
            "비트코인",
            "스테이블코인",
            "암호화폐",
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

    def _calculate_importance_score(self, article_data: Dict) -> float:
        """뉴스 중요도 점수 계산"""
        title = article_data.get("title", "").lower()
        content = article_data.get("content", "").lower()

        high_keywords = ["실적", "발표", "급등", "급락", "신제품", "인수", "합병"]
        medium_keywords = ["상승", "하락", "전망", "계획", "투자"]

        score = 1.0

        for keyword in high_keywords:
            if keyword in title:
                score += 1.5

        for keyword in medium_keywords:
            if keyword in title:
                score += 0.5

        return min(score, 5.0)

    def _calculate_disclosure_importance(self, disclosure) -> float:
        """공시 중요도 점수 계산"""
        title = str(disclosure.get("report_nm", "")).lower()

        if any(
            keyword in title for keyword in ["분기보고서", "반기보고서", "사업보고서"]
        ):
            return 3.0
        elif any(keyword in title for keyword in ["실적", "배당"]):
            return 2.5
        else:
            return 1.5

    def _save_news_to_db(self, news_items: List[NewsItem]):
        """뉴스를 데이터베이스에 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR IGNORE INTO news (title, content, source, published_at, entities, importance_score) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    n.title,
                    n.summary,
                    n.source,
                    n.published_at,
                    json.dumps(n.entities, ensure_ascii=False),
                    n.importance_score,
                )
                for n in news_items
            ],
        )
        conn.commit()
        conn.close()

    def _save_disclosures_to_db(self, disclosures: List[DisclosureItem]):
        """공시를 데이터베이스에 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR IGNORE INTO disclosures (company, title, date, type, importance_score) VALUES (?, ?, ?, ?, ?)",
            [
                (d.company, d.title, d.date, d.type, d.importance_score)
                for d in disclosures
            ],
        )
        conn.commit()
        conn.close()

    def _save_stock_data_to_db(self, stock_data: List[StockPrice]):
        """주식 데이터를 데이터베이스에 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR REPLACE INTO stock_prices (symbol, company_name, price, change_amount, change_percent, volume, market_cap, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    s.symbol,
                    s.company_name,
                    s.price,
                    s.change_amount,
                    s.change_percent,
                    s.volume,
                    s.market_cap,
                    s.date,
                )
                for s in stock_data
            ],
        )
        conn.commit()
        conn.close()

    def get_personalized_data(self, user_id: str) -> Dict:
        """사용자 개인화 데이터 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT symbol, company_name, shares, avg_price, sector FROM user_portfolios WHERE user_id = ?",
            (user_id,),
        )
        portfolio = cursor.fetchall()

        cursor.execute(
            "SELECT preferred_sectors, risk_level, investment_style, news_keywords FROM user_preferences WHERE user_id = ?",
            (user_id,),
        )
        pref_tuple = cursor.fetchone()
        conn.close()

        preferences = (
            {
                "preferred_sectors": pref_tuple[0],
                "risk_level": pref_tuple[1],
                "investment_style": pref_tuple[2],
                "news_keywords": pref_tuple[3],
            }
            if pref_tuple
            else {}
        )

        return {"portfolio": portfolio, "preferences": preferences}
