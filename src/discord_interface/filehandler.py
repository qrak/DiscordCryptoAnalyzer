import asyncio
import json
import os
from datetime import datetime
from typing import Optional

import discord

from config.config import FILE_MESSAGE_EXPIRY
from src.utils.decorators import retry_async


class DiscordFileHandler:
    """Simplified handler for message tracking and automatic deletion with a centralized approach"""
    
    def __init__(self, bot, logger, tracking_file="data/tracked_messages.json", cleanup_interval=7200):
        self.bot = bot
        self.logger = logger
        self.tracking_file = tracking_file
        self.cleanup_interval = cleanup_interval
        self.cleanup_task = None
        self.is_initialized = False
        self.deletion_tasks = set()
        self._message_deletion_tasks = {}  # Map message_id to deletion tasks
        self._tracking_lock = asyncio.Lock()  # Single lock for all tracking operations
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
        
    def initialize(self):
        self.is_initialized = True
        self.start_cleanup_background_task()
    
    def start_cleanup_background_task(self):
        """Start the background task that cleans up expired messages"""
        if self.cleanup_task is not None:
            self.cleanup_task.cancel()
            
        self.cleanup_task = self.bot.loop.create_task(
            self.periodic_cleanup_task(),
            name="MessageCleanupTask"
        )
        self.logger.info(f"Started background message cleanup task (interval: {self.cleanup_interval}s)")
    
    async def periodic_cleanup_task(self):
        """Periodically runs the cleanup process for messages"""
        try:
            await asyncio.sleep(10)  # Initial delay
            
            while True:
                try:
                    await self.cleanup_all_expired_messages()
                    self.logger.debug("Scheduled message cleanup check completed")
                except asyncio.CancelledError:
                    self.logger.info("Message cleanup task cancelled")
                    break
                except Exception as e:
                    self.logger.error(f"Error in scheduled message cleanup: {e}")
                
                try:
                    await asyncio.sleep(self.cleanup_interval)
                except asyncio.CancelledError:
                    self.logger.info("Message cleanup sleep cancelled")
                    break
        except asyncio.CancelledError:
            self.logger.info("Periodic message cleanup task cancelled")
        except Exception as e:
            self.logger.error(f"Unexpected error in periodic message cleanup task: {e}")

    async def cleanup_all_expired_messages(self):
        """Clean up all expired messages"""
        try:
            deleted_count = await self.check_and_delete_expired_messages()
            if deleted_count > 0:
                self.logger.debug(f"Cleaned up {deleted_count} expired messages")
        except Exception as e:
            self.logger.error(f"Error in cleanup_all_expired_messages: {e}")
    
    async def shutdown(self):
        cancelled_tasks = 0
        
        # Cancel the cleanup task
        if self.cleanup_task and not self.cleanup_task.done():
            try:
                self.cleanup_task.cancel()
                cancelled_tasks += 1
            except Exception as e:
                self.logger.warning(f"Error cancelling cleanup task: {e}")
            self.cleanup_task = None
        
        # Cancel all remaining tasks
        deletion_tasks = list(self.deletion_tasks)
        if deletion_tasks:
            for task in deletion_tasks:
                if not task.done():
                    task.cancel()
                    cancelled_tasks += 1
            
            if cancelled_tasks > 0:
                await asyncio.gather(*[asyncio.create_task(self._wait_task_cancelled(task)) for task in deletion_tasks], 
                                    return_exceptions=True)
        
        self.logger.info(f"Cancelled {cancelled_tasks} file handler tasks")
    
    @staticmethod
    async def _wait_task_cancelled(task):
        """Wait for a task to acknowledge cancellation with a short timeout"""
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=0.5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
    
    async def track_message(self, message_id: int, channel_id: int, user_id: Optional[int] = None, 
                           message_type: str = "message", expire_after: int = FILE_MESSAGE_EXPIRY):
        """Track a message and schedule it for deletion after expire_after seconds"""
        async with self._tracking_lock:
            try:
                # Load all tracking data
                tracking_data = await self._load_tracking_data()
                
                expires_at = int(datetime.now().timestamp() + expire_after)
                str_message_id = str(message_id)
                
                tracking_data[str_message_id] = {
                    "channel_id": channel_id,
                    "user_id": user_id if user_id is not None else 0,  # Use 0 for bot messages
                    "created_at": int(datetime.now().timestamp()),
                    "expires_at": expires_at,
                    "message_type": message_type
                }
                
                # Save updated data
                await self._save_tracking_data(tracking_data)
                
                self.logger.debug(f"Tracked {message_type} {message_id} for user {user_id or 'bot'}")
                
                # Schedule deletion task
                self._schedule_message_deletion(message_id, channel_id, expire_after)
                
            except Exception as e:
                self.logger.error(f"Failed to track message {message_id}: {e}")

    async def remove_message_tracking(self, message_id: int):
        """Remove tracking for a specific message"""
        # Cancel any scheduled deletion task
        if message_id in self._message_deletion_tasks:
            task = self._message_deletion_tasks.pop(message_id)
            if not task.done():
                task.cancel()
        
        # Remove from tracking data
        async with self._tracking_lock:
            try:
                tracking_data = await self._load_tracking_data()
                str_message_id = str(message_id)
                
                if str_message_id in tracking_data:
                    del tracking_data[str_message_id]
                    await self._save_tracking_data(tracking_data)
                    self.logger.debug(f"Removed tracking for message {message_id}")
            except Exception as e:
                self.logger.error(f"Error removing tracking for message {message_id}: {e}")
    
    def _schedule_message_deletion(self, message_id: int, channel_id: int, delay: int = FILE_MESSAGE_EXPIRY):
        """Schedule a message for deletion after the specified delay"""
        # Cancel existing task if there is one
        if message_id in self._message_deletion_tasks and not self._message_deletion_tasks[message_id].done():
            self._message_deletion_tasks[message_id].cancel()
            
        # Create a new deletion task
        task = self.bot.loop.create_task(
            self._delete_message_after_delay(message_id, channel_id, delay),
            name=f"DeleteMsg-{message_id}"
        )
        self._message_deletion_tasks[message_id] = task
        self.deletion_tasks.add(task)
        
        # Add cleanup callbacks
        task.add_done_callback(lambda t: self._message_deletion_tasks.pop(message_id, None))
        task.add_done_callback(self.deletion_tasks.discard)
        
        return task
        
    async def _delete_message_after_delay(self, message_id: int, channel_id: int, delay: int):
        """Task that waits for the specified delay and then deletes the message"""
        try:
            self.logger.debug(f"Scheduled message {message_id} for deletion after {delay} seconds")
            await asyncio.sleep(delay)
            
            # Check if message is still being tracked before attempting to delete
            async with self._tracking_lock:
                tracking_data = await self._load_tracking_data()
                if str(message_id) not in tracking_data:
                    # Message was already deleted by another process
                    self.logger.debug(f"Message {message_id} is no longer being tracked, skipping deletion")
                    return
            
            self.logger.debug(f"Deleting message {message_id} after scheduled delay")
            success = await self._delete_message(message_id, channel_id)
            if success:
                # Remove from tracking
                await self.remove_message_tracking(message_id)
                
        except asyncio.CancelledError:
            # Task was cancelled, just exit
            self.logger.debug(f"Deletion task for message {message_id} was cancelled")
            pass
        except Exception as e:
            self.logger.error(f"Error in message deletion task for {message_id}: {e}")

    async def check_and_delete_expired_messages(self):
        """Check for and delete all expired messages concurrently.
        
        Returns the number of successfully deleted messages.
        """
        # First get the list of expired messages under the lock
        async with self._tracking_lock:
            tracking_data = await self._load_tracking_data()
            current_time = datetime.now().timestamp()
            expired_messages_to_delete = []
            
            # Find expired messages not already being handled by a specific deletion task
            for str_message_id, data in list(tracking_data.items()):
                message_id = int(str_message_id)
                if data["expires_at"] < current_time:
                    # Only add to deletion list if not already being handled by a task
                    if message_id not in self._message_deletion_tasks or self._message_deletion_tasks[message_id].done():
                        expired_messages_to_delete.append((message_id, data["channel_id"]))
            
            if not expired_messages_to_delete:
                return 0

        # Log how many messages we found for deletion
        self.logger.info(f"Found {len(expired_messages_to_delete)} expired messages to delete")
            
        # Process deletions outside the lock to avoid deadlocks
        deleted_count = 0
        for message_id, channel_id in expired_messages_to_delete:
            try:
                # Try to delete the message
                result = await self._delete_message(message_id, channel_id)
                
                # If deletion was successful, remove tracking data
                if result is True:
                    async with self._tracking_lock:
                        # Get fresh data in case it changed
                        tracking_data = await self._load_tracking_data()
                        str_message_id = str(message_id)
                        if str_message_id in tracking_data:
                            del tracking_data[str_message_id]
                            await self._save_tracking_data(tracking_data)
                            deleted_count += 1
                
            except discord.NotFound:
                # Message already deleted, remove from tracking
                deleted_count += 1
                async with self._tracking_lock:
                    tracking_data = await self._load_tracking_data()
                    str_message_id = str(message_id)
                    if str_message_id in tracking_data:
                        del tracking_data[str_message_id]
                        await self._save_tracking_data(tracking_data)
                        self.logger.debug(f"Removed tracking for already deleted message {message_id}")
            except Exception as e:
                self.logger.error(f"Error deleting message {message_id}: {e}")
        
        if deleted_count > 0:
            self.logger.info(f"Successfully deleted {deleted_count} expired messages during cleanup")
        
        return deleted_count

    @retry_async(max_retries=3, initial_delay=1, backoff_factor=2, max_delay=30)
    async def _delete_message(self, message_id: int, channel_id: int):
        """Core message deletion logic. Returns True on success, False on permission/HTTP error, raises NotFound."""
        try:
            if not self.bot or self.bot.is_closed():
                self.logger.warning(f"Bot closed, cannot delete message {message_id}")
                return False
                
            channel = self.bot.get_channel(channel_id)
            if not channel:
                self.logger.warning(f"Channel {channel_id} not found for message {message_id}. Assuming deleted.")
                raise discord.NotFound(None, f"Channel {channel_id} not found") 
                
            try:
                message = await channel.fetch_message(message_id)
                await message.delete()
                self.logger.debug(f"Deleted message {message_id} from channel {channel_id}")
                return True
            except discord.NotFound:
                self.logger.debug(f"Message {message_id} already deleted (NotFound exception)")
                # Return True instead of raising, since the end goal (message not existing) is achieved
                return True
            except discord.Forbidden:
                self.logger.warning(f"Missing permissions to delete message {message_id}")
                return False
            except discord.HTTPException as e:
                self.logger.error(f"Failed to delete message {message_id} due to HTTP error: {e}")
                return False
        except discord.NotFound:
             raise
        except Exception as e:
            self.logger.error(f"Unexpected error deleting message {message_id}: {e}")
            return False

    async def _load_tracking_data(self) -> dict:
        """Load all message tracking data"""
        if not os.path.exists(self.tracking_file):
            return {}
            
        try:
            with open(self.tracking_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            self.logger.warning(f"Corrupted tracking file. Creating new.")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading tracking data: {e}")
            return {}

    async def _save_tracking_data(self, data: dict) -> bool:
        """Save tracking data"""
        try:
            if data:
                with open(self.tracking_file, 'w') as f:
                    json.dump(data, f)
            elif os.path.exists(self.tracking_file):
                with open(self.tracking_file, 'w') as f:
                    json.dump({}, f)
            return True
        except Exception as e:
            self.logger.error(f"Error saving tracking data: {e}")
            return False