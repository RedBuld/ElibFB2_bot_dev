import sqlalchemy as sa
from datetime import datetime, date
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class AuthForm(StatesGroup):
	site = State()
	login = State()
	password = State()

class DownloadConfig(StatesGroup):
	state = State()


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
	created_on = sa.Column(sa.DateTime(), default=datetime.now())
	updated_on = sa.Column(sa.DateTime(), default=datetime.now(), onupdate=datetime.now())

	def __repr__(self) -> str:
		return '<UserAuth '+str({
			'id': self.id,
			'user': self.user,
			'site': self.site,
			'login': self.login,
			'password': self.password,
			'created_on': self.created_on,
			'updated_on': self.updated_on,
		})+'>'

	def get_name(self):
		_r = self.login
		if self.updated_on:
			_r = _r+' [от '+str(self.updated_on.strftime('%d.%m.%Y'))+']'
		return _r

class Message(Base):
	__tablename__ = 'messages_query'
	id = sa.Column(sa.BigInteger, primary_key=True)
	bot_id = sa.Column(sa.String(5), index=True)
	#
	callee = sa.Column(sa.Text, default=None)
	args = sa.Column(sa.JSON, default=None)
	kwargs = sa.Column(sa.JSON, default=None)

	def __repr__(self) -> str:
		return '<Message '+str({
			'id': self.id,
			'bot_id': self.bot_id,
			'callee': self.callee,
			'args': self.args,
			'kwargs': self.kwargs,
		})+'>'

class Download(Base):
	__tablename__ = 'downloads_query'
	id = sa.Column(sa.BigInteger, primary_key=True)
	#
	bot_id = sa.Column(sa.String(5), index=True)
	user_id = sa.Column(sa.BigInteger, index=True)
	chat_id = sa.Column(sa.BigInteger, default=None)
	message_id = sa.Column(sa.BigInteger, default=None)
	#
	site = sa.Column(sa.String(240), nullable=False, index=True)
	url = sa.Column(sa.Text, nullable=False)
	start = sa.Column(sa.Text, nullable=True, default=None)
	end = sa.Column(sa.Text, nullable=True, default=None)
	format = sa.Column(sa.Text)
	auth = sa.Column(sa.Text, default='none')
	images = sa.Column(sa.String(1), default=0)
	cover = sa.Column(sa.String(1), default=0)
	status = sa.Column(sa.Integer, default=DOWNLOAD_STATUS.WAIT)
	result = sa.Column(sa.JSON, default=None)
	#
	pid = sa.Column(sa.BigInteger, default=None)
	last_message = sa.Column(sa.Text)
	mq_message_id = sa.Column(sa.BigInteger, nullable=True, default=None)


	def __repr__(self) -> str:
		return '<Download '+str({
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
		})+'>'

class SiteStat(Base):
	__tablename__ = 'sites_stats'
	__table_args__ = ( sa.UniqueConstraint("site", "bot_id", "day", name="site_day_index"), )
	id = sa.Column(sa.BigInteger, primary_key=True)
	bot_id = sa.Column(sa.String(5), index=True)
	site = sa.Column(sa.String(100), nullable=False)
	day = sa.Column(sa.Date(), default=date.today())
	count = sa.Column(sa.Integer, default=1)


class BotStat(Base):
	__tablename__ = 'bot_stats'
	__table_args__ = ( sa.UniqueConstraint("bot_id", name="bot_index"), )
	id = sa.Column(sa.BigInteger, primary_key=True)
	bot_id = sa.Column(sa.String(5), index=True)
	queue_length = sa.Column(sa.Text)
	total_length = sa.Column(sa.Text)