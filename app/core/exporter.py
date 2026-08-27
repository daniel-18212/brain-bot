"""
Conversation Transcript and Report Exporter to PDF, Markdown, and TXT.
"""
import io
from datetime import datetime
from fpdf import FPDF
import logging

logger = logging.getLogger(__name__)

class ConversationExporter:
    @staticmethod
    def export_to_markdown(messages: list[dict], user_name: str = "Usuário") -> io.BytesIO:
        """Exporta histórico em formato Markdown limpo e estruturado."""
        lines = [
            f"# 🧠 BrainBot — Relatório de Conversa",
            f"*Gerado em:* {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
            f"*Usuário:* {user_name}",
            f"\n---\n"
        ]

        for msg in messages:
            role = "👤 **Você**" if msg["role"] == "user" else "🤖 **BrainBot**"
            date_str = msg.get("created_at", "")
            lines.append(f"### {role} `({date_str})`\n")
            lines.append(f"{msg['content']}\n")
            lines.append("\n---\n")

        content = "\n".join(lines)
        buf = io.BytesIO(content.encode("utf-8"))
        buf.name = f"conversa_brainbot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        buf.seek(0)
        return buf

    @staticmethod
    def export_to_txt(messages: list[dict], user_name: str = "Usuário") -> io.BytesIO:
        """Exporta histórico em formato TXT simples."""
        lines = [
            f"=== BRAINBOT — HISTÓRICO DE CONVERSA ===",
            f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"Usuário: {user_name}\n",
            "=" * 50 + "\n"
        ]

        for msg in messages:
            role = "VOCÊ" if msg["role"] == "user" else "BRAINBOT"
            lines.append(f"[{msg.get('created_at', '')}] {role}:")
            lines.append(f"{msg['content']}\n")
            lines.append("-" * 40 + "\n")

        content = "\n".join(lines)
        buf = io.BytesIO(content.encode("utf-8"))
        buf.name = f"conversa_brainbot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        buf.seek(0)
        return buf

    @staticmethod
    def export_to_pdf(messages: list[dict], user_name: str = "Usuário") -> io.BytesIO:
        """Exporta histórico em arquivo PDF elegante usando fpdf2."""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Cabeçalho
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "BrainBot — Relatorio de Conversa", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 6, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Usuario: {user_name}", ln=True, align="C")
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        for msg in messages:
            is_user = msg["role"] == "user"
            role_label = "Voce:" if is_user else "BrainBot:"
            date_str = msg.get("created_at", "")

            # Tag do remetente
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(0, 102, 204) if is_user else pdf.set_text_color(46, 139, 87)
            pdf.cell(0, 6, f"{role_label} ({date_str})", ln=True)

            # Conteúdo da mensagem
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            # Remove caracteres incompatíveis com latin-1
            safe_text = msg["content"].encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 5, safe_text)
            pdf.ln(4)

        buf = io.BytesIO()
        pdf.output(buf)
        buf.name = f"conversa_brainbot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        buf.seek(0)
        return buf

conversation_exporter = ConversationExporter()
