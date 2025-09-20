#!/usr/bin/env python3
"""
Script de prueba DIRECTO para verificar cómo se separan los mensajes
Simula directamente las acciones para ver los dispatcher.utter_message() separados
"""

import sys
import os
sys.path.append(os.getcwd())

from actions.actions import ActionProcesarCompania, ActionElegirOpcion
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import REQUESTED_SLOT

class MockEvent:
    """Mock de evento para las pruebas"""
    def __init__(self, intent_name=None, text=None):
        self.intent_name = intent_name
        self.text = text

class MockTracker:
    """Mock de tracker para las pruebas"""
    def __init__(self, slots=None, latest_message=None):
        self.slots = slots or {}
        self.latest_message = latest_message or {}
        
    def get_slot(self, slot_name):
        return self.slots.get(slot_name)
    
    def get_latest_input_channel(self):
        return "rest"
    
    def get_latest_entity_values(self, entity_name):
        """Mock method para get_latest_entity_values"""
        if entity_name == "numero_opcion":
            # Simular extracción de número de la opción
            text = self.latest_message.get("text", "")
            if text == "1":
                yield "1"
            elif text == "2":
                yield "2"
            elif text == "3":
                yield "3"
            # No yield nada si no coincide

class TestingDispatcher(CollectingDispatcher):
    """Dispatcher personalizado para capturar mensajes separados"""
    
    def __init__(self):
        super().__init__()
        self.messages_sent = []
        self.total_messages = 0
    
    def utter_message(self, text=None, image=None, buttons=None, **kwargs):
        """Captura cada mensaje individual enviado"""
        self.total_messages += 1
        
        message_info = {
            'message_number': self.total_messages,
            'text': text,
            'image': image,
            'buttons': buttons,
            'kwargs': kwargs
        }
        
        self.messages_sent.append(message_info)
        
        # También llamar al método padre para mantener compatibilidad
        super().utter_message(text=text, image=image, buttons=buttons, **kwargs)
        
        print(f"📨 MENSAJE {self.total_messages}:")
        print(f"   Texto: {repr(text)}")
        if image:
            print(f"   Imagen: {image}")
        if buttons:
            print(f"   Botones: {len(buttons)} botones")
        print()

def test_message_separation():
    """Prueba la separación de mensajes en las acciones modificadas"""
    
    print("🚀 PRUEBA DIRECTA DE SEPARACIÓN DE MENSAJES")
    print("=" * 50)
    
    # Test 1: Saludo inicial con detección de compañía
    print("\n📝 TEST 1: Saludo inicial (ActionProcesarCompania)")
    dispatcher1 = TestingDispatcher()
    tracker1 = MockTracker(
        slots={"compania_detectada": "general"},
        latest_message={"text": "Hola"}
    )
    
    action1 = ActionProcesarCompania()
    result1 = action1.run(dispatcher1, tracker1, {})
    
    print(f"✅ Total de mensajes enviados: {dispatcher1.total_messages}")
    
    # Test 2: Opción de portabilidad (donde están nuestros cambios principales)
    print("\n📝 TEST 2: Opción Portabilidad (ActionElegirOpcion - opción '1')")
    dispatcher2 = TestingDispatcher()
    tracker2 = MockTracker(
        slots={"estado_menu": "menu_principal"},
        latest_message={"text": "1", "entities": [{"entity": "numero_opcion", "value": "1"}]}
    )
    
    action2 = ActionElegirOpcion()
    result2 = action2.run(dispatcher2, tracker2, {})
    
    print(f"✅ Total de mensajes enviados: {dispatcher2.total_messages}")
    
    # Análisis de resultados
    print("\n" + "="*50)
    print("📊 ANÁLISIS DE RESULTADOS")
    print("=" * 50)
    
    print(f"\n🔍 TEST 1 - Saludo inicial:")
    print(f"   Mensajes totales: {dispatcher1.total_messages}")
    for msg in dispatcher1.messages_sent:
        text_preview = msg['text'][:50] + "..." if msg['text'] and len(msg['text']) > 50 else msg['text']
        print(f"   - Mensaje {msg['message_number']}: {repr(text_preview)}")
    
    print(f"\n🔍 TEST 2 - Portabilidad (NUESTROS CAMBIOS):")
    print(f"   Mensajes totales: {dispatcher2.total_messages}")
    
    # Verificar si los mensajes están correctamente separados
    has_long_messages = False
    has_newline_issues = False
    
    for msg in dispatcher2.messages_sent:
        if msg['text']:
            text_len = len(msg['text'])
            has_newlines = '/n' in msg['text']
            
            text_preview = msg['text'][:50] + "..." if text_len > 50 else msg['text']
            print(f"   - Mensaje {msg['message_number']}: {repr(text_preview)} ({text_len} chars)")
            
            if text_len > 200:
                has_long_messages = True
                print(f"     ⚠️  PROBLEMA: Mensaje muy largo ({text_len} chars)")
            
            if has_newlines:
                has_newline_issues = True
                print(f"     ⚠️  PROBLEMA: Contiene '/n' no procesado")
            
            if text_len <= 100 and not has_newlines:
                print(f"     ✅ BIEN: Mensaje bien separado")
    
    # Resumen final
    print(f"\n🎯 RESUMEN FINAL:")
    if dispatcher2.total_messages >= 3:
        print("✅ ÉXITO: Los mensajes se están separando correctamente")
        print("✅ Node-RED recibirá elementos individuales en el array JSON")
    else:
        print("❌ PROBLEMA: Los mensajes aún no se están separando suficientemente")
    
    if has_long_messages:
        print("❌ PROBLEMA: Aún hay mensajes muy largos sin separar")
    else:
        print("✅ ÉXITO: No hay mensajes excesivamente largos")
    
    if has_newline_issues:
        print("❌ PROBLEMA: Aún hay caracteres '/n' sin procesar")
    else:
        print("✅ ÉXITO: No hay problemas de '/n' sin procesar")

if __name__ == "__main__":
    test_message_separation()
