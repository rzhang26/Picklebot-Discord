import asyncio
import os
from dotenv import load_dotenv 

from fastapi import FastAPI
from contextlib import asynccontextmanager

from bot.client import bot
from api.routes import router

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.load_extension('bot.cogs.filter')
    await bot.load_extension('bot.cogs.news')
    await bot.load_extension('bot.cogs.reminders')

    token = os.getenv('DISCORD_TOKEN', '')
    bot_task = asyncio.create_task(bot.start(token))

    yield 

    print('Shutting down server...')
    await bot.close()
    bot_task.cancel()

app = FastAPI(title='Picklebot', lifespan=lifespan)
app.include_router(router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)