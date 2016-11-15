# -*- coding: utf-8 -*-
import os
import unittest
import webtest
from copy import deepcopy
from datetime import datetime, timedelta
from uuid import uuid4

from openprocurement.api.utils import apply_data_patch
from openprocurement.api.design import sync_design
from openprocurement.api.tests.base import PrefixedRequestClass, test_tender_data, test_organization
from openprocurement.tender.openua.tests.base import test_tender_data as test_ua_tender_data
from openprocurement.tender.openuadefense.tests.base import test_tender_data as test_uadefense_tender_data
from openprocurement.tender.openeu.tests.base import test_tender_data as test_eu_tender_data
from openprocurement.tender.limited.tests.base import (test_tender_data as test_tender_reporting_data,
                                                       test_tender_negotiation_data,
                                                       test_tender_negotiation_quick_data)
from  openprocurement.tender.competitivedialogue.tests.base import(test_tender_data_eu as test_tender_data_competitive_eu,
                                                                   test_tender_data_ua as test_tender_data_competitive_ua)
from openprocurement.contracting.api.tests.base import test_contract_data

test_transfer_data = {}

test_bid_data = {'data': {'tenderers': [test_organization], "value": {"amount": 500}}}
test_ua_bid_data = deepcopy(test_bid_data)
test_ua_bid_data['data'].update({'selfEligible': True, 'selfQualified': True})
test_uadefense_bid_data = deepcopy(test_ua_bid_data)
test_eu_bid_data = deepcopy(test_ua_bid_data)

now = datetime.now()

class BaseWebTest(unittest.TestCase):
    """Base Web Test to test openprocurement.relocation.api.

    It setups the database before each test and delete it after.
    """
    initial_auth = ('Basic', ('broker', ''))
    relative_to = os.path.dirname(__file__)

    @classmethod
    def setUpClass(cls):
        while True:
            try:
                cls.app = webtest.TestApp("config:tests.ini", relative_to=cls.relative_to)
            except:
                pass
            else:
                break
        cls.app.RequestClass = PrefixedRequestClass
        cls.couchdb_server = cls.app.app.registry.couchdb_server
        cls.db = cls.app.app.registry.db
        cls.db_name = cls.db.name

    @classmethod
    def tearDownClass(cls):
        try:
            cls.couchdb_server.delete(cls.db_name)
        except:
            pass

    def setUp(self):
        self.db_name += uuid4().hex
        self.couchdb_server.create(self.db_name)
        db = self.couchdb_server[self.db_name]
        sync_design(db)
        self.app.app.registry.db = db
        self.db = self.app.app.registry.db
        self.db_name = self.db.name
        self.app.authorization = self.initial_auth

    def tearDown(self):
        self.couchdb_server.delete(self.db_name)


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

    def set_qualification_status(self):
        data = {
            "status": 'active.qualification',
            "enquiryPeriod": {
                "startDate": (now - timedelta(days=18)).isoformat(),
                "endDate": (now - timedelta(days=8)).isoformat()
            },
            "tenderPeriod": {
                "startDate": (now - timedelta(days=8)).isoformat(),
                "endDate": (now - timedelta(days=1)).isoformat()
            },
            "auctionPeriod": {
                "startDate": (now - timedelta(days=1)).isoformat(),
                "endDate": (now).isoformat()
            },
            "awardPeriod": {
                "startDate": (now).isoformat()
            }
        }

        tender = self.db.get(self.tender_id)
        tender.update(apply_data_patch(tender, data))
        self.db.save(tender)


class OpenUAOwnershipWebTest(OwnershipWebTest):
    """
    OpenUA Web Test to test openprocurement.relocation.api.
    """

    def set_tendering_status(self):
        data = {
            "status": "active.tendering",
            "enquiryPeriod": {
                "startDate": (now - timedelta(days=15)).isoformat(),
                "endDate": (now).isoformat()
            },
            "tenderPeriod": {
                "startDate": (now).isoformat(),
                "endDate": (now + timedelta(days=30)).isoformat()
            }
        }

        tender = self.db.get(self.tender_id)
        tender.update(apply_data_patch(tender, data))
        self.db.save(tender)

    def set_qualification_status(self):
        data = {
            "status": 'active.qualification',
            "enquiryPeriod": {
                "startDate": (now - timedelta(days=46)).isoformat(),
                "endDate": (now - timedelta(days=31)).isoformat()
            },
            "tenderPeriod": {
                "startDate": (now - timedelta(days=31)).isoformat(),
                "endDate": (now - timedelta(days=1)).isoformat()
            },
            "auctionPeriod": {
                "startDate": (now - timedelta(days=1)).isoformat(),
                "endDate": (now).isoformat()
            },
            "awardPeriod": {
                "startDate": (now).isoformat()
            }
        }

        tender = self.db.get(self.tender_id)
        tender.update(apply_data_patch(tender, data))
        self.db.save(tender)


class OpenEUOwnershipWebTest(OpenUAOwnershipWebTest):
    """
    OpenEU Web Test to test openprocurement.relocation.api.
    """

    def set_qualification_status(self):
        data = {
            "status": 'active.qualification',
            "enquiryPeriod": {
                "startDate": (now - timedelta(days=46)).isoformat(),
                "endDate": (now - timedelta(days=31)).isoformat()
            },
            "tenderPeriod": {
                "startDate": (now - timedelta(days=31)).isoformat(),
                "endDate": (now - timedelta(days=1)).isoformat()
            },
            "auctionPeriod": {
                "startDate": (now - timedelta(days=1)).isoformat(),
                "endDate": (now).isoformat()
            },
            "awardPeriod": {
                "startDate": (now).isoformat()
            }
        }

        tender = self.db.get(self.tender_id)
        tender.update(apply_data_patch(tender, data))
        self.db.save(tender)

    def set_auction_status(self, extra=None):
        data = {
            "enquiryPeriod": {
                "startDate": (now - timedelta(days=46)).isoformat(),
                "endDate": (now - timedelta(days=31)).isoformat()
            },
            "tenderPeriod": {
                "startDate": (now - timedelta(days=31)).isoformat(),
                "endDate": (now - timedelta(days=1)).isoformat()
            },
            "qualificationPeriod": {
                "startDate": (now - timedelta(days=1)).isoformat(),
                "endDate": (now).isoformat()
            },
            "auctionPeriod": {
                "startDate": now.isoformat()
            }
        }
        if extra:
            data.update(extra)

        tender = self.db.get(self.tender_id)
        tender.update(apply_data_patch(tender, data))
        self.db.save(tender)

    def set_pre_qualification_status(self, extra=None):
        data = {
            "enquiryPeriod": {
                "startDate": (now - timedelta(days=45)).isoformat(),
                "endDate": (now - timedelta(days=30)).isoformat()
            },
            "tenderPeriod": {
                "startDate": (now - timedelta(days=30)).isoformat(),
                "endDate": (now).isoformat(),
            },
            "qualificationPeriod": {
                "startDate": (now).isoformat(),
            }
        }
        if extra:
            data.update(extra)

        tender = self.db.get(self.tender_id)
        tender.update(apply_data_patch(tender, data))
        self.db.save(tender)


class ContractOwnershipWebTest(BaseWebTest):

    def setUp(self):
        super(ContractOwnershipWebTest, self).setUp()
        self.create_contract()

    def create_contract(self):
        data = deepcopy(self.initial_data)

        orig_auth = self.app.authorization
        self.app.authorization = ('Basic', ('contracting', ''))
        response = self.app.post_json('/contracts', {'data': data})
        self.contract = response.json['data']
        # self.contract_token = response.json['access']['token']
        self.contract_id = self.contract['id']
        self.app.authorization = orig_auth
