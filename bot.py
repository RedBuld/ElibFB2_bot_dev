import asyncio, sys, uuid, os, glob, re, uuid, logging, aiofiles, idna, base64, orjson, urllib.parse, pprint
from typing import Optional

from modules.config import Config
from modules.db import *
from modules.message_queue import MessageQueue
from modules.download_queue import DownloaderQueue

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
	# filename='err.log',
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
# pprint.pprint(config.__json__(),indent=4)

bot.config = config
router = Router()
dispatcher = Dispatcher(storage=storage)
dispatcher.include_router(router)

db = SQLAlchemy(bot)
message_queue = MessageQueue(bot)
download_queue = DownloaderQueue(bot)

# async def test_db():
# 	# await db.create_db()

# 	ua = UserAuth()
# 	ua.user = 470328529
# 	ua.site = "author.today"
# 	ua.login = "sibiryakov.ya@gmail.com"
# 	ua.password = "1409199696Rus"

# 	db.session.add(ua)
# 	await db.session.commit()
# 	user_auth = await db.session.get(UserAuth,1)


class AuthForm(StatesGroup):
	site = State()
	login = State()
	password = State()

class DownloadConfig(StatesGroup):
	download_config = State()
	# start = State(0)
	# end = State(0)
	# format = State()
	# images = State(False)

@router.message(Command(commands='admin'))
async def admin_cmd_handler(message: types.Message):

	if message.from_user.id != 470328529:
		return

	command = message.text.split('/admin')[1]
	command = command.strip()

	if not command:
		download_id = await bot.download_queue.enqueue( {'start': '', 'end': '10', 'format': 'fb2', 'auth': 'anon', 'book_link': 'https://ranobelib.me/reverend-insanity?bid=8792&section=chapters&ui=2201240', 'site': 'ranobelib.me', 'user_id': 470328529} )
		await bot.download_queue.set_message(download_id, chat_id=470328529, message_id=1871)

	if command == 'reload_config':
		bot.config.__load__()
		await bot.db.reinit()
		return await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Конфиг загружен")

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
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Бот не принимает новые закачки" )

	if command == 'start_accept':
		config.ACCEPT_NEW = True
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Бот принимает новые закачки" )

	if command == '50m_test':
		return await bot.message_queue.enqueue( 'send_document', chat_id=message.chat.id, document=os.path.join(DOWNLOADER_PATH, 'untitled.zip') )

# @router.message(F.content_type.in_({'text'}), ~F.text.startswith('http'))
# async def not_hadleable(message: types.Message, state: FSMContext):
# 	await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Неа. ТОЛЬКО ССЫЛКИ" )

@router.message(F.content_type.in_({'text'}), F.text.startswith('http'))
async def prepare_download(message: types.Message, state: FSMContext):

	if message.from_user.id != 470328529:
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Неа. Это ТЕСТОВЫЙ бот" )
		return

	current_state = await state.get_state()
	if current_state is not None:
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Отмените или завершите предыдущее скачивание" )
		return

	if not config.ACCEPT_NEW:
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Бот временно не принимает новые закачки" )
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

		start_end = False
		use_auth = {}

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
			start_end = True

		payload = {
			'use_auth': use_auth,
			'use_start': start_end,
			'use_end': start_end,
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

		await state.set_state(DownloadConfig.download_config)
		await state.update_data(download_inited=False)
		await state.update_data(book_link=url)
		await state.update_data(site=site)
		await state.update_data(user_id=message.from_user.id)
		await state.update_data(chat_id=message.chat.id)

		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text=f"Подготовка к скачиванию {url}", reply_markup=reply_markup )

@router.message(F.content_type.in_({'web_app_data'}))
async def web_app_callback_data(message: types.Message, state: FSMContext):
	current_state = await state.get_state()
	params = orjson.loads(message.web_app_data.data)
	data = None
	if current_state is not None:
		data = await state.get_data()
		await state.update_data(download_inited=True)
		# await state.clear()
	if data and data['download_inited']:
		return
	if params:
		if data:
			for k in data:
				params[k] = data[k]
		print('params')
		print(params)
		url = params['book_link']
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
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, reply_to_message_id=message.message_id, text=msg, reply_markup=ReplyKeyboardRemove(), callback='initialize_download', callback_kwargs={'params':params} )
		await state.clear()
	else:
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, reply_to_message_id=message.message_id, text='Отправьте ссылку еще раз', reply_markup=ReplyKeyboardRemove())


async def initialize_download(message: types.Message, params: dict):
	download_id = await bot.download_queue.enqueue( params=params )
	if download_id:
		reply_markup = InlineKeyboardMarkup(
			inline_keyboard=[
				[
					InlineKeyboardButton( text='Отмена', callback_data=f'cancel:{download_id}' )
				]
			]
		)
		msg = "Добавлено в очередь"
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text=msg, reply_markup=reply_markup, callback='set_download_message', callback_kwargs={'download_id':download_id,'last_message':msg} )
	else:
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Произошла ошибка" )
bot.initialize_download = initialize_download


async def set_download_message(message: types.Message, download_id: int, last_message: str):
	await bot.download_queue.set_message_id(download_id=download_id, message_id=message.message_id, last_message=last_message)
bot.set_download_message = set_download_message

@router.callback_query()
async def callback_query_handler(callback_query: types.CallbackQuery):
	# print()
	# print()
	# print(callback_query.data)
	# print()
	# print()
	download_id = int(callback_query.data.split(':')[1])
	await bot.download_queue.cancel(download_id)



@router.message(Command(commands=["cancel"]))
@router.message(F.text.casefold() == "cancel")
@router.message(F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext):

	current_state = await state.get_state()
	if current_state is not None:
		await state.clear()

	await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Отменено", reply_markup=ReplyKeyboardRemove() )


async def on_startup(dispatcher: Dispatcher, bot: Bot):
	# await bot.db.create_db()
	await bot.set_webhook(f"{config.WEBHOOK}/{config.WEBHOOK_PATH}")

async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
	await bot.delete_webhook()














async def start_dq():
	try:
		await download_queue.start_queue()
	except (KeyboardInterrupt, SystemExit):  # pragma: no cover
		# Allow to graceful shutdown
		pass
async def start_mq():
	try:
		await message_queue.start_queue()
	except (KeyboardInterrupt, SystemExit):  # pragma: no cover
		# Allow to graceful shutdown
		pass

async def start_bot():
	try:
		await dispatcher.start_polling(bot, skip_updates=False)
	except (KeyboardInterrupt, SystemExit):  # pragma: no cover
		# Allow to graceful shutdown
		pass

async def _start():
	try:
		await asyncio.gather(
			start_dq(),
			start_mq(),
			start_bot()
		)
	except (KeyboardInterrupt, SystemExit):  # pragma: no cover
		# Allow to graceful shutdown
		pass

def start_bot_sync():
	try:
		dispatcher.startup.register(on_startup)
		dispatcher.startup.register(start_dq)
		dispatcher.startup.register(start_mq)
		dispatcher.shutdown.register(on_shutdown)
		app = web.Application()
		SimpleRequestHandler(dispatcher=dispatcher, bot=bot).register(app, path=config.WEBHOOK_PATH)
		setup_application(app, dispatcher, bot=bot)
		# import ssl
		# ssl_context = ssl.create_default_context()
		# ssl_context = ssl_context.load_cert_chain('/etc/letsencrypt/live/ranobe1.elib-fb2.tw1.ru/fullchain.pem', '/etc/letsencrypt/live/ranobe1.elib-fb2.tw1.ru/privkey.pem')
		# web.run_app(app, host="0.0.0.0", ssl_context=ssl_context)
		web.run_app(app, host="0.0.0.0")
		# await dispatcher.start_polling(bot, skip_updates=False)
	except (KeyboardInterrupt, SystemExit):  # pragma: no cover
		# Allow to graceful shutdown
		pass

def _start_sync():
	try:
		start_bot_sync()
	except (KeyboardInterrupt, SystemExit):  # pragma: no cover
		# Allow to graceful shutdown
		pass

if __name__ == '__main__':
	try:
		# asyncio.run(_start())
		_start_sync()
	except (KeyboardInterrupt, SystemExit):  # pragma: no cover
		# Allow to graceful shutdown
		pass
#     # date = asyncio.run(asynchronous())
#     date = asyncio.run(test_exec())
#     # print( asyncio.run( get_last_line('/root/2aa8ec4a-a863-40a6-bbca-d76cebbd4630.log') ) )
