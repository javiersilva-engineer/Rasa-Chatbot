from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

class ActionShowRing(Action):
    def name(self) -> Text:
        return "action_show_ring"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener el tipo de anillo solicitado
        ring_type = tracker.get_slot('ring_type')
        
        # Validar que se haya obtenido el tipo de anillo
        if not ring_type:
            dispatcher.utter_message(
                text="No pude identificar qué anillo quieres ver. ¿Podrías especificarlo?"
            )
            return []
        
        # Enviar un mensaje personalizado con metadata
        dispatcher.utter_message(
            text=f"Mostrando el anillo {ring_type}",
            json_message={
                "type": "show_ring",
                "ring_type": ring_type,
                "ring_id": "699c276e7e1e25e68dde0d96"
            }
        )
        
        return []