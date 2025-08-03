from typing import Optional, Union, TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from logging import Logger


class ReactionHandler(commands.Cog):
    """Handles reactions added to messages."""
    def __init__(self, bot: commands.Bot, logger: Optional['Logger'] = None) -> None:
        """Initializes the ReactionHandler cog."""
        self.bot = bot
        self.logger = logger

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]) -> None:
        """Processes reactions added by non-bot users."""
        if user.bot or not reaction:
            return
        
        # Add reaction handling code here
        # Currently this is a placeholder for future reaction functionality
        pass