# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

# Generated by Django 1.9.2 on 2016-11-08 11:19
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('epics', '0004_auto_20160928_0540'),
    ]

    operations = [
        migrations.AddField(
            model_name='epic',
            name='external_reference',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), blank=True, default=None, null=True, size=None, verbose_name='external reference'),
        ),
    ]
