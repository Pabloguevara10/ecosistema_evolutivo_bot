# =============================================================================
# NOMBRE: comparador_estrategias.py
# UBICACIÓN: /4_DEPARTAMENTO_ANALISIS/
# OBJETIVO: Leer el ADN (JSON) y cruzarlo contra los datos del mercado.
# =============================================================================

import json
import os

class ComparadorEstrategias:
    def __init__(self):
        # Enrutamiento dinámico hacia el Departamento 2
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        
        # Buscamos en la ruta oficial y en una ruta alternativa por si acaso
        self.ruta_db = os.path.join(project_root, "2_DEPARTAMENTO_DESARROLLO", "BBDD_Estrategias", "estrategias_aprobadas_mtf.json")
        alt_path = os.path.join(project_root, "dep_desarrollo", "bbdd_estrategias", "estrategias_aprobadas_mtf.json")
        
        if os.path.exists(alt_path) and not os.path.exists(self.ruta_db):
            self.ruta_db = alt_path
            
        self.adn = self._cargar_adn_vigente()

    def _cargar_adn_vigente(self):
        if not os.path.exists(self.ruta_db):
            raise FileNotFoundError(f"❌ Base de datos de estrategias no encontrada en: {self.ruta_db}")
        
        with open(self.ruta_db, 'r') as file:
            estrategias = json.load(file)
            
        mejor_estrategia = estrategias[-1]  # Toma la última mutación aprobada
        print(f"🧬 [Comparador] Estrategia Activa: {mejor_estrategia['id_estrategia']}")
        return mejor_estrategia

    def evaluar_condiciones_mtf(self, df_4h, df_1h, df_15m, dist_fibo):
        """Lógica estricta de Cascada 4H -> 1H -> 15m basada en el ADN genético."""
        parametros = self.adn['parametros']
        
        rsi_4h = df_4h.iloc[-1]['rsi']
        rsi_15m = df_15m.iloc[-1]['rsi']
        rsi_15m_prev = df_15m.iloc[-2]['rsi']
        macd_1h = df_1h.iloc[-1]['macd_hist']
        obv_slope_1h = df_1h.iloc[-1]['obv_slope']

        # Evaluación Estricta LONG (COMPRA)
        if rsi_4h < parametros['rsi_os_macro']:
            if rsi_15m < parametros['rsi_os_micro'] and (rsi_15m - rsi_15m_prev) > 2:
                if dist_fibo < parametros['fibo_max_dist'] and macd_1h > 0 and obv_slope_1h > -500:
                    return "BUY"

        # Evaluación Estricta SHORT (VENTA)
        elif rsi_4h > parametros['rsi_ob_macro']:
            if rsi_15m > parametros['rsi_ob_micro'] and (rsi_15m - rsi_15m_prev) < -2:
                if dist_fibo < parametros['fibo_max_dist'] and macd_1h < 0 and obv_slope_1h < 500:
                    return "SELL"

        return None