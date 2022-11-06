import os, re, orjson
from pathlib import Path
from typing import Optional, Union
from dotenv import load_dotenv

class Config(object):
	__first__ = True
	__config_file = None
	ACCEPT_NEW                 = True
	LOCKED                     = False
	ADMINS                     = [470328529]
	BOT_ID                     = None
	BOT_MODE                   = 0
	BOT_PORT                   = None
	API_TOKEN                  = None
	DB_URL                     = None
	REDIS_URL                  = None
	LOGS_PATH                  = None
	LOCAL_SERVER               = None
	DOWNLOADER_PATH            = None
	DOWNLOADER_TEMP_PATH       = None
	DOWNLOADER_LOG_PATH        = None
	MESSAGES_Q_INTERVAL        = 1
	DOWNLOADS_Q_INTERVAL       = 3
	DOWNLOADS_Q_LIMIT          = 50
	DOWNLOADS_SIMULTANEOUSLY   = 10
	DOWNLOADS_NOTICES_INTERVAL = 10
	DOWNLOADS_SPLIT_LIMIT      = 400*1024*1024
	DOWNLOADS_FREE_LIMIT       = None
	START_MESSAGE              = None
	SITES_LIST                 = []
	SITES_DATA                 = []
	REGEX_LIST                 = []
	PROXY_LIST                 = {}
	FORMATS                    = {}
	DEMO_USER                  = {}
	DOWNLOAD_URL               = None
	STATS_URL                  = None
	WEBHOOK                    = None
	WEBHOOK_PATH               = None

	def __json__(self):
		return {
			'BOT_ID': self.BOT_ID,
			'BOT_MODE': self.BOT_MODE,
			'API_TOKEN': self.API_TOKEN,
			'REDIS_URL': self.REDIS_URL,
			'LOGS_PATH': self.LOGS_PATH,
			'LOCAL_SERVER': self.LOCAL_SERVER,
			'DOWNLOADER_PATH': self.DOWNLOADER_PATH,
			'DOWNLOADER_TEMP_PATH': self.DOWNLOADER_TEMP_PATH,
			'DOWNLOADER_LOG_PATH': self.DOWNLOADER_LOG_PATH,
			'DOWNLOAD_URL': self.DOWNLOAD_URL,
			'STATS_URL': self.STATS_URL,
			'ACCEPT_NEW': self.ACCEPT_NEW,
			'MESSAGES_Q_INTERVAL': self.MESSAGES_Q_INTERVAL,
			'DB_URL': self.DB_URL,
			'DOWNLOADS_Q_LIMIT': self.DOWNLOADS_Q_LIMIT,
			'DOWNLOADS_Q_INTERVAL': self.DOWNLOADS_Q_INTERVAL,
			'DOWNLOADS_SIMULTANEOUSLY': self.DOWNLOADS_SIMULTANEOUSLY,
			'DOWNLOADS_NOTICES_INTERVAL': self.DOWNLOADS_NOTICES_INTERVAL,
			'DOWNLOADS_FREE_LIMIT': self.DOWNLOADS_FREE_LIMIT,
			'START_MESSAGE': self.START_MESSAGE,
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

	def __init__(self, config_file: Optional[Union[str, Path]]=None) -> None:
		if not config_file or not os.path.exists(config_file):
			raise Exception('Config file not found')

		self.__config_file = config_file

		self.__load__()


	def __load__(self) -> None:
		load_dotenv()
		if self.__first__:
			self.REDIS_URL = os.getenv('REDIS_URL',None)
			self.LOGS_PATH = os.getenv('LOGS_PATH',None)
			self.LOCAL_SERVER = os.getenv('LOCAL_SERVER',None)

		self.DB_URL = os.getenv('DB_URL','sqlite:///:memory:')
		self.DOWNLOADER_PATH = os.getenv('DOWNLOADER_PATH',None)
		if not self.DOWNLOADER_PATH:
			raise Exception('env DOWNLOADER_PATH not set')
		self.DOWNLOADER_TEMP_PATH = os.path.join(self.DOWNLOADER_PATH,'temp')
		self.DOWNLOADER_LOG_PATH = os.path.join(self.DOWNLOADER_PATH,'logs')

		self.DOWNLOAD_URL = os.getenv('DOWNLOAD_URL',None)
		if not self.DOWNLOAD_URL:
			raise Exception('env DOWNLOAD_URL not set')

		self.STATS_URL = os.getenv('STATS_URL',None)
		if not self.DOWNLOAD_URL:
			raise Exception('env STATS_URL not set')

		if not os.path.exists(self.DOWNLOADER_TEMP_PATH):
			os.makedirs(self.DOWNLOADER_TEMP_PATH, 777, exist_ok=True)
		if not os.path.exists(self.DOWNLOADER_LOG_PATH):
			os.makedirs(self.DOWNLOADER_LOG_PATH, 777, exist_ok=True)

		if os.path.exists(self.__config_file):
			with open(self.__config_file,'r') as _c:
				_config = _c.read()
				_config = orjson.loads(_config)

				if self.__first__: # IMMUTABLE DURING EXECUTION
					if 'bot_id' in _config and _config['bot_id']:
						self.BOT_ID = _config['bot_id']

					if 'port' in _config and _config['port']:
						self.BOT_PORT = _config['port']

					if 'token' in _config and _config['token']:
						self.API_TOKEN = _config['token']

					if 'domain' in _config and _config['domain']:
						self.WEBHOOK = _config['domain']
						self.WEBHOOK_PATH = f'/wh_{self.BOT_ID}'

				if not self.BOT_ID:
					raise Exception('`bot_id` not set')

				if not self.BOT_PORT:
					raise Exception('`port` not set')

				if not self.WEBHOOK:
					raise Exception('`domain` not set')

				if 'accept' in _config:
					self.ACCEPT_NEW = _config['accept']

				if 'mode' in _config:
					self.BOT_MODE = _config['mode']

				if 'start_message' in _config:
					self.START_MESSAGE = _config['start_message']

				if 'locked' in _config:
					self.LOCKED = _config['locked']

				if 'admins' in _config:
					self.ADMINS = list(_config['admins'])

				if 'sites' in _config:
					self.SITES_DATA = _config['sites']
					self.SITES_LIST = list(self.SITES_DATA.keys())
					self.REGEX_LIST = [ re.compile(f"https?:\/\/(www\.)*(?P<site>{x})\/") for x in self.SITES_LIST ]

				if 'formats' in _config:
					self.FORMATS = _config['formats']

				if 'proxied' in _config and _config['proxied']:
					self.PROXY_LIST = _config['proxied']

				if 'download' in _config and _config['download']:
					if 'free' in _config['download']:
						self.DOWNLOADS_FREE_LIMIT = _config['download']['free']
					if 'limit' in _config['download']:
						self.DOWNLOADS_Q_LIMIT = _config['download']['limit']
					if 'check_interval' in _config['download']:
						self.DOWNLOADS_Q_INTERVAL = _config['download']['check_interval']
					if 'notices_interval' in _config['download']:
						self.DOWNLOADS_NOTICES_INTERVAL = _config['download']['notices_interval']
					if 'simultaneously' in _config['download']:
						self.DOWNLOADS_SIMULTANEOUSLY = _config['download']['simultaneously']
					if 'split_limit' in _config['download']:
						try:
							self.DOWNLOADS_SPLIT_LIMIT = int(_config['download']['split_limit'])
							if self.DOWNLOADS_SPLIT_LIMIT > 400*1024*1024:
								self.DOWNLOADS_SPLIT_LIMIT = 400*1024*1024
						except Exception as e:
							self.DOWNLOADS_SPLIT_LIMIT = 400*1024*1024

				if 'demo' in _config and _config['demo']:
					self.DEMO_USER = _config['demo']

		self.__first__ = False