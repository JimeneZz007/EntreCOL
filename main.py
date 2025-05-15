from flask import Flask, render_template, request, redirect, url_for, session, flash,send_file
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors
import re
import os
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from io import BytesIO
from pymongo import MongoClient


# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key')

# Configuración de la base de datos
app.config['MYSQL_HOST'] = '192.168.56.101'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'sistemas2024'
app.config['MYSQL_DB'] = 'EntreCOL+'

# Configuración de la base de datos(Mongo)
client = MongoClient("mongodb://192.168.56.101:27017/")  
db = client["entrecol_multimedia"] 
peliculas_collection = db["peliculas"]
libros_collection = db["libros"]

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

# Pagina de inicio de sesion
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
            session['codCreden'] = usuarios['codCreden']
            session['nombre_usuario'] = usuarios['nombre_usuario']
            session['role'] = usuarios['role']

            if usuarios['role'] == 'jefe':
                return redirect(url_for('inicio'))  # Página del jefe
            else:
                return redirect(url_for('pagina_empleado'))  # Página diferente para empleados
        else:
            flash("Usuario o contraseña incorrecta", "danger")

    return render_template('auth/login.html', title="Inicia Sesión")

# Pagina de Resgistrar Usuarios
@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if 'loggedin' not in session or session.get('role') != 'jefe':
        flash("Solo el jefe puede registrar nuevos usuarios.", "danger")
        return redirect(url_for('inicio'))

    if request.method == 'POST' and all(field in request.form for field in ('nombre_usuario', 'contraseña', 'role')):
        nombre_usuario = request.form['nombre_usuario']
        contraseña = request.form['contraseña'] 
        role = request.form['role']  # 'empleado' o 'jefe'

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM usuarios WHERE nombre_usuario = %s', [nombre_usuario])
        cuenta = cursor.fetchone()

        if cuenta:
            flash("Esta cuenta ya existe!", "danger")
        elif not re.match(r'[A-Za-z0-9]+', nombre_usuario):
            flash("El nombre de usuario solo debe contener letras y números.", "danger")
        else:
            hashed_password = generate_password_hash(contraseña)
            cursor.execute('INSERT INTO usuarios (nombre_usuario, contraseña, role) VALUES (%s, %s, %s)',
                           (nombre_usuario, hashed_password, role))
            mysql.connection.commit()
            flash("Usuario registrado exitosamente!", "success")
            return redirect(url_for('inicio'))
    elif request.method == 'POST':
        flash("Por favor completa todos los campos.", "danger")

    return render_template('auth/registrar.html', title="Registrar Empleados")

# Pagina de editar usuarios
@app.route('/editar_usuario/<int:codCreden>', methods=['GET', 'POST'])
def editar_usuario(codCreden):
    if 'loggedin' in session and session['role'] == 'jefe':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        if request.method == 'POST':
            nuevo_usuario = request.form['nombre_usuario']
            nuevo_role = request.form['role']
            nueva_contraseña = request.form.get('nueva_contraseña')

            if nueva_contraseña:  # Si se ingresa nueva contraseña
                hashed_password = generate_password_hash(nueva_contraseña)
                cursor.execute("""
                    UPDATE usuarios 
                    SET nombre_usuario = %s, role = %s, contraseña = %s 
                    WHERE codCreden = %s
                """, (nuevo_usuario, nuevo_role, hashed_password, codCreden))
            else:  # Solo se actualiza nombre y rol
                cursor.execute("""
                    UPDATE usuarios 
                    SET nombre_usuario = %s, role = %s 
                    WHERE codCreden = %s
                """, (nuevo_usuario, nuevo_role, codCreden))

            mysql.connection.commit()
            flash("Usuario actualizado correctamente", "success")
            return redirect(url_for('inicio'))

        # GET: Mostrar datos actuales
        cursor.execute('SELECT * FROM usuarios WHERE codCreden = %s', [codCreden])
        usuario = cursor.fetchone()
        return render_template('auth/editar_usuario.html', usuario=usuario, title="Editar Usuario")

    flash("Acceso no autorizado", "danger")
    return redirect(url_for('inicio'))


# Ruta de home
@app.route('/inicio')
def inicio():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT codCreden, nombre_usuario, role FROM usuarios')
        usuarios = cursor.fetchall()
        return render_template('home/inicio.html', username=session['nombre_usuario'], usuarios=usuarios, title="Inicio")
    return redirect(url_for('login'))


# Ruta del perfil
@app.route('/perfil')
def perfil():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT 
                u.nombre_usuario, u.role,
                e.nombre AS nombre_empleado,
                fechaIngreso,
                c.nombre AS nombre_cargo,
                d.nombre AS nombre_dependencia,
                s.eps, s.arl, s.pension
            FROM 
                usuarios u
            JOIN 
                empleado e ON u.codCreden = e.codCreden
            JOIN 
                cargo c ON e.codCargo = c.codCargo
            JOIN 
                dependencia d ON c.codDep  = d.codDep
            JOIN
                seguridadSocial s ON e.codSeg = s.codSeg
            WHERE 
                u.codCreden = %s
        """, [session['codCreden']])
        perfil = cursor.fetchone()
        return render_template('auth/perfil.html', perfil=perfil, title="Tu Perfil")
    return redirect(url_for('login'))

@app.route('/editar_perfil', methods=['GET', 'POST'])
def editar_perfil():
    if 'loggedin' in session and session['role'] == 'jefe':
        # Obtener los datos actuales del perfil
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT 
                u.nombre_usuario, u.role,
                e.nombre AS nombre_empleado,
                fechaIngreso,
                c.nombre AS nombre_cargo,
                d.nombre AS nombre_dependencia,
                s.eps, s.arl, s.pension
            FROM 
                usuarios u
            JOIN 
                empleado e ON u.codCreden = e.codCreden
            JOIN 
                cargo c ON e.codCargo = c.codCargo
            JOIN 
                dependencia d ON c.codDep = d.codDep
            JOIN
                seguridadSocial s ON e.codSeg = s.codSeg
            WHERE 
                u.codCreden = %s
        """, [session['codCreden']])
        perfil = cursor.fetchone()

        # Si se envían los datos del formulario, actualizar la base de datos
        if request.method == 'POST':
            nombre_empleado = request.form['nombre_empleado']
            fecha_ingreso = request.form['fecha_ingreso']

            cursor.execute("""
                UPDATE empleado SET 
                    nombre = %s, 
                    fechaIngreso = %s 
                WHERE codCreden = %s
            """, (nombre_empleado, fecha_ingreso, session['codCreden']))

            mysql.connection.commit()
            flash("Perfil actualizado exitosamente!", "success")
            return redirect(url_for('perfil'))

        return render_template('auth/editar_perfil.html', perfil=perfil, title="Editar Perfil")
    return redirect(url_for('login'))


# Ruta pagina Empleado
@app.route('/pagina_empleado')
def pagina_empleado():
    if 'loggedin' in session and session['role'] != 'jefe':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT 
                u.nombre_usuario, u.role,
                e.nombre AS nombre_empleado,
                fechaIngreso,
                c.nombre AS nombre_cargo,
                d.nombre AS nombre_dependencia,
                s.eps, s.arl, s.pension
            FROM 
                usuarios u
            JOIN 
                empleado e ON u.codCreden = e.codCreden
            JOIN 
                cargo c ON e.codCargo = c.codCargo
            JOIN 
                dependencia d ON c.codDep  = d.codDep
            JOIN
                seguridadSocial s ON e.codSeg = s.codSeg
            WHERE 
                u.codCreden = %s
        """, [session['codCreden']])
        perfil = cursor.fetchone()

        return render_template("auth/empleado.html",perfil=perfil, title="Tu Perfil de Empleado")
    return redirect(url_for('login'))

# Generar PDF Nomina
@app.route('/descargar_nomina')
def descargar_nomina():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    codCreden = session['codCreden']

    # Obtener codEmp y nombre del empleado actual
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT codEmp FROM empleado WHERE codCreden = %s", (codCreden,))
    emp = cursor.fetchone()

    if not emp:
        flash("No se encontró el empleado.", "danger")
        return redirect(url_for('pagina_empleado'))

    codEmp = emp['codEmp']

    # Obtener última nómina del empleado incluyendo nombre
    cursor.execute("""
        SELECT n.*, e.nombre AS nombre_empleado
        FROM nomina n
        JOIN empleado e ON n.codEmp = e.codEmp
        WHERE n.codEmp = %s
        ORDER BY n.fechaNomina DESC
        LIMIT 1;
    """, (codEmp,))
    nomina = cursor.fetchone()
    cursor.close()

    if not nomina:
        flash("No se encontró información de nómina.", "warning")
        return redirect(url_for('pagina_empleado'))

    # Crear PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(100, 800, f"Nómina de {nomina['nombre_empleado']}")

    pdf.setFont("Helvetica", 12)
    y = 760
    espacio = 25

    datos_ordenados = [
        ("Nombre del Empleado", nomina['nombre_empleado']),
        ("Código del Empleado", nomina['codEmp']),
        ("Bonificación", f"${float(nomina['bonificacion']):,.0f}"),
        ("Transporte", f"${float(nomina['transporte']):,.0f}"),
        ("Sueldo Base", f"${float(nomina['salario']):,.0f}"),
        ("Salario Total", f"${float(nomina['salario_total']):,.0f}"),
        ("Días Trabajados", nomina['diasTrabajados']),
    ]

    for etiqueta, valor in datos_ordenados:
        pdf.drawString(100, y, f"{etiqueta}: {valor}")
        y -= espacio

    pdf.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="nomina.pdf", mimetype='application/pdf')

# Ruta para cerrar sesión
@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.clear()
    return redirect(url_for('login'))

@app.route('/peliculas')
def mostrar_peliculas():
    peliculas = list(peliculas_collection.find())
    return render_template('inicio/peliculas.html', peliculas=peliculas)

@app.route('/libros')
def mostrar_libros():
    libros = list(libros_collection.find())
    return render_template('inicio/libros.html', libros=libros)


# Ejecutar la app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)