import MySQLdb
from werkzeug.security import generate_password_hash

# Configura tus datos de conexión
db = MySQLdb.connect(
    host="192.168.56.101",
    user="root",
    passwd="sistemas2024",
    db="EntreCOL+"
)

cursor = db.cursor()

# Datos del usuario jefe
nombre_usuario = 'Cristiano Ronaldo'
codigo = '1'
contraseña = '1234'
role = 'jefe'

# Encriptar la contraseña
password_hash = generate_password_hash(contraseña)

# Insertar en la tabla usuarios
try:
    cursor.execute(
        "INSERT INTO usuarios (nombre_usuario, codigo, contraseña, role) VALUES (%s, %s, %s, %s)",
        (nombre_usuario, codigo, password_hash, role)
    )
    db.commit()
    print("Usuario jefe creado exitosamente.")
except Exception as e:
    db.rollback()
    print(f"Error al crear el usuario jefe: {e}")

db.close()
