README - Sistema de Análisis de Tráfico con Caché Distribuido
📌 Descripción del Proyecto
Sistema distribuido para análisis de datos de tráfico en la Región Metropolitana de Santiago, implementando:

Extracción de datos de Waze

Almacenamiento en MongoDB

Sistema de caché con Redis

Simulaciones de políticas de caché (LRU, LFU)

Visualización de resultados

🛠 Requisitos Previos
Docker Desktop (con WSL 2 habilitado en Windows)

PowerShell (o terminal compatible)

8GB+ de RAM recomendados

🚀 Instrucciones de Ejecución
1. Configuración Inicial
powershell
# Clonar repositorio
cd Tarea1-SD-master
2. Iniciar Servicios con Docker
powershell
# Levantar contenedores (MongoDB + Redis)
docker-compose up -d mongo redis

# Verificar estado
docker ps
3. Poblar la Base de Datos (Opcional)
powershell
# Ejecutar scraper para obtener datos actualizados (requiere Chromium)
docker-compose run --rm scraper python scraper.py
4. Ejecutar Simulaciones de Caché
powershell
# Ejecutar todas las combinaciones de pruebas
docker-compose run --rm query python cache_query.py

# Alternativa: Ejecutar prueba específica
docker-compose run --rm query python -c "
from cache_query import run_simulation; 
run_simulation(document_ids, collection, 'zipf', 'lfu')"
5. Generar Análisis y Gráficos
powershell
docker-compose run --rm query python analyze_results.py
📊 Estructura de Archivos
├── docker-compose.yml          # Configuración de servicios
├── Dockerfile                  # Entorno para el scraper
├── scraper/
│   ├── scraper.py              # Extracción de datos de Waze
├── cache_query.py              # Simulador de políticas de caché
├── analyze_results.py          # Generador de visualizaciones
├── visualization_output/       # Gráficos generados (se crea automáticamente)
🔍 Parámetros Configurables
En cache_query.py:

python
QUERY_COUNT = 1000      # Número de consultas por simulación
CACHE_CAPACITY = 200    # Tamaño máximo del caché
ACCESS_PATTERNS = {     # Patrones de acceso
    "uniform": "Distribución uniforme",
    "zipf": "Distribución Zipf (80-20)"
}
📦 Datos de Ejemplo
El sistema incluye:

15,000+ registros reales de tráfico (pre-cargados)

Conjunto de datos de prueba en /sample_data/

🧪 Pruebas Realizadas
Comparación de políticas de caché:

LRU vs LFU vs Simple

Patrones de acceso:

Uniforme vs Zipf (distribución 80-20)

Métricas:

Tasa de aciertos (hit rate)

Latencia promedio

📄 Resultados Esperados
Gráficos en visualization_output/:

hit_rate_analysis.png

avg_latency_analysis.png

Archivos JSON con resultados crudos:

results_zipf_lru.json

results_uniform_lfu.json

Consideraciones:
tuve un problema y es que al scrapear lo hice desde mi vscode y no desde mi docker por lo que hay códigos que no se usan pq los usé para pasarlos a mi docker, que igual me costó jdksjdkd
