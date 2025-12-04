"""
Purpose: Automates Item counting for the total Items obtained daily and bounty

Vars Needed:
- start_time
- end_time = start_time + X hours
- team1_total
- team2_total
- start_msg_id
- sticky_msg_id
- sticky_msg_string

TODO: Have the bounty and daily plugin spawn and kill this process from their respective ones? Or should there be a help function elsewhere in bot maybe?
TODO: Update config sheet so that there is another column labelled (Total Drops?) and check if a X in it so we can distinguish the challenges without needing slash commands
TODO: sticky message "last counted image <link to comment id>"
TODO: Check both embed and attchments for each message for an image

Flow:
- Total item counter cog is always running and listens for start / end function calls
- when bounty or daily is served that is a total drops one
    - call totaldrop cog start(), pass in params
    - once new challenge is sent by bot, call totaldrop end() method and cleanup before ret of loop

Total Drop challenge detected in config sheet
    Search for the most recent bounty or daily message posted by the bot
    store the message ID in memory once found so we can use it on subsequent loops as a starting point
    Set process end time in memory
        if daily set for 24 hours from bot message post
        if bounty set for 8 hours from bot message post
    
    --- Main loop ---
    Every X seconds:
        Check if current time >= end time:
            if so kill process

        Reset team1 and team2 totals to 0
        Search starting from the bot message for messages containing image attachments
            If a message doesn't:
                skip
            If a message does:
                Check if it has a 'X' reaction
                    if it does then skip
                Check if it has a "Check" reaction
                    if it does, check the author's roles to determine what team they are on
                    increment team total respectivley
            
        Update sticky message string in memory
        Check if we have a sticky message ID in memory or not yet
            If not:
                then post sticky message
                Update sticky message ID in memory
            If we do:
                Check that the last message ID we retrieved matches the sticky ID in memory
                If not:
                    delete and repost message
                If so:
                    Update the message string
                    continue
"""