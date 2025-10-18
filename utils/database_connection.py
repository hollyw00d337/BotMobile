"""
BotMobile - Conexión Simple a PostgreSQL
========================================

Conexión minimalista para acceder a una base de datos PostgreSQL existente.
Solo necesitas configurar el endpoint en el archivo .env

Uso básico:
    from utils.database_connection import db_connection
    
    # Hacer una consulta
    result = db_connection.query("SELECT * FROM tu_tabla LIMIT 5")
    print(result)

Autor: BotMobile Team
Versión: 1.0
"""

import os
import logging
from typing import Optional, Dict, List, Any, Union
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()  # Carga el archivo .env automáticamente
except ImportError:
    print("⚠️ python-dotenv no disponible. Usando variables de entorno del sistema.")

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Conexión simple y directa a PostgreSQL.
    Se conecta a una base de datos existente usando variables de entorno.
    """
    
    def __init__(self):
        """Inicializa la conexión con parámetros del .env"""
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', 5432))
        self.database = os.getenv('DB_NAME', 'tu_base_datos')
        self.user = os.getenv('DB_USER', 'usuario')
        self.password = os.getenv('DB_PASSWORD', 'contraseña')
        
        # Configuración SSL (opcional)
        self.ssl_mode = os.getenv('DB_SSLMODE', 'prefer')
        
        logger.info(f"📊 Configuración DB: {self.user}@{self.host}:{self.port}/{self.database}")
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Parámetros de conexión para psycopg2"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'sslmode': self.ssl_mode
        }
    
    @contextmanager
    def get_connection(self):
        """Context manager para obtener una conexión"""
        conn = None
        try:
            conn = psycopg2.connect(**self.get_connection_params())
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Error de conexión: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def query(self, sql: str, params: tuple = None) -> List[Dict]:
        """
        Ejecuta una consulta SELECT y devuelve los resultados
        
        Args:
            sql: Consulta SQL (ej: "SELECT * FROM usuarios WHERE id = %s")
            params: Parámetros para la consulta (ej: (123,))
            
        Returns:
            Lista de diccionarios con los resultados
            
        Ejemplo:
            result = db_connection.query("SELECT * FROM usuarios WHERE activo = %s", (True,))
            for usuario in result:
                print(f"Usuario: {usuario['nombre']}")
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(sql, params)
                    results = cursor.fetchall()
                    
                    # Convertir a lista de diccionarios normales
                    return [dict(row) for row in results]
                    
        except Exception as e:
            logger.error(f"❌ Error ejecutando consulta: {e}")
            logger.error(f"SQL: {sql}")
            logger.error(f"Params: {params}")
            return []
    
    def query_one(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """
        Ejecuta una consulta y devuelve solo el primer resultado
        
        Args:
            sql: Consulta SQL
            params: Parámetros para la consulta
            
        Returns:
            Diccionario con el primer resultado o None
            
        Ejemplo:
            usuario = db_connection.query_one("SELECT * FROM usuarios WHERE id = %s", (123,))
            if usuario:
                print(f"Encontrado: {usuario['nombre']}")
        """
        results = self.query(sql, params)
        return results[0] if results else None
    
    def execute(self, sql: str, params: tuple = None) -> int:
        """
        Ejecuta una consulta INSERT, UPDATE o DELETE
        
        Args:
            sql: Consulta SQL
            params: Parámetros para la consulta
            
        Returns:
            Número de filas afectadas
            
        Ejemplo:
            affected = db_connection.execute(
                "UPDATE usuarios SET activo = %s WHERE id = %s", 
                (False, 123)
            )
            print(f"Se actualizaron {affected} registros")
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    return cursor.rowcount
                    
        except Exception as e:
            logger.error(f"❌ Error ejecutando comando: {e}")
            logger.error(f"SQL: {sql}")
            logger.error(f"Params: {params}")
            return 0
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión a la base de datos
        
        Returns:
            True si la conexión es exitosa
            
        Ejemplo:
            if db_connection.test_connection():
                print("✅ Conexión exitosa")
            else:
                print("❌ No se pudo conectar")
        """
        try:
            result = self.query_one("SELECT 1 as test")
            return result is not None and result.get('test') == 1
        except Exception as e:
            logger.error(f"❌ Test de conexión fallido: {e}")
            return False
    
    def get_tables(self) -> List[str]:
        """
        Obtiene la lista de tablas en la base de datos
        
        Returns:
            Lista con nombres de tablas
            
        Ejemplo:
            tablas = db_connection.get_tables()
            print(f"Tablas disponibles: {tablas}")
        """
        try:
            results = self.query("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            return [row['table_name'] for row in results]
        except Exception as e:
            logger.error(f"❌ Error obteniendo tablas: {e}")
            return []
    
    def describe_table(self, table_name: str) -> List[Dict]:
        """
        Obtiene la estructura de una tabla
        
        Args:
            table_name: Nombre de la tabla
            
        Returns:
            Lista con información de las columnas
            
        Ejemplo:
            columnas = db_connection.describe_table("usuarios")
            for col in columnas:
                print(f"Columna: {col['column_name']} - Tipo: {col['data_type']}")
        """
        try:
            return self.query("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns 
                WHERE table_name = %s 
                  AND table_schema = 'public'
                ORDER BY ordinal_position
            """, (table_name,))
        except Exception as e:
            logger.error(f"❌ Error describiendo tabla {table_name}: {e}")
            return []


# Instancia global para usar en toda la aplicación
db_connection = DatabaseConnection()


def get_database_info() -> Dict[str, Any]:
    """
    Obtiene información general de la base de datos
    
    Returns:
        Diccionario con información de la BD
        
    Ejemplo:
        info = get_database_info()
        print(f"Estado: {info['status']}")
        print(f"Tablas: {info['tables']}")
    """
    try:
        if not db_connection.test_connection():
            return {
                'status': 'disconnected',
                'error': 'No se pudo conectar a la base de datos'
            }
        
        tables = db_connection.get_tables()
        
        return {
            'status': 'connected',
            'host': db_connection.host,
            'database': db_connection.database,
            'tables_count': len(tables),
            'tables': tables
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


if __name__ == "__main__":
    """
    Test de la conexión cuando se ejecuta directamente
    
    Para probar: python utils/database_connection.py
    """
    print("🔍 Probando conexión a PostgreSQL...")
    print("=" * 40)
    
    # Test básico de conexión
    if db_connection.test_connection():
        print("✅ Conexión exitosa!")
        
        # Mostrar información de la BD
        info = get_database_info()
        print(f"📊 Base de datos: {info.get('database')}")
        print(f"🏠 Host: {info.get('host')}")
        print(f"📋 Tablas encontradas: {info.get('tables_count', 0)}")
        
        # Mostrar primeras 5 tablas
        tables = info.get('tables', [])
        if tables:
            print("\n📝 Tablas disponibles:")
            for table in tables[:5]:
                print(f"   • {table}")
            if len(tables) > 5:
                print(f"   ... y {len(tables) - 5} más")
        
    else:
        print("❌ No se pudo conectar")
        print("💡 Verifica tu configuración en el archivo .env:")
        print("   - DB_HOST")
        print("   - DB_PORT")
        print("   - DB_NAME")
        print("   - DB_USER")
        print("   - DB_PASSWORD")