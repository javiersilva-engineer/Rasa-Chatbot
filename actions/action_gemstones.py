import os
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import aiohttp
from dotenv import load_dotenv

load_dotenv()

class ActionGemasDB(Action):
    
    def name(self) -> Text:
        return "action_gemas_bd"
    
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/gemstones"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        # Obtener la respuesta completa
                        response_data = await response.json()
                        
                        # Extraer el array de gemas desde la clave "gemstones"
                        gemstones_array = response_data.get("gemstones", [])
                        
                        # Extraer los nombres de las gemas
                        gemstone_names = [gem["name"] for gem in gemstones_array if "name" in gem]
                        
                        # Construir mensaje
                        if gemstone_names:
                            gemstone_list = ", ".join(gemstone_names)
                            message = f"Las gemas con las que trabajamos son: {gemstone_list}"
                        else:
                            message = "Lo siento, actualmente no tenemos gemas disponibles."
                    else:
                        message = "Lo siento, no pude obtener la información de las gemas en este momento."
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar las gemas disponibles."
            )
            print(f"Error al consultar la API: {str(e)}")
        
        return []