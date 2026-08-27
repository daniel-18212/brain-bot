"""
Safe Python Data Analysis & Matplotlib Chart Generator.
Renders high-definition graphs in-memory and returns image buffers for Telegram.
"""
import io
import logging
import re
import matplotlib
matplotlib.use("Agg")  # Backend não-gráfico sem display
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

CHART_TRIGGERS = [
    r"\b(gr[aá]fico|grafico|plot|plote|plotar|desenhe um gr[aá]fico)\b",
    r"\b(gr[aá]fico de barras|gr[aá]fico de pizza|gr[aá]fico de linha|histograma)\b",
]

class ChartGenerator:
    @staticmethod
    def is_chart_request(text: str) -> bool:
        """Verifica se a mensagem solicita a criação visual de um gráfico."""
        if not text: return False
        lower = text.lower()
        for p in CHART_TRIGGERS:
            if re.search(p, lower):
                return True
        return False

    @staticmethod
    def extract_and_run_matplotlib(code_str: str) -> io.BytesIO | None:
        """Executa código matplotlib gerado pela IA e captura a imagem PNG em buffer."""
        # Extrai código dentro de blocos ```python ... ```
        code_match = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", code_str)
        code_to_exec = code_match.group(1) if code_match else code_str

        # Bloqueia chamadas perigosas
        dangerous = ["import os", "import sys", "import subprocess", "open(", "eval(", "exec(", "shutil"]
        for d in dangerous:
            if d in code_to_exec:
                logger.warning(f"Código matplotlib bloqueado por conter termo restrito: {d}")
                return None

        try:
            plt.figure(figsize=(10, 6), dpi=150)
            plt.style.use("seaborn-v0_8-darkgrid" if "seaborn-v0_8-darkgrid" in plt.style.available else "default")
            
            # Namespace seguro
            local_ns = {"plt": plt, "io": io}
            exec(code_to_exec, {}, local_ns)

            buf = io.BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight")
            plt.close("all")
            buf.seek(0)
            return buf
        except Exception as e:
            logger.error(f"Erro ao renderizar gráfico matplotlib: {e}")
            plt.close("all")
            return None

chart_generator = ChartGenerator()
