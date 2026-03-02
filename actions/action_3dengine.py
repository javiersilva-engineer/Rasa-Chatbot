from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

class ActionShowRing(Action):
    def name(self) -> Text:
        return "action_show_ring"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        
        ring_type = tracker.get_slot('ring_type')
        
        if not ring_type:
            dispatcher.utter_message(
                text="No pude identificar qué anillo quieres ver. ¿Podrías especificarlo?"
            )
            return []
        
        # Usar custom en lugar de json_message
        dispatcher.utter_message(
            text=f"Mostrando el anillo {ring_type}",
            custom={
                "type": "show_ring",
                "ring_type": ring_type,
                "ring_id": "699c276e7e1e25e68dde0d96"
            }
        )
        
        return []