# -*- coding: utf-8 -*-
import os
import unittest
import webtest
from copy import deepcopy
from datetime import datetime, timedelta

from openprocurement.api.utils import apply_data_patch
from openprocurement.api.tests.base import PrefixedRequestClass, test_tender_data
now = datetime.now()


class BaseWebTest(unittest.TestCase):
    """Base Web Test to test openprocurement.relocation.api.

    It setups the database before each test and delete it after.
    """
    initial_auth = ('Basic', ('broker', ''))

    def setUp(self):
        self.app = webtest.TestApp(
            "config:tests.ini", relative_to=os.path.dirname(__file__))
        self.app.RequestClass = PrefixedRequestClass
        self.app.authorization = self.initial_auth
        self.couchdb_server = self.app.app.registry.couchdb_server
        self.db = self.app.app.registry.db

    def tearDown(self):
        del self.couchdb_server[self.db.name]


class OwnershipWebTest(BaseWebTest):

    def setUp(self):
        super(OwnershipWebTest, self).setUp()
        self.create_tender()

    def create_tender(self):
        data = deepcopy(self.initial_data)
        response = self.app.post_json('/tenders', {'data': data})
        tender = response.json['data']
        self.tender_token = response.json['access']['token']
        self.tender_transfer = response.json['access']['transfer']
        self.tender_id = tender['id']

    def set_tendering_status(self):
        data = {
            "status": "active.tendering",
            "enquiryPeriod": {
                "startDate": (now - timedelta(days=10)).isoformat(),
                "endDate": (now).isoformat()
            },
            "tenderPeriod": {
                "startDate": (now).isoformat(),
                "endDate": (now + timedelta(days=7)).isoformat()
            }
        }

        tender = self.db.get(self.tender_id)
        tender.update(apply_data_patch(tender, data))
        self.db.save(tender)
