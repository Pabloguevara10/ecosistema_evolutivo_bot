# =============================================================================
# NOMBRE: gestor_cupos.py
# UBICACIÓN: /5_DEPARTAMENTO_EJECUCION/
# OBJETIVO: Administrar exposición, lotes máximos y promediado inteligente.
# =============================================================================

class GestorCupos:
    def __init__(self, max_ordenes=2, distancia_minima_pct=0.015):
        # Límite estricto de exposición total
        self.max_ordenes = max_ordenes
        # Distancia porcentual obligatoria para permitir un segundo disparo (Ej: 1.5%)
        self.distancia_minima = distancia_minima_pct
        self.posiciones_activas = [] 
        # Formato de tracking: [{'id': '123', 'side': 'LONG', 'entry_price': 100.0}]

    def solicitar_cupo(self, side: str, precio_propuesto: float) -> bool:
        """
        Evalúa si la nueva señal tiene permiso para ser ejecutada basándose
        en el riesgo global de la cuenta.
        """
        # 1. Filtro de Capacidad Máxima Global
        if len(self.posiciones_activas) >= self.max_ordenes:
            print(f"🛑 [GESTOR CUPOS] DENEGADO: Límite máximo de {self.max_ordenes} operaciones activas alcanzado.")
            return False

        # 2. Filtro de Separación de Precio (Si ya existe una orden activa en la misma dirección)
        for pos in self.posiciones_activas:
            if pos['side'] == side:
                precio_base = pos['entry_price']
                
                # Calculamos la distancia porcentual absoluta
                distancia_actual = abs(precio_base - precio_propuesto) / precio_base
                
                if distancia_actual < self.distancia_minima:
                    print(f"🛑 [GESTOR CUPOS] DENEGADO: El precio (${precio_propuesto}) está muy cerca de la orden previa (${precio_base}).")
                    print(f"   Distancia actual: {distancia_actual*100:.2f}%. Requerida: {self.distancia_minima*100:.2f}%.")
                    return False
                else:
                    # Validar que el precio esté "en contra" (Drawdown temporal) para mejorar el promedio.
                    # No gastamos el segundo cupo si la primera orden ya está en grandes ganancias.
                    if (side == 'BUY' and precio_propuesto > precio_base) or \
                       (side == 'SELL' and precio_propuesto < precio_base):
                        print("🛑 [GESTOR CUPOS] DENEGADO: El nuevo precio no mejora el promedio de entrada anterior.")
                        return False

        print("✅ [GESTOR CUPOS] APROBADO: Cumple parámetros de exposición y distancia espacial.")
        return True

    def registrar_entrada(self, orden_id: str, side: str, entry_price: float):
        """Añade la orden al registro activo una vez disparada en el Exchange."""
        self.posiciones_activas.append({
            'id': orden_id,
            'side': side,
            'entry_price': entry_price
        })

    def liberar_cupo(self, orden_id: str):
        """Elimina una orden del registro cuando toca TP o SL."""
        self.posiciones_activas = [pos for pos in self.posiciones_activas if pos['id'] != orden_id]
        print(f"🔓 [GESTOR CUPOS] Orden {orden_id} cerrada. Cupo liberado.")