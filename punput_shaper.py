# Punput Shaper: jokes, puns, facts and advice for the Klipper console.
# https://github.com/IdleStep/punput_shaper
#
# A Klipper/Kalico host module. Add a [punput_shaper] section to printer.cfg to load it.
# This file may be distributed under the terms of the GNU GPLv3 license.
import json
import logging
import os
import random
import threading
import time
import urllib.request

USER_AGENT = "punput_shaper (https://github.com/IdleStep/punput_shaper)"
TIMEOUT = 4  # seconds per socket operation
DEADLINE = 10  # seconds for a whole request, so a trickling server cannot hold the worker
MAX_BYTES = 65536
# The module is linked into Klipper, so look next to the real file for the joke list.
LOCAL_JOKES = os.path.join(os.path.dirname(os.path.realpath(__file__)), "punput.txt")


def fetch_json(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    deadline = time.monotonic() + DEADLINE
    body = b""
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        while len(body) < MAX_BYTES and time.monotonic() < deadline:
            chunk = response.read1(4096)  # what has arrived so far, so the deadline gets checked
            if not chunk:
                return json.loads(body)
            body += chunk
    raise ValueError("response too large or too slow")


def get_dadjoke():
    return fetch_json("https://icanhazdadjoke.com/")["joke"]


def get_official_joke():
    joke = fetch_json("https://official-joke-api.appspot.com/jokes/programming/random")[0]
    return "%s %s" % (joke["setup"], joke["punchline"])


def get_chuck_norris():
    return fetch_json("https://api.chucknorris.io/jokes/random")["value"]


def get_jokeapi():
    return fetch_json("https://v2.jokeapi.dev/joke/Programming?type=single&safe-mode")["joke"]


def get_pun():
    joke = fetch_json("https://v2.jokeapi.dev/joke/Pun?safe-mode")
    if joke["type"] == "twopart":
        return "%s %s" % (joke["setup"], joke["delivery"])
    return joke["joke"]


def get_useless_fact():
    fact = fetch_json("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en")["text"]
    return fact.replace("`", "'")  # the API writes apostrophes as backticks


def get_advice():
    return fetch_json("https://api.adviceslip.com/advice")["slip"]["advice"]


def get_corporate_bs():
    return fetch_json("https://corporatebs-generator.sameerkumar.website/")["phrase"]


def get_local_joke():
    with open(LOCAL_JOKES, encoding="utf-8-sig") as f:
        jokes = [line.strip() for line in f if line.strip()]
    if not jokes:
        raise ValueError("no jokes found in %s" % (LOCAL_JOKES,))
    return random.choice(jokes)


SOURCES = {
    "local": get_local_joke,
    "icanhazdadjoke": get_dadjoke,
    "official": get_official_joke,
    "jokeapi": get_jokeapi,
    "pun": get_pun,
    "uselessfacts": get_useless_fact,
    "adviceslip": get_advice,
    "corporatebs": get_corporate_bs,
    "norris": get_chuck_norris,
}


class PunputShaper:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object("gcode")
        self.source = config.getchoice("source", {name: name for name in SOURCES}, "local")
        self.loop_at_startup = config.getboolean("loop_at_startup", True)
        self.loop_duration = config.getint("loop_duration", 900, minval=1)
        self.loop_drift = config.getint("loop_drift", 30, minval=0)
        self.only_while_printing = config.getboolean("only_while_printing", True)
        self.thread = None
        self.timer = self.reactor.register_timer(self._loop_event, self.reactor.NEVER)
        self.printer.register_event_handler("klippy:ready", self._handle_ready)
        self.printer.register_event_handler("klippy:shutdown", self._handle_shutdown)
        self.gcode.register_command(
            "PUNPUT_SHAPER", self.cmd_PUNPUT_SHAPER,
            desc="Print one joke now. Optional SOURCE=<name> tries another source")
        self.gcode.register_command(
            "PUNPUT_SHAPER_START", self.cmd_PUNPUT_SHAPER_START,
            desc="Start the periodic jokes")
        self.gcode.register_command(
            "PUNPUT_SHAPER_STOP", self.cmd_PUNPUT_SHAPER_STOP,
            desc="Stop the periodic jokes")

    def _handle_ready(self):
        if self.loop_at_startup:
            self.reactor.update_timer(self.timer, self.reactor.monotonic() + self.loop_duration)
            message = ("\U0001F601 Punput Shaper: jokes every ~%ds from '%s' (only while printing: %s)"
                       % (self.loop_duration, self.source, self.only_while_printing))
        else:
            message = ("⚠️ Punput Shaper: loop not started (loop_at_startup is False). "
                       "Run PUNPUT_SHAPER_START to begin.")
        # Moonraker is not listening for console output yet when Klipper becomes ready.
        self.reactor.register_callback(
            lambda eventtime: self.gcode.respond_info(message), self.reactor.monotonic() + 3.0)

    def _handle_shutdown(self):
        self.reactor.update_timer(self.timer, self.reactor.NEVER)

    def _loop_event(self, eventtime):
        if self._may_tell(eventtime):
            self._tell(self.source)
        delay = self.loop_duration + random.randint(-self.loop_drift, self.loop_drift)
        return eventtime + max(1, delay)

    def _may_tell(self, eventtime):
        if not self.only_while_printing:
            return True
        idle_timeout = self.printer.lookup_object("idle_timeout", None)
        return idle_timeout is not None and idle_timeout.get_status(eventtime)["state"] == "Printing"

    def _tell(self, source):
        """Fetch a joke on a worker thread so a slow API never holds up Klipper."""
        if self.thread is not None and self.thread.is_alive():
            return False
        self.thread = threading.Thread(target=self._worker, args=(source,), daemon=True)
        self.thread.start()
        return True

    def _worker(self, source):
        try:
            message = " ".join(SOURCES[source]().split())  # collapse embedded newlines
        except Exception as e:
            logging.exception("punput_shaper: source '%s' failed", source)
            message = "Punput Shaper: could not get a joke from '%s': %s" % (source, e)
        self.reactor.register_async_callback(
            lambda eventtime: self.gcode.respond_info(message, log=False))

    def cmd_PUNPUT_SHAPER(self, gcmd):
        source = gcmd.get("SOURCE", self.source).lower()
        if source not in SOURCES:
            raise gcmd.error("Unknown joke source '%s'. Options: %s" % (source, ", ".join(SOURCES)))
        if not self._tell(source):
            gcmd.respond_info("Punput Shaper: still fetching the last joke")

    def cmd_PUNPUT_SHAPER_START(self, gcmd):
        self.reactor.update_timer(self.timer, self.reactor.monotonic() + 1.0)
        gcmd.respond_info("Punput Shaper: loop started")

    def cmd_PUNPUT_SHAPER_STOP(self, gcmd):
        self.reactor.update_timer(self.timer, self.reactor.NEVER)
        gcmd.respond_info("Punput Shaper: loop stopped")


def load_config(config):
    return PunputShaper(config)
