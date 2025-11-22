# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher

# class ActionLLMFallback(Action):
#     def name(self):
#         return "action_llm_fallback"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: dict):

#         # Enviar el input a la NLG (que será el LLM)
#         dispatcher.utter_message(response="utter_llm_fallback")
#         return []
