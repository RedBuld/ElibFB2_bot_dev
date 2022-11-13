import asyncio, re, os, logging, glob, orjson, ijson
import aiogram.utils.markdown as fmt
from pathlib import Path
from typing import Optional, Union, Iterator
from time import time
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .db import DOWNLOAD_STATUS, Download

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
	_process = None
	_log_file = None
	_files_dir = None
	_running_lock = None
	_chapters_ln = 0

	bot = None
	task = None
	status = DOWNLOAD_STATUS.INIT
	action = ''
	result = {}
	last_status = {}
	mq_id = None

	def __repr__(self) -> str:
		return str({
			'task': self.task,
			'status': self.status,
			'process': self._process.pid if self._process else False,
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
		self.mq_id = self.task.mq_message_id
		self._running_lock = asyncio.Lock()
		self._path = str(self.bot.config.get('BOT_ID'))+'-'+str(self.task.user_id)+'-'+str(self.task.id)
		self._log_file = os.path.join( self.bot.config.get('DOWNLOADER_LOG_PATH'), self._path+'.log' )
		self._files_dir = os.path.join( self.bot.config.get('DOWNLOADER_TEMP_PATH'), self._path )
		self._running_lock = asyncio.Lock()
		self._chapters_ln = 0


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

		# await self.bot.db.add_user_usage_extended(self.task.user_id,self.task.site)

		if not self._thread:

			proc = await asyncio.create_subprocess_shell(f'rm -rf "{self._log_file}"')
			await proc.wait()

			proc = await asyncio.create_subprocess_shell(f'rm -rf "{self._files_dir}"')
			await proc.wait()

			if self.status == DOWNLOAD_STATUS.INIT:
				self.status = DOWNLOAD_STATUS.RUNNING
				await self.update_status()
				try:
					self._thread = asyncio.create_task( self.__start() )
				except asyncio.CancelledError:
					pass
			if self.status == DOWNLOAD_STATUS.PROCESSING:
				try:
					self._thread = asyncio.create_task( self.__process() )
				except asyncio.CancelledError:
					pass

	async def cancel(self) -> None:
		self.status = DOWNLOAD_STATUS.CANCELLED

		if self._process:
			self._process.kill()

		if self._thread:
			self._thread.cancel()

		self.status = DOWNLOAD_STATUS.CANCELLED

		await self.update_status()
		return True

	async def stop(self) -> None:

		# await self.bot.db.reduce_user_usage_extended(self.task.user_id,self.task.site)

		status = self.status

		if self._process:
			self._process.kill()

		if self._thread:
			self._thread.cancel()

		self.status = status

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
			# if len(self.result['files']) > 1:
			# 	async for files in self.__chunked_media_group():
			# 		media = []
			# 		for file in files:
			# 			m = {
			# 				'media': file,
			# 				'caption': self.result['caption'],
			# 				'parse_mode':'MarkdownV2'
			# 			}
			# 			media.append(m)
			# 		await self.bot.messages_queue.add( 'send_media_group', chat_id=self.task.chat_id, media=media )
			# else:
			# 	await self.bot.messages_queue.add( 'send_document', chat_id=self.task.chat_id, document=self.result['files'][0], caption=self.result['caption'], parse_mode='MarkdownV2' )
			for file in self.result['files']:
				await self.bot.messages_queue.add( 'send_document', chat_id=self.task.chat_id, document=file, caption=self.result['caption'], parse_mode='MarkdownV2' )

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
			message = 'Загрузка завершена, выгружаю файлы'

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
			self.last_status['timestamp'] <= ( timestamp - self.bot.config.get('DOWNLOADS_NOTICES_INTERVAL') )
		)

		if need_send:

			if cancellable == 0:
				reply_markup = InlineKeyboardMarkup(
					inline_keyboard=[
						[
							InlineKeyboardButton( text='Нельзя отменить', callback_data=f'dqc:0' )
						]
					]
				)
			if cancellable == 1:
				reply_markup = InlineKeyboardMarkup(
					inline_keyboard=[
						[
							InlineKeyboardButton( text='Отмена', callback_data=f'dqc:{self.task.id}' )
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
				logger.info(f'Started download: {self.task}')
				await self.__download()
				await self.__process()
				logger.info(f'Ended download: {self.task}')
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
			# if not line.startswith('Загружена картинка'):
			# 	last_line = line
			last_line = line
			if last_line.startswith('Начинаю сохранение книги'):
				last_line = 'Сохраняю файлы'
			if 'успешно сохранена' in last_line:
				last_line = 'Файл скачан'
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
			yield self.result['files'][i:i + 10]


	async def __download(self) -> None:

		_exec, args = await self.__prepare_command()

		try:
			with open(self._log_file,'w') as log:
				self._process = await asyncio.create_subprocess_exec(_exec, *args, stdout=log, cwd=self.bot.config.get('DOWNLOADER_PATH'))
			await self._process.wait()

			if self._process.returncode != 0:
				raise Exception('Произошла ошибка')

			_json, file, cover = await self.__process_results()

			if not _json:
				raise Exception('Файл конфигурации не найден')

			file_caption = await self.__process_caption(_json)

			self.result['caption'] = file_caption

			if cover:
				if os.path.exists(cover):
					self.result['cover'] = cover

			if file:
				if os.path.exists(file):
					self.result['files'].append( file )
			else:
				raise Exception('Произошла ошибка чтения файлов')

			self.status = DOWNLOAD_STATUS.PROCESSING
			await self.update_status()

		except asyncio.CancelledError:
			pass

		except Exception as e:
			self.status = DOWNLOAD_STATUS.ERROR
			error_text = await self.__process_error('Произошла ошибка:',e=e)
			self.result['files'].append( self._log_file )
			self.result['caption'] = error_text
			await self.update_status()
			return

	async def __process(self) -> None:
		if self.status == DOWNLOAD_STATUS.PROCESSING:
			try:
				try:
					await self.__process_files()
				except Exception as e:
					raise e

				size = await self.__process_files_size()

				await self.bot.db.add_site_stat( self.task.site, size )

				self.status = DOWNLOAD_STATUS.DONE
				await self.update_status()

			except asyncio.CancelledError:
				pass

			except Exception as e:
				self.status = DOWNLOAD_STATUS.ERROR
				error_text = await self.__process_error('Произошла ошибка:',e=e)
				self.result['files'].append( self._log_file )
				self.result['caption'] = error_text
				await self.update_status()
				return

	async def __prepare_command(self) -> str:

		_exec = 'dotnet'
		command = []

		command.append('Elib2Ebook.dll')
		command.append('--save')
		command.append(f"{self._files_dir}")
		# _dpath = self.bot.config.get('DOWNLOADER_PATH')
		# command = f'cd {_dpath}; dotnet Elib2Ebook.dll --save "{self._files_dir}"'

		task = self.task

		if task.url:
			# command += f' --url "{task.url}"'
			command.append('--url')
			command.append(f"{task.url}")

		if task.format:
			# command += f' --format "{task.format},json"'
			command.append('--format')
			command.append(f"{task.format},json")
		else:
			command.append('--format')
			_def = self.bot.config.get('FORMATS_LIST')[0]
			command.append(f"{_def},json")

		if task.start:
			# command += f' --start "{task.start}"'
			command.append('--start')
			command.append(f"{task.start}")

		if task.end:
			# command += f' --end "{task.end}"'
			command.append('--end')
			command.append(f"{task.end}")

		_proxied = self.bot.config.get('PROXY_PARAMS')
		if task.site in _proxied:
			_p = _proxied[task.site]
			# command += f' --proxy "{_p}" -timeout 120'
			command.append('--proxy')
			command.append(f"{_p}")
			command.append('--timeout')
			command.append('120')
		else:
			if task.proxy:
				command.append('--proxy')
				command.append(f"{task.proxy}")
				command.append('--timeout')
				command.append('120')
			else:
				# command += f' --timeout 30'
				command.append('--timeout')
				command.append('60')

		if task.cover == '1':
			# command += ' --cover'
			command.append('--cover')

		if task.images == '0':
			# command += ' --no-image'
			command.append('--no-image')

		if task.auth:
			login = None
			password = None
			if task.auth == 'anon':
				try:
					_auths = self.bot.config.get('BUILTIN_AUTHS')
					if task.site in _auths:
						login = _auths[task.site]['login']
						password = _auths[task.site]['password']
				except Exception as e:
					pass
			elif task.auth != 'none':
				try:
					_auth = await self.bot.db.get_site_auth(int(task.auth))
					if _auth:
						login = _auth.login
						password = _auth.password
				except Exception as e:
					pass

			if login and password:
				if not login.startswith('/') and not login.startswith('http:') and not login.startswith('https:') and not password.startswith('/') and not password.startswith('http:') and not password.startswith('https:'):
					# command += f' --login="{login}" --password="{password}"'
					command.append('--login')
					command.append(f"{login}")
					command.append('--password')
					command.append(f"{password}")

		# command += f' > {self._log_file}'
		logger.info('__prepare_command')
		logger.info(command)

		return _exec, command

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

		for _t in _trash:
			proc = await asyncio.create_subprocess_shell(f'rm -rf "{_t}"')
			await proc.wait()

		return _json, file, cover

	async def __process_caption(self, _json_file: Union[str, Path]) -> str:
		# logger.info('__process_caption')
		book_caption = []
		_title = ''
		_author = ''
		_seria = ''
		_chapters = ''

		_book_title = ''
		_book_url = ''
		_author_name = ''
		_author_url = ''
		_seria_name = ''
		_seria_number = ''
		_seria_url = ''
		_book_chapters = []
		_book_chapter = None
		try:
			if _json_file is not None:
				with open(_json_file, "rb") as f:
					parser = ijson.parse(f)
					for prefix, event, value in parser:
						if prefix == 'Title':
							_book_title = value
						if prefix == 'Url':
							_book_url = value
						if prefix == 'Author.Name':
							_author_name = value
						if prefix == 'Author.Url':
							_author_url = value
						if prefix == 'Seria.Name':
							_seria_name = value
						if prefix == 'Seria.Number':
							_seria_number = value
						if prefix == 'Seria.Url':
							_seria_url = value
						if prefix == 'Chapters.item' and event == 'start_map':
							_book_chapter = {}
						if prefix == 'Chapters.item.Title':
							_book_chapter['Title'] = value
						if prefix == 'Chapters.item.IsValid':
							_book_chapter['IsValid'] = value
						if prefix == 'Chapters.item' and event == 'end_map':
							_book_chapters.append(_book_chapter)
							_book_chapter = None

				if _book_title:
					t = TAG_RE.sub('', _book_title)
					if _book_url:
						u = TAG_RE.sub('', _book_url)
						_title = fmt.link( t, u )
					else:
						_title = fmt.text( fmt.escape_md(t) )
				if _author_name:
					t = TAG_RE.sub('', _author_name)
					if _author_url:
						u = TAG_RE.sub('', _author_url)
						_author = fmt.text( 'Автор: ', fmt.link(t,u) )
					else:
						_author = fmt.text( 'Автор: ', fmt.escape_md(t) )
				if _seria_name:
					t = TAG_RE.sub('', _seria_name)
					if _seria_url:
						u = TAG_RE.sub('', _seria_url)
						_seria = fmt.text( 'Серия: ', fmt.link(t,u) )
					else:
						_seria = fmt.text( 'Серия: ', fmt.escape_md(t) )
					if _seria_number:
						t = TAG_RE.sub('', _seria_number)
						_seria += fmt.text( ' №', fmt.escape_md(t) )
				if _book_chapters:
					_tc = 0
					_vc = 0
					_fc = ''
					_lc = ''
					if len(_book_chapters) > 0:
						for chapter in _book_chapters:
							if chapter['Title']:
								_tc += 1
								if chapter['IsValid']:
									_vc += 1
									if not _fc:
										_fc = chapter['Title']
									_lc = chapter['Title']
						self._chapters_ln = _tc
						if _fc and _lc:
							_fc = TAG_RE.sub('', _fc)
							_lc = TAG_RE.sub('', _lc)
							_chapters = fmt.text( 'Глав ', fmt.escape_md(_vc), 'из', fmt.escape_md(_tc), ', с ', fmt.escape_md(f'"{_fc}"'), ' по ', fmt.escape_md(f'"{_lc}"') )
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

	async def __process_files(self) -> list:

		await self.__process_files__maybe_rename()

		await self.__process_files__maybe_convert()

		await self.__process_files__maybe_split()

	async def __process_files__maybe_rename(self) -> None:

		_cl = ''
		if self.task.start or self.task.end:
			if self._chapters_ln > 0:
				_start = self.task.start
				_end = self.task.end

				if _start and _end:
					_start = int(_start)
					_end = int(_end)
					if _start > 0 and _end > 0:
						_cl = f'-parted-{_start}-{_end}'
					elif _start > 0 and _end < 0:
						__end = _start+self._chapters_ln
						_cl = f'-parted-{_start}-{__end}'
				elif _start and not _end:
					_start = int(_start)
					if _start > 0:
						__end = _start+self._chapters_ln
						_cl = f'-parted-{_start}-{__end}'
					else:
						if abs(_start) >= self._chapters_ln:
							_cl = f'-parted-last{_start}'
				elif _end and not _start:
					_end = int(_end)
					if _end > 0:
						_cl = f'-parted-1-{self._chapters_ln}'
					else:
						if abs(_end) >= self._chapters_ln:
							_cl = f'-parted-first{_end}'

			path = self.result['files'][0]


			if _cl != '':
				file = os.path.basename(path)
				_tmp_name, extension = os.path.splitext(file)

				_tmp_name = _tmp_name+_cl
				_tmp_path = os.path.join(self._files_dir, _tmp_name+extension)

				proc = await asyncio.create_subprocess_shell(f'mv "{path}" "{_tmp_path}"')
				await proc.wait()

				self.result['files'][0] = _tmp_path

	async def __process_files__maybe_convert(self) -> int:

		_converters_path = self.bot.config.get('CONVERTERS_PATH')

		if self.task.target_format and _converters_path:
			source_path = os.path.dirname( self.result['files'][0] )
			target_path = os.path.join( source_path, 'converted' )

			_exec = 'python3'
			command = []
			command.append('convert.py')
			command.append(source_path)
			command.append(target_path)
			command.append(self.task.target_format)

			os.makedirs(target_path,exist_ok=True)

			self._process = await asyncio.create_subprocess_exec(_exec, *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=_converters_path)
			await self._process.wait()
			# stdout, stderr = await self._process.communicate()

			file = None
			_trash = []

			t = os.listdir(target_path)
			for x in t:
				_tmp_name, extension = os.path.splitext(x)
				extension = extension[1:]
				if extension == self.task.target_format:
					file = os.path.join(target_path, x)
				else:
					_trash.append(os.path.join(target_path, x))

			for _t in _trash:
				proc = await asyncio.create_subprocess_shell(f'rm -rf "{_t}"')
				await proc.wait()

			if file:
				orig_file = self.result['files'][0]
				proc = await asyncio.create_subprocess_shell(f'rm -rf "{orig_file}"')
				await proc.wait()
				self.result['files'][0] = file

	async def __process_files__maybe_split(self) -> int:

		if len(self.result['files']) == 1:

			_return = []
			path = self.result['files'][0]

			fsize = os.path.getsize(path)
			_split_limit = self.bot.config.get('DOWNLOADS_SPLIT_LIMIT')

			if fsize > _split_limit:
				file = os.path.basename(path)
				_tmp_name, extension = os.path.splitext(file)

				splitted_folder = os.path.join(self._files_dir, 'splitted')
				os.makedirs(splitted_folder,exist_ok=True)

				splitted_file = os.path.join(splitted_folder, f'{_tmp_name}.zip')

				sfs = int(_split_limit / 1024 / 1024)
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
				_return.append(self.result['files'][0])
			self.result['files'] = _return

	async def __process_files_size(self) -> int:
		size = 0
		for file in self.result['files']:
			fsize = os.path.getsize(file)
			size += fsize
		return int(size/1024)

	async def __process_error(self, message: str, command: Optional[str]=None, e: Optional[Exception]=None) -> str:
		if e:
			message += '\n'+fmt.escape_md(repr(e))
		if message:
			logger.error(message)
		if command:
			logger.error('command')
			logger.error(command)
		logger.error('Downloader')
		logger.error(self)
		return message