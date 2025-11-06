from flask import Flask, render_template
import sqlite3
import os
import re

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "InventarioBD_2.db")


def list_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    names = [r[0] for r in cur.fetchall()]
    conn.close()
    return names


def find_table(keyword: str, fallbacks=None):
    names = list_tables()
    names_lower = [n.lower() for n in names]

    for n in names:
        if keyword in n.lower():
            return n

    if fallbacks:
        for fb in fallbacks:
            if fb.lower() in names_lower:
                return names[names_lower.index(fb.lower())]
    return None


def normalize_type(t: str) -> str:
    """Clasifica el tipo SQLite hacia un input HTML probable."""
    t = (t or "").upper()
    if "INT" in t:
        return "number-int"
    if "REAL" in t or "FLOA" in t or "DOUB" in t or "DEC" in t or "NUM" in t:
        return "number-float"
    if "DATE" == t:
        return "date"
    if "DATETIME" in t or "TIMESTAMP" in t or "DATE" in t:
        return "datetime"
    return "text"


def should_hide_column(name: str, pk: int) -> bool:
    """Oculta columnas típicas de solo lectura/PK."""
    name_l = name.lower()
    if pk == 1:
        return True
    blacklist = {
        "id", "created_at", "updated_at",
        "fecha_creacion", "fecha_actualizacion"
    }
    return name_l in blacklist


def get_columns(table_name: str):
    """
    Devuelve metadatos de columnas:
    [
      {name, type, html_type, notnull(bool), default, pk(int), hidden(bool)}
    ]
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = []
    for c in cur.fetchall():
        name = c["name"]
        col_type = c["type"]
        pk = int(c["pk"] or 0)
        notnull = bool(c["notnull"])
        default = c["dflt_value"]
        html_type = normalize_type(col_type)
        hidden = should_hide_column(name, pk)
        cols.append({
            "name": name,
            "type": col_type,
            "html_type": html_type,
            "notnull": notnull,
            "default": default,
            "pk": pk,
            "hidden": hidden
        })
    conn.close()
    return cols


def fetch_all(table_name: str, headers=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if headers is None:
        cur.execute(f"PRAGMA table_info({table_name})")
        headers = [c["name"] for c in cur.fetchall()]

    try:
        cur.execute(f"SELECT * FROM {table_name} ORDER BY 1 DESC")
    except Exception:
        cur.execute(f"SELECT * FROM {table_name}")
    rows = cur.fetchall()
    conn.close()

    rows_list = [[row[h] for h in headers] for row in rows] if headers else []
    return headers, rows_list


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/productos")
def vista_productos():
    table = find_table(
        keyword="producto",
        fallbacks=["productos", "producto", "tbl_productos", "product", "products"]
    )
    error, headers, rows, columns = None, [], [], []
    if table:
        columns = get_columns(table)
        headers = [c["name"] for c in columns]
        headers, rows = fetch_all(table, headers)
    else:
        error = ("No se encontró una tabla de productos en la base de datos. "
                 "Ejemplo esperado: 'productos'.")
    return render_template("productos.html",
                           error=error, headers=headers, rows=rows, columns=columns)


@app.route("/almacenes")
def vista_almacenes():
    table = find_table(
        keyword="almacen",
        fallbacks=["almacenes", "almacen", "tbl_almacenes", "warehouses", "warehouse"]
    )
    error, headers, rows, columns = None, [], [], []
    if table:
        columns = get_columns(table)
        headers = [c["name"] for c in columns]
        headers, rows = fetch_all(table, headers)
    else:
        error = ("No se encontró una tabla de almacenes en la base de datos. "
                 "Ejemplo esperado: 'almacenes'.")
    return render_template("almacenes.html",
                           error=error, headers=headers, rows=rows, columns=columns)


if __name__ == "__main__":
    app.run(debug=True)
