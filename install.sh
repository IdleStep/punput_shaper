#!/usr/bin/env bash
# Install Punput Shaper as a Klipper/Kalico plugin. Run ./install.sh -h for the options.
exec python3 "$(dirname "$(readlink -f "$0")")/install.py" "$@"
