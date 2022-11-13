# ElibFB2 bot

Исходники телеграм-бота для создания бота качающего книги с множества сайтов.

Имеет очередь сообщений, очередь загрузок, сатистику, восстановление очередей после перезапуска.

Поддерживает множественные авторизации для сайтов.

Работает в комплекте с https://github.com/OnlyFart/Elib2Ebook



## .env


```bash
# CORE
DB_URL - обязательно, для хранения данных между перезапусками
REDIS_URL - рекомендуется, для хранения состояний
LOCAL_SERVER - рекомендуется, для адекватной отправки файлов больше 40мб
# CONFIGS
GLOBAL_CONFIG=_global_.json - не обязательно, файл централизованного управения конфигурациями
# STORAGES
LOGS_PATH - рекомендуется, путь для хранения логов
CONFIGS_PATH - обязательно, путь к папке с конфигурациями
DOWNLOADER_PATH - не обязательно, путь к папке с загрузчиком, может быть указан в .json конфигах
CONVERTERS_PATH - не обязательно, путь к папке с конверерами, может быть указан в .json конфигах, либо не указан совсем
# WEB INTERFACES
BOT_URL - не обязательно, web-адрес, если запускать бота в webhook-режиме
DOWNLOAD_URL - не обязательно, web-адрес, интерфейс конфигурации загрузки (требуется для mode 0)
STATS_URL - не обязательно, web-адрес, интерфейс статистики
USAGE_URL - не обязательно, web-адрес, интерфейс нагрузки ботов
AUTH_URL - не обязательно, web-адрес, интерфейс добавления авторизации (требуется для mode 0)
# MISC
FREE_LIMIT=100 - не обязательно, ограничение бесплатных скачиваний в день, по умолчанию 100
```

## config.json

```json
{
	"bot_port": 7080, # порт для WEBHOOK, только в конфиге конкретного бота
	"bot_token": "TOKEN", # API-токен, только в конфиге конкретного бота
	"bot_mode": 0, # режим работы, 0 - с web-окнами, 1 - стандартный
	"start_message": "Привет, я бот для скачивания книг\nКоманды в меню", # сообщение команды start, может быть указано в центральном конфиге
	"domain": "DOMAIN", # домен для WEBHOOK
	"locked": false, # блокировка загрузок для НЕадминов
	"accept": false, # блокировка всех загрузок
	"admins": [ ADMIN_USER_ID ],
	"sites_params": { # параметры сайтов, может быть указано в центральном конфиге
		"DOMAIN": [ARGS], # аргументы paging, images, force_images, auth
		"author.today": ["paging","images","auth"],
		"mangalib.me": ["paging","force_images","auth"],
	},
	"allowed_sites": [ # список используемых ботом сайтов
		"author.today",
		"bigliba.com",
		"bookinbook.ru",
	],
	"proxy_params": { # работа с прокси для конкретных сайтов
		"DOMAIN": "IP:PORT",
	},
	"formats_params": { # доступные форматы, может быть указано в центральном конфиге
		"fb2": "Fb2 - для книг",
		"epub": "Epub - для книг"
	},
	"allowed_formats": [ # список используемых ботом форматов
		"fb2",
		"epub",
		"mobi",
		"azw3"
	],
	"convert_params": { # параметры конвертируемых форматов, пары target_format : source_format
		"mobi": "fb2",
		"azw3": "fb2"
	},
	"builtin_auth": { # встроенные аккаунты для сайтов
		"DOMAIN": {
			"login":"EMAIL",
			"password":"PASSWORD"
		}
	},
	"download": { # конфигурация очереди загрузок, может быть указано в центральном конфиге
		"running": true, # работает ли очередь закачек
		"simultaneously": 10, # число одновременных скачиваний
		"check_interval": 3, # интервал проверки очереди закачек
		"notices_interval": 10, # интервал уведомлений очереди закачек
		"length_limit": 50, # максимальная длина очереди закачек
		"split_limit": 400*1024*1024, # размера файла в байтах, после которого идет разбитие на zip-ы указанного размера
		"free_limit": 100 # не обязательно, ограничение бесплатных скачиваний в день, по умолчанию 100
	}
}
```

## NGINX - в режиме работы через webhook-и

```bash
server {
	listen 80;
	server_name {BOT_URL}; - домен бота из .env/.json

	location = /wh_{BOT_ID} {
		proxy_pass http://127.0.0.1:{BOT_PORT}/wh_{BOT_ID}; - порт из config.json и id бота
		include proxy_params;
	}
}
```


## Support

Поддержка https://t.me/elib_fb2_bot_support

Сказать спасибо https://boosty.to/elib2ebook/about - АВТОР КАЧАЛКИ

Сказать спасибо https://boosty.to/redbuld/about - АВТОР БОТА
