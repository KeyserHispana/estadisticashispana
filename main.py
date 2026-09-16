from flask import Flask
from threading import Thread
import os
import discord
from discord.ext import commands
from discord import Embed
import json
import matplotlib.pyplot as plt
import io
from datetime import datetime

app = Flask('')

@app.route('/')
def home():
    return "Bot de Estadisticas activo 24/7"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- GESTIÓN DE MEMORIA (JSON) ---
ARCHIVO_HISTORIAL = 'historial_eficiencia.json'

def cargar_historial():
    if not os.path.exists(ARCHIVO_HISTORIAL):
        return {}
    with open(ARCHIVO_HISTORIAL, 'r', encoding='utf-8') as f:
        return json.load(f)

def guardar_en_historial(fecha, datos_actuales):
    historial = cargar_historial()
    
    # Extraer solo la eficiencia para no hacer el archivo enorme
    datos_guardar = {nombre: datos['eficiencia'] for nombre, datos in datos_actuales.items()}
    
    # Guardar usando la fecha como llave
    historial[fecha] = datos_guardar
    
    # Mantener solo las últimas 6 fechas registradas
    fechas_ordenadas = sorted(historial.keys())
    if len(fechas_ordenadas) > 6:
        fechas_a_borrar = fechas_ordenadas[:-6]
        for f in fechas_a_borrar:
            del historial[f]
            
    with open(ARCHIVO_HISTORIAL, 'w', encoding='utf-8') as f:
        json.dump(historial, f, indent=4)

# --- CARGA DE DATOS TXT ---
def cargar_datos_quincena(nombre_archivo):
    datos_aerolineas = {}
    datos_alianza = None
    
    if not os.path.exists(nombre_archivo):
        return datos_alianza, datos_aerolineas
        
    with open(nombre_archivo, 'r', encoding='utf-8') as f:
        for linea in f:
            if not linea.strip() or linea.startswith('AEROLINEA'):
                continue
                
            partes = linea.strip().split(',')
            
            if partes[0].strip().upper() == 'ALIANZA' and len(partes) >= 4:
                try:
                    datos_alianza = {
                        'rank': int(partes[1]),
                        'valor': float(partes[2]),
                        'crecimiento_diario': float(partes[3])
                    }
                except ValueError:
                    pass
                continue
                
            # NUEVO FORMATO: Nombre, Acciones, C_Diaria, Potencial, Promedio, Eficiencia
            if len(partes) >= 6:
                nombre = partes[0].strip()
                try:
                    acciones = float(partes[1])
                    c_diaria = int(partes[2])
                    potencial = float(partes[3])
                    promedio = float(partes[4])
                    eficiencia = int(partes[5])
                    
                    datos_aerolineas[nombre] = {
                        'acciones': acciones,
                        'c_diaria': c_diaria,
                        'potencial': potencial,
                        'promedio': promedio,
                        'eficiencia': eficiencia
                    }
                except ValueError:
                    continue
                    
    return datos_alianza, datos_aerolineas

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"Bot de Estadisticas conectado como {bot.user}")

@bot.command(name='reporte_quincena')
async def reporte_quincena(ctx):
    alianza_pasada, datos_pasados = cargar_datos_quincena('quincena_pasada.txt')
    alianza_actual, datos_actuales = cargar_datos_quincena('quincena_actual.txt')
    
    if not datos_pasados or not datos_actuales:
        await ctx.send("⚠️ Faltan datos de aerolíneas en los archivos de texto.")
        return
        
    # Guardar en la memoria histórica
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    guardar_en_historial(fecha_hoy, datos_actuales)

    # 1. Resumen General de la Alianza
    embed_resumen = Embed(title="📊 Reporte Quincenal HISPANA", color=discord.Color.green())
    if alianza_pasada and alianza_actual:
        avance_rank = alianza_pasada['rank'] - alianza_actual['rank']
        icono_rank = "⬆️" if avance_rank > 0 else "⬇️" if avance_rank < 0 else "➖"
        embed_resumen.add_field(name="🏆 Ranking Global", value=f"Anterior: **{alianza_pasada['rank']}**\nActual: **{alianza_actual['rank']}**\nMovimiento: {icono_rank} **{abs(avance_rank)}**", inline=True)
    await ctx.send(embed=embed_resumen)

    # 2. Ordenar por Eficiencia
    ranking_pasado = sorted(datos_pasados.items(), key=lambda x: x[1]['eficiencia'], reverse=True)
    ranking_actual = sorted(datos_actuales.items(), key=lambda x: x[1]['eficiencia'], reverse=True)

    pos_pasadas_dict = {nombre: idx + 1 for idx, (nombre, datos) in enumerate(ranking_pasado)}
    lineas_reporte = []

    for idx, (nombre, datos) in enumerate(ranking_actual):
        pos_actual = idx + 1
        pos_pasada = pos_pasadas_dict.get(nombre)

        if pos_pasada:
            diferencia = pos_pasada - pos_actual
            if diferencia > 0: movimiento = f"⬆️{diferencia}"
            elif diferencia < 0: movimiento = f"⬇️{abs(diferencia)}"
            else: movimiento = "➖0"
        else:
            movimiento = "🆕"

        cd_fmt = f"{datos['c_diaria']:,}"
        prom_fmt = f"{datos['promedio']:,.0f}"
        pot_fmt = f"{datos['potencial']:,.1f}"
        
        # LÍNEA OPTIMIZADA (Sin vuelos)
        linea = f"**{pos_actual}.** {movimiento} | **{nombre}** (⚡**{datos['eficiencia']}%**) | 📊 CD:**{cd_fmt}** | Prom:**{prom_fmt}** | Pot:**{pot_fmt}**"
        lineas_reporte.append(linea)

    # Enviar el ranking general en bloques
    chunk_size = 15
    for idx_chunk, i in enumerate(range(0, len(lineas_reporte), chunk_size)):
        chunk = lineas_reporte[i:i + chunk_size]
        texto_bloque = "\n\n".join(chunk)
        
        if idx_chunk == 0:
            leyenda = (
                "📖 **Leyenda:** ⬆️/⬇️/➖ Movimiento | 🆕 Nueva | ⚡ % Eficiencia\n"
                "📊 **CD:** Contribución Diaria | **Prom:** Promedio C/D | **Pot:** Potencial C/D\n"
                "__________________________________________\n"
            )
            texto_bloque = leyenda + "\n" + texto_bloque

        embed_chunk = Embed(description=texto_bloque, color=discord.Color.blue())
        await ctx.send(embed=embed_chunk)


# --- NUEVO COMANDO: GRÁFICA DE EFICIENCIA ---
@bot.command(name='grafica_eficiencia')
async def grafica_eficiencia(ctx):
    historial = cargar_historial()
    
    if len(historial) < 2:
        await ctx.send("⚠️ Aún no hay suficientes datos históricos. Ejecuta al menos 2 reportes quincenales en fechas distintas.")
        return

    fechas = sorted(historial.keys())
    
    # Identificar todas las aerolíneas que existen en el historial
    aerolineas_todas = set()
    for datos_fecha in historial.values():
        aerolineas_todas.update(datos_fecha.keys())

    plt.figure(figsize=(10, 6))
    
    # Graficar cada aerolínea
    for aerolinea in aerolineas_todas:
        valores_y = []
        for fecha in fechas:
            # Si no estaba en esa fecha, ponemos None para que no conecte la línea
            eficiencia = historial[fecha].get(aerolinea, None)
            valores_y.append(eficiencia)
        
        # Solo graficamos si tiene al menos un dato válido
        if any(v is not None for v in valores_y):
            plt.plot(fechas, valores_y, marker='o', label=aerolinea)

    plt.title('Evolución de Eficiencia - HISPANA')
    plt.xlabel('Fechas de Reporte')
    plt.ylabel('% Eficiencia')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Ajustar la leyenda fuera del gráfico si son muchas aerolíneas
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small', ncol=2)
    plt.tight_layout()

    # Guardar gráfico en un buffer de memoria para enviarlo a Discord
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    archivo_discord = discord.File(buffer, filename='grafica_eficiencia.png')
    await ctx.send("📈 **Histórico de Eficiencia (Últimas 6 quincenas)**", file=archivo_discord)


keep_alive()
bot.run(os.environ['QUINCENAL_BOT_TOKEN'])
