import asyncio, logging, copy
from typing import Optional
from aiogram.types import FSInputFile
from aiogram.types.input_media_document import InputMediaDocument
from aiogram.types.input_media_photo import InputMediaPhoto
from aiogram.exceptions import TelegramRetryAfter, TelegramMigrateToChat, TelegramBadRequest, TelegramNotFound, TelegramConflictError, TelegramUnauthorizedError, TelegramForbiddenError, TelegramServerError, RestartingTelegram, TelegramAPIError, TelegramEntityTooLarge, ClientDecodeError
from aiogram import Bot
from .db import Message

logger = logging.getLogger(__name__)

class MessagesQueue():
	bot = None
	_thread = None
	_running_lock = None
	_max_try = 3

	_queue = {}
	_cancelled = []

	def __init__(self, bot: Bot) -> None:

		super(MessagesQueue, self).__init__()

		self.bot = bot
		self.bot.messages_queue = self

		self._queue = {}
		self._cancelled = []
		self._running_lock = asyncio.Lock()

	@property
	def __queue_ids__(self) -> list:
		l = list(self._queue.keys())
		l.sort()
		return l

	@property
	def __cancelled_ids__(self) -> list:
		return list(self._cancelled)

	# PUBLIC

	async def start(self) -> None:
		self._queue = {}
		self._cancelled = []

		logger.info('Starting mq:MessagesQueue')

		await self.__queue_restore()

		self._thread = asyncio.create_task( self.__queue_run() )

	async def stop(self) -> None:

		logger.info('Stopping mq:MessagesQueue')

		if self._thread:
			self._thread.cancel()
		return

	async def add(self, callee: str, *args, **kwargs) -> Optional[int]:
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

		params = {
			'callee':callee,
			'args':_args,
			'kwargs':_kwargs
		}

		index = await self.bot.db.add_message(params)
		if index:
			self._queue[index] = 0
			return index

		return None

	async def update_or_add(self, callee: str, mq_id: Optional[int]=None, *args, **kwargs) -> Optional[int]:
		update = False

		if mq_id and mq_id in self._queue:
			update = True
			del self._queue[mq_id]

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

		params = {
			'callee':callee,
			'args':_args,
			'kwargs':_kwargs
		}

		index = None

		if update:
			message = await self.bot.db.update_message(mq_id, params)
			if message:
				index = message.id
		else:
			index = await self.bot.db.add_message(params)

		if index:
			self._queue[index] = 0
			return index

		return None

	async def cancel(self, message_id: int) -> None:
		if message_id not in self._cancelled:
			self._cancelled.append( message_id )
			await self.bot.db.remove_message( message_id )

	# PRIVATE

	async def __queue_restore(self) -> None:
		db_tasks = await self.bot.db.get_all_messages()
		if db_tasks:
			for task in db_tasks:
				self._queue[task] = 0

	async def __queue_run(self) -> None:
		try:
			async with self._running_lock:
				logger.info('Messages queue running')
				while True:
					await self.__queue_step()
		except asyncio.CancelledError:
			pass
		except Exception as e:
			logger.error('Messages queue error: '+repr(e))

	async def __queue_step(self) -> None:

		_cancelled_ids = self.__cancelled_ids__
		for message_id in _cancelled_ids:
			del self._cancelled[message_id]

			if message_id in self._queue:
				del self._queue[message_id]
				await self.bot.db.remove_message(message_id)

		if len(self.__queue_ids__) > 0:
			message_id = self.__queue_ids__.pop(0)
			try_count = self._queue[message_id]
			try:
				del self._queue[message_id]
			except Exception as e:
				pass
			try:
				asyncio.create_task( self.__process_message(message_id,try_count) )
			except Exception as e:
				logger.error('mq:__process_message error'+repr(e))


		await asyncio.sleep( self.bot.config.get('MESSAGES_Q_INTERVAL') )

	async def __process_message(self, message_id: int, try_count: int) -> None:

		try:
			del self._queue[message_id]
		except Exception as e:
			pass

		task = await self.bot.db.get_message(message_id)

		if not task:
			return

		_try = True
		_ignore = False
		_sended = False

		callback = None
		callback_kwargs = {}
		delete_files = []

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
			return self.__process_message(message_id,try_count)
		except TelegramMigrateToChat as e:
			logger.error(f"---------\n[TelegramMigrateToChat]:\n{repr(e)}\n---------")
			pass
		except TelegramBadRequest as e:
			if 'message is not modified' in str(e):
				_ignore = True
			if 'chat not found' in str(e):
				_ignore = True
			if 'web App buttons' in str(e):
				_ignore = True
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
			if 'bot was blocked' in str(e):
				_ignore = True
			if 'bot is not a member' in str(e):
				_ignore = True
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
			_try = False
			self._queue[message_id] = self._max_try
			logger.error(f"---------\n[TelegramEntityTooLarge]:\n{repr(e)}\n---------")
			pass
		except ClientDecodeError as e:
			logger.error(f"---------\n[ClientDecodeError]:\n{repr(e)}\n---------")
			pass
		except FileNotFoundError:
			_try = False
			self._queue[message_id] = self._max_try
			logger.error(f"File not found")
			pass
		except Exception as e:
			logger.exception(f"Base exception [Exception],\n---------\n{repr(e)}\n---------")
		finally:

			if not _sended:

				if _ignore:
					await self.bot.db.remove_message(message_id)
					return

				if _try:
					try_count += 1
				
				if try_count > self._max_try:

					params = {
						'callee':'send_message_once',
						'args':[],
						'kwargs':{
							'chat_id': kwargs['chat_id'],
							'text':'Произошла ошибка'
						}
					}

					message = await self.bot.db.update_message(message_id, params)

					try:
						self._queue[message_id] = 0
					except Exception as e:
						pass

					for delete_file in delete_files:
						proc = await asyncio.create_subprocess_shell(f'rm -rf "{delete_file}"')
						await proc.wait()
					
				else:

					try:
						self._queue[message_id] = try_count
					except Exception as e:
						pass
			else:

				try:
					del self._queue[message_id]
				except Exception as e:
					pass

				await self.bot.db.remove_message(message_id)

				for delete_file in delete_files:
					proc = await asyncio.create_subprocess_shell(f'rm -rf "{delete_file}"')
					await proc.wait()

				if callback:
					try:
						await getattr(self.bot, callback)(_sended, **callback_kwargs)
					except Exception as e:
						logger.info('--')
						logger.info(callback)
						logger.error(e)
						logger.info('--')
						pass