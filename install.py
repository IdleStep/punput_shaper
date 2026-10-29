#!/usr/bin/env python3
"""Install or remove Punput Shaper as a Klipper/Kalico plugin.

Run it from the cloned repository:

    python3 install.py              install (safe to run again)
    python3 install.py -u           uninstall
    python3 install.py -n           show what would change and change nothing

It backs up printer.cfg and moonraker.conf, adds a [punput_shaper] section to printer.cfg and
an update_manager entry to moonraker.conf, links punput_shaper.py into Klipper, and restarts
Moonraker and Klipper unless a print is running or paused.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.realpath(__file__))
MODULE = "punput_shaper.py"
BEGIN = "# >>> punput_shaper (added by install.py)"
END = "# <<< punput_shaper"
DEFAULT_ORIGIN = "https://github.com/IdleStep/punput_shaper.git"
SAVE_CONFIG = "#*# <---------------------- SAVE_CONFIG"
HEADER = re.compile(r"^\[([^\]]+)\]")
# The setup from before Punput Shaper was a plugin. It defines the same G-code command.
OLD_STYLE = re.compile(
    r"^\s*\[(include\s+punput_shap(er|ing)/punput_shaper\.cfg|gcode_macro\s+_punput_?shap(er|ing)_vars)\s*\]",
    re.I | re.M)
DEFAULTS = [
    ("source", "local", "local, icanhazdadjoke, official, jokeapi, pun, uselessfacts, adviceslip, corporatebs, norris"),
    ("loop_at_startup", "True", "start the joke loop when Klipper starts"),
    ("loop_duration", "900", "seconds between jokes"),
    ("loop_drift", "30", "random +/- seconds added to each interval"),
    ("only_while_printing", "True", ""),
]


# --- text edits (pure functions, so they can be tested without a printer) ---

def section_name(line):
    match = HEADER.match(line)
    return match.group(1).strip().lower() if match else None


def new_section():
    lines = [BEGIN, "[punput_shaper]"]
    for name, default, comment in DEFAULTS:
        line = "%s: %s" % (name, default)
        if comment:
            line = line.ljust(24) + "# " + comment
        lines.append(line)
    lines.append(END)
    return lines


def edit_printer_cfg(text):
    """Return (new text, notes): add [punput_shaper] above the SAVE_CONFIG block unless it is there."""
    lines = text.split("\n")
    trailing_newline = lines[-1] == ""
    if trailing_newline:
        lines.pop()
    end = next((i for i, line in enumerate(lines) if line.startswith(SAVE_CONFIG)), len(lines))
    body, tail = lines[:end], lines[end:]
    if any(section_name(line) == "punput_shaper" for line in body):
        return text, ["printer.cfg already has a [punput_shaper] section"]
    while body and body[-1].strip() == "":
        body.pop()
    body += [""] + new_section()
    if tail:
        body.append("")
    return "\n".join(body + tail) + ("\n" if trailing_newline else ""), ["added a [punput_shaper] section"]


def edit_moonraker(text, path, origin):
    """Add [update_manager punput_shaper] unless moonraker.conf has one; return (new text, notes)."""
    lines = text.split("\n")
    if any(section_name(line) == "update_manager punput_shaper" for line in lines):
        return text, ["already has an [update_manager punput_shaper] section; left as it is "
                      "(if you moved the clone, fix its path by hand)"]
    block = ["", BEGIN, "[update_manager punput_shaper]", "type: git_repo", "path: %s" % path,
             "origin: %s" % origin, "primary_branch: main", "managed_services: klipper", END]
    while lines and lines[-1].strip() == "":
        lines.pop()
    return "\n".join(lines + block) + "\n", ["added [update_manager punput_shaper]"]


def remove_block(text):
    """Remove the block this installer added, if it is still there."""
    pattern = re.compile(r"\n?%s\n.*?\n%s\n?" % (re.escape(BEGIN), re.escape(END)), re.S)
    return pattern.sub("", text, count=1)


# --- the installer ---

class Installer:
    def __init__(self, args):
        self.args = args
        self.dry = args.dry_run
        self.klipper = os.path.expanduser(args.klipper_dir)
        self.config_dir = os.path.expanduser(args.config_dir)
        self.printer_cfg = os.path.join(self.config_dir, "printer.cfg")
        self.moonraker_conf = os.path.join(self.config_dir, "moonraker.conf")
        plugins = os.path.join(self.klipper, "klippy", "plugins")
        self.module_dir = plugins if os.path.isdir(plugins) else os.path.join(self.klipper, "klippy", "extras")
        self.module_link = os.path.join(self.module_dir, MODULE)
        self.changed = False

    def say(self, message):
        print(("[dry run] " if self.dry else "") + message)

    def check(self, remove):
        """Stop before changing anything if the install could not work."""
        if os.geteuid() == 0:
            sys.exit("Run this as your normal user, not root: it edits your config and links into Klipper.")
        if not os.path.isdir(os.path.join(self.klipper, "klippy")):
            sys.exit("Klipper was not found in %s. Use -k to point at it." % self.klipper)
        if not os.path.isfile(os.path.join(REPO, MODULE)):
            sys.exit("%s is missing from %s" % (MODULE, REPO))
        if remove:
            return
        if os.path.lexists(self.module_link) and not os.path.islink(self.module_link):
            sys.exit("%s exists and is not a link; not touching it" % self.module_link)
        if os.path.exists(self.printer_cfg) and OLD_STYLE.search(open(self.printer_cfg).read()):
            sys.exit("printer.cfg still has the older Punput Shaper setup ([include punput_shaper/"
                     "punput_shaper.cfg] or [gcode_macro _PUNPUT_SHAPER_VARS]). It defines the same "
                     "PUNPUT_SHAPER command as the plugin, so remove those lines and run this again.")

    def link(self, remove):
        source = os.path.join(REPO, MODULE)
        exists = os.path.islink(self.module_link)
        if remove:
            if exists:
                self.say("removing link %s" % self.module_link)
                if not self.dry:
                    os.remove(self.module_link)
                self.changed = True
            return
        if exists and os.path.realpath(self.module_link) == source:
            self.say("module already linked in %s" % self.module_dir)
            return
        self.say("linking %s -> %s" % (self.module_link, source))
        if not self.dry:
            if exists:
                os.remove(self.module_link)
            os.symlink(source, self.module_link)
        self.changed = True

    def git_exclude(self):
        """Hide the link from Klipper's git status. Uninstall leaves the entry; it does no harm."""
        info = os.path.join(self.klipper, ".git", "info")
        entry = os.path.relpath(self.module_link, self.klipper)
        exclude = os.path.join(info, "exclude")
        if not os.path.isdir(info):
            return
        current = open(exclude).read() if os.path.exists(exclude) else ""
        if entry not in current.split("\n"):
            self.say("hiding the link from Klipper's git status (.git/info/exclude)")
            if not self.dry:
                with open(exclude, "a") as f:
                    f.write(("" if current.endswith("\n") or not current else "\n") + entry + "\n")

    def edit_file(self, path, editor, label):
        if not os.path.exists(path):
            return None
        with open(path) as f:
            old = f.read()
        new, notes = editor(old)
        for note in notes:
            self.say("%s: %s" % (label, note))
        if new != old:
            backup = path + ".before-punput-shaper"
            if not os.path.exists(backup):  # keep the first one: it is the file as you had it
                self.say("backing up %s to %s" % (os.path.basename(path), os.path.basename(backup)))
                if not self.dry:
                    shutil.copy2(path, backup)
            if not self.dry:
                with open(path, "w") as f:
                    f.write(new)
            self.changed = True
            return True
        return False

    def configs(self, remove):
        if not os.path.exists(self.printer_cfg):
            self.say("no printer.cfg at %s; add the section by hand (see README.md)" % self.printer_cfg)
        elif remove:
            self.edit_file(self.printer_cfg, lambda t: (remove_block(t), [
                "removed the [punput_shaper] block" if BEGIN in t else
                "no block added by install.py; delete [punput_shaper] by hand if you want it gone"]), "printer.cfg")
        else:
            self.edit_file(self.printer_cfg, edit_printer_cfg, "printer.cfg")
        if not os.path.exists(self.moonraker_conf):
            self.say("no moonraker.conf at %s; skipping the update_manager entry" % self.moonraker_conf)
            return
        if remove:
            self.edit_file(self.moonraker_conf, lambda t: (remove_block(t), [
                "removed the update_manager block" if BEGIN in t else
                "no block added by install.py; delete [update_manager punput_shaper] by hand if you want it gone"]),
                           "moonraker.conf")
            return
        home = os.path.expanduser("~")
        path = REPO.replace(home, "~", 1) if REPO.startswith(home + os.sep) else REPO
        origin = subprocess.run(["git", "-C", REPO, "remote", "get-url", "origin"], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, universal_newlines=True).stdout.strip() or DEFAULT_ORIGIN
        self.edit_file(self.moonraker_conf, lambda t: edit_moonraker(t, path, origin), "moonraker.conf")

    def api(self, path, post=False):
        request = urllib.request.Request(self.args.moonraker_url + path, method="POST" if post else "GET")
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def restart(self):
        if not self.changed:
            self.say("nothing changed, so nothing was restarted")
            return
        if self.args.no_restart or self.dry:
            self.say("not restarting; restart Moonraker and Klipper yourself to load the changes")
            return
        try:
            state = self.api("/printer/objects/query?print_stats")["result"]["status"]["print_stats"]["state"]
        except (urllib.error.URLError, OSError, KeyError, ValueError) as e:
            print("Could not read the print state from Moonraker at %s (%s). Restart Moonraker and Klipper "
                  "yourself." % (self.args.moonraker_url, e))
            return
        if state in ("printing", "paused"):
            print("A print is running or paused, so nothing was restarted. Restart Klipper when it is done.")
            return
        print("restarting Moonraker, then Klipper")
        try:
            self.api("/machine/services/restart?service=moonraker", post=True)
            for _ in range(30):
                time.sleep(1)
                try:
                    self.api("/server/info")
                    break
                except (urllib.error.URLError, OSError, ValueError):
                    continue
            self.api("/machine/services/restart?service=klipper", post=True)
        except (urllib.error.URLError, OSError, ValueError) as e:
            print("Restart failed (%s). Restart Moonraker and Klipper yourself." % e)

    def run(self, remove):
        self.check(remove)
        # Install links the module before editing the configs, so a failure never leaves a config
        # that names a module Klipper cannot load. Uninstall does the reverse.
        if remove:
            self.configs(remove)
        self.link(remove)
        if not remove:
            self.git_exclude()
            self.configs(remove)
        self.restart()
        if remove:
            print("\nPunput Shaper is removed. The clone in %s is still there; delete it if you like." % REPO)
        else:
            print("\nDone. In the console, try:  PUNPUT_SHAPER   (and PUNPUT_SHAPER SOURCE=pun)")


def main():
    parser = argparse.ArgumentParser(description="Install or remove Punput Shaper as a Klipper/Kalico plugin.")
    parser.add_argument("-k", "--klipper-dir", default="~/klipper", help="Klipper directory (default ~/klipper)")
    parser.add_argument("-c", "--config-dir", default="~/printer_data/config",
                        help="config directory (default ~/printer_data/config)")
    parser.add_argument("--moonraker-url", default="http://localhost:7125", help="Moonraker address")
    parser.add_argument("-u", "--uninstall", action="store_true", help="remove Punput Shaper")
    parser.add_argument("-n", "--dry-run", action="store_true", help="show what would change, change nothing")
    parser.add_argument("-r", "--no-restart", action="store_true", help="do not restart Moonraker and Klipper")
    args = parser.parse_args()
    Installer(args).run(args.uninstall)


if __name__ == "__main__":
    main()
