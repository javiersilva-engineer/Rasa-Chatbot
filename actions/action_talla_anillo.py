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
                dispatcher.utter_message(text="No encontré ninguna medida en tu mensaje. Por favor, proporciona un número seguido de la unidad (mm o cm).")
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
            
            # Determinar si está en cm o mm (con variaciones)
            palabras_cm = ['cm', 'centimetro', 'centimetros']
            palabras_mm = ['mm', 'milimetro', 'milimetros']
            
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
            dispatcher.utter_message(text=f"No pude procesar la medida. Por favor, proporciona la circunferencia de tu dedo en mm o cm. Error: {str(e)}")
            return []
        
        if medida_mm is None:
            dispatcher.utter_message(text="Por favor, proporciona la medida de tu dedo en mm o cm.")
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
                text=f"Lo siento, no existe una talla española para una circunferencia de {medida_mm} mm. "
                     f"Las tallas españolas van desde la 1 (40 mm) hasta la 36 (75 mm)."
            )
            return [SlotSet("talla_anillo", None)]
        
        # Responder con la talla encontrada
        dispatcher.utter_message(
            text=f"Para una circunferencia de {medida_mm} mm, la talla de anillo española es la {talla_encontrada}."
        )
        
        return [SlotSet("talla_anillo", talla_encontrada)]