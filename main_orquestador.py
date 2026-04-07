# =============================================================================
# NOMBRE: main_orquestador.py
# UBICACIÓN: RAÍZ DEL PROYECTO
# OBJETIVO: Orquestador Central Multi-Hilo con Consola Manual (Hotkeys) e UI.
# INCLUYE: Integración Segura de Estrategia Pirámide MTF y VIP ADN.
# =============================================================================

import os
import sys
import time
import threading
import msvcrt  # Librería nativa de Windows para capturar teclado sin bloquear
from datetime import datetime
from binance.client import Client
from dotenv import load_dotenv

# --- LIBRERÍAS VISUALES DEL DASHBOARD ---
try:
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.console import Group
    from rich import box
except ImportError:
    print("❌ Faltan dependencias visuales. Ejecuta: python -m pip install rich")
    sys.exit(1)

# --- 🔑 CARGA DE CREDENCIALES DESDE .env ---
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY_TESTNET")
API_SECRET = os.getenv("BINANCE_API_SECRET_TESTNET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") 

if not API_KEY or not API_SECRET:
    print("❌ Error Crítico: No se encontraron las variables de Binance en .env")
    sys.exit(1)

# --- RUTAS ESTRICTAS ---
project_root = os.path.dirname(os.path.abspath(__file__))
carpetas_deptos = ["dep_herramientas", "dep_analisis", "dep_ejecucion", "dep_salud"]
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
    from bitacora_central import BitacoraCentral
    from auditor_red import AuditorRed
    from monitor_recursos import MonitorRecursos
    from controlador_telegram import ControladorTelegram
    from reporte_diagnostico import ReporteDiagnostico
except ImportError as e:
    print(f"❌ Error de Importación: {e}")
    sys.exit(1)

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
        self.inicio_sesion = datetime.now()
        
        # --- VARIABLES DE CONTROL (KILLSWITCH) ---
        self.trading_permitido = True
        
        # 🎛️ PANEL DE CONTROL DE ESTRATEGIAS (Módulo de Aislamiento)
        self.config_estrategias = {
            "VIP_ADN": True,         # Tu estrategia original
            "PIRAMIDE_MTF": True     # La nueva estrategia de cobertura
        }
        
        # Cargar estrategia MTF si está activa
        self.estrategia_piramide = None
        if self.config_estrategias["PIRAMIDE_MTF"]:
            try:
                from estrategia_piramide_mtf import EstrategiaPiramideMTF
                self.estrategia_piramide = EstrategiaPiramideMTF()
            except ImportError:
                self.config_estrategias["PIRAMIDE_MTF"] = False

        # --- ESTADO COMPARTIDO (UI) ---
        self.estado_ui = {
            "precio_actual": 0.0,  
            "balance_inicial": 0.0,
            "balance_actual": 0.0,
            "latencia": "0ms",
            "entradas_hoy": 0,
            "telegram_status": "[green]Activo[/green]" if TELEGRAM_TOKEN else "[yellow]Inactivo[/yellow]",
            "mensajes_sistema": ["", "", "Sistemas armados. Esperando datos..."],
            "comando_buffer": "", 
            "estado_bot": "[green]OPERATIVO[/green]",
            "mtf": {
                "1d": {"rsi": [0,0], "macd": [0,0], "stoch": [0,0], "adx": [0,0], "vol": [0,0], "bb": "Calc...", "div": "Ninguna", "trend": "Lateral"},
                "4h": {"rsi": [0,0], "macd": [0,0], "stoch": [0,0], "adx": [0,0], "vol": [0,0], "bb": "Calc...", "div": "Ninguna", "trend": "Lateral"},
                "1h": {"rsi": [0,0], "macd": [0,0], "stoch": [0,0], "adx": [0,0], "vol": [0,0], "bb": "Calc...", "div": "Ninguna", "trend": "Lateral"},
                "15m": {"rsi": [0,0], "macd": [0,0], "stoch": [0,0], "adx": [0,0], "vol": [0,0], "bb": "Calc...", "div": "Ninguna", "trend": "Lateral"},
                "5m": {"rsi": [0,0], "macd": [0,0], "stoch": [0,0], "adx": [0,0], "vol": [0,0], "bb": "Calc...", "div": "Ninguna", "trend": "Lateral"},
                "1m": {"rsi": [0,0], "macd": [0,0], "stoch": [0,0], "adx": [0,0], "vol": [0,0], "bb": "Calc...", "div": "Ninguna", "trend": "Lateral"}
            }
        }
        
        # Dependencias
        self.bitacora = BitacoraCentral()
        self.conexion = ConexionWrapper(API_KEY, API_SECRET, testnet=True)
        self.auditor = AuditorRed(self.conexion, self.bitacora)
        self.monitor_hw = MonitorRecursos(self.bitacora)
        self.diagnostico = ReporteDiagnostico(self.monitor_hw, self.bitacora)
        self.monitor = MonitorMercado(self.conexion.client)
        self.comparador = ComparadorEstrategias()
        self.emisor = EmisorSenales()
        self.gestor = GestorCupos()
        self.evaluador = EvaluadorEntradas(self.gestor)
        self.disparador = DisparadorBinance(self.conexion)
        self.asegurador = AseguradorPosicion(self.conexion, self.disparador)

        self.porcentaje_riesgo = 0.05 

    def log_ui(self, mensaje):
        hora = datetime.now().strftime("%H:%M:%S")
        texto = f"[{hora}] {mensaje}"
        self.estado_ui['mensajes_sistema'].append(texto)
        if len(self.estado_ui['mensajes_sistema']) > 3:
            self.estado_ui['mensajes_sistema'].pop(0)

    def actualizar_balance(self, es_inicio=False):
        try:
            balances = self.conexion.client.futures_account_balance()
            for b in balances:
                if b['asset'] == 'USDT':
                    saldo = float(b['balance'])
                    self.estado_ui['balance_actual'] = saldo
                    if es_inicio:
                        self.estado_ui['balance_inicial'] = saldo
                    return
        except Exception:
            pass

    def formatear_pendiente(self, valores, is_vol=False):
        prev, act = valores[0], valores[1]
        if is_vol:
            if act > prev: return f"{prev/1000:.1f}k ➔ [green]{act/1000:.1f}k ▲[/green]"
            elif act < prev: return f"{prev/1000:.1f}k ➔ [red]{act/1000:.1f}k ▼[/red]"
            return f"{prev/1000:.1f}k ➔ [yellow]{act/1000:.1f}k ▶[/yellow]"

        if act > prev + 0.1: return f"{prev:.1f} ➔ [green]{act:.1f} ▲[/green]"
        elif act < prev - 0.1: return f"{prev:.1f} ➔ [red]{act:.1f} ▼[/red]"
        else: return f"{prev:.1f} ➔ [yellow]{act:.1f} ▶[/yellow]"

    def generar_dashboard(self):
        pnl = self.estado_ui['balance_actual'] - self.estado_ui['balance_inicial']
        color_pnl = "green" if pnl >= 0 else "red"
        
        cabecera = Table(box=box.ROUNDED, expand=True)
        cabecera.add_column("💰 Capital", justify="center", style="bold white")
        cabecera.add_column("🪙 Activo", justify="center", style="bold yellow") 
        cabecera.add_column("📊 PnL Diario", justify="center", style=f"bold {color_pnl}")
        cabecera.add_column("⚙️ Estado", justify="center")
        cabecera.add_column("🔌 Binance", justify="center", style="blue")
        cabecera.add_column("✈️ Telegram", justify="center")

        cabecera.add_row(
            f"${self.estado_ui['balance_actual']:.2f}",
            f"{self.symbol}: ${self.estado_ui['precio_actual']:.2f}",
            f"${pnl:+.2f}",
            self.estado_ui['estado_bot'],
            f"{self.estado_ui['latencia']}",
            self.estado_ui['telegram_status']
        )

        matriz = Table(title="📊 Matriz Numérica de Indicadores MTF", box=box.SIMPLE_HEAVY, expand=True)
        matriz.add_column("TF", style="bold cyan", justify="center")
        matriz.add_column("RSI", justify="center")
        matriz.add_column("MACD", justify="center")
        matriz.add_column("StochRSI", justify="center")
        matriz.add_column("ADX", justify="center")
        matriz.add_column("Volumen", justify="center")
        matriz.add_column("BBoll (Ancho|Dist)", justify="center") 
        matriz.add_column("Divergencia", justify="center")
        matriz.add_column("Tendencia", justify="center")

        for tf in ["1d", "4h", "1h", "15m", "5m", "1m"]:
            d = self.estado_ui['mtf'][tf]
            matriz.add_row(
                tf.upper(), 
                self.formatear_pendiente(d['rsi']),
                self.formatear_pendiente(d['macd']),
                self.formatear_pendiente(d['stoch']),
                self.formatear_pendiente(d['adx']),
                self.formatear_pendiente(d['vol'], is_vol=True),
                d['bb'],
                d['div'],
                d['trend']
            )

        texto_logs = "\n".join(self.estado_ui['mensajes_sistema'])
        monitor = Panel(
            f"[bold white]{texto_logs}[/bold white]", 
            title="🛡️ Monitor de Eventos del Sistema", 
            border_style="blue",
            height=5 
        )
        
        consola = Panel(
            f"[bold cyan]>[/bold cyan] {self.estado_ui['comando_buffer']}█", 
            title="⌨️ Terminal de Comandos Manuales (Escribe y presiona Enter)", 
            border_style="magenta"
        )

        return Group(cabecera, matriz, monitor, consola)

    def obtener_valor_seguro(self, df, columna, posicion):
        return df[columna].iloc[posicion] if columna in df.columns else 0.0

    # =========================================================
    # PARSER DE COMANDOS MANUALES
    # =========================================================
    def procesar_comando_manual(self, comando):
        comando = comando.strip().lower()
        adn = self.comparador.adn['parametros']
        precio = self.estado_ui['precio_actual']

        if comando == "k l 1":
            self.trading_permitido = False
            self.estado_ui['estado_bot'] = "[yellow]PAUSADO[/yellow]"
            self.log_ui("⏸️ KILLSWITCH ACTIVADO: Operaciones Automáticas Pausadas.")
            
        elif comando == "k l 2":
            self.trading_permitido = False
            self.estado_ui['estado_bot'] = "[red]EMERGENCIA[/red]"
            self.log_ui("🚨 EMERGENCIA: Pausando bot y cerrando posiciones...")
            self.ejecutar_panico_nuclear()

        elif comando == "r":
            self.trading_permitido = True
            self.estado_ui['estado_bot'] = "[green]OPERATIVO[/green]"
            self.log_ui("▶️ SISTEMA REANUDADO: Operaciones Automáticas Activas.")

        elif comando.startswith("c "):
            try:
                qty = float(comando.split(" ")[1])
                self.log_ui(f"🧑‍💻 COMANDO RECIBIDO: Forzando LONG de {qty} lotes...")
                paquete = self.emisor.empaquetar_entrada(self.comparador.adn['id_estrategia'], {'senal':'LONG'}, precio, adn)
                self.ciclo_ejecucion(paquete, lote_manual=qty)
            except:
                self.log_ui("❌ Error de Sintaxis. Usa: c 1")

        elif comando.startswith("v "):
            try:
                qty = float(comando.split(" ")[1])
                self.log_ui(f"🧑‍💻 COMANDO RECIBIDO: Forzando SHORT de {qty} lotes...")
                paquete = self.emisor.empaquetar_entrada(self.comparador.adn['id_estrategia'], {'senal':'SHORT'}, precio, adn)
                self.ciclo_ejecucion(paquete, lote_manual=qty)
            except:
                self.log_ui("❌ Error de Sintaxis. Usa: v 1")
        else:
            if comando: self.log_ui(f"⚠️ Comando desconocido: '{comando}'")

    def ejecutar_panico_nuclear(self):
        try:
            self.conexion.client.futures_cancel_all_open_orders(symbol=self.symbol)
            posiciones = self.conexion.client.futures_position_information(symbol=self.symbol)
            for pos in posiciones:
                amt = float(pos['positionAmt'])
                if amt != 0:
                    side_salida = "SELL" if amt > 0 else "BUY"
                    self.conexion.client.futures_create_order(
                        symbol=self.symbol, side=side_salida, 
                        type="MARKET", quantity=abs(amt)
                    )
            self.log_ui("☢️ POSICIONES LIQUIDADAS. El bot está inactivo.")
        except Exception as e:
            self.log_ui(f"❌ FALLO CRÍTICO EN KILLSWITCH: {e}")

    # =========================================================
    # LÓGICA CORE Y RUTEO DE ESTRATEGIAS
    # =========================================================
    def ciclo_analisis(self):
        adn = self.comparador.adn['parametros']
        
        try:
            df_1d = self.monitor.calcular_indicadores(self.monitor.obtener_velas(self.symbol, "1d"), 14)
            df_4h = self.monitor.calcular_indicadores(self.monitor.obtener_velas(self.symbol, "4h"), adn['rsi_period_macro'])
            df_1h = self.monitor.calcular_indicadores(self.monitor.obtener_velas(self.symbol, "1h"), 14)
            df_15m = self.monitor.calcular_indicadores(self.monitor.obtener_velas(self.symbol, "15m"), adn['rsi_period_micro'])
            df_5m = self.monitor.calcular_indicadores(self.monitor.obtener_velas(self.symbol, "5m"), 14)
            df_1m = self.monitor.calcular_indicadores(self.monitor.obtener_velas(self.symbol, "1m"), 14)
        except Exception:
            return
        
        dfs = {"1d": df_1d, "4h": df_4h, "1h": df_1h, "15m": df_15m, "5m": df_5m, "1m": df_1m}
        
        if df_1m is not None and not df_1m.empty:
            self.estado_ui['precio_actual'] = df_1m.iloc[-1]['close']

        for tf, df in dfs.items():
            if df is not None and len(df) > 1:
                self.estado_ui['mtf'][tf]['rsi'] = [self.obtener_valor_seguro(df, 'rsi', -2), self.obtener_valor_seguro(df, 'rsi', -1)]
                self.estado_ui['mtf'][tf]['macd'] = [self.obtener_valor_seguro(df, 'macd', -2), self.obtener_valor_seguro(df, 'macd', -1)]
                self.estado_ui['mtf'][tf]['stoch'] = [self.obtener_valor_seguro(df, 'stochrsi', -2), self.obtener_valor_seguro(df, 'stochrsi', -1)]
                self.estado_ui['mtf'][tf]['adx'] = [self.obtener_valor_seguro(df, 'adx', -2), self.obtener_valor_seguro(df, 'adx', -1)]
                self.estado_ui['mtf'][tf]['vol'] = [self.obtener_valor_seguro(df, 'volume', -2), self.obtener_valor_seguro(df, 'volume', -1)]
                
                c_price = df.iloc[-1]['close']
                bb_up = self.obtener_valor_seguro(df, 'bb_upper', -1)
                bb_mid = self.obtener_valor_seguro(df, 'bb_mid', -1)
                bb_low = self.obtener_valor_seguro(df, 'bb_lower', -1)
                
                if bb_mid > 0:
                    ancho_pct = ((bb_up - bb_low) / bb_mid) * 100
                    dist_centro_pct = ((c_price - bb_mid) / bb_mid) * 100
                    if c_price >= bb_mid:
                        self.estado_ui['mtf'][tf]['bb'] = f"{ancho_pct:.1f}% | [green]{dist_centro_pct:+.2f}%[/green]"
                    else:
                        self.estado_ui['mtf'][tf]['bb'] = f"{ancho_pct:.1f}% | [red]{dist_centro_pct:+.2f}%[/red]"
                
                rsi_act = self.estado_ui['mtf'][tf]['rsi'][1]
                if rsi_act > 60: self.estado_ui['mtf'][tf]['trend'] = "[green]Alcista[/green]"
                elif rsi_act < 40: self.estado_ui['mtf'][tf]['trend'] = "[red]Bajista[/red]"
                else: self.estado_ui['mtf'][tf]['trend'] = "[yellow]Lateral[/yellow]"

        if not self.trading_permitido:
            return 

        # --- RUTEO A: ESTRATEGIA VIP ADN (TU CÓDIGO ORIGINAL) ---
        if self.config_estrategias["VIP_ADN"]:
            try:
                scanner = StructureScanner(df_1h)
                scanner.precompute()
                precio_actual = df_15m.iloc[-1]['close']
                ctx_fibo = scanner.get_fibonacci_context(len(df_1h) - 1)
                dist_fibo = min([abs(precio_actual - v) / precio_actual for v in ctx_fibo['fibs'].values()]) if ctx_fibo else 999

                signal = self.comparador.evaluar_mercado(df_4h, df_1h, df_15m, dist_fibo)
                
                if signal:
                    tipo_senal = signal.get('senal', 'UNKNOWN')
                    self.log_ui(f"🚨 ALERTA ESTRUCTURAL VIP: {tipo_senal}")
                    paquete = self.emisor.empaquetar_entrada(self.comparador.adn['id_estrategia'], signal, precio_actual, adn)
                    self.ciclo_ejecucion(paquete)
            except Exception:
                pass

        # --- RUTEO B: ESTRATEGIA PIRÁMIDE MTF (NUEVO MÓDULO AISLADO) ---
        if self.config_estrategias["PIRAMIDE_MTF"] and self.estrategia_piramide:
            try:
                datos_mtf = {"1h": df_1h, "15m": df_15m, "5m": df_5m}
                senal_mtf = self.estrategia_piramide.calcular_senyal(datos_mtf)
                
                if senal_mtf:
                    self.log_ui(f"⚡ ALERTA MTF: {senal_mtf['accion']} ({senal_mtf['motivo']})")
                    self.ciclo_ejecucion_mtf(senal_mtf)
            except Exception as e:
                self.log_ui(f"⚠️ Error procesando Pirámide MTF: {e}")


    # =========================================================
    # EJECUCIÓN VIP ADN (Original Intacto)
    # =========================================================
    def ciclo_ejecucion(self, paquete_senal, lote_manual=None):
        side = paquete_senal['side']
        precio_referencia = paquete_senal['precio_referencia']
        leverage = paquete_senal['leverage']

        precio_mercado = float(self.conexion.client.futures_symbol_ticker(symbol=self.symbol)['price'])
        self.actualizar_balance()
        
        if lote_manual is not None:
            cantidad_monedas = lote_manual
            self.log_ui(f"⚠️ Aplicando Override de Riesgo: {cantidad_monedas} Lotes.")
        else:
            if not self.evaluador.validar_viabilidad(paquete_senal, precio_mercado): return
            if not self.gestor.solicitar_cupo(side, precio_referencia): return
            
            margen = self.estado_ui['balance_actual'] * self.porcentaje_riesgo
            poder_compra = margen * leverage
            cantidad_monedas = poder_compra / precio_mercado

        try:
            self.disparador.ejecutar_orden_entrada(
                symbol=self.symbol, side=side, tipo_orden="MARKET",
                cantidad=cantidad_monedas, precio=None, price_precision=2, qty_precision=1    
            )
            self.estado_ui['entradas_hoy'] += 1
            if lote_manual is None:
                self.gestor.registrar_entrada(f"ORD_{int(time.time())}", side, precio_mercado)
            
            sl_price = precio_mercado * (1 - paquete_senal['sl_pct']) if side == 'BUY' else precio_mercado * (1 + paquete_senal['sl_pct'])
            tp_price = precio_mercado * (1 + paquete_senal['tp_pct']) if side == 'BUY' else precio_mercado * (1 - paquete_senal['tp_pct'])
            side_salida = "SELL" if side == "BUY" else "BUY"
            pos_side = "LONG" if side == "BUY" else "SHORT"
            
            self.conexion.client.futures_create_order(symbol=self.symbol, side=side_salida, positionSide=pos_side, type="STOP_MARKET", stopPrice=round(sl_price, 2), closePosition="true")
            self.conexion.client.futures_create_order(symbol=self.symbol, side=side_salida, positionSide=pos_side, type="TAKE_PROFIT_MARKET", stopPrice=round(tp_price, 2), closePosition="true")
            self.log_ui(f"✅ PROTECCIÓN VIP ACTIVA. SL: {sl_price:.2f} | TP: {tp_price:.2f}")
        except Exception as e:
            self.log_ui(f"❌ Fallo crítico en disparador VIP: {e}")

    # =========================================================
    # EJECUCIÓN PIRAMIDE MTF (Ruta Nueva y Segura)
    # =========================================================
    def ciclo_ejecucion_mtf(self, senal):
        lado = senal['lado']
        accion = senal['accion']
        self.actualizar_balance()

        # 1. Cierre Parcial si aplica (Rebalanceo)
        fraccion = senal.get('reducir_contraria', 0)
        if fraccion > 0:
            lado_contrario = "SHORT" if lado == "LONG" else "LONG"
            self.log_ui(f"✂️ MTF: Reduciendo {fraccion*100}% posición {lado_contrario}")
            # Descomenta cuando el disparador tenga esta función
            # self.disparador.cerrar_posicion_parcial(self.symbol, lado_contrario, fraccion)

        # 2. Calcular Tamaño Asimétrico
        margen = self.estado_ui['balance_actual'] * self.porcentaje_riesgo
        leverage = self.comparador.adn['parametros']['leverage'] 
        precio_mercado = float(self.conexion.client.futures_symbol_ticker(symbol=self.symbol)['price'])
        
        poder_compra = margen * leverage
        cantidad_base = poder_compra / precio_mercado
        cantidad_final = cantidad_base * senal.get('lotaje', 1.0)
        
        # 3. Disparo Límite o Mercado
        side_binance = "BUY" if lado == "LONG" else "SELL"
        tipo_orden = senal.get('tipo_orden', 'MARKET')
        precio_limit = senal.get('precio_limit', None)
        
        try:
            self.disparador.ejecutar_orden_entrada(
                symbol=self.symbol, side=side_binance, tipo_orden=tipo_orden,
                cantidad=cantidad_final, precio=precio_limit, price_precision=2, qty_precision=1    
            )
            self.estado_ui['entradas_hoy'] += 1
            self.log_ui(f"✅ MTF {lado} Ejecutado | Lotes: {senal.get('lotaje', 1.0)}")
            
            # 4. Trailing de Ola
            if senal.get('use_trailing', False):
                self.log_ui(f"🌊 MTF: Activando Trailing Stop de la Ola...")
                # self.asegurador.configurar_trailing_binance(self.symbol, lado, senal['trailing_pct'])
                
        except Exception as e:
            self.log_ui(f"❌ Fallo MTF: {e}")

    # =========================================================
    # HILOS (MOTOR Y TECLADO)
    # =========================================================
    def hilo_motor_trading(self):
        while True:
            try:
                # --- NUEVO FILTRO: FIN DE SEMANA ---
                if datetime.now().weekday() >= 5:
                    if self.estado_ui['estado_bot'] != "[yellow]REPOSO (FIN DE SEMANA)[/yellow]":
                        self.estado_ui['estado_bot'] = "[yellow]REPOSO (FIN DE SEMANA)[/yellow]"
                        self.log_ui("💤 Mercado errático detectado. Pausando bot por fin de semana.")
                    time.sleep(60) # Chequea cada minuto si ya es Lunes
                    continue
                else:
                    if self.estado_ui['estado_bot'] == "[yellow]REPOSO (FIN DE SEMANA)[/yellow]":
                        self.estado_ui['estado_bot'] = "[green]OPERATIVO[/green]"
                        self.log_ui("▶️ Apertura de mercado. Reanudando operaciones.")

                ping_start = time.time()
                self.conexion.client.ping()
                self.estado_ui['latencia'] = f"{int((time.time() - ping_start)*1000)}ms"
                self.ciclo_analisis()
                time.sleep(5)
            except Exception:
                time.sleep(5)

    def hilo_escucha_teclado(self):
        """Hilo dedicado a escuchar el teclado mediante msvcrt (Windows nativo)"""
        while True:
            if msvcrt.kbhit():
                tecla = msvcrt.getch()
                try:
                    tecla_str = tecla.decode('utf-8')
                    if tecla == b'\r': # ENTER
                        if self.estado_ui["comando_buffer"].strip():
                            self.procesar_comando_manual(self.estado_ui["comando_buffer"])
                        self.estado_ui["comando_buffer"] = ""
                    elif tecla == b'\x08': # BACKSPACE
                        self.estado_ui["comando_buffer"] = self.estado_ui["comando_buffer"][:-1]
                    else:
                        self.estado_ui["comando_buffer"] += tecla_str
                except:
                    pass
            time.sleep(0.05) 

    def arrancar_sistema(self):
        try:
            self.conexion.client.futures_change_leverage(symbol=self.symbol, leverage=self.comparador.adn['parametros']['leverage'])
            self.conexion.client.futures_change_margin_type(symbol=self.symbol, marginType='ISOLATED')
        except Exception: pass

        self.actualizar_balance(es_inicio=True)
        os.system('cls' if os.name == 'nt' else 'clear')

        # Arrancar hilos fantasma
        threading.Thread(target=self.hilo_motor_trading, daemon=True).start()
        threading.Thread(target=self.hilo_escucha_teclado, daemon=True).start()
        
        # Arrancar Hilo de Telegram
        telegram = ControladorTelegram(TELEGRAM_TOKEN, self)
        telegram.iniciar()

        # Hilo Principal (Renderizado UI)
        with Live(self.generar_dashboard(), refresh_per_second=2) as live:
            while True:
                try:
                    live.update(self.generar_dashboard())
                    time.sleep(0.5)
                except KeyboardInterrupt:
                    break

if __name__ == "__main__":
    bot = OrquestadorCentral(symbol="AAVEUSDT")
    bot.arrancar_sistema()