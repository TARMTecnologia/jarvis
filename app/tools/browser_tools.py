"""
Ferramentas de Navegador e Pesquisa em Tempo Real na Internet para o JARVIS.
Utiliza DDGS e Wikipedia para obter noticias, cotacoes, fatos e respostas em tempo real.
"""

import json
import urllib.parse
import urllib.request
import webbrowser
import re
from typing import Dict, Any, List
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.core.logging_config import get_logger

logger = get_logger("tools.browser")


@tool(
    name="search_web",
    description="Realiza uma pesquisa em tempo real na internet para responder perguntas sobre fatos atuais, noticias, clima, cotacoes, jogos, programacao ou conhecimento geral.",
    permission_level=PermissionLevel.SAFE
)
def search_web(query: str) -> Dict[str, Any]:
    """Busca resultados reais e atualizados na internet."""
    clean_query = query.strip()
    if not clean_query:
        return {"status": "error", "error": "Termo de busca vazio."}

    logger.info(f"Executando pesquisa na web: '{clean_query}'")
    results = []

    # 1. Tenta DDGS (DuckDuckGo Live Search)
    try:
        from ddgs import DDGS
        ddgs = DDGS()
        raw_res = list(ddgs.text(clean_query, max_results=4))
        for r in raw_res:
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            if body:
                results.append({
                    "title": title,
                    "snippet": body,
                    "source": href
                })
    except Exception as e:
        logger.debug(f"DDGS falhou, tentando fallback: {e}")

    # 2. Se DDGS não retornou ou falhou, tenta Wikipedia Search API em Português
    if not results:
        try:
            wiki_url = f"https://pt.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote_plus(clean_query)}&format=json&utf8=1&srlimit=3"
            req = urllib.request.Request(wiki_url, headers={"User-Agent": "JarvisAssistant/1.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                wdata = json.loads(response.read().decode("utf-8"))
                search_items = wdata.get("query", {}).get("search", [])
                for item in search_items:
                    title = item.get("title", "")
                    raw_snippet = item.get("snippet", "")
                    clean_snippet = re.sub(r"<[^>]+>", "", raw_snippet).strip()
                    if clean_snippet:
                        results.append({
                            "title": title,
                            "snippet": clean_snippet,
                            "source": f"https://pt.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                        })
        except Exception as e:
            logger.debug(f"Aviso na API Wikipedia: {e}")

    # 3. Formata retorno
    if not results:
        return {
            "status": "success",
            "query": clean_query,
            "results_count": 0,
            "message": f"Nenhum resultado direto encontrado para '{clean_query}'."
        }

    return {
        "status": "success",
        "query": clean_query,
        "results_count": len(results),
        "results": results
    }


@tool(
    name="open_url",
    description="Abre uma URL ou site no navegador padrao do Windows.",
    permission_level=PermissionLevel.SAFE
)
def open_url(url: str) -> Dict[str, Any]:
    """Abre um link no navegador do usuario."""
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    try:
        webbrowser.open(clean_url)
        logger.info(f"URL aberta no navegador: {clean_url}")
        return {"status": "success", "url": clean_url, "message": f"Site aberto no navegador: {clean_url}"}
    except Exception as e:
        logger.error(f"Erro ao abrir URL '{clean_url}': {e}")
        return {"status": "error", "error": f"Nao foi possivel abrir a URL: {str(e)}"}


@tool(
    name="search_web_browser",
    description="Abre uma busca do Google diretamente em uma nova aba do navegador padrao.",
    permission_level=PermissionLevel.SAFE
)
def search_web_browser(query: str) -> Dict[str, Any]:
    """Abre uma busca no Google diretamente no navegador."""
    clean_query = query.strip()
    search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(clean_query)}"
    try:
        webbrowser.open(search_url)
        logger.info(f"Busca no Google aberta no navegador: {clean_query}")
        return {"status": "success", "query": clean_query, "message": f"Pesquisa aberta no navegador: '{clean_query}'"}
    except Exception as e:
        logger.error(f"Erro ao abrir busca no navegador: {e}")
        return {"status": "error", "error": f"Falha ao abrir navegador: {str(e)}"}
