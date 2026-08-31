"""
Ferramentas de Informacoes e Controle do Sistema Windows para o JARVIS.
"""

import os
import sys
import ctypes
import datetime
import subprocess
import psutil
import socket
from typing import Dict, Any, List, Optional
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.core.logging_config import get_logger

logger = get_logger("tools.system")


@tool(
    name="get_current_time",
    description="Retorna o horario local atual formatado (horas, minutos e segundos).",
    permission_level=PermissionLevel.SAFE
)
def get_current_time() -> Dict[str, Any]:
    now = datetime.datetime.now()
    return {
        "time": now.strftime("%H:%M:%S"),
        "formatted": f"{now.hour} horas e {now.minute} minutos"
    }


@tool(
    name="get_current_date",
    description="Retorna a data atual com dia da semana, dia, mes e ano em portugues.",
    permission_level=PermissionLevel.SAFE
)
def get_current_date() -> Dict[str, Any]:
    now = datetime.datetime.now()
    dias_semana = ["Segunda-feira", "Terca-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sabado", "Domingo"]
    meses = ["Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    
    dia_sem = dias_semana[now.weekday()]
    mes_nome = meses[now.month - 1]
    
    return {
        "date": now.strftime("%d/%m/%Y"),
        "day_of_week": dia_sem,
        "day": now.day,
        "month": mes_nome,
        "year": now.year,
        "formatted": f"{dia_sem}, {now.day} de {mes_nome} de {now.year}"
    }


@tool(
    name="get_system_status",
    description="Obtem um panorama completo do computador: uso de CPU, memoria RAM, disco C:, status da bateria e tempo de atividade.",
    permission_level=PermissionLevel.SAFE
)
def get_system_status() -> Dict[str, Any]:
    cpu_percent = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\" if os.name == "nt" else "/")
    
    battery = psutil.sensors_battery()
    battery_info = None
    if battery:
        battery_info = {
            "percent": battery.percent,
            "power_plugged": battery.power_plugged
        }
        
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.datetime.now() - boot_time
    hours_uptime = int(uptime.total_seconds() // 3600)
    minutes_uptime = int((uptime.total_seconds() % 3600) // 60)

    return {
        "cpu_usage_percent": cpu_percent,
        "memory_used_gb": round(mem.used / (1024 ** 3), 2),
        "memory_total_gb": round(mem.total / (1024 ** 3), 2),
        "memory_percent": mem.percent,
        "disk_free_gb": round(disk.free / (1024 ** 3), 1),
        "disk_total_gb": round(disk.total / (1024 ** 3), 1),
        "disk_percent_used": disk.percent,
        "battery": battery_info,
        "uptime": f"{hours_uptime}h {minutes_uptime}min"
    }


@tool(
    name="get_cpu_usage",
    description="Obtem a porcentagem de uso do processador (CPU) e quantidade de nucleos.",
    permission_level=PermissionLevel.SAFE
)
def get_cpu_usage() -> Dict[str, Any]:
    percent = psutil.cpu_percent(interval=0.2)
    cores = psutil.cpu_count(logical=True)
    return {"cpu_percent": percent, "logical_cores": cores}


@tool(
    name="get_memory_usage",
    description="Obtem o consumo detalhado de memoria RAM.",
    permission_level=PermissionLevel.SAFE
)
def get_memory_usage() -> Dict[str, Any]:
    mem = psutil.virtual_memory()
    return {
        "used_gb": round(mem.used / (1024 ** 3), 2),
        "total_gb": round(mem.total / (1024 ** 3), 2),
        "available_gb": round(mem.available / (1024 ** 3), 2),
        "percent": mem.percent
    }


@tool(
    name="get_disk_usage",
    description="Obtem o espaco total, usado e disponivel de uma unidade de disco (ex: C:).",
    permission_level=PermissionLevel.SAFE
)
def get_disk_usage(drive: str = "C:") -> Dict[str, Any]:
    drive_path = drive if drive.endswith("\\") else f"{drive}\\"
    try:
        disk = psutil.disk_usage(drive_path)
        return {
            "drive": drive,
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "used_gb": round(disk.used / (1024 ** 3), 2),
            "percent": disk.percent
        }
    except Exception as e:
        return {"error": f"Nao foi possivel acessar a unidade {drive}: {e}"}


@tool(
    name="get_battery_status",
    description="Informa a porcentagem da bateria do notebook e se esta conectada a tomada.",
    permission_level=PermissionLevel.SAFE
)
def get_battery_status() -> Dict[str, Any]:
    battery = psutil.sensors_battery()
    if not battery:
        return {"has_battery": False, "message": "Nenhuma bateria detectada (computador desktop conectado na tomada)."}
    return {
        "has_battery": True,
        "percent": battery.percent,
        "power_plugged": battery.power_plugged,
        "seconds_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
    }


@tool(
    name="get_network_status",
    description="Informa o nome do computador na rede e endereco IP local.",
    permission_level=PermissionLevel.SAFE
)
def get_network_status() -> Dict[str, Any]:
    hostname = socket.gethostname()
    try:
        ip_addr = socket.gethostbyname(hostname)
    except Exception:
        ip_addr = "127.0.0.1"
    return {"hostname": hostname, "ip_address": ip_addr}


# Mapeamento de aplicativos populares para inicializacao rapida
COMMON_APPS = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "spotify": "spotify",
    "notepad": "notepad",
    "bloco de notas": "notepad",
    "calculadora": "calc",
    "calculator": "calc",
    "calc": "calc",
    "explorer": "explorer",
    "arquivos": "explorer",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "vscode": "code",
    "code": "code",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "terminal": "wt",
    "cmd": "cmd",
    "powershell": "powershell"
}


@tool(
    name="open_application",
    description="Abre um programa ou aplicativo instalado no computador (ex: Spotify, Chrome, Bloco de Notas, Calculadora, VS Code).",
    permission_level=PermissionLevel.SAFE
)
def open_application(app_name: str) -> Dict[str, Any]:
    clean_name = app_name.strip().lower()
    command = COMMON_APPS.get(clean_name, clean_name)
    
    try:
        if os.name == "nt":
            # Usa os.startfile ou subprocess seguro no Windows sem shell=True
            try:
                os.startfile(command)
                return {"status": "success", "message": f"Aplicativo '{app_name}' aberto com sucesso."}
            except Exception:
                # Tenta chamar executavel diretamente via powershell Start-Process
                subprocess.Popen(["cmd.exe", "/c", "start", "", command], shell=False)
                return {"status": "success", "message": f"Aplicativo '{app_name}' iniciado."}
        else:
            subprocess.Popen([command])
            return {"status": "success", "message": f"Aplicativo '{app_name}' iniciado."}
    except Exception as e:
        logger.error(f"Erro ao abrir aplicativo '{app_name}': {e}")
        return {"status": "error", "error": f"Nao foi possivel abrir '{app_name}': {str(e)}"}


@tool(
    name="list_running_apps",
    description="Lista os principais programas e janelas em execucao no momento.",
    permission_level=PermissionLevel.SAFE
)
def list_running_apps(limit: int = 15) -> Dict[str, Any]:
    apps = []
    seen = set()
    for proc in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            name = proc.info["name"]
            if name and name.lower().endswith(".exe") and name not in seen:
                # Filtra processos comuns de sistema para retornar os de usuario
                if name.lower() not in ("svchost.exe", "system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "lsass.exe"):
                    seen.add(name)
                    apps.append({
                        "name": name,
                        "pid": proc.info["pid"],
                        "memory_percent": round(proc.info["memory_percent"] or 0, 1)
                    })
                    if len(apps) >= limit:
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return {"running_apps": apps, "total_listed": len(apps)}


@tool(
    name="close_application",
    description="Fecha um processo ou aplicativo em execucao pelo nome (ex: spotify.exe ou spotify).",
    permission_level=PermissionLevel.SENSITIVE
)
def close_application(app_name: str) -> Dict[str, Any]:
    clean_name = app_name.strip().lower()
    if not clean_name.endswith(".exe"):
        clean_name += ".exe"

    closed_count = 0
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == clean_name:
                proc.terminate()
                closed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if closed_count > 0:
        return {"status": "success", "message": f"{closed_count} instancia(s) de '{app_name}' encerrada(s)."}
    return {"status": "not_found", "message": f"Nenhum processo em execucao encontrado com o nome '{app_name}'."}


@tool(
    name="lock_computer",
    description="Bloqueia a estacao de trabalho do Windows imediatamente (Tela de Bloqueio).",
    permission_level=PermissionLevel.SAFE
)
def lock_computer() -> Dict[str, Any]:
    try:
        if os.name == "nt":
            ctypes.windll.user32.LockWorkStation()
            return {"status": "success", "message": "Computador bloqueado com sucesso."}
        return {"status": "error", "message": "Comando suportado apenas no Windows."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@tool(
    name="restart_computer",
    description="Reinicia o computador do usuario. Requer confirmacao previa.",
    permission_level=PermissionLevel.DESTRUCTIVE
)
def restart_computer() -> Dict[str, Any]:
    try:
        if os.name == "nt":
            subprocess.run(["shutdown", "/r", "/t", "10"], check=True)
            return {"status": "success", "message": "O computador sera reiniciado em 10 segundos."}
        return {"status": "error", "message": "Operacao suportada no Windows."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@tool(
    name="shutdown_computer",
    description="Desliga o computador do usuario. Requer confirmacao previa.",
    permission_level=PermissionLevel.DESTRUCTIVE
)
def shutdown_computer() -> Dict[str, Any]:
    try:
        if os.name == "nt":
            subprocess.run(["shutdown", "/s", "/t", "15"], check=True)
            return {"status": "success", "message": "O computador sera desligado em 15 segundos."}
        return {"status": "error", "message": "Operacao suportada no Windows."}
    except Exception as e:
        return {"status": "error", "error": str(e)}
