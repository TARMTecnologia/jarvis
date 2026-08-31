"""
Ferramentas de Gerenciamento e Localizacao de Arquivos Locais para o JARVIS.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.core.logging_config import get_logger

logger = get_logger("tools.files")


@tool(
    name="find_file",
    description="Localiza arquivos pelo nome nas pastas do usuario (Documentos, Desktop, Downloads) ou em um diretorio especifico.",
    permission_level=PermissionLevel.SAFE
)
def find_file(filename: str, search_directory: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
    target_name = filename.strip().lower()
    
    search_dirs = []
    if search_directory and os.path.exists(search_directory):
        search_dirs.append(Path(search_directory))
    else:
        user_home = Path.home()
        search_dirs = [
            user_home / "Desktop",
            user_home / "Documents",
            user_home / "Downloads"
        ]

    found_files = []

    for base_dir in search_dirs:
        if not base_dir.exists():
            continue
        try:
            for root, dirs, files in os.walk(base_dir):
                depth = len(Path(root).relative_to(base_dir).parts)
                if depth > 4:
                    dirs.clear()
                    continue

                for f in files:
                    if target_name in f.lower():
                        full_p = Path(root) / f
                        try:
                            size_mb = round(full_p.stat().st_size / (1024 * 1024), 2)
                        except Exception:
                            size_mb = 0.0

                        found_files.append({
                            "name": f,
                            "path": str(full_p),
                            "size_mb": size_mb
                        })
                        if len(found_files) >= max_results:
                            break
                if len(found_files) >= max_results:
                    break
        except Exception as e:
            logger.debug(f"Erro ao escanear {base_dir}: {e}")

    return {
        "query": filename,
        "results_count": len(found_files),
        "files": found_files
    }


@tool(
    name="list_directory",
    description="Lista o conteudo de uma pasta do computador com nomes, tipos e tamanhos.",
    permission_level=PermissionLevel.SAFE
)
def list_directory(path: Optional[str] = None) -> Dict[str, Any]:
    target_path = Path(path) if path else Path.home() / "Desktop"
    if not target_path.exists() or not target_path.is_dir():
        return {"error": f"O caminho '{target_path}' nao existe ou nao e uma pasta."}

    items = []
    try:
        for entry in target_path.iterdir():
            try:
                is_dir = entry.is_dir()
                size_kb = round(entry.stat().st_size / 1024, 1) if not is_dir else None
                items.append({
                    "name": entry.name,
                    "type": "folder" if is_dir else "file",
                    "size_kb": size_kb
                })
            except Exception:
                pass
    except Exception as e:
        return {"error": f"Erro ao ler diretorio: {e}"}

    return {
        "path": str(target_path),
        "total_items": len(items),
        "items": items[:30]
    }


@tool(
    name="open_file",
    description="Abre um arquivo local com o programa padrao associado no Windows (ex: documento, pdf, imagem, pasta).",
    permission_level=PermissionLevel.SAFE
)
def open_file(filepath: str) -> Dict[str, Any]:
    clean_path = filepath.strip()
    if not os.path.exists(clean_path):
        return {"status": "error", "error": f"O arquivo '{clean_path}' nao foi encontrado no disco."}

    try:
        if os.name == "nt":
            os.startfile(clean_path)
            return {"status": "success", "message": f"Arquivo '{clean_path}' aberto com sucesso."}
        return {"status": "error", "error": "Suportado no Windows."}
    except Exception as e:
        logger.error(f"Erro ao abrir arquivo {clean_path}: {e}")
        return {"status": "error", "error": str(e)}


@tool(
    name="create_folder",
    description="Cria uma nova pasta no caminho especificado.",
    permission_level=PermissionLevel.SENSITIVE
)
def create_folder(folder_path: str) -> Dict[str, Any]:
    target = Path(folder_path)
    try:
        target.mkdir(parents=True, exist_ok=True)
        return {"status": "success", "message": f"Pasta criada com sucesso em: {target}"}
    except Exception as e:
        logger.error(f"Erro ao criar pasta {folder_path}: {e}")
        return {"status": "error", "error": str(e)}
