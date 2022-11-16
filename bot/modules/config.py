import os, re, orjson, copy
from pathlib import Path
from typing import Optional, Union, Any
from dotenv import load_dotenv

class __Config__(object):
	__loaded__ = False

	# GLOBAL CONFIG
	__GLOBAL_STORE = {
		# CORE
		'DB_URL'                      : None,
		'REDIS_URL'                   : None,
		'LOCAL_SERVER'                : None,
		# BOT CONFIG
		'BOT_ID'                      : None,
		'BOT_MODE'                    : 0,
		'BOT_TOKEN'                   : None,
		'BOT_URL'                     : None,
		'BOT_PORT'                    : None,
		'BOT_HOOK'                    : None,
		# STORAGES
		'LOGS_PATH'                   : None,
		'DOWNLOADERS_PATH'            : None,
		'DOWNLOADERS_TEMP_PATH'       : None,
		'DOWNLOADERS_LOG_PATH'        : None,
		'CONVERTERS_PATH'             : None,
		# MESSAGES
		'MESSAGES_Q_INTERVAL'         : 1,
		# DOWNLOADS
		'DOWNLOADS_Q_LENGTH_LIMIT'    : 50,
		'DOWNLOADS_Q_SIMULTANEOUSLY'  : 10,
		'DOWNLOADS_Q_RUNNING'         : True,
		'DOWNLOADS_CHECK_INTERVAL'    : 3,
		'DOWNLOADS_NOTICES_INTERVAL'  : 10,
		'DOWNLOADS_SPLIT_LIMIT'       : 1900*1024*1024,
		'DOWNLOADS_FREE_LIMIT'        : 100,
		# WEB INTERFACES
		'DOWNLOAD_URL'                : None,
		'STATS_URL'                   : None,
		'USAGE_URL'                   : None,
		'AUTH_URL'                    : None,
		# CONFIG
		'SITES_PARAMS'                : {},
		'PROXY_PARAMS'                : {},
		'CONVERT_PARAMS'              : {},
		'FORMATS_PARAMS'              : {},
		'BUILTIN_AUTHS'               : {},
		'SITES_LIST'                  : [],
		'REGEX_LIST'                  : [],
		'FORMATS_LIST'                : [],
		# MISC
		'ADMINS'                      : [],
		'START_MESSAGE'               : None,
		'FREE_LIMIT'                  : 100,
		'ACCEPT_NEW'                  : True,
		'LOCKED'                      : False,
	}

	# LOCAL CONFIG
	__LOCAL_STORE = {} # SHADOW COPY OF GLOBAL CONFIG

	# BOT PERSONAL CONFIG
	# BOT_ID    = None
	# BOT_MODE  = 0
	# BOT_PORT  = None
	# BOT_TOKEN = None

	def __init__(self, bot_id: str) -> None:
		super(__Config__, self).__init__()

		self.set('BOT_ID', bot_id)

		self.__load__()
		self.__loaded__ = True

	def __repr__(self) -> str :
		def default(obj):
			if isinstance(obj, re.Pattern):
				return str(obj)
		return orjson.dumps( self.__json__(), option=orjson.OPT_INDENT_2, default=default ).decode()

	def get(self, key: str, default: Optional[Any] = None):
		if key in self.__LOCAL_STORE and self.__LOCAL_STORE[key] != None:
			return self.__LOCAL_STORE[key]
		if key in self.__GLOBAL_STORE and self.__GLOBAL_STORE[key] != None:
			return self.__GLOBAL_STORE[key]
		return default

	def set(self, key: str, value: Optional[Any] = None):
		# prev = self.get(key)
		__immutable__ = [
			'DB_URL',
			'REDIS_URL',
			'LOCAL_SERVER',
			'BOT_ID',
			'BOT_TOKEN',
			'BOT_MODE',
			'BOT_URL',
			'BOT_PORT',
			'BOT_HOOK',
			'LOGS_PATH',
			'CONFIGS_PATH'
		]

		if key in __immutable__ and self.__loaded__:
			raise Exception(f'ERROR: Trying to change immutable during execution variable {key}')

		if key in self.__GLOBAL_STORE:
			self.__LOCAL_STORE[key] = value

		# curr = self.get(key)

	def reload(self):
		self.__load__()

	def __json__(self):
		result = {
			# '__GLOBAL_STORE': self.__GLOBAL_STORE,
			# '__LOCAL_STORE': self.__LOCAL_STORE,
		}
		show_params = [
			'DB_URL',
			'REDIS_URL',
			'LOCAL_SERVER',
			'BOT_ID',
			'BOT_MODE',
			'BOT_TOKEN',
			'LOGS_PATH',
			'DOWNLOADERS_PATH',
			'DOWNLOADERS_TEMP_PATH',
			'DOWNLOADERS_LOG_PATH',
			'CONVERTERS_PATH',
			'MESSAGES_Q_INTERVAL',
			'DOWNLOADS_CHECK_INTERVAL',
			'DOWNLOADS_Q_LENGTH_LIMIT',
			'DOWNLOADS_Q_RUNNING',
			'DOWNLOADS_Q_SIMULTANEOUSLY',
			'DOWNLOADS_NOTICES_INTERVAL',
			'DOWNLOADS_SPLIT_LIMIT',
			'DOWNLOADS_FREE_LIMIT',
			'DOWNLOAD_URL',
			'STATS_URL',
			'USAGE_URL',
			'AUTH_URL',
			'BOT_URL',
			'BOT_PORT',
			'BOT_HOOK',
			'SITES_PARAMS',
			'PROXY_PARAMS',
			'CONVERT_PARAMS',
			'FORMATS_PARAMS',
			'BUILTIN_AUTHS',
			'SITES_LIST',
			'REGEX_LIST',
			'FORMATS_LIST',
			'ADMINS',
			'START_MESSAGE',
			'FREE_LIMIT',
			'ACCEPT_NEW',
			'LOCKED',
		]
		for param in show_params:
			result[param] = self.get(param,None)

		return result

	def __load__(self) -> None:
		self.__load_env__()
		self.__validate_env__()
		self.__load_global_json__()
		self.__load_local_json__()
		self.__validate__()

	def __load_env__(self) -> None:
		load_dotenv()

		# CORE
		if not self.__loaded__: # IMMUTABLE DURING EXECUTION
			self.__GLOBAL_STORE['DB_URL'] = os.getenv('DB_URL','sqlite:///:memory:')
			self.__GLOBAL_STORE['REDIS_URL'] = os.getenv('REDIS_URL',None)
			self.__GLOBAL_STORE['LOCAL_SERVER'] = os.getenv('LOCAL_SERVER',None)
			self.__GLOBAL_STORE['BOT_URL'] = os.getenv('BOT_URL',None)

		# STORAGES
		if not self.__loaded__: # IMMUTABLE DURING EXECUTION
			self.__GLOBAL_STORE['LOGS_PATH'] = os.getenv('LOGS_PATH',None)
			self.__GLOBAL_STORE['CONFIGS_PATH'] = os.getenv('CONFIGS_PATH',None)

		self.__GLOBAL_STORE['DOWNLOADERS_PATH'] = os.getenv('DOWNLOADERS_PATH',None)
		self.__GLOBAL_STORE['CONVERTERS_PATH'] = os.getenv('CONVERTERS_PATH',None)

		# WEB INTERFACES
		self.__GLOBAL_STORE['DOWNLOAD_URL'] = os.getenv('DOWNLOAD_URL',None)
		self.__GLOBAL_STORE['STATS_URL'] = os.getenv('STATS_URL',None)
		self.__GLOBAL_STORE['USAGE_URL'] = os.getenv('USAGE_URL',None)
		self.__GLOBAL_STORE['AUTH_URL'] = os.getenv('AUTH_URL',None)

		# MISC
		self.__GLOBAL_STORE['FREE_LIMIT'] = int(os.getenv('FREE_LIMIT',100))

	def __load_global_json__(self) -> None:
		# print('__load_global_json__')

		config_id = os.getenv('GLOBAL_CONFIG',None)
		config_file = os.path.join( self.get('CONFIGS_PATH'), config_id )
		store = self.__GLOBAL_STORE

		# print()
		# print()
		# print('config_file')
		# print(config_file)
		# print()
		# print()
		# print('self.__GLOBAL_STORE before')
		# print(store)
		# print()
		# print()

		if not os.path.exists(config_file):
			raise Exception(f'Config file "{config_id}" not found, expecting "{config_file}"')

		self.__GLOBAL_STORE = self.__load_json__(store, config_file)

		# print('self.__GLOBAL_STORE after')
		# print(self.__GLOBAL_STORE)
		# print()
		# print()

	def __load_local_json__(self) -> None:
		# print('__load_local_json__')

		bot_id = self.get('BOT_ID')
		config_file = os.path.join( self.get('CONFIGS_PATH'), f'{bot_id}.json' )
		store = self.__LOCAL_STORE

		# print()
		# print()
		# print('config_file')
		# print(config_file)
		# print()
		# print()
		# print('self.__LOCAL_STORE before')
		# print(store)
		# print()
		# print()

		if not os.path.exists(config_file):
			raise Exception(f'Config file "{bot_id}.json" not found, expecting "{config_file}"')

		self.__LOCAL_STORE = self.__load_json__(store, config_file)

		# print('self.__LOCAL_STORE after')
		# print(self.__LOCAL_STORE)
		# print()
		# print()

	def __load_json__(self, store, file) -> None:
		with open(file,'r') as _config_file:
			_config = _config_file.read()
			_config = orjson.loads(_config)

			# CORE
			if not self.__loaded__: # IMMUTABLE DURING EXECUTION

				if 'db_url' in _config and _config['db_url']:
					store['DB_URL'] = _config['db_url']

				if 'redis_url' in _config and _config['redis_url']:
					store['REDIS_URL'] = _config['redis_url']

				if 'local_server' in _config and _config['local_server']:
					store['LOCAL_SERVER'] = _config['local_server']

				if 'bot_token' in _config and _config['bot_token']:
					store['BOT_TOKEN'] = _config['bot_token']

				if 'bot_url' in _config and _config['bot_url']:
					store['BOT_URL'] = _config['bot_url']

				if 'bot_port' in _config and _config['bot_port']:
					store['BOT_PORT'] = _config['bot_port']

				if 'bot_mode' in _config:
					store['BOT_MODE'] = _config['bot_mode']

			# STORAGES
			if not self.__loaded__: # IMMUTABLE DURING EXECUTION

				if 'logs_path' in _config and _config['logs_path']:
					store['LOGS_PATH'] = _config['logs_path']

				if 'configs_path' in _config and _config['configs_path']:
					store['CONFIGS_PATH'] = _config['configs_path']

			if 'downloaders_path' in _config and _config['downloaders_path']:
				store['DOWNLOADERS_PATH'] = _config['downloaders_path']

			if 'converters_path' in _config and _config['converters_path']:
				store['CONVERTERS_PATH'] = _config['converters_path']

			# CONFIGS
			if 'sites_params' in _config and _config['sites_params']:
				store['SITES_PARAMS'] = _config['sites_params']

			if 'proxy_params' in _config and _config['proxy_params']:
				store['PROXY_PARAMS'] = _config['proxy_params']

			if 'convert_params' in _config and _config['convert_params']:
				store['CONVERT_PARAMS'] = _config['convert_params']

			if 'builtin_auth' in _config and _config['builtin_auth']:
				store['BUILTIN_AUTHS'] = _config['builtin_auth']

			if 'formats_params' in _config and _config['formats_params']:
				store['FORMATS_PARAMS'] = _config['formats_params']

			if 'allowed_sites' in _config and _config['allowed_sites']:
				store['SITES_LIST'] = _config['allowed_sites']

			if 'allowed_formats' in _config and _config['allowed_formats']:
				store['FORMATS_LIST'] = _config['allowed_formats']

			# MESSAGES
			if 'messages' in _config and _config['messages']:

				if 'check_interval' in _config['messages']:
					store['MESSAGES_Q_INTERVAL'] = int(_config['messages']['check_interval'])

			# DOWNLOADS
			if 'download' in _config and _config['download']:

				if 'running' in _config['download']:
					store['DOWNLOADS_Q_RUNNING'] = bool(_config['download']['running'])

				if 'simultaneously' in _config['download'] and _config['download']['simultaneously']:
					store['DOWNLOADS_Q_SIMULTANEOUSLY'] = int(_config['download']['simultaneously'])

				if 'check_interval' in _config['download'] and _config['download']['check_interval']:
					store['DOWNLOADS_CHECK_INTERVAL'] = int(_config['download']['check_interval'])

				if 'notices_interval' in _config['download'] and _config['download']['notices_interval']:
					store['DOWNLOADS_NOTICES_INTERVAL'] = int(_config['download']['notices_interval'])

				if 'length_limit' in _config['download'] and _config['download']['length_limit']:
					store['DOWNLOADS_Q_LENGTH_LIMIT'] = int(_config['download']['length_limit'])

				if 'split_limit' in _config['download'] and _config['download']['split_limit']:
					store['DOWNLOADS_SPLIT_LIMIT'] = int(_config['download']['split_limit'])

				if 'free_limit' in _config['download'] and _config['download']['free_limit']:
					store['DOWNLOADS_FREE_LIMIT'] = int(_config['download']['free_limit'])

			# MISC
			if 'start_message' in _config and _config['start_message']:
				store['START_MESSAGE'] = _config['start_message']

			if 'accept' in _config and _config['accept']:
				store['ACCEPT_NEW'] = _config['accept']

			if 'locked' in _config and _config['locked']:
				store['LOCKED'] = _config['locked']

			if 'admins' in _config and _config['admins']:
				store['ADMINS'] = list(_config['admins'])

		return store

	def __validate_env__(self):

		if not self.get('CONFIGS_PATH'):
			raise Exception('CONFIGS_PATH/configs_path not set')

		if not self.get('DOWNLOADERS_PATH'):
			raise Exception('DOWNLOADERS_PATH/downloaders_path not set')

	def __validate__(self):

		# CORE
		if not self.get('BOT_TOKEN'):
			raise Exception('bot_token not set')

		if self.get('BOT_URL'):
			if not self.get('BOT_PORT'):
				raise Exception('bot_port not set')

			bot_id = self.get('BOT_ID')
			self.set('BOT_HOOK', f"/wh_{bot_id}")

		# STORAGES
		self.set( 'DOWNLOADERS_TEMP_PATH', os.path.join( self.get('DOWNLOADERS_PATH'), 'temp' ) )
		self.set( 'DOWNLOADERS_LOG_PATH', os.path.join( self.get('DOWNLOADERS_PATH'), 'logs' ) )

		if not os.path.exists( self.get('DOWNLOADERS_TEMP_PATH') ):
			os.makedirs( self.get('DOWNLOADERS_TEMP_PATH'), 777, exist_ok=True)

		if not os.path.exists( self.get('DOWNLOADERS_LOG_PATH') ):
			os.makedirs( self.get('DOWNLOADERS_LOG_PATH'), 777, exist_ok=True)

		# CONFIG
		if not self.get('SITES_PARAMS'):
			raise Exception('no sites_params provided')

		if not self.get('SITES_LIST'):
			self.set( 'SITES_LIST', list( self.get('SITES_PARAMS').keys() ) )

		if not self.get('SITES_LIST'):
			raise Exception('no sites provided')

		if not self.get('FORMATS_LIST'):
			self.set( 'FORMATS_LIST', list( self.get('FORMATS_PARAMS').keys() ) )

		if not self.get('FORMATS_LIST'):
			raise Exception('no formats provided')

		self.set( 'REGEX_LIST', [ re.compile(f"https?:\/\/(www\.)*(?P<site>{x})\/") for x in self.get('SITES_LIST') ] )

		# DOWNLOADS
		if self.get('LOCAL_SERVER'):
			__max_file_size = 1900*1024*1024 # Telegram API limit for local server is 2GB
			if self.get('DOWNLOADS_SPLIT_LIMIT') > __max_file_size:
				self.set( 'DOWNLOADS_SPLIT_LIMIT', __max_file_size)
		else:
			__max_file_size = 39*1024*1024 # Telegram API limit for non-local server is 40MB
			if self.get('DOWNLOADS_SPLIT_LIMIT') > __max_file_size:
				self.set( 'DOWNLOADS_SPLIT_LIMIT', __max_file_size)

class Config(__Config__):
	pass