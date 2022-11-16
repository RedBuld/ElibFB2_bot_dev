import argparse, asyncio, os, re

parser = argparse.ArgumentParser(prog='bot.py', conflict_handler='resolve')
parser.add_argument('--url', dest="url", type=str, help='Обязательное. Ссылка на книгу')
parser.add_argument('--format', dest="format", type=str, help='Обязательное. Формат для сохранения книги. Допустимые значения: epub, fb2, cbz, json')
parser.add_argument('--save', dest="save", type=str, help='Директория для сохранения данных')
parser.add_argument('--start', dest="start", type=int, help='Стартовый номер главы')
parser.add_argument('--end', dest="end", type=int, help='Конечный номер главы')
parser.add_argument('--proxy', dest="proxy", type=str, help='Прокси в формате host:port')
parser.add_argument('--timeout', dest="timeout", type=int, default=60, help='Timeout для запросов в секундах')
parser.add_argument('--cover', dest="cover", const=True, default=False, action='store_const', help='Сохранить обложку книги в отдельный файл')
parser.add_argument('--no-image', dest="no_image", const=True, default=False, action='store_const', help='Не загружать картинки')
parser.add_argument('--login', dest="login", type=str, help='Логин от сайта')
parser.add_argument('--password', dest="password", type=str, help='Пароль от сайта')
execute_args = parser.parse_args()

_process = None

_Elib2Ebook_sites = ['acomics.ru','author.today','bigliba.com','bookinbook.ru','bookinist.pw','booknet.com','booknet.ua','bookstab.ru','bookriver.ru','dark-novels.ru','dreame.com','eznovels.com','fb2.top','ficbook.net','fictionbook.ru','hentailib.me','hogwartsnet.ru','hotnovelpub.com','hub-book.com','ifreedom.su','jaomix.ru','ladylib.top','lanovels.com','libbox.ru','libst.ru','lightnoveldaily.com','litexit.ru','litgorod.ru','litmarket.ru','litmir.me','litnet.com','litres.ru','manga.ovh','mangalib.me','mybook.ru','online-knigi.com.ua','noveltranslate.com','novelxo.com','prodaman.ru','ranobe-novels.ru','ranobehub.org','ranobelib.me','ranobe.ovh','ranobes.com','readli.net','readmanga.live','remanga.org','renovels.org','ru.novelxo.com','samlib.ru','topliba.com','tl.rulate.ru','twilightrussia.ru','wattpad.com','wuxiaworld.ru','xn--80ac9aeh6f.xn--p1ai']

async def __Elib2Ebook__prepare_command(args) -> str:
	_cwd = os.path.join(
		os.path.dirname(
			os.path.abspath(__file__)
		),
		'_Elib2Ebook'
	)

	_exec = 'dotnet'

	command = []

	command.append('Elib2Ebook.dll')
	if 'save' in args and args['save']:
		command.append('--save')
		command.append(f"{args['save']}")

	if 'url' in args and args['url']:
		command.append('--url')
		command.append(f"{args['url']}")

	if 'format' in args:
		command.append('--format')
		command.append(f"{args['format']},json")

	if 'start' in args and args['start']:
		command.append('--start')
		command.append(f"{args['start']}")

	if 'end' in args and args['end']:
		command.append('--end')
		command.append(f"{args['end']}")

	if 'proxy' in args and args['proxy']:
		command.append('--proxy')
		command.append(f"{args['proxy']}")
		command.append('--timeout')
		command.append('120')
	else:
		command.append('--timeout')
		command.append('60')

	if 'cover' in args and args['cover']:
		command.append('--cover')

	if 'no_image' in args and args['no_image']:
		command.append('--no-image')

	if 'login' in args and 'password' in args:
		if args['login'] and args['password']:
			command.append('--login')
			command.append(f"{args['login']}")
			command.append('--password')
			command.append(f"{args['password']}")

	return _exec, command, _cwd

async def download(args: dict) -> None:

	global _process

	_exec = None
	command = None
	_cwd = None

	site = re.match(r"https?:\/\/(www\.)*(?P<site>[^\/]*)\/",execute_args.url)
	site = site.group('site')

	if site in _Elib2Ebook_sites:
		_exec, command, _cwd = await __Elib2Ebook__prepare_command(args)

	if _exec and command and _cwd:
		_process = await asyncio.create_subprocess_exec(_exec, *command, cwd=_cwd)
		await _process.wait()

		# print()
		# print('_success')
		# print(_success.decode())
		# print()
		# print('_error')
		# print(_error.decode())
		# print()


if __name__ == '__main__':
	if execute_args.url and execute_args.format:
		try:
			asyncio.run( download( vars(execute_args) ) )
		except (KeyboardInterrupt, SystemExit):
			if _process:
				try:
					_process.kill()
				except Exception as e:
					pass
		except Exception as e:
			raise e
		# asyncio.run( download( vars(execute_args) ) )