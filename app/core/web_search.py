"""
Live Web Search Integration using DuckDuckGo Engine.
"""
import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

class WebSearchEngine:
    async def search(self, query: str, max_results: int = 5) -> str:
        """Executa busca ao vivo e formata resultados com títulos e URLs."""
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(
                        f"🔹 **{r.get('title', 'Sem título')}**\n"
                        f"📝 {r.get('body', '')}\n"
                        f"🔗 {r.get('href', '')}"
                    )
            
            if not results:
                return "Nenhum resultado recente encontrado na web."
            
            return "\n\n".join(results)
        except Exception as e:
            logger.error(f"Erro na busca DuckDuckGo: {e}")
            return f"Erro ao acessar a web: {e}"

web_search_engine = WebSearchEngine()
