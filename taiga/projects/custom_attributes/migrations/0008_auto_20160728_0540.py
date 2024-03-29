# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

# Generated by Django 1.9.2 on 2016-07-28 05:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('custom_attributes', '0007_auto_20160208_1751'),
    ]

    operations = [
        # Function: Remove a key in a json field
        migrations.RunSQL(
            """
        CREATE OR REPLACE FUNCTION "json_object_delete_keys"("json" json, VARIADIC "keys_to_delete" text[])
                           RETURNS json
                          LANGUAGE sql
                         IMMUTABLE
                            STRICT
                                AS $function$
                   SELECT COALESCE ((SELECT ('{' || string_agg(to_json("key") || ':' || "value", ',') || '}')
                                       FROM json_each("json")
                                      WHERE "key" <> ALL ("keys_to_delete")),
                                    '{}')::json $function$;
            """,
            reverse_sql="""
        DROP FUNCTION IF EXISTS "json_object_delete_keys"("json" json, VARIADIC "keys_to_delete" text[])
                        CASCADE;"""
        ),

        # Function: Romeve a key in the json field of *_custom_attributes_values.values
        migrations.RunSQL(
            """
    CREATE OR REPLACE FUNCTION "clean_key_in_custom_attributes_values"()
                       RETURNS trigger
                            AS $clean_key_in_custom_attributes_values$
                       DECLARE
                               key text;
                               project_id int;
                               object_id int;
                               attribute text;
                               tablename text;
                               custom_attributes_tablename text;
                         BEGIN
                               key := OLD.id::text;
                               project_id := OLD.project_id;
                               attribute := TG_ARGV[0]::text;
                               tablename := TG_ARGV[1]::text;
                               custom_attributes_tablename := TG_ARGV[2]::text;

                               EXECUTE 'UPDATE ' || quote_ident(custom_attributes_tablename) || '
                                           SET attributes_values = json_object_delete_keys(attributes_values, ' || quote_literal(key) || ')
                                          FROM ' || quote_ident(tablename) || '
                                         WHERE ' || quote_ident(tablename) || '.project_id = ' || project_id || '
                                           AND ' || quote_ident(custom_attributes_tablename) || '.' || quote_ident(attribute) || ' = ' || quote_ident(tablename) || '.id';
                               RETURN NULL;
                           END; $clean_key_in_custom_attributes_values$
                      LANGUAGE plpgsql;
            """
        ),

        # Trigger: Clean userstorycustomattributes values before remove a userstorycustomattribute
        migrations.RunSQL(
            """
            DROP TRIGGER IF EXISTS "update_userstorycustomvalues_after_remove_userstorycustomattribute"
                                ON custom_attributes_userstorycustomattribute
                           CASCADE;

            CREATE TRIGGER "update_userstorycustomvalues_after_remove_userstorycustomattribute"
           AFTER DELETE ON custom_attributes_userstorycustomattribute
              FOR EACH ROW
         EXECUTE PROCEDURE clean_key_in_custom_attributes_values('user_story_id', 'userstories_userstory',
                                            'custom_attributes_userstorycustomattributesvalues');
            """
        ),

        # Trigger: Clean taskcustomattributes values before remove a taskcustomattribute
        migrations.RunSQL(
            """
            DROP TRIGGER IF EXISTS "update_taskcustomvalues_after_remove_taskcustomattribute"
                                ON custom_attributes_taskcustomattribute
                           CASCADE;

            CREATE TRIGGER "update_taskcustomvalues_after_remove_taskcustomattribute"
           AFTER DELETE ON custom_attributes_taskcustomattribute
              FOR EACH ROW
         EXECUTE PROCEDURE clean_key_in_custom_attributes_values('task_id', 'tasks_task',
                                            'custom_attributes_taskcustomattributesvalues');
            """
        ),

        # Trigger: Clean issuecustomattributes values before remove a issuecustomattribute
        migrations.RunSQL(
            """
            DROP TRIGGER IF EXISTS "update_issuecustomvalues_after_remove_issuecustomattribute"
                                ON custom_attributes_issuecustomattribute
                           CASCADE;

            CREATE TRIGGER "update_issuecustomvalues_after_remove_issuecustomattribute"
           AFTER DELETE ON custom_attributes_issuecustomattribute
              FOR EACH ROW
         EXECUTE PROCEDURE clean_key_in_custom_attributes_values('issue_id', 'issues_issue',
                                            'custom_attributes_issuecustomattributesvalues');
            """
        ),
        migrations.AlterIndexTogether(
            name='issuecustomattributesvalues',
            index_together=set([('issue',)]),
        ),
        migrations.AlterIndexTogether(
            name='taskcustomattributesvalues',
            index_together=set([('task',)]),
        ),
        migrations.AlterIndexTogether(
            name='userstorycustomattributesvalues',
            index_together=set([('user_story',)]),
        ),
    ]
