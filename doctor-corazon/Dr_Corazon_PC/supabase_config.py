# supabase_config.py - Configuración de Supabase

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables de entorno
load_dotenv()

# Configuración desde .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Verificar que existen
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Faltan credenciales de Supabase en .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============ FUNCIONES DE BASE DE DATOS ============

def crear_paciente(nombre: str, edad: int = None, genero: str = None, identificacion: str = None):
    """
    Crea un nuevo paciente en la base de datos
    
    Returns:
        dict: Datos del paciente creado (incluyendo ID)
    """
    try:
        data = {
            "nombre": nombre,
            "edad": edad,
            "genero": genero,
            "identificacion": identificacion
        }
        
        response = supabase.table("pacientes").insert(data).execute()
        print(f"✅ Paciente creado: {nombre} (ID: {response.data[0]['id']})")
        return response.data[0]
    except Exception as e:
        print(f"❌ Error al crear paciente: {e}")
        return None

def guardar_diagnostico(
    paciente_id: str,
    diagnostico: str,
    probabilidades: dict,
    tiempo_analisis: float,
    alerta_critica: bool = False,
    notas: str = None,
    hr_bpm: float = None,
    hrv_sdnn: float = None,
    hrv_rmssd: float = None,
    hrv_pnn50: float = None,
    num_picos_r: int = None
):
    """
    Guarda un diagnóstico en la base de datos
    
    Args:
        paciente_id: UUID del paciente
        diagnostico: Texto del diagnóstico (ej: "NORMAL")
        probabilidades: Dict con probabilidades {"Normal": 0.87, "Infarto": 0.08, ...}
        tiempo_analisis: Tiempo que tomó el análisis en segundos
        alerta_critica: True si hay alerta de infarto
        notas: Notas adicionales (opcional)
        hr_bpm: Frecuencia cardíaca en BPM (opcional)
        hrv_sdnn: HRV SDNN en ms (opcional)
        hrv_rmssd: HRV RMSSD en ms (opcional)
        hrv_pnn50: HRV pNN50 en % (opcional)
        num_picos_r: Número de picos R detectados (opcional)
    
    Returns:
        dict: Datos del diagnóstico guardado
    """
    try:
        data = {
            "paciente_id": paciente_id,
            "diagnostico": diagnostico,
            "probabilidad_normal": probabilidades.get("Normal", 0),
            "probabilidad_infarto": probabilidades.get("Infarto", 0),
            "probabilidad_bradicardia": probabilidades.get("Bradicardia", 0),
            "probabilidad_taquicardia": probabilidades.get("Taquicardia", 0),
            "tiempo_analisis": tiempo_analisis,
            "alerta_critica": alerta_critica,
            "notas": notas,
            "hr_bpm": hr_bpm,
            "hrv_sdnn": hrv_sdnn,
            "hrv_rmssd": hrv_rmssd,
            "hrv_pnn50": hrv_pnn50,
            "num_picos_r": num_picos_r
        }
        
        response = supabase.table("diagnosticos").insert(data).execute()
        print(f"✅ Diagnóstico guardado: {diagnostico} | HR: {hr_bpm} BPM (ID: {response.data[0]['id']})")
        return response.data[0]
    except Exception as e:
        print(f"❌ Error al guardar diagnóstico: {e}")
        return None

def guardar_senales_ecg(
    diagnostico_id: int,
    canal_x: list,
    canal_y: list,
    canal_z: list,
    frecuencia_muestreo: int = 500,
    duracion_segundos: int = 10
):
    """
    Guarda las señales ECG raw (opcional, consume espacio)
    
    Args:
        diagnostico_id: ID del diagnóstico asociado
        canal_x, canal_y, canal_z: Listas con los valores de cada canal
        frecuencia_muestreo: Hz (default 500)
        duracion_segundos: Duración de la captura (default 10)
    """
    try:
        data = {
            "diagnostico_id": diagnostico_id,
            "canal_x": canal_x,
            "canal_y": canal_y,
            "canal_z": canal_z,
            "frecuencia_muestreo": frecuencia_muestreo,
            "duracion_segundos": duracion_segundos
        }
        
        response = supabase.table("senales_ecg").insert(data).execute()
        print(f"✅ Señales ECG guardadas (ID: {response.data[0]['id']})")
        return response.data[0]
    except Exception as e:
        print(f"❌ Error al guardar señales: {e}")
        return None

def obtener_diagnosticos_paciente(paciente_id: str, limite: int = 10):
    """
    Obtiene los últimos diagnósticos de un paciente
    
    Args:
        paciente_id: UUID del paciente
        limite: Número máximo de registros a retornar
    
    Returns:
        list: Lista de diagnósticos
    """
    try:
        response = supabase.table("diagnosticos")\
            .select("*")\
            .eq("paciente_id", paciente_id)\
            .order("timestamp", desc=True)\
            .limit(limite)\
            .execute()
        
        return response.data
    except Exception as e:
        print(f"❌ Error al obtener diagnósticos: {e}")
        return []

def obtener_alertas_criticas(limite: int = 20):
    """
    Obtiene las alertas críticas más recientes
    
    Returns:
        list: Lista de diagnósticos con alerta crítica
    """
    try:
        response = supabase.table("diagnosticos")\
            .select("*, pacientes(nombre, identificacion)")\
            .eq("alerta_critica", True)\
            .order("timestamp", desc=True)\
            .limit(limite)\
            .execute()
        
        return response.data
    except Exception as e:
        print(f"❌ Error al obtener alertas: {e}")
        return []

def obtener_estadisticas_paciente(paciente_id: str):
    """
    Calcula estadísticas de diagnósticos de un paciente
    
    Returns:
        dict: Estadísticas (total, por tipo, últimos 7 días, etc.)
    """
    try:
        # Obtener todos los diagnósticos
        response = supabase.table("diagnosticos")\
            .select("diagnostico, alerta_critica, timestamp")\
            .eq("paciente_id", paciente_id)\
            .execute()
        
        diagnosticos = response.data
        
        if not diagnosticos:
            return {"total": 0, "mensaje": "Sin diagnósticos"}
        
        # Contar por tipo
        from collections import Counter
        conteo = Counter([d["diagnostico"] for d in diagnosticos])
        
        # Alertas críticas
        alertas = sum(1 for d in diagnosticos if d["alerta_critica"])
        
        return {
            "total": len(diagnosticos),
            "por_tipo": dict(conteo),
            "alertas_criticas": alertas,
            "ultimo": diagnosticos[0] if diagnosticos else None
        }
    except Exception as e:
        print(f"❌ Error al calcular estadísticas: {e}")
        return {}

# ============ FUNCIONES DE TEST ============

def test_conexion():
    """Prueba la conexión a Supabase"""
    try:
        response = supabase.table("pacientes").select("count").execute()
        print(f"✅ Conexión exitosa a Supabase")
        return True
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    # Test básico
    print("🔍 Probando conexión a Supabase...")
    test_conexion()
