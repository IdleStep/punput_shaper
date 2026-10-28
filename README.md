# 🤣 Punput Shaper

A pun on Klipper's [input shaper](https://www.klipper3d.org/Resonance_Compensation.html): comedy for your printer, tuned for maximum comedic resonance.

**Punput Shaper periodically sends a joke to your Klipper console.** Jokes come from a built-in list of 3D printing puns (works offline) or from a free public joke API.

![Mainsail console after running PUNPUT_SHAPER twice, each run printing a printer pun](example_manual.png)

> ⚠️ **Requires** Klipper with the [`gcode_shell_command`](https://github.com/dw-0/kiauh/blob/master/docs/gcode_shell_command.md) extension installed, or [Kalico](https://docs.kalico.gg/G-Code_Shell_Command.html). Python 3 is also required, which Klipper hosts already have.

## Installation

1. Clone the repository into your Klipper config folder:

   ```bash
   git clone https://github.com/IdleStep/punput_shaper.git ~/printer_data/config/punput_shaper
   ```

2. Add this line to your `printer.cfg`:

   ```ini
   [include punput_shaper/punput_shaper.cfg]
   ```

3. *(Optional)* Add the following to your `moonraker.conf` to receive updates through Moonraker:

   ```ini
   [update_manager punput_shaper]
   type: git_repo
   origin: https://github.com/IdleStep/punput_shaper.git
   path: ~/printer_data/config/punput_shaper
   primary_branch: main
   is_system_service: False
   managed_services: klipper
   ```

4. *(Optional)* Hide the command log lines in Mainsail under **Settings → Console → Filters → Add Filter**:

   - **Name**: `PunputShaper`
   - **Regex**: `.*Command \{punput.*\}.*`

5. Restart Klipper.

The shell command assumes the standard KIAUH layout: Klipper in `~/klipper` and configs in `~/printer_data/config`.

## Configuration

The defaults live in `punput_shaper.cfg`. Don't edit that file, because it would conflict with updates. Instead, add a section to `printer.cfg` **after** the `[include]` line and list only the options you want to change:

```ini
[gcode_macro _PUNPUT_SHAPER_VARS]
variable_api: "local"
variable_loop_at_startup: True
variable_loop_duration: 900
variable_loop_drift: 30
variable_only_while_printing: True
```

| Variable | Default | Description |
| --- | --- | --- |
| `variable_api` | `"local"` | Joke source: `local`, `icanhazdadjoke`, `official`, `norris` or `jokeapi` (see [Joke sources](#joke-sources)) |
| `variable_loop_at_startup` | `True` | Start the joke loop when Klipper starts. If `False`, [start it manually](#usage) |
| `variable_loop_duration` | `900` | Seconds between jokes (900 = 15 minutes). Keep this long when using an online source to avoid hammering the API |
| `variable_loop_drift` | `30` | Random ± seconds added to each interval, so jokes don't arrive on a fixed beat |
| `variable_only_while_printing` | `True` | Only tell jokes while Klipper's `idle_timeout` state is `Printing`. This also covers homing, heating and macros, not just print jobs |

## Usage

Run these in the console, or call them from your own macros:

| Command | Effect |
| --- | --- |
| `PUNPUT_SHAPER` | Print one joke now |
| `UPDATE_DELAYED_GCODE ID=PUNPUT_SHAPER_LOOP DURATION=1` | Start the joke loop |
| `UPDATE_DELAYED_GCODE ID=PUNPUT_SHAPER_LOOP DURATION=0` | Stop the joke loop |

Starting the loop, letting it run, and stopping it again. This capture used `variable_loop_duration: 8`, `variable_loop_drift: 2` and `variable_only_while_printing: False` so it fits on one screen:

![Mainsail console showing the loop being started, three jokes arriving about eight seconds apart, and the loop being stopped](example_loop.png)

The `Running Command` and `finished` lines come from `gcode_shell_command`. The optional console filter from [Installation](#installation) hides them.

## Joke sources

| `variable_api` | Source | Notes |
| --- | --- | --- |
| `local` | [`punput.txt`](punput.txt) | 3D printing puns, one per line. Works offline. Add your own lines to the file |
| `icanhazdadjoke` | [icanhazdadjoke](https://icanhazdadjoke.com/) | Dad jokes |
| `official` | [Official Joke API](https://github.com/15Dkatz/official_joke_api) | Programming jokes |
| `jokeapi` | [JokeAPI](https://jokeapi.dev/) | Programming jokes with safe mode on |
| `norris` | [chucknorris.io](https://api.chucknorris.io/) | Chuck Norris facts. This API has no content filter |

Online sources need internet access from the printer's host and time out after 5 seconds.

To try a source without editing `printer.cfg`, set it from the console and run the macro. This change lasts until Klipper restarts:

```gcode
SET_GCODE_VARIABLE MACRO=_PUNPUT_SHAPER_VARS VARIABLE=api VALUE='"jokeapi"'
PUNPUT_SHAPER
```

![Mainsail console running PUNPUT_SHAPER with the icanhazdadjoke, official and jokeapi sources in turn](example_sources.png)

## Troubleshooting

Run the script by hand to see any error. Replace `local` with the source you use:

```bash
python3 ~/printer_data/config/punput_shaper/punput_shaper.py local
```

If the script works but nothing appears in the console, make sure `gcode_shell_command` is installed and Klipper was restarted.

## Upgrading from punput_shaping

The project was renamed from `punput_shaping` to `punput_shaper`, and the macros were renamed to match. To update an existing install:

1. Move the folder and point Git at the new name:

   ```bash
   mv ~/printer_data/config/punput_shaping ~/printer_data/config/punput_shaper
   git -C ~/printer_data/config/punput_shaper remote set-url origin https://github.com/IdleStep/punput_shaper.git
   git -C ~/printer_data/config/punput_shaper pull
   ```

2. In `printer.cfg`, change the include to `[include punput_shaper/punput_shaper.cfg]` and rename your override section to `[gcode_macro _PUNPUT_SHAPER_VARS]`. The `variable_*` names are unchanged.
3. In `moonraker.conf`, rename the section to `[update_manager punput_shaper]` and update `origin` and `path` as shown in [Installation](#installation).
4. Restart Moonraker and Klipper.

The macros are now `PUNPUT_SHAPER`, `PUNPUT_SHAPER_LOOP` and `PUNPUT_SHAPER_STARTUP`. Update any of your own macros that call the old names.

## License

[GPL-3.0](LICENSE)
