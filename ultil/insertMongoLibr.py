import json
import pymongo
import sys
from pymongo.errors import ConnectionFailure, OperationFailure

def importar_json_a_mongodb(archivo_json, uri_mongodb, base_datos, coleccion):
    try:
        with open(archivo_json, 'r', encoding='utf-8') as file:
            datos = json.load(file)
        
        if not isinstance(datos, list) and not isinstance(datos, dict):
            print(f"Error: El archivo JSON debe contener una lista de documentos o un documento.")
            return False
        

        if isinstance(datos, dict):
            datos = [datos]  
        
        cliente = pymongo.MongoClient(uri_mongodb)
        

        db = cliente[base_datos]
        col = db[coleccion]
        

        if len(datos) == 1:
            resultado = col.insert_one(datos[0])
            print(f"Se ha insertado 1 documento con ID: {resultado.inserted_id}")
        else:
            resultado = col.insert_many(datos)
            print(f"Se han insertado {len(resultado.inserted_ids)} documentos")
        
        cliente.close()
        return True
        
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{archivo_json}'")
    except json.JSONDecodeError:
        print(f"Error: El archivo '{archivo_json}' no contiene un JSON válido")
    except ConnectionFailure:
        print("Error: No se pudo conectar a MongoDB. Verifique la URI de conexión.")
    except OperationFailure as e:
        print(f"Error en la operación de MongoDB: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")
    
    return False

if __name__ == "__main__":

    archivo_json = "ultil\Books.json"
    uri_mongodb = "mongodb://192.168.56.101:27017/"
    base_datos = "Entrecol_multimedia"
    coleccion = "libros"
    

    importar_json_a_mongodb(archivo_json, uri_mongodb, base_datos, coleccion)