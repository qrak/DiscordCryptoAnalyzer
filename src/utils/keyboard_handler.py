import asyncio
import sys
from typing import Dict, Callable, Awaitable, Optional, Tuple

from src.logger.logger import Logger

# Platform-specific imports
if sys.platform == "win32":
    import msvcrt
else:
    import select
    import tty
    import termios


class KeyboardHandler:
    """Handles keyboard input for console commands"""
    
    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the keyboard handler
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger
        self.running = False
        self._commands: Dict[str, Tuple[Callable, str]] = {}
        self._listening_task = None
    
    def register_command(self, key: str, callback: Callable[[], Awaitable], description: str) -> None:
        """Register a keyboard command
        
        Args:
            key: Single character key that triggers the command
            callback: Async function to call when key is pressed
            description: Description of what the command does
        """
        if len(key) != 1:
            raise ValueError("Key must be a single character")
        
        self._commands[key.lower()] = (callback, description)
        
    async def start_listening(self) -> None:
        """Start listening for keyboard input"""
        if self.running:
            return
            
        self.running = True
        
        if self.logger:
            self.logger.debug("Keyboard handler started")
            
        while self.running:
            try:
                await self._process_keyboard_input()
                await asyncio.sleep(0.1)  # Prevent CPU hogging
                
            except asyncio.CancelledError:
                if self.logger:
                    self.logger.debug("Keyboard listener task cancelled")
                break
            except Exception as e:
                await self._handle_keyboard_error(e)

    async def _process_keyboard_input(self) -> None:
        """Process keyboard input if available."""
        if not self._has_input():
            return
            
        key = self._read_key()
        if key and key in self._commands:
            await self._execute_command(key)

    def _has_input(self) -> bool:
        """Check if keyboard input is available."""
        if sys.platform == "win32":
            return msvcrt.kbhit()
        else:
            # Linux/Unix implementation using select
            return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

    def _read_key(self) -> Optional[str]:
        """Read a single character from keyboard input."""
        try:
            if sys.platform == "win32":
                return msvcrt.getch().decode('utf-8', errors='ignore').lower()
            else:
                # Linux/Unix implementation
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setraw(sys.stdin.fileno())
                    char = sys.stdin.read(1)
                    return char.lower() if char else None
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception:
            return None

    async def _execute_command(self, key: str) -> None:
        """Execute a keyboard command."""
        callback, description = self._commands[key]
        try:
            await callback()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error executing keyboard command '{key}': {e}")

    async def _handle_keyboard_error(self, error: Exception) -> None:
        """Handle errors in keyboard processing."""
        if self.logger:
            self.logger.error(f"Error in keyboard handler: {error}")
        await asyncio.sleep(1)  # Longer sleep on error
    
    async def stop_listening(self) -> None:
        """Stop listening for keyboard input"""
        self.running = False
        
        if self._listening_task and not self._listening_task.done():
            self._listening_task.cancel()
            try:
                await self._listening_task
            except asyncio.CancelledError:
                pass
            
        if self.logger:
            self.logger.debug("Keyboard handler stopped")
            
    def display_help(self) -> None:
        """Display available keyboard commands"""
        for key, (_, description) in sorted(self._commands.items()):
            if self.logger:
                self.logger.info(f"  '{key}' - {description}")
            else:
                print(f"  '{key}' - {description}")
