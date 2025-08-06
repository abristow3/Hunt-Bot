import os
import yaml
import logging
from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)

class State:
    def __init__(self, state_file: str = "conf/state.yaml", lock_timeout: int = 5) -> None:
        self.state_file = state_file
        self.lock_file = self.state_file + ".lock"
        self.lock_timeout = lock_timeout
        self.state_data = {}
        self._init_state_file()

    def _init_state_file(self) -> None:
        # Check if state file exists
        if not os.path.exists(self.state_file):
            logger.warning(f"[STATE] No state file found at: {self.state_file}")

            # Create an empty YAML file
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            self.state_data = {"bot": {}, "cogs": {}}
            with open(self.state_file, 'w') as f:
                yaml.safe_dump(self.state_data, f)
            logger.info(f"[STATE] Created new empty state file at {self.state_file}")
        else:
            logger.info("[STATE] State file found")
            # Load existing state data
            try:
                with open(self.state_file, 'r') as f:
                    self.state_data = yaml.safe_load(f)
                logger.info(f"[STATE] Loaded state from {self.state_file}")
                logger.info(self.state_data)
            except yaml.YAMLError as e:
                logger.error(f"[STATE] Failed to load YAML from {self.state_file}: {e}")
                self.state_data = {"bot": {}, "cogs": {}}

    async def update_state(self, cog: bool = False, bot: bool = False, **kwargs) -> None:
        """Safely update the YAML state file using a lock."""
        lock = FileLock(self.lock_file, timeout=self.lock_timeout)
        try:
            with lock:
                self._load_state_locked()

                if bot:
                    if 'bot' not in self.state_data:
                        self.state_data['bot'] = {}
                    self.state_data['bot'].update(kwargs)

                if cog:
                    if 'cogs' not in self.state_data:
                        self.state_data['cogs'] = {}
                    self.state_data['cogs'].update(kwargs)

                self._write_state_locked()
                logger.info("[STATE] State Updated")
        except Timeout:
            logger.error("[STATE] Could not acquire state lock within timeout.")
            raise

    async def load_state(self) -> None:
        """Load the state with a lock to prevent partial reads."""
        lock = FileLock(self.lock_file, timeout=self.lock_timeout)
        try:
            with lock:
                self._load_state_locked()
        except Timeout:
            logger.error("[STATE] Could not acquire lock to load state.")
            raise

    def _load_state_locked(self) -> None:
        """Internal function to read state file. Call only with lock held."""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as file:
                try:
                    self.state_data = yaml.safe_load(file)
                    if self.state_data is None:
                        self.state_data = {"bot": {}, "cogs": {}}
                except yaml.YAMLError as e:
                    raise ValueError(f"[STATE] Error reading YAML file: {e}")
        else:
            logger.warning(f"[STATE] No state file found at: {self.state_file}")
            self.state_data = {"bot": {}, "cogs": {}}

    def _write_state_locked(self) -> None:
        """Internal function to write state file. Call only with lock held."""
        with open(self.state_file, 'w') as file:
            yaml.safe_dump(self.state_data, file, default_flow_style=False)

