import asyncio, re, os, logging, glob, orjson
import aiogram.utils.markdown as fmt
from pathlib import Path
from typing import Optional, Union, Iterator
from time import time
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from modules.db import DOWNLOAD_STATUS, Download

logger = logging.getLogger(__name__)

TAG_RE = re.compile(r'<[^>]+>')

def escape_md(*content, sep=" ") -> str:
	"""
	Escape markdown text
	E.g. for usernames
	:param content:
	:param sep:
	:return:
	"""
	return fmt.markdown_decoration.quote(fmt._join(*content, sep=sep))
fmt.escape_md = escape_md

class Downloader(object):
	_path = ''
	_thread = None
	_log_file = None
	_files_dir = None

	bot = None
	task = None
	status = DOWNLOAD_STATUS.INIT
	action = ''
	process = None
	result = {}
	last_status = {}
	mq_id = None

	def __repr__(self) -> str:
		return str({
			'task': self.task,
			'status': self.status,
			'process': self.process.pid if self.process else False,
			'result': self.result,
			'last_status': self.last_status,
		})

	def __init__(self, bot: Bot, task: Download) -> None:
		self.bot = bot
		self.task = task
		self.status = self.task.status
		self.action = ''
		self.last_status = {
			'message': self.task.last_message,
			'status': self.status,
			'timestamp': time(),
			'cancellable': self.__cancellable__(),
		}
		self.result = {
			'cover': None,
			'files': [],
			'caption': None
		}
		self._running_lock = asyncio.Lock()
		self.mq_id = self.task.mq_message_id
		self._path = str(self.task.chat_id)+'-'+str(self.task.id)
		self._log_file = os.path.join( self.bot.config.DOWNLOADER_LOG_PATH, self._path+'.log' )
		self._files_dir = os.path.join( self.bot.config.DOWNLOADER_TEMP_PATH, self._path )


	def __cancellable__(self) -> None:
		if self.status == DOWNLOAD_STATUS.CANCELLED:
			return 2
		if self.status == DOWNLOAD_STATUS.ERROR:
			return 2
		if self.status == DOWNLOAD_STATUS.DONE:
			return 2
		if self.status == DOWNLOAD_STATUS.PROCESSING:
			return 0
		return 1

	async def start(self) -> None:
		self.status = DOWNLOAD_STATUS.RUNNING

		await self.update_status()

		self._thread = asyncio.create_task( self.__start() )

	async def cancel(self) -> None:

		if self._thread:
			self._thread.cancel()

		if self.process:
			await self.process.kill()

		await self.clear_results()

		await self.update_status()

	async def clear_results(self) -> None:
		proc = await asyncio.create_subprocess_shell(f'rm -rf "{self._log_file}"')
		await proc.wait()

		proc = await asyncio.create_subprocess_shell(f'rm -rf "{self._files_dir}"')
		await proc.wait()

	async def send_results(self) -> None:
		if self.result['cover']:
			if self.status != DOWNLOAD_STATUS.ERROR:
				await self.bot.messages_queue.add( 'send_photo', chat_id=self.task.chat_id, photo=self.result['cover'] )
			else:
				cover = self.result['cover']
				proc = await asyncio.create_subprocess_shell(f'rm -rf "{cover}"')
				await proc.wait()

		if self.result['files']:
			if len(self.result['files']) > 1:
				async for files in self.__chunked_media_group():
					media = []
					for file in files:
						m = {
							'media': file,
							'caption': self.result['caption'],
							'parse_mode':'MarkdownV2'
						}
						media.append(m)
					await self.bot.messages_queue.add( 'send_media_group', chat_id=self.task.chat_id, media=media )
			else:
				await self.bot.messages_queue.add( 'send_document', chat_id=self.task.chat_id, document=self.result['files'][0], caption=self.result['caption'], parse_mode='MarkdownV2' )

		if self.status != DOWNLOAD_STATUS.ERROR:
			proc = await asyncio.create_subprocess_shell(f'rm -rf "{self._log_file}"')
			await proc.wait()

	async def update_status(self) -> None:
		message = ''

		if self.last_status['status'] in [ DOWNLOAD_STATUS.CANCELLED, DOWNLOAD_STATUS.ERROR, DOWNLOAD_STATUS.DONE ]:
			return

		if self.status == DOWNLOAD_STATUS.INIT:
			message = 'Загрузка начата'

		if self.status == DOWNLOAD_STATUS.RUNNING:
			message = await self.__get_last_line()
			if not message and self.last_status['status'] == DOWNLOAD_STATUS.INIT:
				message = 'Загрузка начата'

		if self.status == DOWNLOAD_STATUS.PROCESSING:
			message = 'Обработка файлов'

		if self.status == DOWNLOAD_STATUS.DONE:
			message = 'Загрузка завершена'

		if self.status == DOWNLOAD_STATUS.ERROR:
			message = 'Произошла ошибка'

		if self.status == DOWNLOAD_STATUS.CANCELLED:
			message = 'Загрузка отменена'

		if not message:
			message = self.last_status['message']
		# else:
		# 	message = self.url+'\n'+message

		cancellable = self.__cancellable__()
		timestamp = time()

		need_send = (
			self.last_status['message'] != message
			or
			self.last_status['status'] != self.status
			or
			self.last_status['cancellable'] != cancellable
			or
			self.last_status['timestamp'] <= ( timestamp - self.bot.config.DOWNLOADS_NOTICES_INTERVAL )
		)

		if need_send:

			if cancellable == 0:
				reply_markup = InlineKeyboardMarkup(
					inline_keyboard=[
						[
							InlineKeyboardButton( text='Нельзя отменить', callback_data=f'cancel:0' )
						]
					]
				)
			if cancellable == 1:
				reply_markup = InlineKeyboardMarkup(
					inline_keyboard=[
						[
							InlineKeyboardButton( text='Отмена', callback_data=f'cancel:{self.task.id}' )
						]
					]
				)
			if cancellable == 2:
				reply_markup = None

			mq_id = self.mq_id

			if self.last_status['message'] != message:
				mq_id = await self.bot.messages_queue.update_or_add( callee='edit_message_text', mq_id=self.task.mq_message_id, chat_id=self.task.chat_id, message_id=self.task.message_id, text=message, reply_markup=reply_markup)
			else:
				if self.last_status['cancellable'] != cancellable:
					mq_id = await self.bot.messages_queue.update_or_add( callee='edit_message_reply_markup', mq_id=self.task.mq_message_id, chat_id=self.task.chat_id, message_id=self.task.message_id, reply_markup=reply_markup)
				# else:
				# 	timestamp = self.last_status['timestamp']
			self.mq_id = mq_id

		self.last_status = {
			'message': message,
			'status': self.status,
			'cancellable': cancellable,
			'timestamp': timestamp,
		}

		task = await self.bot.db.update_download( self.task.id, {'status':self.status,'last_message':message,'mq_message_id':self.mq_id,'result':self.result} )
		self.task = task

	# PRIVATE

	async def __start(self) -> None:
		try:
			async with self._running_lock:
				logger.info(f'Started download #{self.task.id}')
				await self.__download()
				logger.info(f'Ended download #{self.task.id}')
		except asyncio.CancelledError:
			pass
		except Exception as e:
			logger.error('Download error: '+repr(e))

	async def __get_last_line(self) -> str:
		line = ''
		last_line = ''
		if not os.path.exists(self._log_file):
			return ''
		with open(self._log_file, 'r') as f:
			for line in f:
				pass
			last_line = line
		return last_line

	async def __get_last_line_seek(self) -> str:
		list_of_lines = []
		if not os.path.exists(self._log_file):
			return ''
		with open(self._log_file, 'rb') as read_obj:
			read_obj.seek(0, os.SEEK_END)
			buffer = bytearray()
			pointer_location = read_obj.tell()
			while pointer_location >= 0:
				read_obj.seek(pointer_location)
				pointer_location = pointer_location -1
				new_byte = read_obj.read(1)
				if new_byte == b'\n':
					list_of_lines.append(bytes(reversed(buffer)).decode())
					buffer = bytearray()
					if len(list_of_lines) > 1:
						break
				else:
					buffer.extend(new_byte)
			if len(buffer) > 0:
				list_of_lines.append(bytes(reversed(buffer)).decode())

		if len(list_of_lines) > 1:
			return list_of_lines[0]
		return ''

	async def __chunked_media_group(self) -> Iterator[Union[str, Path]]:
		for i in range(0, len(self.result['files']), 10):
			yield self.result['files'][i:i + n]


	async def __download(self) -> None:

		command = await self.__prepare_command()

		try:
			self.process = await asyncio.create_subprocess_shell(command)
			await self.process.wait()

			if self.process.returncode != 0:
				raise Exception('Произошла ошибка')

			_json, file, cover = await self.__process_results()

			if not _json:
				raise Exception('Файл конфигурации не найден')

			self.status = DOWNLOAD_STATUS.PROCESSING

			file_caption = await self.__process_caption(_json)

			self.result['caption'] = file_caption

			if cover:
				if os.path.exists(cover):
					self.result['cover'] = cover

			if file:
				if os.path.exists(file):
					try:
						files = await self.__process_split_files(file)
					except Exception as e:
						raise e
					for _file in files:
						self.result['files'].append( _file )
			else:
				raise Exception('Произошла ошибка чтения файлов')

		except asyncio.CancelledError:
			pass

		except Exception as e:
			self.status = DOWNLOAD_STATUS.ERROR
			error_text = await self.__process_error('Произошла ошибка:',command=command,e=e)
			self.result['files'].append( self._log_file )
			self.result['caption'] = error_text
			return

		self.status = DOWNLOAD_STATUS.DONE

		await self.update_status()

	async def __prepare_command(self) -> str:
		# logger.info('__prepare_command')
		command = f'cd {self.bot.config.DOWNLOADER_PATH}; dotnet Elib2Ebook.dll --save "{self._files_dir}"'

		task = self.task

		if task.url:
			command += f' --url "{task.url}"'

		if task.format:
			command += f' --format "{task.format},json"'

		if task.start:
			command += f' --start "{task.start}"'

		if task.end:
			command += f' --end "{task.end}"'

		if task.site in self.bot.config.PROXY_LIST:
			_p = self.bot.config.PROXY_LIST[task.site]
			command += f' --proxy "{_p}" -t 120'
		else:
			command += f' --timeout 30'

		if task.cover:
			command += ' --cover'

		if not task.images:
			command += ' --no-image'

		if task.auth:
			login = None
			password = None
			if task.auth == 'self':
				try:
					_auth = await self.bot.db.get_user_auth(task.user_id,task.site)
					if _auth:
						login = _auth.login
						password = _auth.password
				except Exception as e:
					pass

			if task.auth == 'anon':
				try:
					if task.site in self.bot.config.DEMO_USER:
						login = self.bot.config.DEMO_USER[task.site]['login']
						password = self.bot.config.DEMO_USER[task.site]['password']
				except Exception as e:
					pass

			if login and password:
				if not login.startswith('/') and not login.startswith('http:') and not login.startswith('https:') and not password.startswith('/') and not password.startswith('http:') and not password.startswith('https:'):
					command += f' --login="{login}" --password="{password}"'

		command += f' > {self._log_file}'

		return command

	async def __process_results(self) -> tuple:
		# logger.info('__process_results')
		_json = None
		cover = None
		file = None
		_trash = []
		
		t = os.listdir(self._files_dir)
		for x in t:
			_tmp_name, extension = os.path.splitext(x)
			extension = extension[1:]
			if extension == 'json':
				_json = os.path.join(self._files_dir, x)
			elif extension == self.task.format:
				file = os.path.join(self._files_dir, x)
			elif extension in ['jpg','jpeg','png','gif']:
				cover = os.path.join(self._files_dir, x)
			else:
				_trash.append(os.path.join(self._files_dir, x))

		return _json, file, cover

	async def __process_caption(self, _json_file: Union[str, Path]) -> str:
		# logger.info('__process_caption')
		book_caption = []
		_title = ''
		_author = ''
		_chapters = ''
		_seria = ''
		try:
			if _json_file is not None:
				with open(_json_file, 'r') as t:
					_json_data = t.read()
					if _json_data:
						_json = orjson.loads(_json_data)
						if _json:
							if 'Title' in _json and _json['Title']:
								t = TAG_RE.sub('', _json["Title"])
								if "Url" in _json and _json["Url"]:
									u = TAG_RE.sub('', _json["Url"])
									_title = fmt.link( t, u )
								else:
									_title = fmt.text( fmt.escape_md(t) )
							if 'Author' in _json and _json['Author']:
								if "Name" in _json["Author"] and _json["Author"]["Name"]:
									t = TAG_RE.sub('', _json["Author"]["Name"])
									if 'Url' in _json['Author'] and _json['Author']['Url']:
										u = TAG_RE.sub('', _json["Author"]["Url"])
										_author = fmt.text( 'Автор: ', fmt.link(t,u) )
									else:
										_author = fmt.text( 'Автор: ', fmt.escape_md(t) )
							if 'Seria' in _json and _json['Seria']:
								if 'Name' in _json['Seria'] and _json['Seria']['Name']:
									t = TAG_RE.sub('', _json["Seria"]["Name"])
									_seria = fmt.text( 'Серия: ', fmt.escape_md(t) )
								if 'Number' in _json['Seria'] and _json['Seria']['Number']:
									t = TAG_RE.sub('', _json["Seria"]["Number"])
									_seria += fmt.text( ', №', fmt.escape_md(t) )
							if 'Chapters' in _json and _json['Chapters']:
								_tc = 0
								_vc = 0
								_lc = ''
								if len(_json['Chapters']) > 0:
									for chapter in _json['Chapters']:
										if chapter['Title']:
											_tc += 1
											if chapter['IsValid']:
												_vc += 1
												_lc = chapter['Title']
									if _lc:
										t = TAG_RE.sub('', _lc)
										_chapters = fmt.text( 'Глав ', fmt.escape_md(_vc), 'из', fmt.escape_md(_tc), ', по ', fmt.escape_md(f'"{t}"') )
									else:
										_chapters = fmt.text( 'Глав ', fmt.escape_md(_vc), 'из', fmt.escape_md(_tc) )
		except Exception as e:
			await self.__process_error('Произошла ошибка чтения json',e=e)

		proc = await asyncio.create_subprocess_shell(f'rm -rf "{_json_file}"')
		await proc.wait()

		if _title:
			book_caption.append(_title)
		if _author:
			book_caption.append(_author)
		if _seria:
			book_caption.append(_seria)
		if _chapters:
			book_caption.append('\n'+_chapters)

		book_caption.append('\n')
		book_caption.append( fmt.text( fmt.link('Спасибо автору качалки','https://boosty.to/elib2ebook'), fmt.escape_md(' (Boosty)') ) )

		book_caption = '\n'.join(book_caption)

		return book_caption

	# SERVICE

	async def __process_split_files(self, file: Union[str, Path]) -> list:
		# logger.info('__process_split_files')

		fsize = os.path.getsize(file)
		_return = []

		if fsize > self.bot.config.DOWNLOADS_SPLIT_LIMIT:
			_tmp_name, extension = os.path.splitext(file)
			_tmp_name = _tmp_name.split(self._files_dir)[1][1:]

			splitted_folder = os.path.join(self._files_dir, 'splitted')
			os.makedirs(splitted_folder,exist_ok=True)

			splitted_file = os.path.join(splitted_folder, f'{_tmp_name}.zip')

			sfs = int(self.bot.config.DOWNLOADS_SPLIT_LIMIT / 1024 / 1024)
			sfs = f'{sfs}m'
			cmd = f'cd {self._files_dir}; zip -s {sfs} "{splitted_file}" "{file}"'

			proc = await asyncio.create_subprocess_shell(cmd)
			await proc.wait()

			proc = await asyncio.create_subprocess_shell(f'rm -rf "{file}"')
			await proc.wait()

			t = os.listdir(splitted_folder)
			for x in t:
				_return.append( os.path.join(splitted_folder, x) )
		else:
			_return.append(file)
		return _return

	async def __process_error(self, message: str, command: Optional[str]=None, e: Optional[Exception]=None) -> str:
		if e:
			message += '\n'+repr(e)
		if message:
			logger.error(message)
		if command:
			logger.error('command')
			logger.error(command)
		logger.error('Downloader')
		logger.error(self)
		return message