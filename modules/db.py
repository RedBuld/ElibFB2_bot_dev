import time, asyncio, orjson
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import delete
# from aiomysql.sa import create_engine
# from aiogram.fsm.state import State, StatesGroup

Base = declarative_base()

DOWNLOAD_STATUS_CANCELLED = 99
DOWNLOAD_STATUS_WAIT = 1
DOWNLOAD_STATUS_INIT = 2
DOWNLOAD_STATUS_RUNNING = 3
DOWNLOAD_STATUS_PROCESSING = 4
DOWNLOAD_STATUS_DONE = 5

class UserAuth(Base):
	__tablename__ = 'users_auth'
	id = sa.Column(sa.BigInteger, primary_key=True)
	user = sa.Column(sa.BigInteger, nullable=False, index=True)
	site = sa.Column(sa.String(240), nullable=False, index=True)
	login = sa.Column(sa.Text, nullable=True)
	password = sa.Column(sa.Text, nullable=True)
	created_on = sa.Column(sa.DateTime(), default=datetime.now)
	updated_on = sa.Column(sa.DateTime(), default=datetime.now, onupdate=datetime.now)

class MessagesQuery(Base):
	__tablename__ = 'messages_query'
	id = sa.Column('id', sa.BigInteger, primary_key=True)
	bot_id = sa.Column('bot', sa.Integer, index=True)
	#
	callee = sa.Column('callee', sa.Text, default=None)
	args = sa.Column('args', sa.JSON, default=None)
	kwargs = sa.Column('kwargs', sa.JSON, default=None)

	def __repr__(self):
		return str({
			'id': self.id,
			'bot_id': self.bot_id,
			'callee': self.callee,
			'args': self.args,
			'kwargs': self.kwargs,
		})

class DownloadsQuery(Base):
	__tablename__ = 'downloads_query'
	id = sa.Column('id', sa.BigInteger, primary_key=True)
	#
	bot_id = sa.Column('bot', sa.Integer, index=True)
	user_id = sa.Column('user', sa.BigInteger, index=True)
	chat_id = sa.Column('chat', sa.Text, default=None)
	message_id = sa.Column('message', sa.Text, default=None)
	#
	site = sa.Column('site', sa.String(240), nullable=False, index=True)
	book_link = sa.Column('book_link', sa.Text, nullable=False)
	start = sa.Column('start', sa.Integer, default=None)
	end = sa.Column('end', sa.Integer, default=None)
	format = sa.Column('format', sa.Text)
	auth = sa.Column('auth', sa.Text, default='none')
	images = sa.Column('images', sa.Integer, default=0)
	cover = sa.Column('cover', sa.Integer, default=0)
	status = sa.Column('status', sa.Integer, default=DOWNLOAD_STATUS_WAIT)
	result = sa.Column('result', sa.JSON, default=None)
	#
	pid = sa.Column('pid', sa.Text, default=None)
	last_message = sa.Column('last_message', sa.Text)


	def __repr__(self):
		return str({
			'id': self.id,
			'bot_id': self.bot_id,
			'chat_id': self.chat_id,
			'message_id': self.message_id,
			'user_id': self.user_id,
			'site': self.site,
			'book_link': self.book_link,
			'start': self.start,
			'end': self.end,
			'format': self.format,
			'auth': self.auth,
			'images': self.images,
			'cover': self.cover,
			'status': self.status,
			'pid': self.pid,
			'last_message': self.last_message,
			'result': self.result,
		})

class SiteStat(Base):
	__tablename__ = 'sites_stats'
	id = sa.Column(sa.BigInteger, primary_key=True)
	site = sa.Column(sa.String(100), nullable=False)
	day = sa.Column(sa.Date(), default=datetime.now)
	count = sa.Column(sa.Integer)

class SQLAlchemy(object):
	bot = None
	engine = None
	session = None

	def __init__(self, bot):
		self.bot = bot
		self.bot.db = self
		self.init()

	def init(self):
		host = self.bot.config.DB_HOST
		user = self.bot.config.DB_USER
		password = self.bot.config.DB_PASSWORD
		database = self.bot.config.DB_DATABASE
		socket = self.bot.config.DB_SOCKET
		mysql_url = f"mysql+aiomysql://{user}:{password}@{host}/{database}"
		if socket:
			mysql_url = f"{mysql_url}?unix_socket={socket}"
		try:
			self.engine = create_async_engine(mysql_url)
			self.session = AsyncSession(self.engine, expire_on_commit=False)
		except (KeyboardInterrupt, SystemExit):
			pass

	async def stop(self):
		if self.session:
			await self.session.close()
		if self.engine:
			await self.engine.dispose()

	async def reinit(self):
		await self.stop()
		self.init()

	async def create_db(self):
		async with self.engine.begin() as conn:
			await conn.run_sync(Base.metadata.drop_all)
			await conn.run_sync(Base.metadata.create_all)

	async def get_user_auth(self, uid, site):
		res = None
		async with self.session as session:
			res = await session.execute(
				select(UserAuth)\
					.filter(UserAuth.site==site,UserAuth.user==uid)\
					.order_by(UserAuth.id).limit(1)
			)
			res = res.scalars().first()
			if res:
				res = res[0]
		await self.engine.dispose()
		return res

	# MESSAGES

	async def get_messages_tasks(self):
		res = None
		async with self.session as session:
			res = await session.execute(
				select(MessagesQuery.id)\
					.filter(MessagesQuery.bot_id==self.bot.config.BOT_ID)\
					.order_by(sa.asc(MessagesQuery.id))
			)
			res = res.scalars().all()
		await self.engine.dispose()
		return res

	async def get_messages_task(self,id):
		res = None
		async with self.session as session:
			res = await session.execute(
				select(MessagesQuery)\
					.filter(MessagesQuery.id==id)
			)
			res = res.scalars().first()
		await self.engine.dispose()
		return res

	async def add_messages_task(self,callee=None,args=None,kwargs=None):

		mq = MessagesQuery()
		mq.bot_id = self.bot.config.BOT_ID
		mq.callee = callee
		mq.args = args
		mq.kwargs = kwargs

		self.session.add(mq)

		await self.session.commit()
		await self.engine.dispose()
		return mq.id

	async def remove_messages_task(self,id):

		mq = await self.get_messages_task(id)
		if mq:
			await self.session.delete(mq)

		await self.session.commit()
		await self.engine.dispose()
		return mq

	# TASKS

	async def get_download_tasks(self):
		res = None
		async with self.session as session:
			res = await session.execute(
				select(DownloadsQuery)\
					.filter(DownloadsQuery.bot_id==self.bot.config.BOT_ID)\
					.order_by(sa.desc(DownloadsQuery.status),sa.asc(DownloadsQuery.id))
			)
			res = res.scalars().all()
		await self.engine.dispose()
		return res

	async def get_download_task(self,id):
		res = None
		async with self.session as session:
			res = await session.execute(
				select(DownloadsQuery)\
					.filter(DownloadsQuery.id==id)
			)
			res = res.scalars().first()
		await self.engine.dispose()
		return res

	async def add_download_task(self,params):

		dq = DownloadsQuery()
		dq.bot_id = self.bot.config.BOT_ID
		dq.status = DOWNLOAD_STATUS_WAIT
		for arg in params:
			setattr(dq, arg, params.get(arg,None))

		self.session.add(dq)

		await self.session.commit()
		await self.engine.dispose()
		return dq.id

	async def update_download_task(self,download_id,params):
		dq = await self.get_download_task(download_id)
		if dq:
			for arg in params:
				setattr(dq, arg, params.get(arg,None))

			await self.session.commit()
			await self.engine.dispose()
		return dq

	async def remove_download_task(self,id):

		dq = await self.get_download_task(id)
		if dq:
			await self.session.delete(dq)

		await self.session.commit()
		await self.engine.dispose()
		return dq

	# async def set_download_task_message(self,download_id,message_id):
	# 	dq = await self.get_download_task(download_id)
	# 	if dq:
	# 		dq.message_id = message_id
	# 		self.session.add(dq)

	# 	await self.session.commit()
	# 	await self.engine.dispose()
	# 	return dq