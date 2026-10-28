#!/usr/bin/env python3
"""Print one joke for the Klipper console.

Usage: punput_shaper.py [source]

Sources: icanhazdadjoke, official, norris, jokeapi, local (default)
"""
import json
import os
import random
import sys
import urllib.error
import urllib.request

USER_AGENT = "punput_shaper (https://github.com/IdleStep/punput_shaper)"
TIMEOUT = 4  # seconds; keep below the timeout of the gcode_shell_command
LOCAL_JOKES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "punput.txt")


def fetch_json(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def get_dadjoke():
    return fetch_json("https://icanhazdadjoke.com/")["joke"]


def get_official_joke():
    joke = fetch_json("https://official-joke-api.appspot.com/jokes/programming/random")[0]
    return f"{joke['setup']} {joke['punchline']}"


def get_chuck_norris():
    return fetch_json("https://api.chucknorris.io/jokes/random")["value"]


def get_jokeapi():
    return fetch_json("https://v2.jokeapi.dev/joke/Programming?type=single&safe-mode")["joke"]


def get_pun():
    return fetch_json("https://v2.jokeapi.dev/joke/Pun?type=single&safe-mode")["joke"]


def get_geek_joke():
    return fetch_json("https://geek-jokes.sameerkumar.website/api?format=json")["joke"]


def get_useless_fact():
    return fetch_json("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en")["text"]


def get_advice():
    return fetch_json("https://api.adviceslip.com/advice")["slip"]["advice"]


def get_corporate_bs():
    return fetch_json("https://corporatebs-generator.sameerkumar.website/")["phrase"]


def get_cat_fact():
    return fetch_json("https://catfact.ninja/fact")["fact"]


def get_excuse():
    return fetch_json("https://excuser-three.vercel.app/v1/excuse")[0]["excuse"]


def get_local_joke():
    with open(LOCAL_JOKES, encoding="utf-8") as f:
        jokes = [line.strip() for line in f if line.strip()]
    if not jokes:
        raise ValueError(f"no jokes found in {LOCAL_JOKES}")
    return random.choice(jokes)


SOURCES = {
    "icanhazdadjoke": get_dadjoke,
    "official": get_official_joke,
    "norris": get_chuck_norris,
    "jokeapi": get_jokeapi,
    "pun": get_pun,
    "geekjokes": get_geek_joke,
    "uselessfacts": get_useless_fact,
    "adviceslip": get_advice,
    "corporatebs": get_corporate_bs,
    "catfacts": get_cat_fact,
    "excuser": get_excuse,
    "local": get_local_joke,
}


def main(argv):
    source = argv[1].lower() if len(argv) > 1 else "local"
    if source not in SOURCES:
        print(f"[ERROR] Unknown joke source '{source}'. Options: {', '.join(SOURCES)}", file=sys.stderr)
        return 2
    try:
        joke = SOURCES[source]()
    except (OSError, ValueError, LookupError) as e:
        print(f"[ERROR] Could not get a joke from '{source}': {e}", file=sys.stderr)
        return 1
    print(" ".join(joke.split()))  # collapse any embedded newlines
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
