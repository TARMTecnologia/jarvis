"""
Ferramentas de Navegador e Pesquisa na Internet para o JARVIS.
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
    description="Realiza uma pesquisa em tempo real na internet para responder perguntas sobre fatos atuais, noticias, clima, cotacoes ou conhecimento geral.",
    permission_level=PermissionLevel.SAFE
)
def search_web(query: str) -> Dict[str, Any]:
    """Busca resultados reais e resumos da internet via DuckDuckGo / Wikipedia."""
    clean_query = query.strip()
    if not clean_query:
        return {"status": "error", "error": "Termo de busca vazio."}

    logger.info(f"Executando pesquisa na web: '{clean_query}'")
    results = []

    # 1. Tenta DuckDuckGo Instant Answer API
    try:
        api_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote_plus(clean_query)}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            abstract = data.get("AbstractText", "")
            if abstract:
                results.append({"title": data.get("Heading", "Resumo"), "snippet": abstract, "source": data.get("AbstractURL", "")})

            # Tópicos relacionados
            for topic in data.get("RelatedTopics", [])[:3]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append({"title": "Tópico Relacionado", "snippet": topic["Text"], "source": topic.get("FirstURL", "")})
    except Exception as e:
        logger.debug(f"Aviso na API DuckDuckGo: {e}")

    # 2. Tenta Wikipedia Search API em Português
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
                        "title": f"Wikipédia: {title}",
                        "snippet": clean_snippet,
                        "url": f"https://pt.wikipedia.org/wiki/{urllib.parse.quote(title)}"
                    })
    except Exception as e:
        logger.debug(f"Aviso na API Wikipedia: {e}")

    if results:
        return {
            "status": "success",
            "query": clean_query,
            "results_count": len(results),
            "results": results
        }

    # Se ambas as APIs rápidas não trouxerem texto suficiente, retorna link de busca
    return {
        "status": "success",
        "query": clean_query,
        "results_count": 1,
        "results": [{
            "title": f"Busca Web por {clean_query}",
            "snippet": f"Informações atualizadas sobre '{clean_query}'.",
            "url": f"https://www.google.com/search?q={urllib.parse.quote_plus(clean_query)}"
        }]
    }


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
    description="Abre o navegador padrao da maquina com a pagina de pesquisa do Google ou Bing.",
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
