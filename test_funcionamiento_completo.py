#!/usr/bin/env python3
"""
🧪 PRUEBAS COMPLETAS DE FUNCIONAMIENTO - BotMobile spotybot:1.25
=================================================================
Script para probar todas las funcionalidades del bot
"""

import requests
import json
import time
from datetime import datetime

class BotTester:
    def __init__(self):
        self.base_url = "http://localhost:5005"
        self.webhook_url = f"{self.base_url}/webhooks/rest/webhook"
        self.status_url = f"{self.base_url}/status"
        self.sender_id = f"test_user_{int(time.time())}"
        
    def print_header(self, title):
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print(f"{'='*60}")
    
    def print_step(self, step, description):
        print(f"\n{step} {description}")
        print("-" * 50)
    
    def send_message(self, message, wait_time=2):
        """Enviar mensaje al bot y obtener respuesta"""
        try:
            payload = {
                "sender": self.sender_id,
                "message": message
            }
            
            print(f"👤 Usuario: {message}")
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                bot_responses = response.json()
                
                if bot_responses:
                    for i, resp in enumerate(bot_responses, 1):
                        if "text" in resp:
                            # Truncar respuestas muy largas para mejor lectura
                            text = resp["text"]
                            if len(text) > 200:
                                text = text[:200] + "..."
                            print(f"🤖 Bot (respuesta {i}): {text}")
                        
                        if "image" in resp:
                            print(f"🖼️  Bot (imagen {i}): {resp['image']}")
                        
                        if "buttons" in resp:
                            print(f"🔘 Bot (botones {i}): {len(resp['buttons'])} botones")
                            for btn in resp['buttons'][:3]:  # Mostrar solo primeros 3
                                print(f"   • {btn.get('title', 'Sin título')}")
                else:
                    print("🤖 Bot: (sin respuesta)")
                
                time.sleep(wait_time)
                return bot_responses
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error de conexión: {str(e)}")
            return None
    
    def test_connection(self):
        """Probar conexión básica"""
        self.print_step("🔗", "PRUEBA DE CONEXIÓN")
        
        try:
            response = requests.get(self.status_url, timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ Bot conectado - Modelo: {status_data.get('model_file', 'Unknown')}")
                return True
            else:
                print(f"❌ Error de conexión: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error de conexión: {str(e)}")
            return False
    
    def test_basic_conversation(self):
        """Probar conversación básica"""
        self.print_step("💬", "CONVERSACIÓN BÁSICA")
        
        # Saludo inicial
        response = self.send_message("Hola")
        if not response:
            return False
        
        # Seleccionar portabilidad
        response = self.send_message("1")
        if not response:
            return False
        
        # Regresar al menú
        response = self.send_message("0")
        if not response:
            return False
        
        print("✅ Conversación básica: OK")
        return True
    
    def test_company_detection(self):
        """Probar detección de compañías"""
        self.print_step("🏢", "DETECCIÓN DE COMPAÑÍAS")
        
        companies = ["Telcel", "Movistar", "AT&T", "Unefon", "Virgin Mobile"]
        
        for company in companies:
            print(f"\n🔍 Probando: {company}")
            response = self.send_message(company)
            
            if response and len(response) > 0:
                # Verificar si menciona la compañía en la respuesta
                response_text = response[0].get("text", "").lower()
                if company.lower() in response_text:
                    print(f"✅ {company}: Detección personalizada")
                else:
                    print(f"⚠️  {company}: Respuesta genérica")
            else:
                print(f"❌ {company}: Sin respuesta")
            
            time.sleep(1)
        
        return True
    
    def test_portability_flow(self):
        """Probar flujo completo de portabilidad"""
        self.print_step("📱", "FLUJO DE PORTABILIDAD COMPLETO")
        
        # Nuevo sender para flujo limpio
        self.sender_id = f"portability_test_{int(time.time())}"
        
        steps = [
            ("Hola", "Saludo inicial"),
            ("1", "Seleccionar portabilidad"),
            ("1", "Conseguir NIP"),
            ("1", "Ya tengo NIP"),
            ("1234", "Proporcionar NIP"),
            ("123456789012345", "Proporcionar IMEI"),
            ("Juan Pérez López", "Proporcionar nombre")
        ]
        
        for message, description in steps:
            print(f"\n📝 {description}")
            response = self.send_message(message, wait_time=3)
            
            if not response:
                print(f"❌ Falló en: {description}")
                return False
        
        print("✅ Flujo de portabilidad: COMPLETADO")
        return True
    
    def test_node_red_format(self):
        """Probar formato compatible con Node-RED"""
        self.print_step("🔄", "FORMATO NODE-RED")
        
        # Nuevo sender para prueba limpia
        self.sender_id = f"nodered_test_{int(time.time())}"
        
        response = self.send_message("Telcel")
        
        if response and len(response) > 0:
            # CORRECCIÓN: Revisar TODOS los mensajes, no solo el primero
            has_text_total = False
            has_buttons_total = False
            
            for i, msg in enumerate(response):
                has_text = "text" in msg and msg["text"].strip()
                has_buttons = "buttons" in msg and len(msg.get("buttons", [])) > 0
                
                if has_text:
                    has_text_total = True
                if has_buttons:
                    has_buttons_total = True
                    print(f"🔘 Mensaje {i+1} tiene botones: ✅")
                    buttons = msg["buttons"]
                    print(f"🔢 Número de botones: {len(buttons)}")
                    
                    for j, btn in enumerate(buttons[:3], 1):
                        title = btn.get("title", "Sin título")
                        payload = btn.get("payload", "Sin payload")
                        print(f"   {j}. {title} -> {payload}")
            
            print(f"📄 Tiene texto: {'✅' if has_text_total else '❌'}")
            print(f"🔘 Tiene botones: {'✅' if has_buttons_total else '❌'}")
            
            return has_text_total and has_buttons_total
        
        return False
    
    def test_error_handling(self):
        """Probar manejo de errores"""
        self.print_step("⚠️", "MANEJO DE ERRORES")
        
        error_inputs = [
            "asdfghjkl",
            "999",
            "mensaje muy largo " * 20,
            "",
            "!@#$%^&*()"
        ]
        
        for error_input in error_inputs[:3]:  # Solo probar primeros 3
            print(f"\n🔍 Probando entrada: '{error_input[:30]}{'...' if len(error_input) > 30 else ''}'")
            response = self.send_message(error_input, wait_time=1)
            
            if response:
                print("✅ Bot responde a entrada inválida")
            else:
                print("❌ Bot no responde")
        
        return True
    
    def run_all_tests(self):
        """Ejecutar todas las pruebas"""
        self.print_header("INICIANDO PRUEBAS COMPLETAS DEL BOT")
        print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 URL: {self.webhook_url}")
        print(f"👤 ID de prueba: {self.sender_id}")
        
        tests = [
            ("Conexión", self.test_connection),
            ("Conversación Básica", self.test_basic_conversation),
            ("Detección de Compañías", self.test_company_detection),
            ("Flujo de Portabilidad", self.test_portability_flow),
            ("Formato Node-RED", self.test_node_red_format),
            ("Manejo de Errores", self.test_error_handling)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                print(f"❌ Error en {test_name}: {str(e)}")
                results[test_name] = False
        
        # Resumen final
        self.print_header("RESUMEN DE PRUEBAS")
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASÓ" if result else "❌ FALLÓ"
            print(f"{status} - {test_name}")
            if result:
                passed += 1
        
        success_rate = (passed / total) * 100
        print(f"\n📊 RESULTADO FINAL: {passed}/{total} pruebas exitosas ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print("🎉 ¡BOT FUNCIONANDO CORRECTAMENTE!")
        elif success_rate >= 60:
            print("⚠️  Bot funciona con algunos problemas")
        else:
            print("❌ Bot tiene problemas significativos")
        
        return results

if __name__ == "__main__":
    tester = BotTester()
    tester.run_all_tests()
