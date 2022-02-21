# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos Ventures SL

from unittest import mock
from django.urls import reverse

from taiga.projects import services
from taiga.base.utils import json

from .. import factories as f

import pytest
pytestmark = pytest.mark.django_db


def test_get_members_from_bulk():
    data = [{"role_id": "1", "username": "member1@email.com"},
            {"role_id": "1", "username": "member2@email.com"}]
    members = services.get_members_from_bulk(data, project_id=1)

    assert len(members) == 2
    assert members[0].email == "member1@email.com"
    assert members[1].email == "member2@email.com"


def test_create_member_forbidden_for_unverified_user(client):
    project = f.ProjectFactory()
    john = f.UserFactory.create(verified_email=False)
    joseph = f.UserFactory.create()
    tester = f.RoleFactory(project=project, name="Tester")
    f.MembershipFactory(project=project, user=john, is_admin=True)
    url = reverse("memberships-list")

    data = {"project": project.id, "role": tester.pk, "username": joseph.email}
    client.login(john)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400


def test_create_member_forbidden_for_unverified_user_in_bulk(client):
    project = f.ProjectFactory()
    john = f.UserFactory.create(verified_email=False)
    joseph = f.UserFactory.create()
    tester = f.RoleFactory(project=project, name="Tester")
    f.MembershipFactory(project=project, user=john, is_admin=True)
    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships":[{"role_id": tester.pk, "username": joseph.email}]
    }
    client.login(john)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400


def test_create_member_using_email(client):
    project = f.ProjectFactory()
    john = f.UserFactory.create()
    joseph = f.UserFactory.create()
    tester = f.RoleFactory(project=project, name="Tester")
    f.MembershipFactory(project=project, user=john, is_admin=True)
    url = reverse("memberships-list")

    data = {"project": project.id, "role": tester.pk, "username": joseph.email}
    client.login(john)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 201
    assert response.data["email"] == joseph.email


def test_create_member_using_username_without_being_contacts(client):
    project = f.ProjectFactory()
    john = f.UserFactory.create()
    joseph = f.UserFactory.create()
    tester = f.RoleFactory(project=project, name="Tester")
    f.MembershipFactory(project=project, user=john, is_admin=True)
    url = reverse("memberships-list")

    data = {"project": project.id, "role": tester.pk, "username": joseph.username}
    client.login(john)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "The user must be a valid contact" in response.data["username"][0]


def test_create_member_using_username_being_contacts(client):
    project = f.ProjectFactory()
    john = f.UserFactory.create()
    joseph = f.UserFactory.create()
    tester = f.RoleFactory(project=project, name="Tester", permissions=["view_project"])
    f.MembershipFactory(project=project, user=john, role=tester, is_admin=True)

    # They are members from another project
    project2 = f.ProjectFactory()
    gamer = f.RoleFactory(project=project2, name="Gamer", permissions=["view_project"])
    f.MembershipFactory(project=project2, user=john, role=gamer, is_admin=True)
    f.MembershipFactory(project=project2, user=joseph, role=gamer)

    url = reverse("memberships-list")

    data = {"project": project.id, "role": tester.pk, "username": joseph.username}
    client.login(john)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 201
    assert response.data["user"] == joseph.id


def test_create_members_in_bulk():
    with mock.patch("taiga.projects.services.members.db") as db:
        data = [{"role_id": "1", "username": "member1@email.com"},
                {"role_id": "1", "username": "member2@email.com"}]
        members = services.get_members_from_bulk(data, project_id=1)
        services.create_members_in_bulk(members)
        db.save_in_bulk.assert_called_once_with(members, None, None)


def test_api_create_bulk_members(client):
    project = f.ProjectFactory()
    john = f.UserFactory.create()
    joseph = f.UserFactory.create()
    other = f.UserFactory.create()
    tester = f.RoleFactory(project=project, name="Tester", permissions=["view_project"])
    gamer = f.RoleFactory(project=project, name="Gamer", permissions=["view_project"])
    f.MembershipFactory(project=project, user=john, role=tester, is_admin=True)

    # John and Other are members from another project
    project2 = f.ProjectFactory()
    f.MembershipFactory(project=project2, user=john, role=gamer, is_admin=True)
    f.MembershipFactory(project=project2, user=other, role=gamer)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": gamer.pk, "username": joseph.email},
            {"role_id": gamer.pk, "username": other.username},
        ]
    }
    client.login(john)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 200
    response_user_ids = set([u["user"] for u in response.data])
    user_ids = {other.id, joseph.id}
    assert(user_ids.issubset(response_user_ids))


def test_api_create_bulk_members_invalid_user_id(client):
    project = f.ProjectFactory()
    john = f.UserFactory.create()
    joseph = f.UserFactory.create()
    other = f.UserFactory.create()
    tester = f.RoleFactory(project=project, name="Tester", permissions=["view_project"])
    gamer = f.RoleFactory(project=project, name="Gamer", permissions=["view_project"])
    f.MembershipFactory(project=project, user=john, role=tester, is_admin=True)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": gamer.pk, "username": joseph.email},
            {"role_id": gamer.pk, "username": other.username},
        ]
    }
    client.login(john)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "bulk_memberships" in response.data
    assert "username" in response.data["bulk_memberships"][1]


def test_api_create_bulk_members_with_invalid_roles(client):
    project = f.ProjectFactory()
    john = f.UserFactory.create()
    joseph = f.UserFactory.create()
    tester = f.RoleFactory(name="Tester")
    gamer = f.RoleFactory(name="Gamer")
    f.MembershipFactory(project=project, user=project.owner, is_admin=True)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": tester.pk, "username": john.email},
            {"role_id": gamer.pk, "username": joseph.email},
        ]
    }
    client.login(project.owner)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "bulk_memberships" in response.data


def test_api_create_bulk_members_with_allowed_domain(client):
    project = f.ProjectFactory()
    john = f.UserFactory.create()
    joseph = f.UserFactory.create()
    tester = f.RoleFactory(project=project, name="Tester")
    gamer = f.RoleFactory(project=project, name="Gamer")
    f.MembershipFactory(project=project, user=project.owner, is_admin=True)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": tester.pk, "username": "test1@email.com"},
            {"role_id": gamer.pk, "username": "test2@email.com"},
        ]
    }
    client.login(project.owner)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 200
    assert response.data[0]["email"] == "test1@email.com"
    assert response.data[1]["email"] == "test2@email.com"


def test_api_create_bulk_members_with_allowed_and_unallowed_domain(client, settings):
    project = f.ProjectFactory()
    settings.USER_EMAIL_ALLOWED_DOMAINS = ['email.com']
    tester = f.RoleFactory(project=project, name="Tester")
    gamer = f.RoleFactory(project=project, name="Gamer")
    f.MembershipFactory(project=project, user=project.owner, is_admin=True)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": tester.pk, "username": "test@invalid-domain.com"},
            {"role_id": gamer.pk, "username": "test@email.com"},
        ]
    }
    client.login(project.owner)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "username" in response.data["bulk_memberships"][0]
    assert "username" not in response.data["bulk_memberships"][1]


def test_api_create_bulk_members_with_unallowed_domains(client, settings):
    project = f.ProjectFactory()
    settings.USER_EMAIL_ALLOWED_DOMAINS = ['email.com']
    tester = f.RoleFactory(project=project, name="Tester")
    gamer = f.RoleFactory(project=project, name="Gamer")
    f.MembershipFactory(project=project, user=project.owner, is_admin=True)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": tester.pk, "username": "test1@invalid-domain.com"},
            {"role_id": gamer.pk, "username": "test2@invalid-domain.com"},
        ]
    }
    client.login(project.owner)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "username" in response.data["bulk_memberships"][0]
    assert "username" in response.data["bulk_memberships"][1]

########
# Number of member and project restriction
########

# Private
def test_api_create_bulk_members_without_enough_memberships_private_project_slots_multiple_projects(client):
    user = f.UserFactory.create(max_memberships_private_projects=4)
    project = f.ProjectFactory(owner=user, is_private=True)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=user, is_admin=True)

    other_project = f.ProjectFactory(owner=user, is_private=True)
    f.MembershipFactory(project=other_project, user=user, is_admin=True)
    f.MembershipFactory(project=other_project)
    f.MembershipFactory(project=other_project)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": role.pk, "username": "test1@test.com"},
            {"role_id": role.pk, "username": "test2@test.com"},
        ]
    }
    client.login(user)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "reached your current limit of memberships for private" in response.data["_error_message"]


def test_api_create_bulk_members_without_enough_memberships_private_project_slots_one_project(client):
    user = f.UserFactory.create(max_memberships_private_projects=2)
    project = f.ProjectFactory(owner=user, is_private=True)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=user, is_admin=True)

    project2 = f.ProjectFactory(owner=user, is_private=True)
    f.MembershipFactory(project=project2)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": role.pk, "username": "test1@test.com"},
            {"role_id": role.pk, "username": "test2@test.com"},
        ]
    }
    client.login(user)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "reached your current limit of memberships for private" in response.data["_error_message"]


def test_api_create_bulk_members_for_admin_without_enough_memberships_private_project_slots_one_project(client):
    owner = f.UserFactory.create(max_memberships_private_projects=3)
    user = f.UserFactory.create()
    project = f.ProjectFactory(owner=owner, is_private=True)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=owner, is_admin=True)
    f.MembershipFactory(project=project, user=user, is_admin=True)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": role.pk, "username": "test1@test.com"},
            {"role_id": role.pk, "username": "test4@test.com"},
        ]
    }
    client.login(user)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "reached your current limit of memberships for private" in response.data["_error_message"]


def test_api_create_bulk_members_with_enough_memberships_private_project_slots_one_project(client):
    user = f.UserFactory.create(max_memberships_private_projects=3)
    project = f.ProjectFactory(owner=user, is_private=True)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=user, is_admin=True)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": role.pk, "username": "test1@test.com"},
            {"role_id": role.pk, "username": "test2@test.com"},
        ]
    }
    client.login(user)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 200

# Public

def test_api_create_bulk_members_without_enough_memberships_public_project_slots_multiple_projects(client):
    user = f.UserFactory.create(max_memberships_public_projects=4)
    project = f.ProjectFactory(owner=user, is_private=False)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=user, is_admin=True)

    other_project = f.ProjectFactory(owner=user, is_private=False)
    f.MembershipFactory(project=other_project, user=user, is_admin=True)
    f.MembershipFactory(project=other_project)
    f.MembershipFactory(project=other_project)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": role.pk, "username": "test1@test.com"},
            {"role_id": role.pk, "username": "test2@test.com"},
        ]
    }
    client.login(user)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "reached your current limit of memberships for public" in response.data["_error_message"]


def test_api_create_bulk_members_without_enough_memberships_public_project_slots_one_project(client):
    user = f.UserFactory.create(max_memberships_public_projects=2)
    project = f.ProjectFactory(owner=user, is_private=False)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=user, is_admin=True)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": role.pk, "username": "test1@test.com"},
            {"role_id": role.pk, "username": "test2@test.com"},
        ]
    }
    client.login(user)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "reached your current limit of memberships for public" in response.data["_error_message"]


def test_api_create_bulk_members_for_admin_without_enough_memberships_public_project_slots_one_project(client):
    owner = f.UserFactory.create(max_memberships_public_projects=3)
    user = f.UserFactory.create()
    project = f.ProjectFactory(owner=owner, is_private=False)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=owner, is_admin=True)
    f.MembershipFactory(project=project, user=user, is_admin=True)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": role.pk, "username": "test1@test.com"},
            {"role_id": role.pk, "username": "test4@test.com"},
        ]
    }
    client.login(user)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "reached your current limit of memberships for public" in response.data["_error_message"]


def test_api_create_bulk_members_with_enough_memberships_public_project_slots_one_project(client):
    user = f.UserFactory.create(max_memberships_public_projects=3)
    project = f.ProjectFactory(owner=user, is_private=False)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=user, is_admin=True)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": role.pk, "username": "test1@test.com"},
            {"role_id": role.pk, "username": "test2@test.com"},
        ]
    }
    client.login(user)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 200


def test_api_create_bulk_members_with_extra_text(client, outbox):
    project = f.ProjectFactory()
    tester = f.RoleFactory(project=project, name="Tester")
    f.MembershipFactory(project=project, user=project.owner, is_admin=True)
    url = reverse("memberships-bulk-create")

    invitation_extra_text = "this is a not so random invitation text"
    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": tester.pk, "username": "john@email.com"},
        ],
        "invitation_extra_text": invitation_extra_text
    }
    client.login(project.owner)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 200
    assert response.data[0]["email"] == "john@email.com"

    message = outbox[0]
    assert len(outbox) == 1
    assert message.to == ["john@email.com"]
    assert "this is a not so random invitation text" in message.body


def test_api_resend_invitation(client, outbox):
    invitation = f.create_invitation(user=None)
    f.MembershipFactory(project=invitation.project, user=invitation.project.owner, is_admin=True)
    url = reverse("memberships-resend-invitation", kwargs={"pk": invitation.pk})

    client.login(invitation.project.owner)
    response = client.post(url)

    assert response.status_code == 204
    assert len(outbox) == 1
    assert outbox[0].to == [invitation.email]


def test_api_invite_existing_user(client, outbox):
    "Should create the invitation linked to that user"
    user = f.UserFactory.create()
    role = f.RoleFactory.create()
    f.MembershipFactory(project=role.project, user=role.project.owner, is_admin=True)

    client.login(role.project.owner)

    url = reverse("memberships-list")
    data = {"role": role.pk, "project": role.project.pk, "username": user.email}

    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 201, response.data
    assert len(outbox) == 1
    assert user.memberships.count() == 1

    message = outbox[0]

    assert message.to == [user.email]
    assert "Added to the project" in message.subject


def test_api_create_invalid_membership_no_email_no_user(client):
    "Should not create the invitation linked to that user"
    user = f.UserFactory.create()
    role = f.RoleFactory.create()
    client.login(role.project.owner)

    url = reverse("memberships-list")
    data = {"role": role.pk, "project": role.project.pk}

    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400, response.data
    assert user.memberships.count() == 0


def test_api_create_invalid_membership_role_doesnt_exist_in_the_project(client):
    "Should not create the invitation linked to that user"
    user = f.UserFactory.create()
    role = f.RoleFactory.create()
    project = f.ProjectFactory.create()

    client.login(project.owner)

    url = reverse("memberships-list")
    data = {"role": role.pk, "project": project.pk, "username": user.email}

    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400, response.data
    assert response.data["role"][0] == "Invalid role for the project"
    assert user.memberships.count() == 0


def test_api_create_membership(client):
    membership = f.MembershipFactory(is_admin=True)
    role = f.RoleFactory.create(project=membership.project)
    user = f.UserFactory.create()

    client.login(membership.user)
    url = reverse("memberships-list")
    data = {"role": role.pk, "project": role.project.pk, "username": user.email}
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 201
    assert response.data["user_email"] == user.email


def test_api_create_membership_with_unallowed_domain(client, settings):
    settings.USER_EMAIL_ALLOWED_DOMAINS = ['email.com']

    membership = f.MembershipFactory(is_admin=True)
    role = f.RoleFactory.create(project=membership.project)

    client.login(membership.user)
    url = reverse("memberships-list")
    data = {"role": role.pk, "project": role.project.pk, "username": "test@invalid-email.com"}
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "username" in response.data


def test_api_create_membership_with_allowed_domain(client, settings):
    settings.USER_EMAIL_ALLOWED_DOMAINS = ['email.com']

    membership = f.MembershipFactory(is_admin=True)
    role = f.RoleFactory.create(project=membership.project)

    client.login(membership.user)
    url = reverse("memberships-list")
    data = {"role": role.pk, "project": role.project.pk, "username": "test@email.com"}
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 201
    assert response.data["email"] == "test@email.com"


def test_api_create_membership_without_enough_memberships_private_project_slots_one_projects(client):
    user = f.UserFactory.create(max_memberships_private_projects=1)
    project = f.ProjectFactory(owner=user, is_private=True)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=user, is_admin=True)

    client.login(user)
    url = reverse("memberships-list")
    data = {"role": role.pk, "project": project.pk, "username": "test@test.com"}
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "reached your current limit of memberships for private" in response.data["_error_message"]


def test_api_create_membership_without_enough_memberships_private_project_slots_multiple_projects(client):
    user = f.UserFactory.create(max_memberships_private_projects=3)
    project = f.ProjectFactory(owner=user, is_private=True)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=user, is_admin=True)

    other_project = f.ProjectFactory(owner=user, is_private=True)
    f.MembershipFactory(project=other_project, user=user, is_admin=True)
    f.MembershipFactory(project=other_project)
    f.MembershipFactory(project=other_project)

    client.login(user)
    url = reverse("memberships-list")
    data = {"role": role.pk, "project": project.pk, "username": "test@test.com"}
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "reached your current limit of memberships for private" in response.data["_error_message"]


def test_api_create_membership_with_enough_memberships_private_project_slots_multiple_projects(client):
    user = f.UserFactory.create(max_memberships_private_projects=5)
    project = f.ProjectFactory(owner=user, is_private=True)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=user, is_admin=True)

    other_project = f.ProjectFactory(owner=user)
    f.MembershipFactory.create(project=other_project)
    f.MembershipFactory.create(project=other_project)

    client.login(user)
    url = reverse("memberships-list")
    data = {"role": role.pk, "project": project.pk, "username": "test@test.com"}
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 201


def test_api_create_membership_without_enough_memberships_public_project_slots_one_projects(client):
    user = f.UserFactory.create(max_memberships_public_projects=1)
    project = f.ProjectFactory(owner=user, is_private=False)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=user, is_admin=True)

    client.login(user)
    url = reverse("memberships-list")
    data = {"role": role.pk, "project": project.pk, "username": "test@test.com"}
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "reached your current limit of memberships for public" in response.data["_error_message"]


def test_api_create_membership_without_enough_memberships_public_project_slots_multiple_projects(client):
    user = f.UserFactory.create(max_memberships_public_projects=3)
    project = f.ProjectFactory(owner=user, is_private=False)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=user, is_admin=True)

    other_project = f.ProjectFactory(owner=user, is_private=False)
    f.MembershipFactory(project=other_project, user=user, is_admin=True)
    f.MembershipFactory(project=other_project)
    f.MembershipFactory(project=other_project)

    client.login(user)
    url = reverse("memberships-list")
    data = {"role": role.pk, "project": project.pk, "username": "test@test.com"}
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400
    assert "reached your current limit of memberships for public" in response.data["_error_message"]


def test_api_create_membership_with_enough_memberships_public_project_slots_multiple_projects(client):
    user = f.UserFactory.create(max_memberships_public_projects=5)
    project = f.ProjectFactory(owner=user, is_private=False)
    role = f.RoleFactory(project=project, name="Test")
    f.MembershipFactory(project=project, user=user, is_admin=True)

    other_project = f.ProjectFactory(owner=user)
    f.MembershipFactory.create(project=other_project)
    f.MembershipFactory.create(project=other_project)
    f.MembershipFactory.create(project=other_project)
    f.MembershipFactory.create(project=other_project)

    client.login(user)
    url = reverse("memberships-list")
    data = {"role": role.pk, "project": project.pk, "username": "test@test.com"}
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 201


def test_api_edit_membership(client):
    membership = f.MembershipFactory(is_admin=True)
    client.login(membership.user)
    url = reverse("memberships-detail", args=[membership.id])
    data = {"username": "new@email.com"}
    response = client.json.patch(url, json.dumps(data))
    assert response.status_code == 200


def test_api_edit_membership_two(client):
    membership = f.MembershipFactory(is_admin=True)
    client.login(membership.user)
    url = reverse("memberships-detail", args=[membership.id])
    data = {"username": "new@email.com"}
    response = client.json.patch(url, json.dumps(data))
    assert response.status_code == 200


def test_api_change_owner_membership_to_no_admin_return_error(client):
    project = f.ProjectFactory()
    membership_owner = f.MembershipFactory(project=project, user=project.owner, is_admin=True)
    membership = f.MembershipFactory(project=project, is_admin=True)

    url = reverse("memberships-detail", args=[membership_owner.id])
    data = {"is_admin": False}

    client.login(membership.user)
    response = client.json.patch(url, json.dumps(data))

    assert response.status_code == 400
    assert 'is_admin' in response.data


def test_api_delete_membership(client):
    membership = f.MembershipFactory(is_admin=True)
    client.login(membership.user)
    url = reverse("memberships-detail", args=[membership.id])
    response = client.json.delete(url)

    assert response.status_code == 400

    f.MembershipFactory(is_admin=True, project=membership.project)

    url = reverse("memberships-detail", args=[membership.id])
    response = client.json.delete(url)

    assert response.status_code == 204


def test_api_delete_membership_without_user(client):
    membership_owner = f.MembershipFactory(is_admin=True)
    membership_without_user_one = f.MembershipFactory(project=membership_owner.project, user=None)
    f.MembershipFactory(project=membership_owner.project, user=None)
    client.login(membership_owner.user)
    url = reverse("memberships-detail", args=[membership_without_user_one.id])
    response = client.json.delete(url)

    assert response.status_code == 204


def test_api_create_member_max_pending_memberships(client, settings):
    settings.MAX_PENDING_MEMBERSHIPS = 3
    project = f.ProjectFactory()
    john = f.UserFactory.create()
    tester = f.RoleFactory(project=project, name="Tester")
    f.MembershipFactory(project=project, user=john, is_admin=True)
    f.MembershipFactory(project=project, user=None, email="test1@mail.com")
    f.MembershipFactory(project=project, user=None, email="test2@mail.com")
    f.MembershipFactory(project=project, user=None, email="test3@mail.com")

    url = reverse("memberships-list")
    data = {"project": project.id, "role": tester.id, "username": "joseph@email.com"}
    client.login(john)
    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 400
    assert "limit of pending memberships" in response.data["_error_message"]


def test_api_create_bulk_members_max_pending_memberships(client, settings):
    settings.MAX_PENDING_MEMBERSHIPS = 2
    project = f.ProjectFactory()
    john = f.UserFactory.create()
    joseph = f.UserFactory.create()
    tester = f.RoleFactory(project=project, name="Tester")
    f.MembershipFactory(project=project, user=john, is_admin=True)
    f.MembershipFactory(project=project, user=None, email="test1@mail.com")
    f.MembershipFactory(project=project, user=None, email="test2@mail.com")

    url = reverse("memberships-bulk-create")
    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": tester.id, "username": "joseph@email.com"},
        ]
    }
    client.login(john)
    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 400
    assert "limit of pending memberships" in response.data["_error_message"]


def test_create_memberhips_throttling(client, settings):
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["create-memberships"] = "1/minute"

    membership = f.MembershipFactory(is_admin=True)
    role = f.RoleFactory.create(project=membership.project)
    user = f.UserFactory.create()
    user2 = f.UserFactory.create()

    client.login(membership.user)
    url = reverse("memberships-list")
    data = {"role": role.pk, "project": role.project.pk, "username": user.email}
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 201
    assert response.data["user_email"] == user.email

    data = {"role": role.pk, "project": role.project.pk, "username": user2.email}
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 429
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["create-memberships"] = None


def test_api_resend_invitation_throttling(client, outbox, settings):
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["create-memberships"] = "1/minute"

    invitation = f.create_invitation(user=None)
    f.MembershipFactory(project=invitation.project, user=invitation.project.owner, is_admin=True)
    url = reverse("memberships-resend-invitation", kwargs={"pk": invitation.pk})

    client.login(invitation.project.owner)
    response = client.post(url)

    assert response.status_code == 204
    assert len(outbox) == 1
    assert outbox[0].to == [invitation.email]

    response = client.post(url)

    assert response.status_code == 429
    assert len(outbox) == 1
    assert outbox[0].to == [invitation.email]
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["create-memberships"] = None


def test_api_create_bulk_members_throttling(client, settings):
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["create-memberships"] = "2/minute"

    project = f.ProjectFactory()
    john = f.UserFactory.create()
    joseph = f.UserFactory.create()
    other = f.UserFactory.create()
    tester = f.RoleFactory(project=project, name="Tester", permissions=["view_project"])
    gamer = f.RoleFactory(project=project, name="Gamer", permissions=["view_project"])
    f.MembershipFactory(project=project, user=john, role=tester, is_admin=True)

    # John and Other are members from another project
    project2 = f.ProjectFactory()
    f.MembershipFactory(project=project2, user=john, role=gamer, is_admin=True)
    f.MembershipFactory(project=project2, user=other, role=gamer)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": gamer.pk, "username": joseph.email},
            {"role_id": gamer.pk, "username": other.username},
        ]
    }
    client.login(john)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 200
    response_user_ids = set([u["user"] for u in response.data])
    user_ids = {other.id, joseph.id}
    assert(user_ids.issubset(response_user_ids))

    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 429
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["create-memberships"] = None
