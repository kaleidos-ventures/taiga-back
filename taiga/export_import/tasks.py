# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import datetime
import logging
import sys
import gzip

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone

from django.conf import settings
from django.utils.translation import gettext as _

from taiga.base.mails import mail_builder
from taiga.base.utils import json
from taiga.celery import app

from . import exceptions as err
from . import services
from .renderers import ExportRenderer

logger = logging.getLogger('taiga.export_import')


@app.task(bind=True)
def dump_project(self, user, project, dump_format):
    try:
        if dump_format == "gzip":
            path = "exports/{}/{}-{}.json.gz".format(project.pk, project.slug, self.request.id)
            with default_storage.open(path, mode="wb") as outfile:
                services.render_project(project, gzip.GzipFile(fileobj=outfile, mode="wb"))
        else:
            path = "exports/{}/{}-{}.json".format(project.pk, project.slug, self.request.id)
            with default_storage.open(path, mode="wb") as outfile:
                services.render_project(project, outfile)

        url = default_storage.url(path)

    except Exception:
        # Error
        ctx = {
            "user": user,
            "error_subject": _("Error generating project dump"),
            "error_message": _("Error generating project dump"),
            "project": project
        }
        email = mail_builder.export_error(user, ctx)
        email.send()
        logger.error('Error generating dump %s (by %s)', project.slug, user, exc_info=sys.exc_info())
    else:
        # Success
        deletion_date = timezone.now() + datetime.timedelta(seconds=settings.EXPORTS_TTL)
        ctx = {
            "url": url,
            "project": project,
            "user": user,
            "deletion_date": deletion_date
        }
        email = mail_builder.dump_project(user, ctx)
        email.send()


@app.task
def delete_project_dump(project_id, project_slug, task_id, dump_format):
    if dump_format == "gzip":
        path = "exports/{}/{}-{}.json.gz".format(project_id, project_slug, task_id)
    else:
        path = "exports/{}/{}-{}.json".format(project_id, project_slug, task_id)
    default_storage.delete(path)


ADMIN_ERROR_LOAD_PROJECT_DUMP_MESSAGE = _("""

Error loading dump by {user_full_name} <{user_email}>:"


REASON:
-------
{reason}

DETAILS:
--------
{details}

TRACE ERROR:
------------""")


@app.task
def load_project_dump(user, dump):
    try:
        project = services.store_project_from_dict(dump, user)
    except err.TaigaImportError as e:
        # On Error
        ## remove project
        if e.project:
            e.project.delete_related_content()
            e.project.delete()

        ## send email to the user
        error_subject = _("Error loading project dump")
        error_message = e.message or _("Error loading your project dump file")

        ctx = {
            "user": user,
            "error_subject": error_message,
            "error_message": error_subject,
            "details": json.dumps(e.errors, indent=4)
        }
        email = mail_builder.import_error(user, ctx)
        email.send()

        ## logged the error to sysadmins
        text = ADMIN_ERROR_LOAD_PROJECT_DUMP_MESSAGE.format(
            user_full_name=user,
            user_email=user.email,
            reason=e.message or _("  -- no detail info --"),
            details=json.dumps(e.errors, indent=4)
        )
        logger.error(text, exc_info=sys.exc_info())

    else:
        # On Success
        ctx = {"user": user, "project": project}
        email = mail_builder.load_dump(user, ctx)
        email.send()
