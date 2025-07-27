# URLs de imágenes para Botmobile
# Configuración centralizada de todas las imágenes usadas en el bot

class ImageConfig:
    """Configuración centralizada de URLs de imágenes"""
    
    # Imágenes de paquetes
    PAQUETES_PROMOCION = "https://raw.githubusercontent.com/hollyw00d337/BotMobile/main/assets/images/paquetes-promocion.jpeg"
    
    # Imágenes de portabilidad
    PORTABILIDAD_3_PASOS = "https://raw.githubusercontent.com/hollyw00d337/BotMobile/main/assets/images/portabilidad-3-pasos.jpeg"
    
    # Imágenes de instrucciones
    COMO_OBTENER_NIP = "https://raw.githubusercontent.com/hollyw00d337/BotMobile/main/assets/images/como-obtener-nip.jpeg"
    COMO_OBTENER_IMEI = "https://raw.githubusercontent.com/hollyw00d337/BotMobile/main/assets/images/como-obtener-imei.jpeg"
    
    # Imágenes de bienvenida
    BIENVENIDA_BOTMOBILE = "https://raw.githubusercontent.com/hollyw00d337/BotMobile/main/assets/images/bienvenida-spotty.jpeg"
    
    @classmethod
    def get_image_url(cls, image_name: str) -> str:
        return getattr(cls, image_name, "")
    
    @classmethod
    def get_all_images(cls) -> dict:
     
        return {
            name: value for name, value in cls.__dict__.items()
            if isinstance(value, str) and value.startswith('http')
        }
