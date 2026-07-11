import datetime
import os
import urllib.parse
import aiohttp
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks, commands

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, Field, select
from sqlmodel.ext.asyncio.session import AsyncSession

EASTERN_TZ = ZoneInfo("America/New_York")
DAILY_TRIGGER_TIME = datetime.time(hour=9, minute=0, second=0, tzinfo=EASTERN_TZ)
DATABASE_URL = "sqlite+aiosqlite:///picklebot_news_state.db"

load_dotenv()
NEWS_API_KEY = os.getenv('API_NEWS_KEY', '')
comp_channel_id = int(os.getenv('COMPETITION_CHANNEL_ID', 0))
consumer_channel_id = int(os.getenv('CONSUMER_CHANNEL_ID', 0))
tech_channel_id = int(os.getenv('TECH_CHANNEL_ID', 0))

CATEGORIES_MAP = {
    comp_channel_id: {  
        "qInTitle": "pickleball",
        "q": "pickleball AND (tournament OR PPA OR APP OR championship OR pro)",
        "label": "competition-news"
    },
    consumer_channel_id: { 
        "qInTitle": "pickleball",
        "q": "pickleball AND (paddle OR gear OR shoes OR equipment OR brand)",
        "label": "consumer-news"
    },
    tech_channel_id: { 
        "qInTitle": "pickleball",
        "q": "pickleball AND (technology OR engineering OR innovation OR 'smart court')",
        "label": "tech-news"
    }
}


class PostedArticle(SQLModel, table=True):
    __tablename__ = "posted_articles"
    
    url: str = Field(primary_key=True)
    category: str  
    date_posted: str


class NewsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.async_engine = None

    async def cog_load(self):
        print("[News Setup] Initializing database engine inside loop context...")
        self.async_engine = create_async_engine(DATABASE_URL, echo=False)
        
        async with self.async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            
        print("[News Setup] Database verified. Launching background loop.")
        self.daily_news_feed.start()

    def cog_unload(self):
        self.daily_news_feed.cancel()

    async def fetch_latest_pickleball_news(self, session: aiohttp.ClientSession, q_in_title: str, q_body: str) -> list[dict]:
        
        encoded_title = urllib.parse.quote_plus(q_in_title)
        encoded_body = urllib.parse.quote_plus(q_body)
        
        # Built URL using dual query tracking parameters + relevance sorting
        json_url = (
            f"https://newsapi.org/v2/everything?"
            f"qInTitle={encoded_title}&"
            f"q={encoded_body}&"
            f"sortBy=relevancy&"
            f"language=en&"
            f"apiKey={NEWS_API_KEY}"
        )
        
        headers = {"User-Agent": "PicklebotDiscordNewsBot/1.0"}
        articles = []
        
        try:
            async with session.get(json_url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get("articles", []):
                        title = item.get("title")
                        link = item.get("url")
                        if title and link:
                            articles.append({"title": title, "url": link})
                else:
                    print(f"[News Error] API Request failed with status code: {response.status}")
        except Exception as e:
            print(f"[News Error] Exception encountered during API network fetch: {e}")
            
        return articles

    async def broadcast_article(self, channel_id: int, label: str, article: dict) -> bool:
        pickleball_green = discord.Color.from_rgb(143, 227, 23) 
        embed = discord.Embed(
            title="🏓 Fresh Pickleball Update",
            description=f"**[{article['title']}]({article['url']})**",
            color=pickleball_green,
            timestamp=datetime.datetime.now(EASTERN_TZ)
        )
        friendly_category = label.replace("-", " ").title()
        embed.set_footer(text=f"Picklebot Daily Feed • {friendly_category}")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception as e:
                print(f"[News Error] Channel ID {channel_id} could not be resolved: {e}")
                return False

        try:
            await channel.send(embed=embed)
            print(f"[News Dispatch] Successfully posted article directly to channel ID: {channel_id} (#{label})")
            return True
        except Exception as e:
            print(f"[News Error] Failed to write message text to channel ID {channel_id}: {e}")
            return False

    
    @tasks.loop(time=DAILY_TRIGGER_TIME)
    async def daily_news_feed(self):
        await self.bot.wait_until_ready()
        print("[News Automation] Running daily pickleball aggregation...")
        
        today_iso = datetime.datetime.now(EASTERN_TZ).strftime("%Y-%m-%d")
        
        async with aiohttp.ClientSession() as session:
            for channel_id, config in CATEGORIES_MAP.items():
                channel_label = config["label"]
                q_title = config["qInTitle"]
                q_body = config["q"]
                
                async with AsyncSession(self.async_engine) as db_session:
                    statement = select(PostedArticle).where(
                        PostedArticle.category == channel_label,
                        PostedArticle.date_posted == today_iso
                    )
                    history_check = await db_session.exec(statement)
                    if history_check.first() is not None:
                        print(f"[News Guard] Category #{channel_label} already completed for today ({today_iso}). Skipping.")
                        continue

                    found_articles = await self.fetch_latest_pickleball_news(session, q_title, q_body)
                    
                    target_article = None
                    for article in found_articles:
                        url_check = await db_session.get(PostedArticle, article["url"])
                        if url_check is None:
                            target_article = article
                            break
                    
                    if target_article:
                        was_distributed = await self.broadcast_article(channel_id, channel_label, target_article)
                        
                        if was_distributed:
                            new_record = PostedArticle(
                                url=target_article["url"],
                                category=channel_label,
                                date_posted=today_iso
                            )
                            db_session.add(new_record)
                            await db_session.commit()
                    else:
                        print(f"[News Guard] No unique articles found in search payload for #{channel_label}")

async def setup(bot: commands.Bot):
    await bot.add_cog(NewsCog(bot))