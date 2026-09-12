from flask import Flask
from threading import Thread
import os
import discord
from discord.ext import commands
from discord import Embed

# --- Servidor Flask para UptimeRobot ---
app = Flask('')

@app.route('/')
def home():
    return "Bot de Estadisticas activo 24/7"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Función para cargar los datos de las aerolíneas ---
def cargar_datos_quincena(nombre_archivo):
    datos = {}
    if not os.path.exists(nombre_archivo):
        return datos
        
    with open(nombre_archivo, 'r', encoding='utf-8') as f:
        for linea in f:
            if not linea.strip() or linea.startswith('AEROLINEA'):
                continue
                
            partes = linea.strip().split(',')
            if len(partes) >= 5:
                nombre = partes[0].strip()
                try:
                    acciones = float(partes[1])
                    vuelos = int(partes[2])
                    c_diaria = int(partes[3])
                    eficiencia = int(partes[4])
                    
                    datos[nombre] = {
                        'acciones': acciones,
                        'vuelos': vuelos,
                        'c_diaria': c_diaria,
                        'eficiencia': eficiencia
                    }
                except ValueError:
                    continue # Ignora valores rotos y pasa al siguiente
                    
    return datos

# --- Configuración del Bot ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"Bot de Estadisticas conectado como {bot.user}")

@bot.command(name='reporte_quincena')
async def reporte_quincena(ctx):
    datos_pasados = cargar_datos_quincena('quincena_pasada.txt')
    datos_actuales = cargar_datos_quincena('quincena_actual.txt')
    
    if not datos_pasados or not datos_actuales:
        await ctx.send("⚠️ Faltan datos en los archivos de texto. Revisa que estén completos.")
        return

    # Por ahora, confirmamos la lectura exitosa (Luego agregaremos los cálculos del ranking)
    total_pasadas = len(datos_pasados)
    total_actuales = len(datos_actuales)
    
    await ctx.send(f"✅ ¡Datos cargados correctamente!\nAerolíneas registradas hace 15 días: **{total_pasadas}**\nAerolíneas actuales registradas: **{total_actuales}**\n\n*(Todo listo para programar los cálculos del ranking en el siguiente paso).*")

# --- Mantiene el bot vivo y se conecta a Discord ---
keep_alive()
bot.run(os.environ['QUINCENAL_BOT_TOKEN'])
