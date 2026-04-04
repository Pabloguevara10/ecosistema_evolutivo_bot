# Módulo: monitor_posiciones.py - Pertenece a dep_control
from binance.error import ClientError

class MonitorPosiciones:
    def __init__(self, conexion_exchange):
        self.conexion = conexion_exchange
        self.client = self.conexion.client

    def obtener_posiciones_vivas(self, symbol="AAVEUSDT"):
        """Consulta la API y devuelve una lista filtrada solo con operaciones activas (>0)."""
        posiciones_vivas = []
        try:
            ts = self.conexion.sincronizador.get_timestamp_corregido()
            datos_riesgo = self.client.get_position_risk(symbol=symbol, timestamp=ts)
            
            for pos in datos_riesgo:
                cantidad = float(pos['positionAmt'])
                if cantidad != 0:
                    posiciones_vivas.append({
                        'symbol': pos['symbol'],
                        'cantidad': cantidad,
                        'entry_price': float(pos['entryPrice']),
                        'mark_price': float(pos['markPrice']),
                        'side': 'LONG' if cantidad > 0 else 'SHORT',
                        'pnl_usdt': float(pos['unRealizedProfit'])
                    })
        except ClientError as e:
            print(f"⚠️ [Monitor Posiciones] Fallo de lectura API: {e.error_message}")
            
        return posiciones_vivas

if __name__ == "__main__":
    print("Módulo Monitor de Posiciones Compilado.")