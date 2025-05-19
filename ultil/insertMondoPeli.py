import pymongo
import sys
from pymongo.errors import ConnectionFailure, OperationFailure

def importar_dat_a_mongodb(archivo_dat, uri_mongodb, base_datos, coleccion):
    try:
        documentos = []
        
        with open(archivo_dat, 'r', encoding='utf-8') as file:
            for linea in file:
                linea = linea.strip()
                if not linea:  
                    continue
                
                partes = linea.split('::')
                if len(partes) != 3:
                    print(f"Advertencia: Formato incorrecto en línea, se esperan 3 partes: {linea}")
                    continue
                
                movie_id, titulo_con_anio, generos = partes
                
                anio = None
                if '(' in titulo_con_anio and ')' in titulo_con_anio:
                    ultimo_parentesis_abierto = titulo_con_anio.rfind('(')
                    ultimo_parentesis_cerrado = titulo_con_anio.rfind(')')
                    
                    if ultimo_parentesis_abierto < ultimo_parentesis_cerrado:

                        posible_anio = titulo_con_anio[ultimo_parentesis_abierto+1:ultimo_parentesis_cerrado].strip()
                        if posible_anio.isdigit():
                            anio = int(posible_anio)
                            titulo = titulo_con_anio[:ultimo_parentesis_abierto].strip()
                        else:
                            titulo = titulo_con_anio
                    else:
                        titulo = titulo_con_anio
                else:
                    titulo = titulo_con_anio
                

                lista_generos = generos.split('|') if generos else []
                

                documento = {
                    'id': int(movie_id) if movie_id.isdigit() else movie_id,
                    'titulo': titulo,
                    'titulo_original': titulo_con_anio,
                    'generos': lista_generos
                }
                
                if anio:
                    documento['anio'] = anio
                
                documentos.append(documento)

        cliente = pymongo.MongoClient(uri_mongodb)     

        db = cliente[base_datos]
        col = db[coleccion]
        

        resultado = col.insert_many(documentos)
        print(f"Se han insertado {len(resultado.inserted_ids)} documentos")
        
        cliente.close()
        return True
        
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{archivo_dat}'")
    except ConnectionFailure:
        print("Error: No se pudo conectar a MongoDB. Verifique la URI de conexión.")
    except OperationFailure as e:
        print(f"Error en la operación de MongoDB: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")
    
    return False

if __name__ == "__main__":

    archivo_dat = "ultil\movies.dat"
    uri_mongodb = "mongodb://192.168.56.101:27017/"
    base_datos = "Entrecol_multimedia"
    coleccion = "peliculas"
    

    importar_dat_a_mongodb(archivo_dat, uri_mongodb, base_datos, coleccion)