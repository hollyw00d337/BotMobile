from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from config.image_config import ImageConfig
import logging
import re

logger = logging.getLogger(__name__)


def format_as_button_option(number: int, text: str) -> str:
    """
    Formatea un texto como opción de botón con identificadores.
    
    Args:
        number: Número de la opción (1, 2, 3, etc.)
        text: Texto de la opción
        
    Returns:
        Texto formateado como: "1️⃣ Texto de la opción."
    """
    # Mapear números a emojis
    emoji_map = {
        1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣",
        6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
    }
    
    emoji = emoji_map.get(number, f"{number}️⃣")
    
    # Asegurar que termine con punto
    if not text.endswith('.'):
        text += '.'
    
    return f"{emoji} {text}"


def format_message_with_options(intro_text: str, options: List[str]) -> str:
    """
    Formatea un mensaje con texto introductorio y opciones numeradas.
    
    Args:
        intro_text: Texto introductorio (mensaje simple)
        options: Lista de opciones que serán formateadas como botones
        
    Returns:
        Mensaje completo formateado
    """
    formatted_options = []
    for i, option in enumerate(options, 1):
        formatted_options.append(format_as_button_option(i, option))
    
    return f"{intro_text}\n\n" + "\n".join(formatted_options)


class ActionSessionStart(Action):
    """Acción personalizada para iniciar la sesión.
    Diseñada para trabajar exactamente con el código Node-RED original.
    """
    
    def name(self) -> Text:
        return "action_session_start"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        print(f"[DEBUG ActionSessionStart] ═══ INICIANDO SESIÓN ═══")
        print(f"[DEBUG ActionSessionStart] Mensaje recibido: {tracker.latest_message}")
        
        # Enviar imagen de bienvenida
        dispatcher.utter_message(image=ImageConfig.BIENVENIDA_BOTMOBILE)
        
        # **IDENTIFICADOR DE INICIO DE CONVERSACIÓN**
        inicio_conversacion_detectado = False
        mensaje_texto = None
        
        # Obtener el mensaje del usuario
        if tracker.latest_message:
            mensaje_texto = tracker.latest_message.get('text', '')
            print(f"[DEBUG ActionSessionStart] Texto extraído: '{mensaje_texto}'")
        
        # Verificar identificadores especiales de Node-RED
        if mensaje_texto:
            mensaje_upper = mensaje_texto.upper().strip()
            
            # **IDENTIFICADOR DE INICIO**: Detectar inicio de conversación
            if self._es_inicio_conversacion(mensaje_upper):
                print(f"[DEBUG ActionSessionStart] ✅ INICIO DE CONVERSACIÓN DETECTADO")
                inicio_conversacion_detectado = True
            
            # **PROCESAMIENTO DE COMPAÑÍA**: Usar código Node-RED exacto
            if self._es_mensaje_node_red(mensaje_texto):
                print(f"[DEBUG ActionSessionStart] ✅ MENSAJE DE NODE-RED DETECTADO")
                
                # Extraer compañía usando la lógica exacta del Node-RED
                compania_detectada = self._extraer_compania_node_red(mensaje_texto)
                if compania_detectada:
                    print(f"[DEBUG ActionSessionStart] ✅ Compañía detectada: {compania_detectada}")
                    
                    mensaje_personalizado = self._crear_mensaje_personalizado_con_menu(compania_detectada)
                    dispatcher.utter_message(text=mensaje_personalizado)
                    
                    slots_to_set = [
                        SlotSet("compania_operador", compania_detectada),
                        SlotSet("estado_menu", "menu_principal"),
                        SlotSet("session_started", True),
                        SlotSet("inicio_conversacion", inicio_conversacion_detectado)
                    ]
                    
                    # Extraer número si existe (formato Node-RED)
                    numero_extraido = self._extraer_numero_node_red(mensaje_texto)
                    if numero_extraido:
                        slots_to_set.append(SlotSet("numero_telefono", numero_extraido))
                        print(f"[DEBUG ActionSessionStart] ✅ Número extraído: {numero_extraido}")
                    
                    return slots_to_set
        
        print(f"[DEBUG ActionSessionStart] ❌ Mensaje genérico, usando saludo por defecto")
        
        # Saludo genérico por defecto con identificadores de botones
        intro_text = """👋 ¡Hola! Soy BotMobile, tu asistente móvil ☕
Estoy aquí para ayudarte a conectarte fácil, rápido y sin interrupciones 📶

📦 Tenemos paquetes para todos los usos, con cobertura nacional.
Elige entre chip físico o eSIM, ¡y hazlo todo desde aquí!

👇 ¿Qué necesitas hoy?"""

        opciones = [
            "Conservar mi número (portabilidad)",
            "Ver paquetes disponibles", 
            "Hablar con alguien del equipo"
        ]
        
        mensaje_menu = format_message_with_options(intro_text, opciones)
        mensaje_menu += "\n\n☕ ¡Vamos a hacerlo simple! Solo responde con el número de la opción."
        
        dispatcher.utter_message(text=mensaje_menu)
        
        return [
            SlotSet("estado_menu", "menu_principal"),
            SlotSet("session_started", True),
            SlotSet("inicio_conversacion", inicio_conversacion_detectado)
        ]
    
    def _es_inicio_conversacion(self, mensaje_upper: str) -> bool:
        """
        Detecta identificadores de inicio de conversación.
        Patrones comunes de Node-RED para inicio.
        """
        patrones_inicio = [
            r'^INICIO',
            r'^START',
            r'^BEGIN',
            r'^NUEVA_CONVERSACION',
            r'^NEW_CONVERSATION',
            r'INICIO_BOT',
            r'START_SESSION'
        ]
        
        for patron in patrones_inicio:
            if re.search(patron, mensaje_upper):
                return True
        
        return False
    
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
    
    def _extraer_compania_node_red(self, texto: str) -> str:
        """
        Extrae la compañía usando la lógica EXACTA del Node-RED original.
        """
        if not texto:
            return None
            
        texto_upper = texto.upper()
        
        # **MAPEO EXACTO DEL NODE-RED**
        mapeo_companias = {
            'TELCEL': 'Telcel',
            'MOVISTAR': 'Movistar', 
            'AT&T': 'AT&T',
            'UNEFON': 'Unefon',
            'VIRGIN': 'Virgin Mobile',
            'ALTAN': 'Altan Redes'
        }
        
        # **PATRONES DE EXTRACCIÓN (orden de prioridad)**
        
        # 1. Formato: "COMPANIA_DETECTADA TELCEL"
        match = re.search(r'COMPANIA_DETECTADA\s+([A-Z&]+)', texto_upper)
        if match:
            compania_raw = match.group(1)
            compania_final = mapeo_companias.get(compania_raw, compania_raw.capitalize())
            print(f"[DEBUG] Compañía extraída formato 1: {compania_raw} -> {compania_final}")
            return compania_final
        
        # 2. Formato especial: "OPERATOR SPOT UNO NUMERO xxx" (caso especial con espacio)
        match = re.search(r'OPERATOR\s+(SPOT\s+UNO)', texto_upper)
        if match:
            print(f"[DEBUG] Compañía extraída formato 2 especial: SPOT UNO -> Spot Uno")
            return "Spot Uno"
        
        # 3. Formato: "OPERATOR TELCEL NUMERO 5512345678" 
        match = re.search(r'OPERATOR\s+([A-Z&]+)', texto_upper)
        if match:
            compania_raw = match.group(1)
            compania_final = mapeo_companias.get(compania_raw, compania_raw.capitalize())
            print(f"[DEBUG] Compañía extraída formato 3: {compania_raw} -> {compania_final}")
            return compania_final
        
        # 4. Formato: "TELCEL NUMERO 5512345678"
        match = re.search(r'(TELCEL|MOVISTAR|AT&T|UNEFON|VIRGIN|ALTAN)', texto_upper)
        if match:
            compania_raw = match.group(1)
            compania_final = mapeo_companias.get(compania_raw, compania_raw.capitalize())
            print(f"[DEBUG] Compañía extraída formato 4: {compania_raw} -> {compania_final}")
            return compania_final
        
        # 5. Operador solo (formato directo)
        texto_limpio = texto_upper.strip()
        if texto_limpio in mapeo_companias:
            compania_final = mapeo_companias[texto_limpio]
            print(f"[DEBUG] Compañía extraída formato 5: {texto_limpio} -> {compania_final}")
            return compania_final
        
        # 5. Formato Node-RED actual: nombres formateados (ej: "Telcel", "CFE", "Walmart")
        texto_original = texto.strip()
        mapeo_nombres_formateados = {
            'Telcel': 'Telcel', 'Movistar': 'Movistar', 'AT&T': 'AT&T', 'Unefon': 'Unefon', 
            'Virgin': 'Virgin Mobile', 'Altan': 'Altan Redes', 'CFE': 'CFE', 'Walmart': 'Walmart',
            'Quickly': 'Quickly', 'Ibo Cell': 'Ibo Cell', 'Tel 360': 'Tel 360', 'Kubo': 'Kubo',
            'Virgin Mobile': 'Virgin Mobile', 'Telecommerce': 'Telecommerce', 'MVH': 'MVH', 'Neus': 'Neus',
            'Truu': 'Truu', 'Celmex': 'Celmex', 'Eja': 'Eja', 'Logistica': 'Logistica', 'Her': 'Her',
            'Comnet': 'Comnet', 'Marduk': 'Marduk', 'Freedom': 'Freedom', 'Hidalguense': 'Hidalguense',
            'Mobilebandits': 'Mobilebandits', 'Hip Cricket': 'Hip Cricket', 'Moluger': 'Moluger', 'Altcel': 'Altcel',
            'Inbtel': 'Inbtel', 'AINT': 'AINT', 'Islim': 'Islim', 'Airbus': 'Airbus', 'Clearcom': 'Clearcom',
            'Gurucomm': 'Gurucomm', 'MBT': 'MBT', 'RTM': 'RTM', 'Esmero': 'Esmero', 'Talento': 'Talento',
            'Oxio': 'Oxio', 'Rocketel': 'Rocketel', 'Ads': 'Ads', 'Arloesi': 'Arloesi', 'Diri': 'Diri',
            'Topos': 'Topos', 'Wimo': 'Wimo', 'Diveracy': 'Diveracy', 'Tridex': 'Tridex', 'Exis': 'Exis',
            'Ome': 'Ome', 'Edilar': 'Edilar', 'Novavision': 'Novavision', 'Guga': 'Guga', 
            'Absoluteteck': 'Absoluteteck', 'Yonder': 'Yonder', 'Cobranza': 'Cobranza', 'Tritium': 'Tritium',
            'Afcaza': 'Afcaza', 'Balesia': 'Balesia', 'Rosa': 'Rosa', 'Telmov': 'Telmov', 'Marketing': 'Marketing',
            'Bitelit': 'Bitelit', 'Orange': 'Orange', 'R&R': 'R&R', 'Viral': 'Viral', 'Oceannet': 'Oceannet',
            'Element': 'Element', 'Broco': 'Broco', 'Allesklar': 'Allesklar', 'Lider': 'Lider', 'Secure': 'Secure',
            'Gameplanet': 'Gameplanet', 'Axios': 'Axios', 'Celsfi': 'Celsfi', 'Maya': 'Maya', 'Telexes': 'Telexes',
            'Cambacel': 'Cambacel', 'Pantera': 'Pantera', 'Othis': 'Othis', 'Femaseisa': 'Femaseisa',
            'Alcance': 'Alcance', 'Francisco': 'Francisco', 'Valor': 'Valor', 'Pajal': 'Pajal',
            'Speednet': 'Speednet', 'Liimaxtum': 'Liimaxtum', 'Yaqui': 'Yaqui', 'Rex': 'Rex',
            'Saavedra': 'Saavedra', 'Negocios': 'Negocios', 'Nexbus': 'Nexbus', 'King': 'King',
            'Bene': 'Bene', 'Elux': 'Elux', 'Igou': 'Igou', 'Voztelecom': 'Voztelecom', 'Abafon': 'Abafon',
            'Romel': 'Romel', 'Celmax': 'Celmax', 'Alestra': 'Alestra', 'VPN': 'VPN', 'Maxcom': 'Maxcom',
            'IENTC': 'IENTC', 'OpenIP': 'OpenIP', 'Operbes': 'Operbes', 'Cablevision': 'Cablevision',
            'Plintron': 'Plintron', 'Sev Tronc': 'Sev Tronc', 'Megacable': 'Megacable', 'Vasanta': 'Vasanta',
            'Inten': 'Inten', 'Next': 'Next', 'Guadiana': 'Guadiana', 'Solucionika': 'Solucionika',
            'Abix': 'Abix', 'Girnet': 'Girnet', 'Fobos': 'Fobos', 'Unet': 'Unet', 'Plasma': 'Plasma',
            'Tu Visión': 'Tu Visión', 'Tele Imagen': 'Tele Imagen', 'Telgen': 'Telgen', 'Ultravision': 'Ultravision',
            'Trends': 'Trends', 'Apco': 'Apco', 'Spot Uno': 'Spot Uno', 'Uriel': 'Uriel', 'Eni': 'Eni',
            'At&t': 'AT&T'  # Mapeo especial para el formato de la base de datos
        }
        
        if texto_original in mapeo_nombres_formateados:
            compania_final = mapeo_nombres_formateados[texto_original]
            print(f"[DEBUG] Compañía extraída formato 5 (Node-RED): {texto_original} -> {compania_final}")
            return compania_final
        
        print(f"[DEBUG] ❌ No se pudo extraer compañía de: '{texto}'")
        return None
    
    def _extraer_numero_node_red(self, texto: str) -> str:
        """
        Extrae el número de teléfono usando los patrones del Node-RED original.
        """
        if not texto:
            return None
        
        # Patrones para extraer número
        patrones_numero = [
            r'NUMERO\s+(\d{10,})',  # "NUMERO 5512345678"
            r'NUMBER\s+(\d{10,})',  # "NUMBER 5512345678" 
            r'(\d{10})',            # Número directo de 10 dígitos
        ]
        
        texto_upper = texto.upper()
        
        for patron in patrones_numero:
            match = re.search(patron, texto_upper)
            if match:
                numero = match.group(1)
                print(f"[DEBUG] ✅ Número extraído: {numero}")
                return numero
        
        return None

    def _crear_mensaje_personalizado_con_menu(self, compania: str) -> str:
        """
        Crea mensaje personalizado basado en la compañía del usuario con identificadores de botones.
        Exactamente como funciona con el Node-RED original.
        """
        
        mensajes_personalizados = {
            "Telcel": {
                "intro": """🎯 ¡Hola! Detecté que vienes de Telcel. Te ayudo con tu portabilidad a BotMobile de manera súper fácil.

💰 ¡Ahorra $80 pesos al mes!
Telcel: $300/mes por 8GB
BotMobile: $220/mes por 72GB

👇 ¿Qué necesitas hoy?""",
                "opciones": [
                    "Conservar mi número (portabilidad)",
                    "Ver paquetes disponibles", 
                    "Hablar con alguien del equipo"
                ]
            },
            
            "AT&T": {
                "intro": """🎯 ¡Perfecto! Detecté que vienes de AT&T. 

💰 BotMobile te ofrece:
📱 72GB por solo $220/mes
🎬 Netflix + Disney+ + Prime incluido
📶 Cobertura nacional garantizada

👇 ¿Qué te interesa?""",
                "opciones": [
                    "Conservar mi número (portabilidad)",
                    "Ver paquetes disponibles", 
                    "Hablar con alguien del equipo"
                ]
            },
            
            "Movistar": {
                "intro": """🎯 ¡Hola! Veo que vienes de Movistar.

💸 Compara y ahorra:
Movistar: $350/mes por 10GB  
BotMobile: $220/mes por 72GB + streaming incluido

👇 ¿Cómo te ayudo?""",
                "opciones": [
                    "Conservar mi número (portabilidad)",
                    "Ver paquetes disponibles", 
                    "Hablar con alguien del equipo"
                ]
            },
            
            "Unefon": {
                "intro": """🎯 ¡Hola! Detecté que vienes de Unefon.

🚀 Mejora tu experiencia:
✅ Más datos por menos dinero
✅ Cobertura nacional real
✅ Streaming incluido sin costo extra

👇 ¿Qué necesitas?""",
                "opciones": [
                    "Conservar mi número (portabilidad)",
                    "Ver paquetes disponibles", 
                    "Hablar con alguien del equipo"
                ]
            },
            
            "Virgin Mobile": {
                "intro": """🎯 ¡Hola! Veo que vienes de Virgin Mobile.

⚡ Velocidad real + más beneficios:
📱 72GB de alta velocidad
🎬 Plataformas de streaming incluidas
📶 Red nacional de calidad

👇 ¿Cómo puedo ayudarte?""",
                "opciones": [
                    "Conservar mi número (portabilidad)",
                    "Ver paquetes disponibles", 
                    "Hablar con alguien del equipo"
                ]
            },
            
            "Altan Redes": {
                "intro": """🎯 ¡Perfecto! Detecté que vienes de Altan Redes.

💫 Migración súper sencilla:
✅ Conservas tu número
✅ Más datos, mismo precio
✅ Sin complicaciones

👇 ¿Qué te gustaría saber?""",
                "opciones": [
                    "Conservar mi número (portabilidad)",
                    "Ver paquetes disponibles", 
                    "Hablar con alguien del equipo"
                ]
            },
            
            "Spot Uno": {
                "intro": """🎯 ¡Hola! Detecté que vienes de Spot Uno.

💰 ¡Es hora de una actualización!
✨ BotMobile te ofrece mucho más:
📱 72GB por solo $220/mes
🎬 Netflix + Disney+ + Prime incluido
📶 Cobertura nacional superior

👇 ¿Qué te interesa conocer?""",
                "opciones": [
                    "Conservar mi número (portabilidad)",
                    "Ver paquetes disponibles", 
                    "Hablar con alguien del equipo"
                ]
            }
        }
        
        if compania in mensajes_personalizados:
            config = mensajes_personalizados[compania]
            mensaje = format_message_with_options(config["intro"], config["opciones"])
        else:
            # Mensaje genérico para operadores no específicamente configurados
            intro = f"""🎯 ¡Hola! Detecté que vienes de {compania}.

💰 BotMobile te ofrece más por menos:
📱 72GB por solo $220/mes
🎬 Netflix + Disney+ + Prime incluido
📶 Cobertura nacional garantizada

👇 ¿Cómo te ayudo?"""
            
            opciones = [
                "Conservar mi número (portabilidad)",
                "Ver paquetes disponibles", 
                "Hablar con alguien del equipo"
            ]
            mensaje = format_message_with_options(intro, opciones)
        
        mensaje += "\n\n☕ ¡Vamos a hacerlo simple! Solo responde con el número de la opción."
        return mensaje


class ActionFinalizarConversacion(Action):
    """
    **IDENTIFICADOR DE FIN DE CONVERSACIÓN**
    Maneja el cierre de conversaciones y cleanup.
    """
    
    def name(self) -> Text:
        return "action_finalizar_conversacion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        print(f"[DEBUG ActionFinalizarConversacion] ═══ FINALIZANDO CONVERSACIÓN ═══")
        
        # Mensaje de despedida con identificadores
        intro_text = """👋 ¡Gracias por contactar BotMobile!

🎯 Recuerda:
📱 Siempre tenemos los mejores planes
💬 Estamos aquí cuando nos necesites
🚀 Tu portabilidad es gratis y sencilla

✨ ¿Necesitas algo más?"""
        
        opciones = [
            "Volver al menú principal",
            "Hablar con el equipo", 
            "Finalizar conversación"
        ]
        
        mensaje_despedida = format_message_with_options(intro_text, opciones)
        dispatcher.utter_message(text=mensaje_despedida)
        
        return [
            SlotSet("estado_menu", "despedida"),
            SlotSet("conversation_ending", True)
        ]


class ActionElegirOpcion(Action):
    """Maneja las opciones del menú principal con identificadores de botones"""
    
    def name(self) -> Text:
        return "action_elegir_opcion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener la opción seleccionada
        numero_opcion = None
        entities = tracker.latest_message.get('entities', [])
        
        for entity in entities:
            if entity.get('entity') == 'numero_opcion':
                numero_opcion = entity.get('value')
                break
        
        # Si no se encontró en entities, buscar en el texto
        if not numero_opcion:
            texto = tracker.latest_message.get('text', '')
            match = re.search(r'(\d+)', texto)
            if match:
                numero_opcion = match.group(1)
        
        print(f"[DEBUG ActionElegirOpcion] Opción seleccionada: {numero_opcion}")
        
        compania_operador = tracker.get_slot("compania_operador")
        
        if numero_opcion == "1":
            # Portabilidad
            if compania_operador:
                # Mensaje personalizado para portabilidad
                intro_text = f"""🔄 ¡Perfecto! Te ayudo con la portabilidad desde {compania_operador}.

📋 Necesitarás:
📱 Tu número actual activo
🆔 Tu NIP de portabilidad
📄 Identificación oficial

👇 ¿Cómo quieres continuar?"""
                
                opciones = [
                    "Solicitar mi NIP de portabilidad",
                    "Ya tengo mi NIP, continuar",
                    "Volver al menú principal"
                ]
            else:
                intro_text = """🔄 ¡Excelente elección! La portabilidad es gratis y sencilla.

📋 Proceso simple:
1️⃣ Solicitas tu NIP a tu operador actual
2️⃣ Nos proporcionas tus datos
3️⃣ ¡Listo! Conservas tu número

👇 ¿Necesitas ayuda con algún paso?"""
                
                opciones = [
                    "¿Cómo obtener mi NIP?",
                    "Ya tengo mi NIP",
                    "Volver al menú principal"
                ]
            
            mensaje = format_message_with_options(intro_text, opciones)
            dispatcher.utter_message(text=mensaje)
            
            return [SlotSet("estado_menu", "portabilidad")]
            
        elif numero_opcion == "2":
            # Ver paquetes
            dispatcher.utter_message(image=ImageConfig.PAQUETES_PROMOCION)
            
            intro_text = """📦 Nuestros Planes BotMobile:

🔥 Plan Ilimitado - $220/mes
📱 72GB + Ilimitadas llamadas
🎬 Netflix + Disney+ + Prime Video
📶 Cobertura nacional

💎 Plan Premium - $300/mes  
📱 100GB + Todo ilimitado
🎮 Gaming sin lag
🎬 Todas las plataformas incluidas

👇 ¿Qué te interesa?"""
            
            opciones = [
                "Contratar Plan Ilimitado $220",
                "Contratar Plan Premium $300", 
                "Volver al menú principal"
            ]
            
            mensaje = format_message_with_options(intro_text, opciones)
            dispatcher.utter_message(text=mensaje)
            
            return [SlotSet("estado_menu", "paquetes")]
            
        elif numero_opcion == "3":
            # Hablar con el equipo
            intro_text = """👥 Contacta a nuestro equipo

📲 WhatsApp: +52 614 558 7289

⚡ Nuestro equipo te ayudará con:
• Detalles de cada paquete
• Disponibilidad en tu zona
• Proceso de activación
• Resolver cualquier duda

� Horarios de atención:
• Lunes a Viernes: 9:00 - 18:00
• Sábados: 9:00 - 14:00

0️⃣ Volver al menú principal"""
            
            dispatcher.utter_message(text=intro_text)
            
            return [SlotSet("estado_menu", "contacto")]
        else:
            # Opción no válida
            dispatcher.utter_message(text="Opción no válida. Por favor elige un número del 1 al 3.")
            return []


class ActionDefaultFallback(Action):
    """Acción de fallback cuando no se entiende el mensaje"""
    
    def name(self) -> Text:
        return "action_default_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Mensaje de fallback amigable con identificadores
        intro_text = """🤔 No estoy seguro de entender. 

👋 Puedo ayudarte con:
📱 Portabilidad (conservar tu número)
📦 Ver nuestros planes
👥 Contactar con el equipo

👇 ¿Qué necesitas?"""
        
        opciones = [
            "Conservar mi número (portabilidad)",
            "Ver paquetes disponibles", 
            "Hablar con alguien del equipo"
        ]
        
        mensaje = format_message_with_options(intro_text, opciones)
        dispatcher.utter_message(text=mensaje)
        
        return [SlotSet("estado_menu", "menu_principal")]
