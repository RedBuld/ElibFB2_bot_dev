import asyncio, sys, uuid, os, glob, re, uuid, logging, aiofiles, idna, base64, orjson, urllib.parse
from typing import Optional

from modules.config import Config
from modules.db import DB
from modules.messages_queue import MessagesQueue
from modules.downloads_queue import DownloadsQueue

from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.webhook.aiohttp_server import (
	SimpleRequestHandler,
	setup_application,
)

logging.basicConfig(
	filename='err.log',
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=logging.INFO
)
logger=logging.getLogger(__name__)

global config
config = Config()
if config.LOCAL_SERVER:
	local_server = TelegramAPIServer.from_base( config.LOCAL_SERVER, is_local = True )
	session = AiohttpSession( api=local_server )
	bot = Bot( token=config.API_TOKEN, session=session )
else:
	bot = Bot( token=config.API_TOKEN )
# bot = Bot( token=config.API_TOKEN )

if config.REDIS_CONFIG:
	storage = RedisStorage.from_url( config.REDIS_CONFIG )
if not storage:
	storage = MemoryStorage()

# storage = MemoryStorage()

bot.config = config
router = Router()
dispatcher = Dispatcher(storage=storage)
dispatcher.include_router(router)

db = DB(bot)
messages_queue = MessagesQueue(bot)
downloads_queue = DownloadsQueue(bot)


class AuthForm(StatesGroup):
	site = State()
	login = State()
	password = State()

class DownloadConfig(StatesGroup):
	state = State()

@router.message(Command(commands='admin'))
async def admin_cmd_handler(message: types.Message) -> None:

	if message.from_user.id != 470328529:
		return

	command = message.text.split('/admin')[1]
	command = command.strip()

	if not command:
		download_id = await bot.downloads_queue.enqueue( {'start': '', 'end': '10', 'format': 'fb2', 'auth': 'anon', 'url': 'https://ranobelib.me/reverend-insanity?bid=8792&section=chapters&ui=2201240', 'site': 'ranobelib.me', 'user_id': 470328529} )
		await bot.downloads_queue.set_message(download_id, chat_id=470328529, message_id=1871)

	if command == 'reload_config':
		bot.config.__load__()
		await bot.db.reinit()
		return await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Конфиг загружен")

	if command.startswith('ban'):
		cmd = command.split()
		uid = cmd[1]
		time = cmd[2] +' '+ cmd[3]
		reason = ' '.join(cmd[4::])
		await safe_send_message( bot.send_message, chat_id=message.chat.id, text=f"{uid} {time} {reason}")
		await set_user_ban(uid,reason,time)
		return await safe_send_message( bot.send_message, chat_id=message.chat.id, text="Юзер забанен")

	if command == 'stop_accept':
		config.ACCEPT_NEW = False
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот не принимает новые закачки" )

	if command == 'start_accept':
		config.ACCEPT_NEW = True
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот принимает новые закачки" )

	if command == '50m_test':
		return await bot.messages_queue.add( callee='send_document', chat_id=message.chat.id, document=os.path.join(DOWNLOADER_PATH, 'untitled.zip') )

# @router.message(F.content_type.in_({'text'}), ~F.text.startswith('http'))
# async def not_hadleable(message: types.Message, state: FSMContext) -> None:
# 	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Неа. ТОЛЬКО ССЫЛКИ" )

@router.message(F.content_type.in_({'text'}), F.text.startswith('http'))
async def prepare_download(message: types.Message, state: FSMContext) -> None:

	# if message.from_user.id != 470328529:
	# 	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Неа. Это ТЕСТОВЫЙ бот" )
	# 	return

	current_state = await state.get_state()
	if current_state is not None:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Отмените или завершите предыдущее скачивание" )
		return

	can_add = await bot.downloads_queue.can_add()
	if not can_add:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Очередь заполнена. Пжалста пдждте" )
		return

	if not config.ACCEPT_NEW:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот временно не принимает новые закачки" )
		return

	query = message.text.strip()
	query = query.split()

	url = ''
	site = ''

	for q in query:
		for r in config.REGEX_LIST:
			m = r.match(q)
			if m:
				site = m.group('site')
				if site not in config.SITES_LIST:
					site = None
				else:
					url = q
				break
		if url:
			break

	if url:

		use_start_end = False
		use_auth = {}
		use_images = False
		force_images = False

		if "auth" in bot.config.SITES_DATA[site]:
			ua = await bot.db.get_user_auth(message.from_user.id,site)
			priv_login = True if ua else False
			demo_login = True if site in bot.config.DEMO_USER else False
			if priv_login:
				use_auth['self'] = 'Свои доступы'
			if demo_login:
				use_auth['anon'] = 'Анонимные доступы'
			use_auth['none'] = 'Без авторизации'

		if "paging" in bot.config.SITES_DATA[site]:
			use_start_end = True

		if "images" in bot.config.SITES_DATA[site]:
			images = True

		if "force_images" in bot.config.SITES_DATA[site]:
			force_images = True
			use_images = False

		payload = {
			'use_auth': use_auth,
			'use_start': use_start_end,
			'use_end': use_start_end,
			'use_images': use_images,
			'use_cover': True,
			'formats': config.FORMATS,
			'images': True,
			'cover': False,
		}
		payload = orjson.dumps(payload).decode('utf8')
		payload = urllib.parse.quote_plus( payload )
		web_app = types.WebAppInfo(url=f"https://elib-fb2.tw1.ru/?payload={payload}")
		
		reply_markup = ReplyKeyboardMarkup(
			keyboard=[
				[
					KeyboardButton( text='Скачать', web_app=web_app ),
					KeyboardButton( text='Отмена' )
				]
			]
		)

		await state.set_state(DownloadConfig.state)
		await state.update_data(inited=False)
		await state.update_data(url=url)
		await state.update_data(site=site)
		await state.update_data(user_id=message.from_user.id)
		await state.update_data(chat_id=message.chat.id)
		if force_images:
			await state.update_data(images=True)

		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f"Подготовка к скачиванию {url}", reply_markup=reply_markup )

@router.message(F.content_type.in_({'web_app_data'}))
async def web_app_callback_data(message: types.Message, state: FSMContext) -> None:
	current_state = await state.get_state()
	params = orjson.loads(message.web_app_data.data)
	data = None
	if current_state is not None:
		data = await state.get_data()
		await state.update_data(inited=True)
		# await state.clear()
	if data and data['inited']:
		return
	if params:
		if data:
			for k in data:
				params[k] = data[k]
		url = params['url']
		msg = f"Добавляю в очередь {url}"
		if 'auth' in params:
			if params['auth'] == 'self':
				msg += "\nИспользую личные доступы"
			if params['auth'] == 'anon':
				msg += "\nИспользую анонимные доступы"
			if params['auth'] == 'none':
				msg += "\nБез авторизации"

		if 'images' in params:
			msg += "\nСкачиваю картинки"
		else:
			msg += "\nНе скачиваю картинки"

		if 'cover' in params:
			msg += "\nСкачиваю обложку"
		else:
			msg += "\nНе скачиваю обложку"
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, reply_to_message_id=message.message_id, text=msg, reply_markup=ReplyKeyboardRemove(), callback='enqueue_download', callback_kwargs={'params':params} )
		await state.clear()
	else:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, reply_to_message_id=message.message_id, text='Отправьте ссылку еще раз', reply_markup=ReplyKeyboardRemove())


async def enqueue_download(message: types.Message, params: dict) -> None:
	if 'start' in params:
		params['start'] = int(params['start'])
	if 'end' in params:
		params['end'] = int(params['end'])
	if 'images' in params:
		params['images'] = int(params['images'])
	if 'cover' in params:
		params['cover'] = int(params['cover'])

	download_id = await bot.downloads_queue.add( params=params )
	if download_id:
		reply_markup = InlineKeyboardMarkup(
			inline_keyboard=[
				[
					InlineKeyboardButton( text='Отмена', callback_data=f'cancel:{download_id}' )
				]
			]
		)
		msg = "Добавлено в очередь"
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=msg, reply_markup=reply_markup, callback='initiate_download', callback_kwargs={'download_id':download_id,'last_message':msg} )
	else:
		msg = "Произошла ошибка"
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=msg )
bot.enqueue_download = enqueue_download


async def initiate_download(message: types.Message, download_id: int, last_message: str) -> None:
	await bot.downloads_queue.initiate(download_id=download_id, message_id=message.message_id, last_message=last_message)
bot.initiate_download = initiate_download

@router.callback_query()
async def callback_query_handler(callback_query: types.CallbackQuery) -> None:
	# logger.info()
	# logger.info()
	# logger.info(callback_query.data)
	# logger.info()
	# logger.info()
	download_id = int(callback_query.data.split(':')[1])
	await bot.downloads_queue.cancel(download_id)



@router.message(Command(commands=["cancel"]))
@router.message(F.text.casefold() == "cancel")
@router.message(F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:

	current_state = await state.get_state()
	if current_state is not None:
		await state.clear()

	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Отменено", reply_markup=ReplyKeyboardRemove() )


async def on_startup(dispatcher: Dispatcher, bot: Bot) -> None:
	# await bot.db.create_db()
	await bot.db.init()
	await bot.messages_queue.start()
	await bot.downloads_queue.start()
	await bot.set_webhook(f"{config.WEBHOOK}/{config.WEBHOOK_PATH}")

async def on_shutdown(dispatcher: Dispatcher, bot: Bot) -> None:
	await bot.messages_queue.stop()
	await bot.downloads_queue.stop()
	await bot.delete_webhook()
	await bot.db.stop()
	await bot.session.close()


def start_bot_sync() -> None:
	try:
		dispatcher.startup.register(on_startup)
		dispatcher.shutdown.register(on_shutdown)

		app = web.Application()
		SimpleRequestHandler(dispatcher=dispatcher, bot=bot).register(app, path=config.WEBHOOK_PATH)
		setup_application(app, dispatcher, bot=bot)
		web.run_app(app, host="0.0.0.0")
	except (KeyboardInterrupt, SystemExit):
		pass

if __name__ == '__main__':
	if len(sys.argv) > 1 and sys.argv[1] == 'create_db':
		logger.info('\n'*5)
		logger.info('Recreating DB')
		logger.info('\n'*5)
		asyncio.run( bot.db.create_db() )
	else:
		try:
			logger.info('\n'*5)
			start_bot_sync()
			logger.info('\n'*5)
		except (KeyboardInterrupt, SystemExit):
			pass