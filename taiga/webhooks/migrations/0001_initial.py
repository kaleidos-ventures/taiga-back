# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

from __future__ import unicode_literals

from django.db import models, migrations
import taiga.base.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0015_auto_20141230_1212'),
    ]

    operations = [
        migrations.CreateModel(
            name='Webhook',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('url', models.URLField(verbose_name='URL')),
                ('key', models.TextField(verbose_name='secret key')),
                ('project', models.ForeignKey(related_name='webhooks', to='projects.Project', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='WebhookLog',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('url', models.URLField(verbose_name='URL')),
                ('status', models.IntegerField(verbose_name='Status code')),
                ('request_data', taiga.base.db.models.fields.JSONField(verbose_name='Request data')),
                ('response_data', models.TextField(verbose_name='Response data')),
                ('webhook', models.ForeignKey(related_name='logs', to='webhooks.Webhook', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
