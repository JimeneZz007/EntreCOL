from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors
import re
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key')

# Configuración de la base de datos
app.config['MYSQL_HOST'] = '192.168.56.101'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'sistemas2024'
app.config['MYSQL_DB'] = 'EntreCOL+'

# Inicializar MySQL
mysql = MySQL(app)

# Página principal de bienvenida
@app.route('/')
def bienvenido():
    return render_template('inicio/index.html')

# Página para explorar (de momento vacía)
@app.route('/bienvenido/')
def explore():
    return render_template('inicio/peliculas.html')

@app.route('/iniciar_sesion/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and 'nombre_usuario' in request.form and 'contraseña' in request.form:
        nombre_usuario = request.form['nombre_usuario']
        contraseña = request.form['contraseña']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM usuarios WHERE nombre_usuario = %s', [nombre_usuario])
        usuarios = cursor.fetchone()

        if usuarios and check_password_hash(usuarios['contraseña'], contraseña):
            session['loggedin'] = True
            session['id'] = usuarios['id']
            session['nombre_usuario'] = usuarios['nombre_usuario']
            session['role'] = usuarios['role']

            if usuarios['role'] == 'jefe':
                return redirect(url_for('inicio'))  # Página del jefe
            else:
                return redirect(url_for('pagina_empleado'))  # Página diferente para empleados
        else:
            flash("Usuario o contraseña incorrecta", "danger")

    return render_template('auth/login.html', title="Inicia Sesión")

@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if 'loggedin' not in session or session.get('role') != 'jefe':
        flash("Solo el jefe puede registrar nuevos usuarios.", "danger")
        return redirect(url_for('inicio'))

    if request.method == 'POST' and all(field in request.form for field in ('nombre_usuario', 'contraseña', 'codigo', 'role')):
        nombre_usuario = request.form['nombre_usuario']
        contraseña = request.form['contraseña'] 
        codigo = request.form['codigo']
        role = request.form['role']  # 'empleado' o 'jefe'

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM usuarios WHERE nombre_usuario = %s', [nombre_usuario])
        cuenta = cursor.fetchone()

        if cuenta:
            flash("Esta cuenta ya existe!", "danger")
        elif not re.match(r'[0-9]+', codigo):
            flash("Codigo inválido!", "danger")
        elif not re.match(r'[A-Za-z0-9]+', nombre_usuario):
            flash("El nombre de usuario solo debe contener letras y números.", "danger")
        else:
            hashed_password = generate_password_hash(contraseña)
            cursor.execute('INSERT INTO usuarios (nombre_usuario, codigo, contraseña, role) VALUES (%s, %s, %s, %s)',
                           (nombre_usuario, codigo, hashed_password, role))
            mysql.connection.commit()
            flash("Usuario registrado exitosamente!", "success")
            return redirect(url_for('inicio'))
    elif request.method == 'POST':
        flash("Por favor completa todos los campos.", "danger")

    return render_template('auth/registrar.html', title="Registrar Empleados")

# Ruta de home
@app.route('/inicio')
def inicio():
    if 'loggedin' in session:
        return render_template('home/inicio.html', username=session['nombre_usuario'], title="Inicio")
    return redirect(url_for('inicio'))

# Ruta del perfil
@app.route('/perfil')
def perfil():
    if 'loggedin' in session:
        return render_template('auth/perfil.html', username=session['nombre_usuario'], title="Tu Perfil")
    return redirect(url_for('login'))

# Ruta pagina Empleado
@app.route('/pagina_empleado')
def pagina_empleado():
    if 'loggedin' in session and session['role'] != 'jefe':
        return render_template('auth/empleado.html', username=session['nombre_usuario'], title="Bienvenido Empleado")
    return redirect(url_for('login'))


# Ruta para cerrar sesión
@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.clear()
    return redirect(url_for('login'))


# Ejecutar la app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)