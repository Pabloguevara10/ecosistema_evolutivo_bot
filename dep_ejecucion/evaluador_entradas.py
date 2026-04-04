# Módulo: evaluador_entradas.py - Pertenece a dep_ejecucion
class EvaluadorEntradas:
    def __init__(self, max_slippage_pct=0.002):
        # Deslizamiento máximo permitido: 0.2% por defecto
        self.max_slippage = max_slippage_pct

    def validar_viabilidad(self, señal: dict, precio_actual_mercado: float) -> bool:
        """
        Evalúa si la señal generada aún es matemáticamente viable en el mercado actual
        antes de solicitar cupos y comprometer capital.
        """
        id_estrategia = señal.get('id_estrategia', 'UNKNOWN')
        side = señal.get('side', '')
        
        # El precio de referencia es el precio al que Análisis detectó la señal
        precio_referencia = señal.get('precio_referencia', precio_actual_mercado)
        
        # Calcular el deslizamiento (Slippage)
        deslizamiento_absoluto = abs(precio_actual_mercado - precio_referencia)
        deslizamiento_pct = deslizamiento_absoluto / precio_referencia
        
        if deslizamiento_pct > self.max_slippage:
            print(f"⚠️ [Evaluador] Entrada {id_estrategia} rechazada por Slippage.")
            print(f"El precio saltó un {deslizamiento_pct*100:.3f}% (Límite: {self.max_slippage*100}%).")
            return False
            
        # Validación de dirección del Slippage (Si el precio mejoró a nuestro favor, siempre se acepta)
        if side == 'BUY' and precio_actual_mercado < precio_referencia:
            print("✅ [Evaluador] Precio mejorado a favor (Descuento). Entrada viable.")
            return True
        elif side == 'SELL' and precio_actual_mercado > precio_referencia:
            print("✅ [Evaluador] Precio mejorado a favor (Premium). Entrada viable.")
            return True
            
        print("✅ [Evaluador] Deslizamiento dentro del umbral de seguridad. Entrada aprobada.")
        return True

if __name__ == "__main__":
    print("Módulo Evaluador de Entradas Compilado.")