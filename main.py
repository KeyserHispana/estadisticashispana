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
    
    # Guardamos la eficiencia y el promedio/potencial para tenerlos a mano en el historial
    datos_guardar = {}
    for nombre, datos in datos_actuales.items():
        datos_guardar[nombre] = {
            'eficiencia': datos['eficiencia'],
            'promedio': datos['promedio'],
            'potencial': datos['potencial']
        }
    
    historial[fecha] = datos_guardar
    
    # Mantener solo las últimas 6 fechas registradas
    fechas_ordenadas = sorted(historial.keys())
    if len(fechas_ordenadas) > 6:
        fechas_a_borrar = fechas_ordenadas[:-6]
        for f in fechas_a_borrar:
            del historial[f]
            
    with open(ARCHIVO_HISTORIAL, 'w', encoding='utf-8') as f:
        json.dump(historial, f, indent=4)

# --- CARGA DE DATOS TXT CON FECHA INCORPORADA ---
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
            
            # Formato Alianza: ALIANZA, YYYY-MM-DD, Rango, Valor, Crecimiento
            if partes[0].strip().upper() == 'ALIANZA' and len(partes) >= 5:
                try:
                    datos_alianza = {
                        'fecha': partes[1].strip(),
                        'rank': int(partes[2]),
                        'valor': float(partes[3]),
                        'crecimiento_diario': float(partes[4])
                    }
                except ValueError:
                    pass
                continue
                
            # Formato Aerolínea: Nombre, Eficiencia, Promedio, Potencial
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
        
    if not alianza_actual or 'fecha' not in alianza_actual:
        await ctx.send("⚠️ El archivo `quincena_actual.txt` debe incluir la fecha en la línea de la ALIANZA (Ej: `ALIANZA, 2026-09-09, 109...`).")
        return

    # --- GESTIÓN DE MEMORIA USANDO LA FECHA DEL ARCHIVO ---
    fecha_reporte_actual = alianza_actual['fecha']
    
    historial_temp = cargar_historial()
    if len(historial_temp) == 0 and alianza_pasada and 'fecha' in alianza_pasada:
        guardar_en_historial(alianza_pasada['fecha'], datos_pasados)
        
    guardar_en_historial(fecha_reporte_actual, datos_actuales)
    # ----------------------------------------------------

    f_pasada = alianza_pasada.get('fecha', 'Anterior') if alianza_pasada else 'Anterior'
    f_actual = alianza_actual.get('fecha', 'Actual')

    embed_resumen = Embed(title="📊 Reporte Quincenal HISPANA", color=discord.Color.green())
    if alianza_pasada and alianza_actual:
        avance_rank = alianza_pasada['rank'] - alianza_actual['rank']
        icono_rank = "⬆️" if avance_rank > 0 else "⬇️" if avance_rank < 0 else "➖"
        embed_resumen.add_field(name="🏆 Ranking Global", value=f"{f_pasada}: **{alianza_pasada['rank']}**\n{f_actual}: **{alianza_actual['rank']}**\nMovimiento: {icono_rank} **{abs(avance_rank)}**", inline=True)
        
        crecimiento_total = alianza_actual['valor'] - alianza_pasada['valor']
        icono_val = "📈" if crecimiento_total > 0 else "📉"
        embed_resumen.add_field(name="💰 Valor de Alianza", value=f"{f_pasada}: **${alianza_pasada['valor']:,.2f}**\n{f_actual}: **${alianza_actual['valor']:,.2f}**\nCrecimiento: {icono_val} **${crecimiento_total:,.2f}**", inline=True)
        
        diff_crecimiento = alianza_actual['crecimiento_diario'] - alianza_pasada['crecimiento_diario']
        icono_crec = "🚀" if diff_crecimiento > 0 else "⚠️"
        embed_resumen.add_field(name="📊 Crecimiento Diario", value=f"{f_pasada}: **${alianza_pasada['crecimiento_diario']:,.2f}**\n{f_actual}: **${alianza_actual['crecimiento_diario']:,.2f}**\nVariación: {icono_crec} **${diff_crecimiento:,.2f}**", inline=True)
        
    await ctx.send(embed=embed_resumen)

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
        
        linea = f"**{pos_actual}.** {movimiento} | **{nombre}** (⚡**{datos['eficiencia']}%**) | Prom:**{prom_fmt}** | Pot:**{pot_fmt}**"
        lineas_reporte.append(linea)

    ranking_para_podios = [item for item in ranking_actual if item[0].lower() != 'keyser' and item[0] in pos_pasadas_dict]
    movimientos_sin_keyser = [x for x in movimientos_lista if x['nombre'].lower() != 'keyser']

    los_que_subieron = sorted([x for x in movimientos_sin_keyser if x['dif'] > 0], key=lambda x: x['dif'], reverse=True)
    los_que_bajaron = sorted([x for x in movimientos_sin_keyser if x['dif'] < 0], key=lambda x: x['dif']) 

    top3_eficientes = ranking_para_podios[:3]
    top3_menos_eficientes = ranking_para_podios[-3:]
    top3_menos_eficientes.reverse() 

    top3_subieron = los_que_subieron[:3]
    top3_bajaron = los_que_bajaron[:3]

    embed_tops = Embed(title=f"🏆 Podios de la Quincena ({f_actual})", color=discord.Color.gold())

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


# --- COMANDO PÚBLICO 1: TARJETA DE AEROLÍNEA CON HISTORIAL (MÁX. 3 QUINCENAS) ---
@bot.command(name='mi_aerolinea')
async def mi_aerolinea(ctx, *, nombre_buscado: str = None):
    if not nombre_buscado:
        await ctx.send("⚠️ Debes indicar el nombre de la aerolínea. Ejemplo: `!mi_aerolinea Fly Aces`")
        return

    _, datos_actuales = cargar_datos_quincena('quincena_actual.txt')
    if not datos_actuales:
        await ctx.send("⚠️ No hay datos actuales cargados en el sistema.")
        return

    # Buscar coincidencia flexible
    nombre_encontrado = None
    for nom in datos_actuales.keys():
        if nombre_buscado.strip().lower() == nom.lower():
            nombre_encontrado = nom
            break

    if not nombre_encontrado:
        await ctx.send(f"❌ No se encontró ninguna aerolínea con el nombre **'{nombre_buscado}'** en el registro actual.")
        return

    # Cargar el historial completo desde el JSON
    historial = cargar_historial()
    fechas_ordenadas = sorted(historial.keys())

    # Tomar un máximo de las últimas 3 fechas disponibles
    ultimas_fechas = fechas_ordenadas[-3:] if len(fechas_ordenadas) >= 3 else fechas_ordenadas

    # Construir el bloque de estadísticas históricas
    historial_texto = ""
    for fecha in ultimas_fechas:
        datos_en_fecha = historial[fecha]
        if nombre_encontrado in datos_en_fecha:
            eficiencia_h = datos_en_fecha[nombre_encontrado]['eficiencia']
            
            # Calcular ranking que tenía en esa fecha específica
            ordenados_h = sorted(datos_en_fecha.items(), key=lambda x: x[1]['eficiencia'], reverse=True)
            puesto_h = next((idx + 1 for idx, (nom, _) in enumerate(ordenados_h) if nom == nombre_encontrado), "N/A")
            
            historial_texto += f"• **{fecha}**: Puesto **#{puesto_h}** | Eficiencia: **{eficiencia_h}%**\n"
        else:
            historial_texto += f"• **{fecha}**: *Sin registro*\n"

    # Datos actuales para el resumen rápido
    ranking_actual = sorted(datos_actuales.items(), key=lambda x: x[1]['eficiencia'], reverse=True)
    pos_actual = next(idx + 1 for idx, (nom, _) in enumerate(ranking_actual) if nom == nombre_encontrado)
    datos_aerolinea = datos_actuales[nombre_encontrado]

    embed = Embed(title=f"✈️ Reporte Histórico: {nombre_encontrado}", color=discord.Color.blue())
    embed.add_field(name="🏆 Posición Actual", value=f"**#{pos_actual}**", inline=True)
    embed.add_field(name="⚡ Eficiencia Actual", value=f"**{datos_aerolinea['eficiencia']}%**", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    embed.add_field(name="📊 Promedio C/D Actual", value=f"${datos_aerolinea['promedio']:,.0f}", inline=True)
    embed.add_field(name="🚀 Potencial C/D Actual", value=f"${datos_aerolinea['potencial']:,.1f}", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    embed.add_field(name="📈 Evolución (Últimas Quincenas)", value=historial_texto if historial_texto else "Aún no hay suficiente historial guardado.", inline=False)

    await ctx.send(embed=embed)


# --- COMANDO PÚBLICO 2: DUELO QUINCENAL (!enfrentar [A] vs [B]) ---
@bot.command(name='enfrentar')
async def enfrentar(ctx, *, texto_duelo: str = None):
    if not texto_duelo or 'vs' not in texto_duelo.lower():
        await ctx.send("⚠️ Formato incorrecto. Debes usar: `!enfrentar Aerolinea A vs Aerolinea B`")
        return

    partes = texto_duelo.split('vs' if 'vs' in texto_duelo else 'VS')
    if len(partes) != 2:
        partes = texto_duelo.lower().split('vs')
        
    if len(partes) != 2:
        await ctx.send("⚠️ No se pudo interpretar el duelo. Usa el formato: `!enfrentar Aerolinea A vs Aerolinea B`")
        return

    busq_a = partes[0].strip()
    busq_b = partes[1].strip()

    _, datos_actuales = cargar_datos_quincena('quincena_actual.txt')
    if not datos_actuales:
        await ctx.send("⚠️ No hay datos actuales cargados.")
        return

    nom_a = next((nom for nom in datos_actuales.keys() if busq_a.lower() == nom.lower()), None)
    nom_b = next((nom for nom in datos_actuales.keys() if busq_b.lower() == nom.lower()), None)

    if not nom_a or not nom_b:
        await ctx.send(f"❌ No se pudo encontrar a una o ambas aerolíneas en el registro. Asegúrate de escribir bien los nombres.\n- Buscaste: **{busq_a}** y **{busq_b}**")
        return

    ranking_actual = sorted(datos_actuales.items(), key=lambda x: x[1]['eficiencia'], reverse=True)
    pos_a = next(idx + 1 for idx, (nom, _) in enumerate(ranking_actual) if nom == nom_a)
    pos_b = next(idx + 1 for idx, (nom, _) in enumerate(ranking_actual) if nom == nom_b)

    d_a = datos_actuales[nom_a]
    d_b = datos_actuales[nom_b]

    embed = Embed(title=f"⚔️ Duelo Quincenal: {nom_a} vs {nom_b}", color=discord.Color.purple())
    
    embed.add_field(name=f"🛫 {nom_a}", value=f"• Puesto: **#{pos_a}**\n• Eficiencia: **{d_a['eficiencia']}%**\n• Prom: **${d_a['promedio']:,.0f}**\n• Pot: **${d_a['potencial']:,.1f}**", inline=True)
    embed.add_field(name=f"🛫 {nom_b}", value=f"• Puesto: **#{pos_b}**\n• Eficiencia: **{d_b['eficiencia']}%**\n• Prom: **${d_b['promedio']:,.0f}**\n• Pot: **${d_b['potencial']:,.1f}**", inline=True)

    if d_a['eficiencia'] > d_b['eficiencia']:
        ganador_txt = f"🏆 **Ganador en Eficiencia:** {nom_a} (+{d_a['eficiencia'] - d_b['eficiencia']}% vs {nom_b})"
    elif d_b['eficiencia'] > d_a['eficiencia']:
        ganador_txt = f"🏆 **Ganador en Eficiencia:** {nom_b} (+{d_b['eficiencia'] - d_a['eficiencia']}% vs {nom_a})"
    else:
        ganador_txt = "🤝 **Empate técnico** en porcentaje de eficiencia."

    embed.add_field(name="📊 Resultado del Enfrentamiento", value=ganador_txt, inline=False)

    await ctx.send(embed=embed)


# --- COMANDO: GRÁFICA DE RANKING CON FECHAS REALES ---
@bot.command(name='grafica_eficiencia')
async def grafica_eficiencia(ctx):
    historial = cargar_historial()
    
    if len(historial) < 2:
        await ctx.send("⚠️ Aún no hay suficientes datos históricos. El bot necesita tener guardadas al menos 2 quincenas para comparar.")
        return

    fechas = sorted(historial.keys())
    fecha_actual = fechas[-1]
    fecha_anterior = fechas[-2]
    
    rankings_por_fecha = {}
    for fecha in fechas:
        datos_fecha = {a: d['eficiencia'] for a, d in historial[fecha].items() if d is not None}
        ordenados = sorted(datos_fecha.items(), key=lambda x: x[1], reverse=True)
        rankings_por_fecha[fecha] = {item[0]: idx + 1 for idx, item in enumerate(ordenados)}
        
    ranking_actual_ordenado = sorted(rankings_por_fecha[fecha_actual].items(), key=lambda x: x[1])
    aerolineas_actuales = [a for a, r in ranking_actual_ordenado]
    
    altura_figura = max(8, len(aerolineas_actuales) * 0.4) 
    fig, ax = plt.subplots(figsize=(12, altura_figura))
    
    for aerolinea in aerolineas_actuales:
        valores_y = []
        fechas_plot = []
        for fecha in fechas:
            rank = rankings_por_fecha[fecha].get(aerolinea)
            if rank is not None:
                valores_y.append(rank)
                fechas_plot.append(fecha)
        
        if len(valores_y) > 0:
            ax.plot(fechas_plot, valores_y, marker='o', linewidth=2)

    ax.invert_yaxis() 
    
    ticks_y = []
    etiquetas_y = []
    
    for aerolinea, rank_actual in ranking_actual_ordenado:
        ticks_y.append(rank_actual)
        
        rank_anterior = rankings_por_fecha[fecha_anterior].get(aerolinea)
        eficiencia_actual = historial[fecha_actual][aerolinea]['eficiencia'] if aerolinea in historial[fecha_actual] else 0
        
        if rank_anterior is not None:
            diferencia = rank_anterior - rank_actual
            if diferencia > 0:
                mov = f"(▲ {diferencia})"
            elif diferencia < 0:
                mov = f"(▼ {abs(diferencia)})"
            else:
                mov = "(=)"
        else:
            mov = "(Nuevo)"
            
        etiquetas_y.append(f"{rank_actual}. {aerolinea}  {mov}  [{eficiencia_actual}%]")
        
    ax.set_yticks(ticks_y)
    ax.set_yticklabels([str(t) for t in ticks_y], fontsize=10, color='gray')
    
    ax2 = ax.twinx()
    ax2.set_ylim(ax.get_ylim())
    ax2.set_yticks(ticks_y)
    ax2.set_yticklabels(etiquetas_y, fontsize=10, weight='bold')
    
    plt.title('Evolución de Posiciones en HISPANA - Ranking de Eficiencia', fontsize=16, pad=20, weight='bold')
    ax.grid(True, linestyle='--', alpha=0.5, axis='x') 
    
    for spine in ['top', 'bottom', 'right', 'left']:
        ax.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
        
    ax.tick_params(axis='y', length=0)
    ax2.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', color='gray')
    
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    plt.close(fig)

    archivo_discord = discord.File(buffer, filename='grafica_posiciones.png')
    await ctx.send("📈 **Evolución del Ranking Interno (Basado en Eficiencia)**", file=archivo_discord)


keep_alive()
bot.run(os.environ['QUINCENAL_BOT_TOKEN'])
