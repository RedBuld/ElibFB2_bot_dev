import asyncio, logging, copy
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .db import DOWNLOAD_STATUS, Download

logger = logging.getLogger(__name__)

class DownloadsQueue():
	bot = None
	_thread = None
	_running_lock = None

	_temp = []
	_queue = {}
	_active = {}
	_cancelled = []

	def __init__(self, bot: Bot) -> None:

		super(DownloadsQueue, self).__init__()

		self.bot = bot
		self.bot.downloads_queue = self

		self._running_lock = asyncio.Lock()
		self._temp = []
		self._queue = {}
		self._active = {}
		self._cancelled = []

	@property
	def __queue_ids__(self) -> list:
		l = list(self._queue.keys())
		l.sort()
		return l

	@property
	def __active_ids__(self) -> list:
		l = list(self._active.keys())
		l.sort()
		return l

	@property
	def __cancelled_ids__(self) -> list:
		l = list(self._cancelled)
		l.sort()
		return l

	# PUBLIC

	async def start(self) -> None:
		self._temp = []
		self._queue = {}
		self._active = {}
		self._cancelled = []

		logger.info('Starting dq:DownloadsQueue')

		await self.__queue_restore()

		self._thread = asyncio.create_task( self.__queue_run() )

	async def stop(self) -> None:

		logger.info('Stopping dq:DownloadsQueue')

		_active_ids = self.__active_ids__
		for download_id in _active_ids:
			task = self._active[download_id]
			await task.stop()

		if self._thread:
			self._thread.cancel()
		return

	async def can_add(self) -> bool:
		return len(self.__queue_ids__) < self.bot.config.DOWNLOADS_Q_LIMIT

	async def add(self, params: dict) -> Optional[int]:

		if 'url' in params and params['url']:
			index = await self.bot.db.add_download(params)
			if index:
				self._temp.append(index)
				return index
		return None

	async def cancel(self, download_id: int, drop_usage: bool=True) -> None:
		if download_id in self._temp:
			await self.__queue_cancel(download_id,drop_usage)
			return
		if download_id not in self._cancelled:
			self._cancelled.append( download_id )
			# await self.bot.db.update_download( download_id, {'status':DOWNLOAD_STATUS.CANCELLED} )
			# task = await self.bot.db.remove_download(download_id)
			# if task and task.message_id:
			# 	await self.bot.messages_queue.add( 'edit_message_text', chat_id=task.chat_id, message_id=task.message_id, text='Загрузка отменена', reply_markup=None )

	async def initiate(self, download_id: int, message_id: int, last_message: str) -> bool:
		payload = {'last_message':last_message,'message_id':message_id,'status':DOWNLOAD_STATUS.INIT}
		task = await self.bot.db.update_download( download_id, payload )
		if task:
			await self.__queue_add(task)
			try:
				self._temp.remove(download_id)
			except Exception as e:
				pass
			return True
		return False


	# PRIVATE


	async def __queue_restore(self) -> None:
		db_tasks = await self.bot.db.get_all_downloads()
		if db_tasks:
			for task in db_tasks:
				if task.status == DOWNLOAD_STATUS.CANCELLED:
					# logger.info('CANCELLED')
					# logger.info(task)
					await self.__init_downloader(task.id)
				if task.status == DOWNLOAD_STATUS.ERROR:
					# logger.info('ERROR')
					# logger.info(task)
					await self.__init_downloader(task.id)
				if task.status == DOWNLOAD_STATUS.DONE:
					# logger.info('DONE')
					# logger.info(task)
					await self.__init_downloader(task.id)
				if task.status == DOWNLOAD_STATUS.PROCESSING:
					# logger.info('PROCESSING')
					# logger.info(task)
					task.status = DOWNLOAD_STATUS.INIT
					await self.bot.db.update_download( task.id, {'status':task.status} )
					await self.__queue_add(task,_upd=False)
				if task.status == DOWNLOAD_STATUS.RUNNING:
					# logger.info('RUNNING')
					# logger.info(task)
					task.status = DOWNLOAD_STATUS.INIT
					await self.bot.db.update_download( task.id, {'status':task.status} )
					await self.__queue_add(task,_upd=False)
				if task.status == DOWNLOAD_STATUS.INIT:
					# logger.info('INIT')
					# logger.info(task)
					await self.__queue_add(task,_upd=False)
				if task.status == DOWNLOAD_STATUS.WAIT:
					# logger.info('WAIT')
					# logger.info(task)
					self._temp.append(task.id)

	async def __queue_run(self) -> None:
		try:
			async with self._running_lock:
				logger.info('Downloads queue running')
				while True:
					await self.__queue_step()
		except asyncio.CancelledError:
			pass
		except Exception as e:
			logger.error('Downloads queue error: '+repr(e))
			raise e

	async def __queue_step(self) -> None:

		_cancelled_ids = self.__cancelled_ids__
		for download_id in _cancelled_ids:
			self._cancelled.remove(download_id)

			if download_id in self._active:
				await self._active[download_id].cancel()
				# del self._active[download_id]

			if download_id in self._queue:
				await self.__queue_cancel(download_id)
				# del self._queue[download_id]

		_active_ids = self.__active_ids__
		for download_id in _active_ids:
			task = self._active[download_id]
			if task:
				if task.status == DOWNLOAD_STATUS.CANCELLED:
					await task.clear_results()
					await self.bot.db.remove_download(download_id)
					del self._active[download_id]

				elif task.status == DOWNLOAD_STATUS.ERROR:
					await task.send_results()
					await self.bot.db.remove_download(download_id)
					del self._active[download_id]

				elif task.status == DOWNLOAD_STATUS.DONE:
					await task.send_results()
					await self.bot.db.remove_download(download_id)
					del self._active[download_id]

				elif task.status == DOWNLOAD_STATUS.PROCESSING:
					await task.update_status()

				elif task.status == DOWNLOAD_STATUS.RUNNING:
					await task.update_status()

				elif task.status == DOWNLOAD_STATUS.INIT:
					await task.start()

		queue_moved = False
		free_slots = self.bot.config.DOWNLOADS_SIMULTANEOUSLY - len(self.__active_ids__)
		if free_slots > 0:
			_queue_ids = self.__queue_ids__[0:free_slots+1]
			for download_id in _queue_ids:
				await self.__init_downloader(download_id)
				del self._queue[download_id]
			queue_moved = True

		if queue_moved:
			_waiting_ids = self.__queue_ids__
			for download_id in _waiting_ids:
				await self.__queue_moved(download_id)

		await asyncio.sleep(self.bot.config.DOWNLOADS_Q_INTERVAL)
	
	async def __queue_add(self, task: Download, _upd: Optional[bool]=True) -> None:
		self._queue[task.id] = {'position':None,'last_message':task.last_message,'chat_id':task.chat_id,'message_id':task.message_id,'mq_id':task.mq_message_id}
		self._queue[task.id]['position'] = self.__queue_ids__.index(task.id)
		if _upd:
			await self.__queue_moved(task.id)
	
	async def __queue_moved(self, download_id: int) -> None:
		position = self.__queue_ids__.index(download_id)+1
		if position != self._queue[download_id]['position']:
			self._queue[download_id]['position'] = position
			message = f'Позиция в очереди: {position}'
			if message != self._queue[download_id]['last_message']:
				self._queue[download_id]['last_message'] = message
				reply_markup = InlineKeyboardMarkup(
					inline_keyboard=[
						[
							InlineKeyboardButton( text='Отмена', callback_data=f'cancel:{download_id}' )
						]
					]
				)
				mq_id = await self.bot.messages_queue.update_or_add( callee='edit_message_text', mq_id=self._queue[download_id]['mq_id'], chat_id=self._queue[download_id]['chat_id'], message_id=self._queue[download_id]['message_id'], text=message, reply_markup=reply_markup)
				await self.bot.db.update_download( download_id, {'last_message':message,'mq_message_id':mq_id} )

	async def __queue_cancel(self, download_id: int, drop_usage: bool=True):
		task = await self.bot.db.remove_download(download_id)
		if download_id in self._temp:
			try:
				self._temp.remove(download_id)
			except Exception as e:
				pass
		if download_id in self._queue:
			try:
				del self._queue[download_id]
			except Exception as e:
				pass
		if task:
			message = 'Загрузка отменена'
			reply_markup = None
			await self.bot.messages_queue.update_or_add( callee='edit_message_text', mq_id=task.mq_message_id, chat_id=task.chat_id, message_id=task.message_id, text=message, reply_markup=reply_markup)

	async def __init_downloader(self, download_id: int) -> None:
		from modules.downloader import Downloader
		task = await self.bot.db.get_download(download_id)
		if task:
			downloader = Downloader(bot=self.bot,task=task)
			self._active[download_id] = downloader