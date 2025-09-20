#!/usr/bin/env python3
"""
Script de prueba para verificar cómo Node-RED recibe los mensajes de Rasa
Simula la llamada que hace Node-RED al endpoint REST de Rasa
"""

import requests
import json
import time

def test_rasa_messages():
    """Prueba los mensajes de Rasa para verificar el formato Node-RED"""
    
    # URL del endpoint REST de Rasa
    url = "http://localhost:5005/webhooks/rest/webhook"
    
    # Configuración de headers
    headers = {
        "Content-Type": "application/json"
    }
    
    print("🚀 INICIANDO PRUEBAS DE MENSAJES PARA NODE-RED")
    print("=" * 50)
    
    # Test 1: Saludo inicial
    print("\n📝 TEST 1: Saludo inicial")
    payload1 = {
        "sender": "test_user_nodered", 
        "message": "Hola"
    }
    
    try:
        response1 = requests.post(url, json=payload1, headers=headers)
        if response1.status_code == 200:
            messages1 = response1.json()
            print(f"✅ Respuesta recibida ({len(messages1)} mensajes):")
            for i, msg in enumerate(messages1, 1):
                print(f"   Mensaje {i}: {json.dumps(msg, ensure_ascii=False, indent=2)}")
        else:
            print(f"❌ Error: {response1.status_code}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
    
    # Esperar un poco entre requests
    time.sleep(2)
    
    # Test 2: Opción de portabilidad (donde están nuestros cambios)
    print("\n📝 TEST 2: Opción de Portabilidad (mensajes separados)")
    payload2 = {
        "sender": "test_user_nodered", 
        "message": "1"
    }
    
    try:
        response2 = requests.post(url, json=payload2, headers=headers)
        if response2.status_code == 200:
            messages2 = response2.json()
            print(f"✅ Respuesta recibida ({len(messages2)} mensajes):")
            
            # Analizar cada mensaje para ver la estructura
            for i, msg in enumerate(messages2, 1):
                print(f"\n   📨 Mensaje {i}:")
                print(f"      Contenido: {json.dumps(msg, ensure_ascii=False, indent=6)}")
                
                # Verificar si hay texto largo sin separar
                if 'text' in msg:
                    text_content = msg['text']
                    if '/n' in text_content:
                        print(f"      ⚠️  PROBLEMA: Texto contiene '/n' sin separar")
                    if len(text_content) > 100:
                        print(f"      ⚠️  PROBLEMA: Texto muy largo ({len(text_content)} chars)")
                    else:
                        print(f"      ✅ Texto bien separado ({len(text_content)} chars)")
        else:
            print(f"❌ Error: {response2.status_code}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 PRUEBAS COMPLETADAS")

if __name__ == "__main__":
    # Esperar a que Rasa esté completamente cargado
    print("⏳ Esperando a que Rasa esté listo...")
    time.sleep(5)
    
    test_rasa_messages()
