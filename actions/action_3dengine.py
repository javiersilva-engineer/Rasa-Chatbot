import os
from typing import Text
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import aiohttp
from dotenv import load_dotenv

load_dotenv()


# =========================
# MOSTRAR ANILLO
# =========================
class ActionShowRing(Action):
    def name(self) -> Text:
        return "action_show_ring"

    async def run(self, dispatcher, tracker, domain):
        ring_type = tracker.get_slot('ring_type')

        if not ring_type:
            dispatcher.utter_message(
                text="No pude identificar qué anillo quieres ver. ¿Podrías especificarlo?"
            )
            return []

        api_url = os.getenv("API_URL", "https://louv.ovh")

        try:
            async with aiohttp.ClientSession() as session:
                # ← Obtener todas las estructuras base
                endpoint = f"{api_url}/api/baseStructures"
                print(f"[DEBUG] GET {endpoint}")

                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="No pude cargar los anillos disponibles."
                        )
                        return []

                    data = await response.json()
                    base_structures = data.get('baseStructures', [])

                    # ← Normalizar y buscar coincidencia
                    normalized_ring_type = ring_type.lower().strip()
                    
                    matching_ring = None
                    for structure in base_structures:
                        structure_name = structure.get('name', '').lower().strip()
                        if structure_name == normalized_ring_type:
                            matching_ring = structure
                            break

                    if not matching_ring:
                        dispatcher.utter_message(
                            text=f"No encontré un anillo llamado '{ring_type}'."
                        )
                        return []

                    ring_id = matching_ring.get('_id')
                    print(f"[DEBUG] Ring ID encontrado: {ring_id}")

                    dispatcher.utter_message(
                        text=f"Mostrando el anillo {ring_type}",
                        custom={
                            "type": "show_ring",
                            "ring_type": ring_type,
                            "ring_id": ring_id
                        }
                    )

                    return [SlotSet("ring_id", ring_id)]

        except Exception as e:
            print(f"[ERROR] {e}")
            dispatcher.utter_message(
                text="Error al buscar el anillo."
            )
            return []





# =========================
# MOSTRAR PERFILES
# =========================
class ActionAskProfileId(Action):
    def name(self) -> Text:
        return "action_ask_profile_id"

    async def run(self, dispatcher, tracker, domain):

        api_url = os.getenv("API_URL", "https://louv.ovh")
        current_ring_id = tracker.get_slot('ring_id')

        print(f"[DEBUG] Ring ID: {current_ring_id}")

        if not current_ring_id:
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            current_ring_id = metadata.get('ring_id')

        print(f"[DEBUG] Ring ID: {current_ring_id}")
        
        if not current_ring_id:
            dispatcher.utter_message(
                text="No tengo información del anillo actual."
            )
            return []

        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{api_url}/api/baseStructures/{current_ring_id}"
                print(f"[DEBUG] GET {endpoint}")

                async with session.get(endpoint) as response:
                    print(f"[DEBUG] Status: {response.status}")

                    if response.status < 200 or response.status >= 300:
                        text = await response.text()
                        print(f"[DEBUG] Response text: {text}")
                        dispatcher.utter_message(
                            text="Lo siento, no pude cargar los perfiles disponibles."
                        )
                        return []

                    ring_data = await response.json()
                    print(f"[DEBUG] JSON recibido OK")

            base_structure = ring_data.get("baseStructure", {})
            profiles = base_structure.get("profiles", [])

            print(f"[DEBUG] Nº perfiles: {len(profiles)}")

            if not profiles:
                dispatcher.utter_message(
                    text="Este anillo no tiene perfiles disponibles."
                )
                return []

            buttons = []

            async with aiohttp.ClientSession() as session:
                for profile_data in profiles:
                    profile_obj = profile_data.get('profile', {})
                    print(f"[DEBUG] profile_obj: {profile_obj}")

                    if isinstance(profile_obj, str):
                        profile_id = profile_obj
                        profile_name = "Perfil"

                        profile_endpoint = f"{api_url}/api/profiles/{profile_id}"
                        print(f"[DEBUG] GET profile {profile_endpoint}")

                        async with session.get(profile_endpoint) as res:
                            print(f"[DEBUG] profile status: {res.status}")

                            if res.status == 200:
                                data = await res.json()
                                profile_name = data.get('name', 'Sin nombre')
                    else:
                        profile_id = profile_obj.get('_id', '')
                        profile_name = profile_obj.get('name', 'Sin nombre')

                    print(f"[DEBUG] Añadiendo botón: {profile_name} ({profile_id})")

                    # 👇 CAMBIO IMPORTANTE: usar SetSlot en lugar de intent
                    buttons.append({
                        "title": profile_name,
                        "payload": f'SetSlot("profile_id", "{profile_id}")'
                    })

            dispatcher.utter_message(
                text="Selecciona el perfil que deseas aplicar:",
                buttons=buttons
            )

        except aiohttp.ClientError as e:
            print(f"[ERROR] Conexión: {e}")
            dispatcher.utter_message(
                text="Error de conexión con el servidor."
            )

        except Exception as e:
            print(f"[ERROR] General: {e}")
            dispatcher.utter_message(
                text="Error interno en el servidor."
            )

        return [SlotSet("ring_id", current_ring_id)]


# =========================
# CAMBIAR PERFIL
# =========================
class ActionChangeProfile(Action):
    def name(self) -> Text:
        return "action_change_profile"

    async def run(self, dispatcher, tracker, domain):

        profile_id = tracker.get_slot('profile_id')

        print(f"[DEBUG] profile_id recibido en action_change_profile: {profile_id}")

        if not profile_id:
            dispatcher.utter_message(
                text="No pude identificar el perfil seleccionado."
            )
            return []

        dispatcher.utter_message(
            text="Perfil cambiado correctamente.",
            custom={
                "type": "change_profile",
                "profile_id": profile_id
            }
        )

        # Limpiar el slot después de usarlo
        return [SlotSet("profile_id", None)]





# =========================
# MOSTRAR VARIANTES
# =========================
class ActionAskVarianteId(Action):
    def name(self) -> Text:
        return "action_ask_variante_id"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")
        current_ring_id = tracker.get_slot('ring_id')

        print(f"[DEBUG] Ring ID para variantes: {current_ring_id}")

        if not current_ring_id:
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            current_ring_id = metadata.get('ring_id')

        print(f"[DEBUG] Ring ID final: {current_ring_id}")
        
        if not current_ring_id:
            dispatcher.utter_message(
                text="No tengo información del anillo actual."
            )
            return []

        try:
            async with aiohttp.ClientSession() as session:
                # Obtener la estructura base del anillo
                endpoint = f"{api_url}/api/baseStructures/{current_ring_id}"
                print(f"[DEBUG] GET {endpoint}")

                async with session.get(endpoint) as response:
                    print(f"[DEBUG] Status: {response.status}")

                    if response.status < 200 or response.status >= 300:
                        text = await response.text()
                        print(f"[DEBUG] Response text: {text}")
                        dispatcher.utter_message(
                            text="Lo siento, no pude cargar las variantes disponibles."
                        )
                        return []

                    ring_data = await response.json()
                    print(f"[DEBUG] JSON recibido OK")

            base_structure = ring_data.get("baseStructure", {})
            
            # Obtener el perfil actual del tracker
            current_profile_id = tracker.get_slot('profile_id')
            
            # Si no hay profile_id en el slot, intentar obtenerlo de la estructura
            if not current_profile_id and base_structure.get("profiles"):
                # Usar el primer perfil por defecto
                first_profile = base_structure["profiles"][0]
                profile_obj = first_profile.get('profile', {})
                if isinstance(profile_obj, str):
                    current_profile_id = profile_obj
                else:
                    current_profile_id = profile_obj.get('_id', '')

            print(f"[DEBUG] Profile ID actual: {current_profile_id}")

            # Buscar el perfil específico
            target_profile = None
            for profile_data in base_structure.get("profiles", []):
                profile_obj = profile_data.get('profile', {})
                profile_id = profile_obj if isinstance(profile_obj, str) else profile_obj.get('_id', '')
                
                if profile_id == current_profile_id:
                    target_profile = profile_data
                    break

            if not target_profile:
                dispatcher.utter_message(
                    text="No pude encontrar el perfil actual del anillo."
                )
                return []

            variants = target_profile.get("variants", [])
            print(f"[DEBUG] Nº variantes: {len(variants)}")

            if not variants:
                dispatcher.utter_message(
                    text="Este perfil no tiene variantes disponibles."
                )
                return []

            buttons = []
            for variant in variants:
                variant_id = variant.get('_id', '')
                variant_name = variant.get('name', 'Sin nombre')

                print(f"[DEBUG] Añadiendo botón variante: {variant_name} ({variant_id})")

                buttons.append({
                    "title": variant_name,
                    "payload": f'SetSlot("variante_id", "{variant_id}")'
                })

            dispatcher.utter_message(
                text="Selecciona la variante que deseas aplicar:",
                buttons=buttons
            )

        except aiohttp.ClientError as e:
            print(f"[ERROR] Conexión: {e}")
            dispatcher.utter_message(
                text="Error de conexión con el servidor."
            )

        except Exception as e:
            print(f"[ERROR] General: {e}")
            dispatcher.utter_message(
                text="Error interno en el servidor."
            )

        return [SlotSet("ring_id", current_ring_id)]


# =========================
# CAMBIAR VARIANTE
# =========================
class ActionChangeVariante(Action):
    def name(self) -> Text:
        return "action_change_variante"

    async def run(self, dispatcher, tracker, domain):
        variante_id = tracker.get_slot('variante_id')

        print(f"[DEBUG] variante_id recibido en action_change_variante: {variante_id}")

        if not variante_id:
            dispatcher.utter_message(
                text="No pude identificar la variante seleccionada."
            )
            return []

        dispatcher.utter_message(
            text="Variante cambiada correctamente.",
            custom={
                "type": "change_variante",
                "variante_id": variante_id
            }
        )

        # Limpiar el slot después de usarlo
        return [SlotSet("variante_id", None)]





# =========================
# MOSTRAR MATERIALES
# =========================
class ActionAskMaterialId(Action):
    def name(self) -> Text:
        return "action_ask_material_id"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")

        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{api_url}/api/materials"
                print(f"[DEBUG] GET {endpoint}")

                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="No pude cargar los materiales disponibles."
                        )
                        return []

                    data = await response.json()
                    materials = data.get('materials', [])

                    print(f"[DEBUG] Nº materiales: {len(materials)}")

                    if not materials:
                        dispatcher.utter_message(
                            text="No hay materiales disponibles."
                        )
                        return []

                    buttons = []
                    for material in materials:
                        material_id = material.get('_id', '')
                        material_name = material.get('name', 'Sin nombre')

                        print(f"[DEBUG] Añadiendo botón material: {material_name} ({material_id})")

                        buttons.append({
                            "title": material_name,
                            "payload": f'SetSlot("material_id", "{material_id}")'
                        })

                    dispatcher.utter_message(
                        text="Selecciona el material que deseas aplicar:",
                        buttons=buttons
                    )

        except aiohttp.ClientError as e:
            print(f"[ERROR] Conexión: {e}")
            dispatcher.utter_message(
                text="Error de conexión con el servidor."
            )

        except Exception as e:
            print(f"[ERROR] General: {e}")
            dispatcher.utter_message(
                text="Error interno en el servidor."
            )

        return []


# =========================
# CAMBIAR MATERIAL
# =========================
class ActionChangeMaterial(Action):
    def name(self) -> Text:
        return "action_change_material"

    async def run(self, dispatcher, tracker, domain):
        material_id = tracker.get_slot('material_id')

        print(f"[DEBUG] material_id recibido en action_change_material: {material_id}")

        if not material_id:
            dispatcher.utter_message(
                text="No pude identificar el material seleccionado."
            )
            return []

        # Guardar el material_id para usarlo al mostrar purezas
        events = [SlotSet("current_material_id", material_id)]

        dispatcher.utter_message(
            text="Material seleccionado correctamente.",
            custom={
                "type": "change_material",
                "material_id": material_id
            }
        )

        # Limpiar el slot de material_id después de usarlo
        events.append(SlotSet("material_id", None))

        return events


# =========================
# MOSTRAR PUREZAS (VERSIÓN CORREGIDA)
# =========================
class ActionAskPurezaId(Action):
    def name(self) -> Text:
        return "action_ask_pureza_id"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")
        
        # Intentar obtener el material_id del slot guardado
        material_id = tracker.get_slot('current_material_id')
        
        # Si no está en el slot, intentar obtenerlo de los metadatos
        if not material_id:
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            material_id = metadata.get('material_id')
        
        print(f"[DEBUG] Material ID para purezas: {material_id}")

        if not material_id:
            dispatcher.utter_message(
                text="Primero debes seleccionar un material."
            )
            return []

        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{api_url}/api/materials/{material_id}"
                print(f"[DEBUG] GET {endpoint}")

                async with session.get(endpoint) as response:
                    print(f"[DEBUG] Status: {response.status}")

                    if response.status < 200 or response.status >= 300:
                        text = await response.text()
                        print(f"[DEBUG] Response text: {text}")
                        dispatcher.utter_message(
                            text="Lo siento, no pude cargar las purezas disponibles."
                        )
                        return []

                    material_data = await response.json()
                    print(f"[DEBUG] JSON completo recibido: {material_data}")

            # Buscar purezas en diferentes niveles de la estructura
            purities = material_data.get("purities", [])
            if not purities:
                material = material_data.get("material", {})
                purities = material.get("purities", [])

            print(f"[DEBUG] Purezas encontradas: {purities}")
            print(f"[DEBUG] Nº purezas: {len(purities)}")

            if not purities:
                dispatcher.utter_message(
                    text="Este material no tiene purezas disponibles."
                )
                return []

            buttons = []
            for purity in purities:
                if isinstance(purity, dict):
                    purity_id = purity.get('_id', '')
                    purity_name = purity.get('name', purity.get('purity', 'Sin nombre'))
                else:
                    purity_id = purity
                    purity_name = purity_id

                print(f"[DEBUG] Añadiendo botón pureza: {purity_name} ({purity_id})")

                buttons.append({
                    "title": purity_name,
                    "payload": f'SetSlot("pureza_id", "{purity_id}")'
                })

            dispatcher.utter_message(
                text="Selecciona la pureza que deseas aplicar:",
                buttons=buttons
            )

            # Guardar el material_id para uso posterior
            return [SlotSet("current_material_id", material_id)]

        except aiohttp.ClientError as e:
            print(f"[ERROR] Conexión: {e}")
            dispatcher.utter_message(
                text="Error de conexión con el servidor."
            )

        except Exception as e:
            print(f"[ERROR] General: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            dispatcher.utter_message(
                text="Error interno en el servidor."
            )

        return []


# =========================
# CAMBIAR PUREZA
# =========================
class ActionChangePurezaMaterial(Action):
    def name(self) -> Text:
        return "action_change_pureza_material"

    async def run(self, dispatcher, tracker, domain):
        pureza_id = tracker.get_slot('pureza_id')
        material_id = tracker.get_slot('current_material_id')

        print(f"[DEBUG] pureza_id recibido: {pureza_id}")
        print(f"[DEBUG] material_id actual: {material_id}")

        if not pureza_id:
            dispatcher.utter_message(
                text="No pude identificar la pureza seleccionada."
            )
            return []

        dispatcher.utter_message(
            text="Material y pureza aplicados correctamente.",
            custom={
                "type": "change_pureza",
                "material_id": material_id,
                "pureza_id": pureza_id
            }
        )

        # Limpiar los slots después de usarlos
        return [
            SlotSet("pureza_id", None),
            SlotSet("current_material_id", None)
        ]