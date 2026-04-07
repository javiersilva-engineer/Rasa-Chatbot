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
        
        requested_language = tracker.get_slot("requested_language")
        
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
        
        # Normalizar el idioma solicitado
        if requested_language:
            language_code = language_mapping.get(requested_language.lower(), "es")
        else:
            language_code = "es"
        
        return [SlotSet("language", language_code)]