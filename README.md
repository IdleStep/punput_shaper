# 🤣 Punput Shaper

A pun on Klipper's [input shaper](https://www.klipper3d.org/Resonance_Compensation.html): comedy for your printer, tuned for maximum comedic resonance.

**Punput Shaper periodically sends a joke to your Klipper console.** Jokes come from a built-in list of 3D printing puns (works offline) or from a free public joke, fact or advice API.

> ⚠️ **Requires** [Kalico](https://docs.kalico.gg/) or [Klipper](https://www.klipper3d.org/), with Moonraker for updates. Punput Shaper is a Klipper host module and needs nothing else installed.

## Installation

Run this on your printer's host:

```bash
cd ~ && git clone https://github.com/IdleStep/punput_shaper.git && python3 punput_shaper/install.py
```

The installer is safe to run again. In this order, it:

1. links `punput_shaper.py` into Klipper (`klippy/plugins` on Kalico, `klippy/extras` on Klipper) and keeps it out of Klipper's `git status`
2. backs up `printer.cfg` and `moonraker.conf` once, as `printer.cfg.before-punput-shaper` and `moonraker.conf.before-punput-shaper`
3. adds a `[punput_shaper]` section to `printer.cfg`, before the `SAVE_CONFIG` block
4. adds an `[update_manager punput_shaper]` section to `moonraker.conf`, so Moonraker updates it and restarts Klipper afterwards
5. restarts Moonraker and Klipper, unless a print is running or paused

Add these options to the command, for example `python3 punput_shaper/install.py -n`:

| Option | Effect |
| --- | --- |
| `-n`, `--dry-run` | Show what would change, and change nothing |
| `-r`, `--no-restart` | Don't restart Moonraker and Klipper |
| `-u`, `--uninstall` | Remove Punput Shaper |
| `-k`, `--klipper-dir` | Klipper directory, if it isn't `~/klipper` |
| `-c`, `--config-dir` | Config directory, if it isn't `~/printer_data/config` |
| `--moonraker-url` | Moonraker's address, if it isn't `http://localhost:7125` |

<details>
<summary>Install by hand</summary>

1. Clone the repository anywhere, for example `git clone https://github.com/IdleStep/punput_shaper.git ~/punput_shaper`.
2. Link the module into Klipper, using `plugins` instead of `extras` on Kalico:

   ```bash
   ln -s ~/punput_shaper/punput_shaper.py ~/klipper/klippy/extras/punput_shaper.py
   ```

3. Add this to `printer.cfg`, above the `SAVE_CONFIG` block:

   ```ini
   [punput_shaper]
   ```

4. Add this to `moonraker.conf` to receive updates:

   ```ini
   [update_manager punput_shaper]
   type: git_repo
   path: ~/punput_shaper
   origin: https://github.com/IdleStep/punput_shaper.git
   primary_branch: main
   managed_services: klipper
   ```

5. Restart Moonraker and Klipper.

</details>

## Configuration

Set these in the `[punput_shaper]` section of `printer.cfg`:

```ini
[punput_shaper]
source: local
loop_at_startup: True
loop_duration: 900
loop_drift: 30
only_while_printing: True
```

| Option | Default | Description |
| --- | --- | --- |
| `source` | `local` | Joke source: `local`, `icanhazdadjoke`, `official`, `jokeapi`, `pun`, `uselessfacts`, `adviceslip`, `corporatebs` or `norris` (see [Joke sources](#joke-sources)) |
| `loop_at_startup` | `True` | Start the joke loop when Klipper starts. If `False`, [start it manually](#usage) |
| `loop_duration` | `900` | Seconds between jokes (900 = 15 minutes). Keep this long when using an online source to avoid hammering the API |
| `loop_drift` | `30` | Random ± seconds added to each interval, so jokes don't arrive on a fixed beat |
| `only_while_printing` | `True` | Only tell jokes while Klipper's `idle_timeout` state is `Printing`. This also covers homing, heating and macros, not just print jobs |

## Usage

Run these in the console, or call them from your own macros:

| Command | Effect |
| --- | --- |
| `PUNPUT_SHAPER` | Print one joke now |
| `PUNPUT_SHAPER SOURCE=pun` | Print one joke from another source, without changing the configuration |
| `PUNPUT_SHAPER_START` | Start the joke loop |
| `PUNPUT_SHAPER_STOP` | Stop the joke loop |

![Mainsail console showing the loop being started, three jokes arriving about eight seconds apart, and the loop being stopped](example_loop.png)

The newest message is at the top, so each command sits below its joke.

## Joke sources

| `source` | Source | Notes |
| --- | --- | --- |
| `local` | [`punput.txt`](punput.txt) | 3D printing puns, one per line. Works offline. Add your own lines to the file |
| `icanhazdadjoke` | [icanhazdadjoke](https://icanhazdadjoke.com/) | Dad jokes |
| `official` | [Official Joke API](https://github.com/15Dkatz/official_joke_api) | Programming jokes |
| `jokeapi` | [JokeAPI](https://jokeapi.dev/) | Programming jokes with safe mode on |
| `pun` | [JokeAPI](https://jokeapi.dev/) | Puns, one-liners and two-parters, with safe mode on. About 45 to choose from, so expect repeats over a long day |
| `uselessfacts` | [Useless Facts](https://uselessfacts.jsph.pl/) | Random "useless but true" facts. Can include adult topics and language |
| `adviceslip` | [Advice Slip](https://api.adviceslip.com/) | Short pieces of everyday advice, from "Always the burrito." to jar-opening tips |
| `corporatebs` | [Corporate BS Generator](https://github.com/sameerkumar18/corporate-bs-generator-api) | Made-up corporate buzzword phrases like "Dynamically Visualize Synergistic Systems" |
| `norris` | [chucknorris.io](https://api.chucknorris.io/) | Chuck Norris facts. Includes adult language and crude humor |

Online sources need internet access from the printer's host. Jokes are fetched in the background, so a slow or unreachable API never holds up your printer.

To try a source without editing `printer.cfg`, name it in the command, for example `PUNPUT_SHAPER SOURCE=pun`.

## Troubleshooting

If `[punput_shaper]` is reported as an unknown section, the module isn't linked into Klipper. Run `python3 punput_shaper/install.py` again and restart Klipper.

If you move the clone, fix `path:` in the `[update_manager punput_shaper]` section of `moonraker.conf` and run the installer again. The installer doesn't change a section that is already there.

If jokes don't appear, look for the module's messages in the Klipper log:

```bash
grep -i punput ~/printer_data/logs/klippy.log
```

A joke that can't be fetched is reported in the console, for example `could not get a joke from 'pun'`, and the next one is tried at the usual time.

## License

[GPL-3.0](LICENSE)
