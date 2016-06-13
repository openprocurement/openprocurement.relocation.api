# -*- coding: utf-8 -*-
import os
import unittest
import webtest
from copy import deepcopy
from datetime import datetime

from openprocurement.api.tests.base import PrefixedRequestClass
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
