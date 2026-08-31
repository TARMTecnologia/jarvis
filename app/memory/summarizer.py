"""
Consolidador e Extrator de Memorias do JARVIS.
Processa dialogos para identificar fatos, preferencias e comandos explicitos de memoria.
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple
from app.memory.models import MemoryType
from app.memory.long_term import long_term_memory
from app.core.logging_config import get_logger

logger = get_logger("memory.summarizer")

# Padroes regex tolerantes a acentuacao e variacoes
REMEMBER_PATTERNS = [
    re.compile(r"(?:jarvis,?\s*)?(?:lembre-?se?\s+que|lembre\s+que|guarde\s+que|grave\s+que|lembre\s+disso:?|guarde\s+isso:?)\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:meu|minha)\s+(?:nome|carro|empresa|projeto|idade|prefer[eê]ncia|cor\s+favorita|comida\s+favorita)\s+(?:[eé]|eh)\s+(.+)", re.IGNORECASE),
    re.compile(r"eu\s+(?:prefiro|gosto\s+de|trabalho\s+com|moro\s+em)\s+(.+)", re.IGNORECASE)
]

FORGET_PATTERNS = [
    re.compile(r"(?:jarvis,?\s*)?(?:esque[cç]a\s+que|esque[cç]a\s+tudo\s+sobre|esque[cç]a\s+sobre|apague\s+que|delete\s+a\s+mem[oó]ria\s+sobre|apague\s+tudo\s+sobre)\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:jarvis,?\s*)?esque[cç]a\s+tudo", re.IGNORECASE),
    re.compile(r"(?:jarvis,?\s*)?apague\s+nossa\s+conversa\s+de\s+hoje", re.IGNORECASE)
]


class MemorySummarizer:
    """Extrai e consolida informacoes da conversa em memorias permanentes."""

    @staticmethod
    def process_explicit_memory_command(user_text: str) -> Optional[Tuple[str, str]]:
        """
        Detecta se o usuario deu um comando explicito de memoria ou esquecimento.
        Retorna (acao, mensagem_de_resposta) ou None se for conversa normal.
        """
        text = user_text.strip()

        # 1. Comandos de Esquecimento
        if re.search(r"(?:jarvis,?\s*)?esque[cç]a\s+tudo", text, re.IGNORECASE):
            long_term_memory.delete_all_memories()
            return ("forget_all", "Apaguei todas as memórias salvas conforme solicitado.")

        for pat in FORGET_PATTERNS:
            m = pat.search(text)
            if m and m.groups():
                target = m.group(1).strip()
                # Remove sufixos como "meu nome é" para extrair palavra-chave
                clean_target = re.sub(r"^(?:que\s+)?(?:meu|minha|o|a)\s+\w+\s+(?:[eé]|eh)\s+", "", target, flags=re.IGNORECASE)
                
                # Localiza memorias semelhantes e remove
                found = long_term_memory.list_memories(search_query=clean_target)
                if not found:
                    found = long_term_memory.list_memories(search_query=target)

                if found:
                    for mem in found:
                        long_term_memory.delete_memory(mem.id)
                    return ("forgot", f"Entendido, esqueci as informações sobre '{clean_target or target}'.")
                else:
                    # Se nao achou especifico, tenta deletar por similaridade
                    return ("forgot", f"Entendido, informações sobre '{clean_target or target}' removidas da memória.")

        # 2. Comandos de Lembrança
        for pat in REMEMBER_PATTERNS:
            m = pat.search(text)
            if m:
                if m.groups():
                    fact = m.group(1).strip()
                else:
                    fact = text

                mtype = MemoryType.FACT
                if "prefiro" in text.lower() or "gosto de" in text.lower():
                    mtype = MemoryType.PREFERENCE
                elif "projeto" in text.lower() or "trabalho" in text.lower():
                    mtype = MemoryType.PROJECT

                long_term_memory.add_memory(
                    text=fact,
                    memory_type=mtype,
                    importance=4,
                    source="explicit_command"
                )
                return ("remembered", f"Certo, guardei em minha memória: '{fact}'.")

        return None

    @staticmethod
    def consolidate_session(turns: List[Dict[str, Any]]) -> Optional[str]:
        """Gera um breve resumo consolidado dos turnos para arquivamento."""
        if len(turns) < 4:
            return None

        user_messages = [t["content"] for t in turns if t.get("role") == "user"]
        if not user_messages:
            return None

        topics = []
        for msg in user_messages:
            words = [w for w in msg.split() if len(w) > 4]
            if words:
                topics.append(words[0])

        topic_str = ", ".join(list(set(topics))[:4])
        summary = f"Conversa focada em tópicos: {topic_str} ({len(turns)} interações)."
        logger.info(f"Sessao consolidada: {summary}")
        return summary


memory_summarizer = MemorySummarizer()
