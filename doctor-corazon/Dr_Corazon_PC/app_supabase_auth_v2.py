# app_supabase_auth_v2.py - Servidor NO bloqueante con Frontend completo
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from flask_socketio import SocketIO, emit
import threading
import numpy as np
import time
import json
import io
from holter_ai import HolterAnalyzer
import receiver_udp  # Tu receptor EASI
from hr_hrv_analyzer import HRVAnalyzer, interpretar_hrv
from supabase_config import supabase, crear_paciente, guardar_diagnostico
from auth_manager import AuthManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dr_corazon_secure_key_2024_change_this'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Inicializar gestor de autenticación
auth = AuthManager(supabase)

# Configuración
RUTA_MODELO = "vcg_model_optimized_4classes.h5"
motor_ia = None
analizador_hrv = None

# Estado global del sistema
estado_sistema = {
    'conectado': False,
    'capturando': False,
    'ultimo_diagnostico': None,
    'modo_captura': 'auto',  # 'auto', 'manual', 'pausado'
    'paciente_activo': {}  # {user_id: paciente_id}
}

# Lock para thread-safety
import threading
estado_lock = threading.Lock()

# ============================================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================================

@app.route('/')
def index():
    """Redirige según estado de autenticación"""
    user = auth.obtener_usuario_actual()
    if user:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        session_data = auth.login(email, password)
        
        if session_data and session_data.user:
            auth.guardar_sesion_flask(session_data.user)
            flash('¡Bienvenido!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales inválidas', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Página de registro"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        nombre_completo = request.form.get('nombre_completo')
        
        user = auth.registrar_usuario(email, password, nombre_completo, rol='usuario')
        
        if user:
            flash('Usuario registrado. Por favor inicia sesión.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Error al registrar usuario', 'danger')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    auth.logout()
    auth.limpiar_sesion_flask()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))

# ============================================================================
# DASHBOARD
# ============================================================================

@app.route('/dashboard')
@auth.login_required
def dashboard():
    """Dashboard principal"""
    user = auth.obtener_usuario_actual()
    perfil = auth.obtener_perfil_usuario(user.id)
    stats = auth.obtener_estadisticas_usuario(user.id)
    
    return render_template('dashboard.html', 
                         usuario=perfil,
                         estadisticas=stats,
                         estado=estado_sistema)

# ============================================================================
# API DE PACIENTES
# ============================================================================

@app.route('/api/pacientes', methods=['GET', 'POST'])
@auth.login_required
def api_pacientes():
    """GET: Lista pacientes / POST: Crea paciente"""
    user_id = auth.obtener_user_id_sesion()
    es_admin = auth.es_administrador(user_id)
    
    if request.method == 'GET':
        try:
            if es_admin:
                response = supabase.table("pacientes").select("*, user_profiles(email, nombre_completo)").execute()
            else:
                response = supabase.table("pacientes").select("*").eq('user_id', user_id).execute()
            
            return jsonify({"status": "ok", "data": response.data})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.json
            
            paciente = supabase.table("pacientes").insert({
                'nombre': data.get('nombre'),
                'edad': data.get('edad'),
                'genero': data.get('genero'),
                'identificacion': data.get('identificacion'),
                'user_id': user_id
            }).execute()
            
            return jsonify({"status": "ok", "data": paciente.data[0]})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/paciente/<paciente_id>/diagnosticos', methods=['GET'])
@auth.login_required
def api_diagnosticos_paciente(paciente_id):
    """Obtiene diagnósticos de un paciente"""
    user_id = auth.obtener_user_id_sesion()
    es_admin = auth.es_administrador(user_id)
    
    try:
        paciente = supabase.table('pacientes').select('user_id').eq('id', paciente_id).single().execute()
        
        if not es_admin and paciente.data['user_id'] != user_id:
            return jsonify({"status": "error", "message": "No tienes permiso"}), 403
        
        limite = request.args.get('limite', 10, type=int)
        diagnosticos = supabase.table("diagnosticos").select("*").eq('paciente_id', paciente_id).order('timestamp', desc=True).limit(limite).execute()
        
        return jsonify({"status": "ok", "data": diagnosticos.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/seleccionar-paciente', methods=['POST'])
@auth.login_required
def api_seleccionar_paciente():
    """Selecciona paciente activo"""
    user_id = auth.obtener_user_id_sesion()
    es_admin = auth.es_administrador(user_id)
    
    data = request.json
    paciente_id = data.get('paciente_id')
    
    try:
        paciente = supabase.table('pacientes').select('user_id').eq('id', paciente_id).single().execute()
        
        if not es_admin and paciente.data['user_id'] != user_id:
            return jsonify({"status": "error", "message": "No tienes permiso"}), 403
        
        with estado_lock:
            estado_sistema['paciente_activo'][user_id] = paciente_id
        
        return jsonify({"status": "ok", "paciente_id": paciente_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================================================
# API DE CONTROL DE CAPTURA
# ============================================================================

@app.route('/api/control/iniciar', methods=['POST'])
@auth.login_required
def api_iniciar_captura():
    """Inicia la captura de datos"""
    with estado_lock:
        estado_sistema['modo_captura'] = 'auto'
        estado_sistema['capturando'] = True
    
    return jsonify({"status": "ok", "message": "Captura iniciada"})

@app.route('/api/control/pausar', methods=['POST'])
@auth.login_required
def api_pausar_captura():
    """Pausa la captura"""
    with estado_lock:
        estado_sistema['modo_captura'] = 'pausado'
        estado_sistema['capturando'] = False
    
    return jsonify({"status": "ok", "message": "Captura pausada"})

@app.route('/api/control/manual', methods=['POST'])
@auth.login_required
def api_captura_manual():
    """Captura un dato manualmente"""
    with estado_lock:
        estado_sistema['modo_captura'] = 'manual'
    
    return jsonify({"status": "ok", "message": "Modo manual activado"})

@app.route('/api/control/estado', methods=['GET'])
@auth.login_required
def api_estado_sistema():
    """Obtiene el estado del sistema"""
    with estado_lock:
        estado = estado_sistema.copy()
    
    return jsonify({"status": "ok", "estado": estado})

# ============================================================================
# EXPORTACIÓN DE DATOS
# ============================================================================

@app.route('/api/exportar-mis-datos')
@auth.login_required
def exportar_mis_datos():
    """Exporta datos del usuario actual"""
    user_id = auth.obtener_user_id_sesion()
    datos = auth.exportar_datos_usuario(user_id)
    
    if datos:
        buffer = io.BytesIO()
        buffer.write(json.dumps(datos, indent=2, ensure_ascii=False).encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'datos_dr_corazon_{user_id}.json'
        )
    else:
        flash('Error al exportar datos', 'danger')
        return redirect(url_for('dashboard'))

# ============================================================================
# PANEL DE ADMINISTRACIÓN
# ============================================================================

@app.route('/admin')
@auth.admin_required
def admin_panel():
    """Panel de administración"""
    return render_template('admin_panel.html')

@app.route('/api/admin/usuarios')
@auth.admin_required
def api_admin_usuarios():
    """Lista todos los usuarios"""
    try:
        # Obtener todos los usuarios
        response = supabase.table('user_profiles').select('*').execute()
        return jsonify({"status": "ok", "data": response.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/estadisticas')
@auth.admin_required
def api_admin_estadisticas():
    """Obtiene estadísticas de todos los usuarios"""
    try:
        response = supabase.table('vista_estadisticas_usuarios').select('*').execute()
        return jsonify({"status": "ok", "data": response.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/cambiar-rol/<user_id>/<nuevo_rol>', methods=['POST'])
@auth.admin_required
def api_admin_cambiar_rol(user_id, nuevo_rol):
    """Cambia el rol de un usuario"""
    if auth.cambiar_rol_usuario(user_id, nuevo_rol):
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "error"}), 500

@app.route('/api/admin/desactivar-usuario/<user_id>', methods=['POST'])
@auth.admin_required
def api_admin_desactivar_usuario(user_id):
    """Desactiva un usuario"""
    if auth.desactivar_usuario(user_id):
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "error"}), 500

@app.route('/api/admin/exportar-usuario/<user_id>')
@auth.admin_required
def api_admin_exportar_usuario(user_id):
    """Exporta datos de cualquier usuario"""
    datos = auth.exportar_datos_usuario(user_id)
    
    if datos:
        buffer = io.BytesIO()
        buffer.write(json.dumps(datos, indent=2, ensure_ascii=False).encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'datos_usuario_{user_id}.json'
        )
    else:
        return jsonify({"status": "error"}), 500

# ============================================================================
# WEBSOCKETS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Cliente conectado"""
    user_id = auth.obtener_user_id_sesion()
    if not user_id:
        return False
    
    # Unir a sala específica del usuario
    from flask_socketio import join_room
    join_room(f'user_{user_id}')
    
    print(f'✅ Cliente conectado: user_{user_id}')
    
    # Enviar estado inicial
    with estado_lock:
        estado = estado_sistema.copy()
        paciente_activo = estado_sistema['paciente_activo'].get(user_id)
    
    emit('status', {
        'message': 'Conectado',
        'estado': estado,
        'paciente_activo': paciente_activo,
        'user_id': user_id
    })
    
    # Enviar último diagnóstico si existe y es del usuario
    with estado_lock:
        ultimo = estado_sistema.get('ultimo_diagnostico')
        if ultimo and paciente_activo:
            emit('diagnostico', ultimo)

@socketio.on('disconnect')
def handle_disconnect():
    """Cliente desconectado"""
    user_id = auth.obtener_user_id_sesion()
    if user_id:
        from flask_socketio import leave_room
        leave_room(f'user_{user_id}')
        print(f'❌ Cliente desconectado: user_{user_id}')

@socketio.on('seleccionar_paciente')
def handle_seleccionar_paciente(data):
    """Handle patient selection via WebSocket"""
    user_id = auth.obtener_user_id_sesion()
    if not user_id:
        emit('error', {'message': 'No autenticado'})
        return
    
    paciente_id = data.get('paciente_id')
    
    try:
        # Verificar permisos
        es_admin = auth.es_administrador(user_id)
        paciente = supabase.table('pacientes').select('user_id, nombre').eq('id', paciente_id).single().execute()
        
        if not es_admin and paciente.data['user_id'] != user_id:
            emit('error', {'message': 'No tienes permiso para este paciente'})
            return
        
        # Actualizar paciente activo
        with estado_lock:
            estado_sistema['paciente_activo'][user_id] = paciente_id
        
        emit('paciente_seleccionado', {
            'paciente_id': paciente_id,
            'nombre': paciente.data['nombre']
        })
        
        print(f"✅ Usuario {user_id} seleccionó paciente: {paciente.data['nombre']}")
        
    except Exception as e:
        emit('error', {'message': str(e)})

# ============================================================================
# HILO DE CAPTURA (NO BLOQUEANTE)
# ============================================================================

def ciclo_de_captura_background():
    """Hilo separado para captura de datos ESP32 - NO bloquea el servidor"""
    global motor_ia, analizador_hrv
    
    print("\n🚀 Iniciando hilo de captura en background...")
    
    # Inicializar IA y HRV
    motor_ia = HolterAnalyzer(RUTA_MODELO)
    analizador_hrv = HRVAnalyzer(frecuencia_muestreo=500)
    print("✅ IA y HRV listos en background\n")
    
    # Marcar como conectado
    with estado_lock:
        estado_sistema['conectado'] = True
    
    socketio.emit('status', {
        'message': 'Sistema inicializado',
        'ia_ready': True,
        'hrv_ready': True
    })
    
    print("👂 Esperando datos ECG desde ESP32...")
    print(f"   Puerto UDP: {receiver_udp.UDP_PORT}")
    print(f"   Esperando ventanas de {receiver_udp.WINDOW_SEC}s ({receiver_udp.N_OUT} muestras)\n")
    
    # USAR TU RECEPTOR EASI
    # enable_plot=False para NO bloquear con matplotlib
    for datos_hardware in receiver_udp.receive_packets(enable_plot=False):
        # Verificar si está pausado
        with estado_lock:
            if estado_sistema['modo_captura'] == 'pausado':
                time.sleep(1)
                continue
            
            pacientes_activos = estado_sistema['paciente_activo'].copy()
        
        if not pacientes_activos:
            print("⚠️  No hay pacientes seleccionados")
            time.sleep(1)
            continue
        
        # Notificar procesamiento
        socketio.emit('procesando', {
            'message': 'Analizando señal EASI...',
            'shape': datos_hardware.shape
        })
        
        # Análisis
        start_time = time.time()
        resultado = motor_ia.diagnosticar(datos_hardware)
        resultado_hrv = analizador_hrv.analizar(datos_hardware, usar_canal='mejor')
        end_time = time.time()
        
        tiempo_analisis = end_time - start_time
        
        if resultado["status"] == "OK":
            print(f"\n📊 Diagnóstico: {resultado['diagnostico_texto']} | HR: {resultado_hrv['hr_bpm']} BPM")
            
            # Guardar para cada usuario activo y emitir a su sala específica
            for user_id, paciente_id in pacientes_activos.items():
                try:
                    # Guardar en base de datos
                    diag_guardado = guardar_diagnostico(
                        paciente_id=paciente_id,
                        diagnostico=resultado['diagnostico_texto'],
                        probabilidades=resultado['detalles'],
                        tiempo_analisis=tiempo_analisis,
                        alerta_critica=resultado.get('alerta_infarto', False),
                        notas=f"User: {user_id} | EASI->XYZ",
                        hr_bpm=resultado_hrv['hr_bpm'],
                        hrv_sdnn=resultado_hrv['hrv_sdnn'],
                        hrv_rmssd=resultado_hrv['hrv_rmssd'],
                        hrv_pnn50=resultado_hrv['hrv_pnn50'],
                        num_picos_r=resultado_hrv['num_picos']
                    )
                    
                    if diag_guardado:
                        print(f"  ✅ Guardado para usuario {user_id}, paciente {paciente_id}")
                    
                except Exception as e:
                    print(f"❌ Error guardando para usuario {user_id}: {e}")
            
            # Preparar payload
            interpretacion_hrv = interpretar_hrv(
                resultado_hrv['hrv_sdnn'],
                resultado_hrv['hrv_rmssd'],
                resultado_hrv['hrv_pnn50']
            )
            
            # Crear payload base
            payload_base = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'diagnostico': resultado['diagnostico_texto'],
                'probabilidades': resultado['detalles'],
                'tiempo_analisis': round(tiempo_analisis, 3),
                'alerta': resultado.get('alerta_infarto', False),
                'hr_bpm': resultado_hrv['hr_bpm'],
                'hr_clasificacion': resultado_hrv['clasificacion_hr'],
                'hrv_sdnn': resultado_hrv['hrv_sdnn'],
                'hrv_rmssd': resultado_hrv['hrv_rmssd'],
                'hrv_pnn50': resultado_hrv['hrv_pnn50'],
                'num_picos': resultado_hrv['num_picos'],
                'calidad_señal': resultado_hrv['calidad'],
                'interpretacion_hrv': interpretacion_hrv,
                'picos_indices': resultado_hrv['picos_indices'].tolist(),
                # Submuestrear para enviar menos datos al frontend
                'datos_x': datos_hardware[::10, 0].tolist(),
                'datos_y': datos_hardware[::10, 1].tolist(),
                'datos_z': datos_hardware[::10, 2].tolist(),
            }
            
            # Enviar a cada usuario en su sala específica
            for user_id, paciente_id in pacientes_activos.items():
                # Agregar info del paciente al payload
                payload = payload_base.copy()
                payload['user_id'] = user_id
                payload['paciente_id'] = paciente_id
                
                # Emitir solo a la sala de este usuario
                socketio.emit('diagnostico', payload, room=f'user_{user_id}')
                
                # Si hay alerta, emitir alerta también
                if resultado.get('alerta_infarto', False):
                    socketio.emit('alerta_critica', {
                        'tipo': 'infarto',
                        'mensaje': 'ALERTA: Posible infarto',
                        'hr_bpm': resultado_hrv['hr_bpm'],
                        'user_id': user_id,
                        'paciente_id': paciente_id
                    }, room=f'user_{user_id}')
            
            with estado_lock:
                estado_sistema['ultimo_diagnostico'] = payload_base
        
        time.sleep(0.5)

# ============================================================================
# INICIAR SERVIDOR
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🫀 Dr Corazón - Sistema Web Completo")
    print("="*60)
    print("\n✅ Servidor Flask iniciado")
    print("✅ Frontend totalmente independiente")
    print("✅ Backend NO bloqueante")
    print("\n📍 URL: http://localhost:5000")
    print("\n⚙️  Características:")
    print("   - Panel Admin funcional")
    print("   - Gestión de usuarios desde web")
    print("   - Control de captura desde web")
    print("   - Exportación de datos desde web")
    print("   - Consola solo para debugging")
    print("\n" + "="*60 + "\n")
    
    # Iniciar hilo de captura EN BACKGROUND
    captura_thread = threading.Thread(target=ciclo_de_captura_background, daemon=True)
    captura_thread.start()
    
    # Iniciar servidor Flask (NO SE BLOQUEA)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)
