from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from config.image_config import ImageConfig


class ActionSessionStart(Action):
    """Acción para iniciar la sesión y mostrar el menú principal"""
    
    def name(self) -> Text:
        return "action_session_start"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        mensaje_menu = """
👋 ¡Hola! Soy Spotty, tu asistente móvil ☕
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
        
        # Estados que no requieren número de opción (manejan texto libre)
        estados_texto_libre = ["validar_imei", "registro_nombre", "registro_correo", "registro_numero", "capturar_nip"]
        
        # Manejar despedida en estados donde NO es texto libre
        if intent == "despedida" and estado_actual not in estados_texto_libre:
            dispatcher.utter_message(text="¡Hasta la vista! 👋 Espero haberte ayudado. Regresa cuando gustes.")
            return []
        
        if estado_actual == "validar_imei":
            return self._manejar_validacion_imei(dispatcher, tracker)
        elif estado_actual == "registro_nombre":
            return self._manejar_registro_nombre(dispatcher, tracker)
        elif estado_actual == "registro_correo":
            return self._manejar_registro_correo(dispatcher, tracker)
        elif estado_actual == "registro_numero":
            return self._manejar_registro_numero(dispatcher, tracker)
        elif estado_actual == "capturar_nip":
            return self._manejar_captura_nip(dispatcher, tracker)
        
        # Si no hay número de opción y estamos en un estado que SÍ lo requiere, volver al menú principal
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
        
        elif estado_actual == "menu_esim_valido":
            return self._manejar_menu_esim_valido(dispatcher, numero_opcion)
        
        elif estado_actual == "submenu_soporte":
            return self._manejar_submenu_soporte(dispatcher, numero_opcion)
        
        # Si el estado no es reconocido, volver al menú principal
        else:
            return self._mostrar_menu_principal(dispatcher)
    
    def _mostrar_menu_principal(self, dispatcher):
        mensaje_menu = """
👋 ¡Hola! Soy Spotty, tu asistente móvil ☕
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
    
    def _manejar_menu_principal(self, dispatcher, numero_opcion):
        if numero_opcion == "1":
            # Enviar la imagen de portabilidad primero
            dispatcher.utter_message(image=ImageConfig.PORTABILIDAD_3_PASOS)
            
            mensaje = """
🔄 PORTABILIDAD 

1️⃣ ¿Cómo conseguir NIP?
2️⃣ Documentos necesarios
3️⃣ Hablar con equipo
0️⃣ Menú principal

¿Qué opción necesitas?
            """
            dispatcher.utter_message(text=mensaje)
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
    
    def _manejar_validacion_imei(self, dispatcher, tracker):
        """Función temporal para mostrar los mensajes de validación de IMEI"""
        mensaje_texto = tracker.latest_message.get('text', '')
        
        # Por ahora, simulamos la validación - después se conectará con Node-RED
        # Si contiene exactamente 15 dígitos, lo consideramos válido
        imei_numeros = ''.join(filter(str.isdigit, mensaje_texto))
        
        if len(imei_numeros) == 15:
            # CASO 1: IMEI válido - mostrar resumen de datos capturados
            nip_usuario = tracker.get_slot("nip_usuario")
            
            mensaje_valido = f"""
🚀 ¡Perfecto! Tu equipo es compatible y acepta eSIM.
🪄 Esto significa que podemos activarte en minutos, sin esperar envíos ni usar chip físico.

📋 Datos registrados:
• NIP: {nip_usuario if nip_usuario else 'No capturado'}
• IMEI: {imei_numeros}

👇 ¿Qué quieres hacer ahora?

1️⃣ Activarlo ya mismo
2️⃣ Ver otros paquetes disponibles
3️⃣ Saber más sobre qué es una eSIM
4️⃣ Hablar con alguien del equipo

✍️ Solo responde con el número de la opción.
            """
            dispatcher.utter_message(text=mensaje_valido)
            
            # Guardar el IMEI también
            return [
                SlotSet("imei_usuario", imei_numeros),
                SlotSet("estado_menu", "menu_esim_valido")
            ]
        else:
            # CASO 2: IMEI inválido o incompleto
            mensaje_invalido = """
😅 Oops, parece que ese IMEI no es válido.

🔄 Asegúrate de copiar los 15 dígitos completos (sin espacios ni guiones).

📲 Marca *#06# en el teclado de tu teléfono y copia el número tal como aparece.

¡Intenta de nuevo y lo validamos al instante! ⚡
            """
            dispatcher.utter_message(text=mensaje_invalido)
        
        # Mantener el estado para que el usuario pueda intentar de nuevo
        return [SlotSet("estado_menu", "validar_imei")]
    
    def _manejar_menu_esim_valido(self, dispatcher, numero_opcion):
        """Maneja las opciones del menú cuando el IMEI es válido y acepta eSIM"""
        if numero_opcion == "0":
            return self._mostrar_menu_principal(dispatcher)
        
        elif numero_opcion == "1":
            # Opción 1: Activarlo ya mismo
            mensaje_activacion = """
✍️ Ahora sí, vamos a preparar tu línea.

1️⃣ Por favor, escríbenos tu nombre completo (como aparece en tu INE o documento oficial).

🧾 Lo necesitamos para comenzar con el registro.
(Tranquilo, tus datos están protegidos y seguros con nosotros.)
            """
            dispatcher.utter_message(text=mensaje_activacion)
            return [SlotSet("estado_menu", "registro_nombre")]
        
        elif numero_opcion == "2":
            # Opción 2: Ver otros paquetes disponibles
            # Enviar la imagen de los paquetes primero
            dispatcher.utter_message(image=ImageConfig.PAQUETES_PROMOCION)
            
            mensaje_paquetes = """
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

📞 Pregunta por disponibilidad y activa el tuyo hoy mismo.

0️⃣ Volver al menú anterior
            """
            dispatcher.utter_message(text=mensaje_paquetes)
            return [SlotSet("estado_menu", "menu_esim_valido")]
        
        elif numero_opcion == "3":
            # Opción 3: Saber más sobre qué es una eSIM
            mensaje_esim = """
📲 ¿Qué es una eSIM?

🔹 eSIM = SIM digital - No necesitas chip físico
🔹 Activación instantánea - En minutos desde tu teléfono
🔹 Más segura - No se puede perder, robar o dañar
🔹 Dual SIM - Puedes tener 2 líneas en un teléfono
🔹 Viajes - Ideal para líneas temporales sin cambiar chip

⚡ Ventajas:
• Sin esperar envíos
• Sin visitas a tiendas
• Activación 24/7
• Cambio de operador al instante

👇 ¿Listo para activar tu eSIM?

1️⃣ Sí, activar ahora
0️⃣ Volver al menú anterior
            """
            dispatcher.utter_message(text=mensaje_esim)
            return [SlotSet("estado_menu", "menu_esim_valido")]
        
        elif numero_opcion == "4":
            # Opción 4: Hablar con alguien del equipo
            mensaje_contacto = """
👥 Contacta a nuestro equipo

📲 WhatsApp: +52 1 614 558 7289

📞 Llama directo o envía mensaje

⚡ Nuestro equipo te ayudará con:
• Procesar tu activación eSIM
• Resolver dudas técnicas
• Elegir el mejor paquete
• Completar el registro

🕒 Horarios de atención:
• Lunes a Viernes: 9:00 - 18:00
• Sábados: 9:00 - 14:00

0️⃣ Volver al menú anterior
            """
            dispatcher.utter_message(text=mensaje_contacto)
            return [SlotSet("estado_menu", "menu_esim_valido")]
        
        else:
        
            mensaje_error = """
Opción no válida. Por favor elige:

1️⃣ Activarlo ya mismo
2️⃣ Ver otros paquetes disponibles
3️⃣ Saber más sobre qué es una eSIM
4️⃣ Hablar con alguien del equipo

0️⃣ Volver al menú principal
            """
            dispatcher.utter_message(text=mensaje_error)
            return [SlotSet("estado_menu", "menu_esim_valido")]
    
    def _manejar_registro_nombre(self, dispatcher, tracker):
        mensaje_texto = tracker.latest_message.get('text', '')
        
        # Limpiar el texto de entrada
        nombre_usuario = mensaje_texto.strip()
        
        # Validar que no esté vacío y que no sea un número
        if not nombre_usuario or nombre_usuario.isdigit():
            mensaje_error = """
❌ Por favor, escríbenos tu nombre completo (como aparece en tu INE).

📝 Intenta de nuevo:
            """
            dispatcher.utter_message(text=mensaje_error)
            return [SlotSet("estado_menu", "registro_nombre")]
        
        # Validar que tenga al menos una letra
        if not any(c.isalpha() for c in nombre_usuario):
            mensaje_error = """
❌ El nombre debe contener al menos una letra.

📝 Intenta de nuevo:
            """
            dispatcher.utter_message(text=mensaje_error)
            return [SlotSet("estado_menu", "registro_nombre")]
        
        # Obtener el primer nombre para personalizar el mensaje
        palabras = nombre_usuario.split()
        primer_nombre = palabras[0] if palabras else "Usuario"
        
        mensaje_correo = f"""
📧 ¡Genial, {primer_nombre}!

2️⃣ Ahora, por favor escríbenos tu correo electrónico.

🔐 Lo necesitamos para enviarte la confirmación de la activación y para cualquier detalle importante sobre tu línea.

💡 Si tienes más de uno, elige el que revises con frecuencia.
        """
        
        dispatcher.utter_message(text=mensaje_correo)
        
        # Guardar el nombre completo en un slot y cambiar al estado de registro de correo
        return [
            SlotSet("nombre_usuario", nombre_usuario),
            SlotSet("estado_menu", "registro_correo")
        ]
    
    def _manejar_registro_correo(self, dispatcher, tracker):
        """Maneja el registro del correo electrónico del usuario"""
        mensaje_texto = tracker.latest_message.get('text', '')
        
        # Capturar el correo electrónico
        correo_usuario = mensaje_texto.strip()
        
        mensaje_numero = """
📱 ¡Gracias!

3️⃣ Ahora, escríbenos el número que quieres portar (el que ya tienes con otra compañía).

🔎 Asegúrate de que tenga exactamente 10 dígitos y no tenga espacios ni guiones.
        """
        
        dispatcher.utter_message(text=mensaje_numero)
        
        # Guardar el correo en un slot y cambiar al estado de registro de número
        return [
            SlotSet("correo_usuario", correo_usuario),
            SlotSet("estado_menu", "registro_numero")
        ]
    
    def _manejar_registro_numero(self, dispatcher, tracker):
        """Maneja el registro del número telefónico del usuario"""
        mensaje_texto = tracker.latest_message.get('text', '')
        
        # Extraer solo los números del mensaje
        numero_telefono = ''.join(filter(str.isdigit, mensaje_texto))
        
        # Validar que el número tenga exactamente 10 dígitos
        if len(numero_telefono) == 10:
            # Número válido - guardarlo y finalizar el registro
            mensaje_final = """
✅ ¡Perfecto! Hemos registrado toda tu información correctamente.

📋 Resumen de tus datos:
• Nombre: Registrado ✓
• Correo: Registrado ✓  
• Número a portar: Registrado ✓
• NIP: Registrado ✓
• IMEI: Registrado ✓

🎉 Gracias por proporcionarnos tus datos. El equipo se contactará contigo pronto.

📲 También puedes contactarnos por WhatsApp: +52 614 558 7289

¡Que tengas un excelente día! 👋
            """
            dispatcher.utter_message(text=mensaje_final)
            
            # Guardar el número y terminar la conversación
            return [SlotSet("numero_telefono", numero_telefono)]
        
        elif len(numero_telefono) > 0 and len(numero_telefono) != 10:
            # Número con cantidad incorrecta de dígitos
            mensaje_error = f"""
⚠️ El número debe tener exactamente 10 dígitos.

Recibí: {numero_telefono} ({len(numero_telefono)} dígitos)

📱 Por favor, escríbeme tu número de 10 dígitos sin espacios ni guiones:
💡 Ejemplo: 6141234567          """
            dispatcher.utter_message(text=mensaje_error)
            return [SlotSet("estado_menu", "registro_numero")]
        
        else:
            # No se encontraron números en el mensaje
            mensaje_error = """
❌ No pude encontrar números en tu mensaje.

📱 Por favor, escríbeme tu número telefónico de 10 dígitos:

💡 Ejemplo: 6141234567

O escribe "0" para volver al menú principal.
            """
            dispatcher.utter_message(text=mensaje_error)
            return [SlotSet("estado_menu", "registro_numero")]
    
    def _manejar_captura_nip(self, dispatcher, tracker):
        """Maneja la captura del NIP del usuario"""
        mensaje_texto = tracker.latest_message.get('text', '')
        
        # Extraer solo los dígitos del mensaje
        nip_numeros = ''.join(filter(str.isdigit, mensaje_texto))
        
        # Validar que el NIP tenga exactamente 4 dígitos
        if len(nip_numeros) == 4:
            # NIP válido - guardarlo y continuar al IMEI
            mensaje_confirmacion = f"""
✅ ¡Perfecto! Tu NIP **{nip_numeros}** ha sido registrado correctamente.

📶 Ahora vamos a verificar si tu teléfono es compatible con nuestra red.

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


class ActionDefaultFallback(Action):
    """Acción de fallback simplificada"""
    
    def name(self) -> Text:
        return "action_default_fallback"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        mensaje = """
🤔 No entendí tu mensaje. 

Por favor escribe:
• Un número (1, 2, 3, etc.) para navegar
• "0" para volver al menú principal
• "hola" para reiniciar

¿En qué puedo ayudarte?
        """
        
        dispatcher.utter_message(text=mensaje)
        return []