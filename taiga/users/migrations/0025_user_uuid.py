# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

# Generated by Django 1.11.2 on 2017-10-31 14:57
from __future__ import unicode_literals

from django.db import migrations, models
import taiga.users.models
import uuid


def update_uuids(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.all():
        user.uuid = uuid.uuid4().hex
        user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0024_auto_20170406_0727'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='uuid',
            field=models.CharField(default=taiga.users.models.get_default_uuid, editable=False, max_length=32),
        ),
        migrations.RunPython(update_uuids, lambda apps, schema_editor: None),
        migrations.AlterField(
            model_name='user',
            name='uuid',
            field=models.CharField(default=taiga.users.models.get_default_uuid, editable=False, max_length=32, unique=True),
        ),
    ]
