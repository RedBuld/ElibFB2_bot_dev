import asyncio, time
import sqlalchemy as sa
from typing import Optional
# from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
# from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.future import select
from aiomysql.sa import create_engine
from sqlalchemy import delete
from aiogram import Bot
from modules.models import *

class DB(object):
	bot = None
	engine = None

	def __init__(self, bot:Bot) -> None:
		self.bot = bot
		self.bot.db = self

	async def __map__(self, rows, map, _class):
		r = []
		map = list(map)
		if type(rows) == list:
			for row in rows:
				c = _class()
				for arg in map:
					setattr(c, arg, row[map.index(arg)])
				r.append(c)
		else:
			c = _class()
			for arg in map:
				setattr(c, arg, rows[map.index(arg)])
			r = c
		return r


	async def init(self, _sync=False) -> None:
		host = self.bot.config.DB_HOST
		user = self.bot.config.DB_USER
		password = self.bot.config.DB_PASSWORD
		database = self.bot.config.DB_DATABASE
		socket = self.bot.config.DB_SOCKET

		try:
			c = "mysql+aiomysql" if self.bot.config.DB_TYPE == 'mysql' else "postgresql+asyncpg"

			db_url = f"{c}://{user}:{password}@{host}/{database}"
			if socket:
				db_url = f"{db_url}?unix_socket={socket}"
			self.engine = create_async_engine(db_url, pool_size=1, max_overflow=50)
			# self.engine = await create_engine(
			# 	user=user,
			# 	db=database,
			# 	host=host,
			# 	password=password,
			# 	minsize=1,
			# 	maxsize=50
			# )
		except Exception as e:
			raise e

	async def stop(self) -> None:
		if self.engine:
			# self.engine.terminate()
			# await self.engine.wait_closed()
			await self.engine.dispose()

	async def reinit(self) -> None:
		await self.stop()
		await self.init()

	async def create_db(self) -> None:
		try:
			await self.init()
			async with self.engine.begin() as conn:
				await conn.run_sync(Base.metadata.drop_all)
				await conn.run_sync(Base.metadata.create_all)
				await conn.commit()
			await self.stop()
		except Exception as e:
			raise e

	async def get_user_auth(self, uid:int, site:str) -> Optional[UserAuth]:
		res = None
		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(UserAuth)\
					.filter(UserAuth.site==site,UserAuth.user==uid)\
					.order_by(UserAuth.id).limit(1)
			)
			res = query.fetchone()
			if res:
				keys = query.keys()
				res = await self.__map__(res,keys,UserAuth)
		return res

	# DEVELOPMENT
	# async with conn.begin() as transaction:
	# code
	# await conn.commit()
	async def test(self):
		res = None
		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(Download)\
					.filter(Download.bot_id==self.bot.config.BOT_ID)\
					.order_by(sa.desc(Download.status),sa.asc(Download.id))
			)
			res = query.fetchall()
			if res:
				keys = query.keys()
				res = await self.__map__(res,keys,Download)
		return res

	# MESSAGES

	async def get_all_messages(self) -> Optional[list]:
		res = None
		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(Message.id)\
					.filter(Message.bot_id==self.bot.config.BOT_ID)\
					.order_by(sa.asc(Message.id))
			)
			res = query.scalars()

		return res

	async def get_message(self, message_id: int) -> Optional[Message]:
		res = None
		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(Message)\
					.filter(Message.id==message_id)
			)
			res = query.fetchone()
			if res:
				keys = query.keys()
				res = await self.__map__(res,keys,Message)
		return res


	async def add_message(self, params: dict) -> Optional[int]:
		res = None
		params['bot_id'] = self.bot.config.BOT_ID
		async with self.engine.begin() as conn:
			# async with conn.begin() as transaction:
			res = await conn.execute(Message.__table__.insert().values(**params))
			await conn.commit()
		return res.lastrowid if res else None

	async def update_message(self, message_id: int, params: dict) -> Optional[Download]:
		res = None
		async with self.engine.begin() as conn:
			# async with conn.begin() as transaction:
			res = await conn.execute(Message.__table__.update().where(Message.id==message_id).values(**params))
			await conn.commit()
		return await self.get_message(message_id)

	async def remove_message(self, message_id: int) -> Optional[Message]:
		res = await self.get_message(message_id)
		async with self.engine.begin() as conn:
			# async with conn.begin() as transaction:
			await conn.execute(Message.__table__.delete().where(Message.id==message_id))
			await conn.commit()
		return res

	# TASKS

	async def get_all_downloads(self) -> Optional[list]:
		res = None
		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(Download)\
					.filter(Download.bot_id==self.bot.config.BOT_ID)\
					.order_by(sa.desc(Download.status),sa.asc(Download.id))
			)
			res = query.fetchall()
			if res:
				keys = query.keys()
				res = await self.__map__(res,keys,Download)
		return res

	async def get_download(self, download_id: int) -> Optional[Download]:
		res = None
		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(Download)\
					.filter(Download.id==download_id)
			)
			res = query.fetchone()
			if res:
				keys = query.keys()
				res = await self.__map__(res,keys,Download)
		return res

	async def add_download(self, params: dict) -> Optional[int]:
		res = None
		params['bot_id'] = self.bot.config.BOT_ID
		async with self.engine.begin() as conn:
			# async with conn.begin() as transaction:
			res = await conn.execute(Download.__table__.insert().values(**params))
			await conn.commit()
		return res.lastrowid if res else None

	async def update_download(self, download_id: int, params: dict) -> Optional[Download]:
		res = None
		async with self.engine.begin() as conn:
			# async with conn.begin() as transaction:
			res = await conn.execute(Download.__table__.update().where(Download.id==download_id).values(**params))
			await conn.commit()
		return await self.get_download(download_id)

	async def remove_download(self, download_id: int) -> Optional[Download]:
		res = await self.get_download(download_id)
		async with self.engine.begin() as conn:
			# async with conn.begin() as transaction:
			await conn.execute(Download.__table__.delete().where(Download.id==download_id))
			await conn.commit()
		return res

	# async def set_downloads_task_message(self,download_id,message_id):
	# 	D = await self.get_download(download_id)
	# 	if D:
	# 		D.message_id = message_id
	# 		self.session.add(D)

	# 	await self.session.commit()
	# 	return D