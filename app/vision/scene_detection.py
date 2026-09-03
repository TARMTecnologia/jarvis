"""
Detector e Analisador de Cena e Presenca Humana em Tempo Real para os Olhos do JARVIS.
Detecta presenca de pessoas na frente da camera, contagem de individuos, silhueta facial,
iluminacao, movimento e correspondencia com o mentor cadastrado.
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from app.core.logging_config import get_logger

logger = get_logger("vision.scene_detection")

MENTOR_FACE_PATH = Path("data") / "mentor_face_reference.jpg"


class SceneDetector:
    """Analisador de visao computacional em tempo real para os olhos do JARVIS."""

    def __init__(self):
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=20, detectShadows=False)
        self._last_analysis_time: float = 0.0
        self._last_telemetry: Dict[str, Any] = {
            "is_person_present": False,
            "people_count": 0,
            "has_mentor_match": False,
            "mentor_confidence": 0.0,
            "lighting": "Normal",
            "motion_detected": False,
            "summary": "Nenhuma pessoa detectada"
        }

    def analyze_frame(self, frame: Optional[np.ndarray]) -> Dict[str, Any]:
        """
        Executa analise visual em tempo real no frame da camera.
        Identifica presenca de pessoas, silhueta, iluminacao e movimento.
        """
        if frame is None or frame.size == 0:
            return self._last_telemetry

        try:
            h, w = frame.shape[:2]

            # 1. Analise de Iluminacao e Brilho Medio
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_brightness = float(np.mean(gray))
            if mean_brightness < 40:
                lighting_desc = "Ambiente escuro / Pouca luz"
            elif mean_brightness > 210:
                lighting_desc = "Ambiente com excesso de luz / Alta luminosidade"
            else:
                lighting_desc = "Boa iluminação"

            # 2. Deteccao de Movimento / Primeiro Plano
            fg_mask = self._bg_subtractor.apply(frame)
            motion_ratio = float(np.sum(fg_mask > 128) / (h * w))
            motion_detected = motion_ratio > 0.02

            # 3. Deteccao de Tons de Pele e Silhueta Humana (HSV + YCrCb combinados)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)

            # Faixa HSV para tons de pele
            lower_hsv = np.array([0, 20, 60], dtype=np.uint8)
            upper_hsv = np.array([25, 255, 255], dtype=np.uint8)
            mask_hsv = cv2.inRange(hsv, lower_hsv, upper_hsv)

            # Faixa YCrCb para tons de pele universais
            lower_ycrcb = np.array([0, 133, 77], dtype=np.uint8)
            upper_ycrcb = np.array([255, 173, 127], dtype=np.uint8)
            mask_ycrcb = cv2.inRange(ycrcb, lower_ycrcb, upper_ycrcb)

            skin_mask = cv2.bitwise_and(mask_hsv, mask_ycrcb)
            # Foco na regiao central superior (onde fica o rosto/busto diante da webcam)
            center_h_start = int(h * 0.1)
            center_h_end = int(h * 0.85)
            center_w_start = int(w * 0.15)
            center_w_end = int(w * 0.85)

            roi_skin = skin_mask[center_h_start:center_h_end, center_w_start:center_w_end]
            skin_pixel_ratio = float(np.count_nonzero(roi_skin) / (roi_skin.shape[0] * roi_skin.shape[1]))

            # 4. Extracao de Contornos e Deteccao de Pessoas
            contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            person_blobs = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 1200:  # Mancha compativel com rosto ou tronco humano
                    x, y, cw, ch = cv2.boundingRect(cnt)
                    aspect = ch / max(1, cw)
                    if 0.6 <= aspect <= 3.5:
                        person_blobs.append((x, y, cw, ch))

            # Deteccao de presenca positiva
            is_person_present = (skin_pixel_ratio > 0.025) or (len(person_blobs) > 0) or (mean_brightness > 45 and motion_ratio > 0.015)
            people_count = max(1 if is_person_present else 0, min(3, len(person_blobs)))

            # 5. Comparacao com Foto de Referencia do Mentor (se cadastrado)
            has_mentor_match = False
            mentor_confidence = 0.0

            if is_person_present and MENTOR_FACE_PATH.exists():
                try:
                    ref_img = cv2.imread(str(MENTOR_FACE_PATH))
                    if ref_img is not None:
                        ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
                        hist_ref = cv2.calcHist([ref_gray], [0], None, [64], [0, 256])
                        hist_cur = cv2.calcHist([gray], [0], None, [64], [0, 256])
                        cv2.normalize(hist_ref, hist_ref, 0, 1, cv2.NORM_MINMAX)
                        cv2.normalize(hist_cur, hist_cur, 0, 1, cv2.NORM_MINMAX)
                        corr = float(cv2.compareHist(hist_ref, hist_cur, cv2.HISTCMP_CORREL))
                        mentor_confidence = max(0.0, min(1.0, (corr + 1.0) / 2.0))
                        if mentor_confidence > 0.60:
                            has_mentor_match = True
                except Exception as e:
                    logger.debug(f"Erro na comparacao de referencia do mentor: {e}")

            if is_person_present:
                if has_mentor_match:
                    summary = f"{people_count} pessoa(s) detectada(s) diante da câmera. Correspondência com mentor: {mentor_confidence*100:.0f}%."
                else:
                    summary = f"{people_count} pessoa(s) detectada(s) em frente à webcam."
            else:
                summary = "Câmera ativa. Nenhuma pessoa na frente no momento."

            self._last_telemetry = {
                "is_person_present": is_person_present,
                "people_count": people_count,
                "has_mentor_match": has_mentor_match,
                "mentor_confidence": mentor_confidence,
                "lighting": lighting_desc,
                "motion_detected": motion_detected,
                "person_blobs": person_blobs,
                "summary": summary
            }

            return self._last_telemetry

        except Exception as e:
            logger.error(f"Erro no processamento da cena: {e}")
            return self._last_telemetry

    def reset(self) -> None:
        """Reinicia o historico de analise de cena."""
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=20, detectShadows=False)


scene_detector = SceneDetector()
