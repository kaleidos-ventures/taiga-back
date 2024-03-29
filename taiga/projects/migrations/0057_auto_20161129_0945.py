# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

# Generated by Django 1.10.3 on 2016-11-29 09:45
from __future__ import unicode_literals

from django.db import migrations


DROP_INDEX = """
    DROP INDEX IF EXISTS projects_project_textquery_idx;
"""


# NOTE: This index is needed by taiga.projects.filters.QFilter
CREATE_INDEX = """
    CREATE INDEX projects_project_textquery_idx
              ON projects_project
           USING gin((setweight(to_tsvector('simple',
                                coalesce(projects_project.name, '')), 'A') ||
                      setweight(to_tsvector('simple',
                                 coalesce(inmutable_array_to_string(projects_project.tags), '')), 'B') ||
                      setweight(to_tsvector('simple',
                                coalesce(projects_project.description, '')), 'C')));
"""


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0056_auto_20161110_1518'),
    ]

    operations = [
        migrations.RunSQL([DROP_INDEX, CREATE_INDEX],
                          [DROP_INDEX]),
    ]
