# -*- coding: utf-8 -*-
from uuid import uuid4

from zope.interface import implementer, Interface
from pyramid.security import Allow
from couchdb_schematics.document import SchematicsDocument
from schematics.types import StringType, BaseType, MD5Type
from schematics.types.compound import ModelType, DictType
from schematics.types.serializable import serializable
from schematics.exceptions import ValidationError
from schematics.transforms import whitelist, blacklist
from openprocurement.api.models import Model, plain_role, schematics_default_role


class Transfer(SchematicsDocument, Model):

    class Options:
        roles = {
            'plain': plain_role,
            'default': schematics_default_role,
            'create': whitelist(),
            'view': whitelist('id', 'doc_id', 'usedFor'),
        }

    owner = StringType(min_length=1)
    access_token = StringType(min_length=1)
    transfer_token = StringType(min_length=1)
    usedFor = StringType()

    create_accreditation = 3

    def __repr__(self):
        return '<%s:%r@%r>' % (type(self).__name__, self.id, self.rev)

    @serializable(serialized_name='id')
    def doc_id(self):
        """A property that is serialized by schematics exports."""
        return self._id
