"""
Ferramentas de Navegador e Abertura de Sites para o JARVIS.
"""

import webbrowser
import urllib.parse
from typing import Dict, Any
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.core.logging_config import get_logger

logger = get_logger("tools.browser")


@tool(
    name="open_url",
    description="Abre um endereco de site (URL) no navegador padrao do usuario (ex: https://youtube.com).",
    permission_level=PermissionLevel.SAFE
)
def open_url(url: str) -> Dict[str, Any]:
    clean_url = url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        clean_url = f"https://{clean_url}"

    try:
        webbrowser.open(clean_url)
        return {"status": "success", "message": f"URL '{clean_url}' aberta no navegador."}
    except Exception as e:
        logger.error(f"Erro ao abrir URL {clean_url}: {e}")
        return {"status": "error", "error": str(e)}


@tool(
    name="search_web_browser",
    description="Pesquisa um termo ou pergunta no Google pelo navegador padrao da maquina.",
    permission_level=PermissionLevel.SAFE
)
def search_web_browser(query: str, search_engine: str = "google") -> Dict[str, Any]:
    encoded_query = urllib.parse.quote_plus(query)
    
    engines = {
        "google": f"https://www.google.com/search?q={encoded_query}",
        "bing": f"https://www.bing.com/search?q={encoded_query}",
        "duckduckgo": f"https://duckduckgo.com/?q={encoded_query}",
        "youtube": f"https://www.youtube.com/results?search_query={encoded_query}"
    }

    url = engines.get(search_engine.lower(), engines["google"])

    try:
        webbrowser.open(url)
        return {"status": "success", "message": f"Pesquisa por '{query}' aberta no {search_engine}."}
    except Exception as e:
        logger.error(f"Erro ao pesquisar {query}: {e}")
        return {"status": "error", "error": str(e)}
