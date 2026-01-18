import discord
from discord.ext import tasks
import requests
import os
import sys
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=" * 50)
logger.info("Starting bot initialization...")
logger.info("=" * 50)

TOKEN = os.getenv("TOKEN")
BOT_NAME = os.getenv("BOT_NAME")
RCON_API_URL = os.getenv("RCON_API_URL", "http://backend:8000/api/get_public_info")  # URL CRCON API

logger.info(f"Environment variables loaded:")
logger.info(f"  TOKEN: {'*' * 20 if TOKEN else 'NOT SET'}")
logger.info(f"  BOT_NAME: {BOT_NAME}")
logger.info(f"  RCON_API_URL: {RCON_API_URL}")

# Check required environment variables
if not TOKEN or not BOT_NAME:
    logger.error("Error: Missing required environment variables: TOKEN or BOT_NAME")
    sys.exit(1)

logger.info("All required environment variables are set")

def get_server_data_from_rcon(api_url):
    """
    Получает данные о сервере из CRCON API
    Возвращает: (numplayers, maxplayers, map_name, score_allied, score_axis, time_remaining, next_map_name)
    """
    try:
        logger.info(f"Fetching server data from RCON API: {api_url}")
        headers = {
            "Accept": "application/json",
            "User-Agent": "DiscordBot/1.0"
        }
        # requests автоматически устанавливает правильный Host header на основе URL
        response = requests.get(api_url, headers=headers, timeout=10, allow_redirects=True)
        logger.info(f"RCON API response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"RCON API returned status {response.status_code}")
            try:
                error_body = response.text[:500]  # Первые 500 символов ошибки
                logger.error(f"RCON API error response: {error_body}")
                # Пробуем получить больше информации об ошибке
                if response.headers.get('Content-Type', '').startswith('application/json'):
                    try:
                        error_json = response.json()
                        logger.error(f"RCON API error JSON: {error_json}")
                    except:
                        pass
            except:
                pass
            return None
        
        data = response.json()
        logger.info(f"RCON API response: {data}")
        
        # Проверяем структуру ответа CRCON API
        if "result" in data:
            result = data["result"]
            numplayers = result.get("player_count", 0)
            maxplayers = result.get("max_player_count", 100)
            current_map = result.get("current_map", {})
            
            # Извлекаем имя карты из вложенной структуры
            if isinstance(current_map, dict):
                map_data = current_map.get("map", {})
                if isinstance(map_data, dict):
                    # Пробуем получить pretty_name, если нет - используем name или shortname
                    map_name = map_data.get("pretty_name") or map_data.get("name") or map_data.get("shortname") or "Unknown map"
                else:
                    map_name = str(map_data) if map_data else "Unknown map"
            else:
                map_name = str(current_map) if current_map else "Unknown map"
            
            # Извлекаем счет команд
            score = result.get("score", {})
            score_allied = score.get("allied", 0) if isinstance(score, dict) else 0
            score_axis = score.get("axis", 0) if isinstance(score, dict) else 0
            
            # Извлекаем оставшееся время (в секундах)
            time_remaining = result.get("time_remaining", 0)
            
            # Извлекаем следующую карту
            next_map = result.get("next_map", {})
            next_map_name = "Unknown"
            if isinstance(next_map, dict):
                next_map_data = next_map.get("map", {})
                if isinstance(next_map_data, dict):
                    next_map_name = next_map_data.get("pretty_name") or next_map_data.get("name") or next_map_data.get("shortname") or "Unknown"
                else:
                    next_map_name = str(next_map_data) if next_map_data else "Unknown"
            
            logger.info(f"Server data from RCON: {numplayers}/{maxplayers} players on {map_name}, Score: {score_allied}-{score_axis}, Time: {time_remaining}s, Next: {next_map_name}")
            return numplayers, maxplayers, map_name, score_allied, score_axis, time_remaining, next_map_name
        else:
            logger.error(f"Unexpected RCON API response structure: {data}")
            return None
            
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Could not connect to RCON API: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching server data from RCON API: {e}", exc_info=True)
        return None

def get_server_data(api_url=None):
    """
    Получает данные о сервере из RCON API
    """
    # Пытаемся получить данные из RCON API
    if api_url:
        # Пробуем несколько вариантов имени хоста
        # Извлекаем базовый путь из URL
        if "://" in api_url:
            protocol, rest = api_url.split("://", 1)
            if "/" in rest:
                host_part, path = rest.split("/", 1)
            else:
                host_part = rest
                path = ""
        else:
            host_part = api_url
            path = ""
        
        # Определяем варианты хоста для попытки
        # В сети common доступно имя сервиса backend_1, а алиас backend доступен только в server сетях
        # Поэтому сначала пробуем backend_1 (имя сервиса в common), затем backend (алиас), затем localhost/127.0.0.1
        host_variants = []
        if "backend_1" in host_part:
            # Если в URL указан backend_1, используем его напрямую, затем пробуем backend (алиас)
            host_variants = [
                host_part,  # backend_1 (имя сервиса в сети common)
                host_part.replace("backend_1", "backend"),  # Алиас backend (в server сетях)
                host_part.replace("backend_1", "localhost"),  # localhost
                host_part.replace("backend_1", "127.0.0.1"),  # 127.0.0.1
            ]
        elif "api_1" in host_part:
            # Если в URL указан api_1, пробуем backend_1 (имя сервиса), затем backend (алиас)
            host_variants = [
                host_part.replace("api_1", "backend_1"),  # Имя сервиса в сети common
                host_part.replace("api_1", "backend"),  # Алиас backend
                host_part.replace("api_1", "localhost"),  # localhost
                host_part.replace("api_1", "127.0.0.1"),  # 127.0.0.1
            ]
        elif "backend" in host_part:
            # Если в URL указан backend, сначала пробуем backend_1 (имя сервиса в common)
            host_variants = [
                host_part.replace("backend", "backend_1"),  # Имя сервиса в сети common
                host_part,  # backend (алиас в server сетях)
                host_part.replace("backend", "localhost"),  # localhost
                host_part.replace("backend", "127.0.0.1"),  # 127.0.0.1
            ]
        else:
            host_variants = [host_part]  # Используем как есть
        
        # Пробуем каждый вариант
        for host in host_variants:
            if path:
                url = f"{protocol}://{host}/{path}"
            else:
                url = f"{protocol}://{host}"
            logger.info(f"Trying RCON API URL: {url}")
            rcon_data = get_server_data_from_rcon(url)
            if rcon_data:
                return rcon_data
            # Если это не последний вариант, пробуем следующий
            if host != host_variants[-1]:
                logger.info(f"Failed with {url}, trying next variant...")
    
    # Если RCON API недоступен, возвращаем значения по умолчанию
    logger.warning("RCON API unavailable, returning default values")
    return 0, 0, "Unknown map", 0, 0, 0, "Unknown"

class GameBot(discord.Client):
    def __init__(self, *, intents, bot_name, rcon_api_url):
        logger.info("Initializing GameBot...")
        super().__init__(intents=intents)
        self.bot_name = bot_name
        self.rcon_api_url = rcon_api_url
        logger.info(f"GameBot initialized with bot_name={bot_name}, rcon_api_url={rcon_api_url}")

    async def on_connect(self):
        logger.info("Bot connected to Discord Gateway")

    async def on_ready(self):
        logger.info("=" * 50)
        logger.info(f"Bot {self.bot_name} is online as {self.user}")
        logger.info(f"Bot ID: {self.user.id}")
        logger.info(f"Bot is in {len(self.guilds)} guild(s)")
        for guild in self.guilds:
            logger.info(f"  - Guild: {guild.name} (ID: {guild.id})")
        logger.info("=" * 50)
        
        # Устанавливаем начальный статус
        await self.change_presence(activity=discord.Game(name="Starting..."), status=discord.Status.online)
        logger.info("Initial presence set to online")
        
        if not self.update_status.is_running():
            logger.info("Starting update_status task...")
            self.update_status.start()
            logger.info("update_status task started")
        else:
            logger.warning("update_status task is already running")

    @tasks.loop(seconds=120)  # Обновление каждые 2 минуты
    async def update_status(self):
        try:
            logger.info("update_status task running...")
            guild = discord.utils.get(self.guilds)
            if not guild:
                logger.warning("Guild not found. Available guilds:")
                for g in self.guilds:
                    logger.warning(f"  - {g.name} (ID: {g.id})")
                return

            logger.info(f"Using guild: {guild.name} (ID: {guild.id})")
            server_data = get_server_data(api_url=self.rcon_api_url)
            
            if not server_data:
                logger.warning("Failed to get server data")
                return
            
            players, maxplayers, map_name, score_allied, score_axis, time_remaining, next_map_name = server_data

            if players >= 95:
                color_emoji = "🔵"
            elif players >= 80:
                color_emoji = "🟢"            
            elif players >= 60:
                color_emoji = "🟡"
            elif players >= 40:
                color_emoji = "🟠"
            elif players >= 20:
                color_emoji = "🔴"
            else:
                color_emoji = "⚫"

            member = guild.me
            if not member:
                logger.error("Bot member not found in guild")
                return

            new_nick = f"{color_emoji} {self.bot_name} - {players}/{maxplayers}"
            logger.info(f"Attempting to update nickname to: {new_nick}")

            try:
                await member.edit(nick=new_nick)
                logger.info(f"✅ Nickname updated successfully: {new_nick}")
            except discord.Forbidden as e:
                logger.error(f"❌ Permission denied when updating nickname: {e}")
            except Exception as e:
                logger.error(f"❌ Error updating nickname: {e}", exc_info=True)

            # Форматируем оставшееся время в минуты:секунды
            def format_time(seconds):
                if seconds <= 0:
                    return "0:00"
                minutes = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{minutes}:{secs:02d}"
            
            # Формируем статус с учетом ограничения Discord (128 символов)
            # Пробуем разные варианты в зависимости от доступного места
            time_str = format_time(time_remaining)
            
            # Вариант 1: Полная информация (если помещается)
            status_message = f"{map_name} | {score_allied}-{score_axis} | {time_str} | Next: {next_map_name}"
            
            # Если слишком длинно, сокращаем
            if len(status_message) > 128:
                # Вариант 2: Без следующей карты
                status_message = f"{map_name} | {score_allied}-{score_axis} | {time_str}"
                if len(status_message) > 128:
                    # Вариант 3: Только карта и счет
                    status_message = f"{map_name} | {score_allied}-{score_axis}"
                    if len(status_message) > 128:
                        # Вариант 4: Только карта (fallback)
                        status_message = f"Map: {map_name}"[:128]
            
            logger.info(f"Updating presence to: {status_message}")
            await self.change_presence(activity=discord.Game(name=status_message), status=discord.Status.online)
            logger.info("✅ Presence updated successfully")

        except Exception as e:
            logger.error(f"❌ Error in update_status: {e}", exc_info=True)

    @update_status.before_loop
    async def before_update_status(self):
        logger.info("Waiting for bot to be ready before starting update_status loop...")
        await self.wait_until_ready()
        logger.info("Bot is ready, update_status loop will start now")

    async def on_error(self, event, *args, **kwargs):
        logger.error(f"Error in event {event}:", exc_info=True)

intents = discord.Intents.default()
intents.guilds = True

if __name__ == "__main__":
    logger.info("Creating GameBot instance...")
    bot = GameBot(intents=intents, bot_name=BOT_NAME, rcon_api_url=RCON_API_URL)
    logger.info("Starting bot...")
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Fatal error running bot: {e}", exc_info=True)
        sys.exit(1)
