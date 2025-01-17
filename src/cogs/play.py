import logging
import re

import discord
from discord import app_commands
from discord.ext import commands
import wavelink

from playing_view import Playing_View

log = logging.getLogger(__name__)


class Play(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackEventPayload):
        log.info(
            f'Now playing "{payload.track.title}" name: {payload.player.guild.name}, id: {payload.player.guild.id}'
        )
        view = Playing_View(self.bot)
        payload.player.message = await payload.player.text_channel.send(
            f"**Playing** 🎶 `{payload.track.title}` by `{payload.track.author}` - Now!",
            view=view,
        )
        payload.player.view = view

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEventPayload):
        log.info(
            f'Finished playing "{payload.track.title}" name: {payload.player.guild.name}, id: {payload.player.guild.id}'
        )
        await self.bot.edit_view_message(payload.player.guild.id, None)

    async def add_to_queue(
        self,
        interaction: discord.Interaction,
        next: bool,
        tracks: wavelink.YouTubePlaylist | list[wavelink.YouTubeTrack],
    ) -> wavelink.Player:
        player: wavelink.Player

        if isinstance(tracks, wavelink.YouTubePlaylist):
            await interaction.response.send_message(
                f"**Added** 🎶 playlist `{tracks.name}` to queue"
            )
            player = await self.connect(interaction)
            if next:
                for track in reversed(
                    tracks.tracks
                ):  # TODO playlist cannot be added via `put_at_front` YET, coming soon
                    player.queue.put_at_front(track)

            else:
                player.queue.put(tracks)

        else:
            await interaction.response.send_message(
                f"**Added** 🎵 `{tracks[0].uri}` to queue"
            )
            player = await self.connect(interaction)
            if next:
                player.queue.put_at_front(tracks[0])

            else:
                player.queue.put(tracks[0])

        return player

    async def connect(self, interaction) -> wavelink.Player:
        if interaction.guild.voice_client:  # already connected
            player: wavelink.Player = interaction.guild.voice_client

        else:
            await interaction.followup.send(
                f"**Connected** 🥁 to `{interaction.user.voice.channel.name}`"
            )
            player: wavelink.Player = await interaction.user.voice.channel.connect(
                cls=wavelink.Player
            )

        return player

    async def get_milliseconds_from_string(
        time_string: str, interaction: discord.Interaction
    ) -> int:
        "takes a time string and returns the time in milliseconds `1:34` -> `94000`, errors return `-1`"
        TIME_RE = re.compile("^[0-5]?\d:[0-5]?\d:[0-5]\d|[0-5]?\d:[0-5]\d|\d+$")
        if not TIME_RE.match(time_string):
            await interaction.response.send_message("Invalid time stamp")
            return -1  # TODO maybe turn this into a exception

        list_of_units = [int(x) for x in time_string.split(":")]

        list_of_units.reverse()  # makes time more predictable to deal with
        total_seconds = 0
        if len(list_of_units) == 3:  # hours
            total_seconds += list_of_units[2] * 3600  # seconds in an hour

        if len(list_of_units) == 2:  # minutes
            total_seconds += list_of_units[1] * 60

        total_seconds += list_of_units[0]  # total seconds

        return total_seconds * 1000  # turn into milliseconds

    @app_commands.command(
        name="play",
        description="plays a track, start time need to formated with colons",
    )
    @app_commands.describe(
        query="What to search for",
        autoplay="Continuously play songs without user querys, once enabled disconnect the bot to disable",
        next="If this track should be put at the front of the queue",
        start_time="Time stamp to start the video at, for example 1:34 or 1:21:19",
    )
    @app_commands.checks.cooldown(1, 2, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_only()
    async def play(
        self,
        interaction: discord.Interaction,
        *,
        query: str,
        autoplay: bool = False,
        next: bool = False,
        start_time: str = None,
    ):
        if not await self.bot.able_to_use_commands(interaction):
            return
        # locked channel is full
        if (
            len(interaction.user.voice.channel.members)
            == interaction.user.voice.channel.user_limit
        ):  # == because admin can drag bot into channel
            await interaction.response.send_message(
                "Locked voice channel is at max capacity"
            )
            return

        # if the bot itself has permissions to join the channel
        if not interaction.user.voice.channel.permissions_for(
            interaction.guild.me
        ).connect:
            await interaction.response.send_message(
                "Does not have permission to connect"
            )
            return

        if start_time is not None:  # parser
            start_time = await get_milliseconds_from_string(start_time, interaction)
            if start_time == -1:  # time code was invalid
                return

        tracks: wavelink.YouTubePlaylist | list[
            wavelink.YouTubeTrack
        ] = await wavelink.YouTubeTrack.search(query)
        if not tracks:
            await interaction.response.send_message("Track not found")
            return

        player: wavelink.player = await self.add_to_queue(interaction, next, tracks)
        player.autoplay = True

        if player.is_playing():  # if busy
            return

        player.text_channel = interaction.channel

        track = player.queue.get()
        await player.play(
            track,
            start=start_time,
            volume=self.bot.cache[interaction.guild_id].volume,
            populate=autoplay,
        )


async def setup(bot):
    await bot.add_cog(Play(bot))
