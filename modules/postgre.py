from discord.ext import commands as cmd
import asyncio
from .utils.postgre import get_db


class PostgreModule(cmd.Cog):
    "Postgre connector"

    def __init__(self, bot: cmd.Bot):
        self.bot = bot
        loop = asyncio.get_event_loop()
        pool = loop.run_until_complete(get_db())
        self.pool = pool

    async def sql_query_db(self, statement, parameters=None):
        result = None
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                if parameters is not None:
                    result = await connection.execute(statement, *parameters)
                elif " WHEREALL " in statement:
                    result = await connection.fetch(
                        statement.replace("WHEREALL", "WHERE")
                    )
                elif " WHERE " in statement:
                    result = await connection.fetchrow(statement)
                else:
                    result = await connection.fetch(statement)
        return result

    async def sql_insert(self, table, data_dict):
        keys = ", ".join(f'"{m}"' for m in data_dict.keys())
        print(keys)
        values = ", ".join(f"${i+1}" for i, x in enumerate(data_dict.values()))
        print(values)
        print(f'INSERT INTO "{table}" ({keys}) VALUES ({values})')
        res = await self.sql_query_db(
            f'INSERT INTO "{table}" ({keys}) VALUES ({values})',
            parameters=tuple(data_dict.values()),
        )
        print(res)
        return


def setup(bot):
    bot.add_cog(PostgreModule(bot))