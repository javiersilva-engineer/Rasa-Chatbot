import os
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import aiohttp
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

class ActionMaterialesDB(Action):
    
    def name(self) -> Text:
        return "action_materiales_bd"
    
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        materials_array = response_data.get("materials", [])
                        material_names = [material["name"] for material in materials_array if "name" in material]
                        
                        if material_names:
                            material_list = ", ".join(material_names)
                            message = f"Los materiales con los que trabajamos son: {material_list}"
                        else:
                            message = "Lo siento, actualmente no tenemos materiales disponibles."
                    else:
                        message = "Lo siento, no pude obtener la información de los materiales en este momento."
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar los materiales disponibles."
            )
            print(f"Error al consultar la API: {str(e)}")
        
        return []