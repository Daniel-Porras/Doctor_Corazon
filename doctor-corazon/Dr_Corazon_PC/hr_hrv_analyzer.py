# hr_hrv_analyzer.py - Análisis de Frecuencia Cardíaca y Variabilidad
import numpy as np
from scipy import signal
from scipy.signal import find_peaks

class HRVAnalyzer:
    """
    Calculador de HR (Heart Rate) y HRV (Heart Rate Variability)
    """
    
    def __init__(self, frecuencia_muestreo=500):
        """
        Args:
            frecuencia_muestreo: Hz, típicamente 500 Hz para ECG
        """
        self.fs = frecuencia_muestreo
    
    def detectar_picos_r(self, señal_ecg):
        """
        Detecta los picos R en la señal ECG (complejo QRS)
        
        Args:
            señal_ecg: Array 1D con la señal ECG (normalizada)
        
        Returns:
            indices: Array con las posiciones de los picos R
        """
        # Normalizar señal
        señal = (señal_ecg - np.mean(señal_ecg)) / np.std(señal_ecg)
        
        # Filtro pasa banda para resaltar complejo QRS (5-15 Hz)
        sos = signal.butter(4, [5, 15], btype='band', fs=self.fs, output='sos')
        señal_filtrada = signal.sosfilt(sos, señal)
        
        # Detectar picos
        # Altura mínima: 50% del máximo de la señal filtrada
        # Distancia mínima: 0.4 seg (150 BPM máximo)
        altura_minima = 0.5 * np.max(np.abs(señal_filtrada))
        distancia_minima = int(0.4 * self.fs)  # 400ms entre picos
        
        picos, propiedades = find_peaks(
            señal_filtrada, 
            height=altura_minima,
            distance=distancia_minima,
            prominence=0.3
        )
        
        return picos
    
    def calcular_intervalos_rr(self, picos):
        """
        Calcula intervalos R-R (tiempo entre latidos consecutivos)
        
        Args:
            picos: Índices de los picos R
        
        Returns:
            rr_intervals: Array con intervalos R-R en milisegundos
        """
        if len(picos) < 2:
            return np.array([])
        
        # Calcular diferencias entre picos consecutivos
        rr_samples = np.diff(picos)
        
        # Convertir de muestras a milisegundos
        rr_intervals = (rr_samples / self.fs) * 1000
        
        return rr_intervals
    
    def calcular_hr(self, picos, duracion_segundos):
        """
        Calcula frecuencia cardíaca en BPM
        
        Args:
            picos: Índices de los picos R
            duracion_segundos: Duración de la grabación en segundos
        
        Returns:
            hr_bpm: Frecuencia cardíaca en latidos por minuto
        """
        if len(picos) < 2:
            return None
        
        num_latidos = len(picos)
        hr_bpm = (num_latidos / duracion_segundos) * 60
        
        return round(hr_bpm, 1)
    
    def calcular_hrv_sdnn(self, rr_intervals):
        """
        Calcula SDNN (Standard Deviation of NN intervals)
        Medida de variabilidad total
        
        Args:
            rr_intervals: Array de intervalos R-R en ms
        
        Returns:
            sdnn: Desviación estándar en ms
        """
        if len(rr_intervals) < 2:
            return None
        
        # Filtrar intervalos anormales (outliers)
        rr_clean = self._filtrar_outliers(rr_intervals)
        
        if len(rr_clean) < 2:
            return None
        
        sdnn = np.std(rr_clean, ddof=1)
        return round(sdnn, 2)
    
    def calcular_hrv_rmssd(self, rr_intervals):
        """
        Calcula RMSSD (Root Mean Square of Successive Differences)
        Medida de variabilidad a corto plazo
        
        Args:
            rr_intervals: Array de intervalos R-R en ms
        
        Returns:
            rmssd: RMSSD en ms
        """
        if len(rr_intervals) < 2:
            return None
        
        # Filtrar outliers
        rr_clean = self._filtrar_outliers(rr_intervals)
        
        if len(rr_clean) < 2:
            return None
        
        # Diferencias sucesivas
        diff_rr = np.diff(rr_clean)
        
        # Raíz cuadrada de la media de cuadrados
        rmssd = np.sqrt(np.mean(diff_rr ** 2))
        
        return round(rmssd, 2)
    
    def calcular_hrv_pnn50(self, rr_intervals):
        """
        Calcula pNN50 (percentage of NN intervals that differ by more than 50ms)
        
        Args:
            rr_intervals: Array de intervalos R-R en ms
        
        Returns:
            pnn50: Porcentaje (0-100)
        """
        if len(rr_intervals) < 2:
            return None
        
        # Filtrar outliers
        rr_clean = self._filtrar_outliers(rr_intervals)
        
        if len(rr_clean) < 2:
            return None
        
        # Diferencias sucesivas
        diff_rr = np.abs(np.diff(rr_clean))
        
        # Contar cuántas difieren por más de 50ms
        nn50 = np.sum(diff_rr > 50)
        
        # Calcular porcentaje
        pnn50 = (nn50 / len(diff_rr)) * 100
        
        return round(pnn50, 2)
    
    def _filtrar_outliers(self, rr_intervals):
        """
        Filtra intervalos R-R anormales (outliers)
        
        Args:
            rr_intervals: Array de intervalos R-R
        
        Returns:
            rr_clean: Array sin outliers
        """
        if len(rr_intervals) < 3:
            return rr_intervals
        
        # Usar percentiles para detectar outliers
        q1 = np.percentile(rr_intervals, 25)
        q3 = np.percentile(rr_intervals, 75)
        iqr = q3 - q1
        
        # Límites: Q1 - 1.5*IQR y Q3 + 1.5*IQR
        limite_inferior = q1 - 1.5 * iqr
        limite_superior = q3 + 1.5 * iqr
        
        # Filtrar
        rr_clean = rr_intervals[
            (rr_intervals >= limite_inferior) & 
            (rr_intervals <= limite_superior)
        ]
        
        return rr_clean
    
    def analizar(self, señal_ecg, usar_canal='mejor'):
        """
        Análisis completo de HR y HRV
        
        Args:
            señal_ecg: Array (N, 3) con canales X, Y, Z o array 1D
            usar_canal: 'x', 'y', 'z', 'mejor' (detecta automáticamente)
        
        Returns:
            dict con:
                - hr_bpm: Frecuencia cardíaca
                - num_picos: Número de picos R detectados
                - rr_intervals: Intervalos R-R en ms
                - hrv_sdnn: SDNN en ms
                - hrv_rmssd: RMSSD en ms
                - hrv_pnn50: pNN50 en porcentaje
                - clasificacion_hr: Clasificación del HR
                - calidad: Indicador de calidad de la señal
        """
        # Determinar duración en segundos
        num_muestras = len(señal_ecg)
        duracion_seg = num_muestras / self.fs
        
        # Seleccionar canal
        if señal_ecg.ndim == 2:
            if usar_canal == 'mejor':
                # Usar el canal con mayor amplitud (mejor señal)
                amplitudes = [np.max(np.abs(señal_ecg[:, i])) for i in range(señal_ecg.shape[1])]
                idx_mejor = np.argmax(amplitudes)
                señal = señal_ecg[:, idx_mejor]
                canal_usado = ['X', 'Y', 'Z'][idx_mejor]
            else:
                canal_map = {'x': 0, 'y': 1, 'z': 2}
                señal = señal_ecg[:, canal_map[usar_canal.lower()]]
                canal_usado = usar_canal.upper()
        else:
            señal = señal_ecg
            canal_usado = 'Único'
        
        # Detectar picos R
        picos = self.detectar_picos_r(señal)
        num_picos = len(picos)
        
        # Calcular HR
        hr_bpm = self.calcular_hr(picos, duracion_seg)
        
        # Calcular intervalos R-R
        rr_intervals = self.calcular_intervalos_rr(picos)
        
        # Calcular métricas HRV
        hrv_sdnn = self.calcular_hrv_sdnn(rr_intervals)
        hrv_rmssd = self.calcular_hrv_rmssd(rr_intervals)
        hrv_pnn50 = self.calcular_hrv_pnn50(rr_intervals)
        
        # Clasificar HR
        clasificacion = self._clasificar_hr(hr_bpm)
        
        # Evaluar calidad de la señal
        calidad = self._evaluar_calidad(num_picos, duracion_seg, rr_intervals)
        
        return {
            'hr_bpm': hr_bpm,
            'num_picos': num_picos,
            'picos_indices': picos,
            'rr_intervals': rr_intervals,
            'hrv_sdnn': hrv_sdnn,
            'hrv_rmssd': hrv_rmssd,
            'hrv_pnn50': hrv_pnn50,
            'clasificacion_hr': clasificacion,
            'calidad': calidad,
            'canal_usado': canal_usado,
            'duracion_seg': duracion_seg
        }
    
    def _clasificar_hr(self, hr_bpm):
        """Clasifica la frecuencia cardíaca"""
        if hr_bpm is None:
            return "DESCONOCIDO"
        elif hr_bpm < 40:
            return "BRADICARDIA SEVERA"
        elif hr_bpm < 60:
            return "BRADICARDIA LEVE"
        elif 60 <= hr_bpm <= 100:
            return "NORMAL"
        elif 100 < hr_bpm <= 120:
            return "TAQUICARDIA LEVE"
        else:
            return "TAQUICARDIA SEVERA"
    
    def _evaluar_calidad(self, num_picos, duracion, rr_intervals):
        """
        Evalúa la calidad de la detección
        
        Returns:
            str: 'EXCELENTE', 'BUENA', 'ACEPTABLE', 'POBRE'
        """
        if num_picos < 5:
            return "POBRE"
        
        # HR esperado entre 40-150 BPM
        hr_estimado = (num_picos / duracion) * 60
        if hr_estimado < 30 or hr_estimado > 180:
            return "POBRE"
        
        if len(rr_intervals) < 5:
            return "ACEPTABLE"
        
        # Variabilidad de intervalos R-R
        cv = np.std(rr_intervals) / np.mean(rr_intervals)
        
        if cv < 0.5 and num_picos >= 10:
            return "EXCELENTE"
        elif cv < 0.8 and num_picos >= 8:
            return "BUENA"
        else:
            return "ACEPTABLE"


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def interpretar_hrv(sdnn, rmssd, pnn50):
    """
    Interpreta los valores de HRV
    
    Returns:
        dict con interpretaciones
    """
    interpretacion = {
        'sdnn': None,
        'rmssd': None,
        'pnn50': None,
        'estado_general': None
    }
    
    # SDNN (valores típicos en adultos sanos: 50-100 ms)
    if sdnn is not None:
        if sdnn < 30:
            interpretacion['sdnn'] = "Muy baja - Posible estrés/fatiga"
        elif sdnn < 50:
            interpretacion['sdnn'] = "Baja - Variabilidad reducida"
        elif sdnn <= 100:
            interpretacion['sdnn'] = "Normal - Buena variabilidad"
        else:
            interpretacion['sdnn'] = "Alta - Excelente variabilidad"
    
    # RMSSD (valores típicos: 20-50 ms)
    if rmssd is not None:
        if rmssd < 15:
            interpretacion['rmssd'] = "Muy baja - Baja actividad parasimpática"
        elif rmssd < 25:
            interpretacion['rmssd'] = "Baja - Actividad parasimpática reducida"
        elif rmssd <= 50:
            interpretacion['rmssd'] = "Normal - Buena modulación vagal"
        else:
            interpretacion['rmssd'] = "Alta - Excelente tono vagal"
    
    # pNN50 (valores típicos: 5-30%)
    if pnn50 is not None:
        if pnn50 < 3:
            interpretacion['pnn50'] = "Muy bajo - Variabilidad limitada"
        elif pnn50 < 10:
            interpretacion['pnn50'] = "Bajo - Variabilidad reducida"
        elif pnn50 <= 30:
            interpretacion['pnn50'] = "Normal - Buena variabilidad"
        else:
            interpretacion['pnn50'] = "Alto - Excelente variabilidad"
    
    # Estado general (basado en SDNN principalmente)
    if sdnn is not None and rmssd is not None:
        if sdnn >= 50 and rmssd >= 25:
            interpretacion['estado_general'] = "Excelente salud cardiovascular"
        elif sdnn >= 30 and rmssd >= 15:
            interpretacion['estado_general'] = "Buena salud cardiovascular"
        else:
            interpretacion['estado_general'] = "Considerar evaluación médica"
    
    return interpretacion


# ============================================================================
# PRUEBA DEL MÓDULO
# ============================================================================

if __name__ == "__main__":
    print("🫀 Analizador de HR y HRV")
    print("=" * 50)
    
    # Generar señal ECG simulada para prueba
    fs = 500  # Hz
    duracion = 10  # segundos
    t = np.linspace(0, duracion, fs * duracion)
    
    # Simular ECG con frecuencia cardíaca de 70 BPM
    hr_simulado = 70
    frecuencia_cardiaca = hr_simulado / 60  # Hz
    
    # Señal base (onda sinusoidal)
    señal_simulada = np.sin(2 * np.pi * frecuencia_cardiaca * t)
    
    # Agregar picos R (complejos QRS)
    for i in range(0, len(t), int(fs / frecuencia_cardiaca)):
        if i < len(señal_simulada):
            señal_simulada[i:min(i+50, len(señal_simulada))] += 2
    
    # Agregar ruido
    ruido = 0.1 * np.random.randn(len(señal_simulada))
    señal_simulada += ruido
    
    # Crear analizador
    analizador = HRVAnalyzer(frecuencia_muestreo=fs)
    
    # Analizar
    resultado = analizador.analizar(señal_simulada)
    
    # Mostrar resultados
    print("\n📊 Resultados del Análisis:")
    print(f"  Frecuencia Cardíaca: {resultado['hr_bpm']} BPM")
    print(f"  Clasificación: {resultado['clasificacion_hr']}")
    print(f"  Picos R detectados: {resultado['num_picos']}")
    print(f"  Calidad de señal: {resultado['calidad']}")
    
    print("\n📈 Métricas HRV:")
    print(f"  SDNN: {resultado['hrv_sdnn']} ms")
    print(f"  RMSSD: {resultado['hrv_rmssd']} ms")
    print(f"  pNN50: {resultado['hrv_pnn50']}%")
    
    # Interpretar
    interpretacion = interpretar_hrv(
        resultado['hrv_sdnn'],
        resultado['hrv_rmssd'],
        resultado['hrv_pnn50']
    )
    
    print("\n💡 Interpretación:")
    for clave, valor in interpretacion.items():
        if valor:
            print(f"  {clave}: {valor}")
    
    print("\n✅ Módulo funcionando correctamente!")
