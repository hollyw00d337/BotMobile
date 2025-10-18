"""
BotMobile - Consultas de Base de Datos
=====================================

Sistema de consultas para manejo de:
- Sesiones de navegador (usuarios_navegadores)
- Datos de portabilidad (usuarios)
- JOIN entre ambas tablas usando 'numero' como clave

Uso desde actions.py:
    from utils.business_queries import action_session_start, save_portability_data
    
    # Ejemplo SessionStart
    session_result = action_session_start(tracker.sender_id, user_id)
    
    # Ejemplo Portabilidad  
    portability_result = save_portability_data(numero, nip, imei, company, nameuser)

Autor: BotMobile Team
"""

from utils.database_connection import db_connection
import logging

logger = logging.getLogger(__name__)


# ==========================================
# 🌐 FUNCIONES DE SESIONES DE NAVEGADOR
# ==========================================

def get_browser_session(numero: str):
    """
    Obtiene información de sesión de navegador por número
    
    Args:
        numero: Número del usuario en el navegador
        
    Returns:
        Diccionario con info de la sesión o None
    """
    try:
        return db_connection.query_one("""
            SELECT 
                id,
                numero,
                user_id,
                last_used
            FROM usuarios_navegadores 
            WHERE numero = %s
            LIMIT 1
        """, (numero,))
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo sesión de navegador: {e}")
        return None


def create_browser_session(numero: str, user_id: str = None):
    """
    Crea una nueva sesión de navegador
    
    Args:
        numero: Número del usuario en el navegador
        user_id: ID del usuario (opcional)
        
    Returns:
        dict: Resultado de la operación
    """
    try:
        result = db_connection.execute("""
            INSERT INTO usuarios_navegadores (
                numero,
                user_id,
                last_used
            ) VALUES (%s, %s, NOW())
        """, (numero, user_id))
        
        if result > 0:
            # Obtener la sesión recién creada
            session = get_browser_session(numero)
            logger.info(f"✅ Sesión de navegador creada para número: {numero}")
            
            return {
                'success': True,
                'message': 'Sesión de navegador creada correctamente',
                'session': session,
                'action': 'created'
            }
        else:
            return {
                'success': False,
                'message': 'No se pudo crear la sesión de navegador',
                'session': None,
                'action': 'insert_failed'
            }
            
    except Exception as e:
        logger.error(f"❌ Error creando sesión de navegador: {e}")
        return {
            'success': False,
            'message': f'Error interno: {str(e)}',
            'session': None,
            'action': 'exception'
        }


def update_browser_session(numero: str, user_id: str = None):
    """
    Actualiza la sesión de navegador (principalmente last_used)
    
    Args:
        numero: Número del usuario en el navegador
        user_id: ID del usuario (opcional, para actualizar)
        
    Returns:
        dict: Resultado de la operación
    """
    try:
        # Construir query dinámicamente
        if user_id is not None:
            query = """
                UPDATE usuarios_navegadores 
                SET user_id = %s, last_used = NOW() 
                WHERE numero = %s
            """
            params = (user_id, numero)
        else:
            query = """
                UPDATE usuarios_navegadores 
                SET last_used = NOW() 
                WHERE numero = %s
            """
            params = (numero,)
        
        result = db_connection.execute(query, params)
        
        if result > 0:
            # Obtener la sesión actualizada
            session = get_browser_session(numero)
            logger.info(f"✅ Sesión de navegador actualizada para número: {numero}")
            
            return {
                'success': True,
                'message': 'Sesión de navegador actualizada correctamente',
                'session': session,
                'action': 'updated'
            }
        else:
            return {
                'success': False,
                'message': 'No se encontró la sesión para actualizar',
                'session': None,
                'action': 'not_found'
            }
            
    except Exception as e:
        logger.error(f"❌ Error actualizando sesión de navegador: {e}")
        return {
            'success': False,
            'message': f'Error interno: {str(e)}',
            'session': None,
            'action': 'exception'
        }


def action_session_start(numero: str, user_id: str = None):
    """
    FUNCIÓN PRINCIPAL: Maneja el inicio de sesión del bot de navegador
    
    Esta función implementa la lógica de actionsessionstart:
    1. Verifica si existe una sesión para el número
    2. Si existe, actualiza last_used (y opcionalmente user_id)
    3. Si no existe, crea nueva sesión
    
    Args:
        numero: Número del usuario en el navegador (requerido)
        user_id: ID del usuario (opcional)
        
    Returns:
        dict: Información completa de la sesión y acción realizada
    """
    try:
        logger.info(f"🚀 Iniciando sesión para número: {numero}")
        
        # Verificar si ya existe una sesión
        existing_session = get_browser_session(numero)
        
        if existing_session:
            # Sesión existe - actualizar
            result = update_browser_session(numero, user_id)
            result['previous_session'] = True
            logger.info(f"🔄 Sesión existente actualizada para número: {numero}")
        else:
            # Sesión no existe - crear nueva
            result = create_browser_session(numero, user_id)
            result['previous_session'] = False
            logger.info(f"🆕 Nueva sesión creada para número: {numero}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en action_session_start: {e}")
        return {
            'success': False,
            'message': f'Error interno en inicio de sesión: {str(e)}',
            'session': None,
            'action': 'exception',
            'previous_session': None
        }


def get_browser_sessions_by_user(user_id: str):
    """
    Obtiene todas las sesiones de navegador de un usuario
    
    Args:
        user_id: ID del usuario
        
    Returns:
        Lista de sesiones del usuario
    """
    try:
        return db_connection.query("""
            SELECT 
                id,
                numero,
                user_id,
                last_used
            FROM usuarios_navegadores 
            WHERE user_id = %s
            ORDER BY last_used DESC
        """, (user_id,))
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo sesiones del usuario: {e}")
        return []


def cleanup_old_browser_sessions(days_old: int = 30):
    """
    Limpia sesiones de navegador antiguas (opcional para mantenimiento)
    
    Args:
        days_old: Días de antigüedad para considerar una sesión como antigua
        
    Returns:
        dict: Resultado de la limpieza
    """
    try:
        result = db_connection.execute("""
            DELETE FROM usuarios_navegadores 
            WHERE last_used < NOW() - INTERVAL %s DAY
        """, (days_old,))
        
        logger.info(f"🧹 Limpieza completada: {result} sesiones antiguas eliminadas")
        
        return {
            'success': True,
            'message': f'Limpieza completada: {result} sesiones eliminadas',
            'deleted_count': result
        }
        
    except Exception as e:
        logger.error(f"❌ Error en limpieza de sesiones: {e}")
        return {
            'success': False,
            'message': f'Error en limpieza: {str(e)}',
            'deleted_count': 0
        }


# ==========================================
# 📞 FUNCIONES DE PORTABILIDAD
# ==========================================

def get_user_portability(numero: str):
    """
    Obtiene información de portabilidad de un usuario por número
    
    Args:
        numero: Número de teléfono del usuario
        
    Returns:
        dict: Información de portabilidad o None
    """
    try:
        return db_connection.query_one("""
            SELECT 
                numero,
                nip,
                imei,
                company,
                nameuser,
                created_at,
                updated_at
            FROM usuarios 
            WHERE numero = %s
            LIMIT 1
        """, (numero,))
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo portabilidad del usuario: {e}")
        return None


def create_user_portability(numero: str, nip: str, imei: str, company: str, nameuser: str):
    """
    Crea un nuevo registro de usuario con datos de portabilidad
    
    Args:
        numero: Número de teléfono del usuario
        nip: NIP de portabilidad
        imei: IMEI del dispositivo
        company: Compañía actual del usuario
        nameuser: Nombre del usuario
        
    Returns:
        dict: Resultado de la operación
    """
    try:
        result = db_connection.execute("""
            INSERT INTO usuarios (
                numero,
                nip,
                imei,
                company,
                nameuser,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
        """, (numero, nip, imei, company, nameuser))
        
        if result > 0:
            # Obtener el usuario recién creado
            new_user = get_user_portability(numero)
            logger.info(f"✅ Usuario de portabilidad creado: {numero}")
            
            return {
                'success': True,
                'message': 'Usuario de portabilidad creado correctamente',
                'user': new_user,
                'action': 'created'
            }
        else:
            return {
                'success': False,
                'message': 'No se pudo crear el usuario de portabilidad',
                'user': None,
                'action': 'insert_failed'
            }
            
    except Exception as e:
        logger.error(f"❌ Error creando usuario de portabilidad: {e}")
        return {
            'success': False,
            'message': f'Error interno: {str(e)}',
            'user': None,
            'action': 'exception'
        }


def update_user_portability(numero: str, nip: str = None, imei: str = None, 
                          company: str = None, nameuser: str = None):
    """
    Actualiza información de portabilidad de un usuario existente
    
    Args:
        numero: Número de teléfono del usuario
        nip: NIP de portabilidad (opcional)
        imei: IMEI del dispositivo (opcional)
        company: Compañía actual del usuario (opcional)
        nameuser: Nombre del usuario (opcional)
        
    Returns:
        dict: Resultado de la operación
    """
    try:
        # Verificar si el usuario existe
        if not get_user_portability(numero):
            return {
                'success': False,
                'message': 'Usuario de portabilidad no encontrado',
                'user': None,
                'action': 'not_found'
            }
        
        # Construir consulta dinámicamente solo con campos proporcionados
        updates = []
        params = []
        
        if nip is not None:
            updates.append("nip = %s")
            params.append(nip)
            
        if imei is not None:
            updates.append("imei = %s")
            params.append(imei)
            
        if company is not None:
            updates.append("company = %s")
            params.append(company)
            
        if nameuser is not None:
            updates.append("nameuser = %s")
            params.append(nameuser)
        
        if not updates:
            return {
                'success': False,
                'message': 'No hay campos para actualizar',
                'user': None,
                'action': 'no_changes'
            }
        
        # Agregar timestamp de actualización
        updates.append("updated_at = NOW()")
        params.append(numero)
        
        query = f"UPDATE usuarios SET {', '.join(updates)} WHERE numero = %s"
        result = db_connection.execute(query, params)
        
        if result > 0:
            updated_user = get_user_portability(numero)
            logger.info(f"✅ Usuario de portabilidad actualizado: {numero}")
            
            return {
                'success': True,
                'message': 'Usuario de portabilidad actualizado correctamente',
                'user': updated_user,
                'action': 'updated'
            }
        else:
            return {
                'success': False,
                'message': 'No se pudo actualizar el usuario de portabilidad',
                'user': None,
                'action': 'update_failed'
            }
        
    except Exception as e:
        logger.error(f"❌ Error actualizando usuario de portabilidad: {e}")
        return {
            'success': False,
            'message': f'Error interno: {str(e)}',
            'user': None,
            'action': 'exception'
        }


def save_portability_data(numero: str, nip: str, imei: str, company: str, nameuser: str):
    """
    FUNCIÓN PRINCIPAL: Guarda o actualiza datos de portabilidad del usuario
    
    Esta función implementa la lógica de llenar la tabla usuarios:
    1. Verifica si existe un usuario con ese número
    2. Si existe, actualiza los datos de portabilidad
    3. Si no existe, crea un nuevo registro
    
    Args:
        numero: Número de teléfono del usuario (clave primaria)
        nip: NIP de portabilidad
        imei: IMEI del dispositivo
        company: Compañía actual del usuario
        nameuser: Nombre del usuario
        
    Returns:
        dict: Información completa del resultado
    """
    try:
        logger.info(f"💾 Guardando datos de portabilidad para número: {numero}")
        
        # Verificar si ya existe el usuario
        existing_user = get_user_portability(numero)
        
        if existing_user:
            # Usuario existe - actualizar datos
            result = update_user_portability(numero, nip, imei, company, nameuser)
            result['previous_user'] = True
            logger.info(f"🔄 Datos de portabilidad actualizados para: {numero}")
        else:
            # Usuario no existe - crear nuevo
            result = create_user_portability(numero, nip, imei, company, nameuser)
            result['previous_user'] = False
            logger.info(f"🆕 Nuevo usuario de portabilidad creado: {numero}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en save_portability_data: {e}")
        return {
            'success': False,
            'message': f'Error interno guardando portabilidad: {str(e)}',
            'user': None,
            'action': 'exception',
            'previous_user': None
        }


def get_user_with_browser_session(numero: str):
    """
    Obtiene información completa del usuario con JOIN entre usuarios y usuarios_navegadores
    
    Args:
        numero: Número de teléfono del usuario (clave para el JOIN)
        
    Returns:
        dict: Información combinada de ambas tablas o None
    """
    try:
        return db_connection.query_one("""
            SELECT 
                u.numero,
                u.nip,
                u.imei,
                u.company,
                u.nameuser,
                u.created_at as user_created_at,
                u.updated_at as user_updated_at,
                un.id as browser_session_id,
                un.user_id as browser_user_id,
                un.last_used as last_browser_session
            FROM usuarios u
            LEFT JOIN usuarios_navegadores un ON u.numero = un.numero
            WHERE u.numero = %s
            LIMIT 1
        """, (numero,))
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo usuario con sesión de navegador: {e}")
        return None


def get_all_users_with_browser_sessions():
    """
    Obtiene todos los usuarios con sus sesiones de navegador asociadas
    
    Returns:
        list: Lista de usuarios con información de sesiones
    """
    try:
        return db_connection.query("""
            SELECT 
                u.numero,
                u.nip,
                u.imei,
                u.company,
                u.nameuser,
                u.created_at as user_created_at,
                u.updated_at as user_updated_at,
                un.id as browser_session_id,
                un.user_id as browser_user_id,
                un.last_used as last_browser_session
            FROM usuarios u
            LEFT JOIN usuarios_navegadores un ON u.numero = un.numero
            ORDER BY u.created_at DESC
        """)
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo usuarios con sesiones: {e}")
        return []


def validate_portability_data(numero: str, nip: str, imei: str, company: str, nameuser: str):
    """
    Valida los datos de portabilidad antes de guardar
    
    Args:
        numero: Número de teléfono
        nip: NIP de portabilidad
        imei: IMEI del dispositivo
        company: Compañía actual
        nameuser: Nombre del usuario
        
    Returns:
        dict: Resultado de la validación con errores específicos
    """
    errors = []
    warnings = []
    
    # Validar número de teléfono
    if not numero or numero.strip() == "":
        errors.append("Número de teléfono es requerido")
    elif len(numero.strip()) < 10:
        errors.append("Número de teléfono debe tener al menos 10 dígitos")
    elif not numero.strip().isdigit():
        errors.append("Número de teléfono debe contener solo números")
    
    # Validar NIP
    if not nip or nip.strip() == "":
        errors.append("NIP es requerido para la portabilidad")
    elif len(nip.strip()) < 4:
        errors.append("NIP debe tener al menos 4 caracteres")
    
    # Validar IMEI
    if not imei or imei.strip() == "":
        errors.append("IMEI del dispositivo es requerido")
    elif len(imei.strip()) != 15:
        warnings.append("IMEI típicamente tiene 15 dígitos")
    
    # Validar compañía
    if not company or company.strip() == "":
        errors.append("Compañía actual es requerida")
    elif len(company.strip()) < 2:
        errors.append("Nombre de compañía debe tener al menos 2 caracteres")
    
    # Validar nombre de usuario
    if not nameuser or nameuser.strip() == "":
        errors.append("Nombre del usuario es requerido")
    elif len(nameuser.strip()) < 2:
        errors.append("Nombre debe tener al menos 2 caracteres")
    elif len(nameuser.strip()) > 100:
        errors.append("Nombre no puede tener más de 100 caracteres")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


# ==========================================
# 🧪 FUNCIÓN DE PRUEBAS
# ==========================================

def test_database_functions():
    """
    Función para probar las funciones de base de datos implementadas
    """
    print("🧪 PROBANDO FUNCIONES DE BASE DE DATOS")
    print("=" * 50)
    
    try:
        from utils.database_connection import DatabaseConnection
        db = DatabaseConnection()
        
        # Probar conexión
        if db.test_connection():
            print("✅ Conexión a base de datos exitosa")
            
            # Probar funciones de sesión de navegador
            print("\n📱 Probando funciones de sesión de navegador...")
            test_numero = "test_browser_123"
            session_result = action_session_start(test_numero)
            print(f"Resultado sesión: {session_result.get('success', False)}")
            
            # Probar funciones de portabilidad
            print("\n📞 Probando funciones de portabilidad...")
            validation = validate_portability_data(
                numero="5512345678",
                nip="1234", 
                imei="123456789012345",
                company="Telcel",
                nameuser="Usuario Test"
            )
            print(f"Validación OK: {validation.get('valid', False)}")
            
            if validation.get('valid'):
                portability_result = save_portability_data(
                    numero="5512345678",
                    nip="1234", 
                    imei="123456789012345",
                    company="Telcel",
                    nameuser="Usuario Test"
                )
                print(f"Resultado portabilidad: {portability_result.get('success', False)}")
            
        else:
            print("❌ No hay conexión a base de datos")
            print("💡 Verifica la configuración de conexión")
            
    except Exception as e:
        print(f"❌ Error en pruebas: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_database_functions()