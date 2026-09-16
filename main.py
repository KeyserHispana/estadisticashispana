from flask import Flask
from threading import Thread
import os
import discord
from discord.ext import commands
from discord import Embed
import json
import matplotlib
matplotlib.use('Agg') # Requerido para servidores sin interfaz gráfica como Render
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
    
    # Extraer solo la eficiencia
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
                
            # FORMATO EXACTO: Nombre, Eficiencia, Promedio, Potencial
            if len(partes) >= 4:
                nombre = partes[0].strip()
                try:
                    eficiencia = int(partes[1])
                    promedio = float(partes[2])
                    potencial = float(partes[3])
                    
                    datos_aerolineas[nombre] = {
                        'eficiencia': eficiencia,
                        'promedio': promedio,
                        'potencial': potencial
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
        
    # Guardar en la memoria histórica automáticamente
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    guardar_en_historial(fecha_hoy, datos_actuales)

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
    movimientos_lista = [] 

    for idx, (nombre, datos) in enumerate(ranking_actual):
        pos_actual = idx + 1
        pos_pasada = pos_pasadas_dict.get(nombre)

        if pos_pasada:
            diferencia = pos_pasada - pos_actual
            movimientos_lista.append({'nombre': nombre, 'dif': diferencia})
            
            if diferencia > 0: movimiento = f"⬆️{diferencia}"
            elif diferencia < 0: movimiento = f"⬇️{abs(diferencia)}"
            else: movimiento = "➖0"
        else:
            movimiento = "🆕"

        prom_fmt = f"{datos['promedio']:,.0f}"
        pot_fmt = f"{datos['potencial']:,.1f}"
        
        # LINEA OPTIMIZADA: Solo Eficiencia, Promedio y Potencial
        linea = f"**{pos_actual}.** {movimiento} | **{nombre}** (⚡**{datos['eficiencia']}%**) | Prom:**{prom_fmt}** | Pot:**{pot_fmt}**"
        lineas_reporte.append(linea)

    # 3. CREAR LOS PODIOS EXCLUYENDO A KEYSER Y A LOS NUEVOS
    ranking_para_podios = [item for item in ranking_actual if item[0].lower() != 'keyser' and item[0] in pos_pasadas_dict]
    movimientos_sin_keyser = [x for x in movimientos_lista if x['nombre'].lower() != 'keyser']

    los_que_subieron = sorted([x for x in movimientos_sin_keyser if x['dif'] > 0], key=lambda x: x['dif'], reverse=True)
    los_que_bajaron = sorted([x for x in movimientos_sin_keyser if x['dif'] < 0], key=lambda x: x['dif']) 

    top3_eficientes = ranking_para_podios[:3]
    top3_menos_eficientes = ranking_para_podios[-3:]
    top3_menos_eficientes.reverse() 

    top3_subieron = los_que_subieron[:3]
    top3_bajaron = los_que_bajaron[:3]

    embed_tops = Embed(title="🏆 Podios de la Quincena", color=discord.Color.gold())

    txt_top_efi = "".join([f"**{i+1}.** {nom} (**{dat['eficiencia']}%**)\n" for i, (nom, dat) in enumerate(top3_eficientes)])
    embed_tops.add_field(name="🌟 Más Eficientes", value=txt_top_efi if txt_top_efi else "N/A", inline=True)

    txt_bot_efi = "".join([f"**{i+1}.** {nom} (**{dat['eficiencia']}%**)\n" for i, (nom, dat) in enumerate(top3_menos_eficientes)])
    embed_tops.add_field(name="🐌 Menos Eficientes", value=txt_bot_efi if txt_bot_efi else "N/A", inline=True)
    
    embed_tops.add_field(name="\u200b", value="\u200b", inline=False) 

    txt_top_sub = "".join([f"**{i+1}.** {item['nombre']} (⬆️{item['dif']})\n" for i, item in enumerate(top3_subieron)])
    embed_tops.add_field(name="🚀 Más Avanzaron", value=txt_top_sub if txt_top_sub else "Nadie avanzó", inline=True)

    txt_top_baj = "".join([f"**{i+1}.** {item['nombre']} (⬇️{abs(item['dif'])})\n" for i, item in enumerate(top3_bajaron)])
    embed_tops.add_field(name="📉 Más Cayeron", value=txt_top_baj if txt_top_baj else "Nadie cayó", inline=True)

    await ctx.send(embed=embed_tops)

    # 4. Enviar el ranking general
    chunk_size = 15
    for idx_chunk, i in enumerate(range(0, len(lineas_reporte), chunk_size)):
        chunk = lineas_reporte[i:i + chunk_size]
        texto_bloque = "\n\n".join(chunk)
        
        if idx_chunk == 0:
            leyenda = (
                "📖 **Leyenda:** ⬆️/⬇️/➖ Movimiento | 🆕 Nueva | ⚡ % Eficiencia\n"
                "📊 **Prom:** Promedio C/D | **Pot:** Potencial C/D\n"
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
        await ctx.send("⚠️ Aún no hay suficientes datos históricos. El bot necesita tener guardadas al menos 2 quincenas para comparar.")
        return

    fechas = sorted(historial.keys())
    
    aerolineas_todas = set()
    for datos_fecha in historial.values():
        aerolineas_todas.update(datos_fecha.keys())

    plt.figure(figsize=(10, 6))
    
    for aerolinea in aerolineas_todas:
        valores_y = []
        for fecha in fechas:
            eficiencia = historial[fecha].get(aerolinea, None)
            valores_y.append(eficiencia)
        
        if any(v is not None for v in valores_y):
            plt.plot(fechas, valores_y, marker='o', label=aerolinea)

    plt.title('Evolución de Eficiencia - HISPANA')
    plt.xlabel('Fechas de Reporte')
    plt.ylabel('% Eficiencia')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small', ncol=2)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    archivo_discord = discord.File(buffer, filename='grafica_eficiencia.png')
    await ctx.send("📈 **Histórico de Eficiencia (Últimas 6 quincenas)**", file=archivo_discord)


keep_alive()
bot.run(os.environ['QUINCENAL_BOT_TOKEN'])
