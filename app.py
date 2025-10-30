from flask import Flask, render_template, jsonify, request
import requests

app = Flask(__name__)

# 🔐 Credenciales de Supabase
SUPABASE_URL = "https://gjkkqwuryafgfamziezj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdqa2txd3VyeWFmZ2ZhbXppZXpqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk3MTMyMDAsImV4cCI6MjA3NTI4OTIwMH0.1qM9QA6NT1qfPgV36C-VY7EMTiEwfZ36JouDpHMVhg0"

def get_supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

# ✅ Función para obtener usuarios desde Supabase
def get_users():
    url = f"{SUPABASE_URL}/rest/v1/Inscripciones"
    response = requests.get(url, headers=get_supabase_headers())

    if response.status_code == 200:
        print("✅ Inscripciones obtenidas con éxito")
        return response.json()
    else:
        print(f"⚠️ Error {response.status_code}: {response.text}")
        return []

def update_user_attendance(user_id, attendance):
    # Construir payload y headers
    data = {"Asistencia": attendance}
    headers = get_supabase_headers()
    # Pedir retorno de representation puede ayudar a depurar (opcional)
    headers['Prefer'] = 'return=representation'

    # Buscar por cédula únicamente
    url = f"{SUPABASE_URL}/rest/v1/Inscripciones?Cedula=eq.{user_id}"
    try:
        response = requests.patch(url, json=data, headers=headers, timeout=10)
        # Supabase suele devolver 204 No Content o 200 con representation
        if response.status_code in (200, 204):
            print(f"✅ PATCH OK (Cedula={user_id}) status={response.status_code}")
            return True
        else:
            print(f"PATCH falló (Cedula={user_id}) status={response.status_code} body={response.text}")
    except Exception as e:
        print(f"Error PATCH a {url}: {e}")
    
    return False

def process_users_data(users):
    # Procesar estadísticas
    total_users = len(users)
    registered_users = len([u for u in users if u.get('Asistencia') is True])
    pending_users = total_users - registered_users
    provinces = set(user.get('Provincia', '') for user in users)
    cities = set(user.get('Canton', '') for user in users)
    
    # Calcular promedio de edad
    ages = [user.get('Edad', 0) for user in users if user.get('Edad')]
    avg_age = round(sum(ages) / len(ages)) if ages else 0
    
    # Contar usuarios por mesa
    mesas = {}
    for user in users:
        mesa = user.get('MesaSelected', '')
        mesas[mesa] = mesas.get(mesa, 0) + 1
    
    # Preparar estadísticas para las gráficas
    cities_data = {}
    provinces_data = {}
    age_groups = {'-18': 0,'18-25': 0, '26-35': 0, '36-45': 0, '46+': 0}
    
    for user in users:
        # Conteo por ciudad
        city = user.get('Canton', '').upper()
        cities_data[city] = cities_data.get(city, 0) + 1
        
        # Conteo por provincia
        province = user.get('Provincia', '')
        provinces_data[province] = provinces_data.get(province, 0) + 1
        
        # Conteo por grupo de edad
        age = user.get('Edad', 0)
        if age:
            if age <= 25:
                age_groups['18-25'] += 1
            elif age <= 35:
                age_groups['26-35'] += 1
            elif age <= 45:
                age_groups['36-45'] += 1
            else:
                age_groups['46+'] += 1
    
    # Obtener listas únicas ordenadas
    unique_cities = sorted(list(cities))
    unique_provinces = sorted(list(provinces))
    unique_mesas = sorted(list(mesas.keys()))

    return {
        'users': users,
        'stats': {
            'total_users': total_users,
            'registered_users': registered_users,
            'pending_users': pending_users,
            'total_provinces': len(provinces),
            'avg_age': round(avg_age, 1),
            'cities_data': cities_data,
            'provinces_data': provinces_data,
            'age_groups': age_groups,
            'mesas_data': mesas
        },
        'filter_options': {
            'cities': unique_cities,
            'provinces': unique_provinces,
            'mesas': unique_mesas
        }
    }

@app.route("/")
def dashboard():
    users = get_users()
    sorted_users = sorted(users, key=lambda x: x.get('Apellidos', ''))
    data = process_users_data(sorted_users)
    return render_template("dashboard.html", **data)

@app.route("/api/attendance", methods=["POST"])
def update_attendance():
    data = request.get_json(silent=True) or {}
    cedula = data.get('user_id')  # Cambio para coincidir con el dato enviado desde el frontend
    attendance = data.get('Asistencia')
    print(f"Actualizando asistencia para cédula: {cedula}")
    if cedula is None or attendance is None:
        return jsonify({"error": "Faltan datos requeridos"}), 400
        
    print(f"Actualizando asistencia para cédula: {cedula}")
    
    success = update_user_attendance(cedula, attendance)
    
    if success:
        print("✅ Asistencia actualizada con éxito")
        return jsonify({"message": "Asistencia actualizada correctamente"}), 200
    else:
        print("error al actualizar la asistencia")
        return jsonify({"error": "Error al actualizar la asistencia"}), 500

if __name__ == "__main__":
    app.run(debug=True)
