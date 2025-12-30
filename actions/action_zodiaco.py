from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import re

class ActionDeterminarSignoZodiacal(Action):
    def name(self) -> Text:
        return "action_determinar_signo_zodiacal"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        fecha_str = tracker.get_slot("fecha_nacimiento")
        
        if not fecha_str:
            return [SlotSet("signo_zodiacal", None)]
        
        # Convertir a minúsculas para facilitar el parsing
        fecha_str = fecha_str.lower().strip()
        
        try:
            dia, mes = self.extraer_fecha(fecha_str)
            
            if dia and mes:
                # Determinar el signo zodiacal
                signo = self.obtener_signo(dia, mes)
                return [SlotSet("signo_zodiacal", signo)]
            else:
                return [SlotSet("signo_zodiacal", None)]
            
        except Exception as e:
            return [SlotSet("signo_zodiacal", None)]
    
    def extraer_fecha(self, fecha_str: Text) -> tuple:
        """Extrae día y mes de diferentes formatos de fecha"""
        
        # Diccionario de meses en español
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'ago': 8,
            'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dic': 12
        }
        
        # Formato: 20/09 o 20-09
        if "/" in fecha_str or "-" in fecha_str:
            separador = "/" if "/" in fecha_str else "-"
            partes = fecha_str.split(separador)
            if len(partes) >= 2:
                dia = int(partes[0])
                mes = int(partes[1])
                return dia, mes
        
        # Formato: "20 de septiembre" o "20 septiembre"
        for mes_nombre, mes_num in meses.items():
            if mes_nombre in fecha_str:
                # Buscar el número del día
                numeros = re.findall(r'\d+', fecha_str)
                if numeros:
                    dia = int(numeros[0])
                    return dia, mes_num
        
        # Formato: solo números separados por espacios "20 9"
        numeros = re.findall(r'\d+', fecha_str)
        if len(numeros) >= 2:
            dia = int(numeros[0])
            mes = int(numeros[1])
            return dia, mes
        
        return None, None
    
    def obtener_signo(self, dia: int, mes: int) -> Text:
        if (mes == 3 and dia >= 21) or (mes == 4 and dia <= 19):
            return "aries"
        elif (mes == 4 and dia >= 20) or (mes == 5 and dia <= 20):
            return "tauro"
        elif (mes == 5 and dia >= 21) or (mes == 6 and dia <= 20):
            return "geminis"
        elif (mes == 6 and dia >= 21) or (mes == 7 and dia <= 22):
            return "cancer"
        elif (mes == 7 and dia >= 23) or (mes == 8 and dia <= 22):
            return "leo"
        elif (mes == 8 and dia >= 23) or (mes == 9 and dia <= 22):
            return "virgo"
        elif (mes == 9 and dia >= 23) or (mes == 10 and dia <= 22):
            return "libra"
        elif (mes == 10 and dia >= 23) or (mes == 11 and dia <= 21):
            return "escorpio"
        elif (mes == 11 and dia >= 22) or (mes == 12 and dia <= 21):
            return "sagitario"
        elif (mes == 12 and dia >= 22) or (mes == 1 and dia <= 19):
            return "capricornio"
        elif (mes == 1 and dia >= 20) or (mes == 2 and dia <= 18):
            return "acuario"
        elif (mes == 2 and dia >= 19) or (mes == 3 and dia <= 20):
            return "piscis"
        else:
            return None