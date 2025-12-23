# auth_manager.py - Sistema de Autenticación con Supabase
from functools import wraps
from flask import session, redirect, url_for, flash, request
from supabase import Client
import bcrypt

class AuthManager:
    """Gestor de autenticación y autorización con Supabase"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    # ============================================================================
    # AUTENTICACIÓN
    # ============================================================================
    
    def registrar_usuario(self, email: str, password: str, nombre_completo: str, rol: str = 'usuario'):
        """
        Registra un nuevo usuario
        
        Args:
            email: Correo electrónico
            password: Contraseña
            nombre_completo: Nombre completo
            rol: 'usuario' o 'administrador'
        
        Returns:
            dict: Datos del usuario creado o None si hay error
        """
        try:
            # Crear usuario en Supabase Auth
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "nombre_completo": nombre_completo,
                        "rol": rol
                    }
                }
            })
            
            if response.user:
                print(f"✅ Usuario registrado: {email} ({rol})")
                return response.user
            else:
                print(f"❌ Error al registrar usuario: {response}")
                return None
                
        except Exception as e:
            print(f"❌ Error en registro: {e}")
            return None
    
    def login(self, email: str, password: str):
        """
        Inicia sesión de un usuario
        
        Args:
            email: Correo electrónico
            password: Contraseña
        
        Returns:
            dict: Sesión del usuario o None si hay error
        """
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                # Actualizar último acceso
                self.supabase.rpc('update_user_last_access', {'user_id': response.user.id}).execute()
                
                print(f"✅ Login exitoso: {email}")
                return response
            else:
                print(f"❌ Login fallido: credenciales inválidas")
                return None
                
        except Exception as e:
            print(f"❌ Error en login: {e}")
            return None
    
    def logout(self):
        """Cierra la sesión del usuario actual"""
        try:
            self.supabase.auth.sign_out()
            print("✅ Sesión cerrada")
            return True
        except Exception as e:
            print(f"❌ Error al cerrar sesión: {e}")
            return False
    
    def obtener_usuario_actual(self):
        """
        Obtiene el usuario actualmente autenticado
        
        Returns:
            dict: Datos del usuario o None
        """
        try:
            user = self.supabase.auth.get_user()
            return user.user if user else None
        except:
            return None
    
    def obtener_perfil_usuario(self, user_id: str = None):
        """
        Obtiene el perfil completo del usuario desde user_profiles
        
        Args:
            user_id: ID del usuario (si es None, usa el usuario actual)
        
        Returns:
            dict: Perfil del usuario
        """
        try:
            if not user_id:
                current_user = self.obtener_usuario_actual()
                if not current_user:
                    return None
                user_id = current_user.id
            
            response = self.supabase.table('user_profiles').select('*').eq('id', user_id).single().execute()
            return response.data
        except Exception as e:
            print(f"❌ Error obteniendo perfil: {e}")
            return None
    
    def es_administrador(self, user_id: str = None):
        """
        Verifica si un usuario es administrador
        
        Args:
            user_id: ID del usuario (si es None, usa el usuario actual)
        
        Returns:
            bool: True si es administrador
        """
        perfil = self.obtener_perfil_usuario(user_id)
        return perfil and perfil.get('rol') == 'administrador'
    
    # ============================================================================
    # DECORADORES PARA RUTAS
    # ============================================================================
    
    def login_required(self, f):
        """Decorador: Requiere que el usuario esté autenticado"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = self.obtener_usuario_actual()
            if not user:
                flash('Debes iniciar sesión para acceder a esta página', 'warning')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    def admin_required(self, f):
        """Decorador: Requiere que el usuario sea administrador"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = self.obtener_usuario_actual()
            if not user:
                flash('Debes iniciar sesión', 'warning')
                return redirect(url_for('login'))
            
            if not self.es_administrador(user.id):
                flash('No tienes permisos de administrador', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    
    # ============================================================================
    # GESTIÓN DE USUARIOS (Solo Administradores)
    # ============================================================================
    
    def listar_usuarios(self):
        """
        Lista todos los usuarios (solo administradores)
        
        Returns:
            list: Lista de usuarios
        """
        try:
            response = self.supabase.table('user_profiles').select('*').execute()
            return response.data
        except Exception as e:
            print(f"❌ Error listando usuarios: {e}")
            return []
    
    def cambiar_rol_usuario(self, user_id: str, nuevo_rol: str):
        """
        Cambia el rol de un usuario (solo administradores)
        
        Args:
            user_id: ID del usuario
            nuevo_rol: 'usuario' o 'administrador'
        
        Returns:
            bool: True si se cambió exitosamente
        """
        if nuevo_rol not in ['usuario', 'administrador']:
            return False
        
        try:
            self.supabase.table('user_profiles').update({
                'rol': nuevo_rol
            }).eq('id', user_id).execute()
            
            print(f"✅ Rol cambiado: {user_id} → {nuevo_rol}")
            return True
        except Exception as e:
            print(f"❌ Error cambiando rol: {e}")
            return False
    
    def desactivar_usuario(self, user_id: str):
        """
        Desactiva un usuario (solo administradores)
        
        Args:
            user_id: ID del usuario
        
        Returns:
            bool: True si se desactivó exitosamente
        """
        try:
            self.supabase.table('user_profiles').update({
                'activo': False
            }).eq('id', user_id).execute()
            
            print(f"✅ Usuario desactivado: {user_id}")
            return True
        except Exception as e:
            print(f"❌ Error desactivando usuario: {e}")
            return False
    
    # ============================================================================
    # EXPORTACIÓN DE DATOS
    # ============================================================================
    
    def exportar_datos_usuario(self, user_id: str = None):
        """
        Exporta todos los datos de un usuario en formato JSON
        
        Args:
            user_id: ID del usuario (si es None, usa el usuario actual)
        
        Returns:
            dict: Datos completos del usuario
        """
        try:
            if not user_id:
                current_user = self.obtener_usuario_actual()
                if not current_user:
                    return None
                user_id = current_user.id
            
            # Usar la función SQL que creamos
            response = self.supabase.rpc('exportar_datos_usuario', {'p_user_id': user_id}).execute()
            return response.data
        except Exception as e:
            print(f"❌ Error exportando datos: {e}")
            return None
    
    def obtener_estadisticas_usuario(self, user_id: str = None):
        """
        Obtiene estadísticas del usuario
        
        Args:
            user_id: ID del usuario (si es None, usa el usuario actual)
        
        Returns:
            dict: Estadísticas del usuario
        """
        try:
            if not user_id:
                current_user = self.obtener_usuario_actual()
                if not current_user:
                    return None
                user_id = current_user.id
            
            # Contar pacientes
            pacientes = self.supabase.table('pacientes').select('id', count='exact').eq('user_id', user_id).execute()
            
            # Contar diagnósticos
            diagnosticos = self.supabase.table('diagnosticos')\
                .select('id', count='exact')\
                .in_('paciente_id', 
                     self.supabase.table('pacientes').select('id').eq('user_id', user_id).execute().data
                ).execute()
            
            # Contar alertas críticas
            alertas = self.supabase.table('diagnosticos')\
                .select('id', count='exact')\
                .eq('alerta_critica', True)\
                .in_('paciente_id',
                     self.supabase.table('pacientes').select('id').eq('user_id', user_id).execute().data
                ).execute()
            
            return {
                'total_pacientes': pacientes.count,
                'total_diagnosticos': diagnosticos.count,
                'alertas_criticas': alertas.count
            }
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {e}")
            return {
                'total_pacientes': 0,
                'total_diagnosticos': 0,
                'alertas_criticas': 0
            }
    
    # ============================================================================
    # HELPERS PARA SESSION
    # ============================================================================
    
    def guardar_sesion_flask(self, user_data):
        """Guarda datos del usuario en la sesión de Flask"""
        session['user_id'] = user_data.id
        session['user_email'] = user_data.email
        session['access_token'] = user_data.session.access_token if hasattr(user_data, 'session') else None
    
    def limpiar_sesion_flask(self):
        """Limpia la sesión de Flask"""
        session.pop('user_id', None)
        session.pop('user_email', None)
        session.pop('access_token', None)
    
    def obtener_user_id_sesion(self):
        """Obtiene el user_id de la sesión de Flask"""
        return session.get('user_id')


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def hash_password(password: str) -> str:
    """Genera hash de contraseña (para uso local si se necesita)"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_password(password: str, hashed: str) -> bool:
    """Verifica una contraseña contra su hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


# ============================================================================
# PRUEBA DEL MÓDULO
# ============================================================================

if __name__ == "__main__":
    print("🔐 Sistema de Autenticación Dr Corazón")
    print("=" * 50)
    print("\nEste módulo debe usarse con supabase_config.py")
    print("\nEjemplo de uso:")
    print("""
from supabase_config import supabase
from auth_manager import AuthManager

# Crear gestor de autenticación
auth = AuthManager(supabase)

# Registrar usuario
auth.registrar_usuario(
    email='usuario@ejemplo.com',
    password='contraseña123',
    nombre_completo='Juan Pérez',
    rol='usuario'
)

# Login
session = auth.login('usuario@ejemplo.com', 'contraseña123')

# Verificar si es admin
es_admin = auth.es_administrador()

# Exportar datos
datos = auth.exportar_datos_usuario()
    """)
