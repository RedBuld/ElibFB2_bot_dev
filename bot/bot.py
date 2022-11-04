import argparse, asyncio, sys, logging
from datetime import datetime
from typing import Union
from pathlib import Path

from modules.config import Config
from modules.db import DB
from modules.messages_queue import MessagesQueue
from modules.downloads_queue import DownloadsQueue
from modules.handlers import get_router

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import (
	SimpleRequestHandler,
	setup_application,
)

parser = argparse.ArgumentParser(prog='bot.py', conflict_handler='resolve')
parser.add_argument('config', type=Path, help='path to config file')
execute_args = parser.parse_args()

if not execute_args.config:
	sys.exit('Not passed `config` path, use -h to get help')

config = Config(config_file=execute_args.config)

if config.LOGS_PATH:
	logging.basicConfig(
		filename=f'{config.LOGS_PATH}/{config.BOT_ID}.log',
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		level=logging.INFO
	)
else:
	logging.basicConfig(
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		level=logging.INFO
	)
logger=logging.getLogger(__name__)

if config.LOCAL_SERVER:
	local_server = TelegramAPIServer.from_base( config.LOCAL_SERVER, is_local=True )
	session = AiohttpSession( api=local_server )
	bot = Bot( token=config.API_TOKEN, session=session )
else:
	bot = Bot( token=config.API_TOKEN )

if config.REDIS_URL:
	kb = DefaultKeyBuilder(prefix=config.BOT_ID, with_bot_id=True, with_destiny=True)
	storage = RedisStorage.from_url( config.REDIS_URL, key_builder=kb )
if not storage:
	storage = MemoryStorage()

bot.config = config
router = get_router(bot)
dispatcher = Dispatcher(storage=storage)
dispatcher.include_router(router)

db = DB(bot)
messages_queue = MessagesQueue(bot)
downloads_queue = DownloadsQueue(bot)


async def on_startup(dispatcher: Dispatcher, bot: Bot) -> None:
	await bot.db.init()
	await bot.messages_queue.start()
	await bot.downloads_queue.start()
	await bot.set_webhook(f"{config.WEBHOOK}{config.WEBHOOK_PATH}")

async def on_shutdown(dispatcher: Dispatcher, bot: Bot) -> None:
	await bot.messages_queue.stop()
	await bot.downloads_queue.stop()
	await bot.delete_webhook()
	await bot.db.stop()
	await bot.session.close()

def start_bot() -> None:
	try:
		dispatcher.startup.register(on_startup)
		dispatcher.shutdown.register(on_shutdown)

		app = web.Application()
		SimpleRequestHandler(dispatcher=dispatcher, bot=bot).register(app, path=config.WEBHOOK_PATH)
		setup_application(app, dispatcher, bot=bot)
		web.run_app(app, host="127.0.0.1", port=config.BOT_PORT)
	except (KeyboardInterrupt, SystemExit):
		pass
	except Exception as e:
		raise e

if __name__ == '__main__':

	logger.info(f'\nLauching bot {config.BOT_ID}\n')
	start_bot()