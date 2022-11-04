import asyncio, idna, orjson, urllib.parse
from datetime import datetime
from typing import Any
from aiogram import Bot, Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, Text
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .models import AuthForm, DownloadConfig

bot = None

router = Router()

direct_functions = {}

@router.message(Command(commands='admin'))
async def admin_command(message: types.Message, state: FSMContext) -> None:

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
		await bot.db.set_user_ban(uid,reason,time)
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Юзер забанен")

	if command == 'stop_accept':
		bot.config.ACCEPT_NEW = False
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот не принимает новые закачки" )

	if command == 'start_accept':
		bot.config.ACCEPT_NEW = True
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот принимает новые закачки" )

@router.message(Command(commands='start'))
async def start_command(message: types.Message, state: FSMContext) -> None:
	await state.clear()
	if bot.config.START_MESSAGE:
		return await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=bot.config.START_MESSAGE, reply_markup=ReplyKeyboardRemove())


@router.message(Command(commands='sites'))
async def sites_command(message: types.Message, state: FSMContext) -> None:

	return await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f'Список поддерживаемых сайтов:\n'+('\n'.join( [idna.decode(x) for x in bot.config.SITES_LIST] )) )


@router.message(Command(commands='login'))
async def login_command(message: types.Message, state: FSMContext) -> None:

	current_state = await state.get_state()
	if current_state is not None:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Отмените или завершите предыдущее скачивание/авторизацию" )
		return

	used_for_auth = []
	for site in bot.config.SITES_DATA:
		if "auth" in bot.config.SITES_DATA[site]:
			used_for_auth.append(site)

	if len(used_for_auth) > 0:
		keyboard = []
		for site in used_for_auth:
			keyboard.append( [types.InlineKeyboardButton(text=idna.decode(site), callback_data=f'site:{site}')] )

		reply_markup = InlineKeyboardMarkup(
			inline_keyboard=keyboard
		)

		await state.set_state(AuthForm.site)

		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Выберите сайт", reply_markup=reply_markup )
	else:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Нет сайтов доступных для авторизации", reply_markup=ReplyKeyboardRemove() )


@router.callback_query(AuthForm.site, F.data.startswith('site:'))
async def login_command_site(callback_query: types.CallbackQuery, state: FSMContext) -> None:

	site = callback_query.data.split(':')[1]

	used_for_auth = []
	for auth_site in bot.config.SITES_DATA:
		if "auth" in bot.config.SITES_DATA[auth_site]:
			used_for_auth.append(auth_site)

	if site in used_for_auth:

		await state.update_data(site=site)

		await state.set_state(AuthForm.login)

		await bot.messages_queue.add( callee='edit_message_text', chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, text=f'Выбран сайт {site}\nНажмите /cancel для отмены', reply_markup=None)

		await bot.messages_queue.add( callee='send_message', chat_id=callback_query.message.chat.id, text=f'Введите логин\n!!!ВХОД ЧЕРЕЗ СОЦ. СЕТИ НЕВОЗМОЖЕН!!!\nНажмите /cancel для отмены')


@router.message(AuthForm.login, ~F.text.startswith('/'))
async def login_command_login(message: types.Message, state: FSMContext) -> None:

	login = message.text.strip()

	await bot.messages_queue.add( callee='delete_message', chat_id=message.chat.id, message_id=message.message_id )

	if not login.startswith('/') and not login.startswith('http:') and not login.startswith('https:'):

		await state.update_data(login=login)

		await state.set_state(AuthForm.password)

		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f'Введите пароль\nНажмите /cancel для отмены')


@router.message(AuthForm.password, ~F.text.startswith('/'))
async def login_command_password(message: types.Message, state: FSMContext) -> None:

	password = message.text.strip()

	await bot.messages_queue.add( callee='delete_message', chat_id=message.chat.id, message_id=message.message_id )

	if not password.startswith('/') and not password.startswith('http:') and not password.startswith('https:'):

		await state.update_data(password=password)

		data = await state.get_data()
		data['user'] = message.from_user.id

		await state.clear()

		ua_id = await bot.db.add_site_auth(data)

		if ua_id:
			ua = await bot.db.get_site_auth(ua_id)
			auth = ua.get_name()
			await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f'Авторизация завершена\n\n{auth}')
		else:
			_login = data["login"]
			_password = data["password"]
			await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f'Неверные логин или пароль\n\nЛогин: "{_login}"\nПароль: "{_password}')


@router.message(Command(commands='logins'))
async def logins_command(message: types.Message, state: FSMContext) -> None:

	user_id = message.from_user.id

	sites = await bot.db.get_all_authed_sites(user_id)

	if sites:
		row_btns = []

		for site in sites:
			row_btns.append([types.InlineKeyboardButton(text=idna.decode(site), callback_data=f'logins:{site}')])

		reply_markup = types.InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)

		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Выберите сайт', reply_markup=reply_markup)

		return
	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Нет сохраненных доступов')


@router.callback_query(F.data.startswith('logins:'))
async def login_command_site(callback_query: types.CallbackQuery, state: FSMContext) -> None:
	user_id = callback_query.from_user.id
	chat_id = callback_query.message.chat.id
	message_id = callback_query.message.message_id
	data = callback_query.data.split(':')

	if len(data) == 2:
		site = data[1]
		if site == 'all':
			await __get_authed_sites(user_id=user_id, chat_id=chat_id, message_id=message_id, data=data)
		else:
			await __get_authed_site_logins(user_id=user_id, chat_id=chat_id, message_id=message_id, data=data)
	elif len(data) == 3:
		await __get_authed_site_login_data(user_id=user_id, chat_id=chat_id, message_id=message_id, data=data)
	elif len(data) == 4:
		site = data[1]
		ua_id = data[2]
		action = data[3]
		if action == 'delete':
			await bot.db.remove_site_auth(ua_id)
			await __get_authed_site_logins(user_id=user_id, chat_id=chat_id, message_id=message_id, data=data)


@router.message(Command(commands='stats'))
async def stats_command(message: types.Message, state: FSMContext) -> None:

	sql_daily = await bot.db.get_daily_stats_dates()
	sql_daily_prev = await bot.db.get_daily_stats_dates(-1)
	sql_montly = await bot.db.get_monthly_stats_dates()
	sql_montly_prev = await bot.db.get_monthly_stats_dates(-1)

	payload = {
		'bot': bot.config.BOT_ID,
		'sql_daily': sql_daily,
		'sql_daily_prev': sql_daily_prev,
		'sql_montly': sql_montly,
		'sql_montly_prev': sql_montly_prev,
	}

	payload = orjson.dumps(payload).decode('utf8')
	payload = urllib.parse.quote_plus( payload )
	row_btns = [
		[types.InlineKeyboardButton(text='Статистика', web_app=types.WebAppInfo(url=f'{bot.config.STATS_URL}?payload={payload}'))]
	]
	reply_markup = types.InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)
	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Статистика доступна тут', reply_markup=reply_markup)


@router.message(F.content_type.in_({'text'}), F.text.startswith('http'))
async def prepare_download(message: types.Message, state: FSMContext) -> None:

	if bot.config.LOCKED:
		if message.from_user.id not in bot.config.ADMINS:
			await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Идет разработка" )
			return

	current_state = await state.get_state()
	if current_state is not None:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Отмените или завершите предыдущее скачивание/авторизацию" )
		return

	can_add = await bot.downloads_queue.can_add()
	if not can_add:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Очередь заполнена. Пжалста пдждте" )
		return

	if not bot.config.ACCEPT_NEW:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот временно не принимает новые закачки" )
		return

	query = message.text.strip()
	query = query.split()

	url = ''
	site = ''

	for q in query:
		for r in bot.config.REGEX_LIST:
			m = r.match(q)
			if m:
				site = m.group('site')
				if site not in bot.config.SITES_LIST:
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
			uas = await bot.db.get_all_site_auths(message.from_user.id,site)
			demo_login = True if site in bot.config.DEMO_USER else False
			if uas:
				for ua in uas:
					use_auth[str(ua.id)] = ua.get_name()
			if demo_login:
				use_auth['anon'] = 'Анонимные доступы'
			use_auth['none'] = 'Без авторизации'

		if "paging" in bot.config.SITES_DATA[site]:
			use_start_end = True

		if "images" in bot.config.SITES_DATA[site]:
			use_images = True

		if "force_images" in bot.config.SITES_DATA[site]:
			force_images = True
			use_images = False

		payload = {
			'use_auth': use_auth,
			'use_start': use_start_end,
			'use_end': use_start_end,
			'use_images': use_images,
			'use_cover': True,
			'formats': bot.config.FORMATS,
			'images': True,
			'cover': False,
		}
		payload = orjson.dumps(payload).decode('utf8')
		payload = urllib.parse.quote_plus( payload )
		web_app = types.WebAppInfo(url=f"{bot.config.DOWNLOAD_URL}?payload={payload}")
		
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
		_format = params['format']
		url = params['url']
		msg = f"Добавляю в очередь {url}"
		msg += f"\nФормат {_format}"
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


@router.callback_query(F.data.startswith('cancel:'))
async def cancel_download(callback_query: types.CallbackQuery) -> None:
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




@router.edited_message()
@router.channel_post()
@router.edited_channel_post()
async def _message_handler(message: types.Message) -> Any:

	if message.chat.type == 'channel':
		# await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот не доступен в чатах. Удачи", reply_markup=ReplyKeyboardRemove() )
		await bot.leave_chat(message.chat.id)

	print()
	print('missed message')
	print(message)
	print()

# @router.inline_query()
# async def _inline_query_handler(inline_query: types.InlineQuery) -> Any:
# 	print()
# 	print('missed inline_query')
# 	print(inline_query)
# 	print()

# @router.chosen_inline_result()
# async def _chosen_inline_result_handler(chosen_inline_result: types.ChosenInlineResult) -> Any:
# 	print()
# 	print('missed chosen_inline_result')
# 	print(chosen_inline_result)
# 	print()

# @router.callback_query()
# async def _callback_query_handler(callback_query: types.CallbackQuery) -> Any:
# 	print()
# 	print('missed callback_query')
# 	print(callback_query)
# 	print()

# @router.shipping_query()
# async def _shipping_query_handler(shipping_query: types.ShippingQuery) -> Any:
# 	print()
# 	print('missed shipping_query')
# 	print(shipping_query)
# 	print()
# @router.pre_checkout_query()
# async def _pre_checkout_query_handler(pre_checkout_query: types.PreCheckoutQuery) -> Any:
# 	print()
# 	print('missed pre_checkout_query')
# 	print(pre_checkout_query)
# 	print()

# @router.poll()
# async def _poll_handler(poll: types.Poll) -> Any:
# 	print()
# 	print('missed poll')
# 	print(poll)
# 	print()

# @router.poll_answer()
# async def _poll_answer_handler(poll_answer: types.PollAnswer) -> Any:
# 	print()
# 	print('missed poll_answer')
# 	print(poll_answer)
# 	print()

@router.errors()
async def _error_handler(exception: types.error_event.ErrorEvent) -> Any:
	print()
	print('exception')
	print(exception)
	print()



async def __get_authed_sites(user_id: int, chat_id: int, message_id: int, data: dict) -> None:
	sites = await bot.db.get_all_authed_sites(user_id)
	if len(sites) > 0:
		row_btns = []
		for site in sites:
			row_btns.append([types.InlineKeyboardButton(text=idna.decode(site), callback_data=f'logins:{site}')])
		reply_markup = types.InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)
		await bot.messages_queue.add( callee='edit_message_text', chat_id=chat_id, message_id=message_id, text='Выберите сайт', reply_markup=reply_markup)
	else:
		await bot.messages_queue.add( callee='edit_message_text', chat_id=chat_id, message_id=message_id, text='Нет сохраненных доступов', reply_markup=None)

async def __get_authed_site_logins(user_id: int, chat_id: int, message_id: int, data: dict) -> None:
	site = data[1]
	uas = await bot.db.get_all_site_auths(user_id,site=site)
	row_btns = []
	msg = ''
	if uas:
		for ua in uas:
			row_btns.append([types.InlineKeyboardButton(text=ua.get_name(), callback_data=f'logins:{site}:{ua.id}')])
		row_btns.append([types.InlineKeyboardButton(text='Назад', callback_data=f'logins:all')])
		msg = f'Список доступов для сайта {site}'
	else:
		row_btns.append([types.InlineKeyboardButton(text='Назад', callback_data=f'logins:all')])
		msg = f'Нет сохраненных доступов для сайта {site}'
	reply_markup = types.InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)
	await bot.messages_queue.add( callee='edit_message_text', chat_id=chat_id, message_id=message_id, text=msg, reply_markup=reply_markup)

async def __get_authed_site_login_data(user_id: int, chat_id: int, message_id: int, data: dict) -> None:
	site = data[1]
	ua_id = data[2]
	ua = await bot.db.get_site_auth(ua_id)
	if ua:
		row_btns = []
		row_btns.append([types.InlineKeyboardButton(text='Удалить', callback_data=f'logins:{site}:{ua.id}:delete')])
		row_btns.append([types.InlineKeyboardButton(text='Назад', callback_data=f'logins:{site}')])
		reply_markup = types.InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)
		await bot.messages_queue.add( callee='edit_message_text', chat_id=chat_id, message_id=message_id, text=f'Авторизация:\n\nЛогин: "{ua.login}"\nПароль: "{ua.password}"', reply_markup=reply_markup)


async def __enqueue_download(message: types.Message, params: dict) -> None:
	del params['inited']

	if 'start' in params:
		if params['start']:
			params['start'] = str(params['start'])
		else:
			del params['start']
	if 'end' in params:
		if params['end']:
			params['end'] = str(params['end'])
		else:
			del params['end']
	if 'images' in params:
		params['images'] = '1' if params['images'] else '0'
	if 'cover' in params:
		params['cover'] = '1' if params['cover'] else '0'

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


async def __initiate_download(message: types.Message, download_id: int, last_message: str) -> None:
	await bot.downloads_queue.initiate(download_id=download_id, message_id=message.message_id, last_message=last_message)


def get_router(_bot: Bot):

	global router
	global bot
	bot = _bot

	bot.enqueue_download = __enqueue_download
	bot.initiate_download = __initiate_download

	return router