# crear_admin.py - Script para crear el primer usuario administrador
from supabase_config import supabase
from auth_manager import AuthManager

def crear_administrador():
    """Crea el primer usuario administrador"""
    auth = AuthManager(supabase)
    
    print("=" * 60)
    print("🔐 CREAR USUARIO ADMINISTRADOR - Dr Corazón")
    print("=" * 60)
    print()
    
    email = input("Email del administrador: ")
    password = input("Contraseña (mínimo 6 caracteres): ")
    nombre_completo = input("Nombre completo: ")
    
    print("\nCreando administrador...")
    
    user = auth.registrar_usuario(
        email=email,
        password=password,
        nombre_completo=nombre_completo,
        rol='administrador'  # ¡Importante!
    )
    
    if user:
        print("\n✅ ¡Administrador creado exitosamente!")
        print(f"   Email: {email}")
        print(f"   Nombre: {nombre_completo}")
        print(f"   Rol: administrador")
        print("\nYa puedes iniciar sesión en: http://localhost:5000/login")
    else:
        print("\n❌ Error al crear administrador")
        print("Verifica que:")
        print("  - El email no esté ya registrado")
        print("  - La contraseña tenga al menos 6 caracteres")
        print("  - Supabase Auth esté habilitado")

def crear_usuario_normal():
    """Crea un usuario normal"""
    auth = AuthManager(supabase)
    
    print("=" * 60)
    print("👤 CREAR USUARIO NORMAL - Dr Corazón")
    print("=" * 60)
    print()
    
    email = input("Email: ")
    password = input("Contraseña (mínimo 6 caracteres): ")
    nombre_completo = input("Nombre completo: ")
    
    print("\nCreando usuario...")
    
    user = auth.registrar_usuario(
        email=email,
        password=password,
        nombre_completo=nombre_completo,
        rol='usuario'  # Usuario normal
    )
    
    if user:
        print("\n✅ ¡Usuario creado exitosamente!")
        print(f"   Email: {email}")
        print(f"   Nombre: {nombre_completo}")
        print(f"   Rol: usuario")
        print("\nYa puede iniciar sesión en: http://localhost:5000/login")
    else:
        print("\n❌ Error al crear usuario")

def menu():
    """Menú principal"""
    while True:
        print("\n" + "=" * 60)
        print("🏥 Dr Corazón - Gestión de Usuarios")
        print("=" * 60)
        print("1. Crear administrador")
        print("2. Crear usuario normal")
        print("3. Listar usuarios existentes")
        print("4. Salir")
        print()
        
        opcion = input("Selecciona una opción: ")
        
        if opcion == "1":
            crear_administrador()
        elif opcion == "2":
            crear_usuario_normal()
        elif opcion == "3":
            listar_usuarios()
        elif opcion == "4":
            print("👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción inválida")

def listar_usuarios():
    """Lista todos los usuarios"""
    auth = AuthManager(supabase)
    
    print("\n" + "=" * 60)
    print("📋 USUARIOS REGISTRADOS")
    print("=" * 60)
    
    usuarios = auth.listar_usuarios()
    
    if not usuarios:
        print("No hay usuarios registrados aún.")
        return
    
    for user in usuarios:
        print(f"\n📧 {user['email']}")
        print(f"   Nombre: {user['nombre_completo']}")
        print(f"   Rol: {user['rol']}")
        print(f"   Activo: {'Sí' if user['activo'] else 'No'}")
        print(f"   Creado: {user['created_at']}")

if __name__ == "__main__":
    print("\n🫀 Dr Corazón - Sistema de Gestión de Usuarios")
    print("\nEste script te ayudará a crear usuarios en el sistema.\n")
    
    try:
        menu()
    except KeyboardInterrupt:
        print("\n\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nAsegúrate de:")
        print("  1. Haber ejecutado migracion_autenticacion.sql en Supabase")
        print("  2. Tener supabase_config.py correctamente configurado")
        print("  3. Haber habilitado Email Auth en Supabase Dashboard")
