"""
High-Speed Web Page URL Reader and Content Extractor.
Fetches pages, parses articles with BeautifulSoup, and formats for LLM analysis.
"""
import logging
import re
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class URLReader:
    URL_REGEX = re.compile(r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)")

    @classmethod
    def extract_urls(cls, text: str) -> list[str]:
        """Encontra todas as URLs contidas no texto."""
        if not text: return []
        return cls.URL_REGEX.findall(text)

    async def fetch_page_content(self, url: str, max_chars: int = 15000) -> str:
        """Baixa e extrai o texto principal de uma página web."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        try:
            timeout = aiohttp.ClientTimeout(total=12)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return f"[Falha ao acessar {url}: HTTP {response.status}]"
                    
                    html = await response.text(errors="replace")

            soup = BeautifulSoup(html, "html.parser")

            # Remove scripts, estilos, rodapés e anúncios
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "form"]):
                tag.extract()

            # Extrai título
            title = soup.title.string.strip() if soup.title and soup.title.string else url

            # Extrai texto limpo
            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 30]
            clean_article = "\n".join(lines)

            if len(clean_article) > max_chars:
                clean_article = clean_article[:max_chars] + f"\n\n[... Conteúdo truncado após {max_chars} caracteres ...]"

            return f"📄 **Título da Página:** {title}\n🔗 **URL:** {url}\n\n{clean_article}"

        except Exception as e:
            logger.error(f"Erro ao ler página {url}: {e}")
            return f"[Erro ao carregar link {url}: {e}]"

url_reader = URLReader()
