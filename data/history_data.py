import requests
import pandas as pd

# Configurar región (The Forge = Jita)
REGION_ID = 10000002  # The Forge
TYPE_ID = 34  # Tritanium, un mineral común

# Endpoint de la API
url = f"https://esi.evetech.net/latest/markets/{REGION_ID}/history/?type_id={TYPE_ID}"

# Hacer la solicitud
response = requests.get(url)

# Verificar si la solicitud fue exitosa
if response.status_code == 200:
    data = response.json()
    # Convertir a DataFrame para análisis
    df = pd.DataFrame(data)
    print(df.head())
    # Guardar en CSV
    df.to_csv('market_history.csv', index=False)
    print("Datos guardados en market_history.csv")
else:
    print(f"Error: {response.status_code}")



import sqlite3

# Conectar a SQLite
conn = sqlite3.connect('eve_market.db')
cursor = conn.cursor()

# Crear tabla
cursor.execute('''
    CREATE TABLE IF NOT EXISTS market_history (
        date TEXT,
        average REAL,
        highest REAL,
        lowest REAL,
        order_count INTEGER,
        volume INTEGER
    )
''')

# Insertar datos
df.to_sql('market_history', conn, if_exists='append', index=False)

conn.commit()
conn.close()
print("Datos guardados en la base de datos SQLite")



import matplotlib.pyplot as plt

# Leer datos de la base de datos
conn = sqlite3.connect('eve_market.db')
query = "SELECT date, average FROM market_history ORDER BY date"
df = pd.read_sql(query, conn)
conn.close()

# Convertir fechas
df['date'] = pd.to_datetime(df['date'])

# Graficar precios promedio
plt.plot(df['date'], df['average'], label='Precio promedio')
plt.xlabel('Fecha')
plt.ylabel('Precio')
plt.title('Tendencia de precios de Tritanium')
plt.legend()
plt.show()

