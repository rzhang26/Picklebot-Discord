import os
import discord
from discord.ext import commands, tasks
import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

EASTERN_TZ = ZoneInfo('America/New_York')
friday_time = datetime.time(hour=20, minute=30, tzinfo=EASTERN_TZ) #8:30 poll
sat_time = datetime.time(hour=20, minute=30, tzinfo=EASTERN_TZ) #8:30 event reminder & creation for meeting @ 9:00

class RemindersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = int(os.getenv("GUILD_ID", 0))
        self.webhook_url = os.getenv("REMINDER_WEBHOOK_URL")

        self.last_poll_date = None
        self.last_event_date = None
        
        self.friday_dm_and_poll_loop.start()
        self.saturday_webhook_loop.start()

    def cog_unload(self):
        self.friday_dm_and_poll_loop.cancel()
        self.saturday_webhook_loop.cancel()

    # @tasks.loop(seconds=15.0)
    @tasks.loop(time=friday_time)
    async def friday_dm_and_poll_loop(self):
        await self.bot.wait_until_ready()
        print("DEBUG: Friday DM/Poll loop is ticking...")

        if datetime.datetime.today().weekday() != 5: #4 = friday
            return

        today = datetime.date.today()
        if self.last_poll_date == today:
            return 
        
        try:
            guild = await self.bot.fetch_guild(self.guild_id)
        except Exception as e:
            print(f"❌ Reminders Cog could not find guild ID {self.guild_id}: {e}")
            return

        poll = discord.Poll(
            question="Are you attending tomorrow's Saturday Meetup at 9:00 PM?",
            duration=timedelta(hours=24)
        )
        poll.add_answer(text="Yes, I am in!", emoji="✅")
        poll.add_answer(text="No, can't make it", emoji="❌")

        success_count = 0
        async for member in guild.fetch_members(limit=None):
            if member.bot:
                continue
            try:
                await member.send(content="👋 Hello Pickler! Quick check-in for tomorrow's event:", poll=poll)
                success_count += 1
                print(f"DEBUG: Sent check-in poll DM directly to {member.name}")
            except discord.Forbidden:
                print(f"DEBUG: Skipped DMing {member.name} (User has private DMs turned off)")
                continue

        general_channel_id = int(os.getenv("GENERAL_CHANNEL_ID", 0))
        if general_channel_id:
            try:
                general_channel = await self.bot.fetch_channel(general_channel_id)
                await general_channel.send(f"📢 **Attendance Check initiated!** Sent out private check-in polls. Check your DMs!")
            except Exception as e:
                print(f"❌ Failed sending poll alert to general chat: {e}")

        self.last_poll_date = today
        print(f"DEBUG: Friday DM/Poll loop finished and locked for {today}")

    # @tasks.loop(seconds=15.0)
    @tasks.loop(time=sat_time)
    async def saturday_webhook_loop(self):
        await self.bot.wait_until_ready()
        print("DEBUG: Saturday Webhook/Event loop is ticking...")

        if datetime.datetime.today().weekday() != 5: #5 = sat
            return
        
        today = datetime.date.today()
        if self.last_event_date == today:
            return 

        try:
            guild = await self.bot.fetch_guild(self.guild_id)
        except Exception as e:
            print(f"❌ Reminders Cog could not find guild ID {self.guild_id}: {e}")
            return

        now = datetime.datetime.now(EASTERN_TZ)
        target_time = now.replace(hour=21, minute=0, second=0, microsecond=0)
        
        if target_time < now:
            target_time += timedelta(days=1)
            
        end_time = target_time + timedelta(hours=3)

        try:
            await guild.create_scheduled_event(
                name="Weekly Pickleball Open Session",
                description="Our normal meeting.",
                start_time=target_time,
                end_time=end_time,
                entity_type=discord.EntityType.external,
                location="On the Court under 'General' ",
                privacy_level=discord.PrivacyLevel.guild_only
            )
            print("DEBUG: Successfully registered Scheduled Event inside Discord Client Server.")
        except Exception as e:
            print(f"❌ Discord refused scheduled event registration: {e}")

        if self.webhook_url:
            try:
                webhook = discord.Webhook.from_url(url=self.webhook_url, client=self.bot) 
                structured_announcement = "### 🗓️ WEEKLY MEETING REMINDER\nOur Saturday session is officially scheduled!"
                await webhook.send(content=structured_announcement, username="Picklebot")
                print("DEBUG: Successfully broadcasted Webhook alert presentation block.")
            except Exception as e:
                print(f"❌ Webhook execution failed: {e}")

        self.last_event_date = today
        print(f"DEBUG: Saturday event loop finished and locked for {today}")

    @commands.command(name="create_event")
    @commands.has_permissions(administrator=True)  # Restricts usage to admins/owners
    async def create_event(self, ctx: commands.Context, title: str, date_str: str, time_str: str, *, description: str = "Picklebot meetup"):
        """
        Creates a custom guild event.
        Usage: !create_event "Saturday Social" 2026-07-18 20:30 "Weekly social matches"
        """
        try:
            combined_str = f"{date_str} {time_str}"
            naive_dt = datetime.datetime.strptime(combined_str, "%Y-%m-%d %H:%M")
            
            local_start_time = naive_dt.replace(tzinfo=EASTERN_TZ)
            
            now = datetime.datetime.now(EASTERN_TZ)
            if local_start_time < now:
                await ctx.send("❌ Error: You cannot schedule an event in the past.")
                return

            local_end_time = local_start_time + datetime.timedelta(hours=2)

            scheduled_event = await ctx.guild.create_scheduled_event(
                name=title,
                description=description,
                start_time=local_start_time,
                end_time=local_end_time,
                entity_type=discord.EntityType.external,  
                location="On the Court",       
                privacy_level=discord.PrivacyLevel.guild_only
            )

            await ctx.send(f"✅ **Event Created Successfully!**\nJoin here: {scheduled_event.url}")

        except ValueError:
            await ctx.send("❌ **Invalid Format.** Use: `!create_event \"Title\" YYYY-MM-DD HH:MM \"Description\"` (e.g., `2026-07-18 20:30`)")
        except Exception as e:
            await ctx.send(f"❌ An unexpected error occurred: {str(e)}")

    @create_event.error
    async def create_event_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("⛔ You do not have permission to use this command. Admins only.")


    @friday_dm_and_poll_loop.error
    async def friday_error(self, error):
        print(f"💥 CRITICAL: Friday poll loop crashed: {error}")

    @saturday_webhook_loop.error
    async def saturday_error(self, error):
        print(f"💥 CRITICAL: Saturday webhook loop crashed: {error}")

async def setup(bot):
    await bot.add_cog(RemindersCog(bot))