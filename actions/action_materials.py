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
        
        try:
            material_name = tracker.get_slot("material_name")
            
            if not material_name:
                dispatcher.utter_message(
                    text="Lo siento, no he podido identificar de qué material quieres saber sobre alergias."
                )
                return [SlotSet("needs_clarification", False)]
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="Lo siento, no pude obtener la información de los materiales en este momento."
                        )
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
                            text=f"Lo siento, no encontré información sobre {material_name} en nuestra base de datos."
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
                        text=f"Encontré varios tipos de {base_material}.",
                        buttons=buttons
                    )
                    return [SlotSet("needs_clarification", True)]
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar los materiales."
            )
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
    
    def translate_allergen(self, allergen: str) -> str:
        """Traduce los alérgenos del inglés al español."""
        translations = {
            'nickel': 'níquel',
            'zinc': 'zinc',
            'copper': 'cobre'
        }
        # Normalizar y buscar traducción
        allergen_lower = allergen.lower().strip()
        return translations.get(allergen_lower, allergen)
    
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
        
        try:
            material_name = tracker.get_slot("material_name")
            
            if not material_name:
                dispatcher.utter_message(
                    text="Lo siento, no he podido identificar de qué material quieres saber sobre alergias."
                )
                return []
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="Lo siento, no pude obtener la información de los materiales en este momento."
                        )
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
                            text=f"Lo siento, no encontré información sobre {material_name} en nuestra base de datos."
                        )
                        return []
                    
                    # Mostrar información de alergias
                    material_name_response = material_found.get("name")
                    has_allergies, allergens = self.get_unique_allergens(material_found)
                    
                    if has_allergies:
                        # Traducir cada alérgeno al español
                        allergens_translated = [self.translate_allergen(allergen) for allergen in allergens]
                        allergens_list = ", ".join(allergens_translated)
                        message = (
                            f"Sí, {material_name_response} puede causar alergias.\n"
                            f"Contiene los siguientes alérgenos: {allergens_list}"
                        )
                    else:
                        message = f"El {material_name_response} no causa alergias según nuestra información. Es hipoalergénico."
                    
                    dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar las alergias del material."
            )
            print(f"Error al consultar la API: {str(e)}")
        
        return []
    
 
class ActionTiposMaterialBD(Action):
    
    def name(self) -> Text:
        return "action_tipos_material_bd"
    
    def normalize_text(self, text: str) -> str:
        """
        Normaliza el texto eliminando tildes y convirtiendo a minúsculas.
        """
        import unicodedata
        # Eliminar tildes
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        # Convertir a minúsculas
        return text.lower().strip()
    
    def remove_plural(self, text: str) -> str:
        """
        Intenta convertir plurales a singular (reglas básicas del español).
        """
        text = text.lower().strip()
        
        # Plurales terminados en -es
        if text.endswith('es') and len(text) > 3:
            return text[:-2]
        # Plurales terminados en -s
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
        
        # Buscar traducción
        if normalized in translations:
            return translations[normalized]
        elif normalized_singular in translations:
            return translations[normalized_singular]
        
        # Si no hay traducción, devolver el original normalizado para ambos
        return (normalized_singular, normalized_singular)
    
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            # Obtener el tipo de material desde el slot
            material_type = tracker.get_slot("material_type")
            
            if not material_type:
                dispatcher.utter_message(
                    text="Lo siento, no he podido identificar de qué material quieres conocer los tipos."
                )
                return []
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        materials_array = response_data.get("materials", [])
                        
                        # Traducir el material buscado al inglés y obtener el término en español
                        material_english, material_spanish = self.translate_material_to_english(material_type)
                        
                        # Buscar todos los materiales que coincidan con el tipo
                        matching_materials = []
                        for material in materials_array:
                            material_field = material.get("material", "")
                            material_field_normalized = self.normalize_text(material_field)
                            
                            if material_field_normalized == material_english:
                                matching_materials.append(material.get("name"))
                        
                        if matching_materials:
                            material_list = ", ".join(matching_materials)
                            # Usar el término en español para el mensaje
                            message = f"Los tipos de {material_spanish} que trabajamos son: {material_list}"
                        else:
                            message = f"Lo siento, no encontré tipos de {material_spanish} en nuestra base de datos."
                    else:
                        message = "Lo siento, no pude obtener la información de los materiales en este momento."
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar los tipos de material."
            )
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
        
        try:
            material_name = tracker.get_slot("material_name_composition")
            
            if not material_name:
                dispatcher.utter_message(
                    text="Lo siento, no he podido identificar de qué material quieres conocer la composición."
                )
                return [SlotSet("needs_clarification", False)]
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="Lo siento, no pude obtener la información de los materiales en este momento."
                        )
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
                            text=f"Lo siento, no encontré información sobre {material_name} en nuestra base de datos."
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
                        text=f"Encontré varios tipos de {base_material}.",
                        buttons=buttons
                    )
                    return [SlotSet("needs_clarification", True)]
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar los materiales."
            )
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
        
        # Plurales terminados en -es
        if text.endswith('es') and len(text) > 3:
            return text[:-2]
        # Plurales terminados en -s
        elif text.endswith('s') and len(text) > 2:
            return text[:-1]
        
        return text
    
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            material_name = tracker.get_slot("material_name_composition")
            
            if not material_name:
                dispatcher.utter_message(
                    text="Lo siento, no he podido identificar de qué material quieres conocer la composición."
                )
                return []
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="Lo siento, no pude obtener la información de los materiales en este momento."
                        )
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
                                message = f"La composición de {material_name_response} es: {composition}"
                            else:
                                message = f"La composición de {material_name_response} es: {composition}"
                        else:
                            message = f"Lo siento, no tengo información sobre la composición de {material_name_response} en este momento."
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
                                message = f"Las composiciones de {material_name_response} son:\n• {compositions_text}"
                            else:
                                message = f"Lo siento, no tengo información sobre la composición de {material_name_response}."
                        else:
                            message = f"Lo siento, no tengo información sobre la composición de {material_name_response}."
                    else:
                        message = f"Lo siento, no encontré información sobre {material_name} en nuestra base de datos."
                    
                    dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar la composición del material."
            )
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
        
        try:
            material_name = tracker.get_slot("material_name_meaning")
            
            if not material_name:
                dispatcher.utter_message(
                    text="Lo siento, no he podido identificar de qué material quieres conocer el significado."
                )
                return [SlotSet("needs_clarification", False)]
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="Lo siento, no pude obtener la información de los materiales en este momento."
                        )
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
                            text=f"Lo siento, no encontré información sobre {material_name} en nuestra base de datos."
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
                        text=f"Encontré varios tipos de {base_material}.",
                        buttons=buttons
                    )
                    return [SlotSet("needs_clarification", True)]
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar los materiales."
            )
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
        
        # Plurales terminados en -es
        if text.endswith('es') and len(text) > 3:
            return text[:-2]
        # Plurales terminados en -s
        elif text.endswith('s') and len(text) > 2:
            return text[:-1]
        
        return text
    
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            material_name = tracker.get_slot("material_name_meaning")
            
            if not material_name:
                dispatcher.utter_message(
                    text="Lo siento, no he podido identificar de qué material quieres conocer el significado."
                )
                return []
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="Lo siento, no pude obtener la información de los materiales en este momento."
                        )
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
                            message = f"El significado de {material_name_response} es: {meaning}"
                        else:
                            message = f"Lo siento, no tengo información sobre el significado de {material_name_response} en este momento."
                    else:
                        message = f"Lo siento, no encontré información sobre {material_name} en nuestra base de datos."
                    
                    dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar el significado del material."
            )
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
        """
        Normaliza el texto eliminando tildes y convirtiendo a minúsculas.
        """
        import unicodedata
        # Eliminar tildes
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        # Convertir a minúsculas
        return text.lower().strip()
    
    def remove_plural(self, text: str) -> str:
        """
        Intenta convertir plurales a singular (reglas básicas del español).
        """
        text = text.lower().strip()
        
        # Plurales terminados en -es
        if text.endswith('es') and len(text) > 3:
            return text[:-2]
        # Plurales terminados en -s
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
        
        # Buscar traducción
        if normalized in translations:
            return translations[normalized]
        elif normalized_singular in translations:
            return translations[normalized_singular]
        
        # Si no hay traducción, devolver el original normalizado para ambos
        return (normalized_singular, normalized_singular.capitalize())
    
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        try:
            # Obtener el signo zodiacal desde el slot
            zodiac_sign = tracker.get_slot("zodiac_sign")
            
            if not zodiac_sign:
                dispatcher.utter_message(
                    text="Lo siento, no he podido identificar para qué signo zodiacal quieres conocer los materiales recomendados."
                )
                return []
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        materials_array = response_data.get("materials", [])
                        
                        # Traducir el signo zodiacal al inglés y obtener el término en español
                        zodiac_english, zodiac_spanish = self.translate_zodiac_to_english(zodiac_sign)
                        
                        # Buscar todos los materiales que tengan este signo zodiacal
                        matching_materials = []
                        for material in materials_array:
                            zodiac_list = material.get("zodiac", [])
                            
                            # Normalizar cada signo en la lista y comparar
                            for zodiac_item in zodiac_list:
                                zodiac_item_normalized = self.normalize_text(zodiac_item)
                                
                                if zodiac_item_normalized == zodiac_english:
                                    matching_materials.append(material.get("name"))
                                    break  # Evitar duplicados si el signo aparece múltiples veces
                        
                        if matching_materials:
                            material_list = ", ".join(matching_materials)
                            message = f"Para {zodiac_spanish}, los materiales recomendados son: {material_list}"
                        else:
                            message = f"Lo siento, no encontré materiales recomendados para {zodiac_spanish} en nuestra base de datos."
                    else:
                        message = "Lo siento, no pude obtener la información de los materiales en este momento."
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar los materiales por signo zodiacal."
            )
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
        
        try:
            material_name = tracker.get_slot("material_name_price")
            
            if not material_name:
                dispatcher.utter_message(
                    text="Lo siento, no he podido identificar de qué material quieres conocer el precio."
                )
                return [SlotSet("needs_clarification", False)]
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="Lo siento, no pude obtener la información de los materiales en este momento."
                        )
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
                            text=f"Lo siento, no encontré información sobre {material_name} en nuestra base de datos."
                        )
                        return [SlotSet("needs_clarification", False)]
                    
                    # Si solo hay una variante, no necesita clarificación
                    if len(variants) == 1:
                        # Actualizar el slot con el nombre exacto de la base de datos
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
                        text=f"Encontré varios tipos de {base_material}.",
                        buttons=buttons
                    )
                    return [SlotSet("needs_clarification", True)]
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar los materiales."
            )
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
        
        # Plurales terminados en -es
        if text.endswith('es') and len(text) > 3:
            return text[:-2]
        # Plurales terminados en -s
        elif text.endswith('s') and len(text) > 2:
            return text[:-1]
        
        return text
    
    def extract_price_value(self, price_data) -> float:
        """Extrae el valor numérico del precio, manejando el formato de MongoDB."""
        if price_data is None:
            return None
        
        # Si es un diccionario con $numberDecimal
        if isinstance(price_data, dict) and '$numberDecimal' in price_data:
            try:
                return float(price_data['$numberDecimal'])
            except (ValueError, TypeError):
                return None
        
        # Si ya es un número
        if isinstance(price_data, (int, float)):
            return float(price_data)
        
        # Si es un string, intentar convertirlo
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
        
        try:
            material_name = tracker.get_slot("material_name_price")
            
            if not material_name:
                dispatcher.utter_message(
                    text="Lo siento, no he podido identificar de qué material quieres conocer el precio."
                )
                return []
            
            api_url = os.getenv("API_URL")
            endpoint = f"{api_url}/api/materials"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="Lo siento, no pude obtener la información de los materiales en este momento."
                        )
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
                                        prices_list.append(f"{purity_name}: {price}€/mm³")
                                
                                if prices_list:
                                    prices_text = "\n\n• ".join(prices_list)
                                    message = f"Los precios de {material_name_response} según pureza son:\n\n• {prices_text}"
                                else:
                                    message = f"Lo siento, no tengo información sobre los precios de {material_name_response}."
                            else:
                                # Si solo hay una pureza, mostrar ese precio
                                purity = purities[0]
                                purity_name = purity.get("purity", "")
                                price_data = purity.get("pricePermm3")
                                price = self.extract_price_value(price_data)
                                
                                if price is not None:
                                    if purity_name:
                                        message = f"El precio de {material_name_response} {purity_name} es: {price}€/mm³"
                                    else:
                                        message = f"El precio de {material_name_response} es: {price}€/mm³"
                                else:
                                    message = f"Lo siento, no tengo información sobre el precio de {material_name_response}."
                        else:
                            message = f"Lo siento, no tengo información sobre el precio de {material_name_response}."
                    else:
                        message = f"Lo siento, no encontré información sobre {material_name} en nuestra base de datos."
                    
                    dispatcher.utter_message(text=message)
            
        except Exception as e:
            dispatcher.utter_message(
                text="Lo siento, ha ocurrido un error al consultar el precio del material."
            )
            print(f"Error al consultar la API: {str(e)}")
        
        return []