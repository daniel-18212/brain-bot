"""
Multi-Format Document Parser (PDF, TXT, CSV, DOCX, Code).
"""
import io
import logging
import pypdf

logger = logging.getLogger(__name__)

class DocumentParser:
    @staticmethod
    def extract_text(file_bytes: bytearray, file_name: str, max_chars: int = 40000) -> str:
        """Extrai texto estruturado de documentos e arquivos de código."""
        lower_name = file_name.lower()
        extracted = ""

        try:
            # Arquivos PDF
            if lower_name.endswith(".pdf"):
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                for page_num, page in enumerate(reader.pages, start=1):
                    text = page.extract_text() or ""
                    extracted += f"\n--- Página {page_num} ---\n{text}"
            
            # Arquivos de Texto / Código / CSV / JSON
            else:
                extracted = file_bytes.decode("utf-8", errors="replace")

            # Trunca de forma segura para não estourar os limites de contexto
            if len(extracted) > max_chars:
                extracted = extracted[:max_chars] + f"\n\n[... Truncado para caber no limite de {max_chars} caracteres ...]"

            return extracted.strip()
        except Exception as e:
            logger.error(f"Erro ao extrair arquivo {file_name}: {e}")
            return f"[Erro na leitura do arquivo {file_name}: {e}]"

document_parser = DocumentParser()
