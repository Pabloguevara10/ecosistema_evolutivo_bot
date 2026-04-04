# =============================================================================
# NOMBRE: monitor_mercado.py
# UBICACIÓN: /4_DEPARTAMENTO_ANALISIS/
# OBJETIVO: Extraer datos en vivo de Binance y calcular los indicadores.
# =============================================================================

import pandas as pd
import numpy as np

class MonitorMercado:
    def __init__(self, binance_client):
        self.client = binance_client

    def obtener_velas(self, symbol, intervalo, limite=100):
        """Descarga las velas crudas desde Binance Futures."""
        klines = self.client.futures_klines(symbol=symbol, interval=intervalo, limit=limite)
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].astype(float)
        return df

    def calcular_indicadores(self, df, rsi_period):
        """Aplica la matemática estricta necesaria para la estrategia MTF."""
        df = df.copy()
        
        # 1. RSI Clásico
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # 2. MACD Histogram
        k_fast = df['close'].ewm(span=12, adjust=False).mean()
        k_slow = df['close'].ewm(span=26, adjust=False).mean()
        macd_line = k_fast - k_slow
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        df['macd_hist'] = macd_line - macd_signal

        # 3. OBV & OBV Slope
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        df['obv_slope'] = df['obv'].diff(3).fillna(0)
        
        return df.dropna()