# Hunt-Bot
A Discord bot to help automate The Hunt

## Slash Commands
### All Hunt Participants
Commands available to anyone participating in the hunt.

- `/bounty` — Shows the current active bounty and its description.
- `/daily` — Shows the current active daily challenge.
- `/countdown` — Displays the time remaining until the hunt begins or ends.
- `/score` — Displays the current hunt score.
- `/list_team_bounties` — Lists all currently active team item bounties.
- `/beep` — Test command that replies with “Boop”.
- `/passwords` — Displays the current hunt passwords.

### Hunt Captains
Commands available to the Hunt Captains.

- `/create_team_bounty item_name:<name> reward_amount:<amount> time_limit_hours:<hours>` — Creates a new team item bounty with an optional time limit.
- `/close_team_bounty item_name:<name> completed_by:<user>` — Closes a team item bounty early and records who completed it.
- `/update_team_bounty item_name:<name> reward_amount:<amount> time_limit_hours:<hours>` — Updates the reward amount and/or time limit for an existing team item bounty.

### Hunt Staff
Commands that require staff/admin permissions.

- `/sheet sheet_id:<id>` — Configures the bot with the Google Sheet ID and configuration tables used for the hunt.
- `/start-hunt` — Starts the hunt bot and begins the hunt logic loop at the configured start time.
- `/update_bounty_image image_url:<url>` — Updates the embedded image in the current bounty message.
- `/update_bounty_description new_description:<text>` — Updates the description in the current bounty message.
- `/update_daily_image image_url:<url>` — Updates the embedded image in the current daily message.
- `/update_daily_description new_description:<text>` — Updates the description in the current daily message.
