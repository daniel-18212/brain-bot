"""
High-Performance Live Web Search Engine with Multi-Query Auto Detection and Resilient Async Scraping.
"""
from datetime import datetime
import logging
import re
import urllib.parse
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Palavras e padrões que ativam busca em tempo real na Web
SEARCH_PATTERNS = [
    r"\b(not[ií]cia|not[ií]cias|manchete|manchetes)\b",
    r"\b(hoje|agora|atualmente|recente|recentes|ontem|esta semana|da semana|do momento|em alta|trends|trending)\b",
    r"\b(clima|tempo|temperatura|previs[aã]o|chuva)\b",
    r"\b(pre[çc]o|cota[çc][aã]o|valor|quanto t[aá]|quanto custa)\b",
    r"\b(quem ganhou|quem venceu|resultado|placar|tabela|jogo|partida|campeonato)\b",
    r"\b(lan[çc]amento|lan[çc]ou|novidade|novidades|saiu)\b",
    r"\b(d[oó]lar|euro|bitcoin|btc|eth|sol|a[çc][oõ]es|ibovespa|selic|cdi|infla[çc][aã]o)\b",
    r"\b(atualiza[çc][aã]o|vers[aã]o mais recente|update|novas regras)\b",
    r"\b(o que aconteceu|o que est[aá] acontecendo|quem [eé] o atual|presidente atual|ministro)\b",
    r"\b(assunto|assuntos mais falado|assuntos mais falados|mais comentad[ao]s?)\b",
    r"\b(fofoca|bbb|pol[ií]tica|elei[çc][oõ]es)\b",
]

class WebSearchEngine:
    @staticmethod
    def should_trigger_search(text: str) -> bool:
        """Detecta se a mensagem do usuário necessita de informações em tempo real da internet."""
        if not text or len(text.strip()) < 3:
            return False
        
        lower = text.lower()
        for pattern in SEARCH_PATTERNS:
            if re.search(pattern, lower, re.IGNORECASE):
                return True
        return False

    async def search(self, query: str, max_results: int = 5) -> str:
        """Executa busca assíncrona ao vivo e extrai os títulos, resumos e fontes reais."""
        # Limpa e otimiza a query de busca
        clean_query = query.strip()
        for p in ["/web", "pesquise", "busque", "procure", "me diga", "quais os", "qual o"]:
            if clean_query.lower().startswith(p):
                clean_query = clean_query[len(p):].strip()
        
        if not clean_query:
            clean_query = query

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(clean_query)}"
        
        try:
            timeout = aiohttp.ClientTimeout(total=12)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, "html.parser")
                        results = []
                        
                        for r in soup.select(".result"):
                            title_el = r.select_one(".result__title a")
                            snippet_el = r.select_one(".result__snippet")
                            if title_el and snippet_el:
                                title = title_el.get_text(strip=True)
                                raw_link = title_el.get("href", "")
                                
                                # Decodifica link real do DuckDuckGo
                                if "uddg=" in raw_link:
                                    try:
                                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_link).query)
                                        real_link = parsed.get("uddg", [raw_link])[0]
                                    except Exception:
                                        real_link = raw_link
                                else:
                                    real_link = raw_link

                                snippet = snippet_el.get_text(strip=True)
                                if snippet and title:
                                    results.append(f"• **{title}**\n  {snippet}\n  🔗 Fonte: {real_link}")
                                    if len(results) >= max_results:
                                        break

                        if results:
                            now_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
                            header = f"🌐 [RESULTADOS DE PESQUISA WEB EM TEMPO REAL — {now_str}]:\n"
                            return header + "\n\n".join(results)

        except Exception as e:
            logger.warning(f"Falha na busca web primária: {e}")

        # Fallback para busca na Wikipedia caso a primária falhe
        try:
            wiki_url = f"https://pt.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(clean_query)}&limit=3&namespace=0&format=json"
            timeout = aiohttp.ClientTimeout(total=6)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.get(wiki_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if len(data) >= 4 and data[1]:
                            wiki_res = []
                            for t, d, l in zip(data[1], data[2], data[3]):
                                if d:
                                    wiki_res.append(f"• **{t}**: {d}\n  🔗 Fonte: {l}")
                            if wiki_res:
                                return "🌐 [DADOS DE CONSULTA DA WEB]:\n" + "\n\n".join(wiki_res)
        except Exception as wiki_err:
            logger.warning(f"Falha no fallback Wikipedia: {wiki_err}")

        return "🌐 [Nota]: A pesquisa ao vivo não retornou resultados suficientes. Responda com base no conhecimento mais recente disponível."

web_search_engine = WebSearchEngine()
