import discord
from discord import app_commands
from discord.ext import commands


class Resume(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="resume", description="Resumes track")
    @app_commands.guild_only()
    async def resume(self, interaction: discord.Interaction):
        await self.helper(interaction)

    async def helper(self, interaction: discord.Interaction):
        if not await self.bot.able_to_use_commands(
            interaction,
            self.bot.cache[interaction.guild_id].music_channel_id,
            self.bot.cache[interaction.guild_id].music_role_id,
        ):
            return

        player = await self.bot.get_player(interaction)

        if player.is_paused():
            await player.resume()
            await interaction.response.send_message("**Resumed** ▶")
            playing_view = self.bot.cache[interaction.guild_id].playing_view
            await playing_view.edit_view(interaction, True)

        else:
            await interaction.response.send_message("Already resumed")


async def setup(bot):
    await bot.add_cog(Resume(bot))
