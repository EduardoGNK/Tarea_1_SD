import requests
import pymongo
import os
import time
import folium
import pandas as pd
from datetime import datetime
from pymongo.errors import ServerSelectionTimeoutError

# Configuración del servicio de mapa en vivo de Waze
WAZE_ENDPOINT = "https://www.waze.com/live-map/api/georss"

# Coordenadas geográficas de la Región Metropolitana de Santiago
SANTIAGO_REGION = {
    "north": -33.079295,
    "south": -33.924396,
    "west": -71.371765,
    "east": -70.240173,
}

# Subdivisiones para optimizar las peticiones
GRID_SIZE = 6

# Variables de conexión a la base de datos
DB_CONNECTION = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DATABASE = os.getenv("DB_NAME", "traffic_data")
EVENTS_COLLECTION = "waze_incidents"

def check_mongodb_connection(connection_uri, max_wait=30):
    """Verifica y espera hasta que la conexión con MongoDB esté disponible."""
    connection = pymongo.MongoClient(connection_uri, serverSelectionTimeoutMS=1000)
    start_time = time.time()
    
    while True:
        try:
            connection.admin.command("ping")
            print("✓ MongoDB connection established successfully.")
            return
        except ServerSelectionTimeoutError:
            if time.time() - start_time > max_wait:
                print("✗ Timeout waiting for MongoDB connection.")
                raise
            print("⌛ Waiting for MongoDB connection...")
            time.sleep(1)

def initialize_database():
    """Establece conexión con la base de datos MongoDB."""
    client = pymongo.MongoClient(DB_CONNECTION)
    database = client[DATABASE]
    return database

def create_geographic_grid(region, divisions):
    """Divide la región en una cuadrícula para peticiones más eficientes."""
    lat_step = (region["north"] - region["south"]) / divisions
    lon_step = (region["east"] - region["west"]) / divisions
    
    grid_cells = []
    for i in range(divisions):
        for j in range(divisions):
            cell = {
                "north": region["north"] - (i * lat_step),
                "south": region["north"] - ((i + 1) * lat_step),
                "west": region["west"] + (j * lon_step),
                "east": region["west"] + ((j + 1) * lon_step),
            }
            grid_cells.append(cell)
    return grid_cells

def get_waze_traffic_data(north, south, west, east):
    """Consulta la API de Waze para obtener datos de tráfico."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    query_params = {
        "top": north,
        "bottom": south,
        "left": west,
        "right": east,
        "env": "row",
        "types": "alerts,traffic,users",
    }
    
    try:
        response = requests.get(WAZE_ENDPOINT, headers=headers, params=query_params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        print(f"API Request Error: {error}")
        return None

def extract_traffic_events(raw_data):
    """Transforma los datos crudos de la API en eventos procesados."""
    events_list = []
    
    if not raw_data:
        print("No data found in API response.")
        return events_list
    
    # Procesar alertas (accidents, hazards, police, etc)
    for alert in raw_data.get('alerts', []):
        timestamp = datetime.fromtimestamp(alert.get('pubMillis', 0) / 1000.0)
        events_list.append({
            'event_type': 'Alert',
            'event_subtype': alert.get('type', 'unknown'),
            'location': {
                'lat': alert.get('location', {}).get('y'),
                'lon': alert.get('location', {}).get('x')
            },
            'time_reported': timestamp.isoformat(),
            'details': alert,
            'collection_timestamp': datetime.now().isoformat()
        })
    
    # Procesar congestiones viales
    for jam in raw_data.get('jams', []):
        timestamp = datetime.fromtimestamp(jam.get('pubMillis', 0) / 1000.0)
        events_list.append({
            'event_type': 'Jam',
            'event_subtype': 'traffic_jam',
            'severity': jam.get('severity', 0),
            'delay': jam.get('delay', 0),
            'street': jam.get('street', 'Unknown'),
            'time_reported': timestamp.isoformat(),
            'details': jam,
            'collection_timestamp': datetime.now().isoformat()
        })
    
    return events_list

def store_events(database, events):
    """Almacena los eventos en la base de datos MongoDB."""
    if not events:
        print("No events to save.")
        return 0
    
    collection = database[EVENTS_COLLECTION]
    saved_count = 0
    
    for event in events:
        try:
            collection.insert_one(event)
            saved_count += 1
        except Exception as error:
            print(f"Error saving event: {error}")
    
    return saved_count

def display_sample_data():
    """Muestra una muestra de los datos almacenados para verificación."""
    client = pymongo.MongoClient(DB_CONNECTION)
    try:
        db = client[DATABASE]
        collection = db[EVENTS_COLLECTION]
        data_sample = list(collection.find().limit(20))
        
        if not data_sample:
            print("Database is empty.")
            return
        
        df = pd.DataFrame(data_sample)
        print("\nSample of collected data:")
        print(df[['event_type', 'time_reported']].head(10))
        print(f"\nTotal events in database: {collection.count_documents({})}")
    finally:
        client.close()

def main():
    """Función principal que coordina el proceso de recolección de datos."""
    print("🚀 Starting Waze traffic data collection for Santiago Metropolitan Region")
    
    # Verificar conexión a MongoDB
    check_mongodb_connection(DB_CONNECTION)
    
    # Inicializar base de datos
    db = initialize_database()
    
    # Crear cuadrícula geográfica
    print(f"Dividing region into {GRID_SIZE}x{GRID_SIZE} grid for optimized collection")
    grid = create_geographic_grid(SANTIAGO_REGION, GRID_SIZE)
    
    # Recolectar datos por cada celda de la cuadrícula
    total_events_collected = 0
    
    for idx, cell in enumerate(grid):
        print(f"📍 Collecting data from grid cell {idx+1}/{len(grid)}")
        
        traffic_data = get_waze_traffic_data(
            north=cell["north"],
            south=cell["south"],
            west=cell["west"],
            east=cell["east"]
        )
        
        if traffic_data:
            events = extract_traffic_events(traffic_data)
            saved = store_events(db, events)
            total_events_collected += saved
            print(f"   ✓ {saved} events saved from this grid cell")
        else:
            print("   ✗ No data retrieved for this grid cell")
        
        # Pausa para evitar sobrecarga en la API
        time.sleep(1.5)
    
    print(f"\n✅ Collection completed. Total events collected: {total_events_collected}")
    display_sample_data()

if __name__ == "__main__":
    main()