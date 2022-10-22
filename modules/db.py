import sqlalchemy as sa
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import delete
from aiogram import Bot
from modules.models import *

class DB(object):
	bot = None
	engine = None
	session = None

	def __init__(self, bot:Bot) -> None:
		self.bot = bot
		self.bot.db = self

	async def init(self) -> None:
		host = self.bot.config.DB_HOST
		user = self.bot.config.DB_USER
		password = self.bot.config.DB_PASSWORD
		database = self.bot.config.DB_DATABASE
		socket = self.bot.config.DB_SOCKET
		db_url = f"postgresql+asyncpg://{user}:{password}@{host}/{database}"
		if socket:
			db_url = f"{db_url}?unix_socket={socket}"
		try:
			self.engine = create_async_engine(db_url, pool_size=50, max_overflow=10)
			self.session = AsyncSession(self.engine, expire_on_commit=False)
		except (KeyboardInterrupt, SystemExit):
			pass

	async def stop(self) -> None:
		if self.session:
			await self.session.close()
		if self.engine:
			await self.engine.dispose()

	async def reinit(self) -> None:
		await self.stop()
		await self.init()

	async def create_db(self) -> None:
		await self.bot.db.init()
		async with self.engine.begin() as conn:
			await conn.run_sync(Base.metadata.drop_all)
			await conn.run_sync(Base.metadata.create_all)

	async def get_user_auth(self, uid:int, site:str) -> Optional[UserAuth]:
		res = await self.session.execute(
			select(UserAuth)\
				.filter(UserAuth.site==site,UserAuth.user==uid)\
				.order_by(UserAuth.id).limit(1)
		)
		res = res.scalars().first()
		if res:
			res = res[0]

		# await self.engine.dispose()
		return res

	# MESSAGES

	async def get_all_messages(self) -> Optional[list]:
		L = None
		L = await self.session.execute(
			select(Message.id)\
				.filter(Message.bot_id==self.bot.config.BOT_ID)\
				.order_by(sa.asc(Message.id))
		)
		L = L.scalars().all()

		# await self.engine.dispose()
		return L

	async def get_message(self, message_id: int) -> Optional[Message]:
		M = await self.session.execute(
			select(Message)\
				.filter(Message.id==message_id)
		)
		M = M.scalars().first()

		# await self.engine.dispose()
		return M

	async def add_message(self, params: dict) -> Optional[int]:
		M = Message()
		M.bot_id = self.bot.config.BOT_ID
		for arg in params:
			setattr(M, arg, params.get(arg,None))

		self.session.add(M)

		await self.session.commit()
		# await self.engine.dispose()
		return M.id

	async def update_message(self, message_id: int, params: dict) -> Optional[Download]:
		M = await self.get_message(message_id)
		if M:
			for arg in params:
				setattr(M, arg, params.get(arg,None))
			self.session.add(M)
		else:
			return await self.add_message(params)

		await self.session.commit()
		# await self.engine.dispose()
		return M

	async def remove_message(self, message_id: int) -> Optional[Message]:
		M = await self.get_message(message_id)
		if M:
			await self.session.delete(M)

		await self.session.commit()
		# await self.engine.dispose()
		return M

	# TASKS

	async def get_all_downloads(self) -> Optional[list]:
		L = await self.session.execute(
			select(Download)\
				.filter(Download.bot_id==self.bot.config.BOT_ID)\
				.order_by(sa.desc(Download.status),sa.asc(Download.id))
		)
		L = L.scalars().all()
		# await self.engine.dispose()
		return L

	async def get_download(self, download_id: int) -> Optional[Download]:
		D = await self.session.execute(
			select(Download)\
				.filter(Download.id==download_id)
		)
		D = D.scalars().first()

		# await self.engine.dispose()
		return D

	async def add_download(self, params: dict) -> Optional[int]:
		D = Download()
		D.bot_id = self.bot.config.BOT_ID
		for arg in params:
			setattr(D, arg, params.get(arg,None))

		self.session.add(D)

		await self.session.commit()
		# await self.engine.dispose()
		return D.id

	async def update_download(self, download_id: int, params: dict) -> Optional[Download]:
		D = await self.get_download(download_id)
		if D:
			for arg in params:
				setattr(D, arg, params.get(arg,None))
			self.session.add(D)

		await self.session.commit()
		# await self.engine.dispose()
		return D

	async def remove_download(self, download_id: int) -> Optional[Download]:
		D = await self.get_download(download_id)
		if D:
			await self.session.delete(D)

		await self.session.commit()
		# await self.engine.dispose()
		return D

	# async def set_downloads_task_message(self,download_id,message_id):
	# 	D = await self.get_download(download_id)
	# 	if D:
	# 		D.message_id = message_id
	# 		self.session.add(D)

	# 	await self.session.commit()
	# 	# await self.engine.dispose()
	# 	return D