import orjson, urllib.parse, logging
from typing import Any, Optional
from aiogram import Bot, Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ..models import DownloadConfig

bot = None

router = Router()

logger = logging.getLogger(__name__)

def get_router(_bot: Bot):
	global router
	global bot
	bot = _bot
	bot.enqueue_download = __enqueue_download
	bot.initiate_download = __initiate_download
	return router

@router.message(F.content_type.in_({'text'}), F.text.startswith('http'))
async def prepare_download(message: types.Message, state: FSMContext) -> None:

	if bot.config.get('LOCKED'):
		_admins = bot.config.get('ADMINS')
		if message.from_user.id not in _admins:
			await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Идет разработка" )
			return

	can_add = await bot.downloads_queue.can_add()
	if not can_add:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Очередь заполнена. Пжалста пдждте" )
		return

	if not bot.config.get('ACCEPT_NEW'):
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот временно не принимает новые закачки" )
		return

	can_download = await bot.db.check_user_limit(message.from_user.id)
	if not can_download:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Достигнуто максимальное количество бесплатных скачиваний в день' )
		return

	check_user_banned = await bot.db.check_user_banned(message.from_user.id)
	if check_user_banned:
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f'Вы были заблокированы. Причина: {check_user_banned.reason}. Срок: {check_user_banned.until}' )
		return

	_bot_mode = bot.config.get('BOT_MODE')
	_download_url = bot.config.get('DOWNLOAD_URL')

	print('_bot_mode,_download_url')
	print(_bot_mode,_download_url)

	if _bot_mode == 0 and _download_url:
		return await __mode_0_download_prepare(message, state)
	else:
		return await __mode_1_download_prepare(message, state)


@router.message(DownloadConfig.state, F.content_type.in_({'web_app_data'}))
async def mode_0_download_handler(message: types.Message, state: FSMContext) -> None:
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

		_formats_list = bot.config.get('FORMATS_LIST')
		_formats_params = bot.config.get('FORMATS_PARAMS')
		if _format not in _formats_list:
			_format = _formats_list[0]
			params['format'] = _format
		_format_name = _formats_params[_format]

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


@router.callback_query(F.data.startswith('pd:'))
async def mode_1_download_handler(callback_query: types.CallbackQuery, state: FSMContext) -> None:

	can_add = await bot.downloads_queue.can_add()
	if not can_add:
		await bot.messages_queue.add( callee='send_message', chat_id=callback_query.message.chat.id, text="Очередь заполнена. Пжалста пдждте" )
		return

	can_download = await bot.db.check_user_limit(callback_query.from_user.id)
	if not can_download:
		await bot.messages_queue.add( callee='send_message', chat_id=callback_query.message.chat.id, text='Достигнуто максимальное количество бесплатных скачиваний в день' )
		return

	check_user_banned = await bot.db.check_user_banned(callback_query.from_user.id)
	if check_user_banned:
		await bot.messages_queue.add( callee='send_message', chat_id=callback_query.message.chat.id, text=f'Вы были заблокированы. Причина: {check_user_banned.reason}. Срок: {check_user_banned.until}' )
		return

	await callback_query.answer()
	data = callback_query.data.split(':')
	link_id = int(data[1])
	auth = str(data[2])

	url = await bot.db.get_link(link_id)

	_regex_list = bot.config.get('REGEX_LIST')
	_sites_list = bot.config.get('SITES_LIST')
	for r in _regex_list:
		m = r.match(url)
		if m:
			site = m.group('site')
			if site not in _sites_list:
				site = None
			break

	_format = await bot.db.get_user_setting(callback_query.from_user.id,'format')
	_format = _format.value

	params = {
		'url': url,
		'site': site,
		'user_id': callback_query.from_user.id,
		'chat_id': callback_query.message.chat.id,
		'images': '1',
		'cover': '1',
		'auth': auth,
		'format': _format
	}

	if url:
		msg = f"Добавляю в очередь {url}"

		_formats_list = bot.config.get('FORMATS_LIST')
		_formats_params = bot.config.get('FORMATS_PARAMS')
		if _format not in _formats_list:
			_format = _formats_list[0]
			params['format'] = _format
		_format_name = _formats_params[_format]

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
		await bot.messages_queue.add( callee='edit_message_text', chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, text=msg, reply_markup=None, callback='enqueue_download', callback_kwargs={'params':params} )
	else:
		await bot.messages_queue.add( callee='send_message', chat_id=callback_query.message.chat.id, text='Отправьте ссылку еще раз', reply_markup=ReplyKeyboardRemove())

@router.callback_query(F.data.startswith('dqc:'))
async def cancel_download(callback_query: types.CallbackQuery, state: FSMContext) -> None:
	await callback_query.answer()
	download_id = int(callback_query.data.split(':')[1])
	if download_id > 0:
		await bot.downloads_queue.cancel(download_id)


async def __mode_0_download_prepare(message: types.Message, state: FSMContext) -> None:

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

	_regex_list = bot.config.get('REGEX_LIST')
	_sites_list = bot.config.get('SITES_LIST')
	for q in query:
		for r in _regex_list:
			m = r.match(q)
			if m:
				site = m.group('site')
				if site not in _sites_list:
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

		_sites_params = bot.config.get('SITES_PARAMS')

		if "auth" in _sites_params[site]:
			uas = await bot.db.get_all_site_auths(message.from_user.id,site)
			demo_login = True if site in bot.config.get('BUILTIN_AUTHS') else False
			if uas:
				for ua in uas:
					use_auth[str(ua.id)] = ua.get_name()
			if demo_login:
				use_auth['anon'] = 'Анонимные доступы'
			use_auth['none'] = 'Без авторизации'

		if "paging" in _sites_params[site]:
			use_start_end = True

		if "images" in _sites_params[site]:
			use_images = True

		if "force_images" in _sites_params[site]:
			force_images = True
			use_images = False

		_format = await bot.db.get_user_setting(message.from_user.id,'format')
		if _format and _format.value:
			_format = _format.value
		else:
			_format = None

		_formats_list = bot.config.get('FORMATS_LIST')
		_formats_params = bot.config.get('FORMATS_PARAMS')
		formats = {}
		for _f in _formats_list:
			formats[_f] = _formats_params[_f]

		payload = {
			'use_auth': use_auth,
			'use_start': use_start_end,
			'use_end': use_start_end,
			'use_images': use_images,
			'use_cover': True,
			'formats': formats,
			'format': _format,
			'images': True,
			'cover': False,
		}
		_download_url = bot.config.get('DOWNLOAD_URL')

		payload = orjson.dumps(payload).decode('utf8')
		payload = urllib.parse.quote_plus( payload )
		web_app = types.WebAppInfo(url=f"{_download_url}?payload={payload}")
		
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

async def __mode_1_download_prepare(message: types.Message, state: FSMContext) -> None:

	# if message.chat.type == 'channel':
	# 	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот не доступен в чатах" )
	# 	await bot.leave_chat(message.chat.id)

	query = message.text.strip()
	query = query.split()

	url = ''
	site = ''

	_regex_list = bot.config.get('REGEX_LIST')
	_sites_list = bot.config.get('SITES_LIST')
	for q in query:
		for r in _regex_list:
			m = r.match(q)
			if m:
				site = m.group('site')
				if site not in _sites_list:
					site = None
				else:
					url = q
				break
		if url:
			break

	if url:

		_format = await bot.db.get_user_setting(message.from_user.id,'format')
		if not _format or not _format.value:
			await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f"Не выбран формат. Нажмите /format" )
			return

		use_auth = {}

		link = await bot.db.maybe_add_link(url)

		# download_id = await bot.downloads_queue.add( params=params )
		_sites_params = bot.config.get('SITES_PARAMS')

		if "auth" in _sites_params[site]:
			uas = await bot.db.get_all_site_auths(message.from_user.id,site)
			demo_login = True if site in bot.config.get('BUILTIN_AUTHS') else False
			if uas:
				for ua in uas:
					use_auth[str(ua.id)] = ua.get_name()
			if demo_login:
				use_auth['anon'] = 'Анонимные доступы'
			use_auth['none'] = 'Без авторизации'
		else:
			use_auth['none'] = 'Скачать'

		row_btns = []
		for key, name in use_auth.items():
			row_btns.append([InlineKeyboardButton(text=name, callback_data=f'pd:{link}:{key}')])
		# row_btns.append([InlineKeyboardButton(text='Отмена', callback_data=f'plain_download_cancel')])

		reply_markup = InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)

		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f"Подготовка к скачиванию {url}\n\nВыберите доступы", reply_markup=reply_markup )

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

		_format = params['format']
		_convertable = bot.config.get('CONVERT_PARAMS')

		if _format in _convertable:
			params['target_format'] = _format
			params['format'] = _convertable[_format]

		download_id = await bot.downloads_queue.add( params=params )
		if download_id:
			reply_markup = InlineKeyboardMarkup(
				inline_keyboard=[
					[
						InlineKeyboardButton( text='Нельзя отменить', callback_data=f'dqc:0' )
					]
				]
			)
			msg = "Добавляю в очередь"
			await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=msg, reply_markup=reply_markup, callback='initiate_download', callback_kwargs={'download_id':download_id,'last_message':msg} )
		else:
			msg = "Произошла ошибка"
			await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=msg )
	except Exception as e:
		msg = "Произошла ошибка:\n"+repr(e)
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=msg )

async def __initiate_download(message: types.Message, download_id: int, last_message: str) -> None:
	added = await bot.downloads_queue.initiate(download_id=download_id, message_id=message.message_id, last_message=last_message)
	if added:
		await bot.db.update_user_usage_extended(added.user_id,added.site)


