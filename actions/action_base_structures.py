import os
from typing import Text, Dict, Any, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import aiohttp
from dotenv import load_dotenv
import traceback
import json

load_dotenv()

class ActionEstructurasBD(Action):
    
    def name(self) -> Text:
        return "action_estructuras_bd"
    
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        # Obtener el idioma del usuario desde el slot
        user_language = tracker.get_slot("language")
        if not user_language:
            user_language = "es"  # Idioma por defecto
        
        # Definir mensajes en ambos idiomas
        messages = {
            "es": {
                "available": "Las formas disponibles son: {structures}",
                "no_structures": "Lo siento, actualmente no tenemos formas disponibles.",
                "error_fetch": "Lo siento, no pude obtener la información de las formas en este momento.",
                "error_general": "Lo siento, ha ocurrido un error al consultar las formas disponibles."
            },
            "en": {
                "available": "The available shapes are: {structures}",
                "no_structures": "Sorry, we currently have no available shapes.",
                "error_fetch": "Sorry, I couldn't retrieve the shapes information at this time.",
                "error_general": "Sorry, an error occurred while querying the available shapes."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/baseStructures"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        structures_array = response_data.get("baseStructures", [])
                        structure_names = [structure["name"] for structure in structures_array if "name" in structure]
                        
                        if structure_names:
                            structure_list = ", ".join(structure_names)
                            message = msgs["available"].format(structures=structure_list)
                        else:
                            message = msgs["no_structures"]
                    else:
                        message = msgs["error_fetch"]
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
        
        return []