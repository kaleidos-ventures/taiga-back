# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

# Generated by Django 1.10.4 on 2017-01-16 16:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0058_auto_20161215_1347'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='looking_for_people_note',
            field=models.TextField(blank=True, default='', verbose_name='looking for people note'),
        ),
        migrations.AlterField(
            model_name='projecttemplate',
            name='looking_for_people_note',
            field=models.TextField(blank=True, default='', verbose_name='looking for people note'),
        ),
    ]
