#!/usr/bin/env python3
from pathlib import Path
import json
from typing import Dict, List, Union, Any

class JsonInspector:
    """Clase para explorar y mostrar contenido de archivos JSON"""
    
    def __init__(self, search_dir: str = '.'):
        self.search_dir = Path(search_dir)
        
    def find_json_files(self) -> List[Path]:
        """Encuentra todos los archivos JSON en el directorio especificado"""
        return list(self.search_dir.glob('*.json'))
    
    def display_json_structure(self, file_path: Path) -> None:
        """Muestra la estructura del archivo JSON de forma amigable"""
        try:
            with open(file_path, 'r', encoding='utf-8') as json_file:
                content = json.load(json_file)
                
            print(f"\n{'*' * 20} {file_path.name} {'*' * 20}")
            
            if isinstance(content, dict):
                self._analyze_dict(content)
            elif isinstance(content, list):
                self._analyze_list(content)
            else:
                print(f"Tipo de contenido no estándar: {type(content).__name__}")
                
        except json.JSONDecodeError:
            print(f"❌ El archivo {file_path.name} no tiene formato JSON válido")
        except Exception as err:
            print(f"❌ Error procesando {file_path.name}: {str(err)}")
    
    def _analyze_dict(self, data: Dict[str, Any]) -> None:
        """Analiza y muestra información sobre un diccionario JSON"""
        key_count = len(data)
        print(f"📋 Estructura: Diccionario con {key_count} clave(s)")
        print(f"🔑 Claves disponibles: {', '.join(data.keys())}")
        
        # Muestra un extracto de valores si no son demasiados
        if key_count <= 5:
            for key, value in data.items():
                print(f"  - {key}: {self._summarize_value(value)}")
    
    def _analyze_list(self, data: List[Any]) -> None:
        """Analiza y muestra información sobre una lista JSON"""
        item_count = len(data)
        print(f"📋 Estructura: Lista con {item_count} elemento(s)")
        
        if item_count > 0:
            print("📌 Primer elemento:")
            if isinstance(data[0], dict):
                # Muestra el primer elemento formateado si es un diccionario
                print(json.dumps(data[0], indent=2, ensure_ascii=False))
            else:
                # Simplemente muestra el primer elemento si es de otro tipo
                print(f"  {self._summarize_value(data[0])}")
    
    def _summarize_value(self, value: Any) -> str:
        """Genera un resumen legible de un valor JSON"""
        if isinstance(value, dict):
            return f"{{diccionario con {len(value)} clave(s)}}"
        elif isinstance(value, list):
            return f"[lista con {len(value)} elemento(s)]"
        elif isinstance(value, str) and len(value) > 50:
            return f'"{value[:47]}..."'
        else:
            return str(value)
            
    def run(self) -> None:
        """Ejecuta el análisis completo de archivos JSON"""
        json_files = self.find_json_files()
        
        if not json_files:
            print("No se encontraron archivos JSON en el directorio actual.")
            return
            
        print(f"🔍 Se encontraron {len(json_files)} archivo(s) JSON:")
        for idx, file_path in enumerate(json_files, 1):
            print(f"{idx}. {file_path.name}")
            
        for file_path in json_files:
            self.display_json_structure(file_path)
            
        print("\n✅ Análisis de archivos JSON completado")


if __name__ == "__main__":
    inspector = JsonInspector()
    inspector.run()