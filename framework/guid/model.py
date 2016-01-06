# -*- coding: utf-8 -*-
import random

import pymongo
from modularodm import fields

from framework.mongo import StoredObject

from modularodm.storage.base import KeyExistsException

ALPHABET = '23456789abcdefghjkmnpqrstuvwxyz'


class BlacklistGuid(StoredObject):

    _id = fields.StringField(primary=True)


class Guid(StoredObject):

    __indices__ = [{
        'unique': False,
        'key_or_list': [('referent.$', pymongo.ASCENDING)]  # Forces a mulitkey index h/t @icereval
    }]

    _id = fields.StringField(primary=True)
    referent = fields.AbstractForeignField()

    @classmethod
    def generate(self, referent=None, min_length=5):
        while True:
            # Create GUID
            guid_id = ''.join(random.sample(ALPHABET, min_length))

            # Check GUID against blacklist
            blacklist_guid = BlacklistGuid.load(guid_id)
            if not blacklist_guid:
                try:
                    guid = Guid(_id=guid_id)
                    guid.save()
                    break
                except KeyExistsException:
                    pass
        if referent:
            guid.referent = referent
            guid.save()
        return guid

    def __repr__(self):
        return '<id:{0}, referent:({1}, {2})>'.format(self._id, self.referent._primary_key, self.referent._name)


class GuidStoredObject(StoredObject):
    """Subclass of `StoredObject` that provisions a `Guid` for each new instance
    on save. When saving a `GuidStoredObject` for the first time, creates a new
    `Guid`, then assigns the primary key of the instance to the primary key of
    the `Guid`. Note: Subclasses should have a `StringField` primary key, since
    the key generated by the associated `Guid` will also be a string.
    """
    __guid_min_length__ = 5

    @property
    def deep_url(self):
        return None

    def _ensure_guid(self):
        """Create GUID record if current record doesn't already have one, then
        point GUID to self.
        """
        # Create GUID with specified ID if provided
        if self._primary_key:

            # Done if GUID already exists
            guid = Guid.load(self._primary_key)
            if guid is not None:
                return

            # Create GUID
            guid = Guid(
                _id=self._primary_key,
                referent=self,
            )
            guid.save()

        # Else create GUID optimistically
        else:
            guid = Guid.generate(min_length=self.__guid_min_length__)
            guid.referent = (guid._primary_key, self._name)
            guid.save()
            # Set primary key to GUID key
            self._primary_key = guid._primary_key

    def save(self, *args, **kwargs):
        """Ensure GUID on save."""
        self._ensure_guid()
        return super(GuidStoredObject, self).save(*args, **kwargs)

    def __str__(self):
        return str(self._id)
