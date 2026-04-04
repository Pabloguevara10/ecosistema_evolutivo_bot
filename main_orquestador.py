# =============================================================================
# NOMBRE: main_orquestador.py
# UBICACIÓN: RAÍZ DEL PROYECTO
# OBJETIVO: Orquestador Central con Salud completa, Riesgo e Interés Compuesto.
# =============================================================================

import os
import sys
import time
from datetime import datetime
from binance.client import Client
from dotenv import load_dotenv

# --- 🔑 CARGA DE CREDENCIALES DESDE .env ---
load_dotenv()
# Actualizado para que coincida con los nombres exactos en tu archivo .env
API_KEY = os.getenv("BINANCE_API_KEY_TESTNET")
API_SECRET = os.getenv("BINANCE_API_SECRET_TESTNET")

if not API_KEY or not API_SECRET:
    print("❌ Error Crítico: No se encontraron las variables BINANCE_API_KEY_TESTNET y BINANCE_API_SECRET_TESTNET en el archivo .env")
    sys.exit(1)

# --- RUTAS ESTRICTAS ---
project_root = os.path.dirname(os.path.abspath(__file__))
carpetas_deptos = [
    "dep_herramientas", 
    "dep_analisis", 
    "dep_ejecucion", 
    "dep_salud"
]
for carpeta in carpetas_deptos:
    ruta_completa = os.path.join(project_root, carpeta)
    if os.path.exists(ruta_completa):
        sys.path.append(ruta_completa)

try:
    from StructureScanner_2 import StructureScanner
    from monitor_mercado import MonitorMercado
    from comparador_estrategias import ComparadorEstrategias
    from emisor_señales import EmisorSenales
    from evaluador_entradas import EvaluadorEntradas
    from gestor_cupos import GestorCupos
    from disparador_binance import DisparadorBinance
    from asegurador_posicion import AseguradorPosicion
    # Módulos del Departamento de Salud
    from bitacora_central import BitacoraCentral
    from auditor_red import AuditorRed
    from monitor_recursos import MonitorRecursos
    from reporte_diagnostico import ReporteDiagnostico
except ImportError as e:
    print(f"❌ Error de Importación: {e}")
    sys.exit(1)

# --- ENVOLTORIOS DE CONEXIÓN ---
class SincronizadorDummy:
    def get_timestamp_corregido(self):
        return int(time.time() * 1000)

class ConexionWrapper:
    def __init__(self, api_key, api_secret, testnet=True):
        self.client = Client(api_key, api_secret, testnet=testnet)
        self.sincronizador = SincronizadorDummy()

# =============================================================================
# ORQUESTADOR CENTRAL
# =============================================================================
class OrquestadorCentral:
    def __init__(self, symbol="AAVEUSDT"):
        self.symbol = symbol
        
        # 1. 🏥 Inicializar Bitácora Primero
        self.bitacora = BitacoraCentral()
        self.bitacora.info("="*60)
        self.bitacora.info("🤖 SISTEMA SENTINEL PRO: INICIANDO SECUENCIA DE ARRANQUE")
        self.bitacora.info("="*60)
        
        # 2. Conexión
        self.conexion = ConexionWrapper(API_KEY, API_SECRET, testnet=True)
        
        # 3. 🏥 Inicializar Telemetría de Salud Completa
        self.auditor = AuditorRed(self.conexion, self.bitacora)
        self.monitor_hw = MonitorRecursos(self.bitacora)
        self.diagnostico = ReporteDiagnostico(self.monitor_hw, self.bitacora)
        
        # 4. Depto Análisis
        self.monitor = MonitorMercado(self.conexion.client)
        self.comparador = ComparadorEstrategias()
        self.emisor = EmisorSenales()
        
        # 5. Depto Ejecución + Reglas de Riesgo Institucional
        self.evaluador = EvaluadorEntradas(max_slippage_pct=0.003)
        self.gestor = GestorCupos(max_ordenes=2, distancia_minima_pct=0.015)
        self.disparador = DisparadorBinance(self.conexion)
        self.asegurador = AseguradorPosicion(self.conexion, self.disparador)

        # Riesgo por operación (5% del capital total vivo)
        self.porcentaje_riesgo = 0.05 

    def obtener_balance_real(self):
        """Consulta el balance USDT actual para aplicar el Interés Compuesto."""
        try:
            balances = self.conexion.client.futures_account_balance()
            for b in balances:
                if b['asset'] == 'USDT':
                    return float(b['balance'])
            return 0.0
        except Exception as e:
            self.bitacora.error(f"Error al consultar balance en Binance: {e}")
            return 0.0

    def configurar_entorno(self):
        leverage = self.comparador.adn['parametros']['leverage']
        try:
            self.conexion.client.futures_change_leverage(symbol=self.symbol, leverage=leverage)
            self.conexion.client.futures_change_margin_type(symbol=self.symbol, marginType='ISOLATED')
            self.bitacora.info(f"Exchange configurado: Margin ISOLATED | Apalancamiento: {leverage}x")
        except Exception:
            pass # Ignoramos si ya está configurado

    def ciclo_analisis(self):
        self.bitacora.info(f"📡 Escaneando matrices MTF para {self.symbol}...")
        adn = self.comparador.adn['parametros']
        
        df_4h = self.monitor.calcular_indicadores(self.monitor.obtener_velas(self.symbol, "4h"), adn['rsi_period_macro'])
        df_1h = self.monitor.calcular_indicadores(self.monitor.obtener_velas(self.symbol, "1h"), 14)
        df_15m = self.monitor.calcular_indicadores(self.monitor.obtener_velas(self.symbol, "15m"), adn['rsi_period_micro'])
        
        scanner = StructureScanner(df_1h)
        scanner.precompute()
        precio_actual = df_15m.iloc[-1]['close']
        ctx_fibo = scanner.get_fibonacci_context(len(df_1h) - 1)
        dist_fibo = min([abs(precio_actual - v) / precio_actual for v in ctx_fibo['fibs'].values()]) if ctx_fibo else 999

        self.bitacora.info(f"📊 4H RSI: {df_4h.iloc[-1]['rsi']:.1f} | 15m RSI: {df_15m.iloc[-1]['rsi']:.1f} | Fibo: {dist_fibo*100:.2f}%")

        signal = self.comparador.evaluar_condiciones_mtf(df_4h, df_1h, df_15m, dist_fibo)
        
        if signal:
            self.bitacora.warning(f"🚨 ALERTA ESTRUCTURAL: {signal} confirmado a ${precio_actual:.2f}.")
            paquete = self.emisor.empaquetar_entrada(self.comparador.adn['id_estrategia'], signal, precio_actual, adn)
            self.ciclo_ejecucion(paquete)
        else:
            self.bitacora.info("💤 Sin oportunidades claras. Manteniendo vigilancia...")

    def ciclo_ejecucion(self, paquete_senal):
        side = paquete_senal['side']
        precio_referencia = paquete_senal['precio_referencia']
        leverage = paquete_senal['leverage']
        
        self.bitacora.info(f"⚡ Iniciando Ejecución para orden {side}...")

        # 1. Filtro de Cupos y Distancia
        if not self.gestor.solicitar_cupo(side, precio_referencia):
            return

        # 2. Refrescar Orden Book
        precio_mercado = float(self.conexion.client.futures_symbol_ticker(symbol=self.symbol)['price'])

        # 3. Filtro Slippage
        if not self.evaluador.validar_viabilidad(paquete_senal, precio_mercado):
            return

        # 4. Lógica de Interés Compuesto
        capital_total = self.obtener_balance_real()
        if capital_total <= 0:
            self.bitacora.error("❌ No hay balance suficiente en USDT.")
            return
            
        margen_inversion = capital_total * self.porcentaje_riesgo
        poder_compra = margen_inversion * leverage
        cantidad_monedas = poder_compra / precio_mercado
        
        self.bitacora.info(f"💰 Capital: ${capital_total:.2f} | Margen 5%: ${margen_inversion:.2f} | Volumen Real: ${poder_compra:.2f}")

        # 5. Disparar al Mercado
        try:
            self.disparador.ejecutar_orden_entrada(
                symbol=self.symbol, side=side, tipo_orden="MARKET",
                cantidad=cantidad_monedas, precio=None, price_precision=2, qty_precision=1    
            )
            
            orden_id_falsa = f"ORD_{int(time.time())}"
            self.gestor.registrar_entrada(orden_id_falsa, side, precio_mercado)
            
            # 6. Asegurador
            sl_price = precio_mercado * (1 - paquete_senal['sl_pct']) if side == 'BUY' else precio_mercado * (1 + paquete_senal['sl_pct'])
            tp_price = precio_mercado * (1 + paquete_senal['tp_pct']) if side == 'BUY' else precio_mercado * (1 - paquete_senal['tp_pct'])
            side_salida = "SELL" if side == "BUY" else "BUY"
            pos_side = "LONG" if side == "BUY" else "SHORT"
            
            self.bitacora.info("🛡️ Asegurador: Colocando red de seguridad...")
            self.conexion.client.futures_create_order(symbol=self.symbol, side=side_salida, positionSide=pos_side, type="STOP_MARKET", stopPrice=round(sl_price, 2), closePosition="true")
            self.conexion.client.futures_create_order(symbol=self.symbol, side=side_salida, positionSide=pos_side, type="TAKE_PROFIT_MARKET", stopPrice=round(tp_price, 2), closePosition="true")
            
            self.bitacora.info("✅ EJECUCIÓN COMPLETADA. Interés Compuesto Aplicado.")
            
        except Exception as e:
            self.bitacora.critical(f"❌ Fallo crítico en ejecución: {e}")

    def arrancar_sistema(self):
        self.bitacora.info("="*60)
        self.bitacora.info("👑 ECOSISTEMA EVOLUTIVO: SISTEMA INSTITUCIONAL EN LÍNEA")
        self.bitacora.info("="*60)
        self.configurar_entorno()
        
        while True:
            try:
                # 🏥 1. CORTE DE CAJA DIARIO
                self.diagnostico.chequear_corte_diario()

                # 🛡️ 2. DOBLE CANDADO DE SALUD (Hardware y Red)
                salud_hw = self.monitor_hw.chequear_salud_hardware()
                if self.auditor.chequeo_salud_integral() and salud_hw['hardware_seguro']:
                    self.ciclo_analisis()
                else:
                    self.bitacora.warning("⏸️ Pausa de seguridad: Esperando estabilización de Red/Hardware...")
                
                time.sleep(60)
            except KeyboardInterrupt:
                self.bitacora.info("🛑 Deteniendo Orquestador por orden del usuario...")
                break
            except Exception as e:
                self.bitacora.error(f"❌ Error general en el hilo principal: {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = OrquestadorCentral(symbol="AAVEUSDT")
    bot.arrancar_sistema()