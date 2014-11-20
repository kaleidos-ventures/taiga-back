from unittest import mock
from django.core.urlresolvers import reverse

from taiga.projects import services
from taiga.base.utils import json

from .. import factories as f

import pytest
pytestmark = pytest.mark.django_db


def test_get_members_from_bulk():
    data = [{"role_id": "1", "email": "member1@email.com"},
            {"role_id": "1", "email": "member2@email.com"}]
    members = services.get_members_from_bulk(data, project_id=1)

    assert len(members) == 2
    assert members[0].email == "member1@email.com"
    assert members[1].email == "member2@email.com"


def test_create_members_in_bulk():
    with mock.patch("taiga.projects.services.members.db") as db:
        data = [{"role_id": "1", "email": "member1@email.com"},
                {"role_id": "1", "email": "member2@email.com"}]
        members = services.create_members_in_bulk(data, project_id=1)
        db.save_in_bulk.assert_called_once_with(members, None, None)


def test_api_create_bulk_members(client):
    project = f.ProjectFactory()
    john = f.UserFactory.create()
    joseph = f.UserFactory.create()
    tester = f.RoleFactory(project=project, name="Tester")
    gamer = f.RoleFactory(project=project, name="Gamer")
    membership = f.MembershipFactory(project=project, user=project.owner, is_owner=True)

    url = reverse("memberships-bulk-create")

    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": tester.pk, "email": john.email},
            {"role_id": gamer.pk, "email": joseph.email},
        ]
    }
    client.login(project.owner)
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 200
    assert response.data[0]["email"] == john.email
    assert response.data[1]["email"] == joseph.email

def test_api_create_bulk_members_with_extra_text(client, outbox):
    project = f.ProjectFactory()
    tester = f.RoleFactory(project=project, name="Tester")
    membership = f.MembershipFactory(project=project, user=project.owner, is_owner=True)
    url = reverse("memberships-bulk-create")

    invitation_extra_text = "this is a not so random invitation text"
    data = {
        "project_id": project.id,
        "bulk_memberships": [
            {"role_id": tester.pk, "email": "john@email.com"},
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
    invitation = f.create_invitation()
    membership = f.MembershipFactory(project=invitation.project, user=invitation.project.owner, is_owner=True)
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
    membership = f.MembershipFactory(project=role.project, user=role.project.owner, is_owner=True)

    client.login(role.project.owner)

    url = reverse("memberships-list")
    data = {"role": role.pk, "project": role.project.pk, "email": user.email}

    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 201, response.data
    assert len(outbox) == 1
    assert user.memberships.count() == 1

    message = outbox[0]

    assert message.to == [user.email]
    assert "Added to the project" in message.subject


def test_api_create_invalid_membership_email_failing(client):
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
    data = {"role": role.pk, "project": project.pk, "email": user.email}

    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 400, response.data
    assert response.data["role"][0] == "Invalid role for the project"
    assert user.memberships.count() == 0


def test_api_create_membership(client):
    user = f.UserFactory()
    role = f.RoleFactory.create()
    client.login(role.project.owner)
    url = reverse("memberships-list")
    data = {"role": role.pk, "project": role.project.pk, "email": user.email}
    response = client.json.post(url, json.dumps(data))

    assert response.status_code == 201
    assert response.data["user_email"] == user.email


def test_api_edit_membership(client):
    membership = f.MembershipFactory()
    client.login(membership.project.owner)
    url = reverse("memberships-detail", args=[membership.id])
    data = {"email": "new@email.com"}
    response = client.json.patch(url, json.dumps(data))

    assert response.status_code == 200


def test_api_delete_membership(client):
    membership = f.MembershipFactory()
    client.login(membership.project.owner)
    url = reverse("memberships-detail", args=[membership.id])
    response = client.json.delete(url)

    assert response.status_code == 204
