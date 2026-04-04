# =============================================================================
# NOMBRE: bitacora_central.py
# UBICACIÓN: /7_DEPARTAMENTO_SALUD/
# OBJETIVO: Sistema de Logging institucional. Guarda el historial de operaciones y errores.
# =============================================================================

import logging
import os
from datetime import datetime

class BitacoraCentral:
    def __init__(self):
        # 1. Crear directorio de logs de forma dinámica
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        self.log_dir = os.path.join(project_root, "logs")
        os.makedirs(self.log_dir, exist_ok=True)

        # 2. Nombrar el archivo según el día actual
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        self.log_file = os.path.join(self.log_dir, f"sys_{fecha_hoy}.log")

        # 3. Configurar el Logger base
        self.logger = logging.getLogger("Sentinel_Pro")
        self.logger.setLevel(logging.DEBUG)

        # 4. Formato profesional del log (Fecha - Nivel - Mensaje)
        formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        # 5. Evitar duplicación de manejadores si la clase se instancia varias veces
        if not self.logger.handlers:
            # File Handler (Guarda en el archivo .log)
            fh = logging.FileHandler(self.log_file, encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

            # Console Handler (Imprime en la pantalla de terminal con el mismo formato)
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO) # En pantalla solo vemos INFO o superior para no saturar
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

    def info(self, mensaje: str):
        """Para eventos normales (ej. 'Escaneando mercado...', 'Orden ejecutada')."""
        self.logger.info(mensaje)

    def warning(self, mensaje: str):
        """Para eventos de riesgo (ej. 'Latencia alta', 'Slippage detectado')."""
        self.logger.warning(mensaje)

    def error(self, mensaje: str):
        """Para fallos controlados (ej. 'Binance API Timeout', 'Saldo Insuficiente')."""
        self.logger.error(mensaje)

    def critical(self, mensaje: str):
        """Para emergencias (ej. 'Caída del servidor', 'Base de datos corrupta')."""
        self.logger.critical(mensaje)