# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import errno

from django.conf import settings
from django.core.files import storage

import django_sites as sites
import os

class FileSystemStorage(storage.FileSystemStorage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if settings.MEDIA_URL.startswith("/"):
            site = sites.get_current()
            url_tmpl = "{scheme}//{domain}{url}"
            scheme = site.scheme and "{0}:".format(site.scheme) or ""
            self.base_url = url_tmpl.format(scheme=scheme, domain=site.domain,
                                            url=settings.MEDIA_URL)

    def open(self, name, mode='rb'):
        """
        Let's create the needed directory structrue before opening the file
        """

        # Create any intermediate directories that do not exist.
        # Note that there is a race between os.path.exists and os.makedirs:
        # if os.makedirs fails with EEXIST, the directory was created
        # concurrently, and we can continue normally. Refs #16082.
        directory = os.path.join(settings.MEDIA_ROOT, os.path.dirname(name))
        if not os.path.exists(directory):
            try:
                if self.directory_permissions_mode is not None:
                    # os.makedirs applies the global umask, so we reset it,
                    # for consistency with file_permissions_mode behavior.
                    old_umask = os.umask(0)
                    try:
                        os.makedirs(directory, self.directory_permissions_mode)
                    finally:
                        os.umask(old_umask)
                else:
                    os.makedirs(directory)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
        if not os.path.isdir(directory):
            raise IOError("%s exists and is not a directory." % directory)

        return super().open(name, mode=mode)
