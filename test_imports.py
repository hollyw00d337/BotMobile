#!/usr/bin/env python3
"""
Script de diagnóstico de importaciones
"""

import sys
import os

# Agregar el directorio actual al path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("🔍 Diagnóstico de importaciones")
print(f"📁 Directorio actual: {current_dir}")
print(f"🐍 Python path: {sys.path[:3]}...")

# Verificar estructura de directorios
print("\n📂 Estructura de archivos:")
if os.path.exists('utils'):
    print("✅ Carpeta 'utils' existe")
    utils_files = os.listdir('utils')
    print(f"   Archivos en utils: {utils_files}")
    
    if '__init__.py' in utils_files:
        print("✅ utils/__init__.py existe")
    else:
        print("❌ utils/__init__.py NO existe")
        
    if 'business_queries.py' in utils_files:
        print("✅ utils/business_queries.py existe")
    else:
        print("❌ utils/business_queries.py NO existe")
else:
    print("❌ Carpeta 'utils' NO existe")

# Intentar importación
print("\n🧪 Probando importaciones:")
try:
    from utils.business_queries import action_session_start
    print("✅ Importación exitosa: action_session_start")
    print(f"   Tipo: {type(action_session_start)}")
    print(f"   Es función: {callable(action_session_start)}")
except ImportError as e:
    print(f"❌ Error de importación: {e}")
except Exception as e:
    print(f"❌ Error inesperado: {e}")

# Verificar config también
try:
    from config.image_config import ImageConfig
    print("✅ Importación exitosa: ImageConfig")
except ImportError as e:
    print(f"❌ Error importando ImageConfig: {e}")

print("\n🏁 Diagnóstico completado")