#!/usr/bin/env bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos Ventures SL

set -euo pipefail

cmd=( celery -A taiga.celery worker -B --concurrency 4 -l INFO "$@" )

if [ "$(id -u)" -eq 0 ]; then
    # Give permission to taiga:taiga after mounting volumes
    echo Give permission to taiga:taiga
    # chown -R taiga:taiga /taiga-back

    # Start Celery processes
    echo Starting Celery...
    exec gosu taiga "${cmd[@]}"
else
    # Start Celery processes
    echo Starting Celery...
    exec "${cmd[@]}"
fi
