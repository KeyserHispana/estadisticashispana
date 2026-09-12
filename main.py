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

    # 1. Resumen General de la Alianza
    embed_resumen = Embed(title="📊 Reporte Quincenal HISPANA", color=discord.Color.green())
    
    if alianza_pasada and alianza_actual:
        avance_rank = alianza_pasada['rank'] - alianza_actual['rank']
        icono_rank = "⬆️" if avance_rank > 0 else "⬇️" if avance_rank < 0 else "➖"
        embed_resumen.add_field(name="🏆 Ranking Global", value=f"Anterior: **{alianza_pasada['rank']}**\nActual: **{alianza_actual['rank']}**\nMovimiento: {icono_rank} **{abs(avance_rank)}**", inline=True)
        
        crecimiento_total = alianza_actual['valor'] - alianza_pasada['valor']
        icono_val = "📈" if crecimiento_total > 0 else "📉"
        embed_resumen.add_field(name="💰 Valor de Alianza", value=f"Anterior: **${alianza_pasada['valor']:,.2f}**\nActual: **${alianza_actual['valor']:,.2f}**\nCrecimiento: {icono_val} **${crecimiento_total:,.2f}**", inline=True)
        
        diff_crecimiento = alianza_actual['crecimiento_diario'] - alianza_pasada['crecimiento_diario']
        icono_crec = "🚀" if diff_crecimiento > 0 else "⚠️"
        embed_resumen.add_field(name="📊 Crecimiento Diario", value=f"Anterior: **${alianza_pasada['crecimiento_diario']:,.2f}**\nActual: **${alianza_actual['crecimiento_diario']:,.2f}**\nVariación: {icono_crec} **${diff_crecimiento:,.2f}**", inline=True)
    
    await ctx.send(embed=embed_resumen)

    # 2. Ordenar por Eficiencia y generar ranking interno
    ranking_pasado = sorted(datos_pasados.items(), key=lambda x: x[1]['eficiencia'], reverse=True)
    ranking_actual = sorted(datos_actuales.items(), key=lambda x: x[1]['eficiencia'], reverse=True)

    pos_pasadas_dict = {nombre: idx + 1 for idx, (nombre, datos) in enumerate(ranking_pasado)}

    lineas_reporte = []
    movimientos_lista = [] # Aquí guardaremos quién subió y quién bajó

    for idx, (nombre, datos) in enumerate(ranking_actual):
        pos_actual = idx + 1
        pos_pasada = pos_pasadas_dict.get(nombre)

        if pos_pasada:
            diferencia = pos_pasada - pos_actual
            movimientos_lista.append({'nombre': nombre, 'dif': diferencia}) # Guardar para los Tops
            
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

    # 3. CREAR LOS PODIOS (Tops)
    # Filtrar y ordenar movimientos
    los_que_subieron = sorted([x for x in movimientos_lista if x['dif'] > 0], key=lambda x: x['dif'], reverse=True)
    los_que_bajaron = sorted([x for x in movimientos_lista if x['dif'] < 0], key=lambda x: x['dif']) # Ordena de más negativo a menos negativo

    # Seleccionar Top 3
    top3_eficientes = ranking_actual[:3]
    
    # Tomamos los 3 últimos del ranking, y los invertimos para que el de hasta abajo (el peor) salga de primero
    top3_menos_eficientes = ranking_actual[-3:]
    top3_menos_eficientes.reverse() 

    top3_subieron = los_que_subieron[:3]
    top3_bajaron = los_que_bajaron[:3]

    # Armar visualmente el panel de Podios
    embed_tops = Embed(title="🏆 Podios de la Quincena", color=discord.Color.gold())

    txt_top_efi = "".join([f"**{i+1}. {nom}** ({dat['eficiencia']}%) \n" for i, (nom, dat) in enumerate(top3_eficientes)])
    embed_tops.add_field(name="🌟 Más Eficientes", value=txt_top_efi, inline=True)

    txt_bot_efi = "".join([f"**{i+1}. {nom}** ({dat['eficiencia']}%) \n" for i, (nom, dat) in enumerate(top3_menos_eficientes)])
    embed_tops.add_field(name="🐌 Menos Eficientes", value=txt_bot_efi, inline=True)
    
    # Campo vacío para forzar que los siguientes caigan en la siguiente fila (estética)
    embed_tops.add_field(name="\u200b", value="\u200b", inline=False) 

    txt_top_sub = "".join([f"**{i+1}. {item['nombre']}** (⬆️ {item['dif']} puestos)\n" for i, item in enumerate(top3_subieron)])
    embed_tops.add_field(name="🚀 Más Avanzaron", value=txt_top_sub if txt_top_sub else "Nadie avanzó", inline=True)

    txt_top_baj = "".join([f"**{i+1}. {item['nombre']}** (⬇️ {abs(item['dif'])} puestos)\n" for i, item in enumerate(top3_bajaron)])
    embed_tops.add_field(name="📉 Más Cayeron", value=txt_top_baj if txt_top_baj else "Nadie cayó", inline=True)

    await ctx.send(embed=embed_tops)

    # 4. Enviar el ranking interno en bloques
    chunk_size = 15
    for i in range(0, len(lineas_reporte), chunk_size):
        chunk = lineas_reporte[i:i + chunk_size]
        embed_chunk = Embed(description="\n".join(chunk), color=discord.Color.blue())
        await ctx.send(embed=embed_chunk)

keep_alive()
bot.run(os.environ['QUINCENAL_BOT_TOKEN'])
