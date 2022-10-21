import asyncio, logging, copy
from aiogram.types import FSInputFile
from aiogram.types.input_media_document import InputMediaDocument
from aiogram.types.input_media_photo import InputMediaPhoto
from aiogram.exceptions import TelegramRetryAfter, TelegramMigrateToChat, TelegramBadRequest, TelegramNotFound, TelegramConflictError, TelegramUnauthorizedError, TelegramForbiddenError, TelegramServerError, RestartingTelegram, TelegramAPIError, TelegramEntityTooLarge, ClientDecodeError

logger = logging.getLogger(__name__)

class MessageQueue():
	bot = None
	_queue = {}

	def __init__(self, bot):

		super(MessageQueue, self).__init__()

		self.bot = bot
		self.bot.message_queue = self

		self._queue = {}
		self._running_lock = asyncio.Lock()

	async def start_queue(self):
		self._queue = {}

		await self.restore_tasks()

		logger.info('Starting mq:MessageQueue')

		asyncio.create_task( self.start_check_queue() )

	async def restore_tasks(self):
		db_tasks = await self.bot.db.get_messages_tasks()
		if db_tasks:
			for task in db_tasks:
				self._queue[task] = 0

	async def start_check_queue(self):
		async with self._running_lock:
			logger.info('Starting mq message queue')
			while True:
				await self.check_queue()

	async def check_queue(self):
		messages_ids = list(self._queue.keys()).sort()
		if len(messages_ids) > 0:
			message_id = messages_ids[0]:
			await self._safe_send_message(message_id)
		await asyncio.sleep(self.bot.config.MESSAGES_SEND_INTERVAL)

	async def enqueue(self, callee, *args, **kwargs):
		_args = []
		_kwargs = {}

		for arg in args:
			try:
				_arg = arg.dict()
				_args.append(_arg)
			except Exception as e:
				_args.append(arg)

		for key in kwargs:
			try:
				_kwargs[key] = kwargs[key].dict()
			except Exception as e:
				_kwargs[key] = kwargs[key]

		index = await self.bot.db.add_messages_task(callee=callee, args=_args, kwargs=_kwargs)
		if index:
			self._queue[index] = 0
			return index

		return None

	async def _safe_send_message(self, message_id):

		task = await self.bot.db.get_messages_task(message_id)

		if not task:
			del self._queue[message_id]
			return

		_sended = False
		callback = None
		callback_kwargs = {}
		delete_files = []
		_try = True

		args = task.args
		kwargs = task.kwargs
		callee = task.callee

		if 'callback' in kwargs:
			callback = kwargs['callback']
			del kwargs['callback']

		if 'callback_kwargs' in kwargs:
			callback_kwargs = kwargs['callback_kwargs']
			del kwargs['callback_kwargs']

		if callee == 'send_message_once':
			_try = False
			callee = 'send_message'

		try:

			if callee == 'send_media_group':
				_m = []
				for m in kwargs['media']:
					delete_files.append(m['media'])
					caption = m['caption'] if 'caption' in m else None
					parse_mode = m['parse_mode'] if 'parse_mode' in m else None
					_m.append( InputMediaDocument( media=FSInputFile(m['media']), caption=caption, parse_mode=parse_mode ) )
				kwargs['media'] = _m

			if callee == 'send_document':
				delete_files.append(kwargs['document'])
				kwargs['document'] = FSInputFile(kwargs['document'])

			if callee == 'send_photo':
				delete_files.append(kwargs['photo'])
				kwargs['photo'] = FSInputFile(kwargs['photo'])

			_sended = await getattr(self.bot, callee)(*args, **kwargs)
		# Handling errors
		except TelegramRetryAfter as e:
			logger.error(f"---------\n[TelegramRetryAfter]:\n{repr(e)}\n---------")
			await asyncio.sleep(e.retry_after)
		except TelegramMigrateToChat as e:
			logger.error(f"---------\n[TelegramMigrateToChat]:\n{repr(e)}\n---------")
			pass
		except TelegramBadRequest as e:
			logger.error(f"---------\n[TelegramBadRequest]:\n{repr(e)}\n---------")
			pass
		except TelegramNotFound as e:
			logger.error(f"---------\n[TelegramNotFound]:\n{repr(e)}\n---------")
			pass
		except TelegramConflictError as e:
			logger.error(f"---------\n[TelegramConflictError]:\n{repr(e)}\n---------")
			pass
		except TelegramUnauthorizedError as e:
			logger.error(f"---------\n[TelegramUnauthorizedError]:\n{repr(e)}\n---------")
			pass
		except TelegramForbiddenError as e:
			logger.error(f"---------\n[TelegramForbiddenError]:\n{repr(e)}\n---------")
			pass
		except TelegramServerError as e:
			logger.error(f"---------\n[TelegramServerError]:\n{repr(e)}\n---------")
			pass
		except RestartingTelegram as e:
			logger.error(f"---------\n[RestartingTelegram]:\n{repr(e)}\n---------")
			pass
		except TelegramAPIError as e:
			logger.error(f"---------\n[TelegramAPIError]:\n{repr(e)}\n{repr(args)}\n{repr(kwargs)}\n---------")
			pass
		except TelegramEntityTooLarge:
			logger.error(f"---------\n[TelegramEntityTooLarge]:\n{repr(e)}\n---------")
			pass
		except ClientDecodeError as e:
			logger.error(f"---------\n[ClientDecodeError]:\n{repr(e)}\n---------")
			pass
		except FileNotFoundError:
			logger.error(f"File not found")
			pass
		except Exception as e:
			logger.exception(f"Base exception [Exception],\n---------\n{repr(e)}\n---------")
		finally:
			if not _sended:
				if _try:
					self._queue[message_id] += 1
					# _task['try'] += 1
					if self._queue[message_id] > 3:
						self._queue[message_id] = {
							'callee':'send_message_once',
							'args':{},
							'kwargs':{
								'chat_id':kwargs['chat_id'],
								'text':'Произошла ошибка'
							}
						}
						for delete_file in delete_files:
							proc = await asyncio.create_subprocess_shell(f'rm -rf "{delete_file}"')
							await proc.wait()
			else:
				del self._queue[message_id]

				for delete_file in delete_files:
					proc = await asyncio.create_subprocess_shell(f'rm -rf "{delete_file}"')
					await proc.wait()

				await self.bot.db.remove_messages_task(message_id)
				if callback:
					# try:
					await getattr(self.bot, callback)(_sended, **callback_kwargs)
					# await callback(_sended,**callback_kwargs)
					# except Exception as e:
					# 	pass
		# await asyncio.sleep(self.bot.config.MESSAGES_SEND_INTERVAL)