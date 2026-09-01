"""
Consolidador e Extrator de Memorias do JARVIS.
Processa dialogos para identificar o nome do mentor, fatos, preferencias e comandos explicitos de memoria.
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple
from app.memory.models import MemoryType
from app.memory.long_term import long_term_memory
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("memory.summarizer")

FORGET_PATTERNS = [
    re.compile(r"(?:jarvis,?\s*)?(?:esque[cç]a\s+que|esque[cç]a\s+tudo\s+sobre|esque[cç]a\s+sobre|apague\s+que|delete\s+a\s+mem[oó]ria\s+sobre|apague\s+tudo\s+sobre)\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:jarvis,?\s*)?esque[cç]a\s+tudo", re.IGNORECASE),
    re.compile(r"(?:jarvis,?\s*)?apague\s+nossa\s+conversa\s+de\s+hoje", re.IGNORECASE)
]

NAME_PATTERNS = [
    re.compile(r"(?:jarvis,?\s*)?(?:meu nome [eé]|me chamo|sou o|sou a|pode me chamar de)\s+([A-Za-zÀ-ÖØ-öø-ÿ]{2,30})", re.IGNORECASE),
    re.compile(r"(?:jarvis,?\s*)?(?:lembre-?se?\s+que\s+)?meu nome [eé]\s+([A-Za-zÀ-ÖØ-öø-ÿ]{2,30})", re.IGNORECASE)
]

REMEMBER_PATTERNS = [
    re.compile(r"(?:jarvis,?\s*)?(?:salve|guarde|grave|armazene)\s+(?:isso\s+)?(?:na\s+(?:sua\s+)?mem[oó]ria:?|para\s+sempre:?)\s*(.*)", re.IGNORECASE),
    re.compile(r"(?:jarvis,?\s*)?(?:salve|guarde|grave|memorize)\s+que\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:jarvis,?\s*)?(?:lembre-?se?\s+que|lembre\s+que|guarde\s+que|grave\s+que|lembre\s+disso:?|guarde\s+isso:?)\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:meu|minha)\s+(?:carro|empresa|projeto|idade|profiss[aã]o|prefer[eê]ncia|cor\s+favorita|comida\s+favorita)\s+(?:[eé]|eh)\s+(.+)", re.IGNORECASE),
    re.compile(r"eu\s+(?:prefiro|gosto\s+de|trabalho\s+com|moro\s+em|sou)\s+(.+)", re.IGNORECASE)
]


class MemorySummarizer:
    """Extrai e consolida informacoes da conversa em memorias permanentes."""

    @staticmethod
    def process_explicit_memory_command(user_text: str) -> Optional[Tuple[str, str]]:
        """
        Detecta se o usuario informou seu nome ou deu um comando de memoria.
        Retorna (acao, mensagem_de_resposta) ou None se for conversa normal.
        """
        text = user_text.strip()

        # 1. Comandos de Esquecimento
        if re.search(r"(?:jarvis,?\s*)?esque[cç]a\s+tudo", text, re.IGNORECASE):
            long_term_memory.delete_all_memories()
            app_config.system.user_name = "Senhor"
            app_config.save()
            return ("forget_all", "Apaguei todas as memórias salvas conforme solicitado.")

        for pat in FORGET_PATTERNS:
            m = pat.search(text)
            if m and m.groups():
                target = m.group(1).strip()
                clean_target = re.sub(r"^(?:que\s+)?(?:meu|minha|o|a)\s+\w+\s+(?:[eé]|eh)\s+", "", target, flags=re.IGNORECASE)
                
                if "nome" in target.lower():
                    app_config.system.user_name = "Senhor"
                    app_config.save()

                found = long_term_memory.list_memories(search_query=clean_target)
                if not found:
                    found = long_term_memory.list_memories(search_query=target)

                if found:
                    for mem in found:
                        long_term_memory.delete_memory(mem.id)
                    return ("forgot", f"Entendido, esqueci as informações sobre '{clean_target or target}'.")
                else:
                    return ("forgot", f"Entendido, informações sobre '{clean_target or target}' removidas da memória.")

        # 2. Deteccao do Nome do Mentor
        for npat in NAME_PATTERNS:
            nm = npat.search(text)
            if nm and nm.groups():
                raw_name = nm.group(1).strip()
                if raw_name.lower() not in ("jarvis", "ajuda", "falar", "isso", "aqui", "agora", "hoje"):
                    clean_name = raw_name.title()
                    app_config.system.user_name = clean_name
                    app_config.save()
                    
                    long_term_memory.add_memory(
                        text=f"O nome do meu mentor e usuário é {clean_name}.",
                        memory_type=MemoryType.FACT,
                        importance=5,
                        source="name_registration"
                    )
                    logger.info(f"Nome do mentor memorizado com sucesso: {clean_name}")
                    return ("name_registered", f"Entendido, é uma honra, {clean_name}. Já registrei seu nome permanentemente em minha memória principal.")

        # 3. Comandos de Memorização e Lembrança
        for pat in REMEMBER_PATTERNS:
            m = pat.search(text)
            if m:
                if m.groups():
                    fact = m.group(1).strip()
                else:
                    fact = text

                if not fact:
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
                user_title = app_config.system.user_name if app_config.system.user_name != "Usuário" else "Senhor"
                return ("remembered", f"Certo {user_title}, guardei permanentemente em minha memória: '{fact}'.")

        return None


memory_summarizer = MemorySummarizer()
