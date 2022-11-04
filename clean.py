import os, logging, datetime, subprocess

logging.basicConfig(
    filename='clean.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s',
    level=logging.INFO
)
logger=logging.getLogger(__name__)

BASE_PATH = os.path.dirname(__file__)
DOWNLOADER_PATH = os.path.join(BASE_PATH, "downloader")
STORE_PATH = os.path.join(DOWNLOADER_PATH, 'temp')
LITRES_PATH = os.path.join(DOWNLOADER_PATH, 'LitresCache')

def clear_temp_folder():
    del_time = datetime.datetime.now() - datetime.timedelta(minutes=180)

    logger.warning(f'Очистка директории скачивания {del_time}')

    del_time = del_time.timestamp()

    folders = os.listdir(STORE_PATH)
    for folder in folders:
        _f = os.path.join(STORE_PATH, folder)
        if os.path.isdir(_f):
            stats = os.stat(_f)
            if stats.st_mtime < del_time:
                logger.warning(f'Удаляем папку {folder}')
                q = subprocess.run(["rm", "-rf", _f])
    return


def clear_litres_folder():
    del_time = datetime.datetime.now() - datetime.timedelta(minutes=60)

    logger.warning(f'Очистка директории токенов Litres {del_time}')

    del_time = del_time.timestamp()

    tokens = os.listdir(LITRES_PATH)
    for token in tokens:
        _t = os.path.join(LITRES_PATH, token)
        stats = os.stat(_t)
        if stats.st_mtime < del_time:
            logger.warning(f'Удаляем токен {token}')
            q = subprocess.run(["rm", "-f", _t])
    return

clear_temp_folder()
clear_litres_folder()