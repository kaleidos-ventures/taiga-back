# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos Ventures SL

import uuid
import csv
import pytz

from datetime import datetime, timedelta
from urllib.parse import quote

from unittest import mock
from django.urls import reverse

from taiga.base.utils import json
from taiga.permissions.choices import MEMBERS_PERMISSIONS, ANON_PERMISSIONS
from taiga.projects.history.models import HistoryEntry
from taiga.projects.occ import OCCResourceMixin
from taiga.projects.userstories import services, models

from .. import factories as f

import pytest
pytestmark = pytest.mark.django_db(transaction=True)


##############################
## Move to the backlog
##############################

def test_api_update_orders_in_bulk_succeeds_moved_in_the_backlog_to_the_begining(client):
    #
    #   BLG  |  ML1  |  ML2    |                    |    BLG  |  ML1  |  ML2
    # -------|-------|-------  |                    |  -------|-------|-------
    #   us1  |       |         |   MOVE: us2, us3   |    us2  |       |
    #   us2  |       |         |   TO: no-milestone |    us3  |       |
    #   us3  |       |         |   AFTER: bigining  |    us1  |       |
    #        |       |         |                    |         |       |
    #        |       |         |                    |         |       |

    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    ml1 = f.MilestoneFactory.create(project=project)
    ml2 = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project, backlog_order=1, milestone=None)
    us2 = f.create_userstory(project=project, backlog_order=2, milestone=None)
    us3 = f.create_userstory(project=project, backlog_order=3, milestone=None)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "after_userstory_id": None,
        "bulk_userstories": [us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 200, response.data

    updated_ids = [
        us2.id,
        us3.id,
        us1.id,
    ]
    res = (project.user_stories.filter(id__in=updated_ids)
                               .values("id", "milestone", "backlog_order")
                               .order_by("backlog_order", "id"))
    assert response.json() == list(res)

    us1.refresh_from_db()
    us2.refresh_from_db()
    us3.refresh_from_db()
    assert us2.backlog_order == 1
    assert us2.milestone_id == None
    assert us3.backlog_order == 2
    assert us3.milestone_id == None
    assert us1.backlog_order == 3
    assert us1.milestone_id == None


def test_api_update_orders_in_bulk_succeeds_moved_in_the_backlog_to_the_middle(client):
    #
    #   BLG  |  ML1  |  ML2    |                    |    BLG  |  ML1  |  ML2
    # -------|-------|-------  |                    |  -------|-------|-------
    #   us1  |  us2  |         |   MOVE: us1, us3   |    us4  | us2   |
    #   us4  |  us3  |         |   TO: no-milestone |    us1  |       |
    #   us5  |       |         |   AFTER: us4       |    us3  |       |
    #        |       |         |                    |    us5  |       |
    #        |       |         |                    |         |       |

    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    ml1 = f.MilestoneFactory.create(project=project)
    ml2 = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project, backlog_order=1, milestone=None)
    us4 = f.create_userstory(project=project, backlog_order=2, milestone=None)
    us5 = f.create_userstory(project=project, backlog_order=3, milestone=None)
    us2 = f.create_userstory(project=project, sprint_order=1, milestone=ml1)
    us3 = f.create_userstory(project=project, sprint_order=2, milestone=ml1)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "after_userstory_id": us4.id,
        "bulk_userstories": [us1.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 200, response.data

    updated_ids = [
        us1.id,
        us3.id,
        us5.id,
    ]
    res = (project.user_stories.filter(id__in=updated_ids)
                               .values("id", "milestone", "backlog_order")
                               .order_by("backlog_order", "id"))
    assert response.json() == list(res)

    us1.refresh_from_db()
    us2.refresh_from_db()
    us3.refresh_from_db()
    us4.refresh_from_db()
    us5.refresh_from_db()
    assert us4.backlog_order == 2
    assert us4.milestone_id == None
    assert us1.backlog_order == 3
    assert us1.milestone_id == None
    assert us3.backlog_order == 4
    assert us3.milestone_id == None
    assert us5.backlog_order == 5
    assert us5.milestone_id == None
    assert us2.sprint_order == 1
    assert us2.milestone_id == ml1.id


def test_api_update_orders_in_bulk_succeeds_moved_in_the_backlog_to_the_end(client):
    #
    #   BLG  |  ML1  |  ML2    |                    |    BLG  |  ML1  |  ML2
    # -------|-------|-------  |                    |  -------|-------|-------
    #   us1  | us3   |         |   MOVE: us3        |    us1  |       |
    #   us2  |       |         |   TO: no-milestone |    us2  |       |
    #        |       |         |   AFTER: us2       |    us3  |       |
    #        |       |         |                    |         |       |
    #        |       |         |                    |         |       |

    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    ml1 = f.MilestoneFactory.create(project=project)
    ml2 = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project, backlog_order=1, milestone=None)
    us2 = f.create_userstory(project=project, backlog_order=2, milestone=None)
    us3 = f.create_userstory(project=project, sprint_order=1, milestone=ml1)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "after_userstory_id": us2.id,
        "bulk_userstories": [us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 200, response.data

    updated_ids = [
        us3.id,
    ]
    res = (project.user_stories.filter(id__in=updated_ids)
                               .values("id", "milestone", "backlog_order")
                               .order_by("backlog_order", "id"))
    assert response.json() == list(res)

    us1.refresh_from_db()
    us2.refresh_from_db()
    us3.refresh_from_db()
    assert us1.backlog_order == 1
    assert us1.milestone_id == None
    assert us2.backlog_order == 2
    assert us2.milestone_id == None
    assert us3.backlog_order == 3
    assert us3.milestone_id == None


def test_api_update_orders_in_bulk_succeeds_moved_in_the_backlog_before_one_us(client):
    #
    #   BLG  |  ML1  |  ML2    |                    |    BLG  |  ML1  |  ML2
    # -------|-------|-------  |                    |  -------|-------|-------
    #   us1  | us3   |         |   MOVE: us3        |    us1  |       |
    #   us2  |       |         |   TO: no-milestone |    us3  |       |
    #        |       |         |   BEFORE: us2      |    us2  |       |
    #        |       |         |                    |         |       |
    #        |       |         |                    |         |       |

    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    ml1 = f.MilestoneFactory.create(project=project)
    ml2 = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project, backlog_order=1, milestone=None)
    us2 = f.create_userstory(project=project, backlog_order=2, milestone=None)
    us3 = f.create_userstory(project=project, sprint_order=1, milestone=ml1)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "before_userstory_id": us2.id,
        "bulk_userstories": [us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 200, response.data

    updated_ids = [
        us2.id,
        us3.id,
    ]
    res = (project.user_stories.filter(id__in=updated_ids)
                               .values("id", "milestone", "backlog_order")
                               .order_by("backlog_order", "id"))
    assert response.json() == list(res)

    us1.refresh_from_db()
    us2.refresh_from_db()
    us3.refresh_from_db()
    assert us1.backlog_order == 1
    assert us1.milestone_id == None
    assert us3.backlog_order == 2
    assert us3.milestone_id == None
    assert us2.backlog_order == 3
    assert us2.milestone_id == None


##############################
## Move to sprint
##############################

def test_api_update_orders_in_bulk_succeeds_moved_to_a_milestone_to_the_begining(client):
    #
    #   BLG  |  ML1  |  ML2    |                    |    BLG  |  ML1  |  ML2
    # -------|-------|-------  |                    |  -------|-------|-------
    #        | us1   |         |   MOVE: us2, us3   |         |  us2  |
    #        |       |  us2    |   TO: milestone-1  |         |  us3  |
    #        |       |  us3    |   AFTER: bigining  |         |  us1  |
    #        |       |         |                    |         |       |
    #        |       |         |                    |         |       |

    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    ml1 = f.MilestoneFactory.create(project=project)
    ml2 = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project, sprint_order=1, milestone=ml1)
    us2 = f.create_userstory(project=project, sprint_order=1, milestone=ml2)
    us3 = f.create_userstory(project=project, sprint_order=2, milestone=ml2)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "after_userstory_id": None,
        "milestone_id": ml1.id,
        "bulk_userstories": [us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 200, response.data

    updated_ids = [
        us2.id,
        us3.id,
        us1.id,
    ]
    res = (project.user_stories.filter(id__in=updated_ids)
                               .values("id", "milestone", "sprint_order")
                               .order_by("sprint_order", "id"))
    assert response.json() == list(res)

    us1.refresh_from_db()
    us2.refresh_from_db()
    us3.refresh_from_db()
    assert us2.sprint_order == 1
    assert us2.milestone_id == ml1.id
    assert us3.sprint_order == 2
    assert us3.milestone_id == ml1.id
    assert us1.sprint_order == 3
    assert us1.milestone_id == ml1.id


def test_api_update_orders_in_bulk_succeeds_moved_to_a_milestone_to_the_middle(client):
    #
    #   BLG  |  ML1  |  ML2    |                    |    BLG  |  ML1  |  ML2
    # -------|-------|-------  |                    |  -------|-------|-------
    #        |  us1  |  us2    |   MOVE: us1, us3   |         |  us4  | us2
    #        |  us4  |  us3    |   TO: milestone-1  |         |  us1  |
    #        |  us5  |         |   AFTER: us4       |         |  us3  |
    #        |       |         |                    |         |  us5  |
    #        |       |         |                    |         |       |

    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    ml1 = f.MilestoneFactory.create(project=project)
    ml2 = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project, sprint_order=1, milestone=ml1)
    us4 = f.create_userstory(project=project, sprint_order=2, milestone=ml1)
    us5 = f.create_userstory(project=project, sprint_order=3, milestone=ml1)
    us2 = f.create_userstory(project=project, sprint_order=1, milestone=ml2)
    us3 = f.create_userstory(project=project, sprint_order=2, milestone=ml2)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "after_userstory_id": us4.id,
        "milestone_id": ml1.id,
        "bulk_userstories": [us1.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 200, response.data

    updated_ids = [
        us1.id,
        us3.id,
        us5.id,
    ]
    res = (project.user_stories.filter(id__in=updated_ids)
                               .values("id", "milestone", "sprint_order")
                               .order_by("sprint_order", "id"))
    assert response.json() == list(res)

    us1.refresh_from_db()
    us2.refresh_from_db()
    us3.refresh_from_db()
    us4.refresh_from_db()
    us5.refresh_from_db()
    assert us4.sprint_order == 2
    assert us4.milestone_id == ml1.id
    assert us1.sprint_order == 3
    assert us1.milestone_id == ml1.id
    assert us3.sprint_order == 4
    assert us3.milestone_id == ml1.id
    assert us5.sprint_order == 5
    assert us5.milestone_id == ml1.id
    assert us2.sprint_order == 1
    assert us2.milestone_id == ml2.id


def test_api_update_orders_in_bulk_succeeds_moved_to_a_milestone_to_the_end(client):
    #
    #   BLG  |  ML1  |  ML2    |                    |    BLG  |  ML1  |  ML2
    # -------|-------|-------  |                    |  -------|-------|-------
    #   us1  | us2   |  us3    |   MOVE: us1, us2   |         |       |  us3
    #        |       |         |   TO: milestone-2  |         |       |  us1
    #        |       |         |   AFTER: us3       |         |       |  us2
    #        |       |         |                    |         |       |
    #        |       |         |                    |         |       |

    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    ml1 = f.MilestoneFactory.create(project=project)
    ml2 = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project, backlog_order=1, milestone=None)
    us2 = f.create_userstory(project=project, sprint_order=1, milestone=ml1)
    us3 = f.create_userstory(project=project, sprint_order=1, milestone=ml2)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "after_userstory_id": us3.id,
        "milestone_id": ml2.id,
        "bulk_userstories": [us1.id,
                             us2.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 200, response.data

    updated_ids = [
        us1.id,
        us2.id,
    ]
    res = (project.user_stories.filter(id__in=updated_ids)
                               .values("id", "milestone", "sprint_order")
                               .order_by("sprint_order", "id"))
    assert response.json() == list(res)

    us1.refresh_from_db()
    us2.refresh_from_db()
    us3.refresh_from_db()
    assert us3.sprint_order == 1
    assert us3.milestone_id == ml2.id
    assert us1.sprint_order == 2
    assert us1.milestone_id == ml2.id
    assert us2.sprint_order == 3
    assert us2.milestone_id == ml2.id


def test_api_update_orders_in_bulk_succeeds_moved_to_a_milestone_before_one_us(client):
    #
    #   BLG  |  ML1  |  ML2    |                    |    BLG  |  ML1  |  ML2
    # -------|-------|-------  |                    |  -------|-------|-------
    #        |  us1  | us3     |   MOVE: us3        |         |  us1  |
    #        |  us2  |         |   TO: milestone-1  |         |  us3  |
    #        |       |         |   BEFORE: us2      |         |  us2  |
    #        |       |         |                    |         |       |
    #        |       |         |                    |         |       |

    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    ml1 = f.MilestoneFactory.create(project=project)
    ml2 = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project, sprint_order=1, milestone=ml1)
    us2 = f.create_userstory(project=project, sprint_order=2, milestone=ml1)
    us3 = f.create_userstory(project=project, sprint_order=1, milestone=ml2)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "before_userstory_id": us2.id,
        "milestone_id": ml1.id,
        "bulk_userstories": [us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 200, response.data

    updated_ids = [
        us2.id,
        us3.id,
    ]
    res = (project.user_stories.filter(id__in=updated_ids)
                               .values("id", "milestone", "sprint_order")
                               .order_by("sprint_order", "id"))
    assert response.json() == list(res)

    us1.refresh_from_db()
    us2.refresh_from_db()
    us3.refresh_from_db()
    assert us1.sprint_order == 1
    assert us1.milestone_id == ml1.id
    assert us3.sprint_order == 2
    assert us3.milestone_id == ml1.id
    assert us2.sprint_order == 3
    assert us2.milestone_id == ml1.id


##############################
## Data errors
##############################

def test_api_update_orders_in_bulk_invalid_userstories(client):
    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    us1 = f.create_userstory(project=project)
    us2 = f.create_userstory(project=project)
    us3 = f.create_userstory()

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "bulk_userstories": [us1.id,
                             us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 400, response.data
    assert len(response.data) == 1
    assert "bulk_userstories" in response.data


def test_api_update_orders_in_bulk_invalid_milestone(client):
    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    milestone = f.MilestoneFactory.create()
    us1 = f.create_userstory(project=project)
    us2 = f.create_userstory(project=project)
    us3 = f.create_userstory(project=project)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "milestone_id": milestone.id,
        "bulk_userstories": [us1.id,
                             us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 400, response.data
    assert len(response.data) == 1
    assert "milestone_id" in response.data


def test_api_update_orders_in_bulk_invalid_after_us_because_project(client):
    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    us1 = f.create_userstory(project=project)
    us2 = f.create_userstory(project=project)
    us3 = f.create_userstory(project=project)
    us4 = f.create_userstory()

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "after_userstory_id": us4.id,
        "bulk_userstories": [us1.id,
                             us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 400, response.data
    assert len(response.data) == 1
    assert "after_userstory_id" in response.data


def test_api_update_orders_in_bulk_invalid_after_us_because_milestone(client):
    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    milestone = f.MilestonmeFactory.create(project=project)
    milestone2 = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project)
    us2 = f.create_userstory(project=project)
    us3 = f.create_userstory(project=project)
    us4 = f.create_userstory(project=project, milestone=milestone2)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "milestone_id": milestone.id,
        "after_userstory_id": us4.id,
        "bulk_userstories": [us1.id,
                             us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.milestone_code == 400, response.data
    assert len(response.data) == 1
    assert "after_userstory_id" in response.data


def test_api_update_orders_in_bulk_invalid_after_us_because_no_milestone(client):
    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    milestone = f.UserStoryStatusFactory.create(project=project)
    swl1 = f.SwimlaneFactory.create(project=project)
    us1 = f.create_userstory(project=project)
    us2 = f.create_userstory(project=project)
    us3 = f.create_userstory(project=project)
    us4 = f.create_userstory(project=project, milestone=None)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "milestone_id": milestone.id,
        "after_userstory_id": us4.id,
        "bulk_userstories": [us1.id,
                             us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.milestone_code == 400, response.data
    assert len(response.data) == 1
    assert "after_userstory_id" in response.data


def test_api_update_orders_in_bulk_invalid_after_us_because_project_two(client):
    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    us1 = f.create_userstory(project=project)
    us2 = f.create_userstory(project=project)
    us3 = f.create_userstory(project=project)
    us4 = f.create_userstory()

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "before_userstory_id": us4.id,
        "bulk_userstories": [us1.id,
                             us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 400, response.data
    assert len(response.data) == 1
    assert "before_userstory_id" in response.data


def test_api_update_orders_in_bulk_invalid_after_us_because_milestone_three(client):
    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    milestone = f.MilestoneFactory.create(project=project)
    milestone2 = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project)
    us2 = f.create_userstory(project=project)
    us3 = f.create_userstory(project=project)
    us4 = f.create_userstory(project=project, milestone=milestone2)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "milestone_id": milestone.id,
        "before_userstory_id": us4.id,
        "bulk_userstories": [us1.id,
                             us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 400, response.data
    assert len(response.data) == 1
    assert "before_userstory_id" in response.data


def test_api_update_orders_in_bulk_invalid_after_us_because_no_milestone_four(client):
    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    milestone = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project)
    us2 = f.create_userstory(project=project)
    us3 = f.create_userstory(project=project)
    us4 = f.create_userstory(project=project, milestone=None)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "milestone_id": milestone.id,
        "before_userstory_id": us4.id,
        "bulk_userstories": [us1.id,
                             us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 400, response.data
    assert len(response.data) == 1
    assert "before_userstory_id" in response.data


def test_api_update_orders_in_bulk_invalid_before_us_because_after_us_exist(client):
    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    us1 = f.create_userstory(project=project, milestone=None)
    us2 = f.create_userstory(project=project, milestone=None)
    us3 = f.create_userstory(project=project, milestone=None)
    us4 = f.create_userstory(project=project, milestone=None)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "before_userstory_id": us4.id,
        "after_userstory_id": us4.id,
        "bulk_userstories": [us1.id,
                             us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 400, response.data
    assert len(response.data) == 1
    assert "before_userstory_id" in response.data


##############################
## Close and/or Open Milestones after users stories are moved, history entries and webhooks should be created too
##############################


@mock.patch('taiga.webhooks.tasks._send_request')
def test_milestone_closed_changed_after_moving_userstories_in_bulk_to_other_milestone(send_request_mock, client, settings):
    settings.WEBHOOKS_ENABLED = True
    settings.CELERY_ENABLED = False
    project = f.ProjectFactory()
    f.WebhookFactory.create(project=project)
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    status_opened = f.UserStoryStatusFactory.create(project=project, order=1, is_closed=False)
    status_closed = f.UserStoryStatusFactory.create(project=project, order=2, is_closed=True)

    ml1 = f.MilestoneFactory.create(project=project, name="ML-1")
    ml2 = f.MilestoneFactory.create(project=project, name="ML-2")

    us1 = f.create_userstory(project=project, status=status_closed, is_closed=True, milestone=ml1, sprint_order=1)
    us2 = f.create_userstory(project=project, status=status_opened, is_closed=False, milestone=ml2, sprint_order=1)
    us3 = f.create_userstory(project=project, status=status_opened, is_closed=False, milestone=ml2, sprint_order=2)
    us4 = f.create_userstory(project=project, status=status_closed, is_closed=True, milestone=ml2, sprint_order=3)

    assert HistoryEntry.objects.all().count() == 0
    assert send_request_mock.call_count == 0

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "after_userstory_id": us1.id,
        "milestone_id": ml1.id,
        "bulk_userstories": [us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 200, response.data

    updated_ids = [
        us2.id,
        us3.id,
    ]
    res = (project.user_stories.filter(id__in=updated_ids)
                               .values("id", "milestone", "sprint_order")
                               .order_by("sprint_order", "id"))
    assert response.json() == list(res)

    ml1.refresh_from_db()
    ml2.refresh_from_db()
    assert not ml1.closed
    assert ml2.closed

    assert HistoryEntry.objects.all().count() == 2
    assert send_request_mock.call_count == 2
