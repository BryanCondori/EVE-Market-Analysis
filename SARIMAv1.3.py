import requests
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

# Configurar región (The Forge = Jita)
REGION_ID = 10000002  # The Forge

# Lista de TYPE_ID para los minerales comunes
minerales = {
    "Tritanium": 34,
    "Pyerite": 35,
    "Mexallon": 36,
    "Isogen": 37,
    "Nocxium": 38,
    "Zydrine": 39,
    "Megacyte": 40,
    "Morphite": 44
}

# Conectar a SQLite
conn = sqlite3.connect('eve_market.db')
cursor = conn.cursor()

# Crear tabla con la columna 'mineral'
cursor.execute('DROP TABLE IF EXISTS market_history')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS market_history (
        date TEXT,
        mineral TEXT,
        average REAL,
        highest REAL,
        lowest REAL,
        order_count INTEGER,
        volume INTEGER
    )
''')

# Obtener datos de la API y almacenarlos en la base de datos
for mineral, type_id in minerales.items():
    url = f"https://esi.evetech.net/latest/markets/{REGION_ID}/history/?type_id={type_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data)
        df['mineral'] = mineral
        print(f"Datos de {mineral} obtenidos")
        df.to_sql('market_history', conn, if_exists='append', index=False)
    else:
        print(f"Error al obtener datos para {mineral}: {response.status_code}")

conn.commit()

# Leer los datos de la base de datos
query = "SELECT date, mineral, average FROM market_history ORDER BY date"
df = pd.read_sql(query, conn)
conn.close()

# Convertir fechas y ordenar
df['date'] = pd.to_datetime(df['date'])
df.sort_values(by=['mineral', 'date'], inplace=True)

# Función para verificar estacionariedad (prueba de Dickey-Fuller)
def verificar_estacionariedad(serie):
    resultado = adfuller(serie)
    return resultado[1] <= 0.05  # Devuelve True si la serie es estacionaria

# Crear una figura para Plotly
fig = go.Figure()

# Iterar sobre cada mineral para analizar y graficar
for mineral, type_id in minerales.items():
    mineral_data = df[df['mineral'] == mineral].copy()
    mineral_data.set_index('date', inplace=True)

    # Verificar estacionariedad de la serie
    if not verificar_estacionariedad(mineral_data['average']):
        # Si no es estacionaria, aplicar diferenciación
        mineral_data['average_diff'] = mineral_data['average'].diff().dropna()
    else:
        mineral_data['average_diff'] = mineral_data['average']

    # Ajustar modelo SARIMA
    p, d, q = 1, 1, 1  # Hiperparámetros iniciales
    seasonal_order = (0, 1, 1, 7)  # Estacionalidad semanal (7 días)

    model = SARIMAX(mineral_data['average_diff'].dropna(), order=(p, d, q), seasonal_order=seasonal_order)
    sarima_result = model.fit(disp=False)

    # Realizar predicciones para los próximos 30 días
    predicciones = sarima_result.get_forecast(steps=30)
    predicciones_mean = predicciones.predicted_mean
    predicciones_ci = predicciones.conf_int()

    # Alinear la predicción con el último valor histórico
    ultimo_valor_historico = mineral_data['average'].iloc[-1]
    predicciones_mean += ultimo_valor_historico - predicciones_mean.iloc[0]

    # Agregar datos históricos al gráfico
    fig.add_trace(go.Scatter(
        x=mineral_data.index,
        y=mineral_data['average'],
        mode='lines',
        name=f'{mineral} Histórico',
        visible=False
    ))

    # Agregar predicción al gráfico
    future_dates = pd.date_range(mineral_data.index[-1], periods=30, freq='D')
    fig.add_trace(go.Scatter(
        x=future_dates,
        y=predicciones_mean,
        mode='lines',
        name=f'{mineral} Predicción',
        visible=False
    ))

    # Agregar intervalo de confianza
    fig.add_trace(go.Scatter(
        x=list(future_dates) + list(future_dates[::-1]),
        y=list(predicciones_ci.iloc[:, 0] + ultimo_valor_historico - predicciones_mean.iloc[0]) +
          list((predicciones_ci.iloc[:, 1] + ultimo_valor_historico - predicciones_mean.iloc[0])[::-1]),
        fill='toself',
        fillcolor='rgba(255, 182, 193, 0.3)',
        line=dict(color='rgba(255, 182, 193, 0)'),
        name=f'{mineral} Intervalo Confianza',
        visible=False
    ))

# Configurar visibilidad inicial
for i in range(0, len(minerales) * 3, 3):
    fig.data[i].visible = True
    fig.data[i + 1].visible = True
    fig.data[i + 2].visible = True
    break  # Solo el primer mineral es visible al inicio

# Crear botones para alternar entre minerales
buttons = []
for i, mineral in enumerate(minerales.keys()):
    buttons.append(dict(
        label=mineral,
        method="update",
        args=[{"visible": [j // 3 == i for j in range(len(minerales) * 3)]}]
    ))

# Agregar botones al diseño
fig.update_layout(
    updatemenus=[dict(
        active=0,
        buttons=buttons,
        x=1.15,
        xanchor="right",
        y=0.5,
        yanchor="middle"
    )],
    title="Predicción de Precios por Mineral",
    xaxis_title="Fecha",
    yaxis_title="Precio Promedio",
    template="plotly_white"
)

# Mostrar gráfico interactivo
fig.show()
