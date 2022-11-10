import calendar, asyncio, time, logging
import sqlalchemy as sa
from datetime import datetime, date
from typing import Optional, Union, Any
from sqlalchemy import delete
from sqlalchemy.sql import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine.result import RMKeyView
from sqlalchemy.dialects.mysql import insert
from aiogram import Bot
from .models import *

logger = logging.getLogger(__name__)

class DB(object):
	bot = None
	engine = None

	def __init__(self, bot: Union[Bot, Any]) -> None:
		self.bot = bot
		self.bot.db = self

	async def __map_one__(self, data: Union[dict, tuple], keys: Union[RMKeyView, dict, list], _class: Base) -> object:
		c = _class()
		k = list(c.__table__.columns.keys())
		data = list(data)
		keys = list(keys)
		for arg in keys:
			if arg in k:
				setattr(c, arg, data[keys.index(arg)])
		return c

	async def __map__(self, data: Union[dict, list, tuple], keys: Union[RMKeyView, dict, list], _class: Base) -> list:
		r = []
		keys = list(keys)
		if type(data) == list:
			for el in data:
				c = await self.__map_one__(el,keys,_class)
				r.append(c)
		else:
			r = await self.__map_one__(data,keys,_class)
		return r

	async def __to_object__(self, obj: Base) -> dict:
		_res = {}
		for column in obj.__table__.columns:
			val = getattr(obj, column.name, None)
			if not val and column.default is not None:
				val = column.default.arg
				if callable(val):
					val = val(obj)
			if column.onupdate is not None:
				val = column.onupdate.arg
				if callable(val):
					val = val(obj)
			_res[column.name] = val
		return _res

	async def __filter__(self, data: dict, _class: object) -> dict:
		_res = {}
		keys = list(data.keys())
		for column in _class.__table__.columns:
			if column.name in keys:
				_res[column.name] = data[column.name]
		return _res


	async def init(self, _sync=False) -> None:
		try:
			self.engine = create_async_engine(self.bot.config.DB_URL, pool_size=1, max_overflow=50)
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
				await conn.run_sync(Base.metadata.create_all,checkfirst=True)
				await conn.commit()
			await self.stop()
		except Exception as e:
			raise e

	async def plural(self, n: int, words: list):
		if n % 10 == 1 and n % 100 != 11:
			p = 0
		elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
			p = 1
		else:
			p = 2
		return str(n) + ' ' + words[p]


	# SERVICE


	async def maybe_add_link(self, link: str) -> int:
		res = None

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(Links.id)\
					.filter(Links.link==link)
			)
			res = query.scalar()
			if not res:
				l = Links()
				l.link = link
				params = await self.__to_object__(l)

				res = await conn.execute(insert(Links.__table__).values(**params))
				await conn.commit()
				if res:
					res = res.lastrowid

		return res


	async def get_link(self, link_id: int) -> str:
		res = None

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(Links.link)\
					.filter(Links.id==link_id)
			)
			res = query.scalar()

		return res



	# USER SETTINGS

	async def add_user_setting(self, user_id: int, key: str, value: str) -> Optional[int]:
		res = None

		us = UserSetting()
		us.user=user_id
		us.key=key
		us.value=value
		params = await self.__to_object__(us)

		async with self.engine.begin() as conn:
			res = await conn.execute(insert(UserSetting.__table__).values(**params).on_duplicate_key_update(value=value))
			await conn.commit()
		return res.lastrowid if res else None

	async def get_user_setting(self, user_id: int, key: str) -> Optional[UserSetting]:
		res = None

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(UserSetting)\
					.filter(UserSetting.user==user_id,UserSetting.key==key)
			)
			res = query.fetchone()
			if res:
				keys = query.keys()
				res = await self.__map_one__(res,keys,UserSetting)
		return res

	async def check_user_limit(self, user_id: int) -> bool:
		if self.bot.config.DOWNLOADS_FREE_LIMIT:
			used = await self.get_user_usage(user_id)
			if used >= self.bot.config.DOWNLOADS_FREE_LIMIT:
				premium = await self.check_user_premium(user_id)
				if not premium:
					return False
		return True

	async def check_user_banned(self, user_id: int) -> Union[bool,ACL]:
		res = False

		day = datetime.now()

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(ACL)\
					.filter(ACL.user==user_id,ACL.banned==1)
			)
			res = query.fetchone()
			if res:
				keys = query.keys()
				res = await self.__map_one__(res,keys,ACL)
				if res.until < day:
					# await self.delete_user_premium(user_id)
					res = False
			else:
				res = False
		return res

	async def check_user_premium(self, user_id: int) -> bool:
		res = False

		day = datetime.now()

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(ACL)\
					.filter(ACL.user==user_id,ACL.premium==1)
			)
			res = query.fetchone()
			if res:
				keys = query.keys()
				res = await self.__map_one__(res,keys,ACL)
				if res.until < day:
					await self.delete_user_premium(user_id)
					res = False
				else:
					res = True
			else:
				res = False
		return res

	async def delete_user_premium(self, user_id: int) -> None:
		async with self.engine.begin() as conn:
			await conn.execute(ACL.__table__.delete().where(ACL.user==user_id,ACL.premium==1))
			await conn.commit()
		return

	async def update_user_usage_extended(self, user_id: int, site: str) -> Optional[int]:
		res = None

		uue = UserUsageExtended()
		uue.user=user_id
		uue.site=site
		params = await self.__to_object__(uue)

		async with self.engine.begin() as conn:
			res = await conn.execute(insert(UserUsageExtended.__table__).values(**params).on_duplicate_key_update(count=sa.text("count+1"),last_on=params['last_on']))
			await conn.commit()

		await self.update_user_usage(user_id)

		return res.lastrowid if res else None

	# async def reduce_user_usage_extended(self, user_id: int, site: str) -> Optional[int]:
	# 	res = None

	# 	uue = UserUsage()
	# 	uue.user=user_id
	# 	uue.site=site
	# 	params = await self.__to_object__(uue)

	# 	async with self.engine.begin() as conn:
	# 		res = await conn.execute(insert(UserUsage.__table__).values(**params).on_duplicate_key_update(count=sa.text("count-1"),last_on=uu.last_on))
	# 		await conn.commit()

	# 	await self.reduce_user_usage(user_id)

	# 	return res.lastrowid if res else None

	async def update_user_usage(self, user_id: int) -> Optional[int]:
		res = None

		uu = UserUsage()
		uu.user=user_id
		uu.count=1
		params = await self.__to_object__(uu)

		async with self.engine.begin() as conn:
			res = await conn.execute(insert(UserUsage.__table__).values(**params).on_duplicate_key_update(count=sa.text("count+1")))
			await conn.commit()
		return res.lastrowid if res else None

	# async def reduce_user_usage(self, user_id: int) -> Optional[int]:
	# 	res = None

	# 	uu = UserUsage()
	# 	uu.user=user_id
	# 	uu.count=1
	# 	params = await self.__to_object__(uu)

	# 	async with self.engine.begin() as conn:
	# 		res = await conn.execute(insert(UserUsage.__table__).values(**params).on_duplicate_key_update(count=sa.text("count-1")))
	# 		await conn.commit()
	# 	return res.lastrowid if res else None

	async def get_user_usage(self, user_id: int) -> Optional[int]:
		res = None

		day = date.today()

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(UserUsage.count)\
					.filter(UserUsage.day==str(day),UserUsage.user==user_id)
			)
			res = query.scalar()
		if not res:
			res = 0
		else:
			res = int(res)
		return res


	# STATISTICS


	async def update_bot_stat(self, queue_length: int, queue_act: int, queue_limit: int, queue_sim: int) -> bool:
		res = None

		bs = BotStat()
		bs.queue_length = queue_length
		bs.queue_limit = queue_limit
		bs.queue_sim = queue_sim
		bs.queue_act = queue_act
		bs.bot_id = self.bot.config.BOT_ID
		params = await self.__to_object__(bs)

		async with self.engine.begin() as conn:
			res = await conn.execute(insert(BotStat.__table__).values(**params).on_duplicate_key_update(queue_length=params['queue_length'],queue_limit=params['queue_limit'],queue_sim=params['queue_sim'],queue_act=params['queue_act'],last_on=params['last_on']))
			await conn.commit()
		return res.lastrowid if res else None

	async def add_site_stat(self, site: str, size: int) -> Optional[int]:
		res = None

		ss = SiteStat()
		ss.site = site
		ss.bot_id = self.bot.config.BOT_ID
		params = await self.__to_object__(ss)

		async with self.engine.begin() as conn:
			res = await conn.execute(insert(SiteStat.__table__).values(**params).on_duplicate_key_update(count=sa.text("count+1"),fsize=sa.text(f"fsize+{size}")))
			await conn.commit()
		return res.lastrowid if res else None

	# AUTHS


	async def get_all_authed_sites(self, user_id: int) -> Optional[list]:
		res = None

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(sa.distinct(UserAuth.site))\
					.filter(UserAuth.user==user_id)\
					.order_by(sa.asc(UserAuth.site))
			)
			res = query.scalars().fetchall()
		return res

	async def get_all_site_auths(self, user_id: int, site: str) -> Optional[list]:
		res = None

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(UserAuth)\
					.filter(UserAuth.user==user_id,UserAuth.site==site)\
					.order_by(sa.asc(UserAuth.id))
			)
			res = query.fetchall()
			if res:
				keys = query.keys()
				res = await self.__map__(res,keys,UserAuth)
		return res

	async def get_site_auth(self, auth_id: int) -> Optional[UserAuth]:
		res = None

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(UserAuth)\
					.filter(UserAuth.id==auth_id)
			)
			res = query.fetchone()
			if res:
				keys = query.keys()
				res = await self.__map_one__(res,keys,UserAuth)
		return res

	async def add_site_auth(self, params: dict) -> Optional[int]:
		res = None
		params = await self.__map_one__(params.values(),params.keys(),UserAuth)
		params = await self.__to_object__(params)

		async with self.engine.begin() as conn:
			res = await conn.execute(UserAuth.__table__.insert().values(**params))
			await conn.commit()
		return res.lastrowid if res else None

	async def update_site_auth(self, user_id: int, params: dict) -> Optional[Download]:
		res = None
		params = await self.__filter__(params, Message)

		async with self.engine.begin() as conn:
			res = await conn.execute(Message.__table__.update().where(Message.id==user_id).values(**params))
			await conn.commit()
		return await self.get_message(user_id)

	async def remove_site_auth(self, auth_id: int) -> Optional[UserAuth]:
		res = await self.get_message(auth_id)

		async with self.engine.begin() as conn:
			await conn.execute(UserAuth.__table__.delete().where(UserAuth.id==auth_id))
			await conn.commit()
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
				res = await self.__map_one__(res,keys,Message)
		return res

	async def add_message(self, params: dict) -> Optional[int]:
		res = None
		params = await self.__map_one__(params.values(),params.keys(),Message)
		params = await self.__to_object__(params)
		params['bot_id'] = self.bot.config.BOT_ID

		async with self.engine.begin() as conn:
			res = await conn.execute(Message.__table__.insert().values(**params))
			await conn.commit()
		return res.lastrowid if res else None

	async def update_message(self, message_id: int, params: dict) -> Optional[Download]:
		res = None
		params = await self.__filter__(params, Message)

		async with self.engine.begin() as conn:
			res = await conn.execute(Message.__table__.update().where(Message.id==message_id).values(**params))
			await conn.commit()
		return await self.get_message(message_id)

	async def remove_message(self, message_id: int) -> Optional[Message]:
		res = await self.get_message(message_id)

		async with self.engine.begin() as conn:
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
				res = await self.__map_one__(res,keys,Download)
		return res

	async def add_download(self, params: dict) -> Optional[int]:
		res = None
		params = await self.__map_one__(params.values(),params.keys(),Download)
		params = await self.__to_object__(params)
		params['bot_id'] = self.bot.config.BOT_ID

		async with self.engine.begin() as conn:
			res = await conn.execute(Download.__table__.insert().values(**params))
			await conn.commit()
		return res.lastrowid if res else None

	async def update_download(self, download_id: int, params: dict) -> Optional[Download]:
		res = None
		# d = await self.get_download()
		# d = await self.__to_object__(d)
		# d = await self.__map_one__(params.values(),params.keys(),Download)
		params['bot_id'] = self.bot.config.BOT_ID
		params['updated_on'] = datetime.now()
		params = await self.__filter__(params, Download)

		async with self.engine.begin() as conn:
			res = await conn.execute(Download.__table__.update().where(Download.id==download_id).values(**params))
			await conn.commit()
		return await self.get_download(download_id)

	async def remove_download(self, download_id: int) -> Optional[Download]:
		res = await self.get_download(download_id)

		async with self.engine.begin() as conn:
			await conn.execute(Download.__table__.delete().where(Download.id==download_id))
			await conn.commit()
		return res