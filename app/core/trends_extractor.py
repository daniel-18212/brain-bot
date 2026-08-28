"""
Real-Time X (Twitter) Trends & Trending Topics Extractor for Brazil and Global.
Fetches top viral topics and trending hashtags with zero API cost.
"""
from datetime import datetime
import logging
import urllib.parse
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class TrendsExtractor:
    @staticmethod
    async def get_x_trends_brazil(limit: int = 15) -> list[dict]:
        """Extrai os Trending Topics do X (Twitter) Brasil em tempo real."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        url = "https://trends24.in/brazil/"
        
        trends = []
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, "html.parser")
                        
                        # Localiza a lista de trends da hora mais recente
                        first_card = soup.select_one(".trend-card")
                        if first_card:
                            items = first_card.select(".trend-card__list li")
                            for idx, li in enumerate(items[:limit], start=1):
                                tag_link = li.select_one("a")
                                tweet_count_el = li.select_one(".tweet-count")
                                if tag_link:
                                    topic = tag_link.get_text(strip=True)
                                    count = tweet_count_el.get_text(strip=True) if tweet_count_el else "Em alta"
                                    trends.append({
                                        "rank": idx,
                                        "topic": topic,
                                        "tweet_count": count
                                    })
        except Exception as e:
            logger.warning(f"Falha ao extrair trends do Trends24: {e}")

        # Fallback via GetDayTrends se necessário
        if not trends:
            try:
                url_fallback = "https://getdaytrends.com/brazil/"
                timeout = aiohttp.ClientTimeout(total=8)
                async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                    async with session.get(url_fallback) as resp:
                        if resp.status == 200:
                            html = await resp.text()
                            soup = BeautifulSoup(html, "html.parser")
                            rows = soup.select("table.table tbody tr")
                            for idx, tr in enumerate(rows[:limit], start=1):
                                a_tag = tr.select_one(".main a")
                                if a_tag:
                                    topic = a_tag.get_text(strip=True)
                                    trends.append({
                                        "rank": idx,
                                        "topic": topic,
                                        "tweet_count": "Em alta"
                                    })
            except Exception as e2:
                logger.warning(f"Falha no fallback de trends: {e2}")

        return trends

    @classmethod
    async def get_trends_summary_prompt(cls) -> str:
        """Gera o contexto formatado com os Trending Topics para alimentar a IA."""
        trends = await cls.get_x_trends_brazil(limit=15)
        now_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
        
        if not trends:
            return "Não foi possível recuperar a lista do X em tempo real no momento."

        lines = [f"🔥 [TRENDING TOPICS DO X (TWITTER) BRASIL — ATUALIZADO EM {now_str}]:\n"]
        for t in trends:
            lines.append(f"{t['rank']}. **{t['topic']}** ({t['tweet_count']})")

        return "\n".join(lines)

trends_extractor = TrendsExtractor()
