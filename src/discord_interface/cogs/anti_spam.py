from datetime import datetime
from typing import Optional, Set

import discord
from discord.ext import commands

from config.config import GUILD_ID_DISCORD


class AntiSpam(commands.Cog):
    """Provides basic anti-spam measures based on message frequency."""
    def __init__(self, bot: commands.Bot, spam_allowed_channels: Set[int]) -> None:
        """Initializes the AntiSpam cog."""
        self.bot = bot
        self.spam_allowed_channels = spam_allowed_channels
        self.spam_cd = commands.CooldownMapping.from_cooldown(5, 60.0, commands.BucketType.user)
        self.mute_role: Optional[discord.Role] = None
        self.last_msg_time: dict[int, datetime] = {}
        self.logger = getattr(bot, 'logger', None)

    async def initialize_role(self) -> None:
        """Initializes the mute role after the bot is ready."""
        guild = self.bot.get_guild(GUILD_ID_DISCORD)
        if guild:
            self.mute_role = discord.utils.get(guild.roles, name="Muted")
            if self.mute_role:
                if self.logger:
                    self.logger.info(f"AntiSpam: Found Muted role (ID: {self.mute_role.id})")
            else:
                if self.logger:
                    self.logger.warning(f"AntiSpam: Mute role 'Muted' not found in guild {GUILD_ID_DISCORD}.")
        elif self.logger:
            self.logger.warning(f"AntiSpam: Could not find guild {GUILD_ID_DISCORD} during role initialization. Cache might still be populating.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Monitors messages for potential spam and applies cooldowns/mutes."""
        if message.author.bot or not message.guild:
            return
        if message.channel.id in self.spam_allowed_channels:
            return
        if isinstance(message.author, discord.Member) and message.author.guild_permissions.manage_messages:
            return

        bucket = self.spam_cd.get_bucket(message)
        if not bucket:
            return

        retry_after = bucket.update_rate_limit()

        if retry_after:
            user_id = message.author.id
            now = message.created_at

            try:
                await message.delete()
            except discord.Forbidden:
                if self.logger:
                    self.logger.warning(f"Missing permissions to delete spam message from {user_id}")
            except discord.NotFound:
                pass

            if user_id in self.last_msg_time and (now - self.last_msg_time[user_id]).total_seconds() < 5.0:
                if self.mute_role and isinstance(message.author, discord.Member):
                    try:
                        await message.author.add_roles(self.mute_role, reason="Spamming")
                        await message.channel.send(f"{message.author.mention} muted for spamming.", delete_after=20)
                    except discord.Forbidden:
                        if self.logger:
                            self.logger.warning(f"Missing permissions to assign Muted role to {user_id}")
                    except discord.HTTPException as e:
                        if self.logger:
                            self.logger.error(f"Failed to mute user {user_id}: {e}")
                if user_id in self.last_msg_time:
                    del self.last_msg_time[user_id]
            else:
                self.last_msg_time[user_id] = now
        else:
            if message.author.id in self.last_msg_time:
                del self.last_msg_time[message.author.id]

    @commands.command(name='unmute')
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def unmute(self, ctx: commands.Context, member: discord.Member) -> None:
        """Unmutes a member by removing the configured 'Muted' role."""
        if not self.mute_role:
            await ctx.send("Mute role not found or configured for this bot.")
            return

        if self.mute_role not in member.roles:
            await ctx.send(f"{member.mention} does not have the Muted role.")
            return

        try:
            await member.remove_roles(self.mute_role, reason=f"Unmuted by {ctx.author}")
            await ctx.send(f"{member.mention} has been unmuted.")
        except discord.Forbidden:
            await ctx.send("I don't have permissions to remove the Muted role.")
        except discord.HTTPException as e:
            if self.logger:
                self.logger.error(f"Failed to unmute {member.id}: {e}")
            await ctx.send("Failed to unmute the member due to a Discord error.")