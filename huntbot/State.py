import os
import yaml
import logging
from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)


class State:
    def __init__(self):
        self.state_file = "../conf/state.yaml"
        self.lock_file = self.state_file + ".lock"
        self.lock_timeout = 5  # seconds
        self.state_data = {}
        self._init_state_file()

    def _init_state_file(self):
        # Check if state file exists
        if not os.path.exists(self.state_file):
            logger.warning(f"No state file found at: {self.state_file}")
            # Create an empty YAML file
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                yaml.safe_dump({}, f)
            logger.info(f"Created new empty state file at {self.state_file}")
            self.state_data = {}
        else:
            logger.info("State file found")
            # Load existing state data
            try:
                with open(self.state_file, 'r') as f:
                    self.state_data = yaml.safe_load(f)
                logger.info(f"Loaded state from {self.state_file}")
                logger.info(self.state_data)
            except yaml.YAMLError as e:
                logger.error(f"Failed to load YAML from {self.state_file}: {e}")
                self.state_data = {}

    async def update_state(self, cog: bool = False, bot: bool = False, **kwargs):
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
        except Timeout:
            logger.error("Could not acquire state lock within timeout.")
            raise

    async def load_state(self):
        """Load the state with a lock to prevent partial reads."""
        lock = FileLock(self.lock_file, timeout=self.lock_timeout)
        try:
            with lock:
                self._load_state_locked()
        except Timeout:
            logger.error("Could not acquire lock to load state.")
            raise

    def _load_state_locked(self):
        """Internal function to read state file. Call only with lock held."""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as file:
                try:
                    self.state_data = yaml.safe_load(file)
                except yaml.YAMLError as e:
                    raise ValueError(f"Error reading YAML file: {e}")
        else:
            logger.warning(f"No state file found at: {self.state_file}")
            self.state_data = {}

    def _write_state_locked(self):
        """Internal function to write state file. Call only with lock held."""
        with open(self.state_file, 'w') as file:
            yaml.safe_dump(self.state_data, file, default_flow_style=False)


if __name__ == '__main__':
    state = State()
    print(state.state_data)
