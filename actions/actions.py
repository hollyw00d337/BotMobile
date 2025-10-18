from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from config.image_config import ImageConfig
from utils.business_queries import action_session_start
import logging
import re
import requests
import json

logger = logging.getLogger(__name__)


class ActionSessionStart(Action):
    """Acción customizada para iniciar la sesión.
    Esta acción reemplaza la action_session_start por defecto de Rasa.
    """
    
    def name(self) -> Text:
        return "action_session_start"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        print(f"[DEBUG ActionSessionStart] INICIANDO SESIÓN")
        print(f"[DEBUG ActionSessionStart] tracker.latest_message: {tracker.latest_message}")
        
        # Enviar imagen de bienvenida
        dispatcher.utter_message(image=ImageConfig.BIENVENIDA_BOTMOBILE)
        
        # Buscar si el mensaje inicial es de Node-RED
        mensaje_texto = None
        
        # 1. Buscar en latest_message
        if tracker.latest_message:
            mensaje_texto = tracker.latest_message.get('text', None)
            print(f"[DEBUG ActionSessionStart] Texto de latest_message: '{mensaje_texto}'")
        
        # 2. Si no se encuentra, buscar en eventos
        if not mensaje_texto:
            print(f"[DEBUG ActionSessionStart] Buscando en eventos del tracker...")
            print(f"[DEBUG ActionSessionStart] Total de eventos: {len(tracker.events)}")
            for i, event in enumerate(tracker.events):
                print(f"[DEBUG ActionSessionStart] Evento {i}: {event.get('event', 'unknown')} - {event.get('text', '')}")
                if event.get('event') == 'user' and event.get('text'):
                    mensaje_texto = event.get('text')
                    print(f"[DEBUG ActionSessionStart] ✅ Encontrado en eventos: '{mensaje_texto}'")
                    break
        
        # 3. NUEVA ESTRATEGIA: Buscar en el tracker completo de formas adicionales
        if not mensaje_texto:
            print(f"[DEBUG ActionSessionStart] BÚSQUEDA AVANZADA...")
            # Buscar en el sender_id o cualquier metadata que pueda contener el mensaje
            if hasattr(tracker, 'sender_id'):
                print(f"[DEBUG ActionSessionStart] Sender ID: {tracker.sender_id}")
            
            # Buscar en los últimos eventos de tipo diferente
            for event in reversed(tracker.events[-10:]):  # Últimos 10 eventos
                event_type = event.get('event')
                print(f"[DEBUG ActionSessionStart] Revisando evento: {event_type} -> {event}")
                
                if 'text' in event and event['text']:
                    mensaje_texto = event['text'] 
                    print(f"[DEBUG ActionSessionStart] ✅ Texto encontrado en evento {event_type}: '{mensaje_texto}'")
                    break
        
        if mensaje_texto:
            print(f"[DEBUG ActionSessionStart] ✅ Procesando mensaje: '{mensaje_texto}'")
            
            # Verificar si es mensaje de Node-RED
            if self._es_mensaje_node_red(mensaje_texto):
                print(f"[DEBUG ActionSessionStart] ✅ MENSAJE DE NODE-RED DETECTADO")
                
                # Extraer compañía
                compania_detectada = self._extraer_compania(mensaje_texto)
                if compania_detectada:
                    # **NUEVO**: Crear mensaje personalizado con botones para Node-RED
                    self._enviar_mensaje_personalizado_con_botones(dispatcher, compania_detectada)
                    
                    slots_to_set = [
                        SlotSet("compania_operador", compania_detectada),
                        SlotSet("estado_menu", "menu_principal"),
                        SlotSet("session_started", True)
                    ]
                    
                    # Extraer número si existe
                    numero_match = re.search(r'NUMERO\s+(\d+)', mensaje_texto.upper())
                    if numero_match:
                        numero = numero_match.group(1)
                        slots_to_set.append(SlotSet("numero_telefono", numero))
                        print(f"[DEBUG ActionSessionStart] ✅ Número extraído: {numero}")
                    
                    return slots_to_set
        
        print(f"[DEBUG ActionSessionStart] ❌ Mensaje normal o sin compañía, usando saludo genérico")
        
        # **INTEGRACIÓN NODE-RED**: Saludo genérico con formato compatible con botones
        mensaje_menu = """👋 ¡Hola! Soy BotMobile, tu asistente móvil ☕
Estoy aquí para ayudarte a conectarte fácil, rápido y sin interrucciones 📶

📦 Tenemos paquetes para todos los usos, con cobertura nacional.
Elige entre chip físico o eSIM, ¡y hazlo todo desde aquí!

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares.

☕ ¡Vamos a hacerlo simple! Selecciona la opción que necesitas."""
        
        # **CORRECCIÓN NODE-RED**: Enviar un solo mensaje con texto + botones
        dispatcher.utter_message(
            text=mensaje_menu,
            buttons=[
                {"title": "1️⃣ Conservar mi número (portabilidad).", "payload": "1"},
                {"title": "2️⃣ Ver paquetes disponibles.", "payload": "2"},
                {"title": "3️⃣ Hablar con alguien del equipo.", "payload": "3"},
                {"title": "4️⃣ Recargas celulares.", "payload": "4"}
            ]
        )
        
        # **NUEVO**: Registrar sesión de navegador en la base de datos
        try:
            # Obtener número del usuario (sender_id o del mensaje)
            numero_navegador = tracker.sender_id
            
            # Si se extrajo un número del mensaje, usarlo como user_id
            user_id = tracker.get_slot("numero_telefono")
            
            print(f"[DEBUG ActionSessionStart] 📊 Registrando sesión: numero={numero_navegador}, user_id={user_id}")
            
            # Llamar a la función de inicio de sesión
            session_result = action_session_start(numero_navegador, user_id)
            
            if session_result.get('success'):
                session_info = session_result.get('session', {})
                is_returning = session_result.get('previous_session', False)
                
                print(f"[DEBUG ActionSessionStart] ✅ Sesión registrada: ID={session_info.get('id')}, "
                      f"Returning={is_returning}, Last_used={session_info.get('last_used')}")
                
                # Agregar información de sesión a los slots
                additional_slots = [
                    SlotSet("browser_session_id", session_info.get('id')),
                    SlotSet("is_returning_user", is_returning),
                    SlotSet("last_session", str(session_info.get('last_used', '')))
                ]
                
                return [
                    SlotSet("estado_menu", "menu_principal"),
                    SlotSet("session_started", True)
                ] + additional_slots
                
            else:
                print(f"[DEBUG ActionSessionStart] ⚠️ Error en sesión: {session_result.get('message')}")
                
        except Exception as e:
            print(f"[DEBUG ActionSessionStart] ❌ Error registrando sesión: {e}")
            # Continuar sin fallar si hay problemas con la BD
        
        return [
            SlotSet("estado_menu", "menu_principal"),
            SlotSet("session_started", True)
        ]
    
    def _es_mensaje_node_red(self, texto: str) -> bool:
        """
        Detecta si el mensaje proviene de Node-RED usando los patrones EXACTOS
        del código que me enviaste.
        """
        if not texto:
            return False
            
        texto_upper = texto.upper()
        
        # **PATRONES EXACTOS DEL NODE-RED ORIGINAL**
        # Basado en tu función24 original
        patrones_node_red = [
            # Formato: "COMPANIA_DETECTADA TELCEL"
            r'COMPANIA_DETECTADA\s+[A-Z&]+',
            
            # Formato: "OPERATOR TELCEL NUMERO 5512345678"
            r'OPERATOR\s+[A-Z&]+(\s+NUMERO\s+\d+)?',
            
            # Formato: "TELCEL NUMERO 5512345678" 
            r'(TELCEL|MOVISTAR|AT&T|UNEFON|VIRGIN|ALTAN)\s+(NUMERO\s+\d+)?',
            
            # Formato directo del operador
            r'^(TELCEL|MOVISTAR|AT&T|UNEFON|VIRGIN|ALTAN)$'
        ]
        
        for patron in patrones_node_red:
            if re.search(patron, texto_upper):
                print(f"[DEBUG] ✅ Patrón Node-RED detectado: {patron} en '{texto_upper}'")
                return True
        
        # **FORMATO NODE-RED ACTUAL**: nombres formateados de la base de datos
        # Lista de operadores válidos según el mapeo de function 28
        operadores_validos = {
            'Telcel', 'Movistar', 'AT&T', 'Unefon', 'Virgin', 'Altan', 'CFE', 'Walmart',
            'Quickly', 'Ibo Cell', 'Tel 360', 'Kubo', 'Virgin Mobile', 'Telecommerce',
            'MVH', 'Neus', 'Truu', 'Celmex', 'Eja', 'Logistica', 'Her', 'Comnet', 'Marduk',
            'Freedom', 'Hidalguense', 'Mobilebandits', 'Hip Cricket', 'Moluger', 'Altcel',
            'Inbtel', 'AINT', 'Islim', 'Airbus', 'Clearcom', 'Gurucomm', 'MBT', 'RTM',
            'Esmero', 'Talento', 'Oxio', 'Rocketel', 'Ads', 'Arloesi', 'Diri', 'Topos',
            'Wimo', 'Diveracy', 'Tridex', 'Exis', 'Ome', 'Edilar', 'Novavision', 'Guga',
            'Absoluteteck', 'Yonder', 'Cobranza', 'Tritium', 'Afcaza', 'Balesia', 'Rosa',
            'Telmov', 'Marketing', 'Bitelit', 'Orange', 'R&R', 'Viral', 'Oceannet',
            'Element', 'Broco', 'Allesklar', 'Lider', 'Secure', 'Gameplanet', 'Axios',
            'Celsfi', 'Maya', 'Telexes', 'Cambacel', 'Pantera', 'Othis', 'Femaseisa',
            'Alcance', 'Francisco', 'Valor', 'Pajal', 'Speednet', 'Liimaxtum', 'Yaqui',
            'Rex', 'Saavedra', 'Negocios', 'Nexbus', 'King', 'Bene', 'Elux', 'Igou',
            'Voztelecom', 'Abafon', 'Romel', 'Celmax', 'Alestra', 'VPN', 'Maxcom',
            'IENTC', 'OpenIP', 'Operbes', 'Cablevision', 'Plintron', 'Sev Tronc',
            'Megacable', 'Vasanta', 'Inten', 'Next', 'Guadiana', 'Solucionika', 'Abix',
            'Girnet', 'Fobos', 'Unet', 'Plasma', 'Tu Visión', 'Tele Imagen', 'Telgen',
            'Ultravision', 'Trends', 'Apco', 'Spot Uno', 'Uriel', 'Eni', 'At&t',
            'AXTEL', 'Convergia', 'Servnet', 'Vinoc', 'TELCEL' ,
        }
        
        if texto.strip() in operadores_validos:
            print(f"[DEBUG] ✅ Operador Node-RED válido detectado: '{texto}'")
            return True
        
        return False
    
    def _extraer_compania(self, texto: str) -> str:
        """Extrae la compañía del mensaje Node-RED"""
        texto_upper = texto.upper()
        
        # Mapeo de variaciones de nombres a nombres estándar
        mapeo_companias = {
            'TELCEL': 'Telcel',
            'MOVISTAR': 'Movistar',
            'AT&T': 'AT&T',
            'ATT': 'AT&T',
            'UNEFON': 'Unefon',
            'VIRGIN': 'Virgin Mobile',
            'VIRGIN MOBILE': 'Virgin Mobile',
            'ALTAN': 'Altan Redes'
        }
        
        # **NUEVO**: Si el texto es exactamente un nombre de operador, devolverlo directamente
        texto_limpio = texto.strip()
        if texto_limpio in mapeo_companias.values():
            print(f"[DEBUG] ✅ Operador directo detectado: '{texto_limpio}'")
            return texto_limpio
        
        # Patrones para detectar compañías en mensajes estructurados
        patterns = [
            r'COMPANIA_DETECTADA\s+(\w+)',
            r'OPERATOR\s+(TELCEL|MOVISTAR|AT&T|ATT|UNEFON|VIRGIN|ALTAN)',
            r'(TELCEL|MOVISTAR|AT&T|ATT|UNEFON|VIRGIN|ALTAN)(?:\s+NUMERO)?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texto_upper)
            if match:
                compania_raw = match.group(1)
                resultado = mapeo_companias.get(compania_raw, compania_raw.capitalize())
                print(f"[DEBUG] ✅ Operador extraído de patrón: '{resultado}'")
                return resultado
        
        # **NUEVO**: Búsqueda directa en la lista de operadores válidos
        # (para nombres que vienen exactamente como en la base de datos)
        operadores_validos = [
            'Telcel', 'Movistar', 'AT&T', 'Unefon', 'Virgin', 'Altan', 'CFE', 'Walmart',
            'Quickly', 'Ibo Cell', 'Tel 360', 'Kubo', 'Virgin Mobile', 'Telecommerce',
            'MVH', 'Neus', 'Truu', 'Celmex', 'Eja', 'Logistica', 'Her', 'Comnet', 'Marduk',
            'Freedom', 'Hidalguense', 'Mobilebandits', 'Hip Cricket', 'Moluger', 'Altcel',
            'Inbtel', 'AINT', 'Islim', 'Airbus', 'Clearcom', 'Gurucomm', 'MBT', 'RTM',
            'Esmero', 'Talento', 'Oxio', 'Rocketel', 'Ads', 'Arloesi', 'Diri', 'Topos',
            'Wimo', 'Diveracy', 'Tridex', 'Exis', 'Ome', 'Edilar', 'Novavision', 'Guga',
            'Absoluteteck', 'Yonder', 'Cobranza', 'Tritium', 'Afcaza', 'Balesia', 'Rosa',
            'Telmov', 'Marketing', 'Bitelit', 'Orange', 'R&R', 'Viral', 'Oceannet',
            'Element', 'Broco', 'Allesklar', 'Lider', 'Secure', 'Gameplanet', 'Axios',
            'Celsfi', 'Maya', 'Telexes', 'Cambacel', 'Pantera', 'Othis', 'Femaseisa',
            'Alcance', 'Francisco', 'Valor', 'Pajal', 'Speednet', 'Liimaxtum', 'Yaqui',
            'Rex', 'Saavedra', 'Negocios', 'Nexbus', 'King', 'Bene', 'Elux', 'Igou',
            'Voztelecom', 'Abafon', 'Romel', 'Celmax', 'Alestra', 'VPN', 'Maxcom',
            'IENTC', 'OpenIP', 'Operbes', 'Cablevision', 'Plintron', 'Sev Tronc',
            'Megacable', 'Vasanta', 'Inten', 'Next', 'Guadiana', 'Solucionika', 'Abix',
            'Girnet', 'Fobos', 'Unet', 'Plasma', 'Tu Visión', 'Tele Imagen', 'Telgen',
            'Ultravision', 'Trends', 'Apco', 'Spot Uno', 'Uriel', 'Eni', 'At&t',
            'AXTEL', 'Convergia', 'Servnet', 'Vinoc'
        ]
        
        if texto_limpio in operadores_validos:
            print(f"[DEBUG] ✅ Operador válido de base de datos: '{texto_limpio}'")
            return texto_limpio
        
        print(f"[DEBUG] ❌ No se pudo extraer operador de: '{texto}'")
        return None
    
    def _crear_mensaje_personalizado_con_menu(self, compania: str) -> str:
        """Crea mensaje personalizado con menú incluido"""
        
        mensajes_por_compania = {
            'Telcel': """
🔴 ¡Hola usuario de Telcel! 
Veo que vienes de la red más grande de México 📶

Con BotMobile puedes cambiar tu chip Telcel por uno nuestro y mantener tu mismo número, pero con mejores beneficios:

✅ Cobertura nacional garantizada
✅ Paquetes más económicos 
✅ Atención 24/7
✅ Sin permanencia

👇 ¿Qué quieres hacer?

1️⃣ Conservar mi número Telcel (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares

💡 La portabilidad desde Telcel es súper fácil y rápida.
            """,
            'Movistar': """
🔵 ¡Hola usuario de Movistar! 
Te damos la bienvenida desde la red azul 📶

Con BotMobile puedes traer tu número de Movistar y disfrutar de mejores beneficios:

✅ Cobertura nacional completa
✅ Planes más flexibles
✅ Sin ataduras ni permanencia
✅ Mejor atención al cliente

👇 ¿Qué necesitas?

1️⃣ Conservar mi número Movistar (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares

💡 El cambio desde Movistar es simple y sin complicaciones.
            """,
            'AT&T': """
🟠 ¡Hola usuario de AT&T! 
Veo que vienes de la red naranja 📶

Con BotMobile puedes migrar desde AT&T manteniendo tu número y obteniendo:

✅ Mejor relación precio-beneficio
✅ Cobertura nacional sólida
✅ Planes sin letra pequeña
✅ Portabilidad express

👇 ¿Qué te interesa?

1️⃣ Conservar mi número AT&T (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares

💡 Cambiar desde AT&T es rápido y mantienes tu número.
            """,
            'Unefon': """
🟢 ¡Hola usuario de Unefon! 
Te reconocemos de la red verde 📶

Con BotMobile puedes traer tu número de Unefon y conseguir:

✅ Mejor cobertura nacional
✅ Paquetes más competitivos
✅ Sin restricciones de permanencia  
✅ Servicio premium

👇 ¿Qué buscas?

1️⃣ Conservar mi número Unefon (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares

💡 La migración desde Unefon es sencilla y rápida.
            """,
            'Virgin Mobile': """
🔴 ¡Hola usuario de Virgin Mobile! 
Vemos que vienes de la marca joven 📶

Con BotMobile puedes evolucionar desde Virgin Mobile obteniendo:

✅ Cobertura más amplia
✅ Mejores tarifas
✅ Flexibilidad total  
✅ Sin complicaciones

👇 ¿Qué prefieres?

1️⃣ Conservar mi número Virgin (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares

💡 El cambio desde Virgin Mobile es directo y simple.
            """,
            'Altan Redes': """
⚪ ¡Hola usuario de Altan! 
Reconocemos tu red actual 📶

Con BotMobile puedes migrar desde Altan manteniendo tu número y accediendo a:

✅ Cobertura nacional optimizada
✅ Planes más accesibles
✅ Mejor experiencia de usuario
✅ Soporte dedicado

👇 ¿Qué necesitas?

1️⃣ Conservar mi número Altan (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares

💡 La portabilidad desde Altan es directa y eficiente.
            """
        }
        
        return mensajes_por_compania.get(compania, f"""
👋 ¡Hola usuario de {compania}! 
Te damos la bienvenida a BotMobile 📶

Puedes conservar tu número actual y disfrutar de nuestros beneficios:

✅ Cobertura nacional
✅ Mejores tarifas  
✅ Sin permanencia
✅ Atención premium

👇 ¿Qué te interesa?

1️⃣ Conservar mi número (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares

💡 El cambio a BotMobile es fácil y rápido.
        """)

    def _enviar_mensaje_personalizado_con_botones(self, dispatcher: CollectingDispatcher, compania: str):
        """
        Nueva función para enviar mensajes personalizados con formato de botones compatible con Node-RED
        """
        # Obtener el mensaje de texto
        mensaje_texto = self._crear_mensaje_personalizado_con_menu(compania)
        
        # **CORRECCIÓN NODE-RED**: Enviar un solo mensaje con texto + botones
        dispatcher.utter_message(
            text=mensaje_texto,
            buttons=[
                {"title": "1️⃣ Conservar mi número (portabilidad).", "payload": "1"},
                {"title": "2️⃣ Ver paquetes disponibles.", "payload": "2"},
                {"title": "3️⃣ Hablar con alguien del equipo.", "payload": "3"},
                {"title": "4️⃣ Recargas celulares.", "payload": "4"}
            ]
        )
        
        print(f"[DEBUG] ✅ Mensaje personalizado con botones enviado para {compania}")


class ActionProcesarCompania(Action):
    """Acción para procesar la compañía detectada por Node-RED"""
    
    def name(self) -> Text:
        return "action_procesar_compania"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        print(f"[DEBUG ActionProcesarCompania] INICIANDO")
        print(f"[DEBUG ActionProcesarCompania] tracker.latest_message: {tracker.latest_message}")
        
        # PRIMERO: Enviar imagen de bienvenida (como action_session_start)
        dispatcher.utter_message(image=ImageConfig.BIENVENIDA_BOTMOBILE)
        
        # Buscar el texto del mensaje en múltiples lugares
        mensaje_texto = None
        
        # 1. Buscar en latest_message
        if tracker.latest_message:
            mensaje_texto = tracker.latest_message.get('text', None)
            print(f"[DEBUG ActionProcesarCompania] Texto de latest_message: '{mensaje_texto}'")
        
        # 2. Si no se encuentra, buscar en todos los eventos del tracker
        if not mensaje_texto:
            print(f"[DEBUG ActionProcesarCompania] Buscando en eventos del tracker...")
            print(f"[DEBUG ActionProcesarCompania] Total de eventos: {len(tracker.events)}")
            for i, event in enumerate(tracker.events):
                event_type = event.get('event', 'unknown')
                event_text = event.get('text', '')
                print(f"[DEBUG ActionProcesarCompania] Evento {i}: {event_type} - '{event_text}'")
                if event.get('event') == 'user' and event.get('text'):
                    mensaje_texto = event.get('text')
                    print(f"[DEBUG ActionProcesarCompania] ✅ Encontrado en eventos: '{mensaje_texto}'")
                    break
        
        # 3. Como último recurso, buscar en parse_data si existe
        if not mensaje_texto and tracker.latest_message and 'parse_data' in tracker.latest_message:
            parse_data = tracker.latest_message.get('parse_data', {})
            mensaje_texto = parse_data.get('text', None)
            print(f"[DEBUG ActionProcesarCompania] Texto de parse_data: '{mensaje_texto}'")
        
        if not mensaje_texto:
            print(f"[DEBUG ActionProcesarCompania] ❌ NO se pudo encontrar texto del mensaje")
            # Si no hay mensaje, mostrar saludo genérico (como action_session_start)
            mensaje_menu = """
👋 ¡Hola! Soy BotMobile, tu asistente móvil ☕
Estoy aquí para ayudarte a conectarte fácil, rápido y sin interrupciones 📶

📦 Tenemos paquetes para todos los usos, con cobertura nacional.
Elige entre chip físico o eSIM, ¡y hazlo todo desde aquí!

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares.
☕ ¡Vamos a hacerlo simple! Solo responde seleccionando la opción que necesites.
            """
            dispatcher.utter_message(text=mensaje_menu)
            return [SlotSet("estado_menu", "menu_principal")]
        
        print(f"[DEBUG ActionProcesarCompania] ✅ Procesando mensaje: '{mensaje_texto}'")
        
        # Inicializar variable para el número
        self.numero_usuario = None
        
        # Extraer la compañía del mensaje usando diferentes patrones
        compania_detectada = self._extraer_compania(mensaje_texto)
        print(f"[DEBUG ActionProcesarCompania] Compañía extraída: {compania_detectada}")
        print(f"[DEBUG ActionProcesarCompania] Número extraído: {getattr(self, 'numero_usuario', None)}")
        
        if compania_detectada:
            logger.info(f"Compañía detectada: {compania_detectada}")
            print(f"[DEBUG ActionProcesarCompania] ✅ Enviando saludo personalizado para: {compania_detectada}")
            
            # Crear mensaje personalizado directamente basado en la compañía + MENÚ
            mensaje_personalizado = self._crear_mensaje_personalizado_con_menu(compania_detectada)
            dispatcher.utter_message(text=mensaje_personalizado)
            
            # Crear lista de slots a establecer
            slots_to_set = [
                SlotSet("compania_operador", compania_detectada),
                SlotSet("estado_menu", "menu_principal")  # ← IMPORTANTE: Establecer estado
            ]
            
            # Si se extrajo un número, también guardarlo
            if hasattr(self, 'numero_usuario') and self.numero_usuario:
                slots_to_set.append(SlotSet("numero_telefono", self.numero_usuario))
            
            return slots_to_set
        else:
            print(f"[DEBUG ActionProcesarCompania] ❌ No se pudo extraer compañía, enviando saludo genérico")
            # Si no se puede extraer la compañía, usar saludo genérico (como action_session_start)
            mensaje_menu = """
👋 ¡Hola! Soy BotMobile, tu asistente móvil ☕
Estoy aquí para ayudarte a conectarte fácil, rápido y sin interrupciones 📶

📦 Tenemos paquetes para todos los usos, con cobertura nacional.
Elige entre chip físico o eSIM, ¡y hazlo todo desde aquí!

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares.

☕ ¡Vamos a hacerlo simple! Solo responde seleccionando la opción que necesites.
            """
            dispatcher.utter_message(text=mensaje_menu)
            return [SlotSet("estado_menu", "menu_principal")]
    
    def _extraer_compania(self, mensaje: str) -> str:
        """Extrae el nombre de la compañía del mensaje de Node-RED"""
        
        # Normalizar el mensaje
        mensaje_lower = mensaje.lower()
        
        # Verificar formato AUTODETECT_COMPANY primero
        if 'autodetect_company' in mensaje_lower:
            # Extraer la parte después de "AUTODETECT_COMPANY"
            import re
            match = re.search(r'autodetect_company[:\s]+([a-záéíóúñ&\s]+)', mensaje_lower)
            if match:
                compania_extraida = match.group(1).strip()
                return self._normalizar_nombre_compania(compania_extraida)
        
        # NUEVO: Extraer compañía y número del formato Node-RED
        if 'compania_detectada' in mensaje_lower and 'numero' in mensaje_lower:
            # Formato: "COMPANIA_DETECTADA Telcel NUMERO 6141234567"
            import re
            match = re.search(r'compania_detectada\s+([a-záéíóúñ&\s]+?)\s+numero\s+(\d+)', mensaje_lower)
            if match:
                compania_extraida = match.group(1).strip()
                numero_extraido = match.group(2).strip()
                print(f"[DEBUG] Extraído - Compañía: {compania_extraida}, Número: {numero_extraido}")
                # Guardar el número para uso posterior
                self.numero_usuario = numero_extraido
                return self._normalizar_nombre_compania(compania_extraida)
        
        # Formato alternativo con delimitadores
        if 'compania_detectada:' in mensaje_lower and 'numero:' in mensaje_lower:
            # Formato: "COMPANIA_DETECTADA:Telcel|NUMERO:6141234567"
            import re
            compania_match = re.search(r'compania_detectada:([a-záéíóúñ&\s]+?)[\|\s]', mensaje_lower)
            numero_match = re.search(r'numero:(\d+)', mensaje_lower)
            if compania_match and numero_match:
                compania_extraida = compania_match.group(1).strip()
                numero_extraido = numero_match.group(1).strip()
                print(f"[DEBUG] Extraído - Compañía: {compania_extraida}, Número: {numero_extraido}")
                self.numero_usuario = numero_extraido
                return self._normalizar_nombre_compania(compania_extraida)
        
        # Patrones para detectar diferentes formatos de compañía (formato original)
        patrones_compania = {
            'telcel': ['telcel', 'telmex'],
            'att': ['at&t', 'att', 'at t'],
            'movistar': ['movistar'],
            'unefon': ['unefon'],
            'virgin': ['virgin', 'virgin mobile'],
            'bait': ['bait'],
            'flash': ['flash mobile', 'flash'],
            'weex': ['weex']
        }
        
        # Buscar cada patrón en el mensaje
        for compania, variantes in patrones_compania.items():
            for variante in variantes:
                if variante in mensaje_lower:
                    # Capitalizar correctamente el nombre
                    if compania == 'att':
                        return 'AT&T'
                    elif compania == 'virgin':
                        return 'Virgin'
                    elif compania == 'bait':
                        return 'Bait'
                    elif compania == 'flash':
                        return 'Flash Mobile'
                    elif compania == 'weex':
                        return 'Weex'
                    else:
                        return compania.capitalize()
        
        # Si no encuentra ninguna, intentar extraer usando regex
        # Buscar patrón "La compañía es: NOMBRE"
        import re
        match = re.search(r'(?:la compañ[íi]a es:?\s*|operador.*?:?\s*)([a-záéíóúñ&\s]+)', mensaje_lower)
        if match:
            compania_extraida = match.group(1).strip()
            return self._normalizar_nombre_compania(compania_extraida)
        
        return None
    
    def _crear_mensaje_personalizado(self, compania: str) -> str:
        """Crea mensaje personalizado basado en la compañía detectada"""
        mensajes_por_compania = {
            'Telcel': "🎯 ¡Hola! Detecté que vienes de Telcel. Te ayudo con tu portabilidad a BotMobile de manera súper fácil.\n\n💰 **¡Ahorra $80 pesos al mes!**\nTelcel: $300/mes por 8GB\nBotMobile: $220/mes por 72GB\n\n¿Te interesa conocer más?",
            'AT&T': "🎯 ¡Hola! Veo que eres cliente de AT&T. Te explico cómo cambiarte a BotMobile paso a paso.\n\n💰 **¡Ahorra $180 pesos al mes!**\nAT&T: $400/mes por 20GB + HBO Max\nBotMobile: $220/mes por 72GB + Netflix + Disney+ + Prime\n\n¿Quieres saber cómo hacer el cambio?",
            'Movistar': "🎯 ¡Perfecto! Eres de Movistar. Conozco muy bien el proceso para cambiarte a BotMobile.\n\n💰 **Mejor oferta garantizada:**\nMovistar: $250/mes por 12GB + Disney+\nBotMobile: $220/mes por 72GB + Netflix + Disney+ + Prime\n\n¿Te gustaría conocer los pasos?",
            'Unefon': "🎯 ¡Hola! Vienes de Unefon. Te ayudo a mejorar tu plan con BotMobile.\n\n💰 **Upgrade completo:**\nUnefon: $200/mes por 6GB\nBotMobile: $220/mes por 72GB + streaming\n\n¿Solo $20 pesos más por 12x más datos!",
            'Virgin': "🎯 ¡Excelente! Eres de Virgin Mobile. Te muestro cómo mejorar con BotMobile.\n\n💰 **Más por menos:**\nVirgin: $180/mes por 4GB\nBotMobile: $220/mes por 72GB + plataformas\n\n¿Te interesa conocer el proceso de cambio?",
            'Bait': "🎯 ¡Perfecto! Vienes de Bait. Te ayudo con tu portabilidad a BotMobile.\n\n💰 **BotMobile te ofrece:**\n📱 72GB por solo $220/mes\n🎬 Netflix + Disney+ + Prime incluido\n📶 Cobertura nacional garantizada\n\n¿Te gustaría conocer cómo hacer el cambio?",
            'Flash Mobile': "🎯 ¡Perfecto! Vienes de Flash Mobile. Te ayudo con tu portabilidad a BotMobile.\n\n💰 **BotMobile te ofrece:**\n📱 72GB por solo $220/mes\n🎬 Netflix + Disney+ + Prime incluido\n📶 Cobertura nacional garantizada\n\n¿Te gustaría conocer cómo hacer el cambio?",
            'Weex': "🎯 ¡Perfecto! Vienes de Weex. Te ayudo con tu portabilidad a BotMobile.\n\n💰 **BotMobile te ofrece:**\n📱 72GB por solo $220/mes\n🎬 Netflix + Disney+ + Prime incluido\n📶 Cobertura nacional garantizada\n\n¿Te gustaría conocer cómo hacer el cambio?"
        }
        
        return mensajes_por_compania.get(compania, "🎯 ¡Perfecto! Te ayudo con tu portabilidad a BotMobile.\n\n💰 **BotMobile te ofrece:**\n📱 72GB por solo $220/mes\n🎬 Netflix + Disney+ + Prime incluido\n📶 Cobertura nacional garantizada\n\n¿Te gustaría conocer cómo hacer el cambio?")
    
    def _crear_mensaje_personalizado_con_menu(self, compania: str) -> str:
        """Crea mensaje personalizado que incluye el mensaje específico + menú"""
        
        mensajes_por_compania = {
            'Telcel': """🎯 ¡Hola! Detecté que vienes de Telcel. Te ayudo con tu portabilidad a BotMobile de manera súper fácil.

💰 **¡Ahorra $80 pesos al mes!**
📱 Telcel: $300/mes por 8GB
🚀 BotMobile: $220/mes por 72GB

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares.
""",

            'AT&T': """🎯 ¡Hola! Veo que eres cliente de AT&T. Te explico cómo cambiarte a BotMobile paso a paso.

💰 **¡Ahorra $180 pesos al mes!**
📱 AT&T: $400/mes por 20GB + HBO Max
🚀 BotMobile: $220/mes por 72GB + Netflix + Disney+ + Prime

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares.
""",

            'Movistar': """🎯 ¡Perfecto! Eres de Movistar. Conozco muy bien el proceso para cambiarte a BotMobile.

💰 **Mejor oferta garantizada:**
📱 Movistar: $250/mes por 12GB + Disney+
🚀 BotMobile: $220/mes por 72GB + Netflix + Disney+ + Prime

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares.
""",

            'Unefon': """🎯 ¡Hola! Vienes de Unefon. Te ayudo a mejorar tu plan con BotMobile.

💰 **Upgrade completo:**
📱 Unefon: $200/mes por 6GB
🚀 BotMobile: $220/mes por 72GB + streaming

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares.

☕ ¡Solo $20 pesos más por 12x más datos! Solo responde con el número de la opción.""",

            'Virgin': """🎯 ¡Excelente! Eres de Virgin Mobile. Te muestro cómo mejorar con BotMobile.

💰 **Más por menos:**
📱 Virgin: $180/mes por 4GB
🚀 BotMobile: $220/mes por 72GB + plataformas

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares.
""",

            'Bait': """🎯 ¡Perfecto! Vienes de Bait. Te ayudo con tu portabilidad a BotMobile.
"""
        }
        
        # Si la compañía no está en el diccionario, usar mensaje genérico
        mensaje_generico = f"""🎯 ¡Perfecto! Vienes de {compania}. Te ayudo con tu portabilidad a BotMobile.

💰 **BotMobile te ofrece:**
📱 72GB por solo $220/mes
🎬 Netflix + Disney+ + Prime incluido
📶 Cobertura nacional garantizada

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares.
"""
        
        return mensajes_por_compania.get(compania, mensaje_generico)

    def _normalizar_nombre_compania(self, nombre: str) -> str:
        """Normaliza el nombre de la compañía a un formato estándar"""
        nombre_lower = nombre.lower().strip()
        
        if 'telcel' in nombre_lower:
            return 'Telcel'
        elif 'at&t' in nombre_lower or 'att' in nombre_lower:
            return 'AT&T'
        elif 'movistar' in nombre_lower:
            return 'Movistar'
        elif 'unefon' in nombre_lower:
            return 'Unefon'
        elif 'virgin' in nombre_lower:
            return 'Virgin'
        elif 'bait' in nombre_lower:
            return 'Bait'
        elif 'flash' in nombre_lower:
            return 'Flash Mobile'
        elif 'weex' in nombre_lower:
            return 'Weex'
        else:
            # Para compañías no registradas, usar formato estándar
            nombre_formateado = ' '.join(word.capitalize() for word in nombre.split())
            return nombre_formateado

    def _normalizar_nombre_persona(self, nombre_completo: str) -> str:
        """
        Normaliza nombres de persona con las siguientes reglas:
        - Primera letra mayúscula, resto en minúsculas
        - Acepta nombres con uno o dos apellidos
        - Maneja caracteres especiales y acentos
        - Elimina espacios extra
        """
        import re
        
        if not nombre_completo or not nombre_completo.strip():
            return ""
        
        # Limpiar el texto: eliminar espacios extra, números y caracteres especiales no deseados
        nombre_limpio = re.sub(r'[^\w\sáéíóúÁÉÍÓÚüÜñÑ\'-]', '', nombre_completo.strip())
        nombre_limpio = re.sub(r'\s+', ' ', nombre_limpio)  # Eliminar espacios múltiples
        
        # Dividir en palabras
        palabras = nombre_limpio.split()
        
        # Validar que tenga al menos 2 palabras (nombre + apellido)
        if len(palabras) < 2:
            return ""  # Nombre inválido
        
        # Validar que no tenga más de 5 palabras (nombre + segundo nombre + apellido paterno + apellido materno + posible tercer apellido)
        if len(palabras) > 5:
            # Tomar solo las primeras 5 palabras
            palabras = palabras[:5]
        
        # Palabras que deben permanecer en minúsculas (conectores comunes)
        conectores = {'de', 'del', 'la', 'las', 'los', 'y', 'e', 'da', 'dos', 'das'}
        
        # Palabras que tienen capitalización especial
        palabras_especiales = {
            'mc': 'Mc',  # McDonald -> McDonald
            'mac': 'Mac',  # MacArthur -> MacArthur
            'van': 'van',  # van der Berg -> van der Berg
            'von': 'von',  # von Neumann -> von Neumann
        }
        
        palabras_normalizadas = []
        
        for i, palabra in enumerate(palabras):
            palabra_lower = palabra.lower()
            
            # Si es un conector y no es la primera palabra, mantenerlo en minúsculas
            if i > 0 and palabra_lower in conectores:
                palabras_normalizadas.append(palabra_lower)
            # Si es una palabra especial
            elif palabra_lower in palabras_especiales:
                palabras_normalizadas.append(palabras_especiales[palabra_lower])
            else:
                # Capitalizar primera letra, resto en minúsculas
                if len(palabra) > 0:
                    palabra_normalizada = palabra_lower[0].upper() + palabra_lower[1:] if len(palabra) > 1 else palabra_lower.upper()
                    palabras_normalizadas.append(palabra_normalizada)
        
        return ' '.join(palabras_normalizadas)
    
    def _validar_nombre_persona(self, nombre: str) -> tuple:
        """
        Valida si un nombre es aceptable
        Retorna: (es_valido: bool, mensaje_error: str, nombre_normalizado: str)
        """
        import re
        
        if not nombre or len(nombre.strip()) < 3:
            return False, "El nombre debe tener al menos 3 caracteres.", ""
        
        nombre_normalizado = self._normalizar_nombre_persona(nombre)
        
        if not nombre_normalizado:
            return False, "Por favor escribe un nombre válido (nombre y apellido).", ""
        
        palabras = nombre_normalizado.split()
        
        # Validar cantidad de palabras (mínimo 2, máximo 5)
        if len(palabras) < 2:
            return False, "Por favor escribe tu nombre completo (nombre y al menos un apellido).", ""
        
        if len(palabras) > 5:
            return False, "El nombre es demasiado largo. Máximo 5 palabras.", ""
        
        # Validar que cada palabra tenga al menos 2 caracteres (excepto conectores)
        conectores = {'de', 'del', 'la', 'las', 'los', 'y', 'e', 'da', 'dos', 'das'}
        for palabra in palabras:
            if palabra.lower() not in conectores and len(palabra) < 2:
                return False, "Cada parte del nombre debe tener al menos 2 caracteres.", ""
        
        # Validar que no contenga solo números o caracteres especiales
        if re.match(r'^[\d\s\W]+$', nombre_normalizado):
            return False, "El nombre no puede contener solo números o símbolos.", ""
        
        return True, "", nombre_normalizado


class ActionElegirOpcion(Action):
    """Acción para manejar la navegación del menú"""
    
    def name(self) -> Text:
        return "action_elegir_opcion"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        estado_actual = tracker.get_slot("estado_menu")
        numero_opcion = next(tracker.get_latest_entity_values("numero_opcion"), None)
        intent = tracker.latest_message.get('intent', {}).get('name')
        texto_usuario = tracker.latest_message.get('text', '').lower()
        
        print(f"DEBUG: estado_actual={estado_actual}, numero_opcion={numero_opcion}, intent={intent}")
        print(f"DEBUG: texto_usuario='{texto_usuario}'")
        print(f"DEBUG: paquete_seleccionado={tracker.get_slot('paquete_seleccionado')}")
        print(f"DEBUG: numero_recarga={tracker.get_slot('numero_recarga')}")
        
        # ✅ Ya no necesitamos el debug aquí - el problema era la línea que regresaba al menú principal
        
        # 🧠 MEJORA: Mapeo inteligente de intents a opciones
        if not numero_opcion and estado_actual == "menu_principal":
            if intent == "portabilidad_interes" or any(palabra in texto_usuario for palabra in ["portabilidad", "conservar número", "mantener número"]):
                numero_opcion = "1"
                print(f"DEBUG: Intent/texto mapeado a opción 1 (portabilidad)")
            elif intent == "planes_interes" or any(palabra in texto_usuario for palabra in ["planes", "paquetes", "ofertas"]):
                numero_opcion = "2"
                print(f"DEBUG: Intent/texto mapeado a opción 2 (planes)")
            elif intent == "contacto_interes" or any(palabra in texto_usuario for palabra in ["contacto", "hablar", "whatsapp"]):
                numero_opcion = "3"
                print(f"DEBUG: Intent/texto mapeado a opción 3 (contacto)")
        
        # 🔄 MEJORA: Detección de regreso al menú desde cualquier estado
        if intent == "regresar_menu" or any(palabra in texto_usuario for palabra in ["menú", "menu", "volver", "regresar", "inicio"]):
            print(f"DEBUG: Regresando al menú principal")
            return self._mostrar_menu_principal(dispatcher)
        
        estados_texto_libre = ["capturar_nip", "validar_imei", "capturar_nombre", 
                                "elegir_pago_s30", "elegir_pago_s50", "elegir_pago_m100", 
                                "elegir_pago_m120", "elegir_pago_m220"]
        
        if intent == "despedida" and estado_actual not in estados_texto_libre:
            dispatcher.utter_message(text="¡Hasta la vista! 👋 Espero haberte ayudado. Regresa cuando gustes.")
            return []
        
        print(f"DEBUG: LLEGANDO A SECCIÓN DE ESTADOS - estado_actual='{estado_actual}'")
        
        if estado_actual == "capturar_nip":
            return self._manejar_captura_nip(dispatcher, tracker)
        elif estado_actual == "validar_imei":
            return self._manejar_validacion_imei(dispatcher, tracker)
        elif estado_actual == "capturar_nombre":
            return self._manejar_captura_nombre(dispatcher, tracker)
        
        # ✅ ARREGLO CRÍTICO: Los estados de pago pueden aceptar texto libre (codi, spei)
        # No regresar al menú si no hay numero_opcion en estados que manejan texto libre
        if not numero_opcion and estado_actual not in estados_texto_libre:
            print(f"DEBUG: Sin numero_opcion en estado '{estado_actual}' - regresando al menú")
            return self._mostrar_menu_principal(dispatcher)
        
        # Menú principal
        if estado_actual == "menu_principal":
            return self._manejar_menu_principal(dispatcher, numero_opcion)
        
        # Submenús
        elif estado_actual == "submenu_paquetes":
            return self._manejar_submenu_paquetes(dispatcher, numero_opcion)
        
        elif estado_actual == "submenu_portabilidad":
            return self._manejar_submenu_portabilidad(dispatcher, numero_opcion)
        
        elif estado_actual == "submenu_nip":
            return self._manejar_submenu_nip(dispatcher, numero_opcion)
        
        elif estado_actual == "submenu_avanzar_nip":
            return self._manejar_submenu_avanzar_nip(dispatcher, numero_opcion)
        
        elif estado_actual == "submenu_soporte":
            return self._manejar_submenu_soporte(dispatcher, numero_opcion)
        
        elif estado_actual == "submenu_recargas":
            return self._manejar_submenu_recargas(dispatcher, numero_opcion)
        
        elif estado_actual in ["submenu_paquete_s30", "submenu_paquete_s50", "submenu_paquete_m100", "submenu_paquete_m120", "submenu_paquete_m220"]:
            # Todos los submenús de paquetes individuales manejan opciones similares
            return self._manejar_submenu_paquete_individual(dispatcher, numero_opcion, estado_actual)
        
        elif estado_actual in ["capturar_numero_s30", "capturar_numero_s50", "capturar_numero_m100", "capturar_numero_m120", "capturar_numero_m220"]:
            # Captura del número de teléfono para recarga
            return self._manejar_captura_numero_recarga(dispatcher, tracker, estado_actual)
        
        elif estado_actual in ["elegir_pago_s30", "elegir_pago_s50", "elegir_pago_m100", "elegir_pago_m120", "elegir_pago_m220"]:
            print(f"DEBUG: ¡ENTRANDO A MANEJO DE PAGO! estado={estado_actual}")
            if not numero_opcion:
                texto_usuario_limpio = texto_usuario.lower().strip()
                print(f"DEBUG: texto_usuario_limpio='{texto_usuario_limpio}'")
                if texto_usuario_limpio in ["codi", "1"]:
                    numero_opcion = "codi"
                elif texto_usuario_limpio in ["spei", "2"]:
                    numero_opcion = "spei"
                elif texto_usuario_limpio in ["0", "cancelar"]:
                    numero_opcion = "0"
                print(f"DEBUG: numero_opcion final='{numero_opcion}'")
            return self._manejar_seleccion_pago(dispatcher, tracker, estado_actual, numero_opcion)
        
        elif estado_actual == "esperando_pago":
            # Usuario ya tiene un QR generado, solo puede volver al menú
            if numero_opcion == "0":
                return self._mostrar_menu_principal(dispatcher)
            else:
                dispatcher.utter_message(
                    text="Tienes un pago pendiente. Completa tu pago escaneando el QR o selecciona 0 para volver al menú principal.",
                    buttons=[{"title": "0️⃣ Menú principal", "payload": "0"}]
                )
                return [SlotSet("estado_menu", "esperando_pago")]
        
        elif estado_actual == "esperando_pago_spei":
            # Usuario ya tiene una referencia SPEI generada, solo puede volver al menú
            if numero_opcion == "0":
                return self._mostrar_menu_principal(dispatcher)
            else:
                dispatcher.utter_message(
                    text="Tienes un pago pendiente con referencia SPEI. Completa tu pago en una de las tiendas afiliadas o selecciona 0 para volver al menú principal.",
                    buttons=[{"title": "0️⃣ Menú principal", "payload": "0"}]
                )
                return [SlotSet("estado_menu", "esperando_pago_spei")]
        
        # Si el estado no es reconocido, volver al menú principal
        else:
            return self._mostrar_menu_principal(dispatcher)
    
    def _mostrar_menu_principal(self, dispatcher):
        # Enviar imagen de bienvenida primero
        dispatcher.utter_message(image=ImageConfig.BIENVENIDA_BOTMOBILE)
        
        mensaje_menu = """👋 ¡Hola! Soy BotMobile, tu asistente móvil ☕
Estoy aquí para ayudarte a conectarte fácil, rápido y sin interrupciones 📶

📦 Tenemos paquetes para todos los usos, con cobertura nacional.
Elige entre chip físico o eSIM, ¡y hazlo todo desde aquí!

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad).
2️⃣ Ver paquetes disponibles.
3️⃣ Hablar con alguien del equipo.
4️⃣ Recargas celulares.
"""
        
        # **CORRECCIÓN NODE-RED**: Enviar un solo mensaje con texto + botones
        dispatcher.utter_message(
            text=mensaje_menu,
            buttons=[
                {"title": "1️⃣ Conservar mi número (portabilidad).", "payload": "1"},
                {"title": "2️⃣ Ver paquetes disponibles.", "payload": "2"},
                {"title": "3️⃣ Hablar con alguien del equipo.", "payload": "3"},
                {"title": "4️⃣ Recargas celulares.", "payload": "4"}
            ]
        )
        return [SlotSet("estado_menu", "menu_principal")]
    
    def _manejar_menu_principal(self, dispatcher, numero_opcion):
        if numero_opcion == "1":
            # Enviar la imagen de portabilidad primero
            dispatcher.utter_message(image=ImageConfig.PORTABILIDAD_3_PASOS)
            
            # **CORRECCIÓN NODE-RED**: Múltiples mensajes para elementos separados en array JSON
            dispatcher.utter_message(text="🔄 PORTABILIDAD")
            dispatcher.utter_message(text="1️⃣ ¿Cómo conseguir NIP?.\n2️⃣ Documentos necesarios.\n3️⃣ Hablar con equipo.\n0️⃣ Menú principal.")
            dispatcher.utter_message(
                text="¿Qué opción necesitas?",
                buttons=[
                    {"title": "1️⃣ ¿Cómo conseguir NIP?.", "payload": "1"},
                    {"title": "2️⃣ Documentos necesarios.", "payload": "2"},
                    {"title": "3️⃣ Hablar con equipo.", "payload": "3"},
                    {"title": "0️⃣ Menú principal.", "payload": "0"}
                ]
            )
            return [SlotSet("estado_menu", "submenu_portabilidad")]
        
        elif numero_opcion == "2":
            # Enviar la imagen de los paquetes primero
            dispatcher.utter_message(image=ImageConfig.PAQUETES_PROMOCION)
            
            mensaje = """
📱 ¡Conéctate con Spot1Mobile y #ViveSinInterrupciones!

🔸 Paquete S1 M100 – $100 / 30 días
✅ 6 GB por promoción + redes sociales ilimitadas
✅ 1,500 minutos + 250 SMS 
💡 Perfecto si usas apps básicas y redes.

🔸 Paquete S1 M120 – $120 / 30 días
✅ 12 GB por promoción
✅ 1,500 minutos + 250 SMS
✅ Compartición de datos
🎥 Para quienes navegan, ven videos o hacen videollamadas.

🔸 Paquete S1 M220 – $220 / 30 días
✅ ¡72 GB por promoción!
✅ 1,500 minutos + 250 SMS
✅ Comparte tus datos
⚡¡Potencia para gamers, trabajo remoto o compartir internet!

👇 ¿Qué quieres hacer?

1️⃣ Conservar mi número con estos paquetes (Portabilidad).
2️⃣ Activar línea nueva con estos paquetes.
3️⃣ Hablar con el equipo para más info.
0️⃣ Volver al menú principal.

            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_paquetes")]
        
        elif numero_opcion == "3":
            mensaje = """
� SOPORTE - Contacta a nuestro equipo

📲 WhatsApp: +52 614 558 7289

⚡ Nuestro equipo te ayudará con:
• Resolver dudas sobre servicios
• Información técnica
• Proceso de activación
• Cualquier consulta que tengas

🕒 Horarios de atención:
• Lunes a Viernes: 9:00 - 18:00
• Sábados: 9:00 - 14:00

0️⃣ Volver al menú principal.
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_soporte")]
        
        elif numero_opcion == "4":
            # Recargas celulares
            mensaje = """
📱 RECARGAS CELULARES

¡Conoce nuestros paquetes de recargas disponibles!

🔸 **Paquete S1 - $30 / 3 días**
✅ 2 GB + Redes sociales ilimitadas
💡 Perfecto para uso básico de pocos días

🔸 **Paquete S1 - $50 / 7 días**  
✅ 3 GB + Hotspot incluido
🎯 Ideal para una semana de uso moderado

🔸 **Paquete S1 M100 - $100 / 30 días**
✅ 2 GB + Redes sociales ilimitadas
📱 Plan básico mensual

🔸 **Paquete S1 M120 - $120 / 30 días**
✅ 4 GB + Redes sociales ilimitadas  
📺 Para navegación y videos

🔸 **Paquete S1 M220 - $220 / 30 días**
✅ 24 GB + Redes sociales ilimitadas
⚡ Para uso intensivo y compartir internet

👇 ¿Qué paquete te interesa?

1️⃣ S1 $30 (3 días)
2️⃣ S1 $50 (7 días)
3️⃣ S1 M100 (30 días)
4️⃣ S1 M120 (30 días)
5️⃣ S1 M220 (30 días)
6️⃣ Hablar con el equipo
0️⃣ Volver al menú principal
            """
            dispatcher.utter_message(
                text=mensaje,
                buttons=[
                    {"title": "1️⃣ S1 $30 - 3 días", "payload": "1"},
                    {"title": "2️⃣ S1 $50 - 7 días", "payload": "2"},
                    {"title": "3️⃣ S1 M100 - $100", "payload": "3"},
                    {"title": "4️⃣ S1 M120 - $120", "payload": "4"},
                    {"title": "5️⃣ S1 M220 - $220", "payload": "5"},
                    {"title": "6️⃣ Hablar con equipo", "payload": "6"},
                    {"title": "0️⃣ Menú principal", "payload": "0"}
                ]
            )
            return [SlotSet("estado_menu", "submenu_recargas")]
        
        else:
            dispatcher.utter_message(text="Opción no válida. Por favor elige una opción del menú.")
            return self._mostrar_menu_principal(dispatcher)
    
    def _manejar_submenu_paquetes(self, dispatcher, numero_opcion):
        """Maneja las opciones del submenú de paquetes"""
        if numero_opcion == "0":
            return self._mostrar_menu_principal(dispatcher)
        
        elif numero_opcion == "1":
            # Dirigir al menú de portabilidad
            # Enviar la imagen de portabilidad primero
            dispatcher.utter_message(image=ImageConfig.PORTABILIDAD_3_PASOS)
            
            # **CORRECCIÓN NODE-RED**: Múltiples mensajes separados
            dispatcher.utter_message(text="🔄 PORTABILIDAD")
            dispatcher.utter_message(text="¡Perfecto! Vamos a conservar tu número actual y activar uno de nuestros paquetes.")
            dispatcher.utter_message(text="1️⃣ ¿Cómo conseguir NIP?.\n2️⃣ Documentos necesarios.\n3️⃣ Hablar con equipo.\n0️⃣ Menú principal.")
            return [SlotSet("estado_menu", "submenu_portabilidad")]
        
        elif numero_opcion == "2":
            # Línea nueva (próximamente)
            # **CORRECCIÓN NODE-RED**: Múltiples mensajes separados
            dispatcher.utter_message(text="📞 LÍNEA NUEVA")
            dispatcher.utter_message(text="Esta opción estará disponible muy pronto.")
            dispatcher.utter_message(text="Por ahora puedes:\n📲 WhatsApp: +52 614 558 7289")
            dispatcher.utter_message(text="🕒 Horarios de atención:\n• Lunes a Viernes: 9:00 - 18:00\n• Sábados: 9:00 - 14:00")
            dispatcher.utter_message(text="👇 ¿Qué quieres hacer?\n\n1️⃣ Ver paquetes de nuevo.\n2️⃣ Ir a portabilidad.\n0️⃣ Menú principal.")
            return [SlotSet("estado_menu", "submenu_paquetes")]
        
        elif numero_opcion == "3":
            # Hablar con el equipo
            # **CORRECCIÓN NODE-RED**: Múltiples mensajes separados
            dispatcher.utter_message(text="👥 Contacta a nuestro equipo")
            dispatcher.utter_message(text="📲 WhatsApp: +52 614 558 7289")
            dispatcher.utter_message(text="⚡ Nuestro equipo te ayudará con:\n• Detalles de cada paquete\n• Disponibilidad en tu zona\n• Proceso de activación\n• Resolver cualquier duda")
            dispatcher.utter_message(text="🕒 Horarios de atención:\n• Lunes a Viernes: 9:00 - 18:00\n• Sábados: 9:00 - 14:00")
            dispatcher.utter_message(text="0️⃣ Volver al menú principal.")
            return [SlotSet("estado_menu", "submenu_paquetes")]
        
        else:
            # Opción no válida
            # **CORRECCIÓN NODE-RED**: Múltiples mensajes separados
            dispatcher.utter_message(text="Opción no válida. Por favor elige:")
            dispatcher.utter_message(text="1️⃣ Conservar mi número con estos paquetes (Portabilidad).\n2️⃣ Activar línea nueva con estos paquetes.\n3️⃣ Hablar con el equipo para más info.\n0️⃣ Volver al menú principal.")
            return [SlotSet("estado_menu", "submenu_paquetes")]
    
    def _manejar_submenu_portabilidad(self, dispatcher, numero_opcion):
        if numero_opcion == "0":
            return self._mostrar_menu_principal(dispatcher)
        
        elif numero_opcion == "1":
            # Enviar imagen de instrucciones para obtener NIP
            dispatcher.utter_message(image=ImageConfig.COMO_OBTENER_NIP)
            
            mensaje_instrucciones = """
📱 ¡Listo para pedir tu NIP de portabilidad!

Solo hay 2 formas:
1. Manda un SMS con la palabra *NIP* al *051*  
2. O marca al *051* y sigue las instrucciones por llamada  

📩 En ambos casos, te llegará un mensaje con el NIP de 4 dígitos  
💡 Recuerda hacerlo desde el número que quieres portar
            """
            dispatcher.utter_message(text=mensaje_instrucciones)
            
            mensaje_menu_nip = """
👇 ¿Ya lo pediste o quieres ayuda?

1️⃣ Ya tengo mi NIP, quiero avanzar.
2️⃣ ¿Dónde lo escribo?.
3️⃣ Quiero hablar con alguien del equipo.
            """
            dispatcher.utter_message(text=mensaje_menu_nip)
            return [SlotSet("estado_menu", "submenu_nip")]
        
        elif numero_opcion == "2":
            # **CORRECCIÓN NODE-RED**: Múltiples mensajes separados
            dispatcher.utter_message(text="📄 Documentos necesarios")
            dispatcher.utter_message(text="Para la portabilidad necesitas:")
            dispatcher.utter_message(text="✅ Identificación oficial vigente\n✅ Código IMEI (para eSIM)\n✅ NIP de tu compañía actual\n✅ Número telefónico a portar")
            dispatcher.utter_message(text="Escribe **0** para volver al menú principal.")
            return [SlotSet("estado_menu", "submenu_portabilidad")]
        
        elif numero_opcion == "3":
            # Hablar con el equipo (ahora es la opción 3)
            # **CORRECCIÓN NODE-RED**: Múltiples mensajes separados
            dispatcher.utter_message(text="👥 Contacta a nuestro equipo")
            dispatcher.utter_message(text="📲 WhatsApp: +52 614 558 7289")
            dispatcher.utter_message(text="⚡ Nuestro equipo te ayudará con:\n• Proceso de portabilidad\n• Resolver dudas sobre documentos\n• Verificar tu NIP\n• Completar el trámite")
            dispatcher.utter_message(text="🕒 Horarios de atención:\n• Lunes a Viernes: 9:00 - 18:00\n• Sábados: 9:00 - 14:00")
            dispatcher.utter_message(text="0️⃣ Volver al menú principal.")
            return [SlotSet("estado_menu", "submenu_portabilidad")]
        
        else:
            # **CORRECCIÓN NODE-RED**: Múltiples mensajes separados
            dispatcher.utter_message(text="Opción no válida.")
            dispatcher.utter_message(text="1️⃣ ¿Cómo conseguir NIP?.\n2️⃣ Documentos necesarios.\n3️⃣ Hablar con equipo.\n0️⃣ Menú principal.")
            return [SlotSet("estado_menu", "submenu_portabilidad")]
    
    def _manejar_submenu_nip(self, dispatcher, numero_opcion):
        if numero_opcion == "0":
            return self._mostrar_menu_principal(dispatcher)
        
        elif numero_opcion == "1":
            mensaje = """
✅ ¡Perfecto! Ya tienes tu NIP.

📝 Por favor, escríbeme tu NIP de 4 dígitos exactamente como te llegó en el mensaje:

🔒 Tu NIP estará seguro y lo usaremos para procesar tu portabilidad.
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "capturar_nip")]
        
        elif numero_opcion == "2":
            mensaje = """
📝 ¿Dónde escribir tu NIP?

¡Por favor envía tu NIP directamente aquí en este chat! 💬

Una vez que lo tengas, solo escribelo y nuestro equipo lo procesará inmediatamente.

📱 Ejemplo:
"Mi NIP es: 1234"

También puedes contactarnos por:
📲 WhatsApp: +52 614 558 7289

0️⃣ Menú principal.
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_nip")]
        
        elif numero_opcion == "3":
            mensaje = """
👥 Contacta a nuestro equipo

Por ahora puedes:
📲 WhatsApp: +52 614 558 7289

🕒 **Horarios de atención:**
• Lunes a Viernes: 9:00 - 18:00
• Sábados: 9:00 - 14:00

0️⃣ Volver al menú principal.
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_nip")]
        
        else:
            mensaje = """
Opción no válida. 

1️⃣ Ya tengo mi NIP, quiero avanzar.
2️⃣ ¿Dónde lo escribo?.
3️⃣ Quiero hablar con alguien del equipo.
0️⃣ Menú principal.
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_nip")]
    
    def _manejar_submenu_avanzar_nip(self, dispatcher, numero_opcion):
        if numero_opcion == "0":
            return self._mostrar_menu_principal(dispatcher)
        
        elif numero_opcion == "1":
            mensaje = """
📲 Continuar por WhatsApp

Te vamos a conectar con nuestro equipo por WhatsApp:

🔗 WhatsApp: +52 614 558 7289

📝 Mensaje sugerido:
"Hola, vengo del bot de Spotty. Tengo mi NIP y quiero portar mi número a Spot1Mobile"

⚡ Nuestro equipo te ayudará con:
• Verificar tu NIP
• Completar el proceso de portabilidad
• Resolver cualquier duda

🕒 Horario: Lunes a Viernes 9:00-18:00

0️⃣ Volver al menú principal.
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_avanzar_nip")]
        
        elif numero_opcion == "2":
            mensaje = """
📞 Hablar por teléfono

Llama directamente a nuestro equipo:

📱 Teléfono: +52 614 558 7289

🗣️ Al contestar menciona:
"Vengo del bot de Spotty, tengo mi NIP para portabilidad"

⚡ Te ayudaremos con:
• Tomar tus datos
• Procesar tu portabilidad
• Programar la activación

🕒 Horarios de atención:
• Lunes a Viernes: 9:00 - 18:00
• Sábados: 9:00 - 14:00

0️⃣ Volver al menú principal.
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_avanzar_nip")]
        
        else:
            mensaje = """
Opción no válida.

1️⃣ Continuar por WhatsApp.
2️⃣ Hablar por teléfono.
0️⃣ Volver al menú principal.
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_avanzar_nip")]
    
    def _manejar_captura_nip(self, dispatcher, tracker):
        """Maneja la captura del NIP del usuario"""
        mensaje_texto = tracker.latest_message.get('text', '')
        
        # Extraer solo los dígitos del mensaje
        nip_numeros = ''.join(filter(str.isdigit, mensaje_texto))
        
        # Validar que el NIP tenga exactamente 4 dígitos
        if len(nip_numeros) == 4:
            # NIP válido - continuar al IMEI (NO terminar aquí)
            # Enviar imagen de instrucciones para obtener IMEI
            dispatcher.utter_message(image=ImageConfig.COMO_OBTENER_IMEI)
            
            mensaje_confirmacion = f"""
✅ ¡Perfecto! Tu NIP **{nip_numeros}** ha sido registrado correctamente.

📱 Ahora vamos a verificar si tu teléfono es compatible con nuestra red.

🔹 Marca **#06#** en el teclado de tu teléfono
🔹 Copia el número que aparece (es tu IMEI)
🔹 Pégalo aquí en el chat y lo validamos al instante ⚡

¿Listo para probarlo? 😎
            """
            dispatcher.utter_message(text=mensaje_confirmacion)
            
            return [
                SlotSet("nip_usuario", nip_numeros),
                SlotSet("estado_menu", "validar_imei")
            ]
        elif len(nip_numeros) > 0 and len(nip_numeros) != 4:
            # NIP con número incorrecto de dígitos
            mensaje_error = f"""
⚠️ El NIP debe tener exactamente 4 dígitos.

Recibí: **{nip_numeros}** ({len(nip_numeros)} dígitos)

📝 Por favor, escríbeme tu NIP de 4 dígitos exactamente como te llegó:

💡 Ejemplo: 1234
            """
            dispatcher.utter_message(text=mensaje_error)
            return [SlotSet("estado_menu", "capturar_nip")]
        
        else:
            # No se encontraron números en el mensaje
            mensaje_error = """
❌ No pude encontrar números en tu mensaje.

📝 Por favor, escríbeme tu NIP de 4 dígitos:

💡 Ejemplo: 1234

O escribe "0" para volver al menú principal.
            """
            dispatcher.utter_message(text=mensaje_error)
            return [SlotSet("estado_menu", "capturar_nip")]
    
    def _manejar_submenu_soporte(self, dispatcher, numero_opcion):
        """Maneja las opciones del submenú de soporte"""
        if numero_opcion == "0":
            return self._mostrar_menu_principal(dispatcher)
        else:
            # Para cualquier otra entrada, mostrar el mensaje de soporte de nuevo
            mensaje = """
👥 SOPORTE - Contacta a nuestro equipo

📲WhatsApp: +52 614 558 7289

🗣️ Mensaje sugerido:
"Hola, vengo del bot de Spotty y necesito ayuda"

⚡ Nuestro equipo te ayudará con:
• Resolver dudas sobre servicios
• Información técnica
• Proceso de activación
• Cualquier consulta que tengas

🕒 Horarios de atención:
• Lunes a Viernes: 9:00 - 18:00
• Sábados: 9:00 - 14:00

0️⃣ Volver al menú principal
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_soporte")]
    
    def _manejar_submenu_recargas(self, dispatcher, numero_opcion):
        """Maneja las opciones del submenú de recargas celulares"""
        if numero_opcion == "0":
            return self._mostrar_menu_principal(dispatcher)
        
        elif numero_opcion == "1":
            # Información del paquete S1 $30 (3 días)
            mensaje = """
📱 PAQUETE S1 $30 - 3 días

✅ 2 GB + Redes sociales ilimitadas
💡 Perfecto para uso básico de pocos días

📋 Características detalladas:
• Datos: 2 GB + redes sociales ilimitadas
• Vigencia: 3 días
• Precio: $30 pesos
• Ideal para emergencias o uso ocasional

🔄 Recarga rápida y económica
📞 Compatible con todas las redes

👇 ¿Qué quieres hacer?

1️⃣ Activar este paquete.
2️⃣ Ver otros paquetes.
0️⃣ Volver al menú principal.
            """
            dispatcher.utter_message(
                text=mensaje,
                buttons=[
                    {"title": "1️⃣ Activar paquete $30", "payload": "1"},
                    {"title": "2️⃣ Ver otros paquetes", "payload": "2"},
                    {"title": "0️⃣ Menú principal", "payload": "0"}
                ]
            )
            return [SlotSet("estado_menu", "submenu_paquete_s30")]
        
        elif numero_opcion == "2":
            # Información del paquete S1 $50 (7 días)
            mensaje = """
📱 PAQUETE S1 $50 - 7 días

✅ 3 GB + Hotspot incluido
🎯 Ideal para una semana de uso moderado

📋 Características detalladas:
• Datos: 3 GB + Hotspot incluido
• Vigencia: 7 días
• Precio: $50 pesos
• Funcionalidad Hotspot para compartir internet

🔄 Recarga semanal perfecta
📞 Compatible con todas las redes

👇 ¿Qué quieres hacer?

1️⃣ Activar este paquete.
2️⃣ Ver otros paquetes.
0️⃣ Volver al menú principal.
            """
            dispatcher.utter_message(
                text=mensaje,
                buttons=[
                    {"title": "1️⃣ Activar paquete $50", "payload": "1"},
                    {"title": "2️⃣ Ver otros paquetes", "payload": "2"},
                    {"title": "0️⃣ Menú principal", "payload": "0"}
                ]
            )
            return [SlotSet("estado_menu", "submenu_paquete_s50")]
        
        elif numero_opcion == "3":
            # Información del paquete S1 M100
            mensaje = """
📱 PAQUETE S1 M100 - $100 / 30 días

✅ 2 GB + Redes sociales ilimitadas
📱 Plan básico mensual

📋 Características detalladas:
• Datos: 2 GB + redes sociales ilimitadas
• Vigencia: 30 días
• Precio: $100 pesos
• Perfecto para uso básico mensual

🔄 Recarga automática disponible
📞 Compatible con todas las redes

👇 ¿Qué quieres hacer?

1️⃣ Activar este paquete.
2️⃣ Ver otros paquetes.
0️⃣ Volver al menú principal.
            """
            dispatcher.utter_message(
                text=mensaje,
                buttons=[
                    {"title": "1️⃣ Activar este paquete", "payload": "1"},
                    {"title": "2️⃣ Ver otros paquetes", "payload": "2"},
                    {"title": "0️⃣ Menú principal", "payload": "0"}
                ]
            )
            return [SlotSet("estado_menu", "submenu_paquete_m100")]
        
        elif numero_opcion == "4":
            # Información del paquete S1 M120
            mensaje = """
📱 PAQUETE S1 M120 - $120 / 30 días

✅ 3 GB + redes sociales ilimitadas
📱 Plan intermedio mensual

📋 Características detalladas:
• Datos: 3 GB + redes sociales ilimitadas
• Vigencia: 30 días
• Precio: $120 pesos
• Ideal para uso moderado mensual

🔄 Recarga automática disponible
📞 Compatible con todas las redes

👇 ¿Qué quieres hacer?

1️⃣ Activar este paquete.
2️⃣ Ver otros paquetes.
0️⃣ Volver al menú principal.
            """
            dispatcher.utter_message(
                text=mensaje,
                buttons=[
                    {"title": "1️⃣ Activar este paquete", "payload": "1"},
                    {"title": "2️⃣ Ver otros paquetes", "payload": "2"},
                    {"title": "0️⃣ Menú principal", "payload": "0"}
                ]
            )
            return [SlotSet("estado_menu", "submenu_paquete_m120")]
        
        elif numero_opcion == "5":
            # Información del paquete S1 M220
            mensaje = """
📱 PAQUETE S1 M220 - $220 / 30 días

✅ ¡72 GB por promoción!
✅ 1,500 minutos + 250 SMS
✅ Comparte tus datos
⚡¡Potencia para gamers, trabajo remoto o compartir internet!

📋 Características detalladas:
• Datos: 72 GB de navegación de alta velocidad
• Llamadas: 1,500 minutos nacionales
• SMS: 250 mensajes de texto
• Vigencia: 30 días
• Precio: $220 pesos
• Compartición de datos incluida
• Ideal para uso intensivo

🔄 Recarga automática disponible
📞 Compatible con todas las redes

👇 ¿Qué quieres hacer?

1️⃣ Activar este paquete.
2️⃣ Ver otros paquetes.
0️⃣ Volver al menú principal.
            """
            dispatcher.utter_message(
                text=mensaje,
                buttons=[
                    {"title": "1️⃣ Activar este paquete", "payload": "1"},
                    {"title": "2️⃣ Ver otros paquetes", "payload": "2"},
                    {"title": "0️⃣ Menú principal", "payload": "0"}
                ]
            )
            return [SlotSet("estado_menu", "submenu_paquete_m220")]
        
        elif numero_opcion == "6":
            # Contactar al equipo para realizar recarga
            mensaje = """
👥 CONTACTA A NUESTRO EQUIPO PARA RECARGAS

📲 WhatsApp: +52 614 558 7289

🗣️ Mensaje sugerido:
"Hola, vengo del bot de BotMobile y quiero hacer una recarga celular"

⚡ Nuestro equipo te ayudará con:
• Activación de cualquier paquete de recarga
• Configuración de recarga automática
• Resolución de dudas sobre los paquetes
• Proceso de activación y facturación

🕒 Horarios de atención:
• Lunes a Viernes: 9:00 - 18:00
• Sábados: 9:00 - 14:00

0️⃣ Volver al menú principal.
            """
            dispatcher.utter_message(
                text=mensaje,
                buttons=[
                    {"title": "0️⃣ Menú principal", "payload": "0"}
                ]
            )
            return [SlotSet("estado_menu", "submenu_recargas")]
        
        else:
            # Opción no válida
            dispatcher.utter_message(text="Opción no válida. Por favor selecciona una opción del menú de recargas.")
            dispatcher.utter_message(
                text="👇 ¿Qué paquete te interesa?",
                buttons=[
                    {"title": "1️⃣ S30 - $30 (3 días)", "payload": "1"},
                    {"title": "2️⃣ S50 - $50 (7 días)", "payload": "2"},
                    {"title": "3️⃣ M100 - $100 (30 días)", "payload": "3"},
                    {"title": "4️⃣ M120 - $120 (30 días)", "payload": "4"},
                    {"title": "5️⃣ M220 - $220 (30 días)", "payload": "5"},
                    {"title": "6️⃣ Hablar con el equipo", "payload": "6"},
                    {"title": "0️⃣ Menú principal", "payload": "0"}
                ]
            )
            return [SlotSet("estado_menu", "submenu_recargas")]
    
    def _manejar_submenu_paquete_individual(self, dispatcher, numero_opcion, estado_actual):
        """Maneja las opciones de los submenús de paquetes individuales"""
        if numero_opcion == "0":
            return self._mostrar_menu_principal(dispatcher)
        
        elif numero_opcion == "1":
            # Activar el paquete - solicitar número de teléfono
            paquete_info = ""
            paquete_precio = ""
            if estado_actual == "submenu_paquete_s30":
                paquete_info = "S30"
                paquete_precio = "$30"
            elif estado_actual == "submenu_paquete_s50":
                paquete_info = "S50"
                paquete_precio = "$50"
            elif estado_actual == "submenu_paquete_m100":
                paquete_info = "S1 M100"
                paquete_precio = "$100"
            elif estado_actual == "submenu_paquete_m120":
                paquete_info = "S1 M120" 
                paquete_precio = "$120"
            elif estado_actual == "submenu_paquete_m220":
                paquete_info = "S1 M220"
                paquete_precio = "$220"
            
            mensaje = f"""
� ACTIVAR PAQUETE {paquete_info} - {paquete_precio}

Para procesar tu recarga necesitamos el número de teléfono.

📞 Por favor escribe el número de teléfono al que quieres hacer la recarga:

💡 Ejemplo: 5512345678 o 55 1234 5678

⚠️ Importante: El número debe estar registrado como cliente de Spot1Mobile para poder procesar la recarga.

0️⃣ Cancelar y volver al menú principal.
            """
            dispatcher.utter_message(
                text=mensaje,
                buttons=[
                    {"title": "0️⃣ Cancelar", "payload": "0"}
                ]
            )
            return [
                SlotSet("estado_menu", f"capturar_numero_{estado_actual.split('_')[-1]}"),
                SlotSet("paquete_seleccionado", estado_actual.split('_')[-1])
            ]
        
        elif numero_opcion == "2":
            # Ver otros paquetes - volver al menú de recargas
            mensaje = """
📱 RECARGAS CELULARES

¡Conoce nuestros paquetes de recargas disponibles!

🔸 Paquete S30 – $30 / 3 días
✅ 1 GB de navegación
💡 Perfecto para uso temporal y emergencias.

🔸 Paquete S50 – $50 / 7 días  
✅ 3 GB + Hotspot incluido
🎯 Ideal para una semana de uso moderado.

🔸 Paquete S1 M100 – $100 / 30 días
✅ 2 GB + redes sociales ilimitadas
💡 Plan básico mensual perfecto.

🔸 Paquete S1 M120 – $120 / 30 días
✅ 3 GB + redes sociales ilimitadas
🎥 Para uso moderado mensual.

🔸 Paquete S1 M220 – $220 / 30 días
✅ ¡72 GB por promoción!
✅ 1,500 minutos + 250 SMS
✅ Comparte tus datos
⚡¡Potencia para gamers, trabajo remoto o compartir internet!

👇 ¿Qué paquete te interesa?

1️⃣ S30 - $30 (3 días)
2️⃣ S50 - $50 (7 días)
3️⃣ M100 - $100 (30 días)
4️⃣ M120 - $120 (30 días)
5️⃣ M220 - $220 (30 días)
6️⃣ Hablar con el equipo
0️⃣ Volver al menú principal.
            """
            dispatcher.utter_message(
                text=mensaje,
                buttons=[
                    {"title": "1️⃣ S30 - $30 (3 días)", "payload": "1"},
                    {"title": "2️⃣ S50 - $50 (7 días)", "payload": "2"},
                    {"title": "3️⃣ M100 - $100 (30 días)", "payload": "3"},
                    {"title": "4️⃣ M120 - $120 (30 días)", "payload": "4"},
                    {"title": "5️⃣ M220 - $220 (30 días)", "payload": "5"},
                    {"title": "6️⃣ Hablar con el equipo", "payload": "6"},
                    {"title": "0️⃣ Menú principal", "payload": "0"}
                ]
            )
            return [SlotSet("estado_menu", "submenu_recargas")]
        
        else:
            # Opción no válida
            dispatcher.utter_message(text="Opción no válida. Por favor selecciona una opción válida.")
            return [SlotSet("estado_menu", estado_actual)]
    
    def _manejar_captura_numero_recarga(self, dispatcher, tracker, estado_actual):
        """Maneja la captura del número de teléfono para recarga"""
        mensaje_texto = tracker.latest_message.get('text', '').strip()
        
        # Si usuario envía "0", cancelar y volver al menú
        if mensaje_texto == "0":
            return self._mostrar_menu_principal(dispatcher)
        
        # Limpiar el número (quitar espacios, guiones, etc.)
        numero_limpio = ''.join(filter(str.isdigit, mensaje_texto))
        
        # Validar formato del número (10 dígitos)
        if len(numero_limpio) == 10:
            # Número válido, mostrar opciones de método de pago
            paquete_tipo = estado_actual.split('_')[-1]  # m100, m120, o m220
            return self._mostrar_metodos_pago(dispatcher, numero_limpio, paquete_tipo)
        
        elif len(numero_limpio) == 12 and numero_limpio.startswith('52'):
            # Número con código de país (+52), extraer los 10 dígitos
            numero_limpio = numero_limpio[2:]
            paquete_tipo = estado_actual.split('_')[-1]
            return self._mostrar_metodos_pago(dispatcher, numero_limpio, paquete_tipo)
        
        else:
            # Número inválido
            mensaje_error = """
❌ Número de teléfono inválido

El número debe tener 10 dígitos. Por favor intenta de nuevo:

📞 Ejemplos válidos:
• 5512345678
• 55 1234 5678
• 551-234-5678

Por favor escribe el número de teléfono correctamente:

0️⃣ Cancelar y volver al menú principal.
            """
            dispatcher.utter_message(
                text=mensaje_error,
                buttons=[
                    {"title": "0️⃣ Cancelar", "payload": "0"}
                ]
            )
            return [SlotSet("estado_menu", estado_actual)]
    
    def _mostrar_metodos_pago(self, dispatcher, numero_telefono, paquete_tipo):
        """Muestra las opciones de método de pago disponibles"""
        # Mapeo de información de paquetes con datos reales de BD
        paquetes_info = {
            's30': {'nombre': 'S30', 'precio': 30, 'duracion': '3 días', 'datos': '1 GB'},
            's50': {'nombre': 'S50', 'precio': 50, 'duracion': '7 días', 'datos': '3 GB + Hotspot'},
            'm100': {'nombre': 'S1 M100', 'precio': 100, 'duracion': '30 días', 'datos': '2 GB + Redes sociales ilimitadas'},
            'm120': {'nombre': 'S1 M120', 'precio': 120, 'duracion': '30 días', 'datos': '3 GB + Redes sociales ilimitadas'},
            'm220': {'nombre': 'S1 M220', 'precio': 220, 'duracion': '30 días', 'datos': '72 GB + 1,500 min + 250 SMS'}
        }
        
        paquete = paquetes_info.get(paquete_tipo, {'nombre': 'Desconocido', 'precio': 0})
        
        mensaje = f"""
💳 ELIGE TU MÉTODO DE PAGO

📱 Paquete: {paquete['nombre']} - ${paquete['precio']}
📞 Número: {numero_telefono}

Selecciona cómo quieres pagar tu recarga:

🔍 1️⃣ Pago con QR CoDi
• Escanea el código QR con tu app bancaria
• Pago inmediato desde tu celular
• Activación automática al confirmar el pago

🏪 2️⃣ Pago en tienda (Referencia SPEI)
• Paga en tiendas físicas con una referencia
• 7-Eleven, Walmart, Farmacias, MTCenter, etc.
• Efectivo o tarjeta en el establecimiento

👇 ¿Cómo prefieres pagar?

0️⃣ Cancelar y volver al menú principal.
        """
        
        dispatcher.utter_message(
            text=mensaje,
            buttons=[
                {"title": "🔍 QR CoDi (App bancaria)", "payload": "codi"},
                {"title": "🏪 Referencia en tienda", "payload": "spei"},
                {"title": "0️⃣ Cancelar", "payload": "0"}
            ]
        )
        
        return [
            SlotSet("estado_menu", f"elegir_pago_{paquete_tipo}"),
            SlotSet("numero_recarga", numero_telefono),
            SlotSet("paquete_seleccionado", paquete_tipo)
        ]
    
    def _manejar_seleccion_pago(self, dispatcher, tracker, estado_actual, numero_opcion):
        """Maneja la selección del método de pago (CoDi o SPEI)"""
        print(f"DEBUG: _manejar_seleccion_pago INICIADA con numero_opcion='{numero_opcion}'")
        
        if numero_opcion == "0":
            return self._mostrar_menu_principal(dispatcher)
        
        # Obtener datos guardados en slots
        numero_telefono = tracker.get_slot("numero_recarga")
        paquete_tipo = tracker.get_slot("paquete_seleccionado")
        
        if not numero_telefono or not paquete_tipo:
            dispatcher.utter_message(text="❌ Error: Datos de sesión perdidos. Por favor inicia de nuevo.")
            return self._mostrar_menu_principal(dispatcher)
        
        if numero_opcion == "codi":
            # Usuario eligió pago con QR CoDi
            return self._generar_qr_pago(dispatcher, tracker, numero_telefono, paquete_tipo)
        
        elif numero_opcion == "spei":
            # Usuario eligió pago con referencia SPEI
            return self._generar_referencia_spei(dispatcher, tracker, numero_telefono, paquete_tipo)
        
        else:
            # Opción no válida, mostrar de nuevo las opciones
            paquetes_info = {
                's30': {'nombre': 'S30', 'precio': 30},
                's50': {'nombre': 'S50', 'precio': 50},
                'm100': {'nombre': 'S1 M100', 'precio': 100},
                'm120': {'nombre': 'S1 M120', 'precio': 120},
                'm220': {'nombre': 'S1 M220', 'precio': 220}
            }
            
            paquete = paquetes_info.get(paquete_tipo, {'nombre': 'Desconocido', 'precio': 0})
            
            mensaje = f"""
❌ Opción no válida

Por favor selecciona un método de pago válido:

📱 Paquete: {paquete['nombre']} - ${paquete['precio']}
📞 Número: {numero_telefono}

👇 ¿Cómo prefieres pagar?
            """
            
            dispatcher.utter_message(
                text=mensaje,
                buttons=[
                    {"title": "🔍 QR CoDi (App bancaria)", "payload": "codi"},
                    {"title": "🏪 Referencia en tienda", "payload": "spei"},
                    {"title": "0️⃣ Cancelar", "payload": "0"}
                ]
            )
            return [SlotSet("estado_menu", estado_actual)]
    
    def _generar_qr_pago(self, dispatcher, tracker, numero_telefono, paquete_tipo):
        """Genera el QR de pago usando la API de CoDi"""
        print(f"DEBUG: _generar_qr_pago INICIADA con numero={numero_telefono}, paquete={paquete_tipo}")
        
        import requests
        import json
        
        # Mostrar mensaje de validación
        dispatcher.utter_message(text="🔄 **Generando tu código QR...**\n\n⏳ Por favor espera mientras validamos tu número y procesamos tu solicitud de pago.\n\nEsto puede tomar unos segundos...")
        
        # Mapeo de paquetes a rate_id y offerID - DATOS REALES DE BD
        paquetes_info = {
            's30': {
                'rate_id': 36,
                'offerID': '180990536',
                'amount': 30,
                'nombre': 'S30',
                'descripcion': '1 GB por 3 días'
            },
            's50': {
                'rate_id': 37,
                'offerID': '180990537',
                'amount': 50,
                'nombre': 'S50',
                'descripcion': '3 GB + Hotspot por 7 días'
            },
            'm100': {
                'rate_id': 38,
                'offerID': '180990538',
                'amount': 100,
                'nombre': 'S1 M100',
                'descripcion': '2 GB + Redes sociales ilimitadas por 30 días'
            },
            'm120': {
                'rate_id': 39,
                'offerID': '180990539',
                'amount': 120,
                'nombre': 'S1 M120',
                'descripcion': '3 GB + Redes sociales ilimitadas por 30 días'
            },
            'm220': {
                'rate_id': 40,
                'offerID': '180990540',
                'amount': 220,
                'nombre': 'S1 M220',
                'descripcion': '72 GB + 1,500 min + 250 SMS por 30 días'
            }
        }
        
        if paquete_tipo not in paquetes_info:
            dispatcher.utter_message(text="❌ Error: Paquete no encontrado.")
            return self._mostrar_menu_principal(dispatcher)
        
        paquete = paquetes_info[paquete_tipo]
        
        # Preparar datos para la API
        payload = {
            'rate_id': paquete['rate_id'],
            'offerID': paquete['offerID'],
            'number': numero_telefono,
            'amount': paquete['amount'],
            'type': 'codi',
            'description': f'Recarga {paquete["nombre"]} - BotMobile'
        }
        
        try:
            # Llamar a la API de CoDi
            response = requests.post(
                'https://apps-ws.spot1.mx/reference-codi',
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Enviar confirmación con QR
                mensaje_exito = f"""
✅ ¡QR de pago generado exitosamente!

📱 **Paquete:** {paquete['nombre']} - ${paquete['amount']}
📞 **Número:** {numero_telefono}
💰 **Monto:** ${paquete['amount']} pesos
📅 **Vigencia:** 30 días

🔍 **Referencia:** {data['reference']}
⏰ **Expira:** {data['expiration_date'][:19].replace('T', ' ')}

📲 **Para completar tu pago:**
1. Escanea el código QR con tu app bancaria
2. Autoriza el pago CoDi
3. Tu recarga se activará automáticamente

**Características del paquete:**
{paquete['descripcion']}

0️⃣ Volver al menú principal.
                """
                
                # Enviar QR como imagen
                dispatcher.utter_message(image=data['qr'])
                
                dispatcher.utter_message(
                    text=mensaje_exito,
                    buttons=[
                        {"title": "0️⃣ Menú principal", "payload": "0"}
                    ]
                )
                
                return [
                    SlotSet("estado_menu", "esperando_pago"),
                    SlotSet("referencia_pago", data['reference']),
                    SlotSet("numero_recarga", numero_telefono)
                ]
            
            else:
                # Error en la API
                if response.status_code == 500:
                    mensaje_error = f"""
❌ Número no registrado

El número {numero_telefono} no está registrado como cliente de Spot1Mobile.

Para usar nuestros servicios de recarga, primero necesitas:

1️⃣ Registrarte como cliente
2️⃣ Activar una línea con nosotros

📲 **Contacta a nuestro equipo:**
WhatsApp: +52 614 558 7289

🕒 Horarios:
• Lunes a Viernes: 9:00 - 18:00  
• Sábados: 9:00 - 14:00

0️⃣ Volver al menú principal.
                    """
                else:
                    mensaje_error = f"""
❌ Error al generar el pago

Código de error: {response.status_code}

Por favor contacta a nuestro equipo de soporte:

📲 WhatsApp: +52 614 558 7289

0️⃣ Volver al menú principal.
                    """
                
                dispatcher.utter_message(
                    text=mensaje_error,
                    buttons=[
                        {"title": "0️⃣ Menú principal", "payload": "0"}
                    ]
                )
                return [SlotSet("estado_menu", "menu_principal")]
        
        except requests.exceptions.Timeout:
            dispatcher.utter_message(
                text="❌ **Tiempo de espera agotado**\n\nPor favor intenta de nuevo más tarde o contacta a soporte.\n\n📲 WhatsApp: +52 614 558 7289",
                buttons=[{"title": "0️⃣ Menú principal", "payload": "0"}]
            )
            return [SlotSet("estado_menu", "menu_principal")]
        
        except requests.exceptions.RequestException as e:
            dispatcher.utter_message(
                text="❌ **Error de conexión**\n\nPor favor verifica tu conexión a internet e intenta de nuevo.\n\n📲 WhatsApp: +52 614 558 7289",
                buttons=[{"title": "0️⃣ Menú principal", "payload": "0"}]
            )
            return [SlotSet("estado_menu", "menu_principal")]
        
        except Exception as e:
            logger.error(f"Error generando QR de pago: {e}")
            dispatcher.utter_message(
                text="❌ **Error inesperado**\n\nPor favor contacta a nuestro equipo de soporte.\n\n📲 WhatsApp: +52 614 558 7289",
                buttons=[{"title": "0️⃣ Menú principal", "payload": "0"}]
            )
            return [SlotSet("estado_menu", "menu_principal")]
    
    def _generar_referencia_spei(self, dispatcher, tracker, numero_telefono, paquete_tipo):
        """Genera referencia SPEI para pago en tienda"""
        
        # Mostrar mensaje de validación  
        dispatcher.utter_message(text="🏪 **Generando tu referencia de pago...**\n\n⏳ Por favor espera mientras validamos tu número y generamos tu referencia para pago en tienda.\n\nEsto puede tomar unos segundos...")
        
        # Mapeo de paquetes a rate_id y offerID - DATOS REALES DE BD
        paquetes_info = {
            's30': {
                'rate_id': 36,
                'offerID': '180990536',
                'amount': 30,
                'nombre': 'S30',
                'descripcion': '1 GB por 3 días'
            },
            's50': {
                'rate_id': 37,
                'offerID': '180990537',
                'amount': 50,
                'nombre': 'S50',
                'descripcion': '3 GB + Hotspot por 7 días'
            },
            'm100': {
                'rate_id': 38,
                'offerID': '180990538',
                'amount': 100,
                'nombre': 'S1 M100',
                'descripcion': '2 GB + Redes sociales ilimitadas por 30 días'
            },
            'm120': {
                'rate_id': 39,
                'offerID': '180990539',
                'amount': 120,
                'nombre': 'S1 M120',
                'descripcion': '3 GB + Redes sociales ilimitadas por 30 días'
            },
            'm220': {
                'rate_id': 40,
                'offerID': '180990540',
                'amount': 220,
                'nombre': 'S1 M220',
                'descripcion': '72 GB + 1,500 min + 250 SMS por 30 días'
            }
        }
        
        if paquete_tipo not in paquetes_info:
            dispatcher.utter_message(text="❌ Error: Paquete no encontrado.")
            return self._mostrar_menu_principal(dispatcher)
        
        paquete = paquetes_info[paquete_tipo]
        
        # Preparar datos para la API SPEI
        payload = {
            'rate_id': paquete['rate_id'],
            'offerID': paquete['offerID'],
            'number': numero_telefono,
            'amount': paquete['amount'],
            'type': 'spei',
            'description': f'Recarga {paquete["nombre"]} - BotMobile SPEI'
        }
        
        try:
            # Llamar a la API de SPEI (mismo endpoint, diferente tipo)
            response = requests.post(
                'https://apps-ws.spot1.mx/reference-codi',
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Enviar confirmación con referencia SPEI
                mensaje_exito = f"""
✅ ¡Referencia de pago generada exitosamente!

📱 **Paquete:** {paquete['nombre']} - ${paquete['amount']}
📞 **Número:** {numero_telefono}
💰 **Monto:** ${paquete['amount']} pesos
📅 **Vigencia:** 30 días

💳 **REFERENCIA DE PAGO:** {data['reference']}
⏰ **Expira:** {data['expiration_date'][:19].replace('T', ' ')}

🏪 ¿DÓNDE PAGAR?
Solicita "PAGO DAPP" en:
• 7-Eleven
• Kiosko  
• Farmapronto
• MTCenter
• Pagaqui
• Sys

Solicita "PAGO PESPAY" en:
• Walmart
• Farmacias Guadalajara
• Farmacias del Ahorro

📋 INSTRUCCIONES:
1. Ve a cualquiera de las tiendas mencionadas
2. Proporciona la referencia: {data['reference']}
3. Paga ${paquete['amount']} pesos en efectivo o tarjeta
4. Tu recarga se activará automáticamente

Características del paquete:
{paquete['descripcion']}

⚠️ Importante: Guarda esta referencia hasta completar tu pago.

0️⃣ Volver al menú principal.
                """
                
                dispatcher.utter_message(
                    text=mensaje_exito,
                    buttons=[
                        {"title": "0️⃣ Menú principal", "payload": "0"}
                    ]
                )
                
                return [
                    SlotSet("estado_menu", "esperando_pago_spei"),
                    SlotSet("referencia_pago", data['reference']),
                    SlotSet("numero_recarga", numero_telefono),
                    SlotSet("tipo_pago", "spei")
                ]
            
            else:
                # Error en la API
                if response.status_code == 500:
                    mensaje_error = f"""
❌ Número no registrado

El número {numero_telefono} no está registrado como cliente de Spot1Mobile.

Para usar nuestros servicios de recarga, primero necesitas:

1️⃣ Registrarte como cliente
2️⃣ Activar una línea con nosotros

📲 Contacta a nuestro equipo:
WhatsApp: +52 614 558 7289

🕒 Horarios:
• Lunes a Viernes: 9:00 - 18:00  
• Sábados: 9:00 - 14:00

0️⃣ Volver al menú principal.
                    """
                else:
                    mensaje_error = f"""
❌ Error al generar la referencia

Código de error: {response.status_code}

Por favor contacta a nuestro equipo de soporte:

📲 WhatsApp: +52 614 558 7289

0️⃣ Volver al menú principal.
                    """
                
                dispatcher.utter_message(
                    text=mensaje_error,
                    buttons=[
                        {"title": "0️⃣ Menú principal", "payload": "0"}
                    ]
                )
                return [SlotSet("estado_menu", "menu_principal")]
        
        except requests.exceptions.Timeout:
            dispatcher.utter_message(
                text="❌ **Tiempo de espera agotado**\n\nPor favor intenta de nuevo más tarde o contacta a soporte.\n\n📲 WhatsApp: +52 614 558 7289",
                buttons=[{"title": "0️⃣ Menú principal", "payload": "0"}]
            )
            return [SlotSet("estado_menu", "menu_principal")]
        
        except requests.exceptions.RequestException as e:
            dispatcher.utter_message(
                text="❌ **Error de conexión**\n\nPor favor verifica tu conexión a internet e intenta de nuevo.\n\n📲 WhatsApp: +52 614 558 7289",
                buttons=[{"title": "0️⃣ Menú principal", "payload": "0"}]
            )
            return [SlotSet("estado_menu", "menu_principal")]
        
        except Exception as e:
            logger.error(f"Error generando referencia SPEI: {e}")
            dispatcher.utter_message(
                text="❌ **Error inesperado**\n\nPor favor contacta a nuestro equipo de soporte.\n\n📲 WhatsApp: +52 614 558 7289",
                buttons=[{"title": "0️⃣ Menú principal", "payload": "0"}]
            )
            return [SlotSet("estado_menu", "menu_principal")]
    
    def _manejar_validacion_imei(self, dispatcher, tracker):
        """Maneja la validación del IMEI del usuario"""
        mensaje_texto = tracker.latest_message.get('text', '')
        
        # Extraer solo los números del IMEI
        imei_numeros = ''.join(filter(str.isdigit, mensaje_texto))
        
        # Validar que el IMEI tenga exactamente 15 dígitos
        if len(imei_numeros) == 15:
            # IMEI válido - continuar al paso de capturar nombre
            mensaje_confirmacion = f"""
✅ ¡Perfecto! Tu IMEI ha sido verificado.

Finalmente, necesito tu nombre completo para completar tu solicitud.

✍️ Por favor, escríbeme tu nombre y apellidos tal como aparecen en tu identificación.

Ejemplo: Juan Pérez López
            """
            dispatcher.utter_message(text=mensaje_confirmacion)
            
            return [
                SlotSet("imei_usuario", imei_numeros),
                SlotSet("estado_menu", "capturar_nombre"),
                # Preservar slots anteriores
                SlotSet("nip_usuario", tracker.get_slot("nip_usuario")),
                SlotSet("compania_operador", tracker.get_slot("compania_operador")),
                SlotSet("numero_telefono", tracker.get_slot("numero_telefono"))
            ]
        
        elif len(imei_numeros) > 0 and len(imei_numeros) != 15:
            # IMEI con número incorrecto de dígitos
            mensaje_error = f"""
⚠️ El IMEI debe tener exactamente 15 dígitos.

Recibí: {imei_numeros} ({len(imei_numeros)} dígitos)

📱 Por favor, marca **#06#** en tu teléfono y copia el número completo:

💡 Ejemplo: 123456789012345
            """
            dispatcher.utter_message(text=mensaje_error)
            return [SlotSet("estado_menu", "validar_imei")]
        
        else:
            # No se encontraron números en el mensaje
            mensaje_error = """
❌ No pude encontrar números en tu mensaje.

📱 Por favor, marca **#06#** en tu teléfono y copia el IMEI completo:

💡 Debe ser un número de 15 dígitos

O escribe "0" para volver al menú principal.
            """
            dispatcher.utter_message(text=mensaje_error)
            return [SlotSet("estado_menu", "validar_imei")]

    def _manejar_captura_nombre(self, dispatcher, tracker):
        """Maneja la captura del nombre del usuario con validación y normalización mejorada"""
        mensaje_texto = tracker.latest_message.get('text', '').strip()
        
        # Validar y normalizar el nombre usando las nuevas funciones
        es_valido, mensaje_error, nombre_normalizado = self._validar_nombre_persona(mensaje_texto)
        
        if es_valido:
            # Nombre válido - mostrar resumen final directamente
            compania_detectada = tracker.get_slot("compania_operador")
            numero_telefono = tracker.get_slot("numero_telefono")
            nip_usuario = tracker.get_slot("nip_usuario")
            imei_usuario = tracker.get_slot("imei_usuario")
            nombre_usuario = nombre_normalizado  # Usar el nombre normalizado
            
            # DEBUG: Imprimir todos los slots para ver qué está pasando
            print(f"🔍 DEBUG - Valores de slots antes del resumen:")
            print(f"   📧 compania_operador: '{compania_detectada}'")
            print(f"   📞 numero_telefono: '{numero_telefono}'")
            print(f"   🔐 nip_usuario: '{nip_usuario}'")
            print(f"   📱 imei_usuario: '{imei_usuario}'")
            print(f"   👤 nombre_usuario: '{nombre_usuario}'")
            
            # Verificar si algún slot está vacío y usar valores por defecto
            nombre_final = nombre_usuario if nombre_usuario else "No capturado"
            compania_final = compania_detectada if compania_detectada else "Detectada automáticamente"
            numero_final = numero_telefono if numero_telefono else "Registrado automáticamente"
            nip_final = nip_usuario if nip_usuario else "No capturado"
            imei_final = imei_usuario if imei_usuario else "No capturado"
            
            mensaje_final = f"""
✅ ¡Perfecto! Ya tengo toda tu información.

📋 RESUMEN DE TU PORTABILIDAD:
• Nombre: {nombre_final}
• Compañía actual: {compania_final}
• Número a portar: {numero_final}
• NIP: {nip_final}
• IMEI: {imei_final}

� Nuestro equipo se pondrá en contacto para completar tu portabilidad.
Si prefieres, puedes escribirnos ahora por WhatsApp: +52 614 558 7289

0️⃣ Menú principal
            """
            dispatcher.utter_message(text=mensaje_final)
            #nuevo mensaje 
            dispatcher.utter_message(text="msj3")
            
            # NO mostrar menú principal automáticamente - solo si el usuario escribe 0
            
            return [
                SlotSet("nombre_usuario", nombre_usuario),
                SlotSet("estado_menu", "menu_principal"),
                # Preservar slots anteriores
                SlotSet("nip_usuario", nip_usuario),
                SlotSet("imei_usuario", imei_usuario),
                SlotSet("compania_operador", compania_detectada),
                SlotSet("numero_telefono", numero_telefono)
            ]
        else:
            # Nombre no válido - usar el mensaje de error específico
            mensaje_completo = f"""
⚠️ {mensaje_error}

✍️ Ejemplos válidos:
• Juan Pérez
• María López García  
• Carlos de la Cruz
• Ana María Rodríguez López
• Hugo Alfredo Díaz Infante López

Por favor intenta de nuevo o escribe "0" para volver al menú principal.
            """
            dispatcher.utter_message(text=mensaje_completo)
            return [SlotSet("estado_menu", "capturar_nombre")]

class ActionDefaultFallback(Action):
    """Acción de fallback mejorada con análisis contextual"""
    
    def name(self) -> Text:
        return "action_default_fallback"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        texto_usuario = tracker.latest_message.get('text', '').lower()
        estado_actual = tracker.get_slot("estado_menu")
        
        # � ANÁLISIS CONTEXTUAL: Intentar entender la intención
        palabras_portabilidad = ["portabilidad", "conservar", "mantener", "número", "cambiar", "operador"]
        palabras_planes = ["planes", "paquetes", "precio", "costo", "tarifa", "oferta", "promoción"]
        palabras_contacto = ["contacto", "hablar", "persona", "humano", "whatsapp", "teléfono"]
        
        if any(palabra in texto_usuario for palabra in palabras_portabilidad):
            dispatcher.utter_message(text="🎯 ¡Entiendo! Te interesa la portabilidad.")
            dispatcher.utter_message(text="🔄 PORTABILIDAD")
            dispatcher.utter_message(text="1️⃣ ¿Cómo conseguir NIP?\n2️⃣ Ya tengo mi NIP\n3️⃣ Volver al menú")
            dispatcher.utter_message(text="¿Qué opción necesitas?")
            return [SlotSet("estado_menu", "submenu_portabilidad")]
            
        elif any(palabra in texto_usuario for palabra in palabras_planes):
            dispatcher.utter_message(text="💰 ¡Perfecto! Te interesan nuestros planes.")
            dispatcher.utter_message(image=ImageConfig.PAQUETES_PROMOCION)
            dispatcher.utter_message(text="📦 PAQUETES DISPONIBLES")
            dispatcher.utter_message(text="1️⃣ Plan Ilimitado $220\n2️⃣ Plan Premium $300\n3️⃣ Volver al menú")
            dispatcher.utter_message(text="¿Qué opción te interesa?")
            return [SlotSet("estado_menu", "submenu_paquetes")]
            
        elif any(palabra in texto_usuario for palabra in palabras_contacto):
            dispatcher.utter_message(text="👥 ¡Claro! Te conectamos con nuestro equipo.")
            dispatcher.utter_message(text="📲 WhatsApp: +52 614 558 7289")
            dispatcher.utter_message(text="⏰ Horarios: Lun-Vie 9-18hrs, Sáb 9-14hrs")
            dispatcher.utter_message(text="0️⃣ Volver al menú principal")
            return [SlotSet("estado_menu", "contacto")]
        
        # Fallback genérico con sugerencias inteligentes
        texto_corto = tracker.latest_message.get('text', '')[:30]
        dispatcher.utter_message(text=f"🤔 No entendí '{texto_corto}...'")
        dispatcher.utter_message(text="💡 Puedes escribir: 'portabilidad', 'planes' o 'contacto'")
        dispatcher.utter_message(text="🏠 MENÚ PRINCIPAL")
        dispatcher.utter_message(text="1️⃣ Conservar mi número\n2️⃣ Ver paquetes\n3️⃣ Hablar con el equipo")
        dispatcher.utter_message(text="¿Qué opción necesitas?")
        
        return [SlotSet("estado_menu", "menu_principal")]


class ActionInicioNodeRed(Action):
    """Acción específica para el inicio del flujo Node-RED"""
    
    def name(self) -> Text:
        return "action_inicio_node_red"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Mensaje de inicio que será interceptado por Node-RED
        mensaje_inicio = """🚀 Iniciando integración con Node-RED...

📱 Por favor, proporciona tu número celular para consultar tu operador."""
        
        response_data = {
            "text": mensaje_inicio,
            "metadata": {
                "type": "node_red_start",
                "next_step": "phone_input"
            }
        }
        
        dispatcher.utter_message(text=mensaje_inicio)
        dispatcher.utter_message(json_message=response_data)
        
        return [SlotSet("node_red_active", True)]


class ActionFinNodeRed(Action):
    """Acción específica para finalizar y regresar el control a Node-RED"""
    
    def name(self) -> Text:
        return "action_fin_node_red"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener información del usuario
        nombre = tracker.get_slot("nombre_usuario") or "Usuario"
        compania = tracker.get_slot("compania_operador") or "tu operador"
        numero = tracker.get_slot("numero_telefono") or "tu número"
        
        # Mensaje de finalización con datos para Node-RED
        mensaje_final = f"""✅ ¡Perfecto, {nombre}!

📋 Resumen de tu solicitud:
• Operador actual: {compania}
• Número: {numero}
• Proceso: Portabilidad a BotMobile

🎯 Nuestro equipo te contactará pronto para completar el proceso.

👥 WhatsApp: +52 614 558 7289

¡Gracias por elegir BotMobile! 🚀"""
        
        response_data = {
            "text": mensaje_final,
            "metadata": {
                "type": "node_red_end",
                "user_data": {
                    "nombre": nombre,
                    "compania": compania,
                    "numero": numero,
                    "nip": tracker.get_slot("nip_usuario"),
                    "imei": tracker.get_slot("imei_usuario")
                },
                "next_action": "complete_process"
            }
        }
        
        dispatcher.utter_message(text=mensaje_final)
        dispatcher.utter_message(json_message=response_data)
        
        return [
            SlotSet("conversation_completed", True),
            SlotSet("node_red_active", False)
        ]
