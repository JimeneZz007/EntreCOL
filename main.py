from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify,send_file
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors
import re
import os
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key')

app.config['MYSQL_HOST'] = '192.168.56.101'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'sistemas2024'
app.config['MYSQL_DB'] = 'EntreCOL+'

client = MongoClient("mongodb://192.168.56.101:27017/")  
db = client["Entrecol_multimedia"] 
peliculas_collection = db["peliculas"]
libros_collection = db["libros"]

# Inicializar MySQL
mysql = MySQL(app)

# Página principal de bienvenida
@app.route('/')
def bienvenido():
    return render_template('inicio/index.html')

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

# Ruta para cerrar sesión
@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.clear()
    return redirect(url_for('login'))

# Ruta de inicio
@app.route('/inicio')
def inicio():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # Consulta correcta para traer codEmp y nombre (columna correcta)
        cursor.execute('SELECT codEmp, nombre FROM empleado')
        empleados = cursor.fetchall()
        cursor.close()
        return render_template('home/inicio.html', username=session['nombre_usuario'], empleados=empleados, title="Inicio")
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
                DATE_FORMAT(e.fechaIngreso, '%%Y-%%m-%%d') AS fechaIngreso,
                c.nombre AS nombre_cargo,
                d.nombre AS nombre_dependencia,
                eps.nombre AS eps,
                arl.nombre AS arl,
                pension.nombre AS pension
            FROM 
                usuarios u
            JOIN empleado e ON u.codCreden = e.codCreden
            JOIN cargo c ON e.codCargo = c.codCargo
            JOIN dependencia d ON c.codDep = d.codDep
            JOIN seguridadSocial s ON e.codSeg = s.codSeg
            LEFT JOIN eps ON s.eps_id = eps.id
            LEFT JOIN arl ON s.arl_id = arl.id
            LEFT JOIN pension ON s.pension_id = pension.id
            WHERE u.codCreden = %s
        """, [session['codCreden']])
        perfil = cursor.fetchone()
        cursor.close()
        return render_template('auth/perfil.html', perfil=perfil, title="Tu Perfil")
    return redirect(url_for('login'))


# Ruta para editar el perfil
@app.route('/editar_perfil', methods=['GET', 'POST'])
def editar_perfil():
    if 'loggedin' in session and session['role'] == 'jefe':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Obtener listas para los selects
        cursor.execute("SELECT codSeg, eps_id, arl_id, pension_id FROM seguridadSocial")
        lista_seguridad = cursor.fetchall()

        # Obtener datos actuales del perfil
        cursor.execute("""
            SELECT 
                u.nombre_usuario, u.role,
                e.nombre AS nombre_empleado,
                e.fechaIngreso,
                c.nombre AS nombre_cargo,
                d.nombre AS nombre_dependencia,
                s.eps_id, s.arl_id, s.pension_id,
                e.codSeg
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

        if request.method == 'POST':
            nombre_empleado = request.form['nombre_empleado']
            fecha_ingreso = request.form['fecha_ingreso']
            eps_id = request.form['eps_id']
            arl_id = request.form['arl_id']
            pension_id = request.form['pension_id']

            # Actualizar nombre y fecha en empleado
            cursor.execute("""
                UPDATE empleado SET 
                    nombre = %s, 
                    fechaIngreso = %s 
                WHERE codCreden = %s
            """, (nombre_empleado, fecha_ingreso, session['codCreden']))

            # Buscar codSeg con la combinación seleccionada
            cursor.execute("""
                SELECT codSeg FROM seguridadSocial
                WHERE eps_id = %s AND arl_id = %s AND pension_id = %s
            """, (eps_id, arl_id, pension_id))
            resultado = cursor.fetchone()

            if resultado:
                nuevo_codSeg = resultado['codSeg']

                # Actualizar empleado con el nuevo codSeg
                cursor.execute("""
                    UPDATE empleado SET codSeg = %s
                    WHERE codCreden = %s
                """, (nuevo_codSeg, session['codCreden']))
            else:
                flash("La combinación de EPS, ARL y Pensión no existe en seguridad social.", "danger")
                return redirect(url_for('editar_perfil'))

            mysql.connection.commit()
            flash("Perfil actualizado exitosamente!", "success")
            return redirect(url_for('perfil'))

        # También debes obtener listas de eps, arl, pension para los selects (con nombres y ids)
        cursor.execute("SELECT id, nombre FROM eps")
        lista_eps = cursor.fetchall()

        cursor.execute("SELECT id, nombre FROM arl")
        lista_arl = cursor.fetchall()

        cursor.execute("SELECT id, nombre FROM pension")
        lista_pension = cursor.fetchall()

        return render_template(
            'auth/editar_perfil.html', 
            perfil=perfil, 
            lista_eps=lista_eps,
            lista_arl=lista_arl,
            lista_pension=lista_pension,
            title="Editar Perfil"
        )
    return redirect(url_for('login'))

# Registrar un empleado
@app.route('/registrar_empleado', methods=['GET', 'POST'])
def registrar_empleado():
    if 'loggedin' not in session or session.get('role') != 'jefe':
        flash("Acceso no autorizado", "danger")
        return redirect(url_for('inicio'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT id, nombre FROM eps")
    eps_list = cursor.fetchall()
    cursor.execute("SELECT id, nombre FROM pension")
    pension_list = cursor.fetchall()

    cursor.execute("SELECT id FROM arl WHERE nombre = %s", ("Positiva",))
    arl_row = cursor.fetchone()
    if not arl_row:
        flash("La ARL 'Positiva' no está configurada en la base de datos", "danger")
        return redirect(url_for('inicio'))
    arl_id = arl_row['id']

    if request.method == 'POST':
        # Usuario
        nombre_usuario = request.form['nombre_usuario']
        contraseña = generate_password_hash(request.form['contraseña'])
        rol = request.form['rol']

        # Empleado
        nombre_empleado = request.form['nombre_empleado']
        fecha_ingreso = request.form['fecha_ingreso']
        nombre_cargo = request.form['nombre_cargo']
        nombre_dependencia = request.form['nombre_dependencia']

        # Seguridad Social
        eps_id = request.form['eps']
        pension_id = request.form['pension']

        # Verificar si ya existe esa combinación
        cursor.execute("""SELECT codSeg FROM seguridadSocial 
                          WHERE eps_id = %s AND arl_id = %s AND pension_id = %s""",
                       (eps_id, arl_id, pension_id))
        seguridad = cursor.fetchone()
        if seguridad:
            codSeg = seguridad['codSeg']
        else:
            cursor.execute("""INSERT INTO seguridadSocial (eps_id, arl_id, pension_id) 
                              VALUES (%s, %s, %s)""", (eps_id, arl_id, pension_id))
            mysql.connection.commit()
            codSeg = cursor.lastrowid

        # Dependencia
        cursor.execute("SELECT codDep FROM dependencia WHERE nombre = %s", (nombre_dependencia,))
        dependencia = cursor.fetchone()
        if not dependencia:
            cursor.execute("INSERT INTO dependencia (nombre) VALUES (%s)", (nombre_dependencia,))
            mysql.connection.commit()
            codDep = cursor.lastrowid
        else:
            codDep = dependencia['codDep']

        # Cargo
        cursor.execute("SELECT codCargo FROM cargo WHERE nombre = %s AND codDep = %s", (nombre_cargo, codDep))
        cargo = cursor.fetchone()
        if not cargo:
            cursor.execute("INSERT INTO cargo (nombre, codDep) VALUES (%s, %s)", (nombre_cargo, codDep))
            mysql.connection.commit()
            codCargo = cursor.lastrowid
        else:
            codCargo = cargo['codCargo']

        # Usuario
        cursor.execute("INSERT INTO usuarios (nombre_usuario, contraseña, role) VALUES (%s, %s, %s)",
                       (nombre_usuario, contraseña, rol))
        mysql.connection.commit()
        codCreden = cursor.lastrowid

        # Empleado
        cursor.execute("""INSERT INTO empleado (codCreden, codCargo, codSeg, nombre, fechaIngreso) 
                          VALUES (%s, %s, %s, %s, %s)""",
                       (codCreden, codCargo, codSeg, nombre_empleado, fecha_ingreso))
        mysql.connection.commit()
        codEmp = cursor.lastrowid

        # Nómina
        bonificacion = float(request.form['bonificacion'])
        transporte = float(request.form['transporte'])
        salario = float(request.form['salario'])
        dias_trabajados = int(request.form['dias_trabajados'])
        salario_total = bonificacion + transporte + salario
        fecha_nomina = request.form['fecha_nomina']

        cursor.execute("""INSERT INTO nomina (codEmp, fechaNomina, bonificacion, transporte, salario, diasTrabajados, salario_total)
                          VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                       (codEmp, fecha_nomina, bonificacion, transporte, salario, dias_trabajados, salario_total))
        mysql.connection.commit()

        flash("Empleado y nómina registrados correctamente!", "success")
        return redirect(url_for('inicio'))

    return render_template("auth/registrar_empleado.html", title="Registrar Nuevo Empleado", eps_list=eps_list, pension_list=pension_list)

# index usuarios
@app.route('/empleado_info/<int:codEmp>')
def empleado_info(codEmp):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT 
            e.codEmp,
            e.nombre,
            c.nombre AS cargo,
            d.nombre AS dependencia,
            eps.nombre AS salud,
            pension.nombre AS pension,
            arl.nombre AS arl,
            DATE_FORMAT(e.fechaIngreso, '%%Y-%%m-%%d') as fechaIngreso
        FROM empleado e
        LEFT JOIN cargo c ON e.codCargo = c.codCargo
        LEFT JOIN dependencia d ON c.codDep = d.codDep
        LEFT JOIN seguridadSocial ss ON e.codSeg = ss.codSeg
        LEFT JOIN eps ON ss.eps_id = eps.id
        LEFT JOIN pension ON ss.pension_id = pension.id
        LEFT JOIN arl ON ss.arl_id = arl.id
        WHERE e.codEmp = %s
    """, (codEmp,))
    
    empleado = cursor.fetchone()
    cursor.close()

    if empleado:
        return jsonify(empleado)
    else:
        return {}, 404

# Pagina de editar empleados
@app.route('/editar_empleado/<int:codEmp>', methods=['GET', 'POST'])
def editar_empleado(codEmp):
    if 'loggedin' in session and session['role'] == 'jefe':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Obtener todos los cargos con su dependencia para el formulario
        cursor.execute("""
            SELECT c.codCargo, c.nombre AS cargo, d.nombre AS dependencia 
            FROM cargo c
            JOIN dependencia d ON c.codDep = d.codDep
        """)
        cargos = cursor.fetchall()

        if request.method == 'POST':
            nuevo_codCargo = request.form['codCargo']

            cursor.execute("""
                UPDATE empleado
                SET codCargo = %s
                WHERE codEmp = %s
            """, (nuevo_codCargo, codEmp))

            mysql.connection.commit()
            flash("Empleado actualizado correctamente", "success")
            return redirect(url_for('inicio'))

        # GET: obtener datos actuales del empleado, incluyendo su cargo y dependencia actuales
        cursor.execute("""
            SELECT e.codEmp, e.nombre, c.codCargo, c.nombre AS cargo, d.nombre AS dependencia
            FROM empleado e
            JOIN cargo c ON e.codCargo = c.codCargo
            JOIN dependencia d ON c.codDep = d.codDep
            WHERE e.codEmp = %s
        """, (codEmp,))
        empleado = cursor.fetchone()

        return render_template('auth/editar_empleado.html', empleado=empleado, cargos=cargos)

    flash("Acceso no autorizado", "danger")
    return redirect(url_for('inicio'))

# Ruta para eliminar empleado
@app.route('/eliminar_empleado/<int:codEmp>', methods=['DELETE'])
def eliminar_empleado(codEmp):
    if 'loggedin' not in session or session.get('role') != 'jefe':
        return jsonify({'message': 'Acceso no autorizado'}), 403

    cursor = mysql.connection.cursor()

    # Obtener codCreden asociado
    cursor.execute("SELECT codCreden FROM empleado WHERE codEmp = %s", (codEmp,))
    empleado = cursor.fetchone()
    if not empleado:
        return jsonify({'message': 'Empleado no encontrado'}), 404

    codCreden = empleado[0]

    # Eliminar nómina
    cursor.execute("DELETE FROM nomina WHERE codEmp = %s", (codEmp,))
    # Eliminar empleado
    cursor.execute("DELETE FROM empleado WHERE codEmp = %s", (codEmp,))
    # Eliminar usuario
    cursor.execute("DELETE FROM usuarios WHERE codCreden = %s", (codCreden,))
    mysql.connection.commit()

    return jsonify({'message': 'Empleado y sus datos fueron eliminados correctamente'})

# Ruta para obtener la nómina de un empleado específico
@app.route('/nomina_empleado/<int:codEmp>')
def nomina_empleado(codEmp):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT 
            e.codEmp,
            e.nombre,
            n.fechaNomina,
            n.bonificacion,
            n.transporte,
            n.salario,
            n.diasTrabajados,
            n.salario_total
        FROM nomina n
        JOIN empleado e ON n.codEmp = e.codEmp
        WHERE e.codEmp = %s
    """, (codEmp,))
    nominas = cursor.fetchall()
    cursor.close()
    if nominas:
        return jsonify(nominas)
    else:
        return jsonify([])  # Retorna lista vacía si no hay nómina


@app.route('/pagina_empleado',methods=['GET', 'POST'])
def pagina_empleado():
    if 'loggedin' in session and session['role'] != 'jefe':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Consulta de datos del perfil del empleado
        cursor.execute("""
            SELECT 
                u.nombre_usuario, u.role,
                e.codEmp,  -- AÑADIDO: necesario para filtrar en 'novedades'
                e.nombre AS nombre_empleado,
                fechaIngreso,
                c.nombre AS nombre_cargo,
                d.nombre AS nombre_dependencia,
                eps.nombre AS eps,
                arl.nombre AS arl,
                pension.nombre AS pension
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
            JOIN 
                eps ON s.eps_id = eps.id
            JOIN 
                arl ON s.arl_id = arl.id
            JOIN 
                pension ON s.pension_id = pension.id
            WHERE 
                u.codCreden = %s
        """, [session['codCreden']])
        perfil = cursor.fetchone()

        # Consulta de las últimas 5 nóminas del empleado
        cursor.execute("""
            SELECT 
                n.fechaNomina,
                n.diasTrabajados,
                n.bonificacion,
                n.transporte,
                n.salario,
                n.salario_total
            FROM 
                nomina n
            JOIN 
                empleado e ON n.codEmp = e.codEmp
            WHERE 
                e.codCreden = %s
            ORDER BY 
                n.fechaNomina DESC
            LIMIT 5
        """, [session['codCreden']])
        nominas_recientes = cursor.fetchall()

        # Consulta dinámica de novedades
        novedades = []
        tipo_consulta = None
        if request.method == 'POST':
            tipo_consulta = request.form['tipo_novedad']
            cursor.execute("""
                SELECT fechaNomina, fechaini, fechaFin
                FROM novedades n
                JOIN empleado e ON n.codEmp = e.codEmp
                WHERE e.codCreden = %s AND tipo = %s
                ORDER BY fechaNomina DESC
            """, [session['codCreden'], tipo_consulta])
            novedades = cursor.fetchall()

        return render_template(
            "auth/empleado.html",
            perfil=perfil,
            nominas=nominas_recientes,
            novedades=novedades,
            tipo_consulta=tipo_consulta,
            title="Tu Perfil de Empleado"
        )

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

    # Crear PDF con estilos
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []

    styles = getSampleStyleSheet()

    # Título centrado
    titulo = Paragraph(f"Nómina de {nomina['nombre_empleado']}", styles['Title'])
    elementos.append(titulo)
    elementos.append(Spacer(1, 20))

    # Datos de nómina
    datos_tabla = [
        ["Campo", "Valor"],
        ["Nombre del Empleado", nomina['nombre_empleado']],
        ["Código del Empleado", nomina['codEmp']],
        ["Bonificación", f"${float(nomina['bonificacion']):,.0f}"],
        ["Transporte", f"${float(nomina['transporte']):,.0f}"],
        ["Sueldo Base", f"${float(nomina['salario']):,.0f}"],
        ["Salario Total", f"${float(nomina['salario_total']):,.0f}"],
        ["Días Trabajados", nomina['diasTrabajados']]
    ]

    tabla = Table(datos_tabla, colWidths=[180, 200])

    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    buffer.seek(0)
    nombre_archivo = re.sub(r'[^a-zA-Z0-9_-]', '_', nomina['nombre_empleado'])
    filename = f"nomina_{nombre_archivo}.pdf"

    return send_file(buffer, as_attachment=True,    download_name=filename, mimetype='application/pdf')

# Ruta para mostrar películas
@app.route('/peliculas', methods=['GET'])
def mostrar_peliculas():
    busqueda = request.args.get('busqueda', '')
    genero = request.args.get('genero', '')
    anio = request.args.get('anio', '')
    ordenar_por = request.args.get('ordenar_por', 'titulo')
    query = {}

    if busqueda:
        query['titulo'] = {'$regex': busqueda, '$options': 'i'}  
    if genero:
        query['generos'] = genero

    if anio:
        try:
            anio_int = int(anio)
            query['anio'] = anio_int
        except ValueError:
            pass 
    
    sort_option = []
    if ordenar_por == 'titulo':
        sort_option = [('titulo', 1)] 
    elif ordenar_por == 'anio':
        sort_option = [('anio', 1)]
    elif ordenar_por == 'anio_desc':
        sort_option = [('anio', -1)] 

    peliculas = list(peliculas_collection.find(query).sort(sort_option))
    
    todos_generos = peliculas_collection.distinct('generos')
    
    todos_anios = sorted(peliculas_collection.distinct('anio'))
    
    return render_template(
        'inicio/peliculas.html', 
        peliculas=peliculas,
        busqueda=busqueda,
        genero_seleccionado=genero,
        anio_seleccionado=anio,
        ordenar_por=ordenar_por,
        todos_generos=todos_generos,
        todos_anios=todos_anios
    )

# Ruta para mostrar libros
@app.route('/libros', methods=['GET'])
def mostrar_libros():
    busqueda = request.args.get('busqueda', '')
    autor = request.args.get('autor', '')
    editorial = request.args.get('editorial', '')
    anio = request.args.get('anio', '')
    ordenar_por = request.args.get('ordenar_por', 'title')
    rating_min = request.args.get('rating_min', '')
    query = {}
    
    if busqueda:
        query['title'] = {'$regex': busqueda, '$options': 'i'}
    
    if autor:
        query['authors'] = {'$regex': autor, '$options': 'i'}
    
    if editorial:
        query['publisher'] = {'$regex': editorial, '$options': 'i'}
    
    if anio:
    
        query['publication_date'] = {'$regex': f'{anio}$', '$options': 'i'}
    
    if rating_min:
        try:
        
            rating_min_float = float(rating_min)
            query['average_rating'] = {'$gte': str(rating_min_float)}
        except ValueError:
            pass 
    
    sort_option = []
    if ordenar_por == 'title':
        sort_option = [('title', 1)]  
    elif ordenar_por == 'title_desc':
        sort_option = [('title', -1)]  
    elif ordenar_por == 'rating':
        sort_option = [('average_rating', -1)] 
    elif ordenar_por == 'fecha':
        sort_option = [('publication_date', 1)]
    elif ordenar_por == 'paginas':
        sort_option = [('num_pages', 1)]
    
    libros = list(libros_collection.find(query).sort(sort_option))
    
    todos_autores = sorted(list(set(libro['authors'] for libro in libros_collection.find({}, {'authors': 1, '_id': 0}) if 'authors' in libro)))
    
    todas_editoriales = sorted(list(set(libro['publisher'] for libro in libros_collection.find({}, {'publisher': 1, '_id': 0}) if 'publisher' in libro and libro['publisher'])))
    
    todos_anios = set()
    for libro in libros_collection.find({}, {'publication_date': 1, '_id': 0}):
        if 'publication_date' in libro and libro['publication_date']:
            partes = libro['publication_date'].split('/')
            if len(partes) >= 3:
                todos_anios.add(partes[2])  
    todos_anios = sorted(list(todos_anios))
    
    return render_template(
        'inicio/libros.html', 
        libros=libros,
        busqueda=busqueda,
        autor_seleccionado=autor,
        editorial_seleccionada=editorial,
        anio_seleccionado=anio,
        rating_min=rating_min,
        ordenar_por=ordenar_por,
        todos_autores=todos_autores,
        todas_editoriales=todas_editoriales,
        todos_anios=todos_anios
    )

# Ejecutar la app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)