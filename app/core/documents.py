"""
Multi-Format Document Parser (PDF, TXT, CSV, DOCX, Code) with High-Performance Text Extraction.
"""
import io
import logging
import pypdf
from app.config import settings

logger = logging.getLogger(__name__)

class DocumentParser:
    @staticmethod
    def extract_text(file_bytes: bytearray, file_name: str, max_chars: int = 50000) -> str:
        """Extrai texto estruturado de documentos e arquivos de código."""
        lower_name = file_name.lower()
        extracted = ""

        try:
            # 1. Arquivos PDF
            if lower_name.endswith(".pdf"):
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                num_pages = len(reader.pages)
                logger.info(f"Lendo PDF '{file_name}' com {num_pages} páginas...")
                
                for page_num, page in enumerate(reader.pages, start=1):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        extracted += f"\n--- Página {page_num} ---\n{page_text}"

            # 2. Arquivos de Texto / Código / CSV / JSON / Markdown
            else:
                extracted = file_bytes.decode("utf-8", errors="replace")

            # Trunca de forma segura caso o documento seja gigantesco
            if len(extracted) > max_chars:
                extracted = extracted[:max_chars] + f"\n\n[... Truncado após {max_chars} caracteres para otimização de contexto ...]"

            result = extracted.strip()
            if not result:
                return (
                    "⚠️ O arquivo foi recebido, mas não contém texto selecionável (pode ser uma imagem escaneada). "
                    "Por favor, envie uma foto da página para que o Gemini Vision analise os detalhes visuais."
                )

            return result

        except Exception as e:
            logger.error(f"Erro ao extrair arquivo {file_name}: {e}")
            return f"[Erro na leitura do arquivo {file_name}: {e}]"

document_parser = DocumentParser()
