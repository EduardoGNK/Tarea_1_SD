import pymongo
import pandas as pd  # Para visualizar los datos en forma de tabla
import os

# Configuración de MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "waze_data")
COLLECTION_NAME = "waze_events"

def visualize_data_from_db():
    """Visualiza los datos de la base de datos en forma de tabla y muestra el número total de eventos."""
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Obtiene todos los documentos de la colección
    data = list(collection.find())

    if not data:
        print("No hay datos en la base de datos.")
        return

    # Convierte los datos a un DataFrame de pandas
    df = pd.DataFrame(data)

    # Muestra los datos en forma de tabla
    print(df.head(20))  # Muestra las primeras 20 filas

    # Muestra el número total de eventos
    total_events = len(data)
    print(f"Número total de eventos en la base de datos: {total_events}")

if __name__ == "__main__":
    visualize_data_from_db()