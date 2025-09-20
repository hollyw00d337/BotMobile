#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de comprensión mejorada del bot
Prueba las nuevas funcionalidades de entendimiento
"""

import asyncio
import sys
import os

# Agregar el directorio actual al path
sys.path.append('.')

from rasa.core.agent import Agent

class TestComprensionMejorada:
    def __init__(self):
        self.agent = None
    
    async def cargar_modelo(self):
        """Cargar el modelo más reciente"""
        print("🤖 Cargando modelo...")
        try:
            # Buscar el modelo más reciente
            models_dir = "models"
            if os.path.exists(models_dir):
                models = [f for f in os.listdir(models_dir) if f.endswith('.tar.gz')]
                if models:
                    latest_model = sorted(models)[-1]
                    model_path = os.path.join(models_dir, latest_model)
                    print(f"📦 Cargando modelo: {latest_model}")
                    self.agent = Agent.load(model_path)
                    return True
        except Exception as e:
            print(f"❌ Error cargando modelo: {e}")
        return False

    async def test_comprension_basica(self):
        """Test básico de comprensión de números y opciones"""
        print("\n🔍 TEST 1: Comprensión Básica")
        print("=" * 40)
        
        tests = [
            ("1", "Número directo"),
            ("opción 1", "Opción con palabra"),
            ("primera", "Número en texto"),
            ("uno", "Número escrito"),
            ("1️⃣", "Emoji número"),
            ("quiero la primera opción", "Frase completa"),
        ]
        
        passed = 0
        for test_input, descripcion in tests:
            # El método handle_text devuelve una lista de mensajes
            result = await self.agent.handle_text(test_input)
            
            # Obtener datos de parsing del último mensaje procesado
            parse_data = await self.agent.parse_message(test_input)
            intent = parse_data.get('intent', {}).get('name', 'unknown')
            confidence = parse_data.get('intent', {}).get('confidence', 0)
            
            success = intent == "seleccionar_opcion" and confidence > 0.7
            status = "✅" if success else "❌"
            print(f"{status} {test_input:<20} | {descripcion:<15} | {intent} ({confidence:.2f})")
            
            if success:
                passed += 1
        
        print(f"\n📊 Resultado: {passed}/{len(tests)} tests pasados")
        return passed == len(tests)

    async def test_comprension_contextual(self):
        """Test de comprensión contextual avanzada"""
        print("\n🧠 TEST 2: Comprensión Contextual")
        print("=" * 40)
        
        tests = [
            ("quiero conservar mi número", "portabilidad_interes", "Portabilidad directa"),
            ("me interesa la portabilidad", "portabilidad_interes", "Portabilidad indirecta"),
            ("cuánto cuestan los planes", "planes_interes", "Planes por precio"),
            ("qué paquetes tienen", "planes_interes", "Planes directos"),
            ("quiero hablar con alguien", "contacto_interes", "Contacto directo"),
            ("necesito ayuda personal", "contacto_interes", "Contacto indirecto"),
        ]
        
        passed = 0
        for test_input, expected_intent, descripcion in tests:
            # Usar parse_message para obtener los datos de intención
            parse_data = await self.agent.parse_message(test_input)
            intent = parse_data.get('intent', {}).get('name', 'unknown')
            confidence = parse_data.get('intent', {}).get('confidence', 0)
            
            success = intent == expected_intent and confidence > 0.6
            status = "✅" if success else "❌"
            print(f"{status} {test_input:<25} | {descripcion:<15} | {intent} ({confidence:.2f})")
            
            if success:
                passed += 1
        
        print(f"\n📊 Resultado: {passed}/{len(tests)} tests pasados")
        return passed >= len(tests) * 0.8  # 80% de acierto mínimo

    async def test_fallback_inteligente(self):
        """Test del fallback inteligente"""
        print("\n🛡️ TEST 3: Fallback Inteligente")
        print("=" * 40)
        
        tests = [
            ("asdfgh", "Texto sin sentido"),
            ("no entiendo nada", "Expresión de confusión"),
            ("xyz 123", "Combinación aleatoria"),
        ]
        
        passed = 0
        for test_input, descripcion in tests:
            parse_data = await self.agent.parse_message(test_input)
            intent = parse_data.get('intent', {}).get('name', 'unknown')
            confidence = parse_data.get('intent', {}).get('confidence', 0)
            
            # El fallback debe activarse con baja confianza
            success = confidence < 0.7 or intent == "nlu_fallback"
            status = "✅" if success else "❌"
            print(f"{status} {test_input:<20} | {descripcion:<20} | {intent} ({confidence:.2f})")
            
            if success:
                passed += 1
        
        print(f"\n📊 Resultado: {passed}/{len(tests)} tests pasados")
        return passed >= len(tests) * 0.8

    async def test_deteccion_variaciones(self):
        """Test de detección de variaciones lingüísticas"""
        print("\n🎭 TEST 4: Variaciones Lingüísticas")
        print("=" * 40)
        
        tests = [
            ("si", "confirmar", "Confirmación simple"),
            ("sí por favor", "confirmar", "Confirmación cortés"),
            ("claro que sí", "confirmar", "Confirmación enfática"),
            ("no gracias", "negar", "Negación cortés"),
            ("mejor no", "negar", "Negación suave"),
            ("paso", "negar", "Negación coloquial"),
        ]
        
        passed = 0
        for test_input, expected_intent, descripcion in tests:
            parse_data = await self.agent.parse_message(test_input)
            intent = parse_data.get('intent', {}).get('name', 'unknown')
            confidence = parse_data.get('intent', {}).get('confidence', 0)
            
            success = intent == expected_intent and confidence > 0.6
            status = "✅" if success else "❌"
            print(f"{status} {test_input:<20} | {descripcion:<15} | {intent} ({confidence:.2f})")
            
            if success:
                passed += 1
        
        print(f"\n📊 Resultado: {passed}/{len(tests)} tests pasados")
        return passed >= len(tests) * 0.7

    async def ejecutar_tests(self):
        """Ejecutar todos los tests de comprensión"""
        print("🚀 INICIANDO TESTS DE COMPRENSIÓN MEJORADA")
        print("=" * 50)
        
        if not await self.cargar_modelo():
            print("❌ No se pudo cargar el modelo")
            return False
        
        print("✅ Modelo cargado exitosamente")
        
        # Ejecutar todos los tests
        results = []
        results.append(await self.test_comprension_basica())
        results.append(await self.test_comprension_contextual())
        results.append(await self.test_fallback_inteligente())
        results.append(await self.test_deteccion_variaciones())
        
        # Resultado final
        passed_tests = sum(results)
        total_tests = len(results)
        
        print(f"\n🎯 RESULTADO FINAL")
        print("=" * 30)
        print(f"Tests pasados: {passed_tests}/{total_tests}")
        
        if passed_tests >= total_tests * 0.8:
            print("🎉 ¡COMPRENSIÓN MEJORADA EXITOSA!")
            print("\n✅ Funcionalidades verificadas:")
            print("   • Detección mejorada de opciones")
            print("   • Comprensión contextual avanzada")
            print("   • Fallback inteligente")
            print("   • Variaciones lingüísticas")
            return True
        else:
            print("⚠️ Algunos tests fallaron")
            print("💡 Considera entrenar más el modelo")
            return False

async def main():
    tester = TestComprensionMejorada()
    await tester.ejecutar_tests()

if __name__ == "__main__":
    asyncio.run(main())
