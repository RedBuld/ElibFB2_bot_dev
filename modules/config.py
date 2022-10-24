import os, re, orjson
from pathlib import Path
from typing import Optional, Union

class Config(object):
	ACCEPT_NEW                 = True
	BOT_ID                     = None
	API_TOKEN                  = None
	DOWNLOADER_PATH            = None
	DOWNLOADER_TEMP_PATH       = None
	DOWNLOADER_LOG_PATH        = None
	LOCAL_SERVER               = None
	DB_TYPE                    = 'mysql'
	DB_HOST                    = None
	DB_USER                    = None
	DB_PASSWORD                = None
	DB_DATABASE                = None
	DB_SOCKET                  = None
	REDIS_CONFIG               = None
	MESSAGES_SEND_INTERVAL     = 2
	DOWNLOADS_Q_LIMIT          = 20
	DOWNLOADS_SIMULTANEOUSLY   = 5
	DOWNLOADS_CHECK_INTERVAL   = 5
	DOWNLOADS_NOTICES_INTERVAL = 10
	DOWNLOADS_SPLIT_LIMIT      = 400*1024*1024
	SITES_LIST                 = []
	SITES_DATA                 = []
	REGEX_LIST                 = []
	PROXY_LIST                 = {}
	FORMATS                    = {}
	DEMO_USER                  = {}
	WEBHOOK                    = None
	WEBHOOK_PATH               = '/wh'

	def __json__(self):
		return {
			'ACCEPT_NEW': self.ACCEPT_NEW,
			'API_TOKEN': self.API_TOKEN,
			'DOWNLOADER_PATH': self.DOWNLOADER_PATH,
			'DOWNLOADER_TEMP_PATH': self.DOWNLOADER_TEMP_PATH,
			'DOWNLOADER_LOG_PATH': self.DOWNLOADER_LOG_PATH,
			'LOCAL_SERVER': self.LOCAL_SERVER,
			'DB_TYPE': self.DB_TYPE,
			'DB_HOST': self.DB_HOST,
			'DB_USER': self.DB_USER,
			'DB_PASSWORD': self.DB_PASSWORD,
			'DB_DATABASE': self.DB_DATABASE,
			'DB_SOCKET': self.DB_SOCKET,
			'REDIS_HOST': self.REDIS_HOST,
			'REDIS_PORT': self.REDIS_PORT,
			'REDIS_DB': self.REDIS_DB,
			'MESSAGES_SEND_INTERVAL': self.MESSAGES_SEND_INTERVAL,
			'DOWNLOADS_SIMULTANEOUSLY': self.DOWNLOADS_SIMULTANEOUSLY,
			'DOWNLOADS_CHECK_INTERVAL': self.DOWNLOADS_CHECK_INTERVAL,
			'DOWNLOADS_NOTICES_INTERVAL': self.DOWNLOADS_NOTICES_INTERVAL,
			'SITES_LIST': self.SITES_LIST,
			'SITES_DATA': self.SITES_DATA,
			'REGEX_LIST': self.REGEX_LIST,
			'PROXY_LIST': self.PROXY_LIST,
			'FORMATS': self.FORMATS,
			'DEMO_USER': self.DEMO_USER,
			'WEBHOOK': self.WEBHOOK,
		}

	def __repr__(self) -> str :
		return str(self.__json__())

	def __init__(self) -> None :
		config_file = os.path.join(os.path.dirname('..'), "config.json")
		if not os.path.exists(config_file):
			raise Exception('No config.json found')

		if config_file:
			self.__load__(config_file)


	def __load__(self, config_file: Optional[Union[str, Path]]=None) -> None :
		if not config_file:
			config_file = os.path.join(os.path.dirname('..'), "config.json")
			if not os.path.exists(config_file):
				raise Exception('No config.json found')
		if os.path.exists(config_file):
			with open(config_file,'r') as _c:
				_config = _c.read()
				_config = orjson.loads(_config)

				if 'bot_id' in _config and _config['bot_id']:
					self.BOT_ID = _config['bot_id']

				if 'token' in _config and _config['token']:
					self.API_TOKEN = _config['token']

				if 'server' in _config and _config['server']:
					self.LOCAL_SERVER = _config['server']

				if 'accept' in _config:
					self.ACCEPT_NEW = _config['accept']

				if 'downloader' in _config:
					self.DOWNLOADER_PATH = os.path.abspath(_config['downloader'])
				else:
					self.DOWNLOADER_PATH = os.path.abspath(os.path.join(os.path.dirname('../..'),'downloader'))
				self.DOWNLOADER_TEMP_PATH = os.path.join(self.DOWNLOADER_PATH,'temp')
				self.DOWNLOADER_LOG_PATH = os.path.join(self.DOWNLOADER_PATH,'logs')

				if 'sites' in _config:
					self.SITES_DATA = _config['sites']
					self.SITES_LIST = list(self.SITES_DATA.keys())
					self.REGEX_LIST = [ re.compile(f"https?:\/\/(www\.)*(?P<site>{x})\/") for x in self.SITES_LIST ]

				if 'formats' in _config:
					self.FORMATS = _config['formats']

				if 'proxied' in _config and _config['proxied']:
					self.PROXY_LIST = _config['proxied']

				if 'download' in _config and _config['download']:
					if 'limit' in _config['download']:
						self.DOWNLOAD_LIMIT = _config['download']['limit']
					if 'delay' in _config['download']:
						self.DOWNLOAD_DELAY = _config['download']['delay']

				if 'db' in _config and _config['db']:
					if 'type' in _config['db']:
						self.DB_TYPE = _config['db']['type']
					if 'host' in _config['db']:
						self.DB_HOST = _config['db']['host']
					if 'user' in _config['db']:
						self.DB_USER = _config['db']['user']
					if 'password' in _config['db']:
						self.DB_PASSWORD = _config['db']['password']
					if 'db' in _config['db']:
						self.DB_DATABASE = _config['db']['db']
					if 'socket' in _config['db']:
						self.DB_SOCKET = _config['db']['socket']

				if 'redis' in _config and _config['redis']:
					self.REDIS_CONFIG = _config['redis']

				if 'demo' in _config and _config['demo']:
					self.DEMO_USER = _config['demo']

				if 'domain' in _config and _config['domain']:
					self.WEBHOOK = _config['domain']