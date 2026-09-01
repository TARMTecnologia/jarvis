"""
Ferramentas de Meteorologia e Previsao do Tempo para o JARVIS.
Utiliza a API pública global Open-Meteo (100% gratuita, sem necessidade de API key).
"""

import json
import urllib.parse
import urllib.request
from typing import Dict, Any
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.core.logging_config import get_logger

logger = get_logger("tools.weather")

WEATHER_CODE_DESCRIPTIONS = {
    0: "Céu limpo e ensolarado",
    1: "Predominantemente limpo",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Neblina",
    48: "Nevoeiro com geada",
    51: "Garoa leve",
    53: "Garoa moderada",
    55: "Garoa densa",
    61: "Chuva fraca",
    63: "Chuva moderada",
    65: "Chuva forte",
    71: "Neve fraca",
    73: "Neve moderada",
    75: "Neve intensa",
    80: "Pancadas de chuva leves",
    81: "Pancadas de chuva moderadas",
    82: "Pancadas de chuva violentas",
    95: "Tempestade com trovoadas",
    96: "Tempestade com granizo leve",
    99: "Tempestade com granizo pesado"
}


@tool(
    name="get_weather",
    description="Obtém a previsão do tempo e clima atual em tempo real para qualquer cidade ou localidade (temperatura, umidade, vento, condições).",
    permission_level=PermissionLevel.SAFE
)
def get_weather(city: str = "São Paulo") -> Dict[str, Any]:
    """Consulta dados meteorológicos em tempo real."""
    clean_city = city.strip() or "São Paulo"
    logger.info(f"Consultando clima para: '{clean_city}'")

    try:
        # 1. Geocodificação da cidade
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(clean_city)}&count=1&language=pt&format=json"
        req_geo = urllib.request.Request(geo_url, headers={"User-Agent": "JarvisWeather/1.0"})
        with urllib.request.urlopen(req_geo, timeout=6) as res_geo:
            geo_data = json.loads(res_geo.read().decode("utf-8"))
            results = geo_data.get("results", [])
            if not results:
                return {"status": "error", "error": f"Localidade '{clean_city}' não encontrada."}

            loc = results[0]
            lat = loc["latitude"]
            lon = loc["longitude"]
            loc_name = loc.get("name", clean_city)
            country = loc.get("country", "")
            admin = loc.get("admin1", "")

        # 2. Dados Meteorológicos Atuais
        w_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
            "&timezone=auto"
        )
        req_w = urllib.request.Request(w_url, headers={"User-Agent": "JarvisWeather/1.0"})
        with urllib.request.urlopen(req_w, timeout=6) as res_w:
            w_data = json.loads(res_w.read().decode("utf-8"))
            current = w_data.get("current", {})

            temp = current.get("temperature_2m")
            feels_like = current.get("apparent_temperature")
            humidity = current.get("relative_humidity_2m")
            wind = current.get("wind_speed_10m")
            code = current.get("weather_code", 0)
            condition = WEATHER_CODE_DESCRIPTIONS.get(code, "Tempo instável")

            formatted_location = f"{loc_name}" + (f", {admin}" if admin else "") + (f" - {country}" if country else "")

            return {
                "status": "success",
                "location": formatted_location,
                "temperature": f"{temp}°C",
                "feels_like": f"{feels_like}°C",
                "humidity": f"{humidity}%",
                "wind_speed": f"{wind} km/h",
                "condition": condition,
                "summary": f"Em {formatted_location} faz {temp}°C (sensação térmica de {feels_like}°C) com {condition}, umidade em {humidity}% e vento a {wind} km/h."
            }

    except Exception as e:
        logger.error(f"Erro ao consultar clima: {e}")
        return {"status": "error", "error": f"Não foi possível obter dados meteorológicos: {str(e)}"}
