import asyncio
import arrow
import discord
from discord.ext import commands as cmd
from .utils.converters import MemberID
from .utils.discord_search import choose_item


class TrackingModule(cmd.Cog):
    """Ever wondered what it was like to be a stalker? Well today is your lucky today. But this stuff can be really useful if you're trying to track someone down."""

    def __init__(self, bot: cmd.Bot):
        self.bot = bot
        self.cap = int(self.bot.config["TRACKING"]["history"])

    @cmd.command()
    async def seen(self, ctx: cmd.Context, *user):
        if user:
            user = await choose_item(ctx, "member", ctx.guild, " ".join(user).lower())
        else:
            user = ctx.author
        obj = await self.bot.db.hget("tr:ls", user.id)
        # user = ctx.guild.get_member(user)
        if not obj:
            raise cmd.BadArgument(f"I have not seen **{user}** before.")
        platform = await self.bot.db.hget("tr:lp", user.id) or ""
        if platform:
            platform = f"on **{platform}** "
        if user and user.status == discord.Status.online:
            platform = ""
            if user.web_status == discord.Status.online:
                platform = "web"
            elif user.mobile_status == discord.Status.online:
                platform = "mobile"
            elif user.desktop_status == discord.Status.online:
                platform = "desktop"
            print(platform)
            await ctx.send(f"**{user}** is on **Discord {platform}** right now!")
            return
        now = arrow.get(obj)
        await ctx.send(
            f"The last time I saw **{user}** {platform}was **{now.humanize()}**."
        )

    @cmd.command()
    async def nicknames(self, ctx: cmd.Context, *user):
        if user:
            user = await choose_item(ctx, "member", ctx.guild, " ".join(user).lower())
        else:
            user = ctx.author
        obj = f"tr:nn:{ctx.guild.id}:{user.id}"
        # user = await self.bot.fetch_user(user)
        previous_nicks = await self.bot.db.lrange(obj, 0, -1)
        if not previous_nicks:
            raise cmd.BadArgument(f"Looks like **{user}** has no previous nicknames.")
        previous_nicks = [f"**{n}**" for n in previous_nicks]
        await ctx.send(
            f"Previous nicknames for **{user}** include: {', '.join(previous_nicks)}."
        )

    @cmd.command()
    async def usernames(self, ctx: cmd.Context, *user):
        if user:
            user = await choose_item(ctx, "member", ctx.guild, " ".join(user).lower())
        else:
            user = ctx.author
        obj = f"tr:nn:{ctx.guild.id}:{user.id}"
        # user = await self.bot.fetch_user(user)
        previous_nicks = await self.bot.db.lrange(obj, 0, -1)
        if not previous_nicks:
            raise cmd.BadArgument(f"Looks like **{user}** has no previous usernames.")
        previous_nicks = [f"**{n}**" for n in previous_nicks]
        await ctx.send(
            f"Previous usernames for **{user}** include: {', '.join(previous_nicks)}."
        )

    async def track_last_seen(self, member):
        await self.bot.db.hset("tr:ls", member.id, arrow.utcnow().timestamp)
        platform = None
        if getattr(member, "web_status", None) == discord.Status.online:
            platform = "web"
        elif getattr(member, "mobile_status", None) == discord.Status.online:
            platform = "mobile"
        elif getattr(member, "desktop_status", None) == discord.Status.online:
            platform = "desktop"
        if platform:
            await self.bot.db.hset("tr:lp", member.id, platform)

    async def track_username(self, member, username):
        obj = f"tr:un:{member.id}"
        names = await self.bot.db.lrange(obj, 0, -1)
        if username not in names:
            await self.bot.db.rpush(obj, username)
        if await self.bot.db.llen(obj) > self.cap:
            await self.bot.db.lpop(obj)

    async def track_nickname(self, member, nickname):
        obj = f"tr:nn:{member.guild.id}:{member.id}"
        nicks = await self.bot.db.lrange(obj, 0, -1)
        if nickname not in nicks:
            await self.bot.db.rpush(obj, nickname)
        if await self.bot.db.llen(obj) > self.cap:
            await self.bot.db.lpop(obj)

    @cmd.Cog.listener()
    async def on_guild_join(self, guild):
        await asyncio.gather(
            *(
                self.track_last_seen(m)
                for m in guild.members
                if m.status != discord.Status.offline
            )
        )

    @cmd.Cog.listener()
    async def on_member_update(self, before, member):
        await self.track_last_seen(member)
        if before.name != member.name:
            await self.track_username(member, before.name)
        nick_before = before.display_name
        nick_after = member.display_name
        if nick_before != nick_after and hasattr(member, "guild"):
            await self.track_nickname(member, nick_before)

    @cmd.Cog.listener()
    async def on_typing(self, _, member, __):
        await self.track_last_seen(member)

    @cmd.Cog.listener()
    async def on_message(self, message):
        await self.track_last_seen(message.author)

    @cmd.Cog.listener()
    async def on_member_join(self, member):
        await self.track_last_seen(member)


def setup(bot):
    cog = TrackingModule(bot)
    bot.add_cog(cog)
