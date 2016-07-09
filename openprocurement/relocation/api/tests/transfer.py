# -*- coding: utf-8 -*-
import unittest
from uuid import uuid4
from copy import deepcopy

from openprocurement.api.tests.base import test_tender_data, test_organization
from openprocurement.relocation.api.models import Transfer
from openprocurement.relocation.api.tests.base import BaseWebTest, OwnershipWebTest
try:
    from openprocurement.tender.openua.tests.base import test_tender_data as ua_t_data
except ImportError:
    ua_t_data = None

try:
    from openprocurement.tender.openeu.tests.base import test_tender_data as eu_t_data
except ImportError:
    eu_t_data = None

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
        response = self.app.post_json('/transfers', status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'], [
            {u'description': u'No JSON object could be decoded', u'location': u'body', u'name': u'data'}
        ])

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


class OwnershipChangeTest(OwnershipWebTest):
    initial_data = test_tender_data

    def test_change_tender_ownership(self):
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id), {"data": {"id": 12} }, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'], [
            {u'description': u'This field is required.', u'location': u'body', u'name': u'transfer'}
        ])

        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['owner'], 'broker')

        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('broker1', ''))

        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        new_access_token = response.json['access']['token']
        new_transfer_token = response.json['access']['transfer']

        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer['id'], 'transfer': self.tender_transfer} })
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertEqual('broker1', response.json['data']['owner'])

        # tender location is stored in Transfer
        transfer_doc = self.db.get(transfer['id'])
        self.assertEqual(transfer_doc['usedFor'], '/tenders/' + self.tender_id)

        # try to use already applied transfer
        self.app.authorization = authorization
        response = self.app.post_json('/tenders', {'data': self.initial_data})
        tender = response.json['data']
        access = response.json['access']
        self.app.authorization = ('Basic', ('broker1', ''))
        response = self.app.post_json('/tenders/{}/ownership'.format(tender['id']),
                                      {"data": {"id": transfer['id'], 'transfer': access['transfer']} }, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
        ])
        # simulate half-applied transfer activation process (i.e. transfer
        # is successfully applied to a tender and relation is saved in transfer,
        # but tender is not stored with new credentials)
        transfer_doc = self.db.get(transfer['id'])
        transfer_doc['usedFor'] = '/tenders/' + tender['id']
        self.db.save(transfer_doc)
        response = self.app.post_json('/tenders/{}/ownership'.format(tender['id']),
                                      {"data": {"id": transfer['id'], 'transfer': access['transfer']} }, status=200)
        self.assertEqual('broker1', response.json['data']['owner'])

        # broker2 can change the tender (first tender which created in test setup)
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, new_access_token),
                                       {"data": {"description": "broker2 now can change the tender"}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertIn('owner', response.json['data'])
        self.assertEqual(response.json['data']['owner'], 'broker1')

        self.app.authorization = authorization
        # old ownfer now can`t change tender
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, new_access_token),
                                       {"data": {"description": "yummy donut"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": 'fake id', 'transfer': 'fake transfer'} }, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])

        # try to use transfer by broker without appropriate accreditation level
        self.app.authorization = ('Basic', ('broker2', ''))

        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token} }, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership activation',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])

        # test level permits to change ownership for 'test' tenders
        # first try on non-test tender
        self.app.authorization = ('Basic', ('broker1t', ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token} }, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership activation',
             u'location': u'procurementMethodType', u'name': u'mode'}
        ])

        # set test mode and try to change ownership
        self.app.authorization = ('Basic', ('administrator', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'mode': 'test'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['mode'], 'test')

        self.app.authorization = ('Basic', ('broker1t', ''))
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token} })
        self.assertEqual(response.status, '200 OK')
        self.assertIn('owner', response.json['data'])
        self.assertEqual(response.json['data']['owner'], 'broker1t')

        # test accreditation levels are also sepatated
        self.app.authorization = ('Basic', ('broker2t', ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']

        new_transfer_token = transfer_tokens['transfer']
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token} }, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership activation',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])

    def test_change_bid_ownership(self):

        self.set_tendering_status()

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(
            self.tender_id), {'data': {'tenderers': [test_organization], "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        bid = response.json['data']
        bid_tokens = response.json['access']

        # current owner can change his bid
        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bid['id'], bid_tokens['token']), {"data": {'value': {"amount": 499}}})
        self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('broker2', ''))

        # other broker can't change the bid
        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bid['id'], bid_tokens['token']), {"data": {'value': {"amount": 498}}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        # change bid ownership
        response = self.app.post_json('/tenders/{}/bids/{}/ownership'.format(self.tender_id, bid['id']),
                                      {"data": {"id": transfer['id'], 'transfer': bid_tokens['transfer']} })
        self.assertEqual(response.status, '200 OK')

        # new owner can change the bid using new credentials
        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bid['id'], transfer_tokens['token']), {"data": {'value': {"amount": 495}}})
        self.assertEqual(response.status, '200 OK')

    def test_complaint_ownership(self):
        # submit complaint from broker
        response = self.app.post_json('/tenders/{}/complaints'.format(
            self.tender_id), {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        complaint = response.json['data']
        complaint_token = response.json['access']['token']
        complaint_transfer = response.json['access']['transfer']
        self.assertEqual(complaint['author']['name'], test_organization['name'])
        self.assertIn('id', complaint)
        self.assertIn(complaint['id'], response.headers['Location'])

        # check complaint owner
        tender_doc = self.db.get(self.tender_id)
        self.assertEqual(tender_doc['complaints'][0]['owner'], "broker")

        self.app.authorization = ('Basic', ('broker2', ''))

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/complaints/{}/ownership'.format(self.tender_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer} })
        self.assertEqual(response.status, '200 OK')
        complaint_transfer = transfer_tokens['transfer']

        # check complaint owner
        tender_doc = self.db.get(self.tender_id)
        self.assertEqual(tender_doc['complaints'][0]['owner'], "broker2")

        self.app.authorization = ('Basic', ('broker1', ''))
        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/complaints/{}/ownership'.format(self.tender_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer} }, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership activation',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])


class BaseTenderOwnershipTest(object):

    def test_tender_transfer(self):
        response = self.app.post_json('/tenders', {"data": self.tender_test_data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        tender = response.json['data']
        tender_access_tokens = response.json['access']
        self.assertEqual('broker', tender['owner'])
        self.assertEqual(self.tender_type, tender['procurementMethodType'])
        self.assertNotIn('transfer', tender)
        self.tender_id = tender['id']

        self.app.authorization = ('Basic', ('broker3', ''))

        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        new_access_token = response.json['access']['token']
        new_transfer_token = response.json['access']['transfer']

        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer['id'], 'transfer': tender_access_tokens['transfer']} })
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(self.tender_type, tender['procurementMethodType'])
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertEqual('broker3', response.json['data']['owner'])


class OpenUAOwnershipChangeTest(BaseWebTest, BaseTenderOwnershipTest):
    tender_type = "aboveThresholdUA"
    tender_test_data = ua_t_data

    @unittest.skipUnless(ua_t_data, "UA tender is not reachable")
    def test_tender_transfer(self):
        super(OpenUAOwnershipChangeTest, self).test_tender_transfer()


class OpenEUOwnershipChangeTest(BaseWebTest, BaseTenderOwnershipTest):
    tender_type = "aboveThresholdEU"
    tender_test_data = eu_t_data

    @unittest.skipUnless(eu_t_data, "EU tender is not reachable")
    def test_ender_transfer(self):
        super(OpenEUOwnershipChangeTest, self).test_tender_transfer()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TrensferTest))
    suite.addTest(unittest.makeSuite(TransferResourceTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
