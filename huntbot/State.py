import os
import yaml
import logging

logger = logging.getLogger(__name__)


class State:
    def __init__(self):
        self.state_file = "conf/state.yaml"
        self.state_data = {}

    def update_state(self, cog: bool = False, bot: bool = False, **kwargs):
        if bot:
            if 'bot' not in self.state_data:
                self.state_data['bot'] = {}
            self.state_data['bot'].update(kwargs)

        if cog:
            if 'cog' not in self.state_data:
                self.state_data['cog'] = {}
            self.state_data['cog'].update(kwargs)

        # Write updated data back to the file
        with open(self.state_file, 'w') as file:
            yaml.safe_dump(self.state_data, file, default_flow_style=False)

    def load_state(self):
        # Load existing data if file exists
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as file:
                try:
                    self.state_data = yaml.safe_load(file) or {}
                except yaml.YAMLError as e:
                    raise ValueError(f"Error reading YAML file: {e}")
        else:
            logger.error(f"No State file found at: {self.state_file}")
