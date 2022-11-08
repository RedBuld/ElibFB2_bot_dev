import asyncio, idna, orjson, urllib.parse, logging
from datetime import datetime
from typing import Any, Optional
from aiogram import Bot, Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, Text
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .models import AuthForm, DownloadConfig

bot = None

router = Router()

direct_functions = {}

logger = logging.getLogger(__name__)

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

	if command.startswith('cancel_d'):
		command = command.split()
		download_id = command[1]
		logger.info(f'cancel_d -> {download_id}')
		if '-' in download_id:
			download_range = download_id.split('-')
			s = int(download_range[0])
			e = int(download_range[1])
			for x in range(s,e):
				logger.info(f'cancel_d r -> {x}')
				await bot.downloads_queue.cancel(x)
		else:
			download_id = int(download_id)
			logger.info(f'cancel_d s -> {download_id}')
			await bot.downloads_queue.cancel(download_id)
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Отменяю закачки" )

@router.message(Command(commands='start'))
async def start_command(message: types.Message, state: FSMContext) -> None:
	await state.clear()
	if bot.config.START_MESSAGE:
		return await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=bot.config.START_MESSAGE, reply_markup=ReplyKeyboardRemove())


@router.message(Command(commands='my_id'))
async def my_id_command(message: types.Message, state: FSMContext) -> None:
	user_id = message.from_user.id
	return await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f'Ваш id {user_id}')

@router.message(Command(commands='format'))
async def format_command(message: types.Message, state: FSMContext) -> None:

	if bot.config.BOT_MODE != 1:
		return

	user_id = message.from_user.id

	row_btns = []
	for fmt in bot.config.FORMATS:
		row_btns.append([InlineKeyboardButton(text=bot.config.FORMATS[fmt], callback_data=f'format:{fmt}')])
	reply_markup = InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)

	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Выберите формат', reply_markup=reply_markup)

@router.callback_query(F.data.startswith('format:'))
async def format_command_format(callback_query: types.CallbackQuery, state: FSMContext) -> None:

	await callback_query.answer()

	data = callback_query.data.split(':')
	_format = str(data[1])
	user_id = callback_query.from_user.id
	_format_name = bot.config.FORMATS[_format]

	await bot.db.add_user_setting(user_id, 'format', _format)
	await bot.messages_queue.add( callee='edit_message_text', chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, text=f'Установлен формат: {_format_name}', reply_markup=None)

@router.message(Command(commands='sites'))
async def sites_command(message: types.Message, state: FSMContext) -> None:

	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f'Список поддерживаемых сайтов:\n'+('\n'.join( [idna.decode(x) for x in bot.config.SITES_LIST] )) )


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
		row_btns = []
		for site in used_for_auth:
			row_btns.append( [InlineKeyboardButton(text=idna.decode(site), callback_data=f'site:{site}')] )

		reply_markup = InlineKeyboardMarkup(row_width=1, inline_keyboard=row_btns)

		await state.set_state(AuthForm.site)

		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Выберите сайт", reply_markup=reply_markup )
	else:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Нет сайтов доступных для авторизации", reply_markup=ReplyKeyboardRemove() )


@router.callback_query(AuthForm.site, F.data.startswith('site:'))
async def login_command_site(callback_query: types.CallbackQuery, state: FSMContext) -> None:

	await callback_query.answer()

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
			row_btns.append([InlineKeyboardButton(text=idna.decode(site), callback_data=f'logins:{site}')])

		reply_markup = InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)

		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Выберите сайт', reply_markup=reply_markup)

		return
	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Нет сохраненных доступов')


@router.callback_query(F.data.startswith('logins:'))
async def logins_command_site(callback_query: types.CallbackQuery, state: FSMContext) -> None:
	await callback_query.answer()

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

	row_btns = [
		[InlineKeyboardButton(text='Статистика', web_app=types.WebAppInfo(url=f'{bot.config.STATS_URL}?bot_id={bot.config.BOT_ID}'))]
	]
	reply_markup = InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)
	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Статистика доступна тут', reply_markup=reply_markup)


@router.message(F.content_type.in_({'text'}), F.text.startswith('http'))
async def prepare_download(message: types.Message, state: FSMContext) -> None:

	if bot.config.LOCKED:
		if message.from_user.id not in bot.config.ADMINS:
			await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Идет разработка" )
			return

	can_add = await bot.downloads_queue.can_add()
	if not can_add:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Очередь заполнена. Пжалста пдждте" )
		return

	if not bot.config.ACCEPT_NEW:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот временно не принимает новые закачки" )
		return

	can_download = await bot.db.can_download(message.from_user.id)
	if not can_download:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Достигнуто максимальное количество бесплатных скачиваний в день' )
		return

	is_user_banned = await bot.db.is_user_banned(message.from_user.id)
	if is_user_banned:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f'Вы были заблокированы. Причина: {is_user_banned.reason}. Срок: {is_user_banned.until}' )
		return

	if bot.config.BOT_MODE == 0:
		return await __mode_0_download(message, state)
	if bot.config.BOT_MODE == 1:
		return await __mode_1_download(message, state)


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
		_format_name = bot.config.FORMATS[_format]
		url = params['url']

		msg = f"Добавляю в очередь {url}"

		msg += f"\nФормат: {_format_name}"

		if 'auth' in params:
			if params['auth'] == 'anon':
				msg += "\nИспользую анонимные доступы"
			elif params['auth'] == 'none':
				msg += "\nБез авторизации"
			elif params['auth']:
				msg += "\nИспользую личные доступы"

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


@router.callback_query(F.data.startswith('download:'))
async def start_preinitiated_download(callback_query: types.CallbackQuery) -> None:
	await callback_query.answer()
	data = callback_query.data.split(':')
	download_id = int(data[1])
	auth = str(data[2])

	reply_markup = InlineKeyboardMarkup(
		inline_keyboard=[
			[
				InlineKeyboardButton( text='Отмена', callback_data=f'cancel:{download_id}' )
			]
		]
	)
	msg = "Добавлено в очередь"
	await bot.messages_queue.add( callee='edit_message_text', chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, text=msg, reply_markup=reply_markup, callback='initiate_download', callback_kwargs={'download_id':download_id,'last_message':msg,'auth':auth,'user_id':callback_query.from_user.id} )

@router.callback_query(F.data.startswith('cancel:'))
async def cancel_download(callback_query: types.CallbackQuery) -> None:
	await callback_query.answer()
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

	logger.info('missed message')
	logger.info(message)

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

# @router.errors()
# async def _error_handler(exception: types.error_event.ErrorEvent) -> Any:
# 	print()
# 	print('exception')
# 	print(exception)
# 	print()




async def __get_authed_sites(user_id: int, chat_id: int, message_id: int, data: dict) -> None:
	sites = await bot.db.get_all_authed_sites(user_id)
	if len(sites) > 0:
		row_btns = []
		for site in sites:
			row_btns.append([InlineKeyboardButton(text=idna.decode(site), callback_data=f'logins:{site}')])
		reply_markup = InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)
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
			row_btns.append([InlineKeyboardButton(text=ua.get_name(), callback_data=f'logins:{site}:{ua.id}')])
		row_btns.append([InlineKeyboardButton(text='Назад', callback_data=f'logins:all')])
		msg = f'Список доступов для сайта {site}'
	else:
		row_btns.append([InlineKeyboardButton(text='Назад', callback_data=f'logins:all')])
		msg = f'Нет сохраненных доступов для сайта {site}'
	reply_markup = InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)
	await bot.messages_queue.add( callee='edit_message_text', chat_id=chat_id, message_id=message_id, text=msg, reply_markup=reply_markup)

async def __get_authed_site_login_data(user_id: int, chat_id: int, message_id: int, data: dict) -> None:
	site = data[1]
	ua_id = data[2]
	ua = await bot.db.get_site_auth(ua_id)
	if ua:
		row_btns = []
		row_btns.append([InlineKeyboardButton(text='Удалить', callback_data=f'logins:{site}:{ua.id}:delete')])
		row_btns.append([InlineKeyboardButton(text='Назад', callback_data=f'logins:{site}')])
		reply_markup = InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)
		await bot.messages_queue.add( callee='edit_message_text', chat_id=chat_id, message_id=message_id, text=f'Авторизация:\n\nЛогин: "{ua.login}"\nПароль: "{ua.password}"', reply_markup=reply_markup)


async def __mode_0_download(message: types.Message, state: FSMContext) -> None:

	if message.chat.type != 'private':
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Данный бот не доступен в чатах" )
		await bot.leave_chat(message.chat.id)

	current_state = await state.get_state()
	if current_state is not None:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Отмените или завершите предыдущее скачивание/авторизацию" )
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
			row_width=1,
			keyboard=[
				[KeyboardButton( text='Скачать', web_app=web_app )],
				[KeyboardButton( text='Отмена' )]
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

async def __mode_1_download(message: types.Message, state: FSMContext) -> None:

	# if message.chat.type == 'channel':
	# 	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот не доступен в чатах" )
	# 	await bot.leave_chat(message.chat.id)

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

		_format = await bot.db.get_user_setting(message.from_user.id,'format')
		if not _format:
			_format = 'fb2'
		else:
			_format = _format.value

		use_auth = {}
		params = {
			'url': url,
			'site': site,
			'user_id': message.from_user.id,
			'chat_id': message.chat.id,
			'images': '1',
			'cover': '1',
			'auth': 'none',
			'format': _format
		}

		download_id = await bot.downloads_queue.add( params=params )

		if "auth" in bot.config.SITES_DATA[site]:
			uas = await bot.db.get_all_site_auths(message.from_user.id,site)
			demo_login = True if site in bot.config.DEMO_USER else False
			if uas:
				for ua in uas:
					use_auth[str(ua.id)] = ua.get_name()
			if demo_login:
				use_auth['anon'] = 'Анонимные доступы'
			use_auth['none'] = 'Без авторизации'

		row_btns = []
		for key, name in use_auth.items():
			row_btns.append([InlineKeyboardButton(text=name, callback_data=f'download:{download_id}:{key}')])
		row_btns.append([InlineKeyboardButton(text='Отмена', callback_data=f'cancel:{download_id}')])

		reply_markup = InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)

		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f"Подготовка к скачиванию {url}\n\nВыберите доступы", reply_markup=reply_markup, callback='preinitiate_download', callback_kwargs={'download_id':download_id} )

async def __enqueue_download(message: types.Message, params: dict) -> None:
	try:
		del params['inited']
	except Exception as e:
		pass

	try:
		if 'start' in params:
			if params['start']:
				params['start'] = str(int(params['start']))
			else:
				del params['start']
		if 'end' in params:
			if params['end']:
				params['end'] = str(int(params['end']))
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
			await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=msg, reply_markup=reply_markup, callback='initiate_download', callback_kwargs={'download_id':download_id,'last_message':msg,'user_id':message.from_user.id} )
		else:
			msg = "Произошла ошибка"
			await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=msg )
	except Exception as e:
		msg = "Произошла ошибка:\n"+repr(e)
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=msg )

async def __preinitiate_download(message: types.Message, download_id: int) -> None:
	await bot.downloads_queue.preinitiate(download_id=download_id, message_id=message.message_id)

async def __initiate_download(message: types.Message, download_id: int, last_message: str, user_id: int, auth: Optional[str]=None) -> None:
	# can_download = await bot.db.can_download(user_id)
	# if not can_download:
	# 	await bot.downloads_queue.preinitiate(download_id=download_id, message_id=message.message_id)
	# 	await bot.downloads_queue.cancel(download_id,False)
	# 	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Достигнуто максимальное количество бесплатных скачиваний в день' )
	# 	return
	await bot.db.add_user_stat(user_id,0)
	await bot.downloads_queue.initiate(download_id=download_id, message_id=message.message_id, last_message=last_message, auth=auth)



def get_router(_bot: Bot):

	global router
	global bot
	bot = _bot

	bot.enqueue_download = __enqueue_download
	bot.initiate_download = __initiate_download
	bot.preinitiate_download = __preinitiate_download

	return router