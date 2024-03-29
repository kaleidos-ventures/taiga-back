# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

from django.urls import reverse

from taiga.base.utils import json
from taiga.projects import choices as project_choices
from taiga.projects.custom_attributes import serializers
from taiga.permissions.choices import (MEMBERS_PERMISSIONS,
                                           ANON_PERMISSIONS)

from tests import factories as f
from tests.utils import helper_test_http_method

import pytest
pytestmark = pytest.mark.django_db


@pytest.fixture
def data():
    m = type("Models", (object,), {})
    m.registered_user = f.UserFactory.create()
    m.project_member_with_perms = f.UserFactory.create()
    m.project_member_without_perms = f.UserFactory.create()
    m.project_owner = f.UserFactory.create()
    m.other_user = f.UserFactory.create()
    m.superuser = f.UserFactory.create(is_superuser=True)

    m.public_project = f.ProjectFactory(is_private=False,
                                        anon_permissions=list(map(lambda x: x[0], ANON_PERMISSIONS)),
                                        public_permissions=list(map(lambda x: x[0], ANON_PERMISSIONS)),
                                        owner=m.project_owner)
    m.private_project1 = f.ProjectFactory(is_private=True,
                                          anon_permissions=list(map(lambda x: x[0], ANON_PERMISSIONS)),
                                          public_permissions=list(map(lambda x: x[0], ANON_PERMISSIONS)),
                                          owner=m.project_owner)
    m.private_project2 = f.ProjectFactory(is_private=True,
                                          anon_permissions=[],
                                          public_permissions=[],
                                          owner=m.project_owner)
    m.blocked_project = f.ProjectFactory(is_private=True,
                                         anon_permissions=[],
                                         public_permissions=[],
                                         owner=m.project_owner,
                                         blocked_code=project_choices.BLOCKED_BY_STAFF)

    m.public_membership = f.MembershipFactory(project=m.public_project,
                                          user=m.project_member_with_perms,
                                          email=m.project_member_with_perms.email,
                                          role__project=m.public_project,
                                          role__permissions=list(map(lambda x: x[0], MEMBERS_PERMISSIONS)))
    m.private_membership1 = f.MembershipFactory(project=m.private_project1,
                                                user=m.project_member_with_perms,
                                                email=m.project_member_with_perms.email,
                                                role__project=m.private_project1,
                                                role__permissions=list(map(lambda x: x[0], MEMBERS_PERMISSIONS)))

    f.MembershipFactory(project=m.private_project1,
                        user=m.project_member_without_perms,
                        email=m.project_member_without_perms.email,
                        role__project=m.private_project1,
                        role__permissions=[])

    m.private_membership2 = f.MembershipFactory(project=m.private_project2,
                                                user=m.project_member_with_perms,
                                                email=m.project_member_with_perms.email,
                                                role__project=m.private_project2,
                                                role__permissions=list(map(lambda x: x[0], MEMBERS_PERMISSIONS)))
    f.MembershipFactory(project=m.private_project2,
                        user=m.project_member_without_perms,
                        email=m.project_member_without_perms.email,
                        role__project=m.private_project2,
                        role__permissions=[])

    m.blocked_membership = f.MembershipFactory(project=m.blocked_project,
                                                user=m.project_member_with_perms,
                                                email=m.project_member_with_perms.email,
                                                role__project=m.blocked_project,
                                                role__permissions=list(map(lambda x: x[0], MEMBERS_PERMISSIONS)))
    f.MembershipFactory(project=m.blocked_project,
                        user=m.project_member_without_perms,
                        email=m.project_member_without_perms.email,
                        role__project=m.blocked_project,
                        role__permissions=[])

    f.MembershipFactory(project=m.public_project,
                        user=m.project_owner,
                        is_admin=True)

    f.MembershipFactory(project=m.private_project1,
                        user=m.project_owner,
                        is_admin=True)

    f.MembershipFactory(project=m.private_project2,
                        user=m.project_owner,
                        is_admin=True)

    f.MembershipFactory(project=m.blocked_project,
                        user=m.project_owner,
                        is_admin=True)

    m.public_epic_ca = f.EpicCustomAttributeFactory(project=m.public_project)
    m.private_epic_ca1 = f.EpicCustomAttributeFactory(project=m.private_project1)
    m.private_epic_ca2 = f.EpicCustomAttributeFactory(project=m.private_project2)
    m.blocked_epic_ca = f.EpicCustomAttributeFactory(project=m.blocked_project)

    m.public_epic = f.EpicFactory(project=m.public_project,
                                  status__project=m.public_project)
    m.private_epic1 = f.EpicFactory(project=m.private_project1,
                                    status__project=m.private_project1)
    m.private_epic2 = f.EpicFactory(project=m.private_project2,
                                    status__project=m.private_project2)
    m.blocked_epic = f.EpicFactory(project=m.blocked_project,
                                    status__project=m.blocked_project)

    m.public_epic_cav = m.public_epic.custom_attributes_values
    m.private_epic_cav1 = m.private_epic1.custom_attributes_values
    m.private_epic_cav2 = m.private_epic2.custom_attributes_values
    m.blocked_epic_cav = m.blocked_epic.custom_attributes_values

    return m


#########################################################
# Epic Custom Attribute
#########################################################

def test_epic_custom_attribute_retrieve(client, data):
    public_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.public_epic_ca.pk})
    private1_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.private_epic_ca1.pk})
    private2_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.private_epic_ca2.pk})
    blocked_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.blocked_epic_ca.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    results = helper_test_http_method(client, 'get', public_url, None, users)
    assert results == [200, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'get', private1_url, None, users)
    assert results == [200, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'get', private2_url, None, users)
    assert results == [401, 403, 403, 200, 200]
    results = helper_test_http_method(client, 'get', blocked_url, None, users)
    assert results == [401, 403, 403, 200, 200]


def test_epic_custom_attribute_create(client, data):
    public_url = reverse('epic-custom-attributes-list')
    private1_url = reverse('epic-custom-attributes-list')
    private2_url = reverse('epic-custom-attributes-list')
    blocked_url = reverse('epic-custom-attributes-list')

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    epic_ca_data = {"name": "test-new", "project": data.public_project.id}
    epic_ca_data = json.dumps(epic_ca_data)
    results = helper_test_http_method(client, 'post', public_url, epic_ca_data, users)
    assert results == [401, 403, 403, 403, 201]

    epic_ca_data = {"name": "test-new", "project": data.private_project1.id}
    epic_ca_data = json.dumps(epic_ca_data)
    results = helper_test_http_method(client, 'post', private1_url, epic_ca_data, users)
    assert results == [401, 403, 403, 403, 201]

    epic_ca_data = {"name": "test-new", "project": data.private_project2.id}
    epic_ca_data = json.dumps(epic_ca_data)
    results = helper_test_http_method(client, 'post', private2_url, epic_ca_data, users)
    assert results == [401, 403, 403, 403, 201]

    epic_ca_data = {"name": "test-new", "project": data.blocked_project.id}
    epic_ca_data = json.dumps(epic_ca_data)
    results = helper_test_http_method(client, 'post', blocked_url, epic_ca_data, users)
    assert results == [401, 403, 403, 403, 451]


def test_epic_custom_attribute_update(client, data):
    public_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.public_epic_ca.pk})
    private1_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.private_epic_ca1.pk})
    private2_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.private_epic_ca2.pk})
    blocked_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.blocked_epic_ca.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    epic_ca_data = serializers.EpicCustomAttributeSerializer(data.public_epic_ca).data
    epic_ca_data["name"] = "test"
    epic_ca_data = json.dumps(epic_ca_data)
    results = helper_test_http_method(client, 'put', public_url, epic_ca_data, users)
    assert results == [401, 403, 403, 403, 200]

    epic_ca_data = serializers.EpicCustomAttributeSerializer(data.private_epic_ca1).data
    epic_ca_data["name"] = "test"
    epic_ca_data = json.dumps(epic_ca_data)
    results = helper_test_http_method(client, 'put', private1_url, epic_ca_data, users)
    assert results == [401, 403, 403, 403, 200]

    epic_ca_data = serializers.EpicCustomAttributeSerializer(data.private_epic_ca2).data
    epic_ca_data["name"] = "test"
    epic_ca_data = json.dumps(epic_ca_data)
    results = helper_test_http_method(client, 'put', private2_url, epic_ca_data, users)
    assert results == [401, 403, 403, 403, 200]

    epic_ca_data = serializers.EpicCustomAttributeSerializer(data.blocked_epic_ca).data
    epic_ca_data["name"] = "test"
    epic_ca_data = json.dumps(epic_ca_data)
    results = helper_test_http_method(client, 'put', private2_url, epic_ca_data, users)
    assert results == [401, 403, 403, 403, 451]


def test_epic_custom_attribute_delete(client, data):
    public_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.public_epic_ca.pk})
    private1_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.private_epic_ca1.pk})
    private2_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.private_epic_ca2.pk})
    blocked_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.blocked_epic_ca.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    results = helper_test_http_method(client, 'delete', public_url, None, users)
    assert results == [401, 403, 403, 403, 204]
    results = helper_test_http_method(client, 'delete', private1_url, None, users)
    assert results == [401, 403, 403, 403, 204]
    results = helper_test_http_method(client, 'delete', private2_url, None, users)
    assert results == [401, 403, 403, 403, 204]
    results = helper_test_http_method(client, 'delete', blocked_url, None, users)
    assert results == [401, 403, 403, 403, 451]



def test_epic_custom_attribute_list(client, data):
    url = reverse('epic-custom-attributes-list')

    response = client.json.get(url)
    assert len(response.data) == 2
    assert response.status_code == 200

    client.login(data.registered_user)
    response = client.json.get(url)
    assert len(response.data) == 2
    assert response.status_code == 200

    client.login(data.project_member_without_perms)
    response = client.json.get(url)
    assert len(response.data) == 2
    assert response.status_code == 200

    client.login(data.project_member_with_perms)
    response = client.json.get(url)
    assert len(response.data) == 4
    assert response.status_code == 200

    client.login(data.project_owner)
    response = client.json.get(url)
    assert len(response.data) == 4
    assert response.status_code == 200


def test_epic_custom_attribute_patch(client, data):
    public_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.public_epic_ca.pk})
    private1_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.private_epic_ca1.pk})
    private2_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.private_epic_ca2.pk})
    blocked_url = reverse('epic-custom-attributes-detail', kwargs={"pk": data.blocked_epic_ca.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    results = helper_test_http_method(client, 'patch', public_url, '{"name": "Test"}', users)
    assert results == [401, 403, 403, 403, 200]
    results = helper_test_http_method(client, 'patch', private1_url, '{"name": "Test"}', users)
    assert results == [401, 403, 403, 403, 200]
    results = helper_test_http_method(client, 'patch', private2_url, '{"name": "Test"}', users)
    assert results == [401, 403, 403, 403, 200]
    results = helper_test_http_method(client, 'patch', blocked_url, '{"name": "Test"}', users)
    assert results == [401, 403, 403, 403, 451]


def test_epic_custom_attribute_action_bulk_update_order(client, data):
    url = reverse('epic-custom-attributes-bulk-update-order')

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    post_data = json.dumps({
        "bulk_epic_custom_attributes": [(1,2)],
        "project": data.public_project.pk
    })
    results = helper_test_http_method(client, 'post', url, post_data, users)
    assert results == [401, 403, 403, 403, 204]

    post_data = json.dumps({
        "bulk_epic_custom_attributes": [(1,2)],
        "project": data.private_project1.pk
    })
    results = helper_test_http_method(client, 'post', url, post_data, users)
    assert results == [401, 403, 403, 403, 204]

    post_data = json.dumps({
        "bulk_epic_custom_attributes": [(1,2)],
        "project": data.private_project2.pk
    })
    results = helper_test_http_method(client, 'post', url, post_data, users)
    assert results == [401, 403, 403, 403, 204]

    post_data = json.dumps({
        "bulk_epic_custom_attributes": [(1,2)],
        "project": data.blocked_project.pk
    })
    results = helper_test_http_method(client, 'post', url, post_data, users)
    assert results == [401, 403, 403, 403, 451]

#########################################################
# Epic Custom Attribute
#########################################################


def test_epic_custom_attributes_values_retrieve(client, data):
    public_url = reverse('epic-custom-attributes-values-detail', kwargs={"epic_id": data.public_epic.pk})
    private_url1 = reverse('epic-custom-attributes-values-detail', kwargs={"epic_id": data.private_epic1.pk})
    private_url2 = reverse('epic-custom-attributes-values-detail', kwargs={"epic_id": data.private_epic2.pk})
    blocked_url = reverse('epic-custom-attributes-values-detail', kwargs={"epic_id": data.blocked_epic.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    results = helper_test_http_method(client, 'get', public_url, None, users)
    assert results == [200, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'get', private_url1, None, users)
    assert results == [200, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'get', private_url2, None, users)
    assert results == [401, 403, 403, 200, 200]
    results = helper_test_http_method(client, 'get', blocked_url, None, users)
    assert results == [401, 403, 403, 200, 200]


def test_epic_custom_attributes_values_update(client, data):
    public_url = reverse('epic-custom-attributes-values-detail', kwargs={"epic_id": data.public_epic.pk})
    private_url1 = reverse('epic-custom-attributes-values-detail', kwargs={"epic_id": data.private_epic1.pk})
    private_url2 = reverse('epic-custom-attributes-values-detail', kwargs={"epic_id": data.private_epic2.pk})
    blocked_url = reverse('epic-custom-attributes-values-detail', kwargs={"epic_id": data.blocked_epic.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    epic_data = serializers.EpicCustomAttributesValuesSerializer(data.public_epic_cav).data
    epic_data["attributes_values"] = {str(data.public_epic_ca.pk): "test"}
    epic_data = json.dumps(epic_data)
    results = helper_test_http_method(client, 'put', public_url, epic_data, users)
    assert results == [401, 403, 403, 200, 200]

    epic_data = serializers.EpicCustomAttributesValuesSerializer(data.private_epic_cav1).data
    epic_data["attributes_values"] = {str(data.private_epic_ca1.pk): "test"}
    epic_data = json.dumps(epic_data)
    results = helper_test_http_method(client, 'put', private_url1, epic_data, users)
    assert results == [401, 403, 403, 200, 200]

    epic_data = serializers.EpicCustomAttributesValuesSerializer(data.private_epic_cav2).data
    epic_data["attributes_values"] = {str(data.private_epic_ca2.pk): "test"}
    epic_data = json.dumps(epic_data)
    results = helper_test_http_method(client, 'put', private_url2, epic_data, users)
    assert results == [401, 403, 403, 200, 200]

    epic_data = serializers.EpicCustomAttributesValuesSerializer(data.blocked_epic_cav).data
    epic_data["attributes_values"] = {str(data.blocked_epic_ca.pk): "test"}
    epic_data = json.dumps(epic_data)
    results = helper_test_http_method(client, 'put', blocked_url, epic_data, users)
    assert results == [401, 403, 403, 451, 451]


def test_epic_custom_attributes_values_patch(client, data):
    public_url = reverse('epic-custom-attributes-values-detail', kwargs={"epic_id": data.public_epic.pk})
    private_url1 = reverse('epic-custom-attributes-values-detail', kwargs={"epic_id": data.private_epic1.pk})
    private_url2 = reverse('epic-custom-attributes-values-detail', kwargs={"epic_id": data.private_epic2.pk})
    blocked_url = reverse('epic-custom-attributes-values-detail', kwargs={"epic_id": data.blocked_epic.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    patch_data = json.dumps({"attributes_values": {str(data.public_epic_ca.pk): "test"},
                             "version": data.public_epic.version})
    results = helper_test_http_method(client, 'patch', public_url, patch_data, users)
    assert results == [401, 403, 403, 200, 200]

    patch_data = json.dumps({"attributes_values": {str(data.private_epic_ca1.pk): "test"},
                             "version": data.private_epic1.version})
    results = helper_test_http_method(client, 'patch', private_url1, patch_data, users)
    assert results == [401, 403, 403, 200, 200]

    patch_data = json.dumps({"attributes_values": {str(data.private_epic_ca2.pk): "test"},
                             "version": data.private_epic2.version})
    results = helper_test_http_method(client, 'patch', private_url2, patch_data, users)
    assert results == [401, 403, 403, 200, 200]

    patch_data = json.dumps({"attributes_values": {str(data.blocked_epic_ca.pk): "test"},
                             "version": data.blocked_epic.version})
    results = helper_test_http_method(client, 'patch', blocked_url, patch_data, users)
    assert results == [401, 403, 403, 451, 451]
