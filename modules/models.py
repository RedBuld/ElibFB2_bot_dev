import sqlalchemy as sa
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class DOWNLOAD_STATUS(object):
	CANCELLED = 99
	ERROR = 98
	WAIT = 1
	INIT = 2
	RUNNING = 3
	PROCESSING = 4
	DONE = 5

class UserAuth(Base):
	__tablename__ = 'users_auth'
	id = sa.Column(sa.BigInteger, primary_key=True)
	user = sa.Column(sa.BigInteger, nullable=False, index=True)
	site = sa.Column(sa.String(240), nullable=False, index=True)
	login = sa.Column(sa.Text, nullable=True)
	password = sa.Column(sa.Text, nullable=True)
	created_on = sa.Column(sa.DateTime(), default=datetime.now)
	updated_on = sa.Column(sa.DateTime(), default=datetime.now, onupdate=datetime.now)

class Message(Base):
	__tablename__ = 'messages_query'
	id = sa.Column('id', sa.BigInteger, primary_key=True)
	bot_id = sa.Column('bot', sa.String(5), index=True)
	#
	callee = sa.Column('callee', sa.Text, default=None)
	args = sa.Column('args', sa.JSON, default=None)
	kwargs = sa.Column('kwargs', sa.JSON, default=None)

	def __repr__(self) -> str:
		return str({
			'id': self.id,
			'bot_id': self.bot_id,
			'callee': self.callee,
			'args': self.args,
			'kwargs': self.kwargs,
		})

class Download(Base):
	__tablename__ = 'downloads_query'
	id = sa.Column('id', sa.BigInteger, primary_key=True)
	#
	bot_id = sa.Column('bot', sa.String(5), index=True)
	user_id = sa.Column('user', sa.BigInteger, index=True)
	chat_id = sa.Column('chat', sa.BigInteger, default=None)
	message_id = sa.Column('message', sa.BigInteger, default=None)
	#
	site = sa.Column('site', sa.String(240), nullable=False, index=True)
	url = sa.Column('url', sa.Text, nullable=False)
	start = sa.Column('start', sa.Integer, default=None)
	end = sa.Column('end', sa.Integer, default=None)
	format = sa.Column('format', sa.Text)
	auth = sa.Column('auth', sa.Text, default='none')
	images = sa.Column('images', sa.Integer, default=0)
	cover = sa.Column('cover', sa.Integer, default=0)
	status = sa.Column('status', sa.Integer, default=DOWNLOAD_STATUS.WAIT)
	result = sa.Column('result', sa.JSON, default=None)
	#
	pid = sa.Column('pid', sa.BigInteger, default=None)
	last_message = sa.Column('last_message', sa.Text)
	mq_message_id = sa.Column('mq_message_id', sa.BigInteger, nullable=True, default=None)


	def __repr__(self) -> str:
		return str({
			'id': self.id,
			'bot_id': self.bot_id,
			'chat_id': self.chat_id,
			'message_id': self.message_id,
			'user_id': self.user_id,
			'site': self.site,
			'url': self.url,
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