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
                    
                    # ✅ AÑADIR: Imprimir el JSON completo
                    import json
                    print(f"[DEBUG] JSON COMPLETO:\n{json.dumps(ring_data, indent=2)}")

            base_structure = ring_data.get("baseStructure", {})
            print(f"[DEBUG] Base structure name: {base_structure.get('name', 'N/A')}")
            
            # Obtener el perfil actual del tracker
            current_profile_id = tracker.get_slot('profile_id')
            
            if not current_profile_id:
                latest_message = tracker.latest_message
                metadata = latest_message.get('metadata', {})
                current_profile_id = metadata.get('profile_id')
            
            if not current_profile_id and base_structure.get("profiles"):
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
                
                print(f"[DEBUG] Comparando perfil: {profile_id} con {current_profile_id}")
                
                if profile_id == current_profile_id:
                    target_profile = profile_data
                    print(f"[DEBUG] ✅ Perfil encontrado!")
                    break

            if not target_profile:
                print(f"[ERROR] No se encontró perfil con ID: {current_profile_id}")
                print(f"[DEBUG] Perfiles disponibles: {[p.get('profile') for p in base_structure.get('profiles', [])]}")
                dispatcher.utter_message(
                    text="No pude encontrar el perfil actual del anillo."
                )
                return []

            # ✅ AÑADIR: Imprimir el perfil completo
            import json
            print(f"[DEBUG] PERFIL COMPLETO:\n{json.dumps(target_profile, indent=2, default=str)}")

            variants = target_profile.get("variants", [])
            print(f"[DEBUG] Nº variantes encontradas: {len(variants)}")
            
            # ✅ AÑADIR: Imprimir cada variante en detalle
            for idx, variant in enumerate(variants):
                print(f"[DEBUG] Variante {idx}:")
                print(f"  - _id: {variant.get('_id', 'NO TIENE _id')}")
                print(f"  - name: {variant.get('name', 'NO TIENE name')}")
                print(f"  - Tipo de _id: {type(variant.get('_id'))}")
                print(f"  - Variante completa: {variant}")

            if not variants:
                dispatcher.utter_message(
                    text="Este perfil no tiene variantes disponibles."
                )
                return []

            buttons = []
            for variant in variants:
                variant_id = variant.get('_id', '')
                variant_name = variant.get('name', 'Sin nombre')

                print(f"[DEBUG] Procesando variante: '{variant_name}'")
                print(f"  - ID extraído: '{variant_id}'")
                print(f"  - Tipo de ID: {type(variant_id)}")

                if not variant_id:
                    print(f"[WARNING] Variante '{variant_name}' no tiene _id, saltando...")
                    continue

                payload = f'/SetSlot("variante_id", "{variant_id}")'
                print(f"  - Payload generado: {payload}")

                buttons.append({
                    "title": variant_name,
                    "payload": payload
                })

            if not buttons:
                print(f"[ERROR] No se generaron botones válidos")
                dispatcher.utter_message(
                    text="No hay variantes válidas disponibles."
                )
                return []

            print(f"[DEBUG] Total de botones generados: {len(buttons)}")
            print(f"[DEBUG] Botones completos:")
            for btn in buttons:
                print(f"  - {btn}")

            dispatcher.utter_message(
                text="Selecciona la variante que deseas aplicar:",
                buttons=buttons
            )

        except aiohttp.ClientError as e:
            print(f"[ERROR] Conexión: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
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

        # NO limpiar el slot aquí - se limpiará después de action_ask_next_edit_option
        return []





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





# =========================
# MOSTRAR GEMAS
# =========================
class ActionAskGemaId(Action):
    def name(self) -> Text:
        return "action_ask_gema_id"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")

        # Obtener la posición de gema (puede ser None si solo hay 1 gema)
        gem_position = tracker.get_slot('gem_position')
        
        print(f"[DEBUG] Posición de gema: {gem_position}")
        
        # Si gem_position es None, establecer posición 0 por defecto (1 gema)
        if gem_position is None:
            print("[DEBUG] No hay gem_position, asumiendo posición 0 (1 gema)")
            gem_position = "0"

        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{api_url}/api/gemstones"
                print(f"[DEBUG] GET {endpoint}")

                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="No pude cargar las gemas disponibles."
                        )
                        return []

                    data = await response.json()
                    gemstones = data.get('gemstones', [])

                    print(f"[DEBUG] Nº gemas: {len(gemstones)}")

                    if not gemstones:
                        dispatcher.utter_message(
                            text="No hay gemas disponibles."
                        )
                        return []

                    buttons = []
                    for gemstone in gemstones:
                        gem_id = gemstone.get('_id', '')
                        gem_name = gemstone.get('name', 'Sin nombre')

                        if not gem_name or gem_name == 'None' or gem_name.strip() == '':
                            print(f"[DEBUG] Omitiendo gema sin nombre válido: ID={gem_id}")
                            continue

                        print(f"[DEBUG] Añadiendo botón gema: {gem_name} ({gem_id})")

                        buttons.append({
                            "title": gem_name,
                            "payload": f'SetSlot("gema_id", "{gem_id}")'
                        })

                    dispatcher.utter_message(
                        text="Selecciona la gema que deseas aplicar:",
                        buttons=buttons
                    )

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

        # Si no había gem_position, establecerlo ahora para ActionChangeGema
        if tracker.get_slot('gem_position') is None:
            return [SlotSet("gem_position", "0")]
        
        return []


# =========================
# CAMBIAR GEMA
# =========================
class ActionChangeGema(Action):
    def name(self) -> Text:
        return "action_change_gema"

    async def run(self, dispatcher, tracker, domain):
        gema_id = tracker.get_slot('gema_id')
        gem_position = tracker.get_slot('gem_position')

        print(f"[DEBUG] gema_id recibido: {gema_id}")
        print(f"[DEBUG] gem_position: {gem_position}")

        if not gema_id:
            dispatcher.utter_message(
                text="No pude identificar la gema seleccionada."
            )
            return []

        if gem_position is None:
            gem_position = "0"  # Por defecto primera posición

        dispatcher.utter_message(
            text="Gema cambiada correctamente.",
            custom={
                "type": "change_gema",
                "gema_id": gema_id,
                "gem_position": int(gem_position)
            }
        )

        # NO limpiar los slots aquí - se limpiarán en action_ask_next_edit_option
        return []
    
class ActionResetGemaSlots(Action):
    def name(self) -> Text:
        return "action_reset_gema_slots"

    async def run(self, dispatcher, tracker, domain):
        print("[DEBUG] Limpiando slots de gema al inicio del flow")
        
        return [
            SlotSet("gem_position", None),
            SlotSet("gema_id", None),
            SlotSet("has_gems", None),
            SlotSet("gem_count", None)
        ]






# =========================
# MOSTRAR FORMAS DE GEMA (CUTS)
# =========================
class ActionAskFormaGemaId(Action):
    def name(self) -> Text:
        return "action_ask_forma_gema_id"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")

        gem_position = tracker.get_slot('gem_position_for_cut')
        
        print(f"[DEBUG] Posición de gema para cambiar forma: {gem_position}")

        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{api_url}/api/cuts"
                print(f"[DEBUG] GET {endpoint}")

                async with session.get(endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="No pude cargar las formas de gema disponibles."
                        )
                        return []

                    data = await response.json()
                    cuts = data.get('cuts', [])

                    if not cuts:
                        dispatcher.utter_message(
                            text="No hay formas de gema disponibles."
                        )
                        return []

                    buttons = []
                    for cut in cuts:
                        cut_id = cut.get('_id', '')
                        cut_name = cut.get('name', 'Sin nombre')

                        # ✅ CORRECCIÓN: Usar SetSlot en lugar de intent
                        buttons.append({
                            "title": cut_name,
                            "payload": f'SetSlot("forma_gema_id", "{cut_id}")'
                        })

                    dispatcher.utter_message(
                        text="Selecciona la forma de gema que deseas aplicar:",
                        buttons=buttons
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
# CAMBIAR FORMA DE GEMA
# =========================
class ActionChangeFormaGema(Action):
    def name(self) -> Text:
        return "action_change_forma_gema"

    async def run(self, dispatcher, tracker, domain):
        forma_gema_id = tracker.get_slot('forma_gema_id')
        gem_position = tracker.get_slot('gem_position_for_cut')

        print(f"[DEBUG] forma_gema_id recibido: {forma_gema_id}")
        print(f"[DEBUG] gem_position recibido: {gem_position}")

        if not forma_gema_id:
            dispatcher.utter_message(
                text="No pude identificar la forma de gema seleccionada."
            )
            return []

        # Convertir a int de manera segura
        try:
            position_int = int(gem_position) if gem_position is not None else 0
        except (ValueError, TypeError):
            position_int = 0
            print(f"[WARNING] No se pudo convertir gem_position '{gem_position}' a int, usando 0")

        dispatcher.utter_message(
            text="Forma de gema cambiada correctamente.",
            custom={
                "type": "change_forma_gema",
                "forma_gema_id": forma_gema_id,
                "gem_position": position_int
            }
        )

        return []
    
# class ActionCheckGemCount(Action):
#     def name(self) -> Text:
#         return "action_check_gem_count"

#     async def run(self, dispatcher, tracker, domain):
#         # Esta acción no hace nada, solo permite evaluar la condición en next
#         return []

class ActionVerifyGemsAvailable(Action):
    def name(self) -> Text:
        return "action_verify_gems_available"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")
        
        current_ring_id = tracker.get_slot('ring_id')
        if not current_ring_id:
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            current_ring_id = metadata.get('ring_id')

        if not current_ring_id:
            dispatcher.utter_message(
                text="No tengo información del anillo actual."
            )
            return [SlotSet("has_gems", False)]

        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{api_url}/api/baseStructures/{current_ring_id}"
                async with session.get(endpoint) as response:
                    if response.status < 200 or response.status >= 300:
                        return [SlotSet("has_gems", False)]

                    ring_data = await response.json()

            base_structure = ring_data.get("baseStructure", {})
            
            # Obtener perfil y variante actuales
            current_profile_id = tracker.get_slot('profile_id')
            if not current_profile_id and base_structure.get("profiles"):
                first_profile = base_structure["profiles"][0]
                profile_obj = first_profile.get('profile', {})
                current_profile_id = profile_obj if isinstance(profile_obj, str) else profile_obj.get('_id', '')

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
                return [SlotSet("has_gems", False)]

            current_variant_id = tracker.get_slot('variante_id')
            if not current_variant_id:
                latest_message = tracker.latest_message
                metadata = latest_message.get('metadata', {})
                current_variant_id = metadata.get('variant_id')

            if not current_variant_id and target_profile.get("variants"):
                current_variant_id = target_profile["variants"][0].get('_id', '')

            variant = None
            for v in target_profile.get("variants", []):
                if v.get('_id') == current_variant_id:
                    variant = v
                    break

            if not variant:
                dispatcher.utter_message(
                    text="No pude encontrar la variante actual del anillo."
                )
                return [SlotSet("has_gems", False)]

            settings_info = variant.get("settingsInfo", [])
            gem_count = len(settings_info)
            
            if gem_count == 0:
                dispatcher.utter_message(
                    text="Esta variante no permite añadir gemas. Por favor, selecciona primero una base que permita poner gemas al anillo."
                )
                return [
                    SlotSet("has_gems", False),
                    SlotSet("gem_count", 0)
                ]

            return [
                SlotSet("has_gems", True),
                SlotSet("gem_count", gem_count)
            ]

        except Exception as e:
            print(f"[ERROR] General: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return [SlotSet("has_gems", False)]





# =========================
# MOSTRAR ENGASTES COMPATIBLES
# =========================
class ActionAskEngasteId(Action):
    def name(self) -> Text:
        return "action_ask_engaste_id"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")

        gem_position = tracker.get_slot('gem_position_for_setting')
        current_ring_id = tracker.get_slot('ring_id')
        
        if not current_ring_id:
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            current_ring_id = metadata.get('ring_id')
        
        print(f"[DEBUG] Ring ID: {current_ring_id}")
        print(f"[DEBUG] Posición de gema para cambiar engaste: {gem_position}")

        # Si gem_position es None, establecer posición 0 por defecto (1 gema)
        if gem_position is None:
            print("[DEBUG] No hay gem_position_for_setting, asumiendo posición 0 (1 gema)")
            gem_position = "0"

        if not current_ring_id:
            print(f"[ERROR] No se encontró ring_id")
            dispatcher.utter_message(
                text="No tengo información del anillo actual. Por favor, intenta cargar el anillo nuevamente."
            )
            return []

        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{api_url}/api/baseStructures/{current_ring_id}"
                print(f"[DEBUG] GET {endpoint}")

                async with session.get(endpoint) as response:
                    if response.status < 200 or response.status >= 300:
                        print(f"[ERROR] Status code: {response.status}")
                        dispatcher.utter_message(
                            text="No pude cargar la información del anillo."
                        )
                        return []

                    ring_data = await response.json()

            base_structure = ring_data.get("baseStructure", {})
            
            current_profile_id = tracker.get_slot('profile_id')
            
            if not current_profile_id:
                latest_message = tracker.latest_message
                metadata = latest_message.get('metadata', {})
                current_profile_id = metadata.get('profile_id')
            
            if not current_profile_id and base_structure.get("profiles"):
                first_profile = base_structure["profiles"][0]
                profile_obj = first_profile.get('profile', {})
                current_profile_id = profile_obj if isinstance(profile_obj, str) else profile_obj.get('_id', '')

            print(f"[DEBUG] Profile ID: {current_profile_id}")

            if not current_profile_id:
                print(f"[ERROR] No se encontró profile_id")
                dispatcher.utter_message(
                    text="No pude identificar el perfil actual del anillo."
                )
                return []

            target_profile = None
            for profile_data in base_structure.get("profiles", []):
                profile_obj = profile_data.get('profile', {})
                profile_id = profile_obj if isinstance(profile_obj, str) else profile_obj.get('_id', '')
                
                if profile_id == current_profile_id:
                    target_profile = profile_data
                    break

            if not target_profile:
                print(f"[ERROR] No se encontró el perfil con ID: {current_profile_id}")
                dispatcher.utter_message(
                    text="No pude encontrar el perfil actual del anillo."
                )
                return []

            current_variant_id = tracker.get_slot('variante_id')
            
            if not current_variant_id:
                latest_message = tracker.latest_message
                metadata = latest_message.get('metadata', {})
                current_variant_id = metadata.get('variant_id')

            if not current_variant_id and target_profile.get("variants"):
                current_variant_id = target_profile["variants"][0].get('_id', '')

            print(f"[DEBUG] Variant ID: {current_variant_id}")

            if not current_variant_id:
                print(f"[ERROR] No se encontró variant_id")
                dispatcher.utter_message(
                    text="No pude identificar la variante actual del anillo."
                )
                return []

            variant = None
            for v in target_profile.get("variants", []):
                if v.get('_id') == current_variant_id:
                    variant = v
                    break

            if not variant:
                print(f"[ERROR] No se encontró la variante con ID: {current_variant_id}")
                dispatcher.utter_message(
                    text="No pude encontrar la variante actual del anillo."
                )
                return []

            settings_info = variant.get("settingsInfo", [])
            
            if not settings_info:
                print(f"[ERROR] No hay settings_info en la variante")
                dispatcher.utter_message(
                    text="Esta variante no tiene configuración de engastes."
                )
                return []

            position_index = 0
            if gem_position is not None:
                try:
                    position_index = int(gem_position)
                except (ValueError, TypeError):
                    position_index = 0

            if position_index >= len(settings_info):
                position_index = 0

            print(f"[DEBUG] Usando posición de gema: {position_index}")

            setting_info = settings_info[position_index]
            compatible_settings = setting_info.get("compatibleSettings", [])

            if not compatible_settings:
                print(f"[ERROR] No hay compatibleSettings en la posición {position_index}")
                dispatcher.utter_message(
                    text="No hay engastes compatibles para esta posición."
                )
                return []

            compatible_setting_ids = set()
            for comp_setting in compatible_settings:
                setting_obj = comp_setting.get('setting')
                if isinstance(setting_obj, str):
                    compatible_setting_ids.add(setting_obj)
                elif isinstance(setting_obj, dict):
                    compatible_setting_ids.add(setting_obj.get('_id', ''))

            print(f"[DEBUG] Engastes compatibles IDs: {compatible_setting_ids}")

            if not compatible_setting_ids:
                print(f"[ERROR] No se extrajeron IDs de engastes compatibles")
                dispatcher.utter_message(
                    text="No encontré engastes compatibles."
                )
                return []

            settings_endpoint = f"{api_url}/api/settings"
            print(f"[DEBUG] GET {settings_endpoint}")

            async with aiohttp.ClientSession() as session:
                async with session.get(settings_endpoint) as response:
                    if response.status != 200:
                        print(f"[ERROR] Status al obtener settings: {response.status}")
                        dispatcher.utter_message(
                            text="No pude cargar los engastes disponibles."
                        )
                        return []

                    data = await response.json()
                    all_settings = data.get('settings', [])

            print(f"[DEBUG] Total de engastes en catálogo: {len(all_settings)}")

            buttons = []
            for setting in all_settings:
                setting_id = setting.get('_id', '')
                
                if setting_id in compatible_setting_ids:
                    setting_name = setting.get('name', 'Sin nombre')
                    
                    print(f"[DEBUG] Añadiendo engaste compatible: {setting_name} ({setting_id})")
                    
                    buttons.append({
                        "title": setting_name,
                        "payload": f'SetSlot("engaste_id", "{setting_id}")'
                    })

            if not buttons:
                print(f"[ERROR] No se generaron botones de engastes")
                dispatcher.utter_message(
                    text="No encontré engastes compatibles disponibles."
                )
                return []

            print(f"[DEBUG] Total de botones generados: {len(buttons)}")

            dispatcher.utter_message(
                text="Selecciona el engaste que deseas aplicar:",
                buttons=buttons
            )

        except aiohttp.ClientError as e:
            print(f"[ERROR] Error de conexión: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            dispatcher.utter_message(
                text="Error de conexión con el servidor."
            )
        except Exception as e:
            print(f"[ERROR] Error general: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            dispatcher.utter_message(
                text="Error interno en el servidor."
            )

        # Si no había gem_position_for_setting, establecerlo ahora para ActionChangeEngaste
        if tracker.get_slot('gem_position_for_setting') is None:
            return [SlotSet("gem_position_for_setting", "0")]
        
        return []


# =========================
# CAMBIAR ENGASTE
# =========================
class ActionChangeEngaste(Action):
    def name(self) -> Text:
        return "action_change_engaste"

    async def run(self, dispatcher, tracker, domain):
        engaste_id = tracker.get_slot('engaste_id')
        gem_position = tracker.get_slot('gem_position_for_setting')

        print(f"[DEBUG] engaste_id recibido: {engaste_id}")
        print(f"[DEBUG] gem_position recibido: {gem_position}")

        if not engaste_id:
            dispatcher.utter_message(
                text="No pude identificar el engaste seleccionado."
            )
            return []

        # Convertir a int de manera segura
        try:
            position_int = int(gem_position) if gem_position is not None else 0
        except (ValueError, TypeError):
            position_int = 0
            print(f"[WARNING] No se pudo convertir gem_position '{gem_position}' a int, usando 0")

        dispatcher.utter_message(
            text="Engaste cambiado correctamente.",
            custom={
                "type": "change_engaste",
                "engaste_id": engaste_id,
                "gem_position": position_int
            }
        )

        return []
    






# =========================
# VERIFICAR Y SELECCIONAR POSICIÓN DE GEMA PARA NÚMERO DE GARRAS
# =========================
class ActionAskGemPositionForClawNumber(Action):
    def name(self) -> Text:
        return "action_ask_gem_position_for_claw_number"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")
        
        current_ring_id = tracker.get_slot('ring_id')
        if not current_ring_id:
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            current_ring_id = metadata.get('ring_id')

        print(f"[DEBUG] Ring ID para número de garras: {current_ring_id}")

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
                    if response.status < 200 or response.status >= 300:
                        dispatcher.utter_message(
                            text="No pude cargar la información del anillo."
                        )
                        return []

                    ring_data = await response.json()

            base_structure = ring_data.get("baseStructure", {})
            
            # Obtener el perfil y variante actuales
            current_profile_id = tracker.get_slot('profile_id')
            if not current_profile_id and base_structure.get("profiles"):
                first_profile = base_structure["profiles"][0]
                profile_obj = first_profile.get('profile', {})
                current_profile_id = profile_obj if isinstance(profile_obj, str) else profile_obj.get('_id', '')

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

            # Obtener la variante actual
            current_variant_id = tracker.get_slot('variante_id')
            if not current_variant_id:
                latest_message = tracker.latest_message
                metadata = latest_message.get('metadata', {})
                current_variant_id = metadata.get('variant_id')

            if not current_variant_id and target_profile.get("variants"):
                current_variant_id = target_profile["variants"][0].get('_id', '')

            variant = None
            for v in target_profile.get("variants", []):
                if v.get('_id') == current_variant_id:
                    variant = v
                    break

            if not variant:
                dispatcher.utter_message(
                    text="No pude encontrar la variante actual del anillo."
                )
                return []

            # Verificar si la variante tiene settings (gemas)
            settings_info = variant.get("settingsInfo", [])
            
            print(f"[DEBUG] Nº settings en variante: {len(settings_info)}")

            if not settings_info:
                dispatcher.utter_message(
                    text="Esta variante no permite añadir gemas. Por favor, selecciona primero una base que permita poner gemas al anillo."
                )
                return []

            # Si hay exactamente 3 settings, preguntar cuál modificar
            if len(settings_info) == 3:
                buttons = [
                    {"title": "Gema izquierda", "payload": 'SetSlot("gem_position_for_claw_number", "0")'},
                    {"title": "Gema central", "payload": 'SetSlot("gem_position_for_claw_number", "1")'},
                    {"title": "Gema derecha", "payload": 'SetSlot("gem_position_for_claw_number", "2")'}
                ]
                
                dispatcher.utter_message(
                    text="¿A qué gema deseas cambiarle el número de garras?",
                    buttons=buttons
                )
                
                return []
            else:
                # Si solo hay 1 gema, establecer posición 0 automáticamente
                return [SlotSet("gem_position_for_claw_number", "0")]

        except Exception as e:
            print(f"[ERROR] General: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            dispatcher.utter_message(
                text="Error al verificar la configuración del anillo."
            )
            return []


class ActionAskNumeroGarrasId(Action):
    def name(self) -> Text:
        return "action_ask_numero_garras_id"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")

        gem_position = tracker.get_slot('gem_position_for_claw_number')
        current_ring_id = tracker.get_slot('ring_id')
        
        if not current_ring_id:
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            current_ring_id = metadata.get('ring_id')
        
        # ← NUEVO: Obtener el setting_id desde metadata
        latest_message = tracker.latest_message
        metadata = latest_message.get('metadata', {})
        current_setting_id = metadata.get('setting_id')
        
        print(f"[DEBUG] Ring ID: {current_ring_id}")
        print(f"[DEBUG] Setting ID actual: {current_setting_id}")
        print(f"[DEBUG] Posición de gema para cambiar número de garras: {gem_position}")

        if not current_ring_id:
            dispatcher.utter_message(
                text="No tengo información del anillo actual."
            )
            return []

        if not current_setting_id:
            dispatcher.utter_message(
                text="No pude identificar el engaste actual."
            )
            return []

        try:
            # Obtener todos los engastes del catálogo
            settings_endpoint = f"{api_url}/api/settings"
            print(f"[DEBUG] GET {settings_endpoint}")

            async with aiohttp.ClientSession() as session:
                async with session.get(settings_endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(
                            text="No pude cargar los engastes disponibles."
                        )
                        return []

                    data = await response.json()
                    all_settings = data.get('settings', [])

            # Buscar el engaste actual en el catálogo usando el setting_id del metadata
            current_setting = None
            for setting in all_settings:
                if setting.get('_id', '') == current_setting_id:
                    current_setting = setting
                    break

            if not current_setting:
                dispatcher.utter_message(
                    text="No pude encontrar el engaste actual en el catálogo."
                )
                return []

            print(f"[DEBUG] Engaste encontrado: {current_setting.get('name', 'Sin nombre')}")

            # Obtener los números de garras disponibles para este engaste
            claw_numbers = current_setting.get('clawNumber', [])

            if not claw_numbers:
                dispatcher.utter_message(
                    text="Este engaste no tiene opciones de número de garras disponibles."
                )
                return []

            print(f"[DEBUG] Números de garras disponibles: {len(claw_numbers)}")

            # Crear botones con los números de garras disponibles
            buttons = []
            for claw_num in claw_numbers:
                claw_num_id = claw_num.get('_id', '')
                claw_num_name = claw_num.get('name', 'Sin nombre')
                
                print(f"[DEBUG] Añadiendo número de garras: {claw_num_name} ({claw_num_id})")
                
                buttons.append({
                    "title": claw_num_name,
                    "payload": f'SetSlot("numero_garras_id", "{claw_num_id}")'
                })

            if not buttons:
                dispatcher.utter_message(
                    text="No encontré opciones de número de garras disponibles para este engaste."
                )
                return []

            dispatcher.utter_message(
                text=f"Selecciona el número de garras que deseas aplicar al engaste {current_setting.get('name', '')}:",
                buttons=buttons
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
# CAMBIAR NÚMERO DE GARRAS
# =========================
class ActionChangeGarrasEngaste(Action):
    def name(self) -> Text:
        return "action_change_garras_engaste"

    async def run(self, dispatcher, tracker, domain):
        numero_garras_id = tracker.get_slot('numero_garras_id')
        gem_position = tracker.get_slot('gem_position_for_claw_number')

        print(f"[DEBUG] numero_garras_id recibido: {numero_garras_id}")
        print(f"[DEBUG] gem_position recibido: {gem_position}")

        if not numero_garras_id:
            dispatcher.utter_message(
                text="No pude identificar el número de garras seleccionado."
            )
            return []

        # Convertir a int de manera segura
        try:
            position_int = int(gem_position) if gem_position is not None else 0
        except (ValueError, TypeError):
            position_int = 0
            print(f"[WARNING] No se pudo convertir gem_position '{gem_position}' a int, usando 0")

        dispatcher.utter_message(
            text="Número de garras cambiado correctamente.",
            custom={
                "type": "change_claw_number",
                "numero_garras_id": numero_garras_id,
                "gem_position": position_int
            }
        )

        # Limpiar los slots después de usarlos
        return [
            SlotSet("numero_garras_id", None),
            SlotSet("gem_position_for_claw_number", None)
        ]






# =========================
# RESETEAR SLOTS DE TIPO DE GARRAS
# =========================
class ActionResetClawTypeSlots(Action):
    def name(self) -> Text:
        return "action_reset_claw_type_slots"

    async def run(self, dispatcher, tracker, domain):
        print("[DEBUG] Limpiando slots de tipo de garras al inicio del flow")
        
        return [
            SlotSet("gem_position_for_claw_type", None),
            SlotSet("tipo_garras_id", None),
            SlotSet("has_claw_types", None),
            SlotSet("gem_count", None)
        ]


# =========================
# VERIFICAR TIPOS DE GARRAS DISPONIBLES
# =========================
class ActionVerifyClawTypesAvailable(Action):
    def name(self) -> Text:
        return "action_verify_claw_types_available"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")
        
        current_ring_id = tracker.get_slot('ring_id')
        if not current_ring_id:
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            current_ring_id = metadata.get('ring_id')

        print(f"[DEBUG] Ring ID para verificar tipos de garras: {current_ring_id}")

        if not current_ring_id:
            return [
                SlotSet("has_claw_types", False),
                SlotSet("gem_count", 0)
            ]

        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{api_url}/api/baseStructures/{current_ring_id}"
                print(f"[DEBUG] GET {endpoint}")

                async with session.get(endpoint) as response:
                    if response.status < 200 or response.status >= 300:
                        return [
                            SlotSet("has_claw_types", False),
                            SlotSet("gem_count", 0)
                        ]

                    ring_data = await response.json()

            base_structure = ring_data.get("baseStructure", {})
            
            # Obtener el perfil actual
            current_profile_id = tracker.get_slot('profile_id')
            if not current_profile_id and base_structure.get("profiles"):
                first_profile = base_structure["profiles"][0]
                profile_obj = first_profile.get('profile', {})
                current_profile_id = profile_obj if isinstance(profile_obj, str) else profile_obj.get('_id', '')

            # Buscar el perfil específico
            target_profile = None
            for profile_data in base_structure.get("profiles", []):
                profile_obj = profile_data.get('profile', {})
                profile_id = profile_obj if isinstance(profile_obj, str) else profile_obj.get('_id', '')
                
                if profile_id == current_profile_id:
                    target_profile = profile_data
                    break

            if not target_profile:
                return [
                    SlotSet("has_claw_types", False),
                    SlotSet("gem_count", 0)
                ]

            # Obtener la variante actual
            current_variant_id = tracker.get_slot('variante_id')
            if not current_variant_id:
                latest_message = tracker.latest_message
                metadata = latest_message.get('metadata', {})
                current_variant_id = metadata.get('variant_id')

            if not current_variant_id and target_profile.get("variants"):
                current_variant_id = target_profile["variants"][0].get('_id', '')

            variant = None
            for v in target_profile.get("variants", []):
                if v.get('_id') == current_variant_id:
                    variant = v
                    break

            if not variant:
                return [
                    SlotSet("has_claw_types", False),
                    SlotSet("gem_count", 0)
                ]

            # Verificar si la variante tiene settings (gemas)
            settings_info = variant.get("settingsInfo", [])
            
            print(f"[DEBUG] Nº settings en variante: {len(settings_info)}")

            if not settings_info:
                return [
                    SlotSet("has_claw_types", False),
                    SlotSet("gem_count", 0)
                ]

            # Verificar que hay tipos de garras disponibles
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            current_setting_id = metadata.get('setting_id')
            current_claw_number_id = metadata.get('claw_number_id')
            current_cut_id = metadata.get('cut_id')

            if not current_setting_id:
                return [
                    SlotSet("has_claw_types", False),
                    SlotSet("gem_count", len(settings_info))
                ]

            # Obtener todos los engastes
            settings_endpoint = f"{api_url}/api/settings"
            async with aiohttp.ClientSession() as session:
                async with session.get(settings_endpoint) as response:
                    if response.status != 200:
                        return [
                            SlotSet("has_claw_types", False),
                            SlotSet("gem_count", len(settings_info))
                        ]
                    data = await response.json()
                    all_settings = data.get('settings', [])

            # Buscar el engaste actual
            current_setting = next((s for s in all_settings if s.get('_id') == current_setting_id), None)
            
            if not current_setting:
                return [
                    SlotSet("has_claw_types", False),
                    SlotSet("gem_count", len(settings_info))
                ]

            # Buscar el clawNumber específico
            claw_number_obj = None
            for cn in current_setting.get('clawNumber', []):
                if cn.get('_id') == current_claw_number_id:
                    claw_number_obj = cn
                    break
            
            if not claw_number_obj:
                claw_number_obj = current_setting.get('clawNumber', [{}])[0]

            # Buscar el cut específico
            compatible_cut_obj = None
            for cc in claw_number_obj.get('compatibleCuts', []):
                cut_obj = cc.get('cut')
                cut_id = cut_obj if isinstance(cut_obj, str) else cut_obj.get('_id')
                if cut_id == current_cut_id:
                    compatible_cut_obj = cc
                    break
            
            if not compatible_cut_obj:
                compatible_cut_obj = claw_number_obj.get('compatibleCuts', [{}])[0]

            # Obtener los tipos de garras disponibles
            claw_types = compatible_cut_obj.get('clawType', [])

            has_claw_types = len(claw_types) > 0

            print(f"[DEBUG] Has claw types: {has_claw_types}")
            print(f"[DEBUG] Gem count: {len(settings_info)}")

            return [
                SlotSet("has_claw_types", has_claw_types),
                SlotSet("gem_count", len(settings_info))
            ]

        except Exception as e:
            print(f"[ERROR] General: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return [
                SlotSet("has_claw_types", False),
                SlotSet("gem_count", 0)
            ]


# =========================
# MOSTRAR TIPOS DE GARRAS COMPATIBLES SEGÚN EL ENGASTE Y NÚMERO DE GARRAS ACTUAL
# =========================
class ActionAskTipoGarrasId(Action):
    def name(self) -> Text:
        return "action_ask_tipo_garras_id"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")

        gem_position = tracker.get_slot('gem_position_for_claw_type')
        
        if gem_position is None:
            print("[DEBUG] No hay gem_position_for_claw_type, asumiendo posición 0")
            gem_position = "0"

        latest_message = tracker.latest_message
        metadata = latest_message.get('metadata', {})
        current_setting_id = metadata.get('setting_id')
        current_claw_number_id = metadata.get('claw_number_id')
        current_cut_id = metadata.get('cut_id')

        if not current_setting_id:
            dispatcher.utter_message(text="No pude identificar el engaste actual.")
            return []

        try:
            settings_endpoint = f"{api_url}/api/settings"
            async with aiohttp.ClientSession() as session:
                async with session.get(settings_endpoint) as response:
                    if response.status != 200:
                        dispatcher.utter_message(text="No pude cargar los engastes disponibles.")
                        return []
                    data = await response.json()
                    all_settings = data.get('settings', [])

            current_setting = next((s for s in all_settings if s.get('_id') == current_setting_id), None)
            if not current_setting:
                dispatcher.utter_message(text="No pude encontrar el engaste actual.")
                return []

            claw_number_obj = None
            for cn in current_setting.get('clawNumber', []):
                if cn.get('_id') == current_claw_number_id:
                    claw_number_obj = cn
                    break
            
            if not claw_number_obj:
                claw_number_obj = current_setting.get('clawNumber', [{}])[0]

            compatible_cut_obj = None
            for cc in claw_number_obj.get('compatibleCuts', []):
                cut_obj = cc.get('cut')
                cut_id = cut_obj if isinstance(cut_obj, str) else cut_obj.get('_id')
                if cut_id == current_cut_id:
                    compatible_cut_obj = cc
                    break
            
            if not compatible_cut_obj:
                compatible_cut_obj = claw_number_obj.get('compatibleCuts', [{}])[0]

            claw_types = compatible_cut_obj.get('clawType', [])

            if not claw_types:
                dispatcher.utter_message(text="No hay tipos de garras disponibles.")
                return []

            buttons = []
            for claw_type in claw_types:
                claw_type_id = claw_type.get('_id', '')
                claw_type_name = claw_type.get('name', 'Sin nombre')
                
                buttons.append({
                    "title": claw_type_name,
                    "payload": f'SetSlot("tipo_garras_id", "{claw_type_id}")'
                })

            dispatcher.utter_message(
                text="Selecciona el tipo de garras que deseas aplicar:",
                buttons=buttons
            )

        except Exception as e:
            print(f"[ERROR] {e}")
            dispatcher.utter_message(text="Error interno en el servidor.")

        if tracker.get_slot('gem_position_for_claw_type') is None:
            return [SlotSet("gem_position_for_claw_type", "0")]
        
        return []


# =========================
# CAMBIAR TIPO DE GARRAS
# =========================
class ActionChangeGarrasTypeEngaste(Action):
    def name(self) -> Text:
        return "action_change_garras_type_engaste"

    async def run(self, dispatcher, tracker, domain):
        tipo_garras_id = tracker.get_slot('tipo_garras_id')
        gem_position = tracker.get_slot('gem_position_for_claw_type')

        if not tipo_garras_id:
            dispatcher.utter_message(text="No pude identificar el tipo de garras seleccionado.")
            return []

        if gem_position is None:
            gem_position = "0"

        try:
            position_int = int(gem_position)
        except (ValueError, TypeError):
            position_int = 0

        dispatcher.utter_message(
            text="Tipo de garras cambiado correctamente.",
            custom={
                "type": "change_claw_type",
                "tipo_garras_id": tipo_garras_id,
                "gem_position": position_int
            }
        )

        # NO limpiar slots aquí - se limpian en action_ask_next_edit_option
        return []
    




# =========================
# MOSTRAR OPCIONES DE EMPAQUETADO
# =========================
class ActionAskBoxShapeId(Action):
    def name(self) -> Text:
        return "action_ask_box_shape_id"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")
        
        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{api_url}/api/box"
                print(f"[DEBUG] GET {endpoint}")
                
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"[ERROR] Response: {error_text}")
                        dispatcher.utter_message(
                            text="No pude cargar las opciones de empaquetado."
                        )
                        return []
                    
                    data = await response.json()
                    all_boxes = data.get('boxes', [])
                    print(f"[DEBUG] Cajas encontradas: {len(all_boxes)}")

            # ✅ Filtrar cajas sin nombre válido
            valid_boxes = [
                box for box in all_boxes 
                if box.get('name') and box.get('name').strip() and box.get('name') != 'None'
            ]

            if not valid_boxes:
                dispatcher.utter_message(
                    text="No hay opciones de empaquetado disponibles."
                )
                return []

            # ✅ Crear botones con payload correcto
            buttons = []
            for box in valid_boxes:
                box_id = box.get('_id', '')
                box_name = box.get('name', '')
                
                print(f"[DEBUG] Caja: {box_name} - ID: {box_id}")
                
                buttons.append({
                    "title": box_name,
                    "payload": f'/SetSlots(box_shape_id={box_id})'  # ✅ Sin comillas
                })

            dispatcher.utter_message(
                text="Selecciona el tipo de empaquetado que deseas:",
                buttons=buttons
            )

        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            dispatcher.utter_message(
                text="Error al cargar las opciones de empaquetado."
            )

        return []


# =========================
# CAMBIAR EMPAQUETADO
# =========================
class ActionChangeBoxShape(Action):
    def name(self) -> Text:
        return "action_change_box_shape"

    async def run(self, dispatcher, tracker, domain):
        box_shape_id = tracker.get_slot('box_shape_id')

        print(f"[DEBUG] box_shape_id recibido: {box_shape_id}")

        if not box_shape_id:
            dispatcher.utter_message(
                text="No pude identificar el tipo de empaquetado seleccionado."
            )
            return []

        dispatcher.utter_message(
            text="Empaquetado seleccionado correctamente.",
            custom={
                "type": "change_box_shape",
                "box_shape_id": box_shape_id
            }
        )

        # El slot ya está establecido por el paso collect
        return []
    

    



# =========================
# MOSTRAR OPCIONES DE MATERIAL EXTERIOR
# =========================
class ActionAskBoxOuterColorId(Action):
    def name(self) -> Text:
        return "action_ask_box_outer_color_id"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")
        
        box_shape_id = tracker.get_slot('box_shape_id')
        
        if not box_shape_id:
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            box_shape_id = metadata.get('box_shape_id')
        
        print(f"[DEBUG] box_shape_id: {box_shape_id}")
        
        if not box_shape_id:
            dispatcher.utter_message(
                text="Primero debes seleccionar un tipo de empaquetado."
            )
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{api_url}/api/box/{box_shape_id}/outerMaterials"
                print(f"[DEBUG] GET {endpoint}")
                
                async with session.get(endpoint) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"[ERROR] Response: {error_text}")
                        dispatcher.utter_message(
                            text="No pude cargar los materiales exteriores."
                        )
                        return []
                    
                    data = await response.json()
                    all_materials = data.get('outerMaterials', [])
                    print(f"[DEBUG] Materiales exteriores: {len(all_materials)}")

            # Filtrar materiales sin nombre válido
            valid_materials = [
                mat for mat in all_materials 
                if mat.get('name') and mat.get('name').strip() and mat.get('name') != 'None'
            ]

            if not valid_materials:
                dispatcher.utter_message(
                    text="No hay materiales exteriores disponibles para este empaquetado."
                )
                return []

            # Crear botones con payload correcto
            buttons = []
            for material in valid_materials:
                material_id = material.get('_id', '')
                material_name = material.get('name', '')
                
                print(f"[DEBUG] Material: {material_name} - ID: {material_id}")
                
                buttons.append({
                    "title": material_name,
                    "payload": f'/SetSlots(box_outer_color_id={material_id})'
                })

            dispatcher.utter_message(
                text="Selecciona el material exterior que deseas:",
                buttons=buttons
            )

        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            dispatcher.utter_message(
                text="Error al cargar los materiales exteriores."
            )

        return []


# =========================
# CAMBIAR MATERIAL EXTERIOR DEL EMPAQUETADO
# =========================
class ActionChangeBoxOuterColor(Action):
    def name(self) -> Text:
        return "action_change_box_outer_color"

    async def run(self, dispatcher, tracker, domain):
        box_outer_color_id = tracker.get_slot('box_outer_color_id')
        box_shape_id = tracker.get_slot('box_shape_id')

        print(f"[DEBUG] box_outer_color_id recibido: {box_outer_color_id}")
        print(f"[DEBUG] box_shape_id actual: {box_shape_id}")

        if not box_outer_color_id:
            dispatcher.utter_message(
                text="No pude identificar el material exterior seleccionado."
            )
            return []

        dispatcher.utter_message(
            text="Material exterior cambiado correctamente.",
            custom={
                "type": "change_box_outer_color",
                "box_outer_color_id": box_outer_color_id
            }
        )

        return []


    






# =========================
# MOSTRAR OPCIONES DE MATERIAL INTERIOR
# =========================
class ActionAskBoxInnerColorId(Action):
    def name(self) -> Text:
        return "action_ask_box_inner_color_id"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")
        
        # Obtener el box_shape_id del slot
        box_shape_id = tracker.get_slot('box_shape_id')
        
        # Si no está en el slot, intentar obtenerlo desde metadata
        if not box_shape_id:
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            box_shape_id = metadata.get('box_shape_id')
        
        print(f"[DEBUG] box_shape_id para material interior: {box_shape_id}")
        
        # Verificar que hay una caja seleccionada
        if not box_shape_id:
            dispatcher.utter_message(
                text="Primero debes seleccionar un tipo de empaquetado antes de cambiar su material interior."
            )
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Obtener los materiales interiores de la caja específica
                endpoint = f"{api_url}/api/box/{box_shape_id}/innerMaterials"
                print(f"[DEBUG] GET {endpoint}")
                
                async with session.get(endpoint) as response:
                    print(f"[DEBUG] Status code: {response.status}")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"[ERROR] Response body: {error_text}")
                        
                        dispatcher.utter_message(
                            text="No pude cargar las opciones de material interior para este empaquetado."
                        )
                        return []
                    
                    data = await response.json()
                    print(f"[DEBUG] Response data: {data}")
                    
                    all_inner_materials = data.get('innerMaterials', [])
                    print(f"[DEBUG] Número de materiales interiores totales: {len(all_inner_materials)}")

            # Filtrar materiales sin nombre válido
            valid_materials = [
                mat for mat in all_inner_materials 
                if mat.get('name') and mat.get('name').strip() and mat.get('name') != 'None'
            ]
            
            print(f"[DEBUG] Número de materiales interiores válidos: {len(valid_materials)}")

            if not valid_materials:
                dispatcher.utter_message(
                    text="No hay opciones de material interior disponibles para este empaquetado."
                )
                return []

            # Crear botones con payload correcto
            buttons = []
            for material in valid_materials:
                material_id = material.get('_id', '')
                material_name = material.get('name', '')
                
                print(f"[DEBUG] Material interior: {material_name} - ID: {material_id}")
                
                buttons.append({
                    "title": material_name,
                    "payload": f'/SetSlots(box_inner_color_id={material_id})'
                })

            if not buttons:
                dispatcher.utter_message(
                    text="No encontré opciones de material interior disponibles."
                )
                return []

            print(f"[DEBUG] Enviando {len(buttons)} botones al usuario")
            
            dispatcher.utter_message(
                text="Selecciona el material interior que deseas para el empaquetado:",
                buttons=buttons
            )

        except aiohttp.ClientError as e:
            print(f"[ERROR] Error de conexión: {e}")
            dispatcher.utter_message(
                text="Error de conexión al cargar las opciones de material interior."
            )
        except Exception as e:
            print(f"[ERROR] Error general: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            dispatcher.utter_message(
                text="Error interno al cargar las opciones de material interior."
            )

        return []


# =========================
# CAMBIAR MATERIAL INTERIOR DEL EMPAQUETADO
# =========================
class ActionChangeBoxInnerColor(Action):
    def name(self) -> Text:
        return "action_change_box_inner_color"

    async def run(self, dispatcher, tracker, domain):
        box_inner_color_id = tracker.get_slot('box_inner_color_id')
        box_shape_id = tracker.get_slot('box_shape_id')
        box_outer_color_id = tracker.get_slot('box_outer_color_id')

        print(f"[DEBUG] box_inner_color_id recibido: {box_inner_color_id}")
        print(f"[DEBUG] box_shape_id actual: {box_shape_id}")
        print(f"[DEBUG] box_outer_color_id actual: {box_outer_color_id}")

        if not box_inner_color_id:
            dispatcher.utter_message(
                text="No pude identificar el material interior seleccionado."
            )
            return []

        dispatcher.utter_message(
            text="Empaquetado completo actualizado correctamente.",
            custom={
                "type": "change_box_complete",
                "box_shape_id": box_shape_id,
                "box_outer_color_id": box_outer_color_id,
                "box_inner_color_id": box_inner_color_id
            }
        )

        return []
    
# =========================
# RESET SLOTS DE EMPAQUETADO
# =========================
class ActionResetBoxSlots(Action):
    def name(self) -> Text:
        return "action_reset_box_slots"

    async def run(self, dispatcher, tracker, domain):
        print("[DEBUG] Reseteando slots de empaquetado")
        return [
            SlotSet("box_shape_id", None),
            SlotSet("box_outer_color_id", None),
            SlotSet("box_inner_color_id", None)
        ]
    





# =========================
# PREGUNTAR SIGUIENTE OPCIÓN DE EDICIÓN (DINÁMICA)
# =========================
class ActionAskNextEditOption(Action):
    def name(self) -> Text:
        return "action_ask_next_edit_option"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")
        
        current_ring_id = tracker.get_slot('ring_id')
        if not current_ring_id:
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            current_ring_id = metadata.get('ring_id')

        print(f"[DEBUG] Ring ID para opciones: {current_ring_id}")

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
                    if response.status < 200 or response.status >= 300:
                        dispatcher.utter_message(
                            text="No pude cargar la información del anillo."
                        )
                        return []

                    ring_data = await response.json()

            base_structure = ring_data.get("baseStructure", {})
            
            # Obtener el perfil actual - PRIMERO del slot, luego de metadata
            current_profile_id = tracker.get_slot('profile_id')
            
            if not current_profile_id:
                latest_message = tracker.latest_message
                metadata = latest_message.get('metadata', {})
                current_profile_id = metadata.get('profile_id')
            
            if not current_profile_id and base_structure.get("profiles"):
                first_profile = base_structure["profiles"][0]
                profile_obj = first_profile.get('profile', {})
                current_profile_id = profile_obj if isinstance(profile_obj, str) else profile_obj.get('_id', '')

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

            # Obtener la variante actual - PRIMERO del slot, luego de metadata
            current_variant_id = tracker.get_slot('variante_id')
            
            if not current_variant_id:
                latest_message = tracker.latest_message
                metadata = latest_message.get('metadata', {})
                current_variant_id = metadata.get('variant_id')

            if not current_variant_id and target_profile.get("variants"):
                current_variant_id = target_profile["variants"][0].get('_id', '')

            variant = None
            for v in target_profile.get("variants", []):
                if v.get('_id') == current_variant_id:
                    variant = v
                    break

            if not variant:
                dispatcher.utter_message(
                    text="No pude encontrar la variante actual del anillo."
                )
                return []

            # Verificar si la variante tiene settings (gemas)
            settings_info = variant.get("settingsInfo", [])
            has_gems = len(settings_info) > 0
            
            print(f"[DEBUG] Variante tiene gemas: {has_gems}")
            print(f"[DEBUG] Número de settings: {len(settings_info)}")

            # Construir lista de botones dinámicamente
            buttons = []
            
            # Siempre disponibles
            buttons.append({
                "title": "Cambiar base",
                "payload": '/StartFlow(modificar_base_del_anillo)'
            })

            buttons.append({
                "title": "Cambiar variante",
                "payload": '/StartFlow(modificar_variante_del_anillo)'
            })
            
            buttons.append({
                "title": "Cambiar material",
                "payload": '/StartFlow(modificar_material_del_anillo)'
            })
            
            # Solo si tiene gemas
            if has_gems:
                buttons.append({
                    "title": "Cambiar gema",
                    "payload": '/StartFlow(modificar_gema_del_anillo)'
                })
                
                buttons.append({
                    "title": "Cambiar forma de gema",
                    "payload": '/StartFlow(modificar_forma_de_la_gema_del_anillo)'
                })
                
                buttons.append({
                    "title": "Cambiar engaste",
                    "payload": '/StartFlow(modificar_engaste_del_anillo)'
                })

                # buttons.append({
                #     "title": "Cambiar número de garras",
                #     "payload": '/StartFlow(modificar_numero_de_garras_del_engaste_del_anillo)'
                # })

                buttons.append({
                    "title": "Cambiar tipo de garras",
                    "payload": '/StartFlow(modificar_tipo_de_garras_del_engaste_del_anillo)'
                })
            
            # Siempre disponible
            buttons.append({
                "title": "Cambiar empaquetado",
                "payload": '/StartFlow(modificar_empaquetado_del_anillo)'
            })
            
            buttons.append({
                "title": "No, gracias",
                "payload": '/inform{"change_option":"finalizar"}'
            })

            dispatcher.utter_message(
                text="¿Deseas realizar otro cambio?",
                buttons=buttons
            )

        except Exception as e:
            print(f"[ERROR] General: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            dispatcher.utter_message(
                text="Error al cargar las opciones de edición."
            )

        # Limpiar TODOS los slots de edición aquí
        return [
            SlotSet("variante_id", None),
            SlotSet("profile_id", None),
            SlotSet("material_id", None),
            SlotSet("pureza_id", None),
            SlotSet("gema_id", None),
            SlotSet("forma_gema_id", None),
            SlotSet("engaste_id", None),
            SlotSet("numero_garras_id", None),
            SlotSet("tipo_garras_id", None),
            SlotSet("box_shape_id", None),
            SlotSet("box_outer_color_id", None),
            SlotSet("box_inner_color_id", None),
            SlotSet("gem_position", None),
            SlotSet("gem_position_for_cut", None),
            SlotSet("gem_position_for_setting", None),
            SlotSet("gem_position_for_claw_number", None),
            SlotSet("gem_position_for_claw_type", None),
            SlotSet("has_gems", None),
            SlotSet("gem_count", None)
        ]
    
# =========================
# MOSTRAR OPCIONES DE EDICIÓN DISPONIBLES DINÁMICAMENTE
# =========================
class ActionAskEditOption(Action):
    def name(self) -> Text:
        return "action_ask_edit_option"

    async def run(self, dispatcher, tracker, domain):
        api_url = os.getenv("API_URL", "https://louv.ovh")
        
        current_ring_id = tracker.get_slot('ring_id')
        if not current_ring_id:
            latest_message = tracker.latest_message
            metadata = latest_message.get('metadata', {})
            current_ring_id = metadata.get('ring_id')

        print(f"[DEBUG] Ring ID para opciones de edición: {current_ring_id}")

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
                    if response.status < 200 or response.status >= 300:
                        dispatcher.utter_message(
                            text="No pude cargar la información del anillo."
                        )
                        return []

                    ring_data = await response.json()

            base_structure = ring_data.get("baseStructure", {})
            
            # Obtener el perfil actual
            current_profile_id = tracker.get_slot('profile_id')
            if not current_profile_id:
                latest_message = tracker.latest_message
                metadata = latest_message.get('metadata', {})
                current_profile_id = metadata.get('profile_id')
            
            if not current_profile_id and base_structure.get("profiles"):
                first_profile = base_structure["profiles"][0]
                profile_obj = first_profile.get('profile', {})
                current_profile_id = profile_obj if isinstance(profile_obj, str) else profile_obj.get('_id', '')

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

            # Obtener la variante actual
            current_variant_id = tracker.get_slot('variante_id')
            if not current_variant_id:
                latest_message = tracker.latest_message
                metadata = latest_message.get('metadata', {})
                current_variant_id = metadata.get('variant_id')

            if not current_variant_id and target_profile.get("variants"):
                current_variant_id = target_profile["variants"][0].get('_id', '')

            variant = None
            for v in target_profile.get("variants", []):
                if v.get('_id') == current_variant_id:
                    variant = v
                    break

            if not variant:
                dispatcher.utter_message(
                    text="No pude encontrar la variante actual del anillo."
                )
                return []

            # Verificar si la variante tiene settings (gemas)
            settings_info = variant.get("settingsInfo", [])
            has_gems = len(settings_info) > 0

            print(f"[DEBUG] Variante tiene gemas: {has_gems}")
            print(f"[DEBUG] Nº de gemas: {len(settings_info)}")

            # Crear botones base (siempre disponibles)
            buttons = [
                {
                    "title": "Perfil",
                    "payload": "Quiero modificar el perfil de mi anillo."
                },
                {
                    "title": "Variante",
                    "payload": "Quiero modificar la variante de mi anillo."
                },
                {
                    "title": "Material",
                    "payload": "Quiero modificar el material de mi anillo."
                },

            ]

            # Añadir opciones relacionadas con gemas solo si la variante las permite
            if has_gems:
                gem_buttons = [
                    {
                        "title": "Gema",
                        "payload": "Quiero modificar la gema de mi anillo."
                    },
                    {
                        "title": "Forma de la gema",
                        "payload": "Quiero modificar la forma de la gema de mi anillo."
                    },
                    {
                        "title": "Engaste",
                        "payload": "Quiero modificar el engaste de mi anillo."
                    },
                    {
                        "title": "Garras del engaste",
                        "payload": "Quiero modificar las garras del engaste de mi anillo."
                    }
                ]
                buttons.extend(gem_buttons)

            buttons.append({
                "title": "Cambiar empaquetado",
                "payload": '/StartFlow(modificar_empaquetado_del_anillo)'
            })
            
            buttons.append({
                "title": "Nada, gracias",
                "payload": '/inform{"change_option":"finalizar"}'
            })

            dispatcher.utter_message(
                text="¿Qué parte de su anillo desea modificar? Puede seleccionar uno de los botones o escribirlo manualmente.",
                buttons=buttons,
                metadata={"rephrase": False}
            )

            # Limpiar slots de ediciones anteriores
            return [
                SlotSet("variante_id", None),
                SlotSet("gem_position", None),
                SlotSet("gem_position_for_cut", None),
                SlotSet("gem_position_for_setting", None),
                SlotSet("gem_position_for_claw_number", None),
                SlotSet("gem_position_for_claw_type", None)
            ]

        except Exception as e:
            print(f"[ERROR] General: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            dispatcher.utter_message(
                text="Error al verificar las opciones de edición disponibles."
            )
            return []
        
class ActionResetFormaGemaSlots(Action):
    def name(self) -> Text:
        return "action_reset_forma_gema_slots"

    async def run(self, dispatcher, tracker, domain):
        print("[DEBUG] Limpiando slots de forma de gema al inicio del flow")
        
        # Limpiar TODOS los slots relacionados con este flow
        return [
            SlotSet("gem_position_for_cut", None),
            SlotSet("forma_gema_id", None),
            SlotSet("has_gems", None),
            SlotSet("gem_count", None)
        ]
    
class ActionResetEngasteSlots(Action):
    def name(self) -> Text:
        return "action_reset_engaste_slots"

    async def run(self, dispatcher, tracker, domain):
        print("[DEBUG] Limpiando slots de engaste al inicio del flow")
        
        return [
            SlotSet("gem_position_for_setting", None),
            SlotSet("engaste_id", None),
            SlotSet("has_gems", None),
            SlotSet("gem_count", None)
        ]