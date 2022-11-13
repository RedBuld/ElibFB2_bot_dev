import idna, logging
from aiogram import Bot, Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

bot = None

router = Router()

logger = logging.getLogger(__name__)

def get_router(_bot: Bot):
	global router
	global bot
	bot = _bot
	return router

@router.message(Command(commands='start'))
async def start_command(message: types.Message, state: FSMContext) -> None:
	await state.clear()
	msg = bot.config.get('START_MESSAGE')
	if msg:
		return await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=msg, reply_markup=ReplyKeyboardRemove())


@router.message(Command(commands='sites'))
async def sites_command(message: types.Message, state: FSMContext) -> None:
	_sites_list = bot.config.get('SITES_LIST')
	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=f'Список поддерживаемых сайтов:\n'+('\n'.join( [idna.decode(x) for x in _sites_list] )) )


@router.message(Command(commands='stats'))
async def stats_command(message: types.Message, state: FSMContext) -> None:

	_stats_url = bot.config.get('STATS_URL')
	_usage_url = bot.config.get('USAGE_URL')
	_bot_id = bot.config.get('BOT_ID')

	row_btns = []
	if _stats_url:
		row_btns.append( [InlineKeyboardButton(text='Статистика', web_app=types.WebAppInfo(url=f'{_stats_url}?bot_id={_bot_id}'))] )
	if _usage_url:
		row_btns.append( [InlineKeyboardButton(text='Загрузка ботов', web_app=types.WebAppInfo(url=f'{_usage_url}?bot_id={_bot_id}'))] )
	row_btns.append( [InlineKeyboardButton(text='Лимит скачивания', callback_data='stats:free')] )
	row_btns.append( [InlineKeyboardButton(text='Ваш ID', callback_data='stats:id')] )

	reply_markup = InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)
	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Статистика доступна тут', reply_markup=reply_markup)

@router.callback_query(F.data.startswith('stats:'))
async def stats_command_handler(callback_query: types.CallbackQuery, state: FSMContext) -> None:

	await callback_query.answer()

	data = callback_query.data.split(':')[1]
	user_id = callback_query.from_user.id

	if data == 'id':
		return await bot.messages_queue.add( callee='send_message', chat_id=callback_query.message.chat.id, text=f'Ваш ID: {user_id}')

	if data == 'free':
		left = 'Неограничено'
		used = await bot.db.get_user_usage(user_id)
		premium = await bot.db.check_user_premium(user_id)

		_free_limit = bot.config.get('DOWNLOADS_FREE_LIMIT')
		if not premium and _free_limit:
			left = int(_free_limit) - int(used)
			if left < 0:
				left = 0
		return await bot.messages_queue.add( callee='send_message', chat_id=callback_query.message.chat.id, text=f'Лимит загрузок: {left}')

@router.message(Command(commands='format'))
async def format_command(message: types.Message, state: FSMContext) -> None:

	_bot_mode = bot.config.get('BOT_MODE')
	_download_url = bot.config.get('DOWNLOAD_URL')

	user_id = message.from_user.id

	_formats_list = bot.config.get('FORMATS_LIST')
	_formats_params = bot.config.get('FORMATS_PARAMS')
	formats = {}
	for _f in _formats_list:
		formats[_f] = _formats_params[_f]

	row_btns = []
	for fmt in formats:
		row_btns.append([InlineKeyboardButton(text=formats[fmt], callback_data=f'format:{fmt}')])
	reply_markup = InlineKeyboardMarkup(row_width=1,inline_keyboard=row_btns)

	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Выберите формат', reply_markup=reply_markup)


@router.callback_query(F.data.startswith('format:'))
async def format_command_format(callback_query: types.CallbackQuery, state: FSMContext) -> None:

	await callback_query.answer()

	data = callback_query.data.split(':')
	_format = str(data[1])
	user_id = callback_query.from_user.id
	_format_name = bot.config.get('FORMATS_PARAMS')[_format]

	await bot.db.add_user_setting(user_id, 'format', _format)
	await bot.messages_queue.add( callee='edit_message_text', chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, text=f'Установлен формат: {_format_name}', reply_markup=None)


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
async def _message_handler(message: types.Message) -> None:

	if message.chat.type == 'channel':
		# await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот не доступен в чатах. Удачи", reply_markup=ReplyKeyboardRemove() )
		await bot.leave_chat(message.chat.id)

	logger.info('missed message')
	logger.info(message)

# @router.inline_query()
# async def _inline_query_handler(inline_query: types.InlineQuery) -> None:
# 	print()
# 	print('missed inline_query')
# 	print(inline_query)
# 	print()

# @router.chosen_inline_result()
# async def _chosen_inline_result_handler(chosen_inline_result: types.ChosenInlineResult) -> None:
# 	print()
# 	print('missed chosen_inline_result')
# 	print(chosen_inline_result)
# 	print()

# @router.callback_query()
# async def _callback_query_handler(callback_query: types.CallbackQuery) -> None:
# 	print()
# 	print('missed callback_query')
# 	print(callback_query)
# 	print()

# @router.shipping_query()
# async def _shipping_query_handler(shipping_query: types.ShippingQuery) -> None:
# 	print()
# 	print('missed shipping_query')
# 	print(shipping_query)
# 	print()
# @router.pre_checkout_query()
# async def _pre_checkout_query_handler(pre_checkout_query: types.PreCheckoutQuery) -> None:
# 	print()
# 	print('missed pre_checkout_query')
# 	print(pre_checkout_query)
# 	print()

# @router.poll()
# async def _poll_handler(poll: types.Poll) -> None:
# 	print()
# 	print('missed poll')
# 	print(poll)
# 	print()

# @router.poll_answer()
# async def _poll_answer_handler(poll_answer: types.PollAnswer) -> None:
# 	print()
# 	print('missed poll_answer')
# 	print(poll_answer)
# 	print()

# @router.errors()
# async def _error_handler(exception: types.error_event.ErrorEvent) -> None:
# 	print()
# 	print('exception')
# 	print(exception)
# 	print()