import argparse, asyncio, sys, logging
from datetime import datetime
from typing import Union
from pathlib import Path

from aiogram import Bot
from modules.config import Config
from modules.db import DB


parser = argparse.ArgumentParser(prog='bot.py', conflict_handler='resolve')
parser.add_argument('config', type=Path, help='path to config file')
execute_args = parser.parse_args()

if not execute_args.config:
	sys.exit('Not passed `config` path, use -h to get help')

config = Config(config_file=execute_args.config)

logging.basicConfig(
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=logging.INFO
)
logger=logging.getLogger(__name__)

bot = Bot( token=config.API_TOKEN )
bot.config = config
db = DB(bot)

asyncio.run( bot.db.create_db() )