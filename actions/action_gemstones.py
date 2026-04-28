import os
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import aiohttp
from dotenv import load_dotenv
from urllib.parse import quote
import unicodedata
import re

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
        
        # Obtener el idioma del usuario desde el slot
        user_language = tracker.get_slot("language")
        if not user_language:
            user_language = "es"  # Idioma por defecto
        
        # Definir mensajes en ambos idiomas
        messages = {
            "es": {
                "available": "Las gemas con las que trabajamos son: {gemstones}\n\n¿Hay algo más en lo que pueda ayudarle?",
                "no_gemstones": "Lo siento, actualmente no tenemos gemas disponibles.",
                "error_fetch": "Lo siento, no pude obtener la información de las gemas en este momento.",
                "error_general": "Lo siento, ha ocurrido un error al consultar las gemas disponibles."
            },
            "en": {
                "available": "The gemstones we work with are: {gemstones}\n\nIs there anything else I can help you with?",
                "no_gemstones": "Sorry, we currently have no gemstones available.",
                "error_fetch": "Sorry, I couldn't retrieve the gemstones information at this time.",
                "error_general": "Sorry, an error occurred while querying the available gemstones."
            }
        }
        
        # Definir botones en ambos idiomas
        buttons_config = {
            "es": [
                {
                    "title": "¿Con qué materiales trabajáis?",
                    "payload": "/start_flow{\"flow_id\": \"que_materiales_teneis\"}"
                },
                {
                    "title": "¿Qué formas de anillo tenéis?",
                    "payload": "/start_flow{\"flow_id\": \"que_formas_teneis\"}"
                },
                {
                    "title": "Quiero modificar el diseño de mi anillo",
                    "payload": "/start_flow{\"flow_id\": \"modificar_diseño_anillo\"}"
                }
            ],
            "en": [
                {
                    "title": "What materials do you work with?",
                    "payload": "/start_flow{\"flow_id\": \"que_materiales_teneis\"}"
                },
                {
                    "title": "What ring shapes do you have?",
                    "payload": "/start_flow{\"flow_id\": \"que_formas_teneis\"}"
                },
                {
                    "title": "I want to modify my ring design",
                    "payload": "/start_flow{\"flow_id\": \"modificar_diseño_anillo\"}"
                }
            ]
        }
        
        # Seleccionar el conjunto de mensajes y botones según el idioma
        msgs = messages.get(user_language, messages["es"])
        buttons = buttons_config.get(user_language, buttons_config["es"])
        
        try:
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/gemstones"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        gemstones_array = response_data.get("gemstones", [])
                        gemstone_names = [
                            gem["name"] for gem in gemstones_array 
                            if "name" in gem and gem["name"] is not None and gem["name"] != "None"
                        ]
                        
                        if gemstone_names:
                            gemstone_list = ", ".join(gemstone_names)
                            message = msgs["available"].format(gemstones=gemstone_list)
                        else:
                            message = msgs["no_gemstones"]
                    else:
                        message = msgs["error_fetch"]
            
            dispatcher.utter_message(text=message, buttons=buttons)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
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
        
        # Obtener el idioma del usuario desde el slot
        user_language = tracker.get_slot("language")
        if not user_language:
            user_language = "es"  # Idioma por defecto
        
        # Definir mensajes en ambos idiomas
        messages = {
            "es": {
                "no_gem_identified": "Lo siento, no he podido identificar qué gema estás buscando.",
                "available": "Sí, trabajamos con {gem_name}.",
                "not_available": "Lo siento, no trabajamos con {gem_name} en nuestra tienda.",
                "error_fetch": "Lo siento, no pude verificar la disponibilidad en este momento.",
                "error_general": "Lo siento, ha ocurrido un error al consultar la gema."
            },
            "en": {
                "no_gem_identified": "Sorry, I couldn't identify which gemstone you're looking for.",
                "available": "Yes, we work with {gem_name}.",
                "not_available": "Sorry, we don't work with {gem_name} in our store.",
                "error_fetch": "Sorry, I couldn't verify availability at this time.",
                "error_general": "Sorry, an error occurred while querying the gemstone."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            # Obtener el nombre de la gema desde el slot
            gem_name = tracker.get_slot("gem_name")
            
            if not gem_name:
                dispatcher.utter_message(text=msgs["no_gem_identified"])
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
                            message = msgs["available"].format(gem_name=gem_name)
                        else:
                            message = msgs["not_available"].format(gem_name=gem_name)
                    elif response.status == 404:
                        message = msgs["not_available"].format(gem_name=gem_name)
                    else:
                        message = msgs["error_fetch"]
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
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
        
        # Obtener el idioma del usuario desde el slot
        user_language = tracker.get_slot("language")
        if not user_language:
            user_language = "es"  # Idioma por defecto
        
        # Definir mensajes en ambos idiomas
        messages = {
            "es": {
                "hardness_info": (
                    "La gema más resistente es {most_resistant} "
                    "con una dureza de {most_hardness} en la escala de Mohs, "
                    "y la gema menos resistente es {least_resistant} "
                    "con una dureza de {least_hardness}."
                ),
                "no_hardness_data": "Lo siento, no tengo información sobre la resistencia de nuestras gemas en este momento.",
                "error_fetch": "Lo siento, no pude obtener la información de resistencia de las gemas en este momento.",
                "error_general": "Lo siento, ha ocurrido un error al consultar la resistencia de las gemas."
            },
            "en": {
                "hardness_info": (
                    "The most resistant gemstone is {most_resistant} "
                    "with a hardness of {most_hardness} on the Mohs scale, "
                    "and the least resistant gemstone is {least_resistant} "
                    "with a hardness of {least_hardness}."
                ),
                "no_hardness_data": "Sorry, I don't have information about the resistance of our gemstones at this time.",
                "error_fetch": "Sorry, I couldn't retrieve the gemstone resistance information at this time.",
                "error_general": "Sorry, an error occurred while querying the gemstone resistance."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
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
                            
                            message = msgs["hardness_info"].format(
                                most_resistant=most_resistant['name'],
                                most_hardness=most_resistant['hardness'],
                                least_resistant=least_resistant['name'],
                                least_hardness=least_resistant['hardness']
                            )
                        else:
                            message = msgs["no_hardness_data"]
                    else:
                        message = msgs["error_fetch"]
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
        
        return []
    
import unicodedata

class ActionGemaMasResistenteEntreDosDB(Action):
    
    def name(self) -> Text:
        return "action_gema_mas_resistente_entre_dos_bd"
    
    def normalize_gem_name(self, gem_name: Text) -> Text:
        """Normaliza el nombre de la gema: elimina acentos y convierte a minúsculas."""
        if not gem_name:
            return gem_name
        normalized = unicodedata.normalize('NFD', gem_name.strip().lower())
        return ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
    
    def find_gem_by_normalized_name(self, gems_list: list, target_name: Text) -> dict:
        """Busca una gema en la lista comparando nombres normalizados."""
        normalized_target = self.normalize_gem_name(target_name)
        for gem in gems_list:
            if "name" in gem and self.normalize_gem_name(gem["name"]) == normalized_target:
                return gem
        return None
    
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
                "need_two_gems": "Lo siento, necesito los nombres de dos gemas para poder compararlas.",
                "gem_not_found": "Lo siento, no encontré información sobre {gem_name}.",
                "no_hardness_data": "Lo siento, no tengo información sobre la dureza de {gem_name}.",
                "gem1_more_resistant": (
                    "La gema {name_1} es más resistente. "
                    "Tiene una dureza de {hardness_1} en la escala de Mohs, "
                    "mientras que {name_2} tiene {hardness_2}."
                ),
                "gem2_more_resistant": (
                    "La gema {name_2} es más resistente. "
                    "Tiene una dureza de {hardness_2} en la escala de Mohs, "
                    "mientras que {name_1} tiene {hardness_1}."
                ),
                "same_resistance": (
                    "Ambas gemas tienen la misma resistencia. "
                    "Tanto {name_1} como {name_2} tienen una dureza de {hardness} "
                    "en la escala de Mohs."
                ),
                "error_fetch": "Lo siento, no pude obtener la información de las gemas en este momento.",
                "error_general": "Lo siento, ha ocurrido un error al comparar las gemas."
            },
            "en": {
                "need_two_gems": "Sorry, I need the names of two gemstones to compare them.",
                "gem_not_found": "Sorry, I couldn't find information about {gem_name}.",
                "no_hardness_data": "Sorry, I don't have hardness information for {gem_name}.",
                "gem1_more_resistant": (
                    "The gemstone {name_1} is more resistant. "
                    "It has a hardness of {hardness_1} on the Mohs scale, "
                    "while {name_2} has {hardness_2}."
                ),
                "gem2_more_resistant": (
                    "The gemstone {name_2} is more resistant. "
                    "It has a hardness of {hardness_2} on the Mohs scale, "
                    "while {name_1} has {hardness_1}."
                ),
                "same_resistance": (
                    "Both gemstones have the same resistance. "
                    "Both {name_1} and {name_2} have a hardness of {hardness} "
                    "on the Mohs scale."
                ),
                "error_fetch": "Sorry, I couldn't retrieve the gemstone information at this time.",
                "error_general": "Sorry, an error occurred while comparing the gemstones."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            gem_name_1 = tracker.get_slot("gem_name")
            gem_name_2 = tracker.get_slot("gem_name_2")
            
            if not gem_name_1 or not gem_name_2:
                dispatcher.utter_message(text=msgs["need_two_gems"])
                return []
            
            api_url = os.getenv("API_URL")
            # Consultar TODAS las gemas
            endpoint = f"{api_url}/api/gemstones"
            
            async with aiohttp.ClientSession() as session:
                response = await session.get(endpoint)
                
                if response.status == 200:
                    data = await response.json()
                    all_gems = data.get("gemstones", [])
                    
                    # Buscar las gemas por nombre normalizado
                    gem_1 = self.find_gem_by_normalized_name(all_gems, gem_name_1)
                    gem_2 = self.find_gem_by_normalized_name(all_gems, gem_name_2)
                    
                    if not gem_1:
                        message = msgs["gem_not_found"].format(gem_name=gem_name_1)
                    elif not gem_2:
                        message = msgs["gem_not_found"].format(gem_name=gem_name_2)
                    elif "hardness" not in gem_1 or gem_1["hardness"] is None:
                        message = msgs["no_hardness_data"].format(gem_name=gem_name_1)
                    elif "hardness" not in gem_2 or gem_2["hardness"] is None:
                        message = msgs["no_hardness_data"].format(gem_name=gem_name_2)
                    else:
                        hardness_1 = gem_1["hardness"]
                        hardness_2 = gem_2["hardness"]
                        name_1 = gem_1["name"]
                        name_2 = gem_2["name"]
                        
                        if hardness_1 > hardness_2:
                            message = msgs["gem1_more_resistant"].format(
                                name_1=name_1,
                                hardness_1=hardness_1,
                                name_2=name_2,
                                hardness_2=hardness_2
                            )
                        elif hardness_2 > hardness_1:
                            message = msgs["gem2_more_resistant"].format(
                                name_1=name_1,
                                hardness_1=hardness_1,
                                name_2=name_2,
                                hardness_2=hardness_2
                            )
                        else:
                            message = msgs["same_resistance"].format(
                                name_1=name_1,
                                name_2=name_2,
                                hardness=hardness_1
                            )
                else:
                    message = msgs["error_fetch"]
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
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
        
        # Obtener el idioma del usuario desde el slot
        user_language = tracker.get_slot("language")
        if not user_language:
            user_language = "es"  # Idioma por defecto
        
        # Definir mensajes en ambos idiomas
        messages = {
            "es": {
                "cheapest_gem": (
                    "La gema más económica es {gem_name} ({gem_type}) "
                    "con un precio de ${price:.2f} por quilate"
                ),
                "cheapest_base": (
                    "El diseño base más económico es {base_name} "
                    "con un precio adicional de ${price:.2f}"
                ),
                "cheapest_material": (
                    "El material más económico es {material_name} "
                    "con un precio de ${price:.2f} por mm³"
                ),
                "header": "Estas son las opciones más económicas:\n\n",
                "no_price_info": "Lo siento, no pude encontrar información de precios en este momento.",
                "error_fetch": "Lo siento, no pude obtener la información de precios en este momento.",
                "error_general": "Lo siento, ha ocurrido un error al consultar las opciones más económicas.",
                "natural": "natural",
                "synthetic": "sintética"
            },
            "en": {
                "cheapest_gem": (
                    "The most affordable gemstone is {gem_name} ({gem_type}) "
                    "at ${price:.2f} per carat"
                ),
                "cheapest_base": (
                    "The most affordable base design is {base_name} "
                    "with an additional price of ${price:.2f}"
                ),
                "cheapest_material": (
                    "The most affordable material is {material_name} "
                    "at ${price:.2f} per mm³"
                ),
                "header": "These are the most affordable options:\n\n",
                "no_price_info": "Sorry, I couldn't find pricing information at this time.",
                "error_fetch": "Sorry, I couldn't retrieve the pricing information at this time.",
                "error_general": "Sorry, an error occurred while querying the most affordable options.",
                "natural": "natural",
                "synthetic": "synthetic"
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
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
                                        cheapest_gem_type = msgs["natural"]
                                
                                # Verificar precio sintético
                                if "pricePerCaratSynthetic" in quality and quality["pricePerCaratSynthetic"]:
                                    price_synthetic = float(quality["pricePerCaratSynthetic"]["$numberDecimal"])
                                    if cheapest_gem_price is None or price_synthetic < cheapest_gem_price:
                                        cheapest_gem_price = price_synthetic
                                        cheapest_gem = gem["name"]
                                        cheapest_gem_type = msgs["synthetic"]
                    
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
                            msgs["cheapest_gem"].format(
                                gem_name=cheapest_gem,
                                gem_type=cheapest_gem_type,
                                price=cheapest_gem_price
                            )
                        )
                    
                    if cheapest_base_structure:
                        message_parts.append(
                            msgs["cheapest_base"].format(
                                base_name=cheapest_base_structure,
                                price=cheapest_base_price
                            )
                        )
                    
                    if cheapest_material:
                        message_parts.append(
                            msgs["cheapest_material"].format(
                                material_name=cheapest_material,
                                price=cheapest_material_price
                            )
                        )
                    
                    if message_parts:
                        message = msgs["header"] + "\n\n".join(message_parts)
                    else:
                        message = msgs["no_price_info"]
                else:
                    message = msgs["error_fetch"]
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
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
        
        # Obtener el idioma del usuario desde el slot
        user_language = tracker.get_slot("language")
        if not user_language:
            user_language = "es"  # Idioma por defecto
        
        # Definir mensajes en ambos idiomas
        messages = {
            "es": {
                "no_gem_identified": "Lo siento, no he podido identificar qué gema estás buscando.",
                "meaning": "El significado de {gem_name} es: {meaning}",
                "no_meaning_data": "Lo siento, no tengo información sobre el significado de {gem_name} en este momento.",
                "gem_not_found": "Lo siento, no encontré información sobre {gem_name}.",
                "error_fetch": "Lo siento, no pude obtener la información en este momento.",
                "error_general": "Lo siento, ha ocurrido un error al consultar el significado de la gema."
            },
            "en": {
                "no_gem_identified": "Sorry, I couldn't identify which gemstone you're looking for.",
                "meaning": "The meaning of {gem_name} is: {meaning}",
                "no_meaning_data": "Sorry, I don't have information about the meaning of {gem_name} at this time.",
                "gem_not_found": "Sorry, I couldn't find information about {gem_name}.",
                "error_fetch": "Sorry, I couldn't retrieve the information at this time.",
                "error_general": "Sorry, an error occurred while querying the gemstone meaning."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            # Obtener el nombre de la gema desde el slot
            gem_name = tracker.get_slot("gem_name")
            
            if not gem_name:
                dispatcher.utter_message(text=msgs["no_gem_identified"])
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
                                message = msgs["meaning"].format(
                                    gem_name=gem_name_response,
                                    meaning=meaning
                                )
                            else:
                                message = msgs["no_meaning_data"].format(gem_name=gem_name_response)
                        else:
                            message = msgs["gem_not_found"].format(gem_name=gem_name)
                    elif response.status == 404:
                        message = msgs["gem_not_found"].format(gem_name=gem_name)
                    else:
                        message = msgs["error_fetch"]
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
        
        return []
    



class ActionChooseGem(Action):
    def name(self) -> Text:
        return "action_choose_gem"
    
    def normalize_text(self, text: Text) -> Text:
        """Normaliza texto: elimina acentos, convierte a minúsculas y elimina espacios extra."""
        if not text:
            return text
        # Normalizar Unicode y eliminar acentos
        normalized = unicodedata.normalize('NFD', text.strip().lower())
        without_accents = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
        return without_accents
    
    def singularize(self, word: Text) -> Text:
        """Convierte plurales simples a singular."""
        word = word.strip()
        if word.endswith('s') and len(word) > 2:
            return word[:-1]
        return word
    
    def find_gems_in_text(self, text: Text, gem_list: list) -> list:
        """Encuentra gemas en el texto usando normalización flexible."""
        normalized_text = self.normalize_text(text)
        found_gems = []
        
        # Crear versiones normalizadas de las gemas
        for gem in gem_list:
            normalized_gem = self.normalize_text(gem)
            # Buscar tanto singular como plural
            singular_gem = self.singularize(normalized_gem)
            
            # Buscar con límites de palabra para evitar coincidencias parciales
            pattern_singular = r'\b' + re.escape(singular_gem) + r's?\b'
            
            if re.search(pattern_singular, normalized_text):
                found_gems.append(gem)
        
        return found_gems
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener el idioma del usuario desde el slot
        user_language = tracker.get_slot("language")
        if not user_language:
            user_language = "es"  # Idioma por defecto
        
        # Definir mensajes en ambos idiomas
        messages = {
            "es": {
                "both_beautiful": "Ambas gemas me parecen preciosas, pero prefiero {gem}.",
                "only_one": "Solo mencionaste {gem}. ¿Podrías mencionar otra gema para comparar?",
                "no_gems": "No pude identificar dos gemas en tu pregunta. ¿Podrías mencionarlas de nuevo?"
            },
            "en": {
                "both_beautiful": "Both gemstones seem beautiful to me, but I prefer {gem}.",
                "only_one": "You only mentioned {gem}. Could you mention another gemstone to compare?",
                "no_gems": "I couldn't identify two gemstones in your question. Could you mention them again?"
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        # Obtener el último mensaje del usuario
        user_message = tracker.latest_message.get('text', '')
        
        # Lista de gemas comunes (con acentos originales)
        gems = ['diamante', 'esmeralda', 'rubí', 'zafiro', 'topacio', 
                'amatista', 'perla', 'ópalo', 'jade', 'turquesa']
        
        # Encontrar las gemas mencionadas
        found_gems = self.find_gems_in_text(user_message, gems)
        
        if len(found_gems) >= 2:
            # Ordenar alfabéticamente y elegir la primera
            chosen_gem = sorted(found_gems)[0]
            dispatcher.utter_message(text=msgs["both_beautiful"].format(gem=chosen_gem))
        elif len(found_gems) == 1:
            dispatcher.utter_message(text=msgs["only_one"].format(gem=found_gems[0]))
        else:
            dispatcher.utter_message(text=msgs["no_gems"])
        
        return []


class ActionRecomendacionSignoZodiacal(Action):
    
    def name(self) -> Text:
        return "action_recomendacion_signo_zodiacal"
    
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
                "no_sign_identified": "Lo siento, no he podido identificar el signo zodiacal.",
                "recommendation_header": "Para el signo {zodiac_sign}, te recomiendo:",
                "gems_label": "\n\nGemas: {gems}",
                "materials_label": "\n\nMateriales: {materials}",
                "any_combination": "Para el signo {zodiac_sign}, cualquier combinación de gemas y materiales quedaría bien.",
                "error_general": "Lo siento, ha ocurrido un error al consultar las recomendaciones."
            },
            "en": {
                "no_sign_identified": "Sorry, I couldn't identify the zodiac sign.",
                "recommendation_header": "For the {zodiac_sign} sign, I recommend:",
                "gems_label": "\n\nGemstones: {gems}",
                "materials_label": "\n\nMaterials: {materials}",
                "any_combination": "For the {zodiac_sign} sign, any combination of gemstones and materials would look great.",
                "error_general": "Sorry, an error occurred while querying the recommendations."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            # Obtener el signo zodiacal desde el slot
            zodiac_sign = tracker.get_slot("zodiac_sign")
            
            if not zodiac_sign:
                dispatcher.utter_message(text=msgs["no_sign_identified"])
                return []
            
            # Normalizar el signo zodiacal a minúsculas
            zodiac_sign_normalized = zodiac_sign.lower().strip()
            
            api_url = os.getenv("API_URL")
            
            # Consultar gemas y materiales
            encoded_zodiac = quote(zodiac_sign_normalized)
            gemstones_endpoint = f"{api_url}/api/gemstones?zodiac={encoded_zodiac}"
            materials_endpoint = f"{api_url}/api/materials?zodiac={encoded_zodiac}"
            
            recommended_gems = []
            recommended_materials = []
            
            async with aiohttp.ClientSession() as session:
                # Consultar gemas
                async with session.get(gemstones_endpoint) as gem_response:
                    print(f"DEBUG - Gemstones endpoint: {gemstones_endpoint}")
                    print(f"DEBUG - Gemstones status: {gem_response.status}")
                    
                    if gem_response.status == 200:
                        gem_data = await gem_response.json()
                        print(f"DEBUG - Gemstones response: {gem_data}")
                        
                        gemstones_array = gem_data.get("gemstones", [])
                        print(f"DEBUG - Gemstones array length: {len(gemstones_array)}")
                        
                        recommended_gems = [gem.get("name") for gem in gemstones_array if gem.get("name")]
                        print(f"DEBUG - Recommended gems: {recommended_gems}")
                
                # Consultar materiales
                async with session.get(materials_endpoint) as material_response:
                    print(f"DEBUG - Materials endpoint: {materials_endpoint}")
                    print(f"DEBUG - Materials status: {material_response.status}")
                    
                    if material_response.status == 200:
                        material_data = await material_response.json()
                        print(f"DEBUG - Materials response: {material_data}")
                        
                        materials_array = material_data.get("materials", [])
                        print(f"DEBUG - Materials array length: {len(materials_array)}")
                        
                        recommended_materials = [mat.get("name") for mat in materials_array if mat.get("name")]
                        print(f"DEBUG - Recommended materials: {recommended_materials}")
            
            # Construir el mensaje de respuesta
            if recommended_gems or recommended_materials:
                message_parts = [msgs["recommendation_header"].format(zodiac_sign=zodiac_sign)]
                
                if recommended_gems:
                    gems_text = ", ".join(recommended_gems)
                    message_parts.append(msgs["gems_label"].format(gems=gems_text))
                
                if recommended_materials:
                    materials_text = ", ".join(recommended_materials)
                    message_parts.append(msgs["materials_label"].format(materials=materials_text))
                
                message = "".join(message_parts)
            else:
                message = msgs["any_combination"].format(zodiac_sign=zodiac_sign)
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return []