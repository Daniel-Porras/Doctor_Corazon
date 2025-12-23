# holter_ai.py - Módulo de Integración para Dispositivo Médico
# Este archivo actúa como puente entre el Hardware y la Inteligencia Artificial.

import os
import numpy as np
import tensorflow as tf

# Desactivar logs basura de TensorFlow para no ensuciar la consola del dispositivo
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

class HolterAnalyzer:
    def __init__(self, model_path):
        """
        Inicializa el motor de IA. Carga el modelo en memoria UNA sola vez.
        
        Args:
            model_path (str): Ruta al archivo .h5 (ej. 'modelos/vcg_model_optimized_4classes.h5')
        """
        print(" [AI SYSTEM] Inicializando motor de diagnóstico...")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"CRÍTICO: No se encuentra el modelo en: {model_path}")
            
        try:
            # Cargamos el modelo compilado
            self.model = tf.keras.models.load_model(model_path, compile=False)
            print(" [AI SYSTEM] Modelo cargado y listo en memoria RAM.")
            
            # Definimos las clases en el mismo orden que el entrenamiento
            self.classes = ['CD', 'MI', 'NORM', 'STTC'] 
            
        except Exception as e:
            print(f" [AI SYSTEM] Error fatal cargando el modelo: {e}")
            raise

    def preprocesar_senal(self, raw_signal):
        """
        Ajusta la señal que viene del hardware para que la IA la entienda.
        Requisito: La señal debe ser un array de (5000, 3) o lista equivalente.
        """
        # 1. Convertir a NumPy Array con tipo de dato flotante (float32 es estándar para IA)
        signal = np.array(raw_signal, dtype=np.float32)
        
        # 2. Validar dimensiones (Debe ser 5000 puntos x 3 canales)
        if signal.shape != (5000, 3):
            # Si viene transpuesto (3, 5000), lo corregimos
            if signal.shape == (3, 5000):
                signal = signal.T
            else:
                raise ValueError(f"Dimensión incorrecta. Se espera (5000, 3), se recibió {signal.shape}")

        # 3. Expandir dimensiones: La IA espera un lote (Batch).
        # Transformamos (5000, 3) -> (1, 5000, 3)
        input_tensor = np.expand_dims(signal, axis=0)
        
        return input_tensor

    def diagnosticar(self, signal_capturada):
        """
        Función principal que se usa en la captura de datos.
        Recibe los datos del sensor y devuelve el diagnóstico.
        """
        try:
            # Preparamos los datos
            tensor = self.preprocesar_senal(signal_capturada)
            
            # Hacemos la predicción (Inferencia)
            # verbose=0 para que no salga la barra de carga en el dispositivo
            probabilidades = self.model.predict(tensor, verbose=0)[0]
            
            # Interpretamos resultados (Umbral 0.5)
            diagnosticos_detectados = []
            resultado_detallado = {}
            
            for i, clase in enumerate(self.classes):
                score = probabilidades[i]
                resultado_detallado[clase] = float(score) # Guardamos probabilidad
                
                if score > 0.5:
                    diagnosticos_detectados.append(clase)
            
            # Si no detectó nada con seguridad, marcamos como incierto
            if not diagnosticos_detectados:
                status = "INCIERTO / SIN HALLAZGOS CLAROS"
            else:
                status = ", ".join(diagnosticos_detectados)
                
            return {
                "status": "OK",
                "diagnostico_texto": status,
                "detalles": resultado_detallado,
                "alerta_infarto": resultado_detallado.get('MI', 0) > 0.5 # Bandera crítica
            }
            
        except Exception as e:
            return {"status": "ERROR", "mensaje": str(e)}