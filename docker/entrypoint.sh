#!/usr/bin/env bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos Ventures SL

set -euo pipefail

cmd=( gunicorn taiga.wsgi:application \
    --name taiga_api \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-tmp-dir /dev/shm \
    --log-level=info \
    --access-logfile - \
    "$@" )

# Execute pending migrations
echo Executing pending migrations
python manage.py migrate

# Load default templates
echo Load default templates
python manage.py loaddata initial_project_templates

if [ "$(id -u)" -eq 0 ]; then
    # Give permission to taiga:taiga after mounting volumes
    echo Give permission to taiga:taiga
    chown -R taiga:taiga /taiga-back

    # Start Taiga processes
    echo Starting Taiga API...
    exec gosu taiga "${cmd[@]}"
else
    # Start Taiga processes
    echo Starting Taiga API...
    exec "${cmd[@]}"
fi
