# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

# Generated by Django 2.2.12 on 2020-06-15 08:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0062_auto_20190826_0920'),
    ]

    operations = [
        migrations.AlterField(
            model_name='epicstatus',
            name='is_closed',
            field=models.BooleanField(blank=True, default=False, verbose_name='is closed'),
        ),
        migrations.AlterField(
            model_name='issueduedate',
            name='by_default',
            field=models.BooleanField(blank=True, default=False, verbose_name='by default'),
        ),
        migrations.AlterField(
            model_name='issuestatus',
            name='is_closed',
            field=models.BooleanField(blank=True, default=False, verbose_name='is closed'),
        ),
        migrations.AlterField(
            model_name='project',
            name='is_backlog_activated',
            field=models.BooleanField(blank=True, default=True, verbose_name='active backlog panel'),
        ),
        migrations.AlterField(
            model_name='project',
            name='is_contact_activated',
            field=models.BooleanField(blank=True, default=True, verbose_name='active contact'),
        ),
        migrations.AlterField(
            model_name='project',
            name='is_epics_activated',
            field=models.BooleanField(blank=True, default=False, verbose_name='active epics panel'),
        ),
        migrations.AlterField(
            model_name='project',
            name='is_featured',
            field=models.BooleanField(blank=True, default=False, verbose_name='is featured'),
        ),
        migrations.AlterField(
            model_name='project',
            name='is_issues_activated',
            field=models.BooleanField(blank=True, default=True, verbose_name='active issues panel'),
        ),
        migrations.AlterField(
            model_name='project',
            name='is_kanban_activated',
            field=models.BooleanField(blank=True, default=False, verbose_name='active kanban panel'),
        ),
        migrations.AlterField(
            model_name='project',
            name='is_looking_for_people',
            field=models.BooleanField(blank=True, default=False, verbose_name='is looking for people'),
        ),
        migrations.AlterField(
            model_name='project',
            name='is_private',
            field=models.BooleanField(blank=True, default=True, verbose_name='is private'),
        ),
        migrations.AlterField(
            model_name='project',
            name='is_wiki_activated',
            field=models.BooleanField(blank=True, default=True, verbose_name='active wiki panel'),
        ),
        migrations.AlterField(
            model_name='project',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_projects', to=settings.AUTH_USER_MODEL, verbose_name='owner'),
        ),
        migrations.AlterField(
            model_name='projecttemplate',
            name='is_backlog_activated',
            field=models.BooleanField(blank=True, default=True, verbose_name='active backlog panel'),
        ),
        migrations.AlterField(
            model_name='projecttemplate',
            name='is_contact_activated',
            field=models.BooleanField(blank=True, default=True, verbose_name='active contact'),
        ),
        migrations.AlterField(
            model_name='projecttemplate',
            name='is_epics_activated',
            field=models.BooleanField(blank=True, default=False, verbose_name='active epics panel'),
        ),
        migrations.AlterField(
            model_name='projecttemplate',
            name='is_issues_activated',
            field=models.BooleanField(blank=True, default=True, verbose_name='active issues panel'),
        ),
        migrations.AlterField(
            model_name='projecttemplate',
            name='is_kanban_activated',
            field=models.BooleanField(blank=True, default=False, verbose_name='active kanban panel'),
        ),
        migrations.AlterField(
            model_name='projecttemplate',
            name='is_looking_for_people',
            field=models.BooleanField(blank=True, default=False, verbose_name='is looking for people'),
        ),
        migrations.AlterField(
            model_name='projecttemplate',
            name='is_wiki_activated',
            field=models.BooleanField(blank=True, default=True, verbose_name='active wiki panel'),
        ),
        migrations.AlterField(
            model_name='taskduedate',
            name='by_default',
            field=models.BooleanField(blank=True, default=False, verbose_name='by default'),
        ),
        migrations.AlterField(
            model_name='taskstatus',
            name='is_closed',
            field=models.BooleanField(blank=True, default=False, verbose_name='is closed'),
        ),
        migrations.AlterField(
            model_name='userstoryduedate',
            name='by_default',
            field=models.BooleanField(blank=True, default=False, verbose_name='by default'),
        ),
        migrations.AlterField(
            model_name='userstorystatus',
            name='is_archived',
            field=models.BooleanField(blank=True, default=False, verbose_name='is archived'),
        ),
        migrations.AlterField(
            model_name='userstorystatus',
            name='is_closed',
            field=models.BooleanField(blank=True, default=False, verbose_name='is closed'),
        ),
    ]
