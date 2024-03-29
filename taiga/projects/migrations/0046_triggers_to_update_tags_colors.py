# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

# Generated by Django 1.9.2 on 2016-06-07 06:19
from __future__ import unicode_literals

from django.db import migrations
from django.db import connection


def _get_agg_array_agg_mult():
    pg_version = connection.cursor().connection.server_version

    if pg_version < 140000: # PostgreSQL < 14.0
        return """
            DROP AGGREGATE IF EXISTS array_agg_mult (anyarray);
            CREATE AGGREGATE array_agg_mult (anyarray)  (
                SFUNC     = array_cat
               ,STYPE     = anyarray
               ,INITCOND  = '{}'
            );
        """
    else: # PostgreSQL >= 14.0
        return """
            DROP AGGREGATE IF EXISTS array_agg_mult (anycompatiblearray);
            CREATE AGGREGATE array_agg_mult (anycompatiblearray)  (
                SFUNC     = array_cat
               ,STYPE     = anycompatiblearray
               ,INITCOND  = '{}'
            );
        """


def _delete_unused_function():
    pg_version = connection.cursor().connection.server_version

    if pg_version < 140000: # PostgreSQL < 14.0
        return """
            DROP AGGREGATE IF EXISTS array_agg_mult (anyarray);
        """
    else: # PostgreSQL >= 14.0
        return """
            DROP AGGREGATE IF EXISTS array_agg_mult (anycompatiblearray);
        """

class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0045_merge'),
        ('userstories', '0011_userstory_tribe_gig'),
        ('tasks', '0009_auto_20151104_1131'),
        ('issues', '0006_remove_issue_watchers'),
    ]

    operations = [
        ###       Error:
        ###         psycopg2.errors.UndefinedFunction: function array_cat(anyarray, anyarray) does not exist


        # Function: Reduce a multidimensional array only on its first level
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION public.reduce_dim(anyarray)
            RETURNS SETOF anyarray
            AS $function$
            DECLARE
                s $1%TYPE;
            BEGIN
                IF $1 = '{}' THEN
                    RETURN;
                END IF;
                FOREACH s SLICE 1 IN ARRAY $1 LOOP
                    RETURN NEXT s;
                END LOOP;
                RETURN;
            END;
            $function$
            LANGUAGE plpgsql IMMUTABLE;
            """
        ),
        # Function: aggregates multi dimensional arrays
        migrations.RunSQL(_get_agg_array_agg_mult()),
        # Function: array_distinct
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION array_distinct(anyarray)
            RETURNS anyarray AS $$
              SELECT ARRAY(SELECT DISTINCT unnest($1))
            $$ LANGUAGE sql;
            """
        ),
        # Rebuild the color tags so it's consisten in any project
        migrations.RunSQL(
            """
                WITH
                tags_colors AS (
                SELECT id project_id, reduce_dim(tags_colors) tags_colors
                    FROM projects_project
                    WHERE tags_colors  != '{}'
                ),
                tags AS (
                    SELECT unnest(tags) tag, NULL color, project_id FROM userstories_userstory
                    UNION
                    SELECT unnest(tags) tag, NULL color, project_id FROM tasks_task
                    UNION
                    SELECT unnest(tags) tag, NULL color, project_id FROM issues_issue
                    UNION
                    SELECT unnest(tags) tag, NULL color, id project_id FROM projects_project
                ),
                rebuilt_tags_colors AS (
                    SELECT tags.project_id project_id,
                           array_agg_mult(ARRAY[[tags.tag, tags_colors.tags_colors[2]]]) tags_colors
                    FROM tags
                    LEFT JOIN tags_colors ON
                        tags_colors.project_id = tags.project_id AND
                        tags_colors[1] = tags.tag
                    GROUP BY tags.project_id
                )
                UPDATE projects_project
                SET tags_colors = rebuilt_tags_colors.tags_colors
                FROM rebuilt_tags_colors
                WHERE rebuilt_tags_colors.project_id = projects_project.id;
            """
        ),
        # Trigger for auto updating projects_project.tags_colors
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION update_project_tags_colors()
            RETURNS trigger AS $update_project_tags_colors$
            DECLARE
                tags text[];
                project_tags_colors text[];
                tag_color text[];
                project_tags text[];
                tag text;
                project_id integer;
            BEGIN
                tags := NEW.tags::text[];
                project_id := NEW.project_id::integer;
                project_tags := '{}';

                -- Read project tags_colors into project_tags_colors
                SELECT projects_project.tags_colors INTO project_tags_colors
                FROM projects_project
                WHERE id = project_id;

                -- Extract just the project tags to project_tags_colors
                IF project_tags_colors != ARRAY[]::text[] THEN
                    FOREACH tag_color SLICE 1 in ARRAY project_tags_colors
                    LOOP
                        project_tags := array_append(project_tags, tag_color[1]);
                    END LOOP;
                END IF;

                -- Add to project_tags_colors the new tags
                IF tags IS NOT NULL THEN
                    FOREACH tag in ARRAY tags
                    LOOP
                        IF tag != ALL(project_tags) THEN
                            project_tags_colors := array_cat(project_tags_colors,
                                                             ARRAY[ARRAY[tag, NULL]]);
                        END IF;
                    END LOOP;
                END IF;

                -- Save the result in the tags_colors column
                UPDATE projects_project
                SET tags_colors = project_tags_colors
                WHERE id = project_id;

                RETURN NULL;
            END; $update_project_tags_colors$
            LANGUAGE plpgsql;
            """
        ),

        # Execute trigger after user_story update
        migrations.RunSQL(
            """
            DROP TRIGGER IF EXISTS update_project_tags_colors_on_userstory_update ON userstories_userstory;
            CREATE TRIGGER update_project_tags_colors_on_userstory_update
            AFTER UPDATE ON userstories_userstory
            FOR EACH ROW EXECUTE PROCEDURE update_project_tags_colors();
            """
        ),
        # Execute trigger after user_story insert
        migrations.RunSQL(
            """
            DROP TRIGGER IF EXISTS update_project_tags_colors_on_userstory_insert ON userstories_userstory;
            CREATE TRIGGER update_project_tags_colors_on_userstory_insert
            AFTER INSERT ON userstories_userstory
            FOR EACH ROW EXECUTE PROCEDURE update_project_tags_colors();
            """
        ),
        # Execute trigger after task update
        migrations.RunSQL(
            """
            DROP TRIGGER IF EXISTS update_project_tags_colors_on_task_update ON tasks_task;
            CREATE TRIGGER update_project_tags_colors_on_task_update
            AFTER UPDATE ON tasks_task
            FOR EACH ROW EXECUTE PROCEDURE update_project_tags_colors();
            """
        ),
        # Execute trigger after task insert
        migrations.RunSQL(
            """
            DROP TRIGGER IF EXISTS update_project_tags_colors_on_task_insert ON tasks_task;
            CREATE TRIGGER update_project_tags_colors_on_task_insert
            AFTER INSERT ON tasks_task
            FOR EACH ROW EXECUTE PROCEDURE update_project_tags_colors();
            """
        ),
        # Execute trigger after issue update
        migrations.RunSQL(
            """
            DROP TRIGGER IF EXISTS update_project_tags_colors_on_issue_update ON issues_issue;
            CREATE TRIGGER update_project_tags_colors_on_issue_update
            AFTER UPDATE ON issues_issue
            FOR EACH ROW EXECUTE PROCEDURE update_project_tags_colors();
            """
        ),
        # Execute trigger after issue insert
        migrations.RunSQL(
            """
            DROP TRIGGER IF EXISTS update_project_tags_colors_on_issue_insert ON issues_issue;
            CREATE TRIGGER update_project_tags_colors_on_issue_insert
            AFTER INSERT ON issues_issue
            FOR EACH ROW EXECUTE PROCEDURE update_project_tags_colors();
            """
        ),
        # Delete unneded function
        migrations.RunSQL(_delete_unused_function()),
    ]
