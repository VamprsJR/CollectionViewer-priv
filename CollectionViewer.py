import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
# Importamos 'timezone' para manejo de UTC
from datetime import datetime, timedelta, timezone
import time

# Asegúrate de que esta línea esté al inicio, después de los imports:
load_dotenv()

# Reemplaza 'TU_TOKEN_DE_BOT' con el token real
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# ----------------------------------------------------
# VARIABLES DEL CICLO (AJUSTADO)
# ----------------------------------------------------
INTERVALO_ITEM_MINUTOS = 20
CICLO_TOTAL_ITEMS = 26

# DURACIÓN AJUSTADA: 8h, 25m, 3s (505 minutos y 3 segundos) para corregir el desfase.
DURACION_CICLO_TOTAL = timedelta(hours=8, minutes=25, seconds=3)

# Almacenamiento: El tiempo base siempre se guarda en UTC (Universal)
ULTIMO_HORARIO_REGISTRO_UTC = None

@bot.event
async def on_ready():
    print(f'Bot iniciado como {bot.user}')
    await bot.change_presence(activity=discord.Game(name="Rastreando Ciclos Globales"))

# ----------------------------------------------------
# COMANDO: Establece el tiempo de partida
# ----------------------------------------------------
@bot.command(name='set_horario', help='Establece el horario del ÚLTIMO reset/aparición. Formato: HH:MM.')
async def set_horario(ctx, hora_str: str):
    global ULTIMO_HORARIO_REGISTRO_UTC
    
    try:
        hora, minuto = map(int, hora_str.split(':'))
        
        # 1. Creamos un datetime ingenuo (naive)
        ahora_local = datetime.now() 
        registro_local = ahora_local.replace(hour=hora, minute=minuto, second=0, microsecond=0)

        # Si ya pasó hoy, asumimos que fue ayer
        if registro_local > ahora_local:
            registro_local -= timedelta(days=1)
        
        # 2. Convertimos el tiempo ingenuo a un tiempo consciente (aware) de la zona horaria del sistema,
        # y luego lo convertimos a UTC.
        registro_aware = registro_local.astimezone() 
        ULTIMO_HORARIO_REGISTRO_UTC = registro_aware.astimezone(timezone.utc)
        
        # Verificación en el canal
        await ctx.send(f'✅ **Horario de partida fijado!** El ciclo base se guardó como `{ULTIMO_HORARIO_REGISTRO_UTC.strftime("%H:%M:%S")} UTC`.')
        
        await mostrar_horarios(ctx)
        
    except Exception as e:
        await ctx.send(f"❌ Error al establecer el horario. Asegúrate de usar HH:MM. Error: {e}")

# ----------------------------------------------------
# COMANDO DE VISUALIZACIÓN (CON AJUSTE DE TIEMPO)
# ----------------------------------------------------
@bot.command(name='ver_horarios', help='Muestra las próximas 5 finalizaciones de los 26 ciclos en la hora local de cada usuario.')
async def mostrar_horarios(ctx):
    global ULTIMO_HORARIO_REGISTRO_UTC
    
    if ULTIMO_HORARIO_REGISTRO_UTC is None:
        await ctx.send('El ciclo de partida no ha sido configurado globalmente. Usa `!set_horario`.')
        return

    # Se usa UTC para todos los cálculos
    # 1. Primera vez que se usa la duración ajustada
    proximo_fin_de_ciclo_utc = ULTIMO_HORARIO_REGISTRO_UTC + DURACION_CICLO_TOTAL 
    ahora_utc = datetime.now(timezone.utc)

    # Saltamos hacia adelante en bloques UTC
    while proximo_fin_de_ciclo_utc <= ahora_utc:
        # 2. Se usa la duración ajustada para saltar ciclos
        proximo_fin_de_ciclo_utc += DURACION_CICLO_TOTAL 

    mensaje = f"**🌍 Próximas 5 Finalizaciones de Ciclo (Hora Local para ti):**\n"
    
    # Generamos los próximos 5 horarios
    for i in range(1, 6): 
        
        # Convertir el datetime UTC a UNIX Timestamp (necesario para Discord)
        timestamp = int(proximo_fin_de_ciclo_utc.timestamp()) 
        # Formato de Discord: <t:timestamp:f> (muestra fecha y hora local)
        discord_timestamp = f'<t:{timestamp}:f>'
        
        # Calcular tiempo restante
        tiempo_restante = proximo_fin_de_ciclo_utc - ahora_utc
        
        total_segundos = int(tiempo_restante.total_seconds())
        horas = total_segundos // 3600
        minutos = (total_segundos % 3600) // 60
        segundos = total_segundos % 60
        
        tiempo_restante_str = f"Quedan: **{horas}h {minutos}m {segundos}s**"
        
        mensaje += f"Ciclo #{i}: {discord_timestamp} ({tiempo_restante_str})\n"
        
        # 3. Se usa la duración ajustada para el siguiente ciclo en el bucle
        proximo_fin_de_ciclo_utc += DURACION_CICLO_TOTAL 
        
    await ctx.send(mensaje)

# La línea final de ejecución ahora lee el token de una variable de entorno
bot.run(os.getenv('DISCORD_TOKEN'))
