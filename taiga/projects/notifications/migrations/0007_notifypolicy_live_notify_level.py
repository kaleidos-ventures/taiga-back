# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

# Generated by Django 1.10.6 on 2017-03-31 13:03
from __future__ import unicode_literals

from django.db import migrations, models
import taiga.projects.notifications.choices


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0006_auto_20151103_0954'),
    ]

    operations = [
        migrations.AddField(
            model_name='notifypolicy',
            name='live_notify_level',
            field=models.SmallIntegerField(choices=[(taiga.projects.notifications.choices.NotifyLevel(1), 'Involved'), (taiga.projects.notifications.choices.NotifyLevel(2), 'All'), (taiga.projects.notifications.choices.NotifyLevel(3), 'None')], default=taiga.projects.notifications.choices.NotifyLevel(1)),
        ),
    ]
