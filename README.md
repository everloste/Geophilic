![Cool logo.](https://i.imgur.com/yJbL99N.png) 

## Updating biome definitions
Since biome definitions can (and do, especially nowadays) vary from minor version to minor version, Geophilic uses a script to create them automatically.
This prevents bugs that arise from forgetting to add a new feature to the list or a new mob to spawns, which was a pain to do anyway, not to mention fairly regular changes to the JSON structure.

Geophilic's new biome definitions are created from what I call *biome overlays*.
Those are stored in `.dev/biome overlays`.
They can be version specific.

The script needs to be ran on your system.
The main prerequisite is that you have Minecraft installed, as the script pulls vanilla files from there.
I use Prism Launcher, so that's what I've written it for, but you can easily change that.

## Notes
While I doubt it will be of use to anyone else, all Python code in this repository is licensed under the [MIT License](https://opensource.org/license/MIT).
