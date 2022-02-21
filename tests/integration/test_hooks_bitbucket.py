# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos Ventures SL

import pytest
import urllib

from unittest import mock

from django.urls import reverse
from django.core import mail
from django.conf import settings

from taiga.base.utils import json
from taiga.hooks.bitbucket import event_hooks
from taiga.hooks.bitbucket.api import BitBucketViewSet
from taiga.hooks.exceptions import ActionSyntaxException
from taiga.projects import choices as project_choices
from taiga.projects.epics.models import Epic
from taiga.projects.issues.models import Issue
from taiga.projects.tasks.models import Task
from taiga.projects.userstories.models import UserStory
from taiga.projects.models import Membership
from taiga.projects.history.services import get_history_queryset_by_model_instance, take_snapshot
from taiga.projects.notifications.choices import NotifyLevel
from taiga.projects.notifications.models import NotifyPolicy
from taiga.projects import services
from .. import factories as f

pytestmark = pytest.mark.django_db


def test_bad_signature(client):
    project = f.ProjectFactory()
    f.ProjectModulesConfigFactory(project=project, config={
        "bitbucket": {
            "secret": "tpnIwJDz4e"
        }
    })

    url = reverse("bitbucket-hook-list")
    url = "{}?project={}&key={}".format(url, project.id, "badbadbad")
    data = "{}"
    response = client.post(url, data, content_type="application/json", HTTP_X_EVENT_KEY="repo:push")

    response_content = response.data
    assert response.status_code == 400
    assert "Bad signature" in response_content["_error_message"]


def test_ok_signature(client):
    project = f.ProjectFactory()
    f.ProjectModulesConfigFactory(project=project, config={
        "bitbucket": {
            "secret": "tpnIwJDz4e"
        }
    })

    url = reverse("bitbucket-hook-list")
    url = "{}?project={}&key={}".format(url, project.id, "tpnIwJDz4e")
    data = json.dumps({"push": {"changes": [{"new": {"target": { "message": "test message"}}}]}})
    response = client.post(url,
                           data,
                           content_type="application/json",
                           HTTP_X_EVENT_KEY="repo:push",
                           REMOTE_ADDR="13.52.5.96")

    assert response.status_code == 204


def test_ok_signature_ip_in_network(client):
    project = f.ProjectFactory()
    f.ProjectModulesConfigFactory(project=project, config={
        "bitbucket": {
            "secret": "tpnIwJDz4e"
        }
    })

    url = reverse("bitbucket-hook-list")
    url = "{}?project={}&key={}".format(url, project.id, "tpnIwJDz4e")
    data = json.dumps({"push": {"changes": [{"new": {"target": { "message": "test message"}}}]}})
    response = client.post(url,
                           data,
                           content_type="application/json",
                           HTTP_X_EVENT_KEY="repo:push",
                           REMOTE_ADDR="13.52.5.96")
    assert response.status_code == 204


def test_ok_signature_invalid_network(client):
    project = f.ProjectFactory()
    f.ProjectModulesConfigFactory(project=project, config={
        "bitbucket": {
            "secret": "tpnIwJDz4e",
            "valid_origin_ips": ["131.103.20.160/27;165.254.145.0/26;104.192.143.0/24"],
        }
    })

    url = reverse("bitbucket-hook-list")
    url = "{}?project={}&key={}".format(url, project.id, "tpnIwJDz4e")
    data = json.dumps({"push": {"changes": [{"new": {"target": { "message": "test message"}}}]}})
    response = client.post(url,
                           data,
                           content_type="application/json",
                           HTTP_X_EVENT_KEY="repo:push",
                           REMOTE_ADDR="104.192.143.193")

    assert response.status_code == 400
    assert "Bad signature" in response.data["_error_message"]


def test_blocked_project(client):
    project = f.ProjectFactory(blocked_code=project_choices.BLOCKED_BY_STAFF)
    f.ProjectModulesConfigFactory(project=project, config={
        "bitbucket": {
            "secret": "tpnIwJDz4e"
        }
    })

    url = reverse("bitbucket-hook-list")
    url = "{}?project={}&key={}".format(url, project.id, "tpnIwJDz4e")
    data = json.dumps({"push": {"changes": [{"new": {"target": { "message": "test message"}}}]}})
    response = client.post(url,
                           data,
                           content_type="application/json",
                           HTTP_X_EVENT_KEY="repo:push",
                           REMOTE_ADDR="13.52.5.96")

    assert response.status_code == 451


def test_invalid_ip(client):
    project = f.ProjectFactory()
    f.ProjectModulesConfigFactory(project=project, config={
        "bitbucket": {
            "secret": "tpnIwJDz4e"
        }
    })

    url = reverse("bitbucket-hook-list")
    url = "{}?project={}&key={}".format(url, project.id, "tpnIwJDz4e")
    data = json.dumps({"push": {"changes": [{"new": {"target": { "message": "test message"}}}]}})
    response = client.post(url,
                           data,
                           content_type="application/json",
                           HTTP_X_EVENT_KEY="repo:push",
                           REMOTE_ADDR="111.111.111.112")
    assert response.status_code == 400


def test_invalid_origin_ip_settings(client):
    project = f.ProjectFactory()
    f.ProjectModulesConfigFactory(project=project, config={
        "bitbucket": {
            "secret": "tpnIwJDz4e",
            "valid_origin_ips": ["testing"]
        }
    })

    url = reverse("bitbucket-hook-list")
    url = "{}?project={}&key={}".format(url, project.id, "tpnIwJDz4e")
    data = json.dumps({"push": {"changes": [{"new": {"target": { "message": "test message"}}}]}})
    response = client.post(url,
                           data,
                           content_type="application/json",
                           HTTP_X_EVENT_KEY="repo:push",
                           REMOTE_ADDR="111.111.111.112")
    assert response.status_code == 400


def test_valid_local_network_ip(client):
    project = f.ProjectFactory()
    f.ProjectModulesConfigFactory(project=project, config={
        "bitbucket": {
            "secret": "tpnIwJDz4e",
            "valid_origin_ips": ["192.168.1.1"]
        }
    })

    url = reverse("bitbucket-hook-list")
    url = "{}?project={}&key={}".format(url, project.id, "tpnIwJDz4e")
    data = json.dumps({"push": {"changes": [{"new": {"target": { "message": "test message"}}}]}})
    response = client.post(url,
                           data,
                           content_type="application/json",
                           HTTP_X_EVENT_KEY="repo:push",
                           REMOTE_ADDR="192.168.1.1")
    assert response.status_code == 204


def test_not_ip_filter(client):
    project = f.ProjectFactory()
    f.ProjectModulesConfigFactory(project=project, config={
        "bitbucket": {
            "secret": "tpnIwJDz4e",
            "valid_origin_ips": []
        }
    })

    url = reverse("bitbucket-hook-list")
    url = "{}?project={}&key={}".format(url, project.id, "tpnIwJDz4e")
    data = json.dumps({"push": {"changes": [{"new": {"target": { "message": "test message"}}}]}})
    response = client.post(url,
                           data,
                           content_type="application/json",
                           HTTP_X_EVENT_KEY="repo:push",
                           REMOTE_ADDR="111.111.111.112")
    assert response.status_code == 204


def test_push_event_detected(client):
    project = f.ProjectFactory()
    url = reverse("bitbucket-hook-list")
    url = "%s?project=%s" % (url, project.id)
    data = json.dumps({"push": {"changes": [{"new": {"target": { "message": "test message"}}}]}})

    BitBucketViewSet._validate_signature = mock.Mock(return_value=True)

    with mock.patch.object(event_hooks.PushEventHook, "process_event") as process_event_mock:
        response = client.post(url, data,
                               HTTP_X_EVENT_KEY="repo:push",
                               content_type="application/json")

        assert process_event_mock.call_count == 1

    assert response.status_code == 204


def test_push_event_epic_processing(client):
    creation_status = f.EpicStatusFactory()
    role = f.RoleFactory(project=creation_status.project, permissions=["view_epics"])
    f.MembershipFactory(project=creation_status.project, role=role, user=creation_status.project.owner)
    new_status = f.EpicStatusFactory(project=creation_status.project)
    epic = f.EpicFactory.create(status=creation_status, project=creation_status.project, owner=creation_status.project.owner)
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-%s    #%s   ok   bye!" % (epic.ref, new_status.slug) }
                    ]
                }
            ]
        }
    }
    mail.outbox = []
    ev_hook = event_hooks.PushEventHook(epic.project, payload)
    ev_hook.process_event()
    epic = Epic.objects.get(id=epic.id)
    assert epic.status.id == new_status.id
    assert len(mail.outbox) == 1


def test_push_event_issue_processing(client):
    creation_status = f.IssueStatusFactory()
    role = f.RoleFactory(project=creation_status.project, permissions=["view_issues"])
    f.MembershipFactory(project=creation_status.project, role=role, user=creation_status.project.owner)
    new_status = f.IssueStatusFactory(project=creation_status.project)
    issue = f.IssueFactory.create(status=creation_status, project=creation_status.project, owner=creation_status.project.owner)
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-%s    #%s   ok   bye!" % (issue.ref, new_status.slug) }
                    ]
                }
            ]
        }
    }
    mail.outbox = []
    ev_hook = event_hooks.PushEventHook(issue.project, payload)
    ev_hook.process_event()
    issue = Issue.objects.get(id=issue.id)
    assert issue.status.id == new_status.id
    assert len(mail.outbox) == 1


def test_push_event_task_processing(client):
    creation_status = f.TaskStatusFactory()
    role = f.RoleFactory(project=creation_status.project, permissions=["view_tasks"])
    f.MembershipFactory(project=creation_status.project, role=role, user=creation_status.project.owner)
    new_status = f.TaskStatusFactory(project=creation_status.project)
    task = f.TaskFactory.create(status=creation_status, project=creation_status.project, owner=creation_status.project.owner)
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-%s    #%s   ok   bye!" % (task.ref, new_status.slug) }
                    ]
                }
            ]
        }
    }
    mail.outbox = []
    ev_hook = event_hooks.PushEventHook(task.project, payload)
    ev_hook.process_event()
    task = Task.objects.get(id=task.id)
    assert task.status.id == new_status.id
    assert len(mail.outbox) == 1


def test_push_event_user_story_processing(client):
    creation_status = f.UserStoryStatusFactory()
    role = f.RoleFactory(project=creation_status.project, permissions=["view_us"])
    f.MembershipFactory(project=creation_status.project, role=role, user=creation_status.project.owner)
    new_status = f.UserStoryStatusFactory(project=creation_status.project)
    user_story = f.UserStoryFactory.create(status=creation_status, project=creation_status.project, owner=creation_status.project.owner)
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-%s    #%s   ok   bye!" % (user_story.ref, new_status.slug) }
                    ]
                }
            ]
        }
    }
    mail.outbox = []
    ev_hook = event_hooks.PushEventHook(user_story.project, payload)
    ev_hook.process_event()
    user_story = UserStory.objects.get(id=user_story.id)
    assert user_story.status.id == new_status.id
    assert len(mail.outbox) == 1


def test_push_event_issue_mention(client):
    creation_status = f.IssueStatusFactory()
    role = f.RoleFactory(project=creation_status.project, permissions=["view_issues"])
    f.MembershipFactory(project=creation_status.project, role=role, user=creation_status.project.owner)
    issue = f.IssueFactory.create(status=creation_status, project=creation_status.project, owner=creation_status.project.owner)
    take_snapshot(issue, user=creation_status.project.owner)
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-%s   ok   bye!" % (issue.ref) }
                    ]
                }
            ]
        }
    }
    mail.outbox = []
    ev_hook = event_hooks.PushEventHook(issue.project, payload)
    ev_hook.process_event()
    issue_history = get_history_queryset_by_model_instance(issue)
    assert issue_history.count() == 1
    assert issue_history[0].comment.startswith("This issue has been mentioned by")
    assert len(mail.outbox) == 1


def test_push_event_task_mention(client):
    creation_status = f.TaskStatusFactory()
    role = f.RoleFactory(project=creation_status.project, permissions=["view_tasks"])
    f.MembershipFactory(project=creation_status.project, role=role, user=creation_status.project.owner)
    task = f.TaskFactory.create(status=creation_status, project=creation_status.project, owner=creation_status.project.owner)
    take_snapshot(task, user=creation_status.project.owner)
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-%s   ok   bye!" % (task.ref) }
                    ]
                }
            ]
        }
    }
    mail.outbox = []
    ev_hook = event_hooks.PushEventHook(task.project, payload)
    ev_hook.process_event()
    task_history = get_history_queryset_by_model_instance(task)
    assert task_history.count() == 1
    assert task_history[0].comment.startswith("This task has been mentioned by")
    assert len(mail.outbox) == 1


def test_push_event_user_story_mention(client):
    creation_status = f.UserStoryStatusFactory()
    role = f.RoleFactory(project=creation_status.project, permissions=["view_us"])
    f.MembershipFactory(project=creation_status.project, role=role, user=creation_status.project.owner)
    user_story = f.UserStoryFactory.create(status=creation_status, project=creation_status.project, owner=creation_status.project.owner)
    take_snapshot(user_story, user=creation_status.project.owner)
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-%s   ok   bye!" % (user_story.ref) }
                    ]
                }
            ]
        }
    }

    mail.outbox = []
    ev_hook = event_hooks.PushEventHook(user_story.project, payload)
    ev_hook.process_event()
    us_history = get_history_queryset_by_model_instance(user_story)
    assert us_history.count() == 1
    assert us_history[0].comment.startswith("This user story has been mentioned by")
    assert len(mail.outbox) == 1




def test_push_event_multiple_actions(client):
    creation_status = f.IssueStatusFactory()
    role = f.RoleFactory(project=creation_status.project, permissions=["view_issues"])
    f.MembershipFactory(project=creation_status.project, role=role, user=creation_status.project.owner)
    new_status = f.IssueStatusFactory(project=creation_status.project)
    issue1 = f.IssueFactory.create(status=creation_status, project=creation_status.project, owner=creation_status.project.owner)
    issue2 = f.IssueFactory.create(status=creation_status, project=creation_status.project, owner=creation_status.project.owner)
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-%s    #%s   ok  test   TG-%s    #%s   ok  bye!" % (issue1.ref, new_status.slug, issue2.ref, new_status.slug) }
                    ]
                }
            ]
        }
    }
    mail.outbox = []
    ev_hook1 = event_hooks.PushEventHook(issue1.project, payload)
    ev_hook1.process_event()
    issue1 = Issue.objects.get(id=issue1.id)
    issue2 = Issue.objects.get(id=issue2.id)
    assert issue1.status.id == new_status.id
    assert issue2.status.id == new_status.id
    assert len(mail.outbox) == 2


def test_push_event_processing_case_insensitive(client):
    creation_status = f.TaskStatusFactory()
    role = f.RoleFactory(project=creation_status.project, permissions=["view_tasks"])
    f.MembershipFactory(project=creation_status.project, role=role, user=creation_status.project.owner)
    new_status = f.TaskStatusFactory(project=creation_status.project)
    task = f.TaskFactory.create(status=creation_status, project=creation_status.project, owner=creation_status.project.owner)
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-%s    #%s   ok   bye!" % (task.ref, new_status.slug) }
                    ]
                }
            ]
        }
    }
    mail.outbox = []
    ev_hook = event_hooks.PushEventHook(task.project, payload)
    ev_hook.process_event()
    task = Task.objects.get(id=task.id)
    assert task.status.id == new_status.id
    assert len(mail.outbox) == 1


def test_push_event_task_bad_processing_non_existing_ref(client):
    issue_status = f.IssueStatusFactory()
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-6666666    #%s   ok   bye!" % (issue_status.slug) }
                    ]
                }
            ]
        }
    }
    mail.outbox = []

    ev_hook = event_hooks.PushEventHook(issue_status.project, payload)
    with pytest.raises(ActionSyntaxException) as excinfo:
        ev_hook.process_event()

    assert str(excinfo.value) == "The referenced element doesn't exist"
    assert len(mail.outbox) == 0


def test_push_event_task_bad_processing_non_existing_ref_two(client):
    issue_status = f.IssueStatusFactory()
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-6666666    #%s   ok   bye!" % (issue_status.slug) }
                    ]
                }
            ]
        }
    }
    mail.outbox = []

    ev_hook = event_hooks.PushEventHook(issue_status.project, payload)
    with pytest.raises(ActionSyntaxException) as excinfo:
        ev_hook.process_event()

    assert str(excinfo.value) == "The referenced element doesn't exist"
    assert len(mail.outbox) == 0


def test_push_event_us_bad_processing_non_existing_status(client):
    user_story = f.UserStoryFactory.create()
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-%s    #non-existing-slug   ok   bye!" % (user_story.ref) }
                    ]
                }
            ]
        }
    }

    mail.outbox = []

    ev_hook = event_hooks.PushEventHook(user_story.project, payload)
    with pytest.raises(ActionSyntaxException) as excinfo:
        ev_hook.process_event()

    assert str(excinfo.value) == "The status doesn't exist"
    assert len(mail.outbox) == 0


def test_push_event_bad_processing_non_existing_status(client):
    issue = f.IssueFactory.create()
    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "push": {
            "changes": [
                {
                    "commits": [
                        { "message": "test message   test   TG-%s    #non-existing-slug   ok   bye!" % (issue.ref) }
                    ]
                }
            ]
        }
    }
    mail.outbox = []

    ev_hook = event_hooks.PushEventHook(issue.project, payload)
    with pytest.raises(ActionSyntaxException) as excinfo:
        ev_hook.process_event()

    assert str(excinfo.value) == "The status doesn't exist"
    assert len(mail.outbox) == 0


def test_issues_event_opened_issue(client):
    issue = f.IssueFactory.create()
    issue.project.default_issue_status = issue.status
    issue.project.default_issue_type = issue.type
    issue.project.default_severity = issue.severity
    issue.project.default_priority = issue.priority
    issue.project.save()
    Membership.objects.create(user=issue.owner, project=issue.project, role=f.RoleFactory.create(project=issue.project), is_admin=True)
    notify_policy = NotifyPolicy.objects.get(user=issue.owner, project=issue.project)
    notify_policy.notify_level = NotifyLevel.all
    notify_policy.save()

    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "issue": {
            "id": "10",
            "title": "test-title",
            "links": {"html": {"href": "http://bitbucket.com/site/master/issue/10"}},
            "content": {"raw": "test-content"}
        },
        "repository": {
            "links": {"html": {"href": "http://bitbucket.com/test-user/test-project"}}
        }
    }

    mail.outbox = []

    ev_hook = event_hooks.IssuesEventHook(issue.project, payload)
    ev_hook.process_event()

    assert Issue.objects.count() == 2
    assert len(mail.outbox) == 1


def test_issues_event_bad_issue(client):
    issue = f.IssueFactory.create()
    issue.project.default_issue_status = issue.status
    issue.project.default_issue_type = issue.type
    issue.project.default_severity = issue.severity
    issue.project.default_priority = issue.priority
    issue.project.save()

    payload = {
        "actor": {
        },
        "issue": {
        },
        "repository": {
        }
    }
    mail.outbox = []

    ev_hook = event_hooks.IssuesEventHook(issue.project, payload)

    with pytest.raises(ActionSyntaxException) as excinfo:
        ev_hook.process_event()

    assert str(excinfo.value) == "Invalid issue information"

    assert Issue.objects.count() == 1
    assert len(mail.outbox) == 0


def test_issue_comment_event_on_existing_issue_task_and_us(client):
    project = f.ProjectFactory()
    role = f.RoleFactory(project=project, permissions=["view_tasks", "view_issues", "view_us"])
    f.MembershipFactory(project=project, role=role, user=project.owner)
    user = f.UserFactory()

    issue = f.IssueFactory.create(external_reference=["bitbucket", "http://bitbucket.com/site/master/issue/11"], owner=project.owner, project=project)
    take_snapshot(issue, user=user)
    task = f.TaskFactory.create(external_reference=["bitbucket", "http://bitbucket.com/site/master/issue/11"], owner=project.owner, project=project)
    take_snapshot(task, user=user)
    us = f.UserStoryFactory.create(external_reference=["bitbucket", "http://bitbucket.com/site/master/issue/11"], owner=project.owner, project=project)
    take_snapshot(us, user=user)

    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "issue": {
            "id": "11",
            "title": "test-title",
            "links": {"html": {"href": "http://bitbucket.com/site/master/issue/11"}},
            "content": {"raw": "test-content"}
        },
        "comment": {
            "content": {"raw": "Test body"},
        },
        "repository": {
            "links": {"html": {"href": "http://bitbucket.com/test-user/test-project"}}
        }
    }

    mail.outbox = []

    assert get_history_queryset_by_model_instance(issue).count() == 0
    assert get_history_queryset_by_model_instance(task).count() == 0
    assert get_history_queryset_by_model_instance(us).count() == 0

    ev_hook = event_hooks.IssueCommentEventHook(issue.project, payload)
    ev_hook.process_event()

    issue_history = get_history_queryset_by_model_instance(issue)
    assert issue_history.count() == 1
    assert "Test body" in issue_history[0].comment

    task_history = get_history_queryset_by_model_instance(task)
    assert task_history.count() == 1
    assert "Test body" in issue_history[0].comment

    us_history = get_history_queryset_by_model_instance(us)
    assert us_history.count() == 1
    assert "Test body" in issue_history[0].comment

    assert len(mail.outbox) == 3


def test_issue_comment_event_on_not_existing_issue_task_and_us(client):
    issue = f.IssueFactory.create(external_reference=["bitbucket", "10"])
    take_snapshot(issue, user=issue.owner)
    task = f.TaskFactory.create(project=issue.project, external_reference=["bitbucket", "10"])
    take_snapshot(task, user=task.owner)
    us = f.UserStoryFactory.create(project=issue.project, external_reference=["bitbucket", "10"])
    take_snapshot(us, user=us.owner)

    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "issue": {
            "id": "10",
            "title": "test-title",
            "links": {"html": {"href": "http://bitbucket.com/site/master/issue/10"}},
            "content": {"raw": "test-content"}
        },
        "comment": {
            "content": {"raw": "Test body"},
        },
        "repository": {
            "links": {"html": {"href": "http://bitbucket.com/test-user/test-project"}}
        }
    }

    mail.outbox = []

    assert get_history_queryset_by_model_instance(issue).count() == 0
    assert get_history_queryset_by_model_instance(task).count() == 0
    assert get_history_queryset_by_model_instance(us).count() == 0

    ev_hook = event_hooks.IssueCommentEventHook(issue.project, payload)
    ev_hook.process_event()

    assert get_history_queryset_by_model_instance(issue).count() == 0
    assert get_history_queryset_by_model_instance(task).count() == 0
    assert get_history_queryset_by_model_instance(us).count() == 0

    assert len(mail.outbox) == 0


def test_issues_event_bad_comment(client):
    issue = f.IssueFactory.create(external_reference=["bitbucket", "10"])
    take_snapshot(issue, user=issue.owner)

    payload = {
        "actor": {
            "user": {
                "uuid": "{ce1054cd-3f43-49dc-8aea-d3085ee7ec9b}",
                "username": "test-user",
                "links": {"html": {"href": "http://bitbucket.com/test-user"}}
            }
        },
        "issue": {
            "id": "10",
            "title": "test-title",
            "links": {"html": {"href": "http://bitbucket.com/site/master/issue/10"}},
            "content": {"raw": "test-content"}
        },
        "comment": {
        },
        "repository": {
            "links": {"html": {"href": "http://bitbucket.com/test-user/test-project"}}
        }
    }
    ev_hook = event_hooks.IssueCommentEventHook(issue.project, payload)

    mail.outbox = []

    with pytest.raises(ActionSyntaxException) as excinfo:
        ev_hook.process_event()

    assert str(excinfo.value) == "Invalid issue comment information"

    assert Issue.objects.count() == 1
    assert len(mail.outbox) == 0


def test_api_get_project_modules(client):
    project = f.create_project()
    f.MembershipFactory(project=project, user=project.owner, is_admin=True)

    url = reverse("projects-modules", args=(project.id,))

    client.login(project.owner)
    response = client.get(url)
    assert response.status_code == 200
    content = response.data
    assert "bitbucket" in content
    assert content["bitbucket"]["secret"] != ""
    assert content["bitbucket"]["webhooks_url"] != ""


def test_api_patch_project_modules(client):
    project = f.create_project()
    f.MembershipFactory(project=project, user=project.owner, is_admin=True)

    url = reverse("projects-modules", args=(project.id,))

    client.login(project.owner)
    data = {
        "bitbucket": {
            "secret": "test_secret",
            "url": "test_url",
        }
    }
    response = client.patch(url, json.dumps(data), content_type="application/json")
    assert response.status_code == 204

    config = services.get_modules_config(project).config
    assert "bitbucket" in config
    assert config["bitbucket"]["secret"] == "test_secret"
    assert config["bitbucket"]["webhooks_url"] != "test_url"


def test_replace_bitbucket_references():
    ev_hook = event_hooks.BaseBitBucketEventHook
    assert ev_hook.replace_bitbucket_references(None, "project-url", "#2") == "[BitBucket#2](project-url/issues/2)"
    assert ev_hook.replace_bitbucket_references(None, "project-url", "#2 ") == "[BitBucket#2](project-url/issues/2) "
    assert ev_hook.replace_bitbucket_references(None, "project-url", " #2 ") == " [BitBucket#2](project-url/issues/2) "
    assert ev_hook.replace_bitbucket_references(None, "project-url", " #2") == " [BitBucket#2](project-url/issues/2)"
    assert ev_hook.replace_bitbucket_references(None, "project-url", "#test") == "#test"
    assert ev_hook.replace_bitbucket_references(None, "project-url", None) == ""
