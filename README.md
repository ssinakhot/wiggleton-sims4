# Sims 4 + Twitch Mod

This mod was created out of a need to allow twitch users to be able to directly interact with the Sims 4 game without needing the streamer to do anything.
This works in conjunction with [wiggleton](https://github.com/ssinakhot/wiggleton) codebase.

## What this mod actually does?

The mod achieves connection to twitch by monitoring a folder for files to be dropped in. Once a file is detected, it will run the command that is specified in the file's content. Keep in mind, this can be used to literally run any sims 4 command since the execution command is `sims4.commands.execute`. After the file is processed, the file will be deleted to keep the folder clean.

## Additional Modifications

This mod was used in conjunction with S4MP mod. As a result, there were some fixes to the S4MP code to make the game more playable.

In addition, the built-in alone where not good enough to achieve all the possible interactions we wanted. As a result, we created some additional cheats such as

- buffs(target, true) - this will remove all a sims buffs
- modify_funds(amount) - this will allow you to increase or decrease funds
- set_motive_household(motive, amount) - this allows direct modifications of a specific motive (fun, social, hygiene, hunger, energy, or bladder) to a specific value for all sims
- randomize_motives_household() - this completely randomizes the household motives for all sims
- fill_motives_household - this fills all sims motives
- tank_motives_household - this sets all motives to their min value (sims can die due to this if you do not react fast enough)
