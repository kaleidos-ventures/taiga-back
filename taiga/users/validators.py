# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos Ventures SL

import bleach

from django.core import validators as core_validators
from django.utils.translation import gettext_lazy as _

from taiga.base.api import serializers
from taiga.base.api import validators
from taiga.base.exceptions import ValidationError
from taiga.base.fields import PgArrayField

from django.contrib.auth.password_validation import validate_password as vp

from .models import User, Role

import re


######################################################
# User
######################################################

class UserValidator(validators.ModelValidator):
    full_name = serializers.CharField(max_length=36)

    class Meta:
        model = User
        fields = ("username", "full_name", "color", "bio", "lang",
                  "theme", "timezone", "is_active")

    def validate_username(self, attrs, source):
        value = attrs[source]
        validator = core_validators.RegexValidator(re.compile(r'^[\w.-]+$'), _("invalid username"),
                                                   _("invalid"))

        try:
            validator(value)
        except ValidationError:
            raise ValidationError(_("Required. 255 characters or fewer. Letters, "
                                    "numbers and /./-/_ characters'"))

        if (self.object and
                self.object.username != value and
                User.objects.filter(username=value).exists()):
            raise ValidationError(_("Invalid username. Try with a different one."))

        return attrs

    def validate_full_name(self, attrs, source):
        value = attrs[source]
        if value != bleach.clean(value):
            raise ValidationError(_("Invalid full name"))

        if re.search(r"http[s]?:", value):
            raise ValidationError(_("Invalid full name"))

        return attrs


class UserAdminValidator(UserValidator):
    class Meta:
        model = User
        # IMPORTANT: Maintain the UserSerializer Meta up to date
        # with this info (including here the email)
        fields = ("username", "full_name", "color", "bio", "lang",
                  "theme", "timezone", "is_active", "email", "read_new_terms")

    def validate_read_new_terms(self, attrs, source):
        value = attrs[source]
        if not value:
            raise ValidationError(
                _("Read new terms has to be true'"))

        return attrs


class RecoveryValidator(validators.Validator):
    token = serializers.CharField(required=True, max_length=200)
    password = serializers.CharField(required=True)
    
    def validate_password(self, attrs, source):
        value = attrs[source]
        vp(value)
        return attrs


class ChangeEmailValidator(validators.Validator):
    email_token = serializers.CharField(max_length=200)


class CancelAccountValidator(validators.Validator):
    cancel_token = serializers.CharField()


######################################################
# Role
######################################################

class RoleValidator(validators.ModelValidator):
    permissions = PgArrayField(required=False)

    class Meta:
        model = Role
        fields = ('id', 'name', 'permissions', 'computable', 'project', 'order')
        i18n_fields = ("name",)


class ProjectRoleValidator(validators.ModelValidator):
    class Meta:
        model = Role
        fields = ('id', 'name', 'slug', 'order', 'computable')
