import asyncio, logging, copy
from modules.downloader import Downloader
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from modules.db import DOWNLOAD_STATUS_CANCELLED, DOWNLOAD_STATUS_WAIT, DOWNLOAD_STATUS_INIT, DOWNLOAD_STATUS_RUNNING, DOWNLOAD_STATUS_PROCESSING, DOWNLOAD_STATUS_DONE

logger = logging.getLogger(__name__)

class DownloaderQueue():
	bot = None
	_running_lock = None
	_temp = []
	_queue = {}
	_active = {}
	_cancelled = []

	def __init__(self, bot):

		super(DownloaderQueue, self).__init__()

		self.bot = bot
		self.bot.download_queue = self

		self._downloading_lock = asyncio.Lock()
		self._notices_lock = asyncio.Lock()
		self._temp = []
		self._queue = {}
		self._active = {}

	async def start_queue(self):
		self._temp = []
		self._queue = {}
		self._active = {}

		# print()
		# print()
		# print('db_tasks')
		# print(db_tasks)
		# print()
		# print()
		await self.restore_tasks()


		logger.info('Starting dq:DownloaderQueue')
		logger.info('self._queue')
		logger.info(self._queue)
		logger.info('self._active')
		logger.info(self._active)

		# asyncio.create_task( self.start_check_queue() )
		# asyncio.create_task( self.start_notices_queue() )
		# asyncio.create_task( self.start_cancel_queue() )

	async def restore_tasks(self):
		db_tasks = await self.bot.db.get_download_tasks()
		if db_tasks:
			for task in db_tasks:
				if task.status == DOWNLOAD_STATUS_DONE:
					print('DONE')
					print(task)
					print()
				if task.status == DOWNLOAD_STATUS_PROCESSING:
					print('PROCESSING')
					print(task)
					print()
				if task.status == DOWNLOAD_STATUS_RUNNING:
					print('RUNNING')
					print(task)
					print()
				if task.status == DOWNLOAD_STATUS_INIT:
					self._queue[task.id] = 
				if task.status == DOWNLOAD_STATUS_WAIT:
					self._temp.append(task.id)

	async def start_check_queue(self):
		async with self._downloading_lock:
			logger.info('Starting dq downloading queue')
			while True:
				await self.iter_downloads_queue()

	async def start_notices_queue(self):
		async with self._notices_lock:
			logger.info('Starting dq notices queue')
			while True:
				await self.check_notices_queue()

	async def start_cancel_queue(self):
		async with self._notices_lock:
			logger.info('Starting dq cancel queue')
			while True:
				await self.check_cancel_queue()

	async def iter_downloads_queue(self):

		# if len(self._queue) > 0:
		# 	while len(self._active) < self.bot.config.DOWNLOADS_SIMULTANEOUSLY:
		# 		if not len(self._queue) > 0:
		# 			break
		# 		fk = list(self._queue.keys())[0]
		# 		if fk not in self._cancelled:
		# 			_task = self._queue[fk]
		# 			self._active[fk] = await self.create_downloader(_task['index'], _task['chat_id'], _task['message_id'], _task['params'])
		# 			del self._queue[fk]

		for download_id in self._cancelled:
			del self._cancelled[download_id]
			if download_id in self._active:
				await task.cancel()
				del self._active[download_id]

		if len(self._active) > 0:
			download_ids = list(self._active.keys())
			for download_id in download_ids:
				task = self._active[download_id]
				if task:
					if task.status == DOWNLOAD_STATUS_WAIT:
						await task.start()
					elif task.status == DOWNLOAD_STATUS_RUNNING or task.status == DOWNLOAD_STATUS_PROCESSING:
						await task.update_status()
					elif task.status == DOWNLOAD_STATUS_CANCELLED:
						await task.clear_results()
						del self._active[download_id]
					elif task.status == DOWNLOAD_STATUS_DONE:
						await task.send_results()
						del self._active[download_id]
						# asyncio.create_task( self.send_results( data ) )
						# del self._active[download_id]

		free_slots = self.bot.config.DOWNLOADS_SIMULTANEOUSLY - len(self._active)
		if free_slots > 0:
			used_free_slots = 0
			download_ids = list(self._queue)
			for download_id in download_ids:
				if used_free_slots < free_slots:
					await self.create_downloader(download_id)
					self._queue.remove(download_id)
					used_free_slots += 1

		await asyncio.sleep(self.bot.config.DOWNLOADS_CHECK_INTERVAL)

	async def check_notices_queue(self):

		if len(self._active) > 0:
			download_ids = list(self._active.keys())
			for download_id in download_ids:
				if download_id in self._active:
					downloader = self._active[download_id]
					msg = await downloader.get_status()
					if msg:
						await self.bot.message_queue.enqueue( 'edit_message_text', chat_id=downloader.chat_id, message_id=downloader.message_id, text=msg['text'], reply_markup=msg['reply_markup'] )

		if len(self._queue) > 0:
			download_ids = list(self._queue.keys())
			for download_id in download_ids:
				if download_id in self._queue:
					download = self._queue[download_id]
					reply_markup = InlineKeyboardMarkup(
						inline_keyboard=[
							[
								InlineKeyboardButton( text='Отмена', callback_data=f'cancel:{download_id}' )
							]
						]
					)
					msg = await self.check(download_id)
					if msg and msg != download['last_message']:
						self._queue[download_id]['last_message'] = msg
						await self.bot.message_queue.enqueue( 'edit_message_text', chat_id=download['chat_id'], message_id=download['message_id'], text=msg, reply_markup=reply_markup )

		await asyncio.sleep(self.bot.config.DOWNLOADS_NOTICES_INTERVAL)

	async def check_cancel_queue(self):

		if len(self._cancelled) > 0:
			_cancelled = copy.deepcopy(self._cancelled)
			for download_id in _cancelled:
				if download_id in self._queue:
					chat_id = self._queue[download_id]['chat_id']
					message_id = self._queue[download_id]['message_id']
					del self._queue[download_id]
					self._cancelled.remove(download_id)
					await self.bot.message_queue.enqueue( 'edit_message_text', chat_id=chat_id, message_id=message_id, text='Загрузка отменена', reply_markup=None )
				if download_id in self._active:
					await self._active[download_id].cancel()
					del self._active[download_id]
					self._cancelled.remove(download_id)

		await asyncio.sleep(5)

	async def enqueue(self, params: dict):

		if 'book_link' in params and params['book_link']:
			index = await self.bot.db.add_download_task(params)
			if index:
				self._temp.append(index)
				return index
		return None

	async def cancel(self, download_id: int):
		if download_id not in self._cancelled:
			self._cancelled.append( download_id )
			# task = await self.bot.db.remove_download_task(download_id)
			# if task and task.message_id:
			# 	await self.bot.message_queue.enqueue( 'edit_message_text', chat_id=task.chat_id, message_id=task.message_id, text='Загрузка отменена', reply_markup=None )


	async def set_message(self, download_id: int, message_id: int, last_message: str):
		task = await self.bot.db.update_download_task(download_id,{'last_message':last_message,'message_id':message_id,'status':DOWNLOAD_STATUS_INIT})
		if task:
			self._queue[index] = {'position':None,'last_message':last_message,'mq_id':None}
			self._queue[index]['position'] = list(self._queue.keys()).index(index)
		del self._temp[index]


	async def create_downloader(self, download_id):
		task = await self.bot.db.get_download_task(download_id)
		if task:
			downloader = Downloader(
				query=self,
				task=task
			)
	
	# async def check(self, index: int):
	# 	indexes = list(self._queue.keys())
	# 	if index in indexes:
	# 		i = indexes.index(index)+1
	# 		return 'Место в очереди: '+str(i)+' из '+str(len(indexes))
	# 	return None