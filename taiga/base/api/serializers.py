# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

# The code is partially taken (and modified) from django rest framework
# that is licensed under the following terms:
#
# Copyright (c) 2011-2014, Tom Christie
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
# Redistributions in binary form must reproduce the above copyright notice, this
# list of conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""
Serializers and ModelSerializers are similar to Forms and ModelForms.
Unlike forms, they are not constrained to dealing with HTML output, and
form encoded input.

Serialization in REST framework is a two-phase process:

1. Serializers marshal between complex types like model instances, and
python primitives.
2. The process of marshalling between python primitives and request and
response content is handled by parsers and renderers.
"""
from decimal import Decimal
from django.apps import apps
from django.core.paginator import Page
from django.db import models
from django.forms import widgets
import six
from django.utils.translation import gettext as _

from .settings import api_settings

from collections import OrderedDict
import copy
import datetime
import inspect
import types
import serpy

# Note: We do the following so that users of the framework can use this style:
#
#     example_field = serializers.CharField(...)
#
# This helps keep the separation between model fields, form fields, and
# serializer fields more explicit.

from taiga.base.exceptions import ValidationError

from .relations import *
from .fields import *


def _resolve_model(obj):
    """
    Resolve supplied `obj` to a Django model class.

    `obj` must be a Django model class itself, or a string
    representation of one. Useful in situtations like GH #1225 where
    Django may not have resolved a string-based reference to a model in
    another model's foreign key definition.

    String representations should have the format:
        'appname.ModelName'
    """
    if type(obj) == str and len(obj.split(".")) == 2:
        app_name, model_name = obj.split(".")
        return apps.get_model(app_name, model_name)
    elif inspect.isclass(obj) and issubclass(obj, models.Model):
        return obj
    else:
        raise ValueError("{0} is not a Django model".format(obj))


def pretty_name(name):
    """Converts 'first_name' to 'First name'"""
    if not name:
        return ""
    return name.replace("_", " ").capitalize()


class RelationsList(list):
    _deleted = []


class NestedValidationError(ValidationError):
    """
    The default ValidationError behavior is to stringify each item in the list
    if the messages are a list of error messages.

    In the case of nested serializers, where the parent has many children,
    then the child's `serializer.errors` will be a list of dicts. In the case
    of a single child, the `serializer.errors` will be a dict.

    We need to override the default behavior to get properly nested error dicts.
    """

    def __init__(self, message):
        if isinstance(message, dict):
            self._messages = [message]
        else:
            self._messages = message

    @property
    def messages(self):
        return self._messages


class DictWithMetadata(dict):
    """
    A dict-like object, that can have additional properties attached.
    """
    def __getstate__(self):
        """
        Used by pickle (e.g., caching).
        Overridden to remove the metadata from the dict, since it shouldn't be
        pickled and may in some instances be unpickleable.
        """
        return dict(self)


class OrderedDictWithMetadata(OrderedDict):
    """
    A sorted dict-like object, that can have additional properties attached.
    """
    def __getstate__(self):
        """
        Used by pickle (e.g., caching).
        Overriden to remove the metadata from the dict, since it shouldn't be
        pickle and may in some instances be unpickleable.
        """
        return OrderedDict(self).__dict__


def _is_protected_type(obj):
    """
    True if the object is a native datatype that does not need to
    be serialized further.
    """
    return obj is None or isinstance(obj, (
        int,
        datetime.datetime, datetime.date, datetime.time,
        float, Decimal,
        str)
    )


def _get_declared_fields(bases, attrs):
    """
    Create a list of serializer field instances from the passed in "attrs",
    plus any fields on the base classes (in "bases").

    Note that all fields from the base classes are used.
    """
    fields = [(field_name, attrs.pop(field_name))
              for field_name, obj in list(six.iteritems(attrs))
              if isinstance(obj, Field)]
    fields.sort(key=lambda x: x[1].creation_counter)

    # If this class is subclassing another Serializer, add that Serializer's
    # fields.  Note that we loop over the bases in *reverse*. This is necessary
    # in order to maintain the correct order of fields.
    for base in bases[::-1]:
        if hasattr(base, "base_fields"):
            fields = list(base.base_fields.items()) + fields

    return OrderedDict(fields)


class SerializerMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs["base_fields"] = _get_declared_fields(bases, attrs)
        return super(SerializerMetaclass, cls).__new__(cls, name, bases, attrs)


class SerializerOptions(object):
    """
    Meta class options for Serializer
    """
    def __init__(self, meta):
        self.depth = getattr(meta, "depth", 0)
        self.fields = getattr(meta, "fields", ())
        self.exclude = getattr(meta, "exclude", ())


class BaseSerializer(WritableField):
    """
    This is the Serializer implementation.
    We need to implement it as `BaseSerializer` due to metaclass magicks.
    """
    class Meta(object):
        pass

    _options_class = SerializerOptions
    _dict_class = OrderedDictWithMetadata

    def __init__(self, instance=None, data=None, files=None,
                 context=None, partial=False, many=None,
                 allow_add_remove=False, **kwargs):
        super(BaseSerializer, self).__init__(**kwargs)
        self.opts = self._options_class(self.Meta)
        self.parent = None
        self.root = None
        self.partial = partial
        self.many = many
        self.allow_add_remove = allow_add_remove

        self.context = context or {}

        self.init_data = data
        self.init_files = files
        self.object = instance
        self.fields = self.get_fields()

        self._data = None
        self._files = None
        self._errors = None

        if many and instance is not None and not hasattr(instance, "__iter__"):
            raise ValueError("instance should be a queryset or other iterable with many=True")

        if allow_add_remove and not many:
            raise ValueError("allow_add_remove should only be used for bulk updates, but you have not set many=True")

    #####
    # Methods to determine which fields to use when (de)serializing objects.

    def get_default_fields(self):
        """
        Return the complete set of default fields for the object, as a dict.
        """
        return {}

    def get_fields(self):
        """
        Returns the complete set of fields for the object as a dict.

        This will be the set of any explicitly declared fields,
        plus the set of fields returned by get_default_fields().
        """
        ret = OrderedDict()

        # Get the explicitly declared fields
        base_fields = copy.deepcopy(self.base_fields)
        for key, field in base_fields.items():
            ret[key] = field

        # Add in the default fields
        default_fields = self.get_default_fields()
        for key, val in default_fields.items():
            if key not in ret:
                ret[key] = val

        # If "fields" is specified, use those fields, in that order.
        if self.opts.fields:
            assert isinstance(self.opts.fields, (list, tuple)), "`fields` must be a list or tuple"
            new = OrderedDict()
            for key in self.opts.fields:
                new[key] = ret[key]
            ret = new

        # Remove anything in "exclude"
        if self.opts.exclude:
            assert isinstance(self.opts.exclude, (list, tuple)), "`exclude` must be a list or tuple"
            for key in self.opts.exclude:
                ret.pop(key, None)

        for key, field in ret.items():
            field.initialize(parent=self, field_name=key)

        return ret

    #####
    # Methods to convert or revert from objects <--> primitive representations.

    def get_field_key(self, field_name):
        """
        Return the key that should be used for a given field.
        """
        return field_name

    def restore_fields(self, data, files):
        """
        Core of deserialization, together with `restore_object`.
        Converts a dictionary of data into a dictionary of deserialized fields.
        """
        reverted_data = {}

        if data is not None and not isinstance(data, dict):
            self._errors["non_field_errors"] = [_("Invalid data")]
            return None

        for field_name, field in self.fields.items():
            field.initialize(parent=self, field_name=field_name)
            try:
                field.field_from_native(data, files, field_name, reverted_data)
            except ValidationError as err:
                self._errors[field_name] = list(err.messages)

        return reverted_data

    def perform_validation(self, attrs):
        """
        Run `validate_<fieldname>()` and `validate()` methods on the serializer
        """
        for field_name, field in self.fields.items():
            if field_name in self._errors:
                continue

            source = field.source or field_name
            if self.partial and source not in attrs:
                continue
            try:
                validate_method = getattr(self, "validate_%s" % field_name, None)
                if validate_method:
                    attrs = validate_method(attrs, source)
            except ValidationError as err:
                self._errors[field_name] = self._errors.get(field_name, []) + list(err.messages)

        # If there are already errors, we don't run .validate() because
        # field-validation failed and thus `attrs` may not be complete.
        # which in turn can cause inconsistent validation errors.
        if not self._errors:
            try:
                attrs = self.validate(attrs)
            except ValidationError as err:
                if hasattr(err, "message_dict"):
                    for field_name, error_messages in err.message_dict.items():
                        self._errors[field_name] = self._errors.get(field_name, []) + list(error_messages)
                elif hasattr(err, "messages"):
                    self._errors["non_field_errors"] = err.messages

        return attrs

    def validate(self, attrs):
        """
        Stub method, to be overridden in Serializer subclasses
        """
        return attrs

    def restore_object(self, attrs, instance=None):
        """
        Deserialize a dictionary of attributes into an object instance.
        You should override this method to control how deserialized objects
        are instantiated.
        """
        if instance is not None:
            instance.update(attrs)
            return instance
        return attrs

    def to_native(self, obj):
        """
        Serialize objects -> primitives.
        """
        ret = self._dict_class()
        ret.fields = self._dict_class()
        ret.empty = obj is None

        for field_name, field in self.fields.items():
            field.initialize(parent=self, field_name=field_name)
            key = self.get_field_key(field_name)
            ret.fields[key] = field

            if obj is not None:
                value = field.field_to_native(obj, field_name)
                ret[key] = value

        return ret

    def from_native(self, data, files=None):
        """
        Deserialize primitives -> objects.
        """
        self._errors = {}

        if data is not None or files is not None:
            attrs = self.restore_fields(data, files)
            if attrs is not None:
                attrs = self.perform_validation(attrs)
        else:
            self._errors["non_field_errors"] = [_("No input provided")]

        if not self._errors:
            return self.restore_object(attrs, instance=getattr(self, "object", None))

    def augment_field(self, field, field_name, key, value):
        # This horrible stuff is to manage serializers rendering to HTML
        field._errors = self._errors.get(key) if self._errors else None
        field._name = field_name
        field._value = self.init_data.get(key) if self._errors and self.init_data else value
        if not field.label:
            field.label = pretty_name(key)
        return field

    def field_to_native(self, obj, field_name):
        """
        Override default so that the serializer can be used as a nested field
        across relationships.
        """
        if self.write_only:
            return None

        if self.source == "*":
            return self.to_native(obj)

        # Get the raw field value
        try:
            source = self.source or field_name
            value = obj

            for component in source.split("."):
                if value is None:
                    break
                value = get_component(value, component)
        except ObjectDoesNotExist:
            return None

        if is_simple_callable(getattr(value, "all", None)):
            return [self.to_native(item) for item in value.all()]

        if value is None:
            return None

        if self.many is not None:
            many = self.many
        else:
            many = hasattr(value, "__iter__") and not isinstance(value, (Page, dict, six.text_type))

        if many:
            try:
                return [self.to_native(item) for item in value]
            except TypeError:
                pass # LazyObject is iterable so we need to catch this
        return self.to_native(value)

    def field_from_native(self, data, files, field_name, into):
        """
        Override default so that the serializer can be used as a writable
        nested field across relationships.
        """
        if self.read_only:
            return

        try:
            value = data[field_name]
        except KeyError:
            if self.default is not None and not self.partial:
                # Note: partial updates shouldn't set defaults
                value = copy.deepcopy(self.default)
            else:
                if self.required:
                    raise ValidationError(self.error_messages["required"])
                return

        # Set the serializer object if it exists
        obj = get_component(self.parent.object, self.source or field_name) if self.parent.object else None

        # If we have a model manager or similar object then we need
        # to iterate through each instance.
        if (self.many and
            not hasattr(obj, "__iter__") and
            is_simple_callable(getattr(obj, "all", None))):
            obj = obj.all()

        if self.source == "*":
            if value:
                reverted_data = self.restore_fields(value, {})
                if not self._errors:
                    into.update(reverted_data)
        else:
            if value in (None, ""):
                into[(self.source or field_name)] = None
            else:
                kwargs = {
                    "instance": obj,
                    "data": value,
                    "context": self.context,
                    "partial": self.partial,
                    "many": self.many,
                    "allow_add_remove": self.allow_add_remove
                }
                serializer = self.__class__(**kwargs)

                if serializer.is_valid():
                    into[self.source or field_name] = serializer.object
                else:
                    # Propagate errors up to our parent
                    raise NestedValidationError(serializer.errors)

    def get_identity(self, data):
        """
        This hook is required for bulk update.
        It is used to determine the canonical identity of a given object.

        Note that the data has not been validated at this point, so we need
        to make sure that we catch any cases of incorrect datatypes being
        passed to this method.
        """
        try:
            return data.get("id", None)
        except AttributeError:
            return None

    @property
    def errors(self):
        """
        Run deserialization and return error data,
        setting self.object if no errors occurred.
        """
        if self._errors is None:
            data, files = self.init_data, self.init_files

            if self.many is not None:
                many = self.many
            else:
                many = hasattr(data, "__iter__") and not isinstance(data, (Page, dict, six.text_type))
                if many:
                    warnings.warn("Implicit list/queryset serialization is deprecated. "
                                  "Use the `many=True` flag when instantiating the serializer.",
                                  DeprecationWarning, stacklevel=3)

            if many:
                ret = RelationsList()
                errors = []
                update = self.object is not None

                if update:
                    # If this is a bulk update we need to map all the objects
                    # to a canonical identity so we can determine which
                    # individual object is being updated for each item in the
                    # incoming data
                    objects = self.object
                    identities = [self.get_identity(self.to_native(obj)) for obj in objects]
                    identity_to_objects = dict(zip(identities, objects))

                if hasattr(data, "__iter__") and not isinstance(data, (dict, six.text_type)):
                    for item in data:
                        if update:
                            # Determine which object we"re updating
                            identity = self.get_identity(item)
                            self.object = identity_to_objects.pop(identity, None)
                            if self.object is None and not self.allow_add_remove:
                                ret.append(None)
                                errors.append({"non_field_errors": [_("Cannot create a new item, only existing items may be updated.")]})
                                continue

                        ret.append(self.from_native(item, None))
                        errors.append(self._errors)

                    if update and self.allow_add_remove:
                        ret._deleted = identity_to_objects.values()

                    self._errors = any(errors) and errors or []
                else:
                    self._errors = {"non_field_errors": [_("Expected a list of items.")]}
            else:
                ret = self.from_native(data, files)

            if not self._errors:
                self.object = ret

        return self._errors

    def is_valid(self):
        return not self.errors

    @property
    def data(self):
        """
        Returns the serialized data on the serializer.
        """
        if self._data is None:
            obj = self.object

            if self.many is not None:
                many = self.many
            else:
                many = hasattr(obj, "__iter__") and not isinstance(obj, (Page, dict))
                if many:
                    warnings.warn("Implicit list/queryset serialization is deprecated. "
                                  "Use the `many=True` flag when instantiating the serializer.",
                                  DeprecationWarning, stacklevel=2)

            if many:
                try:
                    self._data = [self.to_native(item) for item in obj]
                except TypeError:
                    self._data = self.to_native(obj) # LazyObject is iterable so we need to catch this
            else:
                self._data = self.to_native(obj)

        return self._data

    def save_object(self, obj, **kwargs):
        obj.save(**kwargs)

    def delete_object(self, obj):
        obj.delete()

    def save(self, **kwargs):
        """
        Save the deserialized object and return it.
        """
        # Clear cached _data, which may be invalidated by `save()`
        self._data = None

        if isinstance(self.object, list):
            [self.save_object(item, **kwargs) for item in self.object]

            if self.object._deleted:
                [self.delete_object(item) for item in self.object._deleted]
        else:
            self.save_object(self.object, **kwargs)

        return self.object

    def metadata(self):
        """
        Return a dictionary of metadata about the fields on the serializer.
        Useful for things like responding to OPTIONS requests, or generating
        API schemas for auto-documentation.
        """
        return OrderedDict(
            [(field_name, field.metadata())
            for field_name, field in six.iteritems(self.fields)]
        )


class Serializer(six.with_metaclass(SerializerMetaclass, BaseSerializer)):
    def skip_field_validation(self, field, attrs, source):
        return source not in attrs and (field.partial or not field.required)

    def perform_validation(self, attrs):
        """
        Run `validate_<fieldname>()` and `validate()` methods on the serializer
        """
        for field_name, field in self.fields.items():
            if field_name in self._errors:
                continue

            source = field.source or field_name
            if self.skip_field_validation(field, attrs, source):
                continue

            try:
                validate_method = getattr(self, 'validate_%s' % field_name, None)
                if validate_method:
                    attrs = validate_method(attrs, source)
            except ValidationError as err:
                self._errors[field_name] = self._errors.get(field_name, []) + list(err.messages)

        # If there are already errors, we don't run .validate() because
        # field-validation failed and thus `attrs` may not be complete.
        # which in turn can cause inconsistent validation errors.
        if not self._errors:
            try:
                attrs = self.validate(attrs)
            except ValidationError as err:
                if hasattr(err, 'message_dict'):
                    for field_name, error_messages in err.message_dict.items():
                        self._errors[field_name] = self._errors.get(field_name, []) + list(error_messages)
                elif hasattr(err, 'messages'):
                    self._errors['non_field_errors'] = err.messages

        return attrs


class ModelSerializerOptions(SerializerOptions):
    """
    Meta class options for ModelSerializer
    """
    def __init__(self, meta):
        super(ModelSerializerOptions, self).__init__(meta)
        self.model = getattr(meta, "model", None)
        self.i18n_fields = getattr(meta, "i18n_fields", ())
        self.read_only_fields = getattr(meta, "read_only_fields", ())
        self.write_only_fields = getattr(meta, "write_only_fields", ())


class ModelSerializer((six.with_metaclass(SerializerMetaclass, BaseSerializer))):
    """
    A serializer that deals with model instances and querysets.
    """
    _options_class = ModelSerializerOptions

    field_mapping = {
        models.AutoField: IntegerField,
        models.FloatField: FloatField,
        models.IntegerField: IntegerField,
        models.PositiveIntegerField: IntegerField,
        models.SmallIntegerField: IntegerField,
        models.PositiveSmallIntegerField: IntegerField,
        models.DateTimeField: DateTimeField,
        models.DateField: DateField,
        models.TimeField: TimeField,
        models.DecimalField: DecimalField,
        models.EmailField: EmailField,
        models.CharField: CharField,
        models.URLField: URLField,
        models.SlugField: SlugField,
        models.TextField: CharField,
        models.CommaSeparatedIntegerField: CharField,
        models.BooleanField: BooleanField,
        models.NullBooleanField: BooleanField,
        models.FileField: FileField,
        models.ImageField: ImageField,
    }

    def get_default_fields(self):
        """
        Return all the fields that should be serialized for the model.
        """

        cls = self.opts.model
        assert cls is not None, \
                "Serializer class '%s' is missing `model` Meta option" % self.__class__.__name__
        opts = cls._meta.concrete_model._meta
        ret = OrderedDict()
        nested = bool(self.opts.depth)

        # Deal with adding the primary key field
        pk_field = opts.pk
        while pk_field.remote_field and pk_field.remote_field.parent_link:
            # If model is a child via multitable inheritance, use parent's pk
            pk_field = pk_field.remote_field.model._meta.pk

        field = self.get_pk_field(pk_field)
        if field:
            ret[pk_field.name] = field

        # Deal with forward relationships
        forward_rels = [field for field in opts.fields if field.serialize]
        forward_rels += [field for field in opts.many_to_many if field.serialize]

        for model_field in forward_rels:
            has_through_model = False

            if model_field.remote_field:
                to_many = isinstance(model_field,
                                     models.fields.related.ManyToManyField)
                related_model = _resolve_model(model_field.remote_field.model)

                if to_many and not model_field.remote_field.through._meta.auto_created:
                    has_through_model = True

            if model_field.remote_field and nested:
                if len(inspect.getfullargspec(self.get_nested_field).args) == 2:
                    warnings.warn(
                        "The `get_nested_field(model_field)` call signature "
                        "is due to be deprecated. "
                        "Use `get_nested_field(model_field, related_model, "
                        "to_many) instead",
                        PendingDeprecationWarning
                    )
                    field = self.get_nested_field(model_field)
                else:
                    field = self.get_nested_field(model_field, related_model, to_many)
            elif model_field.remote_field:
                if len(inspect.getfullargspec(self.get_nested_field).args) == 3:
                    warnings.warn(
                        "The `get_related_field(model_field, to_many)` call "
                        "signature is due to be deprecated. "
                        "Use `get_related_field(model_field, related_model, "
                        "to_many) instead",
                        PendingDeprecationWarning
                    )
                    field = self.get_related_field(model_field, to_many=to_many)
                else:
                    field = self.get_related_field(model_field, related_model, to_many)
            else:
                field = self.get_field(model_field)

            if field:
                if has_through_model:
                    field.read_only = True

                ret[model_field.name] = field

        # Deal with reverse relationships
        if not self.opts.fields:
            reverse_rels = []
        else:
            # Reverse relationships are only included if they are explicitly
            # present in the `fields` option on the serializer

            # NOTE: Rewrite after Django 1.10 upgrade.
            #       See https://docs.djangoproject.com/es/1.10/ref/models/meta/#migrating-from-the-old-api
            reverse_rels = [
                f for f in opts.get_fields()
                if (f.one_to_many or f.one_to_one)
                and f.auto_created and not f.concrete
            ]
            reverse_rels += [
                f for f in opts.get_fields(include_hidden=True)
                if f.many_to_many and f.auto_created
            ]

        for relation in reverse_rels:
            accessor_name = relation.get_accessor_name()
            if not self.opts.fields or accessor_name not in self.opts.fields:
                continue
            related_model = relation.model
            to_many = relation.field.remote_field.multiple
            has_through_model = False
            is_m2m = isinstance(relation.field,
                                models.fields.related.ManyToManyField)

            if (is_m2m and
                hasattr(relation.field.remote_field, "through") and
                not relation.field.remote_field.through._meta.auto_created):
                has_through_model = True

            if nested:
                field = self.get_nested_field(None, related_model, to_many)
            else:
                field = self.get_related_field(None, related_model, to_many)

            if field:
                if has_through_model:
                    field.read_only = True

                ret[accessor_name] = field

        # Add the `read_only` flag to any fields that have been specified
        # in the `read_only_fields` option
        for field_name in self.opts.read_only_fields:
            assert field_name not in self.base_fields.keys(), (
                "field '%s' on serializer '%s' specified in "
                "`read_only_fields`, but also added "
                "as an explicit field.  Remove it from `read_only_fields`." %
                (field_name, self.__class__.__name__))
            assert field_name in ret, (
                "Non-existant field '%s' specified in `read_only_fields` "
                "on serializer '%s'." %
                (field_name, self.__class__.__name__))
            ret[field_name].read_only = True

        for field_name in self.opts.write_only_fields:
            assert field_name not in self.base_fields.keys(), (
                "field '%s' on serializer '%s' specified in "
                "`write_only_fields`, but also added "
                "as an explicit field.  Remove it from `write_only_fields`." %
                (field_name, self.__class__.__name__))
            assert field_name in ret, (
                "Non-existant field '%s' specified in `write_only_fields` "
                "on serializer '%s'." %
                (field_name, self.__class__.__name__))
            ret[field_name].write_only = True

        # Add the `i18n` flag to any fields that have been specified
        # in the `i18n_fields` option
        for field_name in self.opts.i18n_fields:
            ret[field_name].i18n = True

        return ret

    def get_pk_field(self, model_field):
        """
        Returns a default instance of the pk field.
        """
        return self.get_field(model_field)

    def get_nested_field(self, model_field, related_model, to_many):
        """
        Creates a default instance of a nested relational field.

        Note that model_field will be `None` for reverse relationships.
        """
        class NestedModelSerializer(ModelSerializer):
            class Meta:
                model = related_model
                depth = self.opts.depth - 1

        return NestedModelSerializer(many=to_many)

    def get_related_field(self, model_field, related_model, to_many):
        """
        Creates a default instance of a flat relational field.

        Note that model_field will be `None` for reverse relationships.
        """
        # TODO: filter queryset using:
        # .using(db).complex_filter(self.rel.limit_choices_to)

        kwargs = {
            "queryset": related_model._default_manager,
            "many": to_many
        }

        if model_field:
            kwargs["required"] = not(model_field.null or model_field.blank)

        return PrimaryKeyRelatedField(**kwargs)

    def get_field(self, model_field):
        """
        Creates a default instance of a basic non-relational field.
        """
        kwargs = {}

        if model_field.null or model_field.blank:
            kwargs["required"] = False

        if isinstance(model_field, models.AutoField) or not model_field.editable:
            kwargs["read_only"] = True

        if model_field.has_default():
            kwargs["default"] = model_field.get_default()

        if issubclass(model_field.__class__, models.TextField):
            kwargs["widget"] = widgets.Textarea

        if model_field.verbose_name is not None:
            kwargs["label"] = model_field.verbose_name

        if model_field.help_text is not None:
            kwargs["help_text"] = model_field.help_text

        # TODO: TypedChoiceField?
        if model_field.flatchoices:  # This ModelField contains choices
            kwargs["choices"] = model_field.flatchoices
            if model_field.null:
                kwargs["empty"] = None
            return ChoiceField(**kwargs)

        # put this below the ChoiceField because min_value isn't a valid initializer
        if issubclass(model_field.__class__, models.PositiveIntegerField) or\
                issubclass(model_field.__class__, models.PositiveSmallIntegerField):
            kwargs["min_value"] = 0

        attribute_dict = {
            models.CharField: ["max_length"],
            models.CommaSeparatedIntegerField: ["max_length"],
            models.DecimalField: ["max_digits", "decimal_places"],
            models.EmailField: ["max_length"],
            models.FileField: ["max_length"],
            models.ImageField: ["max_length"],
            models.SlugField: ["max_length"],
            models.URLField: ["max_length"],
        }

        if model_field.__class__ in attribute_dict:
            attributes = attribute_dict[model_field.__class__]
            for attribute in attributes:
                kwargs.update({attribute: getattr(model_field, attribute)})

        if model_field.name in self.opts.i18n_fields:
            kwargs["i18n"] = True

        try:
            return self.field_mapping[model_field.__class__](**kwargs)
        except KeyError:
            return ModelField(model_field=model_field, **kwargs)

    def perform_validation(self, attrs):
        for attr in attrs:
            field = self.fields.get(attr, None)
            if field:
                field.required = True
        return super().perform_validation(attrs)

    def get_validation_exclusions(self):
        """
        Return a list of field names to exclude from model validation.
        """
        cls = self.opts.model
        opts = cls._meta.concrete_model._meta
        exclusions = [field.name for field in opts.fields + opts.many_to_many]

        for field_name, field in self.fields.items():
            field_name = field.source or field_name
            if field_name in exclusions \
                and not field.read_only \
                and field.required \
                and not isinstance(field, Serializer):
                exclusions.remove(field_name)
        return exclusions

    def full_clean(self, instance):
        """
        Perform Django's full_clean, and populate the `errors` dictionary
        if any validation errors occur.

        Note that we don't perform this inside the `.restore_object()` method,
        so that subclasses can override `.restore_object()`, and still get
        the full_clean validation checking.
        """
        try:
            instance.full_clean(exclude=self.get_validation_exclusions())
        except ValidationError as err:
            self._errors = err.message_dict
            return None
        return instance

    def restore_object(self, attrs, instance=None):
        """
        Restore the model instance.
        """
        m2m_data = {}
        related_data = {}
        nested_forward_relations = {}
        model = self.opts.model
        meta = self.opts.model._meta

        # Reverse fk or one-to-one relations
        # NOTE: Rewrite after Django 1.10 upgrade.
        #       See https://docs.djangoproject.com/es/1.10/ref/models/meta/#migrating-from-the-old-api
        related_objes_with_models = [
            (f, f.model if f.model != model else None)
            for f in meta.get_fields()
            if (f.one_to_many or f.one_to_one)
            and f.auto_created and not f.concrete
        ]
        for (obj, model) in related_objes_with_models:
            field_name = obj.get_accessor_name()
            if field_name in attrs:
                related_data[field_name] = attrs.pop(field_name)

        # Reverse m2m relations
        # NOTE: Rewrite after Django 1.10 upgrade.
        #       See https://docs.djangoproject.com/es/1.10/ref/models/meta/#migrating-from-the-old-api
        related_m2m_objects_with_model = [
            (f, f.model if f.model != model else None)
            for f in meta.get_fields(include_hidden=True)
            if f.many_to_many and f.auto_created
        ]
        for (obj, model) in related_m2m_objects_with_model:
            field_name = obj.get_accessor_name()
            if field_name in attrs:
                m2m_data[field_name] = attrs.pop(field_name)

        # Forward m2m relations
        for field in list(meta.many_to_many) + meta.private_fields:
            if field.name in attrs:
                m2m_data[field.name] = attrs.pop(field.name)

        # Nested forward relations - These need to be marked so we can save
        # them before saving the parent model instance.
        for field_name in attrs.keys():
            if isinstance(self.fields.get(field_name, None), Serializer):
                nested_forward_relations[field_name] = attrs[field_name]

        # Update an existing instance...
        if instance is not None:
            for key, val in attrs.items():
                try:
                    setattr(instance, key, val)
                except ValueError:
                    self._errors[key] = self.error_messages["required"]

        # ...or create a new instance
        else:
            instance = self.opts.model(**attrs)

        # Any relations that cannot be set until we"ve
        # saved the model get hidden away on these
        # private attributes, so we can deal with them
        # at the point of save.
        instance._related_data = related_data
        instance._m2m_data = m2m_data
        instance._nested_forward_relations = nested_forward_relations

        return instance

    def from_native(self, data, files):
        """
        Override the default method to also include model field validation.
        """
        instance = super(ModelSerializer, self).from_native(data, files)
        if not self._errors:
            return self.full_clean(instance)

    def save(self, **kwargs):
        """
        Due to DRF bug with M2M fields we refresh object state from database
        directly if object is models.Model type and it contains m2m fields

        See: https://github.com/tomchristie/django-rest-framework/issues/1556
        """
        self.object = super().save(**kwargs)
        model = self.Meta.model
        if model._meta.model._meta.local_many_to_many and self.object.pk:
            self.object = model.objects.get(pk=self.object.pk)
        return self.object

    def save_object(self, obj, **kwargs):
        """
        Save the deserialized object.
        """
        if getattr(obj, "_nested_forward_relations", None):
            # Nested relationships need to be saved before we can save the
            # parent instance.
            for field_name, sub_object in obj._nested_forward_relations.items():
                if sub_object:
                    self.save_object(sub_object)
                setattr(obj, field_name, sub_object)

        obj.save(**kwargs)

        if getattr(obj, "_m2m_data", None):
            for accessor_name, object_list in obj._m2m_data.items():
                field = getattr(obj, accessor_name)
                field.set(object_list)
            del(obj._m2m_data)

        if getattr(obj, "_related_data", None):
            related_fields = dict([
                (field.get_accessor_name(), field)
                for field, model
                in obj._meta.get_all_related_objects_with_model()
            ])
            for accessor_name, related in obj._related_data.items():
                if isinstance(related, RelationsList):
                    # Nested reverse fk relationship
                    for related_item in related:
                        fk_field = related_fields[accessor_name].field.name
                        setattr(related_item, fk_field, obj)
                        self.save_object(related_item)

                    # Delete any removed objects
                    if related._deleted:
                        [self.delete_object(item) for item in related._deleted]

                elif isinstance(related, models.Model):
                    # Nested reverse one-one relationship
                    fk_field = obj._meta.get_field_by_name(accessor_name)[0].field.name
                    setattr(related, fk_field, obj)
                    self.save_object(related)
                else:
                    # Reverse FK or reverse one-one
                    setattr(obj, accessor_name, related)
            del(obj._related_data)


class HyperlinkedModelSerializerOptions(ModelSerializerOptions):
    """
    Options for HyperlinkedModelSerializer
    """
    def __init__(self, meta):
        super(HyperlinkedModelSerializerOptions, self).__init__(meta)
        self.view_name = getattr(meta, "view_name", None)
        self.lookup_field = getattr(meta, "lookup_field", None)
        self.url_field_name = getattr(meta, "url_field_name", api_settings.URL_FIELD_NAME)


class HyperlinkedModelSerializer(ModelSerializer):
    """
    A subclass of ModelSerializer that uses hyperlinked relationships,
    instead of primary key relationships.
    """
    _options_class = HyperlinkedModelSerializerOptions
    _default_view_name = "%(model_name)s-detail"
    _hyperlink_field_class = HyperlinkedRelatedField
    _hyperlink_identify_field_class = HyperlinkedIdentityField

    def get_default_fields(self):
        fields = super(HyperlinkedModelSerializer, self).get_default_fields()

        if self.opts.view_name is None:
            self.opts.view_name = self._get_default_view_name(self.opts.model)

        if self.opts.url_field_name not in fields:
            url_field = self._hyperlink_identify_field_class(
                view_name=self.opts.view_name,
                lookup_field=self.opts.lookup_field
            )
            ret = self._dict_class()
            ret[self.opts.url_field_name] = url_field
            ret.update(fields)
            fields = ret

        return fields

    def get_pk_field(self, model_field):
        if self.opts.fields and model_field.name in self.opts.fields:
            return self.get_field(model_field)

    def get_related_field(self, model_field, related_model, to_many):
        """
        Creates a default instance of a flat relational field.
        """
        # TODO: filter queryset using:
        # .using(db).complex_filter(self.rel.limit_choices_to)
        kwargs = {
            "queryset": related_model._default_manager,
            "view_name": self._get_default_view_name(related_model),
            "many": to_many
        }

        if model_field:
            kwargs["required"] = not(model_field.null or model_field.blank)

        if self.opts.lookup_field:
            kwargs["lookup_field"] = self.opts.lookup_field

        return self._hyperlink_field_class(**kwargs)

    def get_identity(self, data):
        """
        This hook is required for bulk update.
        We need to override the default, to use the url as the identity.
        """
        try:
            return data.get(self.opts.url_field_name, None)
        except AttributeError:
            return None

    def _get_default_view_name(self, model):
        """
        Return the view name to use if `view_name` is not specified in `Meta`
        """
        model_meta = model._meta
        format_kwargs = {
            "app_label": model_meta.app_label,
            "model_name": model_meta.object_name.lower()
        }
        return self._default_view_name % format_kwargs


class LightSerializer(serpy.Serializer):
    def __init__(self, *args, **kwargs):
        kwargs.pop("read_only", None)
        kwargs.pop("partial", None)
        kwargs.pop("files", None)
        context = kwargs.pop("context", {})
        view = kwargs.pop("view", {})
        super().__init__(*args, **kwargs)
        self.context = context
        self.view = view


class LightDictSerializer(serpy.DictSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.pop("read_only", None)
        kwargs.pop("partial", None)
        kwargs.pop("files", None)
        context = kwargs.pop("context", {})
        view = kwargs.pop("view", {})
        super().__init__(*args, **kwargs)
        self.context = context
        self.view = view
