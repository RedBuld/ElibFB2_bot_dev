import asyncio, re, os, logging, glob, aiofiles, orjson, pprint
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import aiogram.utils.markdown as fmt

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
	bot = None
	status = 'init'
	index = None
	chat_id = None
	message_id = None
	user_id = None
	site = None
	book_link = None
	start = None
	end = None
	format = None
	auth = None
	images = True
	cover = False
	process = None
	log_file = None
	files_path = None
	last_message = ''
	reply_markup = None
	result_files = {
		'cover': None,
		'files': [],
		'caption': None
	}
	_path_name = ''

	def __repr__(self):
		return str({
			'status': self.status,
			'chat_id': self.chat_id,
			'message_id': self.message_id,
			'user_id': self.user_id,
			'site': self.site,
			'book_link': self.book_link,
			'log_file': self.log_file,
			'process': self.process.pid if self.process else False,
			'start': self.start,
			'end': self.end,
			'format': self.format,
			'auth': self.auth,
			'images': self.images,
			'cover': self.cover,
			'result_files': self.result_files
		})

	def __init__(self, index, bot, chat_id, message_id, params):
		self.bot = bot
		self.index = index
		self.status = STATUS_INIT
		self.chat_id = chat_id
		self.message_id = message_id
		self.user_id = params['user_id'] if 'user_id' in params else None
		self.site = params['site'] if 'site' in params else None
		self.book_link = params['book_link'] if 'book_link' in params else None
		self.start = params['start'] if 'start' in params else None
		self.end = params['end'] if 'end' in params else None
		self.format = params['format'] if 'format' in params else None
		self.auth = params['auth'] if 'auth' in params else 'none'
		self.images = params['images'] if 'images' in params else True
		self.cover = params['cover'] if 'cover' in params else False
		self._path_name = str(self.chat_id)+'-'+str(self.message_id)+'-'+str(self.index)
		self._files_path = os.path.join( self.bot.config.DOWNLOADER_TEMP_PATH, self._path_name )
		self.log_file = os.path.join( self.bot.config.DOWNLOADER_LOG_PATH, self._path_name+'.log' )
		self.reply_markup = InlineKeyboardMarkup(
			inline_keyboard=[
				[
					InlineKeyboardButton( text='Отмена', callback_data=f'cancel:{self.index}' )
				]
			]
		)

	async def start(self):
		self.status = STATUS_RUNNING
		# sts = await self.get_status()
		# await self.bot.message_queue.enqueue( 'edit_message_text', chat_id=self.chat_id, message_id=self.message_id, text=self.last_message, reply_markup=self.reply_markup )
		asyncio.create_task( self._download() )
		# _failure = await self._download()

		# if self.result_files['cover']:
		# 	await self.bot.message_queue.enqueue( 'send_photo', chat_id=self.chat_id, **self.result_files['cover'] )

		# if len(self.result_files['files']) > 0:
		# 	# for _file in self.result_files['files']:
		# 	# 	await self.bot.message_queue.enqueue( 'send_document', chat_id=self.chat_id, **_file )
		# 	if len(self.result_files['files']) > 1:
		# 		for media_group in self._chunks_list(self.result_files['files'],10):
		# 			media = []
		# 			for m in media_group:
		# 				print('m')
		# 				print(m)
		# 				print()
		# 				if 'document' in m and 'media' not in m:
		# 					m['media'] = m['document']
		# 				del m['document']
		# 				media.append(m)
		# 			await self.bot.message_queue.enqueue( 'send_media_group', chat_id=self.chat_id, media=media )
		# 	else:
		# 		await self.bot.message_queue.enqueue( 'send_document', chat_id=self.chat_id, **self.result_files['files'][0] )

		# for _message in _failure:
		# 	await self.bot.message_queue.enqueue( 'send_document', chat_id=self.chat_id, **_message )

		# proc = await asyncio.create_subprocess_shell(f'rm -rf "{self.log_file}"')
		# await proc.wait()
		# self.status = STATUS_DONE

	async def cancel(self):
		self.status = STATUS_CANCELLED
		# await self.bot.message_queue.enqueue( 'edit_message_text', chat_id=self.chat_id, message_id=self.message_id, text='Загрузка отменена', reply_markup=None )
		if self.process:
			await self.process.kill()
		if self.log_file:
			try:
				proc = await asyncio.create_subprocess_shell(f'rm -rf "{self.log_file}"')
				await proc.wait()
			except Exception as e:
				pass

	async def get_status(self):
		if self.status == STATUS_INIT:
			msg = self.book_link+'\nЗагрузка начата'
			if msg and msg != self.last_message:
				self.last_message = msg
				return {'text':self.last_message,'reply_markup':self.reply_markup}
			return None
		if self.status == STATUS_RUNNING:
			msg = await self.get_last_line()
			if msg:
				self.book_link+'\n'+msg
				if msg != self.last_message:
					self.last_message = msg
					return {'text':self.last_message,'reply_markup':self.reply_markup}
			return None
		if self.status == STATUS_PROCESSING:
			msg = self.book_link+'\nОбработка файлов'
			if msg and msg != self.last_message:
				self.last_message = msg
				reply_markup = InlineKeyboardMarkup(
					inline_keyboard=[
						[
							InlineKeyboardButton( text='Нельзя отменить', callback_data=f'cancel:0' )
						]
					]
				)
				return {'text':self.last_message,'reply_markup':reply_markup}
			return None
		if self.status == STATUS_CANCELLED:
			msg = self.book_link+'\nУдаление файлов'
			if msg and msg != self.last_message:
				self.last_message = msg
				reply_markup = InlineKeyboardMarkup(
					inline_keyboard=[
						[
							InlineKeyboardButton( text='Нельзя отменить', callback_data=f'cancel:0' )
						]
					]
				)
				return {'text':self.last_message,'reply_markup':reply_markup}
			return None
		if self.status == STATUS_DONE:
			msg = self.book_link+'\nЗагрузка завершена'
			if msg and msg != self.last_message:
				self.last_message = msg
				return {'text':self.last_message,'reply_markup':None}
			return None

	async def get_last_line(self):
		last_line = ''
		if not os.path.exists(self.log_file):
			return ''
		with open(self.log_file, 'r') as f:
			for line in f:
				pass
			last_line = line
		return last_line

	async def get_last_line_seek(self):
		list_of_lines = []
		if not os.path.exists(self.log_file):
			return ''
		with open(self.log_file, 'rb') as read_obj:
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

	def _chunks_list(self, lst, n):
		for i in range(0, len(lst), n):
			yield lst[i:i + n]

	async def _prepare_command(self):
		command = f'cd {self.bot.config.DOWNLOADER_PATH}; dotnet Elib2Ebook.dll --save "{self._files_path}"'

		if self.book_link:
			command += f' --url "{self.book_link}"'

		if self.format:
			command += f' --format "{self.format},json"'

		if self.start:
			command += f' --start "{self.start}"'

		if self.end:
			command += f' --end "{self.end}"'

		if self.site in self.bot.config.PROXY_LIST:
			_p = self.bot.config.PROXY_LIST[site]
			command += f' --proxy "{_p}" -t 120'
		else:
			command += f' --timeout 30'

		if self.cover:
			command += ' --cover'

		if not self.images:
			command += ' --no-image'

		if self.auth:
			login = None
			password = None
			if self.auth == 'self':
				try:
					_auth = await self.bot.db.get_user_auth(self.user_id,self.site)
					if _auth:
						login = _auth.login
						password = _auth.password
				except Exception as e:
					pass

			if self.auth == 'anon':
				try:
					if self.site in self.bot.config.DEMO_USER:
						login = self.bot.config.DEMO_USER[self.site]['login']
						password = self.bot.config.DEMO_USER[self.site]['password']
				except Exception as e:
					pass

			if login and password:
				if not login.startswith('/') and not login.startswith('http:') and not login.startswith('https:') and not password.startswith('/') and not password.startswith('http:') and not password.startswith('https:'):
					command += f' --login="{login}" --password="{password}"'

		command += f' > {self.log_file}'

		return command

	async def _process_error_text(self,message,command=None,e=None):
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

	async def _process_caption(self, _json_file):
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
			await self._process_error_text('Произошла ошибка чтения json',e=e)

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

	async def _maybe_split_file(self, file):
		fsize = os.path.getsize(file)
		_return = []

		if fsize > self.bot.config.DOWNLOADS_SPLIT_LIMIT:
			_tmp_name, extension = os.path.splitext(file)
			_tmp_name = _tmp_name.split(self._files_path)[1][1:]

			splitted_folder = os.path.join(self._files_path, 'splitted')
			os.makedirs(splitted_folder,exist_ok=True)

			splitted_file = os.path.join(splitted_folder, f'{_tmp_name}.zip')

			sfs = int(self.bot.config.DOWNLOADS_SPLIT_LIMIT / 1024 / 1024)
			sfs = f'{sfs}m'
			cmd = f'cd {self._files_path}; zip -s {sfs} "{splitted_file}" "{file}"'

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

	async def _get_result_files(self):
		_json = None
		cover = None
		file = None
		_trash = []
		
		t = os.listdir(self._files_path)
		for x in t:
			_tmp_name, extension = os.path.splitext(x)
			extension = extension[1:]
			if extension == 'json':
				_json = os.path.join(self._files_path, x)
			elif extension == self.format:
				file = os.path.join(self._files_path, x)
			elif extension in ['jpg','jpeg','png','gif']:
				cover = os.path.join(self._files_path, x)
			else:
				_trash.append(os.path.join(self._files_path, x))
	async def _download(self):

		command = await self._prepare_command()

		_failure = []

		download_result = {
			'stdout': b'',
			'stderr': b'',
		}

		try:
			proc = await asyncio.create_subprocess_shell(command)
			await proc.wait()

			if self.status != STATUS_CANCELLED:

				self.status = STATUS_PROCESSING


				

				if not _json:
					raise Exception('Nothind found')

				file_caption = await self._process_caption(_json)

				if cover:
					if os.path.exists(cover):
						self.result_files['cover'] = {'photo':cover}
				if file:
					if os.path.exists(file):
						files = await self._maybe_split_file(file)
						print('files')
						print(files)
						print()
						for _file in files:
							self.result_files['files'].append( {'document':_file, 'caption':file_caption, 'parse_mode':'MarkdownV2'} )
					else:
						message = await self._process_error_text('Произошла ошибка чтения файла',command=command)
						self.result_files['files'].append( {'document':self.log_file, 'caption':message} )
				else:
					message = await self._process_error_text('Произошла ошибка, скачивание не удалось',command=command)
					self.result_files['files'].append( {'document':self.log_file, 'caption':message} )
					if cover:
						_trash.append(cover)
					if file:
						_trash.append(file)

			else: # if self.status != STATUS_CANCELLED:
				t = os.listdir(self._files_path)
				for x in t:
					_trash.append(os.path.join(self._files_path, x))

		except Exception as e:
			message = await self._process_error_text('Произошла ошибка',command=command,e=e)
			self.result_files['files'].append( {'document':self.log_file, 'caption':message} )

		for _file in _trash:
			proc = await asyncio.create_subprocess_shell(f'rm -rf "{_file}"')
			await proc.wait()