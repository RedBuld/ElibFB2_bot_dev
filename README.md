# ElibFB2 bot

Исходники телеграм-бота для создания бота качающего книги с множества сайтов.

Имеет очередь сообщений, очередь загрузок, сатистику, восстановление очередей после перезапуска.

Поддерживает множественные авторизации для сайтов.




## .env


```bash
DB_URL - рекомендуется, для хранения данных между перезапусками
REDIS_URL - рекомендуется, для хранения данных между перезапусками
LOGS_PATH - рекомендуется, для хранения логов в файле
DOWNLOADER_PATH - обязательно, или бот ищет загрузчик на уровне напки bot
DOWNLOAD_URL - обязательно, домен который отвечает за web/download
STATS_URL - обязательно, домен которы отвечает за web/stats
LOCAL_SERVER - рекомендуется, для отправки больших файлов
```

## config.json

```bash
{
	"bot_id": "b1", - внутренний id бота
	"port": 7080, - порт для WEBHOOK
	"start_message": "Привет, я бот для скачивания книг\nКоманды в меню", - сообщение команды start
	"token": "TOKEN",
	"domain": "DOMAIN", - домен для WEBHOOK
	"locked": false, - блокировка загрузок для НЕадминов
	"admins": [ ADMIN_USER_ID ],
	"sites": {
		"DOMAIN": [ARGS], - аргументы paging, images, force_images, auth
        "author.today": ["paging","images","auth"],
        "mangalib.me": ["paging","force_images","auth"],
	},
	"proxied": {
		"DOMAIN": "IP:PORT",
	},
	"formats": {
		"fb2": "Fb2 - для книг",
		"epub": "Epub - для книг"
	},
	"demo": {
		"DOMAIN": {
			"login":"EMAIL",
			"password":"PASSWORD"
		}
	}
}
```

## NGINX

```bash
server {
	listen 80;
	server_name `domain`; - домен бота из config.json

	location = /wh_b1 {
		proxy_pass http://127.0.0.1:7080/wh_b1; - порт из config.json и id бота из config.json
		include proxy_params;
	}
}
```