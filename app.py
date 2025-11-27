from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash, jsonify
)
import sqlite3
import os
import hashlib
from datetime import datetime
from functools import wraps  # para el decorador login_required

app = Flask(__name__)

# -------------------------------------------------
# Configuración básica
# -------------------------------------------------

# Clave para firmar las cookies de sesión
app.secret_key = "clave-super-secreta-inventario"

# Ruta absoluta al archivo de base de datos SQLite
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "InventarioBD_2.db")


# -------------------------------------------------
# Funciones helper de base de datos
# -------------------------------------------------

def get_connection():
    """
    Crea y devuelve una conexión a SQLite.

    - row_factory=sqlite3.Row hace que cada fila se pueda
      acceder como diccionario (row["nombre_columna"]).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(plain: str) -> str:
    """
    Hashea una contraseña en MD5.

    Para un proyecto real se usaría algo más fuerte (bcrypt, argon2, etc.)
    """
    return hashlib.md5(plain.encode("utf-8")).hexdigest()


def init_db():
    """
    Inicializa la base de datos la primera vez que corre la app.

    - Crea la tabla usuarios si no existe.
    - Inserta usuarios base: ADMIN, PRODUCTOS, ALMACENES.
    - Asegura que las tablas productos y almacenes (si existen)
      tengan las columnas de auditoría:
        * fecha_hora_creacion
        * fecha_hora_ultima_modificacion
        * ultimo_usuario_en_modificar
    - Rellena fecha_hora_creacion con la fecha actual si estuviera en NULL.
    """
    with get_connection() as conn:
        cur = conn.cursor()

        # -------- Crear tabla usuarios --------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                nombre TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                fecha_hora_ultimo_inicio TEXT,
                rol TEXT NOT NULL
            )
        """)

        # Usuarios "semilla" con sus roles y passwords
        usuarios_base = [
            ("ADMIN",      "admin23",      "ADMIN"),
            ("PRODUCTOS",  "productos19",  "PRODUCTOS"),
            ("ALMACENES",  "almacenes11",  "ALMACENES"),
        ]

        # Insertar los usuarios base solo si no existen
        for nombre, plain_pwd, rol in usuarios_base:
            cur.execute("SELECT 1 FROM usuarios WHERE nombre = ?", (nombre,))
            if cur.fetchone() is None:
                cur.execute(
                    "INSERT INTO usuarios (nombre, password, rol) VALUES (?, ?, ?)",
                    (nombre, hash_password(plain_pwd), rol)
                )

        # -------- Asegurar columnas de auditoría en tablas --------
        def ensure_columns(table_name: str):
            """
            Revisa la definición de la tabla y agrega las columnas de auditoría
            si aún no existen.
            """
            cur.execute(f"PRAGMA table_info({table_name})")
            existing_cols = [row["name"] for row in cur.fetchall()]

            # Lista de columnas que queremos garantizar en cada tabla
            columnas_auditoria = [
                "fecha_hora_creacion",
                "fecha_hora_ultima_modificacion",
                "ultimo_usuario_en_modificar",
            ]

            for col in columnas_auditoria:
                if col not in existing_cols:
                    cur.execute(
                        f"ALTER TABLE {table_name} "
                        f"ADD COLUMN {col} TEXT"
                    )

        # Intentar con productos y almacenes; si la tabla no existe, ignorar
        for table in ("productos", "almacenes"):
            try:
                ensure_columns(table)
            except sqlite3.OperationalError:
                # Si la tabla no existe aún, no hacemos nada
                pass

        # -------- Rellenar fecha_hora_creacion cuando esté en NULL --------
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for table in ("productos", "almacenes"):
            try:
                cur.execute(
                    f"UPDATE {table} "
                    "SET fecha_hora_creacion = ? "
                    "WHERE fecha_hora_creacion IS NULL",
                    (ahora,)
                )
            except sqlite3.OperationalError:
                # Si la tabla no existe, también lo ignoramos
                pass

        conn.commit()


def get_columns(table_name: str):
    """
    Lee PRAGMA table_info y devuelve una lista de diccionarios con metadatos
    de cada columna. Esto se usa para construir el formulario dinámico en HTML.

    Cada elemento tiene:
      {
        "name": nombre_columna,
        "type": tipo_sqlite,
        "html_type": tipo_de_input_html,
        "notnull": bool,
        "default": valor_por_defecto,
        "pk": 1 si es clave primaria,
        "hidden": True si NO queremos mostrarla en el formulario
      }
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        info_columnas = cur.fetchall()

    cols = []
    for c in info_columnas:
        name = c["name"]
        col_type = c["type"] or ""
        pk = int(c["pk"] or 0)
        notnull = bool(c["notnull"])
        default = c["dflt_value"]

        # Detectar tipo de input para HTML según el tipo de la columna
        t_upper = col_type.upper()
        if "INT" in t_upper:
            html_type = "number-int"
        elif any(x in t_upper for x in ("REAL", "FLOA", "DOUB", "DEC", "NUM")):
            html_type = "number-float"
        elif t_upper == "DATE":
            html_type = "date"
        elif any(x in t_upper for x in ("DATETIME", "TIMESTAMP", "DATE")):
            html_type = "datetime"
        else:
            html_type = "text"

        # Columnas que se consideran "ocultas" en el formulario
        name_l = name.lower()
        hidden = False
        if pk == 1 or name_l in {
            "id",
            "created_at",
            "updated_at",
            "fecha_creacion",
            "fecha_actualizacion",
            "fecha_hora_creacion",
            "fecha_hora_ultima_modificacion",
            "ultimo_usuario_en_modificar"
        }:
            hidden = True

        cols.append({
            "name": name,
            "type": col_type,
            "html_type": html_type,
            "notnull": notnull,
            "default": default,
            "pk": pk,
            "hidden": hidden
        })

    return cols


def fetch_all(table_name: str, headers=None):
    """
    Devuelve todos los registros de una tabla como:
      (headers, rows_list)

    - headers: lista de nombres de columna.
    - rows_list: lista de listas con los valores de cada fila.
    """
    with get_connection() as conn:
        cur = conn.cursor()

        # Si no se pasan headers, los obtenemos de PRAGMA table_info
        if headers is None:
            cur.execute(f"PRAGMA table_info({table_name})")
            headers = [c["name"] for c in cur.fetchall()]

        # Intentar ordenar por la primera columna (normalmente id)
        try:
            cur.execute(f"SELECT * FROM {table_name} ORDER BY 1 DESC")
        except sqlite3.OperationalError:
            # Si falla (por ejemplo, la tabla no existe), hacemos un SELECT simple
            cur.execute(f"SELECT * FROM {table_name}")

        rows = cur.fetchall()

    rows_list = [[row[h] for h in headers] for row in rows] if headers else []
    return headers, rows_list


# -------------------------------------------------
# Decorador para exigir inicio de sesión
# -------------------------------------------------

def login_required(view):
    """
    Decorador para proteger rutas.

    Si no hay usuario en sesión, redirige al login.
    Si sí hay usuario, ejecuta la vista normal.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# -------------------------------------------------
# Helper para renderizar tablas (productos / almacenes)
# -------------------------------------------------

def render_tabla(table, template_name, roles_edicion):
    """
    Encapsula la lógica compartida entre:
      - vista_productos
      - vista_almacenes

    Parámetros:
      table: nombre de la tabla en SQLite ("productos" o "almacenes").
      template_name: nombre del template HTML.
      roles_edicion: tupla con roles que pueden editar esa tabla.
    """
    usuario = session.get("usuario")
    rol = session.get("rol")

    # Determina si el usuario actual puede agregar/modificar/eliminar
    puede_editar = rol in roles_edicion

    error = None
    columns = []
    headers = []
    rows = []

    try:
        # Metadatos de columnas y registros de la tabla
        columns = get_columns(table)
        headers = [c["name"] for c in columns]
        headers, rows = fetch_all(table, headers)
    except sqlite3.OperationalError:
        error = f"No se encontró la tabla '{table}' en la base de datos."

    # Renderiza el template correspondiente con los datos
    return render_template(
        template_name,
        usuario=usuario,
        rol=rol,
        puede_editar=puede_editar,
        error=error,
        headers=headers,
        rows=rows,
        columns=columns
    )


# -------------------------------------------------
# Rutas de autenticación
# -------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Vista de inicio de sesión.

    - GET: muestra el formulario.
    - POST: valida credenciales y guarda usuario/rol en session.
    """
    # Si ya está logueado, lo mandamos directamente al inicio
    if "usuario" in session and request.method == "GET":
        return redirect(url_for("inicio"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        password = request.form.get("password", "")

        if not nombre or not password:
            flash("Debes ingresar usuario y contraseña.", "danger")
            return render_template("login.html")

        # Buscar usuario en la BD
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT nombre, password, rol FROM usuarios WHERE nombre = ?",
                (nombre,)
            )
            row = cur.fetchone()

        if row is None:
            flash("Usuario o contraseña inválidos.", "danger")
            return render_template("login.html")

        # Comprobar hash de contraseña
        hashed_input = hash_password(password)
        if hashed_input != row["password"]:
            flash("Usuario o contraseña inválidos.", "danger")
            return render_template("login.html")

        # Credenciales válidas -> guardar en sesión
        session["usuario"] = row["nombre"]
        session["rol"] = row["rol"]

        # Registrar última fecha/hora de inicio de sesión
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE usuarios SET fecha_hora_ultimo_inicio = ? WHERE nombre = ?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row["nombre"])
            )
            conn.commit()

        flash("Inicio de sesión exitoso.", "success")
        return redirect(url_for("inicio"))

    # Si es GET y no hay sesión, simplemente mostramos el login
    return render_template("login.html")


@app.route("/logout")
def logout():
    """
    Cierra la sesión actual (vacía la variable session)
    y redirige al formulario de login.
    """
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("login"))


# -------------------------------------------------
# Rutas principales (vistas HTML)
# -------------------------------------------------

@app.route("/")
@login_required
def inicio():
    """
    Vista de Inicio (pantalla con el logo, nombre del alumno y links
    a Productos y Almacenes).
    """
    usuario = session.get("usuario")
    rol = session.get("rol")
    return render_template("index.html", usuario=usuario, rol=rol)


@app.route("/productos")
@login_required
def vista_productos():
    """
    Vista de la tabla de productos.

    Roles con permiso de edición:
      - ADMIN
      - PRODUCTOS
    """
    return render_tabla("productos", "productos.html", ("ADMIN", "PRODUCTOS"))


@app.route("/almacenes")
@login_required
def vista_almacenes():
    """
    Vista de la tabla de almacenes.

    Roles con permiso de edición:
      - ADMIN
      - ALMACENES
    """
    return render_tabla("almacenes", "almacenes.html", ("ADMIN", "ALMACENES"))


# -------------------------------------------------
# Helpers genéricos para API CRUD (insert/update/delete)
# -------------------------------------------------

def insert_row(table: str, data: dict, usuario: str):
    """
    Inserta una fila en la tabla indicada.

    - Elimina la clave 'id' si viene en data.
    - Agrega y rellena las columnas de auditoría.
    """
    data_noid = {k: v for k, v in data.items() if k != "id"}

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_noid.update({
        "fecha_hora_creacion": ahora,
        "fecha_hora_ultima_modificacion": ahora,
        "ultimo_usuario_en_modificar": usuario,
    })

    columnas = ", ".join(data_noid.keys())
    placeholders = ", ".join("?" for _ in data_noid)
    valores = list(data_noid.values())

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO {table} ({columnas}) VALUES ({placeholders})",
            valores
        )
        conn.commit()


def delete_rows(table: str, ids):
    """
    Elimina múltiples filas de 'table' según la lista de IDs.

    Devuelve:
      (ok: bool, msg: str | None)
    """
    if not ids:
        return False, "No se enviaron IDs"

    with get_connection() as conn:
        cur = conn.cursor()
        cur.executemany(
            f"DELETE FROM {table} WHERE id = ?",
            [(i,) for i in ids]
        )
        conn.commit()

    return True, None


def update_row(table: str, data: dict, usuario: str):
    """
    Actualiza una fila de 'table' utilizando los datos en 'data'.

    - Requiere que 'data' tenga la clave 'id'.
    - No actualiza la columna 'id'.
    - Actualiza las columnas de auditoría.
    """
    row_id = data.get("id")
    if not row_id:
        return False, "Falta ID"

    # Quitamos id para construir el SET
    data_noid = {k: v for k, v in data.items() if k != "id"}

    sets = [f"{k} = ?" for k in data_noid]
    values = list(data_noid.values())

    # Campos de auditoría
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sets.append("fecha_hora_ultima_modificacion = ?")
    values.append(ahora)

    sets.append("ultimo_usuario_en_modificar = ?")
    values.append(usuario)

    # ID al final para el WHERE
    values.append(row_id)

    sql = f"UPDATE {table} SET {', '.join(sets)} WHERE id = ?"

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, values)
        conn.commit()

    return True, None


# -------------------------------------------------
# Rutas API específicas (usan los helpers genéricos)
# -------------------------------------------------

@app.route("/productos/insert", methods=["POST"])
@login_required
def insertar_producto():
    """
    API: Inserta un producto nuevo.
    """
    data = request.json or {}
    insert_row("productos", data, session.get("usuario"))
    return jsonify({"ok": True})


@app.route("/productos/delete", methods=["POST"])
@login_required
def eliminar_productos():
    """
    API: Elimina uno o varios productos por ID.
    """
    ids = (request.json or {}).get("ids", [])
    ok, msg = delete_rows("productos", ids)
    return jsonify({"ok": ok, "msg": msg})


@app.route("/productos/update", methods=["POST"])
@login_required
def modificar_producto():
    """
    API: Actualiza un producto existente.
    """
    data = request.json or {}
    ok, msg = update_row("productos", data, session.get("usuario"))
    return jsonify({"ok": ok, "msg": msg})


@app.route("/almacenes/insert", methods=["POST"])
@login_required
def insertar_almacen():
    """
    API: Inserta un almacén nuevo.
    """
    data = request.json or {}
    insert_row("almacenes", data, session.get("usuario"))
    return jsonify({"ok": True})


@app.route("/almacenes/delete", methods=["POST"])
@login_required
def eliminar_almacenes():
    """
    API: Elimina uno o varios almacenes por ID.
    """
    ids = (request.json or {}).get("ids", [])
    ok, msg = delete_rows("almacenes", ids)
    return jsonify({"ok": ok, "msg": msg})


@app.route("/almacenes/update", methods=["POST"])
@login_required
def modificar_almacen():
    """
    API: Actualiza un almacén existente.
    """
    data = request.json or {}
    ok, msg = update_row("almacenes", data, session.get("usuario"))
    return jsonify({"ok": ok, "msg": msg})


# -------------------------------------------------
# Punto de entrada
# -------------------------------------------------

if __name__ == "__main__":
    # Inicializa la base de datos antes de levantar el servidor
    init_db()
    app.run(debug=True)
