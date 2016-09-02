# -*- coding: utf-8 -*-
import unittest
from uuid import uuid4
from copy import deepcopy

from openprocurement.relocation.api.tests.base import ContractOwnershipWebTest
from openprocurement.relocation.api.tests.base import (
    test_contract_data,
    test_transfer_data
)


class ContractrOwnershipChangeTest(ContractOwnershipWebTest):
    initial_data = test_contract_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    initial_auth = ('Basic', (first_owner, ''))

    def test_change_contract_ownership(self):
        tender_token = self.initial_data['tender_token']

        response = self.app.get('/contracts/{}'.format(self.contract['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], "active")

        response = self.app.patch_json('/contracts/{}?acc_token={}'.format(self.contract['id'], tender_token),
                                       {"data": {"title": "New Title"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        response = self.app.patch_json('/contracts/{}/credentials?acc_token={}'.format(self.contract['id'], tender_token),
                                       {'data': ''})
        self.assertEqual(response.status, '200 OK')
        token = response.json['access']['token']
        self.contract_transfer = response.json['access']['transfer']

        response = self.app.patch_json('/contracts/{}?acc_token={}'.format(self.contract['id'], token),
                                       {"data": {"title": "New Title"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['title'], "New Title")

        response = self.app.get('/contracts/{}'.format(self.contract_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['owner'], self.first_owner)

        authorization = self.app.authorization
        self.app.authorization = ('Basic', (self.second_owner, ''))

        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        self.assertIn('date', transfer)
        transfer_creation_date = transfer['date']
        new_access_token = response.json['access']['token']
        new_transfer_token = response.json['access']['transfer']

        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id), {"data": {"id": 12}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'], [
            {u'description': u'This field is required.', u'location': u'body', u'name': u'transfer'}
        ])

        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer['id'], 'transfer': self.contract_transfer}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertEqual(self.second_owner, response.json['data']['owner'])

        # contract location is stored in Transfer
        response = self.app.get('/transfers/{}'.format(transfer['id']))
        transfer = response.json['data']
        transfer_modification_date = transfer['date']
        self.assertEqual(transfer['usedFor'], '/contracts/' + self.contract_id)
        self.assertNotEqual(transfer_creation_date, transfer_modification_date)

        # try to use already applied transfer
        self.app.authorization = ('Basic', ('contracting', ''))
        new_initial_data = deepcopy(self.initial_data)
        new_initial_data['id'] = uuid4().hex
        response = self.app.post_json('/contracts', {'data': new_initial_data})
        self.contract = response.json['data']
        # self.contract_token = response.json['access']['token']
        self.app.authorization = authorization
        response = self.app.patch_json('/contracts/{}/credentials?acc_token={}'.format(self.contract['id'], tender_token),
                                       {'data': ''})
        self.assertEqual(response.status, '200 OK')
        contract_transfer = response.json['access']['transfer']
        self.app.authorization = ('Basic', (self.second_owner, ''))
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract['id']),
                                      {"data": {"id": transfer['id'], 'transfer': contract_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
        ])
        # simulate half-applied transfer activation process (i.e. transfer
        # is successfully applied to a contract and relation is saved in transfer,
        # but contract is not stored with new credentials)
        transfer_doc = self.db.get(transfer['id'])
        transfer_doc['usedFor'] = '/contracts/' + self.contract['id']
        self.db.save(transfer_doc)
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract['id']),
                                      {"data": {"id": transfer['id'], 'transfer': contract_transfer}}, status=200)
        self.assertEqual(self.second_owner, response.json['data']['owner'])

        # broker2 can change the contract (first contract which created in test setup)
        response = self.app.patch_json('/contracts/{}?acc_token={}'.format(self.contract_id, new_access_token),
                                       {"data": {"description": "broker2 now can change the contract"}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertIn('owner', response.json['data'])
        self.assertEqual(response.json['data']['owner'], self.second_owner)

        self.app.authorization = authorization
        # old ownfer now can`t change contract
        response = self.app.patch_json('/contracts/{}?acc_token={}'.format(self.contract_id, new_access_token),
                                       {"data": {"description": "yummy donut"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": 'fake id', 'transfer': 'fake transfer'}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])

        # try to use transfer by broker without appropriate accreditation level
        self.app.authorization = ('Basic', (self.invalid_owner, ''))

        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])

        # test level permits to change ownership for 'test' contracts
        # first try on non-test contract
        self.app.authorization = ('Basic', (self.test_owner, ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'mode'}
        ])

        # set test mode and try to change ownership
        self.app.authorization = ('Basic', ('administrator', ''))
        response = self.app.patch_json('/contracts/{}'.format(self.contract_id), {'data': {'mode': 'test'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['mode'], 'test')

        self.app.authorization = ('Basic', (self.test_owner, ''))
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token}})
        self.assertEqual(response.status, '200 OK')
        self.assertIn('owner', response.json['data'])
        self.assertEqual(response.json['data']['owner'], self.test_owner)

        # test accreditation levels are also sepatated
        self.app.authorization = ('Basic', (self.invalid_owner, ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']

        new_transfer_token = transfer_tokens['transfer']
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ContractrOwnershipChangeTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
