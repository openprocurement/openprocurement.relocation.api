# -*- coding: utf-8 -*-
import os
from copy import deepcopy
from datetime import datetime
from openprocurement.api.tests.base import BaseWebTest

now = datetime.now()


class BaseTransferWebTest(BaseWebTest):
    initial_data = {}

    def setUp(self):
        super(BaseTransferWebTest, self).setUp()
        self.app.authorization = self.initial_auth
        self.create_transfer()

    def create_transfer(self):
        data = deepcopy(self.initial_data)

        response = self.app.post_json('/transfers', {'data': data})
        self.access = response.json['access']
        self.transfer = response.json['data']
        self.transfer_id = self.transfer['id']

    def tearDown(self):
        del self.db[self.transfer_id]
        super(BaseTransferWebTest, self).tearDown()
