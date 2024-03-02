# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos Ventures SL

import uuid

from django.apps import apps
from django.utils.translation import gettext as _
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.password_validation import validate_password

from taiga.auth.exceptions import TokenError
from taiga.auth.tokens import CancelToken
from taiga.auth.settings import api_settings as auth_settings
from taiga.base import exceptions as exc
from taiga.base import filters
from taiga.base import response
from taiga.base.utils.dicts import into_namedtuple
from taiga.base.decorators import list_route
from taiga.base.decorators import detail_route
from taiga.base.api.fields import validate_user_email_allowed_domains
from taiga.base.api.mixins import BlockedByProjectMixin
from taiga.base.api.viewsets import ModelCrudViewSet
from taiga.base.api.utils import get_object_or_404
from taiga.base.filters import MembersFilterBackend
from taiga.base.mails import mail_builder
from taiga.users.services import get_user_by_username_or_email
from easy_thumbnails.source_generators import pil_image

from . import models
from . import serializers
from . import validators
from . import permissions
from . import filters as user_filters
from . import services
from . import utils as user_utils
from .signals import user_cancel_account as user_cancel_account_signal
from .signals import user_change_email as user_change_email_signal
from .throttling import UserDetailRateThrottle, UserUpdateRateThrottle

class UsersViewSet(ModelCrudViewSet):
    permission_classes = (permissions.UserPermission,)
    admin_serializer_class = serializers.UserAdminSerializer
    serializer_class = serializers.UserSerializer
    admin_validator_class = validators.UserAdminValidator
    validator_class = validators.UserValidator
    filter_backends = (MembersFilterBackend,)
    throttle_classes = (UserDetailRateThrottle, UserUpdateRateThrottle)
    model = models.User

    def get_serializer_class(self):
        if self.action in ["partial_update", "update", "retrieve", "by_username"]:
            user = self.object
            if self.request.user == user or self.request.user.is_superuser:
                return self.admin_serializer_class

        return self.serializer_class

    def get_validator_class(self):
        if self.action in ["partial_update", "update", "retrieve", "by_username"]:
            user = self.object
            if self.request.user == user or self.request.user.is_superuser:
                return self.admin_validator_class

        return self.validator_class

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.prefetch_related("memberships")
        qs = user_utils.attach_extra_info(qs, user=self.request.user)
        return qs

    def create(self, *args, **kwargs):
        raise exc.NotSupported()

    def list(self, request, *args, **kwargs):
        self.object_list = MembersFilterBackend().filter_queryset(request,
                                                                  self.get_queryset(),
                                                                  self)

        page = self.paginate_queryset(self.object_list)
        if page is not None:
            serializer = self.get_pagination_serializer(page)
        else:
            serializer = self.get_serializer(self.object_list, many=True)

        return response.Ok(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        self.object = get_object_or_404(self.get_queryset(), **kwargs)
        self.check_permissions(request, 'retrieve', self.object)
        serializer = self.get_serializer(self.object)
        return response.Ok(serializer.data)

    # TODO: commit_on_success
    def partial_update(self, request, *args, **kwargs):
        """
        We must detect if the user is trying to change his email so we can
        save that value and generate a token that allows him to validate it in
        the new email account
        """
        user = self.get_object()
        self.check_permissions(request, "update", user)

        new_email = request.DATA.pop('email', None)
        if new_email is not None:
            valid_new_email = True
            duplicated_email = models.User.objects.filter(email=new_email).exists()

            try:
                validate_email(new_email)
                validate_user_email_allowed_domains(new_email)
            except ValidationError:
                valid_new_email = False

            valid_new_email = valid_new_email and new_email != request.user.email

            if duplicated_email:
                raise exc.WrongArguments(_("Duplicated email"))
            elif not valid_new_email:
                raise exc.WrongArguments(_("Invalid email"))

            # We need to generate a token for the email
            request.user.email_token = str(uuid.uuid4())
            request.user.new_email = new_email
            request.user.save(update_fields=["email_token", "new_email"])
            email = mail_builder.change_email(
                request.user.new_email,
                {
                    "user": request.user,
                    "lang": request.user.lang
                }
            )
            email.send()

        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, pk=None):
        user = self.get_object()
        self.check_permissions(request, "destroy", user)
        stream = request.stream
        request_data = stream is not None and stream.GET or None
        user_cancel_account_signal.send(sender=user.__class__, user=user, request_data=request_data)
        user.cancel()
        return response.NoContent()

    @list_route(methods=["GET"])
    def by_username(self, request, *args, **kwargs):
        username = request.QUERY_PARAMS.get("username", None)
        return self.retrieve(request, username=username)

    @list_route(methods=["POST"])
    def password_recovery(self, request, pk=None):
        username_or_email = request.DATA.get('username', None)

        self.check_permissions(request, "password_recovery", None)

        if not username_or_email:
            raise exc.WrongArguments(_("Invalid username or email"))

        user = get_user_by_username_or_email(username_or_email)
        user.token = str(uuid.uuid4())
        user.save(update_fields=["token"])

        email = mail_builder.password_recovery(user, {"user": user})
        email.send()

        return response.Ok({"detail": _("Mail sent successfully!")})

    @list_route(methods=["POST"])
    def change_password_from_recovery(self, request, pk=None):
        """
        Change password with token (from password recovery step).
        """

        self.check_permissions(request, "change_password_from_recovery", None)

        validator = validators.RecoveryValidator(data=request.DATA, many=False)
        if not validator.is_valid():
            return response.BadRequest(validator.errors)

        try:
            user = models.User.objects.get(token=validator.data["token"])
        except models.User.DoesNotExist:
            raise exc.WrongArguments(_("Token is invalid"))

        user.set_password(validator.data["password"])
        user.token = None
        user.save(update_fields=["password", "token"])

        return response.NoContent()

    @list_route(methods=["POST"])
    def change_password(self, request, pk=None):
        """
        Change password to current logged user.
        """
        self.check_permissions(request, "change_password", None)

        current_password = request.DATA.get("current_password")
        password = request.DATA.get("password")

        # NOTE: GitHub users have no password yet (request.user.password == '') so
        #       current_password can be None
        if not current_password and request.user.password:
            raise exc.WrongArguments(_("Current password parameter needed"))

        if not password:
            raise exc.WrongArguments(_("New password parameter needed"))

        try:
            validate_password(password)
         except ValidationError as e: 
            raise exc.WrongArguments(_(str(e.error_list)))

        if current_password and not request.user.check_password(current_password):
            raise exc.WrongArguments(_("Invalid current password"))

        request.user.set_password(password)
        request.user.save(update_fields=["password"])
        return response.NoContent()

    @list_route(methods=["POST"])
    def change_avatar(self, request):
        """
        Change avatar to current logged user.
        """
        self.check_permissions(request, "change_avatar", None)

        avatar = request.FILES.get('avatar', None)

        if not avatar:
            raise exc.WrongArguments(_("Incomplete arguments"))

        try:
            pil_image(avatar)
        except Exception:
            raise exc.WrongArguments(_("Invalid image format"))

        request.user.photo = avatar
        request.user.save(update_fields=["photo"])
        user_data = self.admin_serializer_class(request.user).data

        return response.Ok(user_data)

    @list_route(methods=["POST"])
    def remove_avatar(self, request):
        """
        Remove the avatar of current logged user.
        """
        self.check_permissions(request, "remove_avatar", None)
        request.user.photo = None
        request.user.save(update_fields=["photo"])
        user_data = self.admin_serializer_class(request.user).data
        return response.Ok(user_data)

    @list_route(methods=["POST"])
    def change_email(self, request, pk=None):
        """
        Verify the email change to current logged user.
        """
        validator = validators.ChangeEmailValidator(data=request.DATA, many=False)
        if not validator.is_valid():
            return response.BadRequest(validator.errors)

        try:
            user = models.User.objects.get(email_token=validator.data["email_token"])
        except models.User.DoesNotExist:
            raise exc.WrongArguments(_("Invalid, are you sure the token is correct and you "
                                       "didn't use it before?"))

        self.check_permissions(request, "change_email", user)

        old_email = user.email
        new_email = user.new_email

        user.email = new_email
        user.new_email = None
        user.email_token = None
        user.verified_email = True
        user.save(update_fields=["email", "new_email", "email_token", "verified_email"])

        user_change_email_signal.send(sender=user.__class__,
                                      user=user,
                                      old_email=old_email,
                                      new_email=new_email)

        # If the user changes their email, the application will ask again if they
        # want to subscribe to the Taiga newsletter.
        user.storage_entries.filter(key="dont_ask_premise_newsletter").delete()

        return response.NoContent()

    @list_route(methods=["GET"])
    def me(self, request, pk=None):
        """
        Get me.
        """
        self.check_permissions(request, "me", None)
        user_data = self.admin_serializer_class(request.user).data
        return response.Ok(user_data)

    @list_route(methods=["POST"])
    def cancel(self, request, pk=None):
        """
        Cancel an account via token
        """
        validator = validators.CancelAccountValidator(data=request.DATA, many=False)
        if not validator.is_valid():
            raise exc.WrongArguments(_("Invalid, are you sure the token is correct?"))

        try:
            validated_token = CancelToken(token=validator.data["cancel_token"])
            user_id_value = validated_token[auth_settings.USER_ID_CLAIM]
            user = models.User.objects.get(**{auth_settings.USER_ID_FIELD: user_id_value})
        except (exc.NotAuthenticated, models.User.DoesNotExist, TokenError, KeyError):
            raise exc.WrongArguments(_("Invalid, are you sure the token is correct?"))

        if not user.is_active:
            raise exc.WrongArguments(_("Invalid, are you sure the token is correct?"))

        user.cancel()
        return response.NoContent()

    @list_route(methods=["POST"])
    def export(self, request, pk=None):
        """
        Export user data and photo
        """
        file_url = services.export_profile(request.user)

        response_data = {
            "url": file_url
        }
        return response.Ok(response_data)

    @list_route(methods=["POST"])
    def send_verification_email(self, request, pk=None):
        """Send email to verify the user email address."""
        self.check_permissions(request, "send_verification_email", None)
        if request.user.verified_email is True:
            raise exc.BadRequest(_("Email address already verified"))
        if not request.user.email_token or request.user.email != request.user.new_email:
            raise exc.BadRequest(_("Unable to verify this email address"))
        email = mail_builder.send_verification(request.user, {"user": request.user})
        email.send()
        return response.Ok({"detail": _("Mail sended successful!")})

    @detail_route(methods=["GET"])
    def contacts(self, request, *args, **kwargs):
        user = get_object_or_404(models.User, **kwargs)
        self.check_permissions(request, 'contacts', user)

        self.object_list = user_filters.ContactsFilterBackend().filter_queryset(
            user, request, self.get_queryset(), self).extra(
            select={"complete_user_name": "concat(full_name, username)"}).order_by("complete_user_name")

        page = self.paginate_queryset(self.object_list)
        if page is not None:
            serializer = self.serializer_class(page.object_list, many=True)
        else:
            serializer = self.serializer_class(self.object_list, many=True)

        return response.Ok(serializer.data)

    @detail_route(methods=["GET"])
    def stats(self, request, *args, **kwargs):
        user = get_object_or_404(models.User, **kwargs)
        self.check_permissions(request, "stats", user)
        return response.Ok(services.get_stats_for_user(user, request.user))

    @detail_route(methods=["GET"])
    def watched(self, request, *args, **kwargs):
        for_user = get_object_or_404(models.User, **kwargs)
        from_user = request.user
        self.check_permissions(request, 'watched', for_user)
        filters = {
            "type": request.GET.get("type", None),
            "q": request.GET.get("q", None),
        }

        self.object_list = services.get_watched_list(for_user, from_user, **filters)
        page = self.paginate_queryset(self.object_list)
        elements = page.object_list if page is not None else self.object_list

        extra_args_liked = {
            "user_watching": services.get_watched_content_for_user(request.user),
            "user_likes": services.get_liked_content_for_user(request.user),
        }

        extra_args_voted = {
            "user_watching": services.get_watched_content_for_user(request.user),
            "user_votes": services.get_voted_content_for_user(request.user),
        }

        response_data = []
        for elem in elements:
            if elem["type"] == "project":
                # projects are liked objects
                response_data.append(serializers.LikedObjectSerializer(into_namedtuple(elem), **extra_args_liked).data)
            else:
                # stories, tasks and issues are voted objects
                response_data.append(serializers.VotedObjectSerializer(into_namedtuple(elem), **extra_args_voted).data)

        return response.Ok(response_data)

    @detail_route(methods=["GET"])
    def liked(self, request, *args, **kwargs):
        for_user = get_object_or_404(models.User, **kwargs)
        from_user = request.user
        self.check_permissions(request, 'liked', for_user)
        filters = {
            "q": request.GET.get("q", None),
        }

        self.object_list = services.get_liked_list(for_user, from_user, **filters)
        page = self.paginate_queryset(self.object_list)
        elements = page.object_list if page is not None else self.object_list

        extra_args = {
            "user_watching": services.get_watched_content_for_user(request.user),
            "user_likes": services.get_liked_content_for_user(request.user),
        }

        response_data = [serializers.LikedObjectSerializer(into_namedtuple(elem), **extra_args).data for elem in elements]

        return response.Ok(response_data)

    @detail_route(methods=["GET"])
    def voted(self, request, *args, **kwargs):
        for_user = get_object_or_404(models.User, **kwargs)
        from_user = request.user
        self.check_permissions(request, 'liked', for_user)
        filters = {
            "type": request.GET.get("type", None),
            "q": request.GET.get("q", None),
        }

        self.object_list = services.get_voted_list(for_user, from_user, **filters)
        page = self.paginate_queryset(self.object_list)
        elements = page.object_list if page is not None else self.object_list

        extra_args = {
            "user_watching": services.get_watched_content_for_user(request.user),
            "user_votes": services.get_voted_content_for_user(request.user),
        }

        response_data = [serializers.VotedObjectSerializer(into_namedtuple(elem), **extra_args).data for elem in elements]

        return response.Ok(response_data)


######################################################
# Role
######################################################
class RolesViewSet(BlockedByProjectMixin, ModelCrudViewSet):
    model = models.Role
    serializer_class = serializers.RoleSerializer
    validator_class = validators.RoleValidator
    permission_classes = (permissions.RolesPermission, )
    filter_backends = (filters.CanViewProjectFilterBackend,)
    filter_fields = ('project',)

    def pre_delete(self, obj):
        move_to = self.request.QUERY_PARAMS.get('moveTo', None)
        if move_to:
            membership_model = apps.get_model("projects", "Membership")
            role_dest = get_object_or_404(self.model, project=obj.project, id=move_to)
            qs = membership_model.objects.filter(project_id=obj.project.pk, role=obj)
            qs.update(role=role_dest)

        super().pre_delete(obj)
