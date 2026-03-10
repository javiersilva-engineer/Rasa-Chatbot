import os
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import aiohttp
from dotenv import load_dotenv
from urllib.parse import quote

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
                        response_data = await response.json()
                        gemstones_array = response_data.get("gemstones", [])
                        gemstone_names = [gem["name"] for gem in gemstones_array if "name" in gem]
                        
                        if gemstone_names:
                            gemstone_list = ", ".join(gemstone_names)
                            message = f"Las gemas con las que trabajamos son: {gemstone_list}\n\n¿Hay algo más en lo que pueda ayudarle?"
                        else:
                            message = "Lo siento, actualmente no tenemos gemas disponibles."
                    else:
                        message = "Lo siento, no pude obtener la información de las gemas en este momento."
            
            buttons = [
                {
                    "title": "¿Con qué materiales trabajáis?",
                    "payload": "/start_flow{\"flow_id\": \"que_materiales_teneis\"}"
                },
                {
                    "title": "¿Qué formas tenéis?",
                    "payload": "/start_flow{\"flow_id\": \"que_formas_teneis\"}"
                },
                {
                    "title": "Quiero modificar el diseño de mi anillo",
                    "payload": "/start_flow{\"flow_id\": \"modificar_diseño_anillo\"}"
                }
            ]
            
            dispatcher.utter_message(text=message, buttons=buttons)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar las gemas disponibles."
            )
            print(f"Error al consultar la API: {str(e)}")
        
        return []


class ActionGemaConcretaDB(Action):
    
    def name(self) -> Text:
        return "action_gema_concreta_bd"
    
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            # Obtener el nombre de la gema desde el slot
            gem_name = tracker.get_slot("gem_name")
            
            if not gem_name:
                dispatcher.utter_message(
                    text="Lo siento, no he podido identificar qué gema estás buscando."
                )
                return []
            
            api_url = os.getenv("API_URL")
            # Codificar el nombre de la gema para URL (maneja espacios, tildes, etc.)
            encoded_gem_name = quote(gem_name)
            # Construir el endpoint con query parameter
            endpoint = f"{api_url}/api/gemstones?name={encoded_gem_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        # Verificar si se encontró la gema en la respuesta
                        gemstones_array = response_data.get("gemstones", [])
                        
                        if gemstones_array and len(gemstones_array) > 0:
                            message = f"Sí, trabajamos con {gem_name}. ¿Te gustaría saber más sobre esta gema?"
                        else:
                            message = f"Lo siento, no trabajamos con {gem_name} en nuestra tienda."
                    elif response.status == 404:
                        message = f"Lo siento, no trabajamos con {gem_name} en nuestra tienda."
                    else:
                        message = "Lo siento, no pude verificar la disponibilidad en este momento."
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar la gema."
            )
            print(f"Error al consultar la API: {str(e)}")
        
        return []


class ActionGemaMasResistenteBD(Action):
    
    def name(self) -> Text:
        return "action_gema_mas_resistente_bd"
    
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
                        response_data = await response.json()
                        gemstones_array = response_data.get("gemstones", [])
                        
                        # Filtrar gemas que tienen el campo hardness
                        gems_with_hardness = [
                            gem for gem in gemstones_array 
                            if "hardness" in gem and "name" in gem and gem["hardness"] is not None
                        ]
                        
                        if gems_with_hardness:
                            # Encontrar la gema más resistente (hardness más alto)
                            most_resistant = max(gems_with_hardness, key=lambda x: x["hardness"])
                            # Encontrar la gema menos resistente (hardness más bajo)
                            least_resistant = min(gems_with_hardness, key=lambda x: x["hardness"])
                            
                            message = (
                                f"La gema más resistente es {most_resistant['name']} "
                                f"con una dureza de {most_resistant['hardness']} en la escala de Mohs, "
                                f"y la gema menos resistente es {least_resistant['name']} "
                                f"con una dureza de {least_resistant['hardness']}."
                            )
                        else:
                            message = "Lo siento, no tengo información sobre la resistencia de nuestras gemas en este momento."
                    else:
                        message = "Lo siento, no pude obtener la información de resistencia de las gemas en este momento."
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar la resistencia de las gemas."
            )
            print(f"Error al consultar la API: {str(e)}")
        
        return []
    
class ActionGemaMasResistenteEntreDosDB(Action):
    
    def name(self) -> Text:
        return "action_gema_mas_resistente_entre_dos_bd"
    
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            # Obtener los nombres de las dos gemas desde los slots
            gem_name_1 = tracker.get_slot("gem_name")
            gem_name_2 = tracker.get_slot("gem_name_2")
            
            if not gem_name_1 or not gem_name_2:
                dispatcher.utter_message(
                    text="Lo siento, necesito los nombres de dos gemas para poder compararlas."
                )
                return []
            
            api_url = os.getenv("API_URL")
            
            # Consultar la primera gema
            encoded_gem_name_1 = quote(gem_name_1)
            endpoint_1 = f"{api_url}/api/gemstones?name={encoded_gem_name_1}"
            
            # Consultar la segunda gema
            encoded_gem_name_2 = quote(gem_name_2)
            endpoint_2 = f"{api_url}/api/gemstones?name={encoded_gem_name_2}"
            
            async with aiohttp.ClientSession() as session:
                # Hacer ambas peticiones
                response_1 = await session.get(endpoint_1)
                response_2 = await session.get(endpoint_2)
                
                if response_1.status == 200 and response_2.status == 200:
                    data_1 = await response_1.json()
                    data_2 = await response_2.json()
                    
                    gems_1 = data_1.get("gemstones", [])
                    gems_2 = data_2.get("gemstones", [])
                    
                    # Verificar que ambas gemas existen y tienen hardness
                    if not gems_1 or len(gems_1) == 0:
                        message = f"Lo siento, no encontré información sobre {gem_name_1}."
                    elif not gems_2 or len(gems_2) == 0:
                        message = f"Lo siento, no encontré información sobre {gem_name_2}."
                    elif "hardness" not in gems_1[0] or gems_1[0]["hardness"] is None:
                        message = f"Lo siento, no tengo información sobre la dureza de {gem_name_1}."
                    elif "hardness" not in gems_2[0] or gems_2[0]["hardness"] is None:
                        message = f"Lo siento, no tengo información sobre la dureza de {gem_name_2}."
                    else:
                        hardness_1 = gems_1[0]["hardness"]
                        hardness_2 = gems_2[0]["hardness"]
                        name_1 = gems_1[0]["name"]
                        name_2 = gems_2[0]["name"]
                        
                        if hardness_1 > hardness_2:
                            message = (
                                f"La gema {name_1} es más resistente. "
                                f"Tiene una dureza de {hardness_1} en la escala de Mohs, "
                                f"mientras que {name_2} tiene {hardness_2}."
                            )
                        elif hardness_2 > hardness_1:
                            message = (
                                f"La gema {name_2} es más resistente. "
                                f"Tiene una dureza de {hardness_2} en la escala de Mohs, "
                                f"mientras que {name_1} tiene {hardness_1}."
                            )
                        else:
                            message = (
                                f"Ambas gemas tienen la misma resistencia. "
                                f"Tanto {name_1} como {name_2} tienen una dureza de {hardness_1} "
                                f"en la escala de Mohs."
                            )
                else:
                    message = "Lo siento, no pude obtener la información de las gemas en este momento."
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al comparar las gemas."
            )
            print(f"Error al consultar la API: {str(e)}")
        
        return []
    
class ActionOpcionesMasEconomicas(Action):
    
    def name(self) -> Text:
        return "action_opciones_mas_economicas"
    
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            api_url = os.getenv("API_URL")
            
            # Endpoints para las tres tablas
            gemstones_endpoint = f"{api_url}/api/gemstones"
            base_structures_endpoint = f"{api_url}/api/baseStructures"
            materials_endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                # Hacer las tres peticiones en paralelo
                gemstones_response = await session.get(gemstones_endpoint)
                base_structures_response = await session.get(base_structures_endpoint)
                materials_response = await session.get(materials_endpoint)
                
                # Verificar que todas las respuestas sean exitosas
                if (gemstones_response.status == 200 and 
                    base_structures_response.status == 200 and 
                    materials_response.status == 200):
                    
                    gemstones_data = await gemstones_response.json()
                    base_structures_data = await base_structures_response.json()
                    materials_data = await materials_response.json()
                    
                    # Procesar gemas (buscar el precio más bajo entre natural y sintético)
                    cheapest_gem = None
                    cheapest_gem_price = None
                    cheapest_gem_type = None
                    
                    for gem in gemstones_data.get("gemstones", []):
                        if "qualities" in gem and gem["qualities"]:
                            for quality in gem["qualities"]:
                                # Verificar precio natural
                                if "pricePerCaratNatural" in quality and quality["pricePerCaratNatural"]:
                                    price_natural = float(quality["pricePerCaratNatural"]["$numberDecimal"])
                                    if cheapest_gem_price is None or price_natural < cheapest_gem_price:
                                        cheapest_gem_price = price_natural
                                        cheapest_gem = gem["name"]
                                        cheapest_gem_type = "natural"
                                
                                # Verificar precio sintético
                                if "pricePerCaratSynthetic" in quality and quality["pricePerCaratSynthetic"]:
                                    price_synthetic = float(quality["pricePerCaratSynthetic"]["$numberDecimal"])
                                    if cheapest_gem_price is None or price_synthetic < cheapest_gem_price:
                                        cheapest_gem_price = price_synthetic
                                        cheapest_gem = gem["name"]
                                        cheapest_gem_type = "sintética"
                    
                    # Procesar baseStructures (buscar el extraPrice más bajo)
                    cheapest_base_structure = None
                    cheapest_base_price = None
                    
                    for base_structure in base_structures_data.get("baseStructures", []):
                        if "profiles" in base_structure:
                            for profile in base_structure["profiles"]:
                                if "variants" in profile:
                                    for variant in profile["variants"]:
                                        if "extraPrice" in variant and variant["extraPrice"]:
                                            extra_price = float(variant["extraPrice"]["$numberDecimal"])
                                            if cheapest_base_price is None or extra_price < cheapest_base_price:
                                                cheapest_base_price = extra_price
                                                cheapest_base_structure = variant["name"]
                    
                    # Procesar materials (buscar el pricePermm3 más bajo)
                    cheapest_material = None
                    cheapest_material_price = None
                    
                    for material in materials_data.get("materials", []):
                        if "purities" in material:
                            for purity in material["purities"]:
                                if "pricePermm3" in purity and purity["pricePermm3"]:
                                    price_per_mm3 = float(purity["pricePermm3"]["$numberDecimal"])
                                    if cheapest_material_price is None or price_per_mm3 < cheapest_material_price:
                                        cheapest_material_price = price_per_mm3
                                        cheapest_material = material["name"]
                    
                    # Construir el mensaje de respuesta
                    message_parts = []
                    
                    if cheapest_gem:
                        message_parts.append(
                            f"La gema más económica es {cheapest_gem} ({cheapest_gem_type}) "
                            f"con un precio de ${cheapest_gem_price:.2f} por quilate"
                        )
                    
                    if cheapest_base_structure:
                        message_parts.append(
                            f"El diseño base más económico es {cheapest_base_structure} "
                            f"con un precio adicional de ${cheapest_base_price:.2f}"
                        )
                    
                    if cheapest_material:
                        message_parts.append(
                            f"El material más económico es {cheapest_material} "
                            f"con un precio de ${cheapest_material_price:.2f} por mm³"
                        )
                    
                    if message_parts:
                        message = "Estas son las opciones más económicas:\n\n" + "\n\n".join(message_parts)
                    else:
                        message = "Lo siento, no pude encontrar información de precios en este momento."
                else:
                    message = "Lo siento, no pude obtener la información de precios en este momento."
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar las opciones más económicas."
            )
            print(f"Error al consultar la API: {str(e)}")
        
        return []
    
class ActionSignificadoGemaDB(Action):
    
    def name(self) -> Text:
        return "action_significado_gema_bd"
    
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            # Obtener el nombre de la gema desde el slot
            gem_name = tracker.get_slot("gem_name")
            
            if not gem_name:
                dispatcher.utter_message(
                    text="Lo siento, no he podido identificar qué gema estás buscando."
                )
                return []
            
            api_url = os.getenv("API_URL")
            # Codificar el nombre de la gema para URL
            encoded_gem_name = quote(gem_name)
            endpoint = f"{api_url}/api/gemstones?name={encoded_gem_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        gemstones_array = response_data.get("gemstones", [])
                        
                        if gemstones_array and len(gemstones_array) > 0:
                            gem = gemstones_array[0]
                            gem_name_response = gem.get("name", gem_name)
                            meaning = gem.get("meaning")
                            
                            if meaning:
                                message = f"El significado de {gem_name_response} es: {meaning}"
                            else:
                                message = f"Lo siento, no tengo información sobre el significado de {gem_name_response} en este momento."
                        else:
                            message = f"Lo siento, no encontré información sobre {gem_name}."
                    elif response.status == 404:
                        message = f"Lo siento, no encontré información sobre {gem_name}."
                    else:
                        message = "Lo siento, no pude obtener la información en este momento."
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar el significado de la gema."
            )
            print(f"Error al consultar la API: {str(e)}")
        
        return []
    
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import re

class ActionChooseGem(Action):
    def name(self) -> Text:
        return "action_choose_gem"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener el último mensaje del usuario
        user_message = tracker.latest_message.get('text', '').lower()
        
        # Lista de gemas comunes
        gems = ['diamante', 'esmeralda', 'rubí', 'zafiro', 'topacio', 
                'amatista', 'perla', 'ópalo', 'jade', 'turquesa']
        
        # Encontrar las gemas mencionadas
        found_gems = [gem for gem in gems if gem in user_message]
        
        if len(found_gems) >= 2:
            # Ordenar alfabéticamente y elegir la primera
            chosen_gem = sorted(found_gems)[0]
            dispatcher.utter_message(text=f"Ambas gemas me parecen preciosas, pero prefiero {chosen_gem}.")
        else:
            dispatcher.utter_message(text="No pude identificar dos gemas en tu pregunta.")
        
        return []