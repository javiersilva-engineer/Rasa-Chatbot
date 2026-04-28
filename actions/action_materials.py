import os
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import aiohttp
from dotenv import load_dotenv
from urllib.parse import quote
import unicodedata

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
        
        # Obtener el idioma del usuario desde el slot
        user_language = tracker.get_slot("language")
        if not user_language:
            user_language = "es"  # Idioma por defecto
        
        # Definir mensajes en ambos idiomas
        messages = {
            "es": {
                "available": "Los materiales con los que trabajamos son: {materials}",
                "no_materials": "Lo siento, actualmente no tenemos materiales disponibles.",
                "error_fetch": "Lo siento, no pude obtener la información de los materiales en este momento.",
                "error_general": "Lo siento, ha ocurrido un error al consultar los materiales disponibles."
            },
            "en": {
                "available": "The materials we work with are: {materials}",
                "no_materials": "Sorry, we currently have no materials available.",
                "error_fetch": "Sorry, I couldn't retrieve the materials information at this time.",
                "error_general": "Sorry, an error occurred while querying the available materials."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
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
                            message = msgs["available"].format(materials=material_list)
                        else:
                            message = msgs["no_materials"]
                    else:
                        message = msgs["error_fetch"]
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
        
        return []


class ActionCheckMaterialVariants(Action):
    
    def name(self) -> Text:
        return "action_check_material_variants"
    
    def normalize_text(self, text: str) -> str:
        """Normaliza el texto eliminando tildes y convirtiendo a minúsculas."""
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        return text.lower().strip()
    
    def extract_base_material(self, material_name: str) -> str:
        """Extrae el material base (ej: 'oro' de 'oro rosa')."""
        normalized = self.normalize_text(material_name)
        base_materials = ['oro', 'plata', 'platino', 'acero', 'titanio', 'paladio']
        
        for base in base_materials:
            if base in normalized:
                return base
        return normalized
    
    def find_exact_match(self, materials_list: list, material_name: str) -> dict:
        """Busca una coincidencia exacta del material."""
        normalized_search = self.normalize_text(material_name)
        
        for material in materials_list:
            material_db_name = material.get("name", "")
            if self.normalize_text(material_db_name) == normalized_search:
                return material
        return None
    
    def get_material_variants(self, materials_list: list, base_material: str) -> list:
        """Obtiene todas las variantes de un material base."""
        normalized_base = self.normalize_text(base_material)
        variants = []
        
        for material in materials_list:
            material_name = material.get("name", "")
            normalized_name = self.normalize_text(material_name)
            
            if normalized_base in normalized_name:
                variants.append(material)
        
        return variants
    
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
                "no_material_identified": "Lo siento, no he podido identificar de qué material quieres saber sobre alergias.",
                "error_fetch": "Lo siento, no pude obtener la información de los materiales en este momento.",
                "not_found": "Lo siento, no encontré información sobre {material_name} en nuestra base de datos.",
                "multiple_variants": "Encontré varios tipos de {base_material}.",
                "error_general": "Lo siento, ha ocurrido un error al consultar los materiales."
            },
            "en": {
                "no_material_identified": "Sorry, I couldn't identify which material you want to know about regarding allergies.",
                "error_fetch": "Sorry, I couldn't retrieve the materials information at this time.",
                "not_found": "Sorry, I couldn't find information about {material_name} in our database.",
                "multiple_variants": "I found several types of {base_material}.",
                "error_general": "Sorry, an error occurred while querying the materials."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            material_name = tracker.get_slot("material_name")
            
            if not material_name:
                dispatcher.utter_message(text=msgs["no_material_identified"])
                return [SlotSet("needs_clarification", False)]
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(text=msgs["error_fetch"])
                        return [SlotSet("needs_clarification", False)]
                    
                    response_data = await response.json()
                    materials_array = response_data.get("materials", [])
                    
                    # PRIMERO: Intentar buscar coincidencia exacta
                    exact_match = self.find_exact_match(materials_array, material_name)
                    
                    if exact_match:
                        # Si hay coincidencia exacta, no necesita clarificación
                        return [SlotSet("needs_clarification", False)]
                    
                    # SEGUNDO: Si no hay coincidencia exacta, buscar por material base
                    base_material = self.extract_base_material(material_name)
                    variants = self.get_material_variants(materials_array, base_material)
                    
                    if not variants:
                        dispatcher.utter_message(
                            text=msgs["not_found"].format(material_name=material_name)
                        )
                        return [SlotSet("needs_clarification", False)]
                    
                    # Si solo hay una variante, no necesita clarificación
                    if len(variants) == 1:
                        # Actualizar el slot con el nombre exacto de la base de datos
                        exact_name = variants[0].get("name")
                        return [
                            SlotSet("material_name", exact_name),
                            SlotSet("needs_clarification", False)
                        ]
                    
                    # Si hay múltiples variantes, mostrar botones
                    buttons = []
                    for variant in variants:
                        variant_name = variant.get("name")
                        buttons.append({
                            "title": variant_name,
                            "payload": f'/set_slot{{"material_name": "{variant_name}"}}'
                        })
                    
                    dispatcher.utter_message(
                        text=msgs["multiple_variants"].format(base_material=base_material),
                        buttons=buttons
                    )
                    return [SlotSet("needs_clarification", True)]
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
            return [SlotSet("needs_clarification", False)]
        

class ActionShowAllergies(Action):
    def name(self) -> Text:
        return "action_show_allergies"
    
    def normalize_text(self, text: str) -> str:
        """Normaliza el texto eliminando tildes y convirtiendo a minúsculas."""
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        return text.lower().strip()
    
    def translate_allergen(self, allergen: str, language: str = "es") -> str:
        """Traduce los alérgenos según el idioma."""
        translations = {
            'nickel': {'es': 'níquel', 'en': 'nickel'},
            'zinc': {'es': 'zinc', 'en': 'zinc'},
            'copper': {'es': 'cobre', 'en': 'copper'}
        }
        allergen_lower = allergen.lower().strip()
        allergen_translations = translations.get(allergen_lower, {})
        return allergen_translations.get(language, allergen)
    
    def get_unique_allergens(self, material: dict) -> tuple:
        """Obtiene alérgenos únicos de todas las purezas de un material."""
        purities = material.get("purities", [])
        all_allergens = set()
        has_allergies = False
        
        for purity in purities:
            allergies = purity.get("allegies", False)
            allergens = purity.get("allergens", [])
            
            if allergies and allergens:
                has_allergies = True
                all_allergens.update(allergens)
        
        return has_allergies, list(all_allergens)
    
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
                "no_material_identified": "Lo siento, no he podido identificar de qué material quieres saber sobre alergias.",
                "error_fetch": "Lo siento, no pude obtener la información de los materiales en este momento.",
                "not_found": "Lo siento, no encontré información sobre {material_name} en nuestra base de datos.",
                "has_allergies": "Sí, {material_name} puede causar alergias.\nContiene los siguientes alérgenos: {allergens}",
                "no_allergies": "El {material_name} no causa alergias según nuestra información. Es hipoalergénico.",
                "error_general": "Lo siento, ha ocurrido un error al consultar las alergias del material."
            },
            "en": {
                "no_material_identified": "Sorry, I couldn't identify which material you want to know about regarding allergies.",
                "error_fetch": "Sorry, I couldn't retrieve the materials information at this time.",
                "not_found": "Sorry, I couldn't find information about {material_name} in our database.",
                "has_allergies": "Yes, {material_name} can cause allergies.\nIt contains the following allergens: {allergens}",
                "no_allergies": "{material_name} does not cause allergies according to our information. It is hypoallergenic.",
                "error_general": "Sorry, an error occurred while querying the material allergies."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            material_name = tracker.get_slot("material_name")
            
            if not material_name:
                dispatcher.utter_message(text=msgs["no_material_identified"])
                return []
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(text=msgs["error_fetch"])
                        return []
                    
                    response_data = await response.json()
                    materials_array = response_data.get("materials", [])
                    
                    # Buscar el material exacto
                    material_found = None
                    normalized_search = self.normalize_text(material_name)
                    
                    for material in materials_array:
                        material_db_name = material.get("name", "")
                        if self.normalize_text(material_db_name) == normalized_search:
                            material_found = material
                            break
                    
                    if not material_found:
                        dispatcher.utter_message(
                            text=msgs["not_found"].format(material_name=material_name)
                        )
                        return []
                    
                    # Mostrar información de alergias
                    material_name_response = material_found.get("name")
                    has_allergies, allergens = self.get_unique_allergens(material_found)
                    
                    if has_allergies:
                        # Traducir cada alérgeno según el idioma
                        allergens_translated = [
                            self.translate_allergen(allergen, user_language) 
                            for allergen in allergens
                        ]
                        allergens_list = ", ".join(allergens_translated)
                        message = msgs["has_allergies"].format(
                            material_name=material_name_response,
                            allergens=allergens_list
                        )
                    else:
                        message = msgs["no_allergies"].format(material_name=material_name_response)
                    
                    dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
        
        return []


class ActionTiposMaterialBD(Action):
    def name(self) -> Text:
        return "action_tipos_material_bd"
    
    def normalize_text(self, text: str) -> str:
        """Normaliza el texto eliminando tildes y convirtiendo a minúsculas."""
        import unicodedata
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        return text.lower().strip()
    
    def remove_plural(self, text: str) -> str:
        """Intenta convertir plurales a singular (reglas básicas del español)."""
        text = text.lower().strip()
        
        if text.endswith('es') and len(text) > 3:
            return text[:-2]
        elif text.endswith('s') and len(text) > 2:
            return text[:-1]
        
        return text
    
    def translate_material_to_english(self, material: str) -> tuple:
        """
        Traduce nombres de materiales comunes del español al inglés.
        Retorna una tupla (término_inglés, término_español_display)
        """
        translations = {
            "oro": ("gold", "oro"),
            "plata": ("silver", "plata"),
            "platino": ("platinum", "platino"),
            "paladio": ("palladium", "paladio"),
            "titanio": ("titanium", "titanio"),
            "acero": ("steel", "acero"),
            "bronce": ("bronze", "bronce"),
            "cobre": ("copper", "cobre"),
            "aluminio": ("aluminum", "aluminio"),
            "hierro": ("iron", "hierro"),
            "niquel": ("nickel", "níquel"),
            "zinc": ("zinc", "zinc"),
            "estano": ("tin", "estaño"),
            "plomo": ("lead", "plomo"),
            "tungsteno": ("tungsten", "tungsteno"),
            "rodio": ("rhodium", "rodio"),
            "iridio": ("iridium", "iridio"),
            "osmio": ("osmium", "osmio"),
            "rutenio": ("ruthenium", "rutenio")
        }
        
        normalized = self.normalize_text(material)
        normalized_singular = self.remove_plural(normalized)
        
        if normalized in translations:
            return translations[normalized]
        elif normalized_singular in translations:
            return translations[normalized_singular]
        
        return (normalized_singular, normalized_singular)
    
    def get_material_display_name(self, material: str, language: str) -> str:
        """Obtiene el nombre del material en el idioma apropiado."""
        material_english, material_spanish = self.translate_material_to_english(material)
        
        # Si el idioma es inglés, usar el término en inglés
        if language == "en":
            return material_english
        # Por defecto, usar el término en español
        return material_spanish
    
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
                "no_material_identified": "Lo siento, no he podido identificar de qué material quieres conocer los tipos.",
                "available_types": "Los tipos de {material} que trabajamos son: {types}",
                "not_found": "Lo siento, no encontré tipos de {material} en nuestra base de datos.",
                "error_fetch": "Lo siento, no pude obtener la información de los materiales en este momento.",
                "error_general": "Lo siento, ha ocurrido un error al consultar los tipos de material."
            },
            "en": {
                "no_material_identified": "Sorry, I couldn't identify which material you want to know the types of.",
                "available_types": "The types of {material} we work with are: {types}",
                "not_found": "Sorry, I couldn't find types of {material} in our database.",
                "error_fetch": "Sorry, I couldn't retrieve the materials information at this time.",
                "error_general": "Sorry, an error occurred while querying the material types."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            material_type = tracker.get_slot("material_type")
            
            if not material_type:
                dispatcher.utter_message(text=msgs["no_material_identified"])
                return []
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        materials_array = response_data.get("materials", [])
                        
                        # Traducir el material buscado al inglés (para la búsqueda en la BD)
                        material_english, _ = self.translate_material_to_english(material_type)
                        
                        # Obtener el nombre del material en el idioma del usuario (para el mensaje)
                        material_display = self.get_material_display_name(material_type, user_language)
                        
                        # Buscar todos los materiales que coincidan con el tipo
                        matching_materials = []
                        for material in materials_array:
                            material_field = material.get("material", "")
                            material_field_normalized = self.normalize_text(material_field)
                            
                            if material_field_normalized == material_english:
                                matching_materials.append(material.get("name"))
                        
                        if matching_materials:
                            material_list = ", ".join(matching_materials)
                            message = msgs["available_types"].format(
                                material=material_display,
                                types=material_list
                            )
                        else:
                            message = msgs["not_found"].format(material=material_display)
                    else:
                        message = msgs["error_fetch"]
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
        
        return []
    
    
class ActionCheckCompositionVariants(Action):
    def name(self) -> Text:
        return "action_check_composition_variants"
    
    def normalize_text(self, text: str) -> str:
        """Normaliza el texto eliminando tildes y convirtiendo a minúsculas."""
        import unicodedata
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        return text.lower().strip()
    
    def extract_base_material(self, material_name: str) -> str:
        """Extrae el material base (ej: 'oro' de 'oro rosa')."""
        normalized = self.normalize_text(material_name)
        base_materials = ['oro', 'plata', 'platino', 'acero', 'titanio', 'paladio']
        
        for base in base_materials:
            if base in normalized:
                return base
        return normalized
    
    def find_exact_match(self, materials_list: list, material_name: str) -> dict:
        """Busca una coincidencia exacta del material."""
        normalized_search = self.normalize_text(material_name)
        
        for material in materials_list:
            material_db_name = material.get("name", "")
            if self.normalize_text(material_db_name) == normalized_search:
                return material
        return None
    
    def get_material_variants(self, materials_list: list, base_material: str) -> list:
        """Obtiene todas las variantes de un material base."""
        normalized_base = self.normalize_text(base_material)
        variants = []
        
        for material in materials_list:
            material_name = material.get("name", "")
            normalized_name = self.normalize_text(material_name)
            
            if normalized_base in normalized_name:
                variants.append(material)
        
        return variants
    
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
                "no_material_identified": "Lo siento, no he podido identificar de qué material quieres conocer la composición.",
                "error_fetch": "Lo siento, no pude obtener la información de los materiales en este momento.",
                "not_found": "Lo siento, no encontré información sobre {material_name} en nuestra base de datos.",
                "multiple_variants": "Encontré varios tipos de {base_material}.",
                "error_general": "Lo siento, ha ocurrido un error al consultar los materiales."
            },
            "en": {
                "no_material_identified": "Sorry, I couldn't identify which material you want to know the composition of.",
                "error_fetch": "Sorry, I couldn't retrieve the materials information at this time.",
                "not_found": "Sorry, I couldn't find information about {material_name} in our database.",
                "multiple_variants": "I found several types of {base_material}.",
                "error_general": "Sorry, an error occurred while querying the materials."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            material_name = tracker.get_slot("material_name_composition")
            
            if not material_name:
                dispatcher.utter_message(text=msgs["no_material_identified"])
                return [SlotSet("needs_clarification", False)]
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(text=msgs["error_fetch"])
                        return [SlotSet("needs_clarification", False)]
                    
                    response_data = await response.json()
                    materials_array = response_data.get("materials", [])
                    
                    # PRIMERO: Intentar buscar coincidencia exacta
                    exact_match = self.find_exact_match(materials_array, material_name)
                    
                    if exact_match:
                        # Si hay coincidencia exacta, no necesita clarificación
                        return [SlotSet("needs_clarification", False)]
                    
                    # SEGUNDO: Si no hay coincidencia exacta, buscar por material base
                    base_material = self.extract_base_material(material_name)
                    variants = self.get_material_variants(materials_array, base_material)
                    
                    if not variants:
                        dispatcher.utter_message(
                            text=msgs["not_found"].format(material_name=material_name)
                        )
                        return [SlotSet("needs_clarification", False)]
                    
                    # Si solo hay una variante, no necesita clarificación
                    if len(variants) == 1:
                        # Actualizar el slot con el nombre exacto de la base de datos
                        exact_name = variants[0].get("name")
                        return [
                            SlotSet("material_name_composition", exact_name),
                            SlotSet("needs_clarification", False)
                        ]
                    
                    # Si hay múltiples variantes, mostrar botones
                    buttons = []
                    for variant in variants:
                        variant_name = variant.get("name")
                        buttons.append({
                            "title": variant_name,
                            "payload": f'/set_slot{{"material_name_composition": "{variant_name}"}}'
                        })
                    
                    dispatcher.utter_message(
                        text=msgs["multiple_variants"].format(base_material=base_material),
                        buttons=buttons
                    )
                    return [SlotSet("needs_clarification", True)]
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
            return [SlotSet("needs_clarification", False)]


class ActionShowComposition(Action):
    
    def name(self) -> Text:
        return "action_show_composition"
    
    def normalize_text(self, text: str) -> str:
        """Normaliza el texto eliminando tildes y convirtiendo a minúsculas."""
        import unicodedata
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        return text.lower().strip()
    
    def remove_plural(self, text: str) -> str:
        """Intenta convertir plurales a singular (reglas básicas del español)."""
        text = text.lower().strip()
        
        if text.endswith('es') and len(text) > 3:
            return text[:-2]
        elif text.endswith('s') and len(text) > 2:
            return text[:-1]
        
        return text
    
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
                "no_material_identified": "Lo siento, no he podido identificar de qué material quieres conocer la composición.",
                "error_fetch": "Lo siento, no pude obtener la información de los materiales en este momento.",
                "composition_single": "La composición de {material_name} es: {composition}",
                "composition_with_purity": "La composición de {material_name} ({purity_class}) es: {composition}",
                "no_composition_data": "Lo siento, no tengo información sobre la composición de {material_name} en este momento.",
                "compositions_multiple": "Las composiciones de {material_name} son:\n• {compositions}",
                "not_found": "Lo siento, no encontré información sobre {material_name} en nuestra base de datos.",
                "error_general": "Lo siento, ha ocurrido un error al consultar la composición del material."
            },
            "en": {
                "no_material_identified": "Sorry, I couldn't identify which material you want to know the composition of.",
                "error_fetch": "Sorry, I couldn't retrieve the materials information at this time.",
                "composition_single": "The composition of {material_name} is: {composition}",
                "composition_with_purity": "The composition of {material_name} ({purity_class}) is: {composition}",
                "no_composition_data": "Sorry, I don't have information about the composition of {material_name} at this time.",
                "compositions_multiple": "The compositions of {material_name} are:\n• {compositions}",
                "not_found": "Sorry, I couldn't find information about {material_name} in our database.",
                "error_general": "Sorry, an error occurred while querying the material composition."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            material_name = tracker.get_slot("material_name_composition")
            
            if not material_name:
                dispatcher.utter_message(text=msgs["no_material_identified"])
                return []
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(text=msgs["error_fetch"])
                        return []
                    
                    response_data = await response.json()
                    materials_array = response_data.get("materials", [])
                    
                    # Normalizar el nombre del material buscado
                    normalized_search = self.normalize_text(material_name)
                    normalized_search_singular = self.remove_plural(normalized_search)
                    
                    # Buscar el material de forma flexible
                    found_material = None
                    found_purity = None
                    
                    for material in materials_array:
                        material_db_name = material.get("name", "")
                        normalized_db_name = self.normalize_text(material_db_name)
                        normalized_db_name_singular = self.remove_plural(normalized_db_name)
                        
                        # Comparar el nombre del material
                        if (normalized_search == normalized_db_name or 
                            normalized_search_singular == normalized_db_name or
                            normalized_search == normalized_db_name_singular or
                            normalized_search_singular == normalized_db_name_singular):
                            found_material = material
                            # Si coincide con el nombre principal, tomar la primera pureza
                            if material.get("purities") and len(material.get("purities")) > 0:
                                found_purity = material.get("purities")[0]
                            break
                        
                        # Si no coincide con el nombre principal, buscar en las purezas
                        purities = material.get("purities", [])
                        for purity in purities:
                            purity_class = purity.get("class", "")
                            normalized_purity_class = self.normalize_text(purity_class)
                            
                            # Comparar con la clase de pureza (ej: "18K", "925")
                            if (normalized_search == normalized_purity_class or
                                normalized_search_singular == normalized_purity_class):
                                found_material = material
                                found_purity = purity
                                break
                        
                        if found_material:
                            break
                    
                    if found_material and found_purity:
                        material_name_response = found_material.get("name")
                        purity_class = found_purity.get("class", "")
                        composition = found_purity.get("composition")
                        
                        if composition:
                            if purity_class:
                                message = msgs["composition_with_purity"].format(
                                    material_name=material_name_response,
                                    purity_class=purity_class,
                                    composition=composition
                                )
                            else:
                                message = msgs["composition_single"].format(
                                    material_name=material_name_response,
                                    composition=composition
                                )
                        else:
                            message = msgs["no_composition_data"].format(material_name=material_name_response)
                    elif found_material:
                        # Si encontramos el material pero no una pureza específica
                        material_name_response = found_material.get("name")
                        purities = found_material.get("purities", [])
                        
                        if purities and len(purities) > 0:
                            # Mostrar todas las composiciones disponibles
                            compositions_list = []
                            for purity in purities:
                                purity_class = purity.get("class", "")
                                composition = purity.get("composition", "")
                                if composition:
                                    compositions_list.append(f"{purity_class}: {composition}")
                            
                            if compositions_list:
                                compositions_text = "\n• ".join(compositions_list)
                                message = msgs["compositions_multiple"].format(
                                    material_name=material_name_response,
                                    compositions=compositions_text
                                )
                            else:
                                message = msgs["no_composition_data"].format(material_name=material_name_response)
                        else:
                            message = msgs["no_composition_data"].format(material_name=material_name_response)
                    else:
                        message = msgs["not_found"].format(material_name=material_name)
                    
                    dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
        
        return []
    
    
class ActionCheckMeaningVariants(Action):
    
    def name(self) -> Text:
        return "action_check_meaning_variants"
    
    def normalize_text(self, text: str) -> str:
        """Normaliza el texto eliminando tildes y convirtiendo a minúsculas."""
        import unicodedata
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        return text.lower().strip()
    
    def extract_base_material(self, material_name: str) -> str:
        """Extrae el material base (ej: 'oro' de 'oro rosa')."""
        normalized = self.normalize_text(material_name)
        base_materials = ['oro', 'plata', 'platino', 'acero', 'titanio', 'paladio']
        
        for base in base_materials:
            if base in normalized:
                return base
        return normalized
    
    def find_exact_match(self, materials_list: list, material_name: str) -> dict:
        """Busca una coincidencia exacta del material."""
        normalized_search = self.normalize_text(material_name)
        
        for material in materials_list:
            material_db_name = material.get("name", "")
            if self.normalize_text(material_db_name) == normalized_search:
                return material
        return None
    
    def get_material_variants(self, materials_list: list, base_material: str) -> list:
        """Obtiene todas las variantes de un material base."""
        normalized_base = self.normalize_text(base_material)
        variants = []
        
        for material in materials_list:
            material_name = material.get("name", "")
            normalized_name = self.normalize_text(material_name)
            
            if normalized_base in normalized_name:
                variants.append(material)
        
        return variants
    
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
                "no_material_identified": "Lo siento, no he podido identificar de qué material quieres conocer el significado.",
                "error_fetch": "Lo siento, no pude obtener la información de los materiales en este momento.",
                "not_found": "Lo siento, no encontré información sobre {material_name} en nuestra base de datos.",
                "multiple_variants": "Encontré varios tipos de {base_material}.",
                "error_general": "Lo siento, ha ocurrido un error al consultar los materiales."
            },
            "en": {
                "no_material_identified": "Sorry, I couldn't identify which material you want to know the meaning of.",
                "error_fetch": "Sorry, I couldn't retrieve the materials information at this time.",
                "not_found": "Sorry, I couldn't find information about {material_name} in our database.",
                "multiple_variants": "I found several types of {base_material}.",
                "error_general": "Sorry, an error occurred while querying the materials."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            material_name = tracker.get_slot("material_name_meaning")
            
            if not material_name:
                dispatcher.utter_message(text=msgs["no_material_identified"])
                return [SlotSet("needs_clarification", False)]
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(text=msgs["error_fetch"])
                        return [SlotSet("needs_clarification", False)]
                    
                    response_data = await response.json()
                    materials_array = response_data.get("materials", [])
                    
                    # PRIMERO: Intentar buscar coincidencia exacta
                    exact_match = self.find_exact_match(materials_array, material_name)
                    
                    if exact_match:
                        # Si hay coincidencia exacta, no necesita clarificación
                        return [SlotSet("needs_clarification", False)]
                    
                    # SEGUNDO: Si no hay coincidencia exacta, buscar por material base
                    base_material = self.extract_base_material(material_name)
                    variants = self.get_material_variants(materials_array, base_material)
                    
                    if not variants:
                        dispatcher.utter_message(
                            text=msgs["not_found"].format(material_name=material_name)
                        )
                        return [SlotSet("needs_clarification", False)]
                    
                    # Si solo hay una variante, no necesita clarificación
                    if len(variants) == 1:
                        # Actualizar el slot con el nombre exacto de la base de datos
                        exact_name = variants[0].get("name")
                        return [
                            SlotSet("material_name_meaning", exact_name),
                            SlotSet("needs_clarification", False)
                        ]
                    
                    # Si hay múltiples variantes, mostrar botones
                    buttons = []
                    for variant in variants:
                        variant_name = variant.get("name")
                        buttons.append({
                            "title": variant_name,
                            "payload": f'/set_slot{{"material_name_meaning": "{variant_name}"}}'
                        })
                    
                    dispatcher.utter_message(
                        text=msgs["multiple_variants"].format(base_material=base_material),
                        buttons=buttons
                    )
                    return [SlotSet("needs_clarification", True)]
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
            return [SlotSet("needs_clarification", False)]


class ActionShowMeaning(Action):
    
    def name(self) -> Text:
        return "action_show_meaning"
    
    def normalize_text(self, text: str) -> str:
        """Normaliza el texto eliminando tildes y convirtiendo a minúsculas."""
        import unicodedata
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        return text.lower().strip()
    
    def remove_plural(self, text: str) -> str:
        """Intenta convertir plurales a singular (reglas básicas del español)."""
        text = text.lower().strip()
        
        if text.endswith('es') and len(text) > 3:
            return text[:-2]
        elif text.endswith('s') and len(text) > 2:
            return text[:-1]
        
        return text
    
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
                "no_material_identified": "Lo siento, no he podido identificar de qué material quieres conocer el significado.",
                "error_fetch": "Lo siento, no pude obtener la información de los materiales en este momento.",
                "meaning": "El significado de {material_name} es: {meaning}",
                "no_meaning_data": "Lo siento, no tengo información sobre el significado de {material_name} en este momento.",
                "not_found": "Lo siento, no encontré información sobre {material_name} en nuestra base de datos.",
                "error_general": "Lo siento, ha ocurrido un error al consultar el significado del material."
            },
            "en": {
                "no_material_identified": "Sorry, I couldn't identify which material you want to know the meaning of.",
                "error_fetch": "Sorry, I couldn't retrieve the materials information at this time.",
                "meaning": "The meaning of {material_name} is: {meaning}",
                "no_meaning_data": "Sorry, I don't have information about the meaning of {material_name} at this time.",
                "not_found": "Sorry, I couldn't find information about {material_name} in our database.",
                "error_general": "Sorry, an error occurred while querying the material meaning."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            material_name = tracker.get_slot("material_name_meaning")
            
            if not material_name:
                dispatcher.utter_message(text=msgs["no_material_identified"])
                return []
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(text=msgs["error_fetch"])
                        return []
                    
                    response_data = await response.json()
                    materials_array = response_data.get("materials", [])
                    
                    # Normalizar el nombre del material buscado
                    normalized_search = self.normalize_text(material_name)
                    normalized_search_singular = self.remove_plural(normalized_search)
                    
                    # Buscar el material de forma flexible
                    found_material = None
                    
                    for material in materials_array:
                        material_db_name = material.get("name", "")
                        normalized_db_name = self.normalize_text(material_db_name)
                        normalized_db_name_singular = self.remove_plural(normalized_db_name)
                        
                        # Comparar en singular y plural
                        if (normalized_search == normalized_db_name or 
                            normalized_search_singular == normalized_db_name or
                            normalized_search == normalized_db_name_singular or
                            normalized_search_singular == normalized_db_name_singular):
                            found_material = material
                            break
                    
                    if found_material:
                        material_name_response = found_material.get("name")
                        meaning = found_material.get("meaning")
                        
                        if meaning:
                            message = msgs["meaning"].format(
                                material_name=material_name_response,
                                meaning=meaning
                            )
                        else:
                            message = msgs["no_meaning_data"].format(material_name=material_name_response)
                    else:
                        message = msgs["not_found"].format(material_name=material_name)
                    
                    dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
        
        return []
    
# class ActionSignificadoMaterialBD(Action):
    
#     def name(self) -> Text:
#         return "action_significado_material_bd"
    
#     def normalize_text(self, text: str) -> str:
#         """
#         Normaliza el texto eliminando tildes y convirtiendo a minúsculas.
#         """
#         import unicodedata
#         # Eliminar tildes
#         text = ''.join(
#             c for c in unicodedata.normalize('NFD', text)
#             if unicodedata.category(c) != 'Mn'
#         )
#         # Convertir a minúsculas
#         return text.lower().strip()
    
#     def remove_plural(self, text: str) -> str:
#         """
#         Intenta convertir plurales a singular (reglas básicas del español).
#         """
#         text = text.lower().strip()
        
#         # Plurales terminados en -es
#         if text.endswith('es') and len(text) > 3:
#             return text[:-2]
#         # Plurales terminados en -s
#         elif text.endswith('s') and len(text) > 2:
#             return text[:-1]
        
#         return text
    
#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict[Text, Any]]:
        
#         try:
#             # Obtener el nombre del material desde el slot
#             material_name = tracker.get_slot("material_name")
            
#             if not material_name:
#                 dispatcher.utter_message(
#                     text="Lo siento, no he podido identificar de qué material quieres conocer el significado."
#                 )
#                 return []
            
#             api_url = os.getenv("API_URL")
#             endpoint = f"{api_url}/api/materials"
            
#             async with aiohttp.ClientSession() as session:
#                 async with session.get(endpoint) as response:
#                     if response.status == 200:
#                         response_data = await response.json()
#                         materials_array = response_data.get("materials", [])
                        
#                         # Normalizar el nombre del material buscado
#                         normalized_search = self.normalize_text(material_name)
#                         normalized_search_singular = self.remove_plural(normalized_search)
                        
#                         # Buscar el material de forma flexible
#                         found_material = None
                        
#                         for material in materials_array:
#                             material_db_name = material.get("name", "")
#                             normalized_db_name = self.normalize_text(material_db_name)
#                             normalized_db_name_singular = self.remove_plural(normalized_db_name)
                            
#                             # Comparar en singular y plural
#                             if (normalized_search == normalized_db_name or 
#                                 normalized_search_singular == normalized_db_name or
#                                 normalized_search == normalized_db_name_singular or
#                                 normalized_search_singular == normalized_db_name_singular):
#                                 found_material = material
#                                 break
                        
#                         if found_material:
#                             material_name_response = found_material.get("name")
#                             meaning = found_material.get("meaning")
                            
#                             if meaning:
#                                 message = f"El significado de {material_name_response} es: {meaning}"
#                             else:
#                                 message = f"Lo siento, no tengo información sobre el significado de {material_name_response} en este momento."
#                         else:
#                             message = f"Lo siento, no encontré información sobre {material_name} en nuestra base de datos."
#                     else:
#                         message = "Lo siento, no pude obtener la información de los materiales en este momento."
            
#             dispatcher.utter_message(text=message)
            
#         except Exception as e:
#             dispatcher.utter_message(
#                 text="Lo siento, ha ocurrido un error al consultar el significado del material."
#             )
#             print(f"Error al consultar la API: {str(e)}")
        
#         return []

class ActionMaterialesPorZodiacoBD(Action):
    
    def name(self) -> Text:
        return "action_materiales_por_zodiaco_bd"
    
    def normalize_text(self, text: str) -> str:
        """Normaliza el texto eliminando tildes y convirtiendo a minúsculas."""
        import unicodedata
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        return text.lower().strip()
    
    def remove_plural(self, text: str) -> str:
        """Intenta convertir plurales a singular (reglas básicas del español)."""
        text = text.lower().strip()
        
        if text.endswith('es') and len(text) > 3:
            return text[:-2]
        elif text.endswith('s') and len(text) > 2:
            return text[:-1]
        
        return text
    
    def translate_zodiac_to_english(self, zodiac: str) -> tuple:
        """
        Traduce nombres de signos zodiacales del español al inglés.
        Retorna una tupla (término_inglés, término_español_display)
        """
        translations = {
            "aries": ("aries", "Aries"),
            "tauro": ("taurus", "Tauro"),
            "geminis": ("gemini", "Géminis"),
            "cancer": ("cancer", "Cáncer"),
            "leo": ("leo", "Leo"),
            "virgo": ("virgo", "Virgo"),
            "libra": ("libra", "Libra"),
            "escorpio": ("scorpio", "Escorpio"),
            "escorpion": ("scorpio", "Escorpio"),
            "sagitario": ("sagittarius", "Sagitario"),
            "capricornio": ("capricorn", "Capricornio"),
            "acuario": ("aquarius", "Acuario"),
            "piscis": ("pisces", "Piscis")
        }
        
        normalized = self.normalize_text(zodiac)
        normalized_singular = self.remove_plural(normalized)
        
        if normalized in translations:
            return translations[normalized]
        elif normalized_singular in translations:
            return translations[normalized_singular]
        
        return (normalized_singular, normalized_singular.capitalize())
    
    def get_zodiac_display_name(self, zodiac: str, language: str) -> str:
        """Obtiene el nombre del signo zodiacal en el idioma apropiado."""
        zodiac_english, zodiac_spanish = self.translate_zodiac_to_english(zodiac)
        
        if language == "en":
            return zodiac_english.capitalize()
        return zodiac_spanish
    
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
                "no_zodiac_identified": "Lo siento, no he podido identificar para qué signo zodiacal quieres conocer los materiales recomendados.",
                "recommended_materials": "Para {zodiac_sign}, los materiales recomendados son: {materials}",
                "not_found": "Lo siento, no encontré materiales recomendados para {zodiac_sign} en nuestra base de datos.",
                "error_fetch": "Lo siento, no pude obtener la información de los materiales en este momento.",
                "error_general": "Lo siento, ha ocurrido un error al consultar los materiales por signo zodiacal."
            },
            "en": {
                "no_zodiac_identified": "Sorry, I couldn't identify which zodiac sign you want to know the recommended materials for.",
                "recommended_materials": "For {zodiac_sign}, the recommended materials are: {materials}",
                "not_found": "Sorry, I couldn't find recommended materials for {zodiac_sign} in our database.",
                "error_fetch": "Sorry, I couldn't retrieve the materials information at this time.",
                "error_general": "Sorry, an error occurred while querying materials by zodiac sign."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            zodiac_sign = tracker.get_slot("zodiac_sign")
            
            if not zodiac_sign:
                dispatcher.utter_message(text=msgs["no_zodiac_identified"])
                return []
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        materials_array = response_data.get("materials", [])
                        
                        # Traducir el signo zodiacal al inglés (para búsqueda en BD)
                        zodiac_english, _ = self.translate_zodiac_to_english(zodiac_sign)
                        
                        # Obtener el nombre del signo en el idioma del usuario (para el mensaje)
                        zodiac_display = self.get_zodiac_display_name(zodiac_sign, user_language)
                        
                        # Buscar todos los materiales que tengan este signo zodiacal
                        matching_materials = []
                        for material in materials_array:
                            zodiac_list = material.get("zodiac", [])
                            
                            for zodiac_item in zodiac_list:
                                zodiac_item_normalized = self.normalize_text(zodiac_item)
                                
                                if zodiac_item_normalized == zodiac_english:
                                    matching_materials.append(material.get("name"))
                                    break
                        
                        if matching_materials:
                            material_list = ", ".join(matching_materials)
                            message = msgs["recommended_materials"].format(
                                zodiac_sign=zodiac_display,
                                materials=material_list
                            )
                        else:
                            message = msgs["not_found"].format(zodiac_sign=zodiac_display)
                    else:
                        message = msgs["error_fetch"]
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
        
        return []


class ActionCheckPriceVariants(Action):
    
    def name(self) -> Text:
        return "action_check_price_variants"
    
    def normalize_text(self, text: str) -> str:
        """Normaliza el texto eliminando tildes y convirtiendo a minúsculas."""
        import unicodedata
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        return text.lower().strip()
    
    def extract_base_material(self, material_name: str) -> str:
        """Extrae el material base (ej: 'oro' de 'oro rosa')."""
        normalized = self.normalize_text(material_name)
        base_materials = ['oro', 'plata', 'platino', 'acero', 'titanio', 'paladio']
        
        for base in base_materials:
            if base in normalized:
                return base
        return normalized
    
    def find_exact_match(self, materials_list: list, material_name: str) -> dict:
        """Busca una coincidencia exacta del material."""
        normalized_search = self.normalize_text(material_name)
        
        for material in materials_list:
            material_db_name = material.get("name", "")
            if self.normalize_text(material_db_name) == normalized_search:
                return material
        return None
    
    def get_material_variants(self, materials_list: list, base_material: str) -> list:
        """Obtiene todas las variantes de un material base."""
        normalized_base = self.normalize_text(base_material)
        variants = []
        
        for material in materials_list:
            material_name = material.get("name", "")
            normalized_name = self.normalize_text(material_name)
            
            if normalized_base in normalized_name:
                variants.append(material)
        
        return variants
    
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
                "no_material_identified": "Lo siento, no he podido identificar de qué material quieres conocer el precio.",
                "error_fetch": "Lo siento, no pude obtener la información de los materiales en este momento.",
                "not_found": "Lo siento, no encontré información sobre {material_name} en nuestra base de datos.",
                "multiple_variants": "Encontré varios tipos de {base_material}.",
                "error_general": "Lo siento, ha ocurrido un error al consultar los materiales."
            },
            "en": {
                "no_material_identified": "Sorry, I couldn't identify which material you want to know the price of.",
                "error_fetch": "Sorry, I couldn't retrieve the materials information at this time.",
                "not_found": "Sorry, I couldn't find information about {material_name} in our database.",
                "multiple_variants": "I found several types of {base_material}.",
                "error_general": "Sorry, an error occurred while querying the materials."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            material_name = tracker.get_slot("material_name_price")
            
            if not material_name:
                dispatcher.utter_message(text=msgs["no_material_identified"])
                return [SlotSet("needs_clarification", False)]
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(text=msgs["error_fetch"])
                        return [SlotSet("needs_clarification", False)]
                    
                    response_data = await response.json()
                    materials_array = response_data.get("materials", [])
                    
                    # PRIMERO: Intentar buscar coincidencia exacta
                    exact_match = self.find_exact_match(materials_array, material_name)
                    
                    if exact_match:
                        return [SlotSet("needs_clarification", False)]
                    
                    # SEGUNDO: Si no hay coincidencia exacta, buscar por material base
                    base_material = self.extract_base_material(material_name)
                    variants = self.get_material_variants(materials_array, base_material)
                    
                    if not variants:
                        dispatcher.utter_message(
                            text=msgs["not_found"].format(material_name=material_name)
                        )
                        return [SlotSet("needs_clarification", False)]
                    
                    # Si solo hay una variante, no necesita clarificación
                    if len(variants) == 1:
                        exact_name = variants[0].get("name")
                        return [
                            SlotSet("material_name_price", exact_name),
                            SlotSet("needs_clarification", False)
                        ]
                    
                    # Si hay múltiples variantes, mostrar botones
                    buttons = []
                    for variant in variants:
                        variant_name = variant.get("name")
                        buttons.append({
                            "title": variant_name,
                            "payload": f'/set_slot{{"material_name_price": "{variant_name}"}}'
                        })
                    
                    dispatcher.utter_message(
                        text=msgs["multiple_variants"].format(base_material=base_material),
                        buttons=buttons
                    )
                    return [SlotSet("needs_clarification", True)]
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
            return [SlotSet("needs_clarification", False)]
        
class ActionShowPrice(Action):
    
    def name(self) -> Text:
        return "action_show_price"
    
    def normalize_text(self, text: str) -> str:
        """Normaliza el texto eliminando tildes y convirtiendo a minúsculas."""
        import unicodedata
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        return text.lower().strip()
    
    def remove_plural(self, text: str) -> str:
        """Intenta convertir plurales a singular (reglas básicas del español)."""
        text = text.lower().strip()
        
        if text.endswith('es') and len(text) > 3:
            return text[:-2]
        elif text.endswith('s') and len(text) > 2:
            return text[:-1]
        
        return text
    
    def extract_price_value(self, price_data) -> float:
        """Extrae el valor numérico del precio, manejando el formato de MongoDB."""
        if price_data is None:
            return None
        
        if isinstance(price_data, dict) and '$numberDecimal' in price_data:
            try:
                return float(price_data['$numberDecimal'])
            except (ValueError, TypeError):
                return None
        
        if isinstance(price_data, (int, float)):
            return float(price_data)
        
        if isinstance(price_data, str):
            try:
                return float(price_data)
            except ValueError:
                return None
        
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
                "no_material_identified": "Lo siento, no he podido identificar de qué material quieres conocer el precio.",
                "error_fetch": "Lo siento, no pude obtener la información de los materiales en este momento.",
                "price_single": "El precio de {material_name} es: {price}€/mm³",
                "price_with_purity": "El precio de {material_name} {purity} es: {price}€/mm³",
                "prices_multiple": "Los precios de {material_name} según pureza son:\n\n• {prices}",
                "no_price_data": "Lo siento, no tengo información sobre el precio de {material_name}.",
                "no_prices_data": "Lo siento, no tengo información sobre los precios de {material_name}.",
                "not_found": "Lo siento, no encontré información sobre {material_name} en nuestra base de datos.",
                "error_general": "Lo siento, ha ocurrido un error al consultar el precio del material."
            },
            "en": {
                "no_material_identified": "Sorry, I couldn't identify which material you want to know the price of.",
                "error_fetch": "Sorry, I couldn't retrieve the materials information at this time.",
                "price_single": "The price of {material_name} is: €{price}/mm³",
                "price_with_purity": "The price of {material_name} {purity} is: €{price}/mm³",
                "prices_multiple": "The prices of {material_name} by purity are:\n\n• {prices}",
                "no_price_data": "Sorry, I don't have price information for {material_name}.",
                "no_prices_data": "Sorry, I don't have price information for {material_name}.",
                "not_found": "Sorry, I couldn't find information about {material_name} in our database.",
                "error_general": "Sorry, an error occurred while querying the material price."
            }
        }
        
        # Seleccionar el conjunto de mensajes según el idioma
        msgs = messages.get(user_language, messages["es"])
        
        try:
            material_name = tracker.get_slot("material_name_price")
            
            if not material_name:
                dispatcher.utter_message(text=msgs["no_material_identified"])
                return []
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(text=msgs["error_fetch"])
                        return []
                    
                    response_data = await response.json()
                    materials_array = response_data.get("materials", [])
                    
                    # Normalizar el nombre del material buscado
                    normalized_search = self.normalize_text(material_name)
                    normalized_search_singular = self.remove_plural(normalized_search)
                    
                    # Buscar el material de forma flexible
                    found_material = None
                    
                    for material in materials_array:
                        material_db_name = material.get("name", "")
                        normalized_db_name = self.normalize_text(material_db_name)
                        normalized_db_name_singular = self.remove_plural(normalized_db_name)
                        
                        if (normalized_search == normalized_db_name or 
                            normalized_search_singular == normalized_db_name or
                            normalized_search == normalized_db_name_singular or
                            normalized_search_singular == normalized_db_name_singular):
                            found_material = material
                            break
                    
                    if found_material:
                        material_name_response = found_material.get("name")
                        purities = found_material.get("purities", [])
                        
                        if purities and len(purities) > 0:
                            # Si hay múltiples purezas, mostrar todas
                            if len(purities) > 1:
                                prices_list = []
                                for purity in purities:
                                    purity_name = purity.get("purity", "")
                                    price_data = purity.get("pricePermm3")
                                    price = self.extract_price_value(price_data)
                                    
                                    if price is not None:
                                        if user_language == "en":
                                            prices_list.append(f"{purity_name}: €{price}/mm³")
                                        else:
                                            prices_list.append(f"{purity_name}: {price}€/mm³")
                                
                                if prices_list:
                                    prices_text = "\n\n• ".join(prices_list)
                                    message = msgs["prices_multiple"].format(
                                        material_name=material_name_response,
                                        prices=prices_text
                                    )
                                else:
                                    message = msgs["no_prices_data"].format(material_name=material_name_response)
                            else:
                                # Si solo hay una pureza, mostrar ese precio
                                purity = purities[0]
                                purity_name = purity.get("purity", "")
                                price_data = purity.get("pricePermm3")
                                price = self.extract_price_value(price_data)
                                
                                if price is not None:
                                    if purity_name:
                                        message = msgs["price_with_purity"].format(
                                            material_name=material_name_response,
                                            purity=purity_name,
                                            price=price
                                        )
                                    else:
                                        message = msgs["price_single"].format(
                                            material_name=material_name_response,
                                            price=price
                                        )
                                else:
                                    message = msgs["no_price_data"].format(material_name=material_name_response)
                        else:
                            message = msgs["no_price_data"].format(material_name=material_name_response)
                    else:
                        message = msgs["not_found"].format(material_name=material_name)
                    
                    dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(text=msgs["error_general"])
            print(f"Error al consultar la API: {str(e)}")
        
        return []