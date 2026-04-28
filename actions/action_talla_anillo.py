from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import re

class ActionDarTallaSegunMedida(Action):
    def name(self) -> Text:
        return "action_dar_talla_segun_medida"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener el idioma del usuario desde el slot
        user_language = tracker.get_slot("language")
        if not user_language:
            user_language = "es"  # Idioma por defecto
        
        # Definir mensajes en ambos idiomas
        messages = {
            "es": {
                "no_measurement": "No encontré ninguna medida en tu mensaje. Por favor, proporciona un número seguido de la unidad (mm o cm).",
                "processing_error": "No pude procesar la medida. Por favor, proporciona la circunferencia de tu dedo en mm o cm. Error: {error}",
                "provide_measurement": "Por favor, proporciona la medida de tu dedo en mm o cm.",
                "out_of_range": "Lo siento, no existe una talla española para una circunferencia de {measurement} mm. Las tallas españolas van desde la 1 (40 mm) hasta la 36 (75 mm).",
                "size_result": "Para una circunferencia de {measurement} mm, la talla de anillo española es la {size}."
            },
            "en": {
                "no_measurement": "I couldn't find any measurement in your message. Please provide a number followed by the unit (mm or cm).",
                "processing_error": "I couldn't process the measurement. Please provide your finger circumference in mm or cm. Error: {error}",
                "provide_measurement": "Please provide your finger measurement in mm or cm.",
                "out_of_range": "Sorry, there is no Spanish ring size for a circumference of {measurement} mm. Spanish sizes range from 1 (40 mm) to 36 (75 mm).",
                "size_result": "For a circumference of {measurement} mm, the Spanish ring size is {size}."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        # Tabla de conversión
        tallas_espanolas = {
            1: 40.0, 2: 41.0, 3: 42.0, 4: 43.0, 5: 44.0,
            6: 45.0, 7: 46.0, 8: 47.0, 9: 48.0, 10: 49.0,
            11: 50.0, 12: 51.0, 13: 52.0, 14: 53.0, 15: 54.0,
            16: 55.0, 17: 56.0, 18: 57.0, 19: 58.0, 20: 59.0,
            21: 60.0, 22: 61.0, 23: 62.0, 24: 63.0, 25: 64.0,
            26: 65.0, 27: 66.0, 28: 67.0, 29: 68.0, 30: 69.0,
            31: 70.0, 32: 71.0, 33: 72.0, 34: 73.0, 35: 74.0,
            36: 75.0
        }
        
        # Obtener el mensaje del usuario
        user_message = tracker.latest_message.get('text', '')
        user_message_lower = user_message.lower()
        
        # Extraer la medida del mensaje
        medida_mm = None
        try:
            # Buscar números con punto o coma como separador decimal
            numeros = re.findall(r'\d+[,.]?\d*', user_message_lower)
            
            if not numeros:
                dispatcher.utter_message(text=msgs["no_measurement"])
                return []
            
            # Reemplazar coma por punto para convertir a float
            medida_str = numeros[0].replace(',', '.')
            medida = float(medida_str)
            
            # Normalizar el texto para búsqueda (quitar tildes y espacios extra)
            import unicodedata
            texto_normalizado = ''.join(
                c for c in unicodedata.normalize('NFD', user_message_lower)
                if unicodedata.category(c) != 'Mn'
            )
            
            # Determinar si está en cm o mm (con variaciones en ambos idiomas)
            palabras_cm = ['cm', 'centimetro', 'centimetros', 'centimeter', 'centimeters']
            palabras_mm = ['mm', 'milimetro', 'milimetros', 'millimeter', 'millimeters']
            
            es_cm = any(palabra in texto_normalizado for palabra in palabras_cm)
            es_mm = any(palabra in texto_normalizado for palabra in palabras_mm)
            
            if es_cm:
                medida_mm = medida * 10  # Convertir cm a mm
            elif es_mm:
                medida_mm = medida  # Ya está en mm
            else:
                # Si no especifica unidad, asumir mm
                medida_mm = medida
                    
        except Exception as e:
            dispatcher.utter_message(text=msgs["processing_error"].format(error=str(e)))
            return []
        
        if medida_mm is None:
            dispatcher.utter_message(text=msgs["provide_measurement"])
            return []
        
        # Buscar la talla más cercana
        talla_encontrada = None
        diferencia_minima = float('inf')
        
        for talla, circunferencia in tallas_espanolas.items():
            diferencia = abs(circunferencia - medida_mm)
            if diferencia < diferencia_minima:
                diferencia_minima = diferencia
                talla_encontrada = talla
        
        # Verificar si la medida está dentro del rango
        if medida_mm < 40.0 or medida_mm > 75.0:
            dispatcher.utter_message(
                text=msgs["out_of_range"].format(measurement=medida_mm)
            )
            return [SlotSet("talla_anillo", None)]
        
        # Responder con la talla encontrada
        dispatcher.utter_message(
            text=msgs["size_result"].format(measurement=medida_mm, size=talla_encontrada)
        )
        
        return [SlotSet("talla_anillo", talla_encontrada)]