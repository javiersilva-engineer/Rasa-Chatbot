from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from pymongo import MongoClient
import os

# Función para obtener la conexión a MongoDB
def get_mongodb_connection():
    """Retorna la conexión a tu base de datos de Materials"""
    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017/')
    mongo_user = os.getenv('MONGO_USER', 'tu_usuario')
    mongo_password = os.getenv('MONGO_PASSWORD', 'tu_contraseña')
    mongo_db = os.getenv('MONGO_DB', 'tu_base_de_datos')
    
    # Conexión con autenticación
    client = MongoClient(
        mongo_url,
        username=mongo_user,
        password=mongo_password,
        authSource='admin'  # o la base de datos donde está el usuario
    )
    return client[mongo_db]
