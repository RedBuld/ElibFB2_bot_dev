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
parser.add_argument('bot_id', type=str, help='bot_id to load config')
parser.add_argument('--dev', dest='dev', const=True, default=False, action='store_const', help='is bot in dev mode')
execute_args = parser.parse_args()

if not execute_args.bot_id:
	sys.exit('Not passed `bot_id`, use -h to get help')

config = Config(bot_id=execute_args.bot_id)

# if execute_args.dev:
# 	print()
# 	print()
# 	print()
# 	print(config)
# 	print()
# 	print()
# 	print()
# 	# sys.exit(0)

if config.get('LOGS_PATH') and not execute_args.dev:
	_path = config.get('LOGS_PATH')
	_bot_id = config.get('BOT_ID')
	logging.basicConfig(
		filename=f'{_path}/{_bot_id}.log',
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		level=logging.INFO
	)
else:
	logging.basicConfig(
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		level=logging.INFO
	)
logger=logging.getLogger(__name__)

if config.get('LOCAL_SERVER'):
	local_server = TelegramAPIServer.from_base( config.get('LOCAL_SERVER'), is_local=True )
	session = AiohttpSession( api=local_server )
	bot = Bot( token=config.get('BOT_TOKEN'), session=session )
else:
	bot = Bot( token=config.get('BOT_TOKEN') )

if config.get('REDIS_URL'):
	kb = DefaultKeyBuilder(prefix=config.get('BOT_ID'), with_bot_id=True, with_destiny=True)
	storage = RedisStorage.from_url( config.get('REDIS_URL'), key_builder=kb )
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
	if config.get('BOT_URL'):
		_bot_url = config.get('BOT_URL')
		_bot_hook = config.get('BOT_HOOK')
		await bot.set_webhook(f"{_bot_url}{_bot_hook}")

async def on_shutdown(dispatcher: Dispatcher, bot: Bot) -> None:
	await bot.messages_queue.stop()
	await bot.downloads_queue.stop()
	if config.get('BOT_URL'):
		await bot.delete_webhook()
	await bot.db.stop()
	await bot.session.close()


def start_bot_webhook() -> None:
	try:
		dispatcher.startup.register(on_startup)
		dispatcher.shutdown.register(on_shutdown)

		app = web.Application()
		SimpleRequestHandler(dispatcher=dispatcher, bot=bot).register(app, path=config.get('BOT_HOOK'))
		setup_application(app, dispatcher, bot=bot)
		web.run_app(app, host="127.0.0.1", port=config.get('BOT_PORT'))
	except (KeyboardInterrupt, SystemExit):
		pass
	except Exception as e:
		raise e

def start_bot_polling() -> None:
	try:
		dispatcher.startup.register(on_startup)
		dispatcher.shutdown.register(on_shutdown)

		dispatcher.run_polling(bot)
	except (KeyboardInterrupt, SystemExit):
		pass
	except Exception as e:
		raise e

if __name__ == '__main__':

	_bot_id = config.get('BOT_ID')
	logger.info(f'\nLauching bot {_bot_id}\n')

	if config.get('BOT_URL'):
		start_bot_webhook()
	else:
		start_bot_polling()