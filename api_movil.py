# ============================================================
#  api_movil.py  -  Endpoints para la app Flutter (Flask)
# ============================================================
# Esto se AGREGA a tu proyecto gacrux-web (Render). La app móvil
# habla SOLO con estos endpoints; nunca toca MySQL directo.
#
# Credenciales de Aiven via VARIABLES DE ENTORNO (no en el código).
# En Render -> Environment, define: DB_HOST, DB_PORT, DB_USER,
# DB_PASSWORD, DB_NAME, JWT_SECRET
# ============================================================
import os
import datetime
import jwt  # pip install pyjwt
import mysql.connector
from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "CAMBIA_ESTE_SECRETO")

def conectar_bd():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        port=int(os.environ.get("DB_PORT", "19257")),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME", "defaultdb"),
    )

# ---- Decorador: exige token válido ----
def requiere_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Falta token"}), 401
        token = auth.split(" ", 1)[1]
        try:
            jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except Exception:
            return jsonify({"error": "Token inválido o expirado"}), 401
        return f(*args, **kwargs)
    return wrapper

# ============================================================
#  LOGIN  -  POST /api/login
# ============================================================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    usuario = (data.get("usuario") or "").strip().lower()
    password = data.get("password") or ""

    if not usuario or not password:
        return jsonify({"error": "Faltan datos"}), 400

    try:
        con = conectar_bd()
        cur = con.cursor(dictionary=True)
        cur.execute(
            "SELECT nombre_real, rol_puesto, password FROM usuarios_gacrux WHERE usuario = %s",
            (usuario,),
        )
        res = cur.fetchone()
        cur.close()
        con.close()
    except Exception as e:
        return jsonify({"error": f"Error de BD: {e}"}), 500

    # OJO: comparación en texto plano (igual que tu POS actual).
    # Cuando migres a hash, cambia esta línea por check de bcrypt.
    if res and res["password"] == password:
        token = jwt.encode(
            {
                "usuario": usuario,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30),
            },
            JWT_SECRET,
            algorithm="HS256",
        )
        return jsonify({
            "ok": True,
            "nombre_real": res["nombre_real"],
            "rol_puesto": res["rol_puesto"],
            "token": token,
        })
    return jsonify({"error": "Usuario o contraseña incorrectos"}), 401

# ============================================================
#  ESCANEAR (modo Nube)  -  POST /api/escanear
#  Mete el código en cola_escaneos -> tu pos.py lo recoge.
# ============================================================
@app.route("/api/escanear", methods=["POST"])
@requiere_token
def escanear():
    data = request.get_json(force=True)
    codigo = (data.get("codigo_barras") or "").strip()
    if not codigo:
        return jsonify({"error": "Código vacío"}), 400
    try:
        con = conectar_bd()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO cola_escaneos (codigo_barras, procesado) VALUES (%s, 0)",
            (codigo,),
        )
        con.commit()
        cur.close()
        con.close()
        return jsonify({"ok": True, "codigo": codigo}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================
#  INVENTARIO (opcional: ver almacén en la app)
#  Ajusta el nombre de tu tabla y columnas reales.
# ============================================================
@app.route("/api/inventario", methods=["GET"])
@requiere_token
def inventario():
    q = (request.args.get("q") or "").strip()
    try:
        con = conectar_bd()
        cur = con.cursor(dictionary=True)
        if q:
            cur.execute(
                # 🔴 AJUSTA 'inventario_gacrux' y columnas a tu tabla real
                "SELECT * FROM inventario_gacrux WHERE codigo_barras LIKE %s OR modelo LIKE %s LIMIT 100",
                (f"%{q}%", f"%{q}%"),
            )
        else:
            cur.execute("SELECT * FROM inventario_gacrux LIMIT 100")
        filas = cur.fetchall()
        cur.close()
        con.close()
        return jsonify(filas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return "API GACRUX móvil OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

