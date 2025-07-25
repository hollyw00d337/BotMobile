# URLs de imágenes para Spotybot
# Configuración centralizada de todas las imágenes usadas en el bot

class ImageConfig:
    """Configuración centralizada de URLs de imágenes"""
    
    # Imágenes de paquetes
    PAQUETES_PROMOCION = "https://raw.githubusercontent.com/hollyw00d337/spotybot/main/assets/images/paquetes-promocion.jpg"
    
    # Imágenes de portabilidad
    PORTABILIDAD_3_PASOS = "https://raw.githubusercontent.com/hollyw00d337/spotybot/main/assets/images/portabilidad-3-pasos.jpg"
    
    # Imágenes de instrucciones
    COMO_OBTENER_NIP = "https://raw.githubusercontent.com/hollyw00d337/spotybot/main/assets/images/como-obtener-nip.jpg"
    COMO_OBTENER_IMEI = "https://raw.githubusercontent.com/hollyw00d337/spotybot/main/assets/images/como-obtener-imei.jpg"
    
    # Imágenes de bienvenida
    BIENVENIDA_SPOTTY = "https://raw.githubusercontent.com/hollyw00d337/spotybot/main/assets/images/bienvenida-spotty.jpg"
    
    # Imágenes de eSIM
    QUE_ES_ESIM = "https://raw.githubusercontent.com/hollyw00d337/spotybot/main/assets/images/que-es-esim.jpg"
    
    @classmethod
    def get_image_url(cls, image_name: str) -> str:
        """
        Obtiene la URL de una imagen por su nombre
        
        Args:
            image_name (str): Nombre de la imagen (ej: 'PAQUETES_PROMOCION')
            
        Returns:
            str: URL de la imagen o cadena vacía si no existe
        """
        return getattr(cls, image_name, "")
    
    @classmethod
    def get_all_images(cls) -> dict:
        """
        Obtiene todas las URLs de imágenes disponibles
        
        Returns:
            dict: Diccionario con todos los nombres y URLs de imágenes
        """
        return {
            name: value for name, value in cls.__dict__.items()
            if isinstance(value, str) and value.startswith('http')
        }
