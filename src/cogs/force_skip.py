import logging

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)


class Force_Skip(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="force-skip", description="Skips the track")
    @app_commands.checks.cooldown(1, 2, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_only()
    async def force_skip(self, interaction: discord.Interaction):
        await self.helper(interaction)

    async def helper(self, interaction: discord.Interaction):
        if not await self.bot.able_to_use_commands(
            interaction
        ) and not await self.bot.does_voice_exist(interaction):
            return

        player = await self.bot.get_player(interaction)

        if player.is_playing():
            await player.stop()
            player.queue.loop = False
            if hasattr(player, "user_ids"):
                player.user_ids.clear()
            log.info(f"Skipped track name: {player.guild.name}, id: {player.guild.id}")
            await interaction.response.send_message("**Skipped** ⏭")

        else:
            await interaction.response.send_message("Nothing is playing")


async def setup(bot):
    await bot.add_cog(Force_Skip(bot))
