from flask import Flask
from threading import Thread
import os
import discord
from discord.ext import commands
from discord import Embed

# --- Servidor Flask para UptimeRobot (Puerto único para este bot) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot Quincenal de Alianzas activo 24/7"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Configuración del Bot de Discord ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"Bot Quincenal conectado como {bot.user}")

@bot.command(name='reporte_quincena')
async def reporte_quincena(ctx):
    # Aquí programaremos la lógica de lectura, comparación y generación de Embeds
    await ctx.send("📊 El sistema quincenal está listo. Esperando datos...")

# Mantener vivo el servidor web
keep_alive()

# Token independiente para este bot (puedes usar otra variable de entorno en Render)
bot.run(os.environ['QUINCENAL_BOT_TOKEN'])
