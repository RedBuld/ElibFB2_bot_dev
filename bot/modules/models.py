import sqlalchemy as sa
from datetime import datetime, date
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class AuthForm(StatesGroup):
	site = State()
	web = State()
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

class BookDirectoryNotExist(Exception):
	pass

class BookNotDownloaded(Exception):
	pass

class Links(Base):
	__tablename__ = 'plain_links'
	__table_args__  = ( sa.Index('plain_links', 'link', mysql_length=191, unique=True), )
	id = sa.Column(sa.BigInteger, primary_key=True)
	link = sa.Column(sa.Text, nullable=False)

class ACL(Base):
	__tablename__ = 'access_list'
	__table_args__ = ( sa.UniqueConstraint("user", "premium", name="user_premium_index"), sa.UniqueConstraint("user", "banned", name="user_banned_index") )
	id = sa.Column(sa.BigInteger, primary_key=True)
	user = sa.Column(sa.BigInteger, nullable=False, index=True)
	premium = sa.Column(sa.Boolean)
	banned = sa.Column(sa.Boolean)
	reason = sa.Column(sa.Text)
	until = sa.Column(sa.DateTime(), default=datetime.now)

class UserAuth(Base):
	__tablename__ = 'users_auth'
	id = sa.Column(sa.BigInteger, primary_key=True)
	user = sa.Column(sa.BigInteger, nullable=False, index=True)
	site = sa.Column(sa.String(240), nullable=False, index=True)
	login = sa.Column(sa.Text, nullable=True)
	password = sa.Column(sa.Text, nullable=True)
	created_on = sa.Column(sa.DateTime(), default=datetime.now)

	def __repr__(self) -> str:
		return '<UserAuth '+str({
			'id': self.id,
			'user': self.user,
			'site': self.site,
			'login': self.login,
			'password': self.password,
			'created_on': self.created_on
		})+'>'

	def get_name(self):
		_r = self.login
		if self.created_on:
			_r = _r+' [от '+str(self.created_on.strftime('%d.%m.%Y'))+']'
		return _r

class User(Base):
	__tablename__ = 'users'
	user = sa.Column(sa.BigInteger, primary_key=True)
	username = sa.Column(sa.Text)
	fullname = sa.Column(sa.Text)

class UserSetting(Base):
	__tablename__ = 'users_settings'
	__table_args__ = ( sa.UniqueConstraint("user", "key", name="user_key_index"), )
	id = sa.Column(sa.BigInteger, primary_key=True)
	user = sa.Column(sa.BigInteger, nullable=False, index=True)
	key = sa.Column(sa.String(100))
	value = sa.Column(sa.Text)


class UserUsage(Base):
	__tablename__ = 'users_usage'
	__table_args__ = ( sa.UniqueConstraint("user", "day", name="user_day_index"), )
	id = sa.Column(sa.BigInteger, primary_key=True)
	user = sa.Column(sa.BigInteger, nullable=False, index=True)
	day = sa.Column(sa.Date(), default=date.today)
	count = sa.Column(sa.Integer, default=1)


class UserUsageExtended(Base):
	__tablename__ = 'users_usage_extended'
	__table_args__ = ( sa.UniqueConstraint("user", "day", "site", name="user_day_site_index"), )
	id = sa.Column(sa.BigInteger, primary_key=True)
	user = sa.Column(sa.BigInteger, nullable=False, index=True)
	day = sa.Column(sa.Date(), default=date.today)
	site = sa.Column(sa.String(240), nullable=False, index=True)
	count = sa.Column(sa.Integer, default=1)
	last_on = sa.Column(sa.DateTime(), default=datetime.now, onupdate=datetime.now)


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
	created_on = sa.Column(sa.DateTime(), default=datetime.now)
	updated_on = sa.Column(sa.DateTime(), default=datetime.now, onupdate=datetime.now)
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
	target_format = sa.Column(sa.Text)
	auth = sa.Column(sa.Text, default='none')
	images = sa.Column(sa.String(1), default=0)
	cover = sa.Column(sa.String(1), default=0)
	status = sa.Column(sa.Integer, default=DOWNLOAD_STATUS.WAIT)
	result = sa.Column(sa.JSON, default=None)
	proxy = sa.Column(sa.Text, nullable=True)
	#
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
			'target_format': self.target_format,
			'auth': self.auth,
			'images': self.images,
			'cover': self.cover,
			'status': self.status,
			'last_message': self.last_message,
			'result': self.result,
		})+'>'

class SiteStat(Base):
	__tablename__ = 'sites_stats'
	__table_args__ = ( sa.UniqueConstraint("site", "bot_id", "day", name="site_day_index"), )
	id = sa.Column(sa.BigInteger, primary_key=True)
	bot_id = sa.Column(sa.String(5), index=True)
	site = sa.Column(sa.String(100), nullable=False)
	day = sa.Column(sa.Date(), default=date.today)
	count = sa.Column(sa.Integer, default=1)
	fsize = sa.Column(sa.BigInteger, default=0)

class BotStat(Base):
	__tablename__ = 'bots_stats'
	id = sa.Column(sa.BigInteger, primary_key=True)
	bot_id = sa.Column(sa.String(5), index=True, unique=True)
	queue_length = sa.Column(sa.Text, nullable=True)
	queue_limit = sa.Column(sa.Text, nullable=True)
	queue_act = sa.Column(sa.Text, nullable=True)
	queue_sim = sa.Column(sa.Text, nullable=True)
	last_on = sa.Column(sa.DateTime(), default=datetime.now, onupdate=datetime.now)