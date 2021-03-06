from discord.ext import commands as cmd
import discord
from .discord_search import choose_item


class Truthy(cmd.Converter):
    async def convert(self, ctx, argument):
        arg = argument.lower()
        if arg not in [
            "0",
            "1",
            "2",
            "strong",
            "weak",
            "on",
            "off",
            "true",
            "false",
            "yes",
            "no",
        ]:
            raise cmd.BadArgument(
                "You must supply a value that's either 'true' or 'false'."
            )
        if arg in ["on", "true", "1", "yes", "weak"]:
            return 1
        if arg in ["2", "strong"]:
            return 2
        return 0


class ChannelID(cmd.Converter):
    async def convert(self, ctx: cmd.Context, argument):
        channel = await choose_item(ctx, "text_channel", ctx.guild, argument.lower())
        if channel is None:
            raise cmd.BadArgument(f"Could not find channel: **{argument}**.")
        return channel.id


class MemberID(cmd.Converter):
    async def convert(self, ctx: cmd.Context, argument):
        member = await choose_item(ctx, "member", ctx.guild, argument.lower())
        if member is None:
            raise cmd.BadArgument(f"Could not find member: **{argument}**.")
        return member.id


class ActionReason(cmd.Converter):
    async def convert(self, ctx: cmd.Context, argument):
        if argument is not None:
            result = f"[{ctx.author.id}]{argument}"
        elif len(result) > 140:
            result = f"[{ctx.author.id}]{argument[0:137]}..."
        elif argument is None or argument == "":
            result = f"[{ctx.author.id}] No reason given."
        return result


class BannedMember(cmd.Converter):
    async def convert(self, ctx: cmd.Context, argument):
        ban_list = await ctx.guild.bans()
        try:
            member_id = int(argument, base=10)
            entity = discord.utils.find(lambda u: u.user.id == member_id, ban_list)
        except ValueError:
            entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if entity is None:
            raise cmd.BadArgument("Not a valid previously-banned member.")
        return entity
