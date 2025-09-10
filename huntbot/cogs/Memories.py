from discord.ext import commands, tasks
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import ConfigurationException
import logging
import random
import re
import yaml
from typing import Union
import time

logger = logging.getLogger(__name__)

class MemoriesCog(commands.Cog):
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.general_channel_id = 0
        self.memories_filepath = "conf/memories.yaml"
        self.memories = []

        # Empty iterator fornow, will populate during setup
        self.memory_iterator = iter(self.memories)

        self.minimum_memory_age_ms = 28800000 # 8 hours in milliseconds
        self.maximum_memory_age_ms = 43200000  # 12 hours in milliseconds
        self.current_time_ms = int(time.time() * 1000)
        self.next_memory_post_time_ms = self.current_time_ms + random.randint(self.minimum_memory_age_ms, self.maximum_memory_age_ms)

    async def cog_load(self) -> None:
        """
        Asynchronously loads the cog, retrieves configuration, loads memories from file,
        waits until the bot is ready, and starts the memory posting task loop.
        """
        try:
            self.get_general_channel()
            self.load_memories_from_file()
            logger.info(f"[Memories Cog] Loaded {len(self.memories)} memories")
            await self.discord_bot.wait_until_ready()
            self.start_memories.start()
        except Exception as e:
            logger.error("Setup failed", exc_info=e)

    def cog_unload(self) -> None:
        """
        Cancels the running task loop when the cog is unloaded.
        """
        self.start_memories.cancel()

    def get_general_channel(self) -> None:
        """
        Retrieves and sets the general channel ID from the HuntBot configuration.
        
        Raises:
            ConfigurationException: If the GENERAL_CHANNEL_ID is missing or invalid.
        """

        self.general_channel_id = int(self.hunt_bot.config_map.get('GENERAL_CHANNEL_ID', "0"))
        if self.general_channel_id == 0:
            logger.error("[Memories Cog] GENERAL_CHANNEL_ID not found")
            raise ConfigurationException(config_key='GENERAL_CHANNEL_ID')

    def load_memories_from_file(self) -> None:
        """
        Loads memory entries from the YAML file, shuffles them, and creates a new iterator.
        
        Logs an error if no memories are found.
        """
        with open(self.memories_filepath, 'r') as file:
            data = yaml.safe_load(file)

        self.memories = data.get('memories', [])

        if not self.memories:
            logger.error("[Memories Cog] No memories found in the file.")
        else:
            # Shuffle the memories list randommly
            random.shuffle(self.memories)
            self.memory_iterator = iter(self.memories)

    def load_next_memory(self) -> Union[str, None]:
        """
        Retrieves the next memory from the iterator, formats it with attribution if present,
        and returns the formatted memory message.
        
        Returns:
            str | None: The formatted memory string, or None if no more memories are available.
        """

        try:
            memory = next(self.memory_iterator)

            # Try to extract the player name from the end of the memory string
            match = re.search(r'\s-\s(.+)$', memory)
            if match:
                player = match.group(1).strip()
                memory_text = memory[:match.start()].strip()
            else:
                player = "Unknown"
                memory_text = memory.strip()

            memory_message = f'"{memory_text}"\n\n— {player}'
            return memory_message
        
        except StopIteration:
            logger.info("[Memories Cog] No more memories to load.")
            return None
        
        except Exception as e:
            logger.error("[Memories Cog] Error loading next memory.", exc_info=e)
            return None

    @tasks.loop(seconds=60)
    async def start_memories(self) -> None:
        """
        Periodic task that checks if it's time to post the next memory.
        
        If so, retrieves and sends the next memory to the configured channel, and schedules
        the next posting time. Stops the loop if no more memories are available or errors occur.
        """
        # Update current time in milliseconds
        self.current_time_ms = int(time.time() * 1000)

        channel = self.discord_bot.get_channel(self.general_channel_id)
        
        if not channel:
            logger.error("[Memories Cog] General Channel not found.")
            return

        try:
            # Current time is less than the next memory posting time, so do nothing this iteration
            if self.current_time_ms < self.next_memory_post_time_ms:
                return
            
            # Otherwise it is time to post the memory and fetch the next one
            else:
                memory_message = self.load_next_memory()

                # If we retrieve nothing from the function, then do nothing this iteration
                if memory_message is None:
                    # Stop the process loop
                    self.start_memories.stop()
                    return
                
                # Otherwise we did get a memory. post it, and generate next memory posting time
                else:
                    await channel.send(memory_message)
                    self.next_memory_post_time_ms = self.current_time_ms + random.randint(self.minimum_memory_age_ms, self.maximum_memory_age_ms)

        except Exception as e:
            logger.error("[Memories Cog] Error during task loop", exc_info=e)
            self.start_memories.stop()
