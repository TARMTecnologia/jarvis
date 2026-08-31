"""
Testes Unitarios para o Subsistema de Memoria do JARVIS.
"""

import pytest
from app.memory.long_term import long_term_memory
from app.memory.models import MemoryType
from app.memory.retrieval import semantic_retrieval
from app.memory.summarizer import memory_summarizer


def test_add_and_retrieve_memory():
    # Limpa antes
    long_term_memory.delete_all_memories()

    # Adiciona memoria
    mem = long_term_memory.add_memory(
        text="Meu carro é um Corolla prata",
        memory_type=MemoryType.FACT,
        importance=4,
        tags=["veiculo", "carro"]
    )
    assert mem.id is not None
    assert mem.text == "Meu carro é um Corolla prata"

    # Busca Semantica
    results = semantic_retrieval.retrieve(query="qual é o meu carro?", top_k=3, similarity_threshold=0.2)
    assert len(results) >= 1
    found_mem, score = results[0]
    assert "Corolla" in found_mem.text


def test_explicit_remember_and_forget_commands():
    # Comando Lembre
    action, reply = memory_summarizer.process_explicit_memory_command("Jarvis, lembre que meu nome é Thiago")
    assert action == "remembered"
    assert "Thiago" in reply

    # Verifica se foi gravado
    mems = long_term_memory.list_memories(search_query="Thiago")
    assert len(mems) >= 1

    # Comando Esqueca
    action, reply = memory_summarizer.process_explicit_memory_command("Jarvis, esqueça que meu nome é Thiago")
    assert action == "forgot"

    # Verifica se foi apagado
    mems_after = long_term_memory.list_memories(search_query="Thiago")
    assert len(mems_after) == 0
