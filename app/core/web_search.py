"""
Live Web Search Integration with Automatic Intent Detection (DuckDuckGo Engine).
"""
import logging
import re
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

SEARCH_TRIGGERS = [
    r"\b(not[ií]cia|not[ií]cias)\b",
    r"\b(hoje|agora|atualmente|recente|recentes|ontem|esta semana)\b",
    r"\b(clima|tempo|temperatura|previs[aã]o)\b",
    r"\b(pre[çc]o|cota[çc][aã]o|valor)\b",
    r"\b(quem ganhou|quem venceu|resultado|placar|tabela|jogo)\b",
    r"\b(lan[çc]amento|lan[çc]ou|novidade|novidades)\b",
    r"\b(d[oó]lar|euro|bitcoin|btc|eth|sol|a[çc][oõ]es|ibovespa)\b",
    r"\b(atualiza[çc][aã]o|vers[aã]o mais recente|update)\b",
    r"\b(o que aconteceu|quem [eé] o atual|presidente atual)\b",
    r"\b(como est[aá]|como fica)\b",
]

class WebSearchEngine:
    @staticmethod
    def should_trigger_search(text: str) -> bool:
        """Detecta automaticamente se a mensagem do usuário exige busca em tempo real na web."""
        if not text or len(text.strip()) < 4:
            return False
        lower = text.lower()
        for pattern in SEARCH_TRIGGERS:
            if re.search(pattern, lower):
                return True
        return False

    async def search(self, query: str, max_results: int = 4) -> str:
        """Executa busca ao vivo e formata resultados com títulos, resumos e links."""
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    title = r.get("title", "Sem título")
                    body = r.get("body", "")
                    href = r.get("href", "")
                    results.append(f"• **{title}**\n  {body}\n  🔗 Fonte: {href}")
            
            if not results:
                return "Nenhum resultado recente encontrado na web."
            
            return "\n\n".join(results)
        except Exception as e:
            logger.error(f"Erro na busca DuckDuckGo: {e}")
            return f"Erro ao acessar a web: {e}"

web_search_engine = WebSearchEngine()
