# -*- coding: utf-8 -*-
import unittest
from uuid import uuid4
from copy import deepcopy

from openprocurement.api.tests.base import test_tender_data
from openprocurement.relocation.api.models import Transfer
from openprocurement.relocation.api.tests.base import BaseWebTest, OwnershipWebTest

test_transfer_data = {}


class TrensferTest(BaseWebTest):

    def test_simple_add_transfer(self):

        data = {"access_token": "1234",
                "transfer_token": "5678",
                "owner": "Chuck Norris"}

        u = Transfer(data)

        assert u.id is None

        u.store(self.db)

        assert u.id is not None

        fromdb = self.db.get(u.id)

        assert u.transfer_token == fromdb['transfer_token']
        assert u.access_token == fromdb['access_token']
        assert u.owner == fromdb['owner']
        assert u.doc_type == "Transfer"

        u.delete_instance(self.db)


class TransferResourceTest(BaseWebTest):
    """ /transfers resource test """

    def test_get_transfer(self):
        response = self.app.get('/transfers', status=405)
        self.assertEqual(response.status, '405 Method Not Allowed')

        response = self.app.post_json('/transfers', {'data': test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        self.assertIn('id', transfer)

        response = self.app.get('/transfers/{}'.format(transfer['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data'], transfer)

        response = self.app.get('/transfers/{}?opt_jsonp=callback'.format(transfer['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/javascript')
        self.assertIn('callback({"data": {"', response.body)

        response = self.app.get('/transfers/{}?opt_pretty=1'.format(transfer['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('{\n    "data": {\n        "', response.body)

    def test_not_found(self):
        response = self.app.post_json('/transfers', {'data': test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']

        response = self.app.get('/transfers/{}'.format("1234" * 8), status=404)
        self.assertEqual(response.status, '404 Not Found')

        orig_auth = self.app.authorization
        self.app.authorization = ('Basic', ('broker1', ''))
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        self.assertEqual(response.status, '201 Created')
        tender = response.json['data']
        self.app.authorization = orig_auth

        response = self.app.get('/transfers/{}'.format(tender['id']), status=404)
        self.assertEqual(response.status, '404 Not Found')

        data = deepcopy(test_transfer_data)
        data['id'] = uuid4().hex
        response = self.app.post_json('/transfers', {'data': data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        self.assertNotEqual(transfer['id'], data['id'])

        response = self.app.get('/transfers/{}'.format(data['id']), status=404)
        self.assertEqual(response.status, '404 Not Found')

        response = self.app.get('/transfers/some_id', status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location': u'url', u'name': u'transfer_id'}
        ])

        response = self.app.patch_json(
            '/transfers/some_id', {'data': {}}, status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location': u'url', u'name': u'transfer_id'}
        ])

    def test_create_transfer(self):
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        transfer = response.json['data']
        self.assertNotIn('usedFor', transfer)
        self.assertIn('token', response.json['access'])
        self.assertIn('transfer', response.json['access'])

        response = self.app.get('/transfers/{}'.format(transfer['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(set(response.json['data']), set(transfer))
        self.assertEqual(response.json['data'], transfer)

        data = test_transfer_data
        response = self.app.post_json('/transfers?opt_jsonp=callback', {"data": data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/javascript')
        self.assertIn('callback({"', response.body)

        response = self.app.post_json('/transfers?opt_pretty=1', {"data": data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('{\n    "', response.body)

        response = self.app.post_json('/transfers', {"data": data, "options": {"pretty": True}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('{\n    "', response.body)

        self.app.authorization = ('Basic', ('broker1', ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit transfer creation', u'location': u'transfer', u'name': u'accreditation'}
        ])


class OwnershipChangeTest(OwnershipWebTest):
    initial_data = test_tender_data

    def test_change_ownership(self):
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id), {"data": {"id": 12} }, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'], [
            {u'description': u'This field is required.', u'location': u'body', u'name': u'transfer'}
        ])

        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['owner'], 'broker')

        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('broker2', ''))

        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer['id'], 'transfer': self.tender_transfer} })
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertEqual('broker2', response.json['data']['owner'])

        # broker3 can change the tender
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, transfer_tokens['token']),
                                       {"data": {"description": "broker2 now can change the tender"}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertIn('owner', response.json['data'])
        self.assertEqual(response.json['data']['owner'], 'broker2')

        self.app.authorization = authorization
        # old ownfer now can`t change tender
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, transfer_tokens['token']),
                                       {"data": {"description": "yummy donut"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": 'fake id', 'transfer': 'fake transfer'} }, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TrensferTest))
    suite.addTest(unittest.makeSuite(TransferResourceTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
