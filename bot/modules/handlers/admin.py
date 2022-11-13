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

	if message.from_user.id not in bot.config.get('ADMINS'):
		return

	command = message.text.split('/admin')[1]
	command = command.strip()

	# if command == 'delayed_restart':
	# 	bot.config.set('DOWNLOADS_Q_RUNNING',False)
	# 	return await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Инициирована отложенная перезагрузка")

	# if command == 'delayed_restart_cancel':
	# 	bot.config.set('DOWNLOADS_Q_RUNNING',True)
	# 	return await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Отменена отложенная перезагрузка")

	if command == 'reload_config':
		bot.config.reload()
		return await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Конфиг загружен")

	if command == 'stop_accept':
		bot.config.set('ACCEPT_NEW',False)
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот не принимает новые закачки" )

	if command == 'start_accept':
		bot.config.set('ACCEPT_NEW',True)
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Бот принимает новые закачки" )

	if command == 'stop_queue':
		bot.config.set('DOWNLOADS_Q_RUNNING',False)
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Очередь закачкек остановлена" )

	if command == 'start_queue':
		bot.config.set('DOWNLOADS_Q_RUNNING',True)
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Очередь закачкек запущена" )

	# if command.startswith('ban'):
	# 	cmd = command.split()
	# 	uid = cmd[1]
	# 	time = cmd[2] +' '+ cmd[3]
	# 	reason = ' '.join(cmd[4::])
	# 	await bot.db.set_user_ban(uid,reason,time)
	# 	await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Юзер забанен")

	if command.startswith('cancel_download'):
		command = command.split()
		download_id = command[1]
		logger.info(f'cancel_download -> {download_id}')
		if '-' in download_id:
			download_range = download_id.split('-')
			s = int(download_range[0])
			e = int(download_range[1])
			for x in range(s,e):
				logger.info(f'cancel_download r -> {x}')
				await bot.downloads_queue.cancel(x)
		else:
			download_id = int(download_id)
			logger.info(f'cancel_download s -> {download_id}')
			await bot.downloads_queue.cancel(download_id)
		await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text="Закачки отменены" )

	if command == 'supertest':
		url = 'https://author.today/work/195501'
		site = 'author.today'
		_format = 'fb2'

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

		msg = f"Добавляю в очередь {url}"

		_format_name = bot.config.FORMATS[_format]

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
		
		for i in range(0,5):
			await bot.messages_queue.add( callee='send_message', chat_id=message.chat.id, text=msg, callback='enqueue_download', callback_kwargs={'params':params} )