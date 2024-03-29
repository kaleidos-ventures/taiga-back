# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db.models import Prefetch, F
from django.test.utils import override_settings

from taiga.timeline.models import Timeline
from taiga.timeline.timeline_implementations import userstory_timeline
from optparse import make_option
from taiga.projects.tasks.models import Task
from taiga.projects.userstories.models import UserStory


def update_timeline(initial_date, final_date):
    timelines = Timeline.objects.all()
    if initial_date:
        timelines = timelines.filter(created__gte=initial_date)
    if final_date:
        timelines = timelines.filter(created__lt=final_date)

    timelines = timelines.filter(event_type="tasks.task.change")

    print("Generating tasks indexed by id dict")
    task_ids = timelines.values_list("object_id", flat=True)

    tasks_iterator = Task.objects.filter(id__in=task_ids).select_related("user_story").iterator()
    tasks_per_id = {task.id: task for task in tasks_iterator}
    del task_ids

    counter = 1
    total = timelines.count()
    print("Updating timelines")
    for timeline in timelines.iterator():
        print("%s/%s"%(counter, total))
        task_id = timeline.object_id
        task = tasks_per_id.get(task_id, None)
        if not task:
            counter += 1
            continue

        user_story = tasks_per_id[task_id].user_story
        if not user_story:
            counter += 1
            continue

        timeline.data["task"]["userstory"] = userstory_timeline(user_story)
        timeline.save(update_fields=["data"])
        counter += 1


class Command(BaseCommand):
    help = 'Regenerate project timeline'
    option_list = BaseCommand.option_list + (
        make_option('--initial_date',
                    action='store',
                    dest='initial_date',
                    default=None,
                    help='Initial date for timeline update'),
        ) + (
        make_option('--final_date',
                    action='store',
                    dest='final_date',
                    default=None,
                    help='Final date for timeline update'),
        )

    @override_settings(DEBUG=False)
    def handle(self, *args, **options):
        update_timeline(options["initial_date"], options["final_date"])
