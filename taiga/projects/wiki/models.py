# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django_pglocks import advisory_lock

from taiga.base.utils.slug import slugify_uniquely_for_queryset
from taiga.base.utils.time import timestamp_ms
from taiga.projects.notifications.mixins import WatchedModelMixin
from taiga.projects.occ import OCCModelMixin


class WikiPage(OCCModelMixin, WatchedModelMixin, models.Model):
    project = models.ForeignKey(
        "projects.Project",
        null=False,
        blank=False,
        related_name="wiki_pages",
        verbose_name=_("project"),
        on_delete=models.CASCADE
    )
    slug = models.SlugField(max_length=500, db_index=True, null=False, blank=False,
                            verbose_name=_("slug"), allow_unicode=True)
    content = models.TextField(null=False, blank=True,
                               verbose_name=_("content"))
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="owned_wiki_pages",
        verbose_name=_("owner"),
        on_delete=models.SET_NULL,
    )
    last_modifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="last_modified_wiki_pages",
        verbose_name=_("last modifier"),
        on_delete=models.SET_NULL,
    )
    created_date = models.DateTimeField(null=False, blank=False,
                                        verbose_name=_("created date"),
                                        default=timezone.now)
    modified_date = models.DateTimeField(null=False, blank=False,
                                         verbose_name=_("modified date"))
    attachments = GenericRelation("attachments.Attachment")
    _importing = None

    class Meta:
        verbose_name = "wiki page"
        verbose_name_plural = "wiki pages"
        ordering = ["project", "slug"]
        unique_together = ("project", "slug",)

    def __str__(self):
        return "project {0} - {1}".format(self.project_id, self.slug)

    def save(self, *args, **kwargs):
        if not self._importing or not self.modified_date:
            self.modified_date = timezone.now()

        return super().save(*args, **kwargs)


class WikiLink(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        null=False,
        blank=False,
        related_name="wiki_links",
        verbose_name=_("project"),
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=500, null=False, blank=False)
    href = models.SlugField(max_length=500, db_index=True, null=False, blank=False,
                            verbose_name=_("href"))
    order = models.BigIntegerField(null=False, blank=False, default=timestamp_ms,
                                             verbose_name=_("order"))

    class Meta:
        verbose_name = "wiki link"
        verbose_name_plural = "wiki links"
        ordering = ["project", "order", "id"]
        unique_together = ("project", "href")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.href:
            with advisory_lock("wiki-page-creation-{}".format(self.project_id)):
                wl_qs = self.project.wiki_links.all()
                self.href = slugify_uniquely_for_queryset(self.title, wl_qs, slugfield="href")
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
