import argparse, asyncio, sys, logging
from datetime import datetime
from typing import Union
from pathlib import Path

from aiogram import Bot
from modules.config import Config
from modules.db import DB


parser = argparse.ArgumentParser(prog='create_db.py', conflict_handler='resolve')
parser.add_argument('bot_id', type=str, help='bot_id to load config')
execute_args = parser.parse_args()

if not execute_args.bot_id:
	sys.exit('Not passed `bot_id`, use -h to get help')

config = Config(bot_id=execute_args.bot_id)

logging.basicConfig(
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=logging.INFO
)
logger=logging.getLogger(__name__)

bot = Bot( token=config.get('BOT_TOKEN') )
bot.config = config
db = DB(bot)

asyncio.run( bot.db.create_db() )