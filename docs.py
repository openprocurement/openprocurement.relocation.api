# -*- coding: utf-8 -*-
import json
import os

import openprocurement.relocation.api.tests.base as base_test
from copy import deepcopy
from openprocurement.api.tests.base import PrefixedRequestClass, test_tender_data
from openprocurement.relocation.api.tests.base import BaseWebTest
from webtest import TestApp


class DumpsTestAppwebtest(TestApp):
    def do_request(self, req, status=None, expect_errors=None):
        req.headers.environ["HTTP_HOST"] = "api-sandbox.openprocurement.org"
        if hasattr(self, 'file_obj') and not self.file_obj.closed:
            self.file_obj.write(req.as_bytes(True))
            self.file_obj.write("\n")
            if req.body:
                try:
                    self.file_obj.write(
                            'DATA:\n' + json.dumps(json.loads(req.body), indent=2, ensure_ascii=False).encode('utf8'))
                    self.file_obj.write("\n")
                except:
                    pass
            self.file_obj.write("\n")
        resp = super(DumpsTestAppwebtest, self).do_request(req, status=status, expect_errors=expect_errors)
        if hasattr(self, 'file_obj') and not self.file_obj.closed:
            headers = [(n.title(), v)
                       for n, v in resp.headerlist
                       if n.lower() != 'content-length']
            headers.sort()
            self.file_obj.write(str('Response: %s\n%s\n') % (
                resp.status,
                str('\n').join([str('%s: %s') % (n, v) for n, v in headers]),
            ))

            if resp.testbody:
                try:
                    self.file_obj.write(json.dumps(json.loads(resp.testbody), indent=2, ensure_ascii=False).encode('utf8'))
                except:
                    pass
            self.file_obj.write("\n\n")
        return resp


class TransferDocsTest(BaseWebTest):

    def setUp(self):
        self.app = DumpsTestAppwebtest(
                "config:tests.ini", relative_to=os.path.dirname(base_test.__file__))
        self.app.RequestClass = PrefixedRequestClass
        self.app.authorization = ('Basic', ('broker', ''))
        self.couchdb_server = self.app.app.registry.couchdb_server
        self.db = self.app.app.registry.db

    def test_docs(self):
        data = deepcopy(test_tender_data)
        self.app.authorization = ('Basic', ('broker', ''))

        with open('docs/source/tutorial/create-tender.http', 'w') as self.app.file_obj:
            response = self.app.post_json('/tenders?opt_pretty=1', {"data": data})
            self.assertEqual(response.status, '201 Created')

        tender = response.json['data']
        self.tender_id = tender['id']
        owner_token = response.json['access']['token']
        orig_tender_transfer_token = response.json['access']['transfer']

        self.app.authorization = ('Basic', ('broker2', ''))

        with open('docs/source/tutorial/create-transfer.http', 'w') as self.app.file_obj:
            response = self.app.post_json('/transfers', {"data": {}})
            self.assertEqual(response.status, '201 Created')
            self.assertEqual(response.content_type, 'application/json')
            transfer = response.json['data']
            new_access_token = response.json['access']['token']
            new_transfer_token = response.json['access']['transfer']

        with open('docs/source/tutorial/change-tender-ownership.http', 'w') as self.app.file_obj:
            response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                        {"data": {"id": transfer['id'], 'transfer': orig_tender_transfer_token} })
            self.assertEqual(response.status, '200 OK')
            self.assertNotIn('transfer', response.json['data'])
            self.assertNotIn('transfer_token', response.json['data'])
            self.assertEqual('broker2', response.json['data']['owner'])

        with open('docs/source/tutorial/modify-tender.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, new_access_token),
                                        {"data": {"description": "broker2 now can change the tender"}})
            self.assertEqual(response.status, '200 OK')
            self.assertEqual(response.json['data']['description'], 'broker2 now can change the tender')
