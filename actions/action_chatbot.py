from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import UserUttered

# class ActionClarifyFlows(Action):
    
#     def name(self) -> Text:
#         return "action_clarify_flows"
    
#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict[Text, Any]]:
        
#         # Mapeo de nombres técnicos de flows a títulos amigables
#         flow_titles = {
#             "que_gema_es_mas_resistente": "¿Cuál es la gema más resistente en general?",
#             "cual_de_estas_gemas_es_mas_resistente": "Comparar dos gemas específicas",
#             "teneis_esta_gema_en_concreto": "¿Tenéis una gema en concreto?",
#             "que_formas_teneis": "¿Qué formas o estructuras tenéis?",
#         }
        
#         # Obtener los flows que necesitan clarificación desde el tracker
#         # Rasa almacena esta información en los metadatos cuando hay ambigüedad
#         metadata = tracker.latest_message.get("metadata", {})
#         candidate_flows = metadata.get("candidate_flows", [])
        
#         # Si no hay flows candidatos en metadata, usar un fallback
#         if not candidate_flows:
#             # Puedes obtenerlos de otra forma o usar valores por defecto
#             candidate_flows = [
#                 "que_gema_es_mas_resistente",
#                 "cual_de_estas_gemas_es_mas_resistente"
#             ]
        
#         # Crear botones dinámicamente
#         buttons = []
#         for flow_name in candidate_flows:
#             title = flow_titles.get(flow_name, flow_name)
#             buttons.append({
#                 "title": title,
#                 "payload": f'/start_flow{{"flow":"{flow_name}"}}'
#             })
        
#         # Enviar mensaje con botones
#         dispatcher.utter_message(
#             text="Puedo ayudarte, pero necesito más información. ¿Cuál de estas opciones prefieres?",
#             buttons=buttons
#         )
        
#         return []