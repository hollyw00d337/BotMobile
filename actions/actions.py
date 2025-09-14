from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from config.image_config import ImageConfig
import logging
import re

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

☕ ¡Vamos a hacerlo simple! Solo responde con el número de la opción."""
        
        # **CORRECCIÓN NODE-RED**: Enviar un solo mensaje con texto + botones
        dispatcher.utter_message(
            text=mensaje_menu,
            buttons=[
                {"title": "1️⃣ Conservar mi número (portabilidad).", "payload": "1"},
                {"title": "2️⃣ Ver paquetes disponibles.", "payload": "2"},
                {"title": "3️⃣ Hablar con alguien del equipo.", "payload": "3"}
            ]
        )
        
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

1️⃣ Conservar mi número Telcel (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

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

1️⃣ Conservar mi número Movistar (portabilidad)
2️⃣ Ver paquetes disponibles  
3️⃣ Hablar con alguien del equipo

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

1️⃣ Conservar mi número AT&T (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

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

1️⃣ Conservar mi número Unefon (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

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

1️⃣ Conservar mi número Virgin (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

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

1️⃣ Conservar mi número Altan (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

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

1️⃣ Conservar mi número (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

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
                {"title": "3️⃣ Hablar con alguien del equipo.", "payload": "3"}
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

1️⃣ Conservar mi número (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

☕ ¡Vamos a hacerlo simple! Solo responde con el número de la opción.
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

1️⃣ Conservar mi número (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

☕ ¡Vamos a hacerlo simple! Solo responde con el número de la opción.
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

1️⃣ Conservar mi número (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

☕ ¡Vamos a hacerlo simple! Solo responde con el número de la opción.""",

            'AT&T': """🎯 ¡Hola! Veo que eres cliente de AT&T. Te explico cómo cambiarte a BotMobile paso a paso.

💰 **¡Ahorra $180 pesos al mes!**
📱 AT&T: $400/mes por 20GB + HBO Max
🚀 BotMobile: $220/mes por 72GB + Netflix + Disney+ + Prime

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

☕ ¡Vamos a hacerlo simple! Solo responde con el número de la opción.""",

            'Movistar': """🎯 ¡Perfecto! Eres de Movistar. Conozco muy bien el proceso para cambiarte a BotMobile.

💰 **Mejor oferta garantizada:**
📱 Movistar: $250/mes por 12GB + Disney+
🚀 BotMobile: $220/mes por 72GB + Netflix + Disney+ + Prime

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

☕ ¡Vamos a hacerlo simple! Solo responde con el número de la opción.""",

            'Unefon': """🎯 ¡Hola! Vienes de Unefon. Te ayudo a mejorar tu plan con BotMobile.

💰 **Upgrade completo:**
📱 Unefon: $200/mes por 6GB
🚀 BotMobile: $220/mes por 72GB + streaming

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

☕ ¡Solo $20 pesos más por 12x más datos! Solo responde con el número de la opción.""",

            'Virgin': """🎯 ¡Excelente! Eres de Virgin Mobile. Te muestro cómo mejorar con BotMobile.

💰 **Más por menos:**
📱 Virgin: $180/mes por 4GB
🚀 BotMobile: $220/mes por 72GB + plataformas

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

☕ ¡Vamos a hacerlo simple! Solo responde con el número de la opción."""
        }
        
        # Si la compañía no está en el diccionario, usar mensaje genérico
        mensaje_generico = f"""🎯 ¡Perfecto! Vienes de {compania}. Te ayudo con tu portabilidad a BotMobile.

💰 **BotMobile te ofrece:**
📱 72GB por solo $220/mes
🎬 Netflix + Disney+ + Prime incluido
📶 Cobertura nacional garantizada

👇 ¿Qué necesitas hoy?

1️⃣ Conservar mi número (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

☕ ¡Vamos a hacerlo simple! Solo responde con el número de la opción."""
        
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
        
        print(f"DEBUG: estado_actual={estado_actual}, numero_opcion={numero_opcion}, intent={intent}")
        
        estados_texto_libre = ["capturar_nip", "validar_imei", "capturar_nombre"]
        
        if intent == "despedida" and estado_actual not in estados_texto_libre:
            dispatcher.utter_message(text="¡Hasta la vista! 👋 Espero haberte ayudado. Regresa cuando gustes.")
            return []
        
        if estado_actual == "capturar_nip":
            return self._manejar_captura_nip(dispatcher, tracker)
        elif estado_actual == "validar_imei":
            return self._manejar_validacion_imei(dispatcher, tracker)
        elif estado_actual == "capturar_nombre":
            return self._manejar_captura_nombre(dispatcher, tracker)
        
        if not numero_opcion and estado_actual not in estados_texto_libre:
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

1️⃣ Conservar mi número (portabilidad)
2️⃣ Ver paquetes disponibles
3️⃣ Hablar con alguien del equipo

☕ ¡Vamos a hacerlo simple! Solo responde con el número de la opción."""
        
        # **CORRECCIÓN NODE-RED**: Enviar un solo mensaje con texto + botones
        dispatcher.utter_message(
            text=mensaje_menu,
            buttons=[
                {"title": "1️⃣ Conservar mi número (portabilidad).", "payload": "1"},
                {"title": "2️⃣ Ver paquetes disponibles.", "payload": "2"},
                {"title": "3️⃣ Hablar con alguien del equipo.", "payload": "3"}
            ]
        )
        return [SlotSet("estado_menu", "menu_principal")]
    
    def _manejar_menu_principal(self, dispatcher, numero_opcion):
        if numero_opcion == "1":
            # Enviar la imagen de portabilidad primero
            dispatcher.utter_message(image=ImageConfig.PORTABILIDAD_3_PASOS)
            
            mensaje = """🔄 PORTABILIDAD 

1️⃣ ¿Cómo conseguir NIP?
2️⃣ Documentos necesarios
3️⃣ Hablar con equipo
0️⃣ Menú principal

¿Qué opción necesitas?"""
            
            # **CORRECCIÓN NODE-RED**: Enviar un solo mensaje con texto + botones
            dispatcher.utter_message(
                text=mensaje,
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

1️⃣ Conservar mi número con estos paquetes (Portabilidad)
2️⃣ Activar línea nueva con estos paquetes
3️⃣ Hablar con el equipo para más info
0️⃣ Volver al menú principal

Escribe el número de la opción que necesitas 👆
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

0️⃣ Volver al menú principal
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_soporte")]
        
        else:
            dispatcher.utter_message(text="Opción no válida. Por favor elige un número del 1 al 3.")
            return self._mostrar_menu_principal(dispatcher)
    
    def _manejar_submenu_paquetes(self, dispatcher, numero_opcion):
        """Maneja las opciones del submenú de paquetes"""
        if numero_opcion == "0":
            return self._mostrar_menu_principal(dispatcher)
        
        elif numero_opcion == "1":
            # Dirigir al menú de portabilidad
            # Enviar la imagen de portabilidad primero
            dispatcher.utter_message(image=ImageConfig.PORTABILIDAD_3_PASOS)
            
            mensaje = """
🔄 PORTABILIDAD 

¡Perfecto! Vamos a conservar tu número actual y activar uno de nuestros paquetes.

1️⃣ ¿Cómo conseguir NIP?
2️⃣ Documentos necesarios
3️⃣ Hablar con equipo
0️⃣ Menú principal

¿Qué opción necesitas?
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_portabilidad")]
        
        elif numero_opcion == "2":
            # Línea nueva (próximamente)
            mensaje = """
📞 LÍNEA NUEVA 

Esta opción estará disponible muy pronto.

Por ahora puedes:
📲 WhatsApp: +52 614 558 7289

🕒 Horarios de atención:
• Lunes a Viernes: 9:00 - 18:00
• Sábados: 9:00 - 14:00

👇 ¿Qué quieres hacer?

1️⃣ Ver paquetes de nuevo
2️⃣ Ir a portabilidad
0️⃣ Menú principal
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_paquetes")]
        
        elif numero_opcion == "3":
            # Hablar con el equipo
            mensaje = """
👥 Contacta a nuestro equipo

📲 WhatsApp: +52 614 558 7289

⚡ Nuestro equipo te ayudará con:
• Detalles de cada paquete
• Disponibilidad en tu zona
• Proceso de activación
• Resolver cualquier duda

🕒 Horarios de atención:
• Lunes a Viernes: 9:00 - 18:00
• Sábados: 9:00 - 14:00

0️⃣ Volver al menú principal
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_paquetes")]
        
        else:
            # Opción no válida
            mensaje = """
Opción no válida. Por favor elige:

1️⃣ Conservar mi número con estos paquetes (Portabilidad)
2️⃣ Activar línea nueva con estos paquetes
3️⃣ Hablar con el equipo para más info
0️⃣ Volver al menú principal
            """
            dispatcher.utter_message(text=mensaje)
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

1️⃣ Ya tengo mi NIP, quiero avanzar 🚀
2️⃣ ¿Dónde lo escribo?
3️⃣ Quiero hablar con alguien del equipo
            """
            dispatcher.utter_message(text=mensaje_menu_nip)
            return [SlotSet("estado_menu", "submenu_nip")]
        
        elif numero_opcion == "2":
            mensaje = """
📄 Documentos necesarios

Para la portabilidad necesitas:

✅ Identificación oficial vigente
✅ Código IMEI (para eSIM)
✅ NIP de tu compañía actual
✅ Número telefónico a portar

Escribe **0** para volver al menú principal.
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_portabilidad")]
        
        elif numero_opcion == "3":
            # Hablar con el equipo (ahora es la opción 3)
            mensaje = """
👥 Contacta a nuestro equipo

📲 WhatsApp: +52 614 558 7289

⚡ Nuestro equipo te ayudará con:
• Proceso de portabilidad
• Resolver dudas sobre documentos
• Verificar tu NIP
• Completar el trámite

🕒 Horarios de atención:
• Lunes a Viernes: 9:00 - 18:00
• Sábados: 9:00 - 14:00

0️⃣ Volver al menú principal
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_portabilidad")]
        
        else:
            mensaje = """
Opción no válida. 

1️⃣ ¿Cómo conseguir NIP?
2️⃣ Documentos necesarios
3️⃣ Hablar con equipo
0️⃣ Menú principal
            """
            dispatcher.utter_message(text=mensaje)
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

0️⃣ Menú principal
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

0️⃣ Volver al menú principal
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_nip")]
        
        else:
            mensaje = """
Opción no válida. 

1️⃣ Ya tengo mi NIP, quiero avanzar 🚀
2️⃣ ¿Dónde lo escribo?
3️⃣ Quiero hablar con alguien del equipo
0️⃣ Menú principal
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

0️⃣ Volver al menú principal
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

0️⃣ Volver al menú principal
            """
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("estado_menu", "submenu_avanzar_nip")]
        
        else:
            mensaje = """
Opción no válida.

1️⃣ Continuar por WhatsApp
2️⃣ Hablar por teléfono
0️⃣ Volver al menú principal
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

Recibí: **{imei_numeros}** ({len(imei_numeros)} dígitos)

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
        """Maneja la captura del nombre del usuario"""
        mensaje_texto = tracker.latest_message.get('text', '').strip()
        
        # Validar que el nombre no esté vacío y tenga al menos 2 palabras
        if len(mensaje_texto) >= 3 and ' ' in mensaje_texto:
            # Nombre válido - mostrar resumen final directamente
            compania_detectada = tracker.get_slot("compania_operador")
            numero_telefono = tracker.get_slot("numero_telefono")
            nip_usuario = tracker.get_slot("nip_usuario")
            imei_usuario = tracker.get_slot("imei_usuario")
            nombre_usuario = mensaje_texto
            
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

0️⃣ Escribe 0 para volver al menú principal
            """
            dispatcher.utter_message(text=mensaje_final)
            
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
            # Nombre no válido
            mensaje_error = """
⚠️ Por favor, escribe tu nombre completo (nombre y apellidos).

✍️ Ejemplo: Juan Pérez López

O escribe "0" para volver al menú principal.
            """
            dispatcher.utter_message(text=mensaje_error)
            return [SlotSet("estado_menu", "capturar_nombre")]

class ActionDefaultFallback(Action):
    """Acción de fallback simplificada"""
    
    def name(self) -> Text:
        return "action_default_fallback"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        mensaje = """🤔 No entendí tu mensaje. 

Por favor escribe:
• Un número (1, 2, 3, etc.) para navegar
• "0" para volver al menú principal
• "hola" para reiniciar

¿En qué puedo ayudarte?"""
        
        dispatcher.utter_message(text=mensaje)
        return []


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
        
        # Formato especial para Node-RED con todos los datos
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
