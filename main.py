from flask import Flask
from threading import Thread
import os
import discord
from discord.ext import commands
from discord import Embed

app = Flask('')

@app.route('/')
def home():
    return "Bot de Estadisticas activo 24/7"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

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
            
            # Identificar la línea de datos generales de la alianza
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
                
            # Procesar aerolíneas normales
            if len(partes) >= 5:
                nombre = partes[0].strip()
                try:
                    acciones = float(partes[1])
                    vuelos = int(partes[2])
                    c_diaria = int(partes[3])
                    eficiencia = int(partes[4])
                    
                    datos_aerolineas[nombre] = {
                        'acciones': acciones,
                        'vuelos': vuelos,
                        'c_diaria': c_diaria,
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

    # 1. Crear el Resumen General de la Alianza
    embed_resumen = Embed(title="📊 Reporte Quincenal HISPANA", color=discord.Color.green())
    
    if alianza_pasada and alianza_actual:
        # Ranking
        avance_rank = alianza_pasada['rank'] - alianza_actual['rank']
        icono_rank = "⬆️" if avance_rank > 0 else "⬇️" if avance_rank < 0 else "➖"
        embed_resumen.add_field(name="🏆 Ranking Global", value=f"Anterior: **{alianza_pasada['rank']}**\nActual: **{alianza_actual['rank']}**\nMovimiento: {icono_rank} **{abs(avance_rank)}**", inline=True)
        
        # Valor de Alianza
        crecimiento_total = alianza_actual['valor'] - alianza_pasada['valor']
        icono_val = "📈" if crecimiento_total > 0 else "📉"
        embed_resumen.add_field(name="💰 Valor de Alianza", value=f"Anterior: **${alianza_pasada['valor']:,.2f}**\nActual: **${alianza_actual['valor']:,.2f}**\nCrecimiento: {icono_val} **${crecimiento_total:,.2f}**", inline=True)
        
        # Crecimiento Diario
        diff_crecimiento = alianza_actual['crecimiento_diario'] - alianza_pasada['crecimiento_diario']
        icono_crec = "🚀" if diff_crecimiento > 0 else "⚠️"
        embed_resumen.add_field(name="📊 Crecimiento Diario", value=f"Anterior: **${alianza_pasada['crecimiento_diario']:,.2f}**\nActual: **${alianza_actual['crecimiento_diario']:,.2f}**\nVariación: {icono_crec} **${diff_crecimiento:,.2f}**", inline=True)
    else:
        embed_resumen.description = "⚠️ No se encontraron los datos de la línea 'ALIANZA' al inicio de los archivos."

    await ctx.send(embed=embed_resumen)

    # 2. Ordenar por Eficiencia y generar ranking interno
    ranking_pasado = sorted(datos_pasados.items(), key=lambda x: x[1]['eficiencia'], reverse=True)
    ranking_actual = sorted(datos_actuales.items(), key=lambda x: x[1]['eficiencia'], reverse=True)

    pos_pasadas_dict = {nombre: idx + 1 for idx, (nombre, datos) in enumerate(ranking_pasado)}

    lineas_reporte = []
    for idx, (nombre, datos) in enumerate(ranking_actual):
        pos_actual = idx + 1
        pos_pasada = pos_pasadas_dict.get(nombre)

        if pos_pasada:
            diferencia = pos_pasada - pos_actual
            if diferencia > 0:
                movimiento = f"⬆️ {diferencia}"
            elif diferencia < 0:
                movimiento = f"⬇️ {abs(diferencia)}"
            else:
                movimiento = "➖ 0"
        else:
            movimiento = "🆕"

        vuelos_fmt = f"{datos['vuelos']:,}"
        cd_fmt = f"{datos['c_diaria']:,}"
        acciones_fmt = f"{datos['acciones']:,.2f}"
        
        linea = f"**{pos_actual}.** {movimiento} | **{nombre}** | Acc: ${acciones_fmt} | Vuelos: {vuelos_fmt} | C/D: {cd_fmt} | Efi: **{datos['eficiencia']}%**"
        lineas_reporte.append(linea)

    # 3. Enviar el ranking interno en bloques
    chunk_size = 15
    for i in range(0, len(lineas_reporte), chunk_size):
        chunk = lineas_reporte[i:i + chunk_size]
        embed_chunk = Embed(description="\n".join(chunk), color=discord.Color.blue())
        await ctx.send(embed=embed_chunk)

keep_alive()
bot.run(os.environ['QUINCENAL_BOT_TOKEN'])
