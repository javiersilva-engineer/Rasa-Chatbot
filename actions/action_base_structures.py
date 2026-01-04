import os
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import aiohttp
from dotenv import load_dotenv

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
        
        try:
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/baseStructures"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        # Obtener la respuesta completa
                        response_data = await response.json()
                        
                        # Extraer el array de estructuras desde la clave correspondiente
                        # Ajusta el nombre de la clave según lo que devuelva tu API
                        structures_array = response_data.get("baseStructures", [])
                        
                        # Extraer los nombres de las estructuras
                        structure_names = [structure["name"] for structure in structures_array if "name" in structure]
                        
                        # Construir mensaje
                        if structure_names:
                            structure_list = ", ".join(structure_names)
                            message = f"Las formas disponibles son: {structure_list}"
                        else:
                            message = "Lo siento, actualmente no tenemos formas disponibles."
                    else:
                        message = "Lo siento, no pude obtener la información de las formas en este momento."
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar las formas disponibles."
            )
            print(f"Error al consultar la API: {str(e)}")
        
        return []