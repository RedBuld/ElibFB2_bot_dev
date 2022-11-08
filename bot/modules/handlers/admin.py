import logging
from aiogram import Bot, Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

bot = None

router = Router()

logger = logging.getLogger(__name__)

def get_router(_bot: Bot):
	global router
	global bot
	bot = _bot
	return router

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

	if command == 'stop_accept':
		bot.config.ACCEPT_NEW = False
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот не принимает новые закачки" )

	if command == 'start_accept':
		bot.config.ACCEPT_NEW = True
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот принимает новые закачки" )

	if command.startswith('ban'):
		cmd = command.split()
		uid = cmd[1]
		time = cmd[2] +' '+ cmd[3]
		reason = ' '.join(cmd[4::])
		await bot.db.set_user_ban(uid,reason,time)
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Юзер забанен")

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

	if command == 'supertest':
		reply_markup = InlineKeyboardMarkup(
			inline_keyboard=[
				[
					InlineKeyboardButton( text='Тест 1', callback_data=f'supertest:asdasdasdasdasasasdasdasdasdasdasdasdasdasdasasd' )
				]
				# [
				# 	InlineKeyboardButton( text='Тест 2', callback_data=f'supertest:asdasdasdasdasasdasdasdasdasdasdadsasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasasdasdasdasdasdasdadsasdasdasdasdasdasdasdasdasdasdasdasdasdasdasd' )
				# ],
				# [
				# 	InlineKeyboardButton( text='Тест 3', callback_data=f'supertest:asdasdasdasdasasdasdasdasdasdasdadsasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasasdasdasdasdasdasdadsasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasdasasdasdasdasdasdasdadsasdasdasdasdasdasdasdasdasdasdasdasdasdasdasd' )
				# ]
			]
		)
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text='Супертест', reply_markup=reply_markup)

@router.callback_query(F.data.startswith('supertest:'))
async def admin_test_qcb(callback_query: types.CallbackQuery) -> None:
	await callback_query.answer()

	print(callback_query.data)
