"""
Multi-Format Document Parser (PDF, TXT, CSV, DOCX, Code) with OCR Fallback.
"""
import io
import logging
import pypdf
import google.generativeai as genai
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
                
                # Se for PDF escaneado (imagem sem texto selecionável) e tiver Gemini API
                if len(extracted.strip()) < 30 and settings.GEMINI_API_KEY:
                    logger.info(f"PDF '{file_name}' parece ser escaneado. Ativando OCR via Gemini Multimodal...")
                    try:
                        model = genai.GenerativeModel("gemini-2.0-flash")
                        pdf_part = {
                            "mime_type": "application/pdf",
                            "data": bytes(file_bytes)
                        }
                        response = model.generate_content([
                            pdf_part,
                            "Extraia e transcreva todo o conteúdo textual e estruturado deste documento PDF com máxima fidelidade:"
                        ])
                        if response and response.text:
                            extracted = response.text
                            logger.info(f"OCR via Gemini concluiu extração de {len(extracted)} caracteres.")
                    except Exception as ocr_err:
                        logger.warning(f"Falha no OCR Gemini do PDF: {ocr_err}")

            # 2. Arquivos de Texto / Código / CSV / JSON / Markdown
            else:
                extracted = file_bytes.decode("utf-8", errors="replace")

            # Trunca de forma segura caso o documento seja gigantesco
            if len(extracted) > max_chars:
                extracted = extracted[:max_chars] + f"\n\n[... Truncado para caber no limite de {max_chars} caracteres ...]"

            result = extracted.strip()
            if not result:
                return (
                    "⚠️ O arquivo foi recebido, mas não contém texto selecionável (pode ser uma imagem escaneada). "
                    "Por favor, envie o texto copiado ou uma foto clara da página para análise via Visão Computacional."
                )

            return result

        except Exception as e:
            logger.error(f"Erro ao extrair arquivo {file_name}: {e}")
            return f"[Erro na leitura do arquivo {file_name}: {e}]"

document_parser = DocumentParser()
