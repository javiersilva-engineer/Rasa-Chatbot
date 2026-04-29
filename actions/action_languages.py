from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

class ActionChangeLanguage(Action):
    def name(self) -> Text:
        return "action_change_language"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener el idioma solicitado del último mensaje del usuario
        latest_message = tracker.latest_message.get('text', '').lower()
        
        # Mapear el idioma solicitado al código correcto
        language_mapping = {
            "inglés": "en",
            "ingles": "en",
            "english": "en",
            "español": "es",
            "espanol": "es",
            "spanish": "es",
            "en": "en",
            "es": "es"
        }
        
        # Detectar el idioma en el mensaje
        language_code = "es"  # Default
        for keyword, code in language_mapping.items():
            if keyword in latest_message:
                language_code = code
                break
        
        # Confirmar el cambio en el idioma apropiado
        # if language_code == "en":
        #     dispatcher.utter_message(text="Language changed to English.")
        # else:
        #     dispatcher.utter_message(text="Idioma cambiado a español.")
        
        return [SlotSet("language", language_code)]