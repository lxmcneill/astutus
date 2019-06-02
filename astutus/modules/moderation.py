import discord
import arrow
from typing import List, Optional
from discord.ext import commands as cmd
from discord.ext import tasks as tsk
from astutus.utils import (
    checks,
    MemberID,
    ActionReason,
    BannedMember,
    delta_convert,
    Duration,
)
from uuid import uuid4
from copy import deepcopy
from itertools import chain


async def bulk_mod(ctx, kind: str, members: List[int], reason: str):
    done = []
    for member in members:
        member_object = await ctx.bot.fetch_user(member)
        try:
            await getattr(ctx.guild, kind)(member_object, reason=reason)
        except:
            pass
        done.append(member_object)
    return done


class ModerationModule(cmd.Cog):
    def __init__(self, bot: cmd.Bot):
        self.bot = bot
        self.unmute_timer.start()
        self.unban_timer.start()

    def cog_unload(self):
        self.unmute_timer.cancel()
        # self.unwarn_timer.cancel()
        self.unban_timer.cancel()
        # self.unjail_timer.cancel()

    @tsk.loop(seconds=10)
    async def unmute_timer(self):
        now = arrow.utcnow()
        for guild in self.bot.guilds:
            to_action = await self.bot.db.zbyscore(
                f"{guild.id}:mutes", now.shift(seconds=-11).timestamp, now.timestamp
            )
            if to_action:
                role = await self.get_or_create_muted_role(guild)
                for action in to_action:
                    yes = guild.get_member(int(action))
                    if yes:
                        await yes.remove_roles(role, reason="Mute expired")
                await self.bot.db.zrembyscore(
                    f"{guild.id}:mutes", now.shift(seconds=-11).timestamp, now.timestamp
                )

    @tsk.loop(seconds=10)
    async def unban_timer(self):
        now = arrow.utcnow()
        for guild in self.bot.guilds:
            to_action = await self.bot.db.zbyscore(
                f"{guild.id}:bans", now.shift(seconds=-11).timestamp, now.timestamp
            )
            if to_action:
                for action in to_action:
                    usr = await self.bot.fetch_user(action)
                    await guild.unban(usr, reason="ban expired")
                await self.bot.db.zrembyscore(
                    f"{guild.id}:bans", now.shift(seconds=-11).timestamp, now.timestamp
                )

    @unban_timer.before_loop
    async def before_unban_timer(self):
        await self.bot.wait_until_ready()

    @unmute_timer.before_loop
    async def before_unmute_timer(self):
        await self.bot.wait_until_ready()

    # async def warn_count(self, member: int, guild: int):
    #     return len(
    #         [
    #             warning
    #             for warning in self.warnings
    #             if warning[0] == member
    #             and warning[1] == guild
    #             and warning[2] < arrow.utcnow().timestamp
    #         ]
    #     )

    async def mute_muted_role(self, role: discord.Role, guild: discord.Guild):
        for channel in guild.channels:
            perms = channel.overwrites_for(role)
            if (
                type(channel) is discord.TextChannel
                and not perms.send_messages == False
            ):
                try:
                    await channel.set_permissions(
                        role, send_messages=False, add_reactions=False
                    )
                except:
                    pass
            elif type(channel) is discord.VoiceChannel and not perms.speak == False:
                try:
                    await channel.set_permissions(role, speak=False)
                except:
                    pass

    async def create_muted_role(self, guild):
        perms = discord.Permissions()
        perms.update(
            send_messages=False,
            read_messages=True,
            add_reactions=False,
            create_instant_invite=False,
            embed_links=False,
            attach_files=False,
            mention_everyone=False,
            speak=False,
            connect=True,
        )
        role = await guild.create_role(
            name="Muted",
            permissions=perms,
            colour=discord.Colour(0xE74C3C),
            reason="Creating Muted role since one does not exist already.",
        )
        await self.mute_muted_role(role, guild)
        await self.bot.db.hset(f"{guild.id}:role", "muted", role.id)
        return role

    async def get_muted_role(self, guild):
        r = await self.bot.db.hget(f"{guild.id}:role", "muted")
        if r:
            found = guild.get_role(int(r))
            if found:
                return found
        return

    async def get_or_create_muted_role(self, guild):
        r = await self.get_muted_role(guild)
        if not r:
            r = await self.create_muted_role(guild)
        return r

    @cmd.command()
    @cmd.guild_only()
    @checks.can_kick()
    async def kick(
        self, ctx: cmd.Context, members: cmd.Greedy[MemberID], *, reason: ActionReason
    ):
        kicked = await bulk_mod(ctx, "kick", members, reason)
        kicked = ", ".join([f"**{k}**" for k in kicked])
        await ctx.send(f"**{ctx.author}** kicked {kicked}.")

    @cmd.command()
    @cmd.guild_only()
    @checks.can_kick()
    async def mute(
        self,
        ctx: cmd.Context,
        members: cmd.Greedy[MemberID],
        duration: Optional[Duration],
        *,
        reason: ActionReason = None,
    ):
        if duration == None or not duration:
            duration = arrow.get(7559466982)
        role = await self.get_or_create_muted_role(ctx.guild)
        await self.mute_muted_role(role, ctx.guild)
        result = []
        for m in members:
            mem = ctx.guild.get_member(m)
            if mem:
                await mem.add_roles(role)
                await self.bot.db.zadd(f"{ctx.guild.id}:mutes", m, duration.timestamp)
                result.append(mem)
        result = ", ".join([f"**{k}**" for k in result])
        duration = duration.humanize()
        if duration == "just now":
            duration = "now"
        await ctx.send(
            f"**{ctx.author}** muted {result}. They will be unmuted **{duration}**."
        )

    @cmd.command()
    @cmd.guild_only()
    @checks.can_ban()
    async def ban(
        self,
        ctx: cmd.Context,
        members: cmd.Greedy[MemberID],
        duration: Optional[Duration],
        *,
        reason: ActionReason = None,
    ):
        if duration == None or not duration:
            duration = arrow.get(7559466982)
        banned = await bulk_mod(ctx, "ban", members, reason)
        for b in banned:
            await self.bot.db.zadd(f"{ctx.guild.id}:bans", b.id, duration.timestamp)
        result = ", ".join([f"**{k}**" for k in banned])
        duration = duration.humanize()
        if duration == "just now":
            duration = "now"
        await ctx.send(
            f"**{ctx.author}** banned {result}. They will be unbanned **{duration}**."
        )

    @cmd.command()
    @cmd.guild_only()
    @checks.can_ban()
    async def unban(
        self,
        ctx: cmd.Context,
        members: cmd.Greedy[MemberID],
        *,
        reason: ActionReason = None,
    ):
        unbanned = await bulk_mod(ctx, "unban", members, reason)
        unbanned = ", ".join([f"**{k}**" for k in unbanned])
        await ctx.send(f"**{ctx.author}** unbanned {unbanned}.")


def setup(bot):
    cog = ModerationModule(bot)
    bot.add_cog(cog)
