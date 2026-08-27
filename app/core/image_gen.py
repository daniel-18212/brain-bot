"""
High-Definition Image Generation Engine (Flux.1 / Pollinations API).
"""
import urllib.parse

class ImageGenerator:
    @staticmethod
    def get_image_url(prompt: str, width: int = 1024, height: int = 1024, model: str = "flux") -> str:
        """Gera URL direta para renderização de imagem de alta definição com Flux.1."""
        prompt_encoded = urllib.parse.quote(prompt)
        return (
            f"https://image.pollinations.ai/prompt/{prompt_encoded}"
            f"?model={model}&width={width}&height={height}&nologo=true&enhance=true"
        )

image_generator = ImageGenerator()
