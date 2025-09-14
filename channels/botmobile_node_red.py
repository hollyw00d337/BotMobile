"""
Canal de salida personalizado para integración con Node-RED
Maneja el formato de botones específico para el flujo de Node-RED
"""

from typing import Text, Dict, Any, List
from rasa.core.channels.channel import OutputChannel


class BotMobileNodeRedChannel(OutputChannel):
    """Canal personalizado para enviar respuestas con botones a Node-RED"""
    
    def name(self) -> Text:
        return "botmobile_node_red"
    
    def send_text_message(
        self, recipient_id: Text, text: Text, **kwargs: Any
    ) -> None:
        """Envía mensaje de texto simple"""
        message = {
            "recipient_id": recipient_id,
            "text": text,
            "type": "text"
        }
        self._send_message(message)
    
    def send_custom_json(
        self, recipient_id: Text, json_message: Dict[Text, Any], **kwargs: Any
    ) -> None:
        """Envía mensaje JSON personalizado con formato de botones"""
        
        # Extraer botones si existen
        buttons = json_message.get("buttons", [])
        quick_replies = json_message.get("quick_replies", [])
        
        # Formato específico para Node-RED
        message = {
            "recipient_id": recipient_id,
            "text": json_message.get("text", ""),
            "type": "custom",
            "metadata": json_message.get("metadata", {}),
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": json_message.get("text", ""),
                    "buttons": buttons
                }
            }
        }
        
        # Agregar quick_replies si existen
        if quick_replies:
            message["quick_replies"] = quick_replies
        
        self._send_message(message)
    
    def send_image_url(
        self, recipient_id: Text, image: Text, **kwargs: Any
    ) -> None:
        """Envía imagen"""
        message = {
            "recipient_id": recipient_id,
            "attachment": {
                "type": "image",
                "payload": {
                    "url": image
                }
            },
            "type": "image"
        }
        self._send_message(message)
    
    def _send_message(self, message: Dict[Text, Any]) -> None:
        """Método base para enviar mensajes - se puede extender para logging"""
        # Aquí podrías agregar logging o envío real a Node-RED
        print(f"[NODE-RED] Enviando mensaje: {message}")
        # En producción, aquí enviarías el mensaje a Node-RED via HTTP/WebSocket
