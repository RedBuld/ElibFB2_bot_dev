import idna, logging
from aiogram import Bot, Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ..models import AuthForm

bot = None

router = Router()

logger = logging.getLogger(__name__)

def get_router(_bot: Bot):
	global router
	global bot
	bot = _bot
	return router

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