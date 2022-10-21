import asyncio, sys, uuid, os, glob, re, uuid, logging, aiofiles, idna, base64, orjson, urllib.parse, pprint
from typing import Optional

from modules.config import Config
from modules.db import *
from modules.message_queue import MessageQueue
from modules.download_queue import DownloaderQueue

from aiogram import Bot, Dispatcher, executor, types
from aiogram.bot.api import TelegramAPIServer
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, Regexp
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logging.basicConfig(
	# filename='err.log',
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=logging.INFO
)
logger=logging.getLogger(__name__)

config = Config()

if config.REDIS_HOST:
    storage = RedisStorage2(pool_size=500,host=config.REDIS_HOST,port=config.REDIS_PORT,db=config.REDIS_DB)
if not storage:
    storage = MemoryStorage()

# if config.LOCAL_SERVER:
# 	local_server = TelegramAPIServer.from_base( config.LOCAL_SERVER )
# 	bot = Bot( token=config.API_TOKEN, server=local_server )
# else:
# 	bot = Bot( token=config.API_TOKEN )
bot = Bot( token=config.API_TOKEN )

bot.config = config
dispatcher = Dispatcher(bot, storage=storage)

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

@dispatcher.message_handler(commands='admin')
async def admin_cmd_handler(message: types.Message):

	if message.chat.id != 470328529:
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


	# # if command == 'restart':
	# #     await message.delete()
	# #     proc = await asyncio.create_subprocess_shell(f'systemctl restart tg-bot')
	# #     return await proc.communicate()
	# if command.startswith('ban'):
	#     cmd = command.split()
	#     uid = cmd[1]
	#     time = cmd[2] +' '+ cmd[3]
	#     reason = ' '.join(cmd[4::])
	#     await safe_send_message( bot.send_message, chat_id=message.chat.id, text=f"{uid} {time} {reason}")
	#     await set_user_ban(uid,reason,time)
	#     return await safe_send_message( bot.send_message, chat_id=message.chat.id, text="Юзер забанен")

	# if command == 'disconnect':
	#     return await bot.log_out()

	if command == 'stop_accept':
		config.ACCEPT_NEW = False
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Бот не принимает новые закачки" )

	if command == 'start_accept':
		config.ACCEPT_NEW = True
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Бот принимает новые закачки" )

	if command == 'split_test':
		_d = os.path.join(DOWNLOADER_PATH, 'tttmp')
		_s = 'Untitled.mp4'
		_t = os.path.join(_d, 'Untitled.zip')
		cmd = f'cd {DOWNLOADER_PATH}; zip -s 2m "{_t}" "{_s}"'
		proc = await asyncio.create_subprocess_shell(cmd,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
		success, error = await proc.communicate()

		m = []
		t = os.listdir(_d)
		for x in t:
			q = {
				'type': 'document',
				'media': os.path.join(_d, x)
			}
			m.append( q )
		return await bot.message_queue.enqueue( 'send_media_group', chat_id=message.chat.id, media=m )

	if command == '50m_test':
		return await bot.message_queue.enqueue( 'send_document', chat_id=message.chat.id, document=os.path.join(DOWNLOADER_PATH, 'untitled.zip') )

@dispatcher.message_handler(content_types='text', text_startswith='http')
async def prepare_download(message: types.Message, state: FSMContext):

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
		await state.update_data(book_link=url)
		await state.update_data(site=site)
		await state.update_data(user_id=message.from_user.id)

		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text=f"Подготовка к скачиванию {url}", reply_markup=reply_markup )

@dispatcher.message_handler(content_types='web_app_data')
async def web_app_callback_data(message: types.Message, state: FSMContext):
	current_state = await state.get_state()
	params = orjson.loads(message.web_app_data.data)
	data = None
	if current_state is not None:
		data = await state.get_data()
		await state.clear()
	if params:
		if data:
			for k in data:
				params[k] = data[k]
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, reply_to_message_id=message.message_id, text="Добавляю в очередь", reply_markup=ReplyKeyboardRemove(), callback=initialize_download, callback_kwargs={'params':params} )
	else:
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, reply_to_message_id=message.message_id, text='Отправьте ссылку еще раз', reply_markup=ReplyKeyboardRemove())


async def initialize_download(message: types.Message, params: dict):
	# print('params')
	# print(params)
	download_id = await bot.download_queue.enqueue( params=params )
	if download_id:
		reply_markup = InlineKeyboardMarkup(
			inline_keyboard=[
				[
					InlineKeyboardButton( text='Отмена', callback_data=f'cancel:{download_id}' )
				]
			]
		)
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Добавлено в очередь", reply_markup=reply_markup, callback=set_download_message, callback_kwargs={'download_id':download_id} )
	else:
		await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Произошла ошибка: Не указана ссылка" )

async def set_download_message(message: types.Message, download_id: int):
	await bot.download_queue.set_message(download_id, chat_id=message.chat.id, message_id=message.message_id)

@dispatcher.callback_query_handler(text_startswith='cancel:')
async def callback_query_handler(callback_query: types.CallbackQuery):
	# print()
	# print()
	# print(callback_query.data)
	# print()
	# print()
	download_id = int(callback_query.data.split(':')[1])
	if download_id != 0:
		await bot.download_queue.cancel(download_id)



@dispatcher.message_handler(commands="cancel")
@dispatcher.message_handler(Text(equals='cancel', ignore_case=True))
@dispatcher.message_handler(Text(equals='отмена', ignore_case=True))
async def cancel_handler(message: types.Message, state: FSMContext):

	current_state = await state.get_state()
	if current_state is not None:
		await state.clear()

	await bot.message_queue.enqueue( 'send_message', chat_id=message.chat.id, text="Отменено", reply_markup=ReplyKeyboardRemove() )



async def start_dq(dispatcher=None):
	try:
		asyncio.create_task( download_queue.start_queue() )
	except (KeyboardInterrupt, SystemExit):  # pragma: no cover
		# Allow to graceful shutdown
		pass

async def start_mq(dispatcher=None):
	try:
		asyncio.create_task( message_queue.start_queue() )
	except (KeyboardInterrupt, SystemExit):  # pragma: no cover
		# Allow to graceful shutdown
		pass

# async def start_bot():
# 	try:
# 		executor.start_polling(dispatcher, loop=loop, skip_updates=False)
# 		# await dispatcher.start_polling(bot, skip_updates=False)
# 	except (KeyboardInterrupt, SystemExit):  # pragma: no cover
# 		# Allow to graceful shutdown
# 		pass

# async def _start():
# 	try:
# 		await asyncio.gather(
# 			start_dq(),
# 			start_mq(),
# 			start_bot()
# 		)
# 	except (KeyboardInterrupt, SystemExit):  # pragma: no cover
# 		# Allow to graceful shutdown
# 		pass

if __name__ == '__main__':
	try:
		executor.start_polling(dispatcher, on_startup=[start_dq,start_mq], skip_updates=False)
		# asyncio.run(_start())
	except (KeyboardInterrupt, SystemExit):  # pragma: no cover
		# Allow to graceful shutdown
		pass