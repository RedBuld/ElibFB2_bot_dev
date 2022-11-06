import calendar
import asyncio, time
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
					value = val(obj)
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


	# USER SETTINGS

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

	async def add_user_setting(self, user_id: int, key: str, value: str) -> Optional[int]:
		res = None

		us = UserSetting()
		us.user=user_id
		us.bot_id = self.bot.config.BOT_ID
		us.key=key
		params = await self.__to_object__(us)

		async with self.engine.begin() as conn:
			res = await conn.execute(insert(UserSetting.__table__).values(**params).on_duplicate_key_update(value=value))
			await conn.commit()
		return res.lastrowid if res else None

	async def set_user_ban(self, *args, **kwargs) -> None:
		# PLACEHOLDER
		return

	async def get_user_ban(self, *args, **kwargs) -> bool:
		# PLACEHOLDER
		return False

	async def can_download(self, user_id: int) -> bool:
		if self.bot.config.DOWNLOADS_FREE_LIMIT:
			used = await self.get_user_stat(user_id)
			if used >= self.bot.config.DOWNLOADS_FREE_LIMIT:
				premium = await self.is_user_premium(user_id)
				if not premium:
					return False
		return True

	async def is_user_premium(self, user_id: int) -> bool:
		res = False

		day = datetime.now()

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(ACL)\
					.filter(ACL.user==user_id,ACL.mode==0)
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
			await conn.execute(ACL.__table__.delete().where(ACL.user==user_id,ACL.mode==0))
			await conn.commit()
		return

	async def add_user_stat(self, user_id: int, mode: int=0) -> Optional[int]:
		res = None

		us = UserStat()
		us.user=user_id
		us.bot_id = self.bot.config.BOT_ID
		params = await self.__to_object__(us)

		cmd = "count+1" if mode==0 else "count-1"

		async with self.engine.begin() as conn:
			res = await conn.execute(insert(UserStat.__table__).values(**params).on_duplicate_key_update(count=sa.text(cmd)))
			await conn.commit()
		return res.lastrowid if res else None

	async def get_user_stat(self, user_id: int) -> Optional[int]:
		res = None

		day = date.today()

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(UserStat.count)\
					.filter(UserStat.day==str(day),UserStat.user==user_id,UserStat.bot_id==self.bot.config.BOT_ID)
			)
			res = query.scalar()
		if not res:
			res = 0
		return res

	# STATISTICS


	async def add_site_stat(self, site: str, size: int) -> Optional[int]:
		res = None

		ss = SiteStat()
		ss.site=site
		ss.bot_id = self.bot.config.BOT_ID
		params = await self.__to_object__(ss)

		async with self.engine.begin() as conn:
			res = await conn.execute(insert(SiteStat.__table__).values(**params).on_duplicate_key_update(count=sa.text("count+1"),fsize=sa.text(f"fsize+{size}")))
			await conn.commit()
		return res.lastrowid if res else None

	async def get_daily_stats(self, days_step: Optional[int]=0) -> Optional[list]:
		res = None

		dat = self.get_daily_stats_dates(days_step)

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(SiteStat.site,SiteStat.count)\
					.filter(SiteStat.day==str(dat),SiteStat.bot_id==self.bot.config.BOT_ID)\
					.order_by(sa.asc(SiteStat.site))
			)
			res = query.fetchall()
		return res

	async def get_daily_stats_dates(self, days_step: Optional[int]=0) -> date:
		today = date.today()

		y = today.year
		m = today.month
		d = today.day + days_step

		dat = date(y, m, d)

		return dat
		# sql = select(SiteStat.site,SiteStat.count).filter(SiteStat.day==str(dat),SiteStat.bot_id==self.bot.config.BOT_ID).order_by(sa.asc(SiteStat.site))
		# return str( sql.compile(self.engine, compile_kwargs={"literal_binds": True}) )

	async def get_monthly_stats(self, month_step: Optional[int]=0) -> Optional[list]:
		res = None

		start, end = self.get_daily_stats_dates(month_step)

		async with self.engine.begin() as conn:
			query = await conn.execute(
				select(SiteStat.site,func.sum(SiteStat.count).label("count"))\
					.filter(SiteStat.day.between(start,end),SiteStat.bot_id==self.bot.config.BOT_ID)\
					.group_by(SiteStat.site)\
					.order_by(sa.asc(SiteStat.site))
			)
			res = query.fetchall()
		return res

	async def get_monthly_stats_dates(self, month_step: Optional[int]=0) -> tuple:
		today = date.today()

		y = today.year
		m = today.month + month_step
		s, e = calendar.monthrange(y, m)

		start = date(y, m, 1)
		end = date(y, m, e)
		return (start, end)
		# sql = select(SiteStat.site,func.sum(SiteStat.count).label("count")).filter(SiteStat.day.between(str(start),str(end)),SiteStat.bot_id==self.bot.config.BOT_ID).group_by(SiteStat.site).order_by(sa.asc(SiteStat.site))
		# return str( sql.compile(self.engine, compile_kwargs={"literal_binds": True}) )
	

	async def update_usage_status(self, queue_length: int,total_length: int) -> Optional[int]:
		res = None

		s = BotStat()
		s.bot_id=self.bot.config.BOT_ID
		s.queue_length=queue_length
		s.total_length=total_length
		params = await self.__to_object__(s)

		async with self.engine.begin() as conn:
			res = await conn.execute(insert(BotStat.__table__).values(**params).on_duplicate_key_update(queue_length=queue_length,total_length=total_length))
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