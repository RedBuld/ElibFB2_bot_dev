from aiogram import Bot, Router
from .admin import get_router as admin_router
from .misc import get_router as misc_router
from .auth import get_router as auth_router
from .downloads import get_router as downloads_router

bot = None

router = Router()

def get_router(_bot: Bot):

    global router
    global bot
    bot = _bot

    _admin = admin_router(bot)
    _auth = auth_router(bot)
    _downloads = downloads_router(bot)
    _misc = misc_router(bot)

    router.include_router(_admin)
    router.include_router(_auth)
    router.include_router(_downloads)
    router.include_router(_misc)

    return router


