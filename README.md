# Hunt-Bot
A Discord bot to help automate The Hunt

## Commands

- `/beep` - Health check, should respond back with boop if the bot is online and healthy
- `/sheet` - Used to supply the hunt bot with a GDoc sheet ID, optionally can also set the sheet_name and config_table name.
If they are not provided then the sheet_name will default to "BotConfig" and the config_table will default to "Discord Conf"
- `/start-hunt` - Starts the hunt process. The bot will wait until the start date and time to begin posting daileis, bounties,
score. The starboard plugin will be available as soon as the command is run.



