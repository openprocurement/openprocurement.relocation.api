# -*- coding: utf-8 -*-
import unittest
from uuid import uuid4
from copy import deepcopy

from openprocurement.relocation.api.tests.base import ContractOwnershipWebTest
from openprocurement.relocation.api.tests.base import (
    test_contract_data,
    test_transfer_data,
    test_tender_token
)


@unittest.skipUnless(test_contract_data, "openprocurement.contracting.api not exists")
class ContractrOwnershipChangeTest(ContractOwnershipWebTest):
    initial_data = test_contract_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    invalid_operator = 'brokerxx'
    initial_auth = ('Basic', (first_owner, ''))

    def test_change_contract_ownership(self):

        response = self.app.get('/contracts/{}'.format(self.contract['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], "active")

        response = self.app.patch_json('/contracts/{}?acc_token={}'.format(self.contract['id'], test_tender_token),
                                       {"data": {"title": "New Title"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        # create transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        self.assertIn('date', response.json['data'])
        transfer_id = response.json['data']['id']
        transfer_creation_date = response.json['data']['date']
        token = response.json['access']['token']
        self.contract_transfer = response.json['access']['transfer']

        # apply transfer on contract to change its credentials
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer_id, "tender_token":test_tender_token}})

        # try to access with new token
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
            {u'description': u'Request must contain either "id and transfer" or "id and tender_token".', u'location': u'body', u'name': u'name'}
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
        self.app.authorization = authorization

        # use Transfer to get credentials
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        transfer_id_1 = response.json['data']['id']
        contract_transfer = response.json['access']['transfer']
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract['id']),
                                      {"data": {"id": transfer_id_1, "tender_token":test_tender_token}})
        self.assertEqual(response.status, '200 OK')

        # apply used transfer
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

        # try to use transfer by broker without appropriate operator
        self.app.authorization = ('Basic', (self.invalid_operator, ''))

        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Contract operator does not permit ownership change', u'location': u'contract', u'name': u'operator'}
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


    def test_generate_credentials_with_transfer(self):

        self.app.authorization = ('Basic', (self.first_owner, ''))
        #try to get contract credentials
        response = self.app.get('/contracts/{0}/credentials?acc_token={1}'.format(self.contract_id,
                                                                                  self.initial_data['tender_token']), status=405)
        self.assertEqual(response.status, '405 Method Not Allowed')

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        self.assertIn('date', response.json['data'])
        transfer_id_1 = response.json['data']['id']
        transfer_creation_date = response.json['data']['date']
        token_1 = response.json['access']['token']
        self.contract_transfer = response.json['access']['transfer']

        # try to apply Transfer on contract to change credentials without tender_token
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer_id_1}}, status = 422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Request must contain either "id and transfer" or "id and tender_token".', u'location': u'body', u'name': u'name'}
        ])

        # try to apply Transfer on contract with tender_token and transfer token
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer_id_1, "tender_token":test_tender_token, "transfer": self.contract_transfer}}, status = 422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Request must contain either "id and transfer" or "id and tender_token".', u'location': u'body', u'name': u'name'}
        ])

        # try to apply transfer on contract without transfer id
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"tender_token":test_tender_token, "transfer":self.contract_transfer}}, status = 422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'], [
            {u'description': u'This field is required.', u'location': u'body', u'name': u'id'}
        ])

        # apply Transfer on contract to change its credentials
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer_id_1, "tender_token":test_tender_token}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])

        # check whether the owner has remained the same
        self.assertEqual(self.first_owner, response.json['data']['owner'])

        # apply the same Transfer twice
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer_id_1, "tender_token":test_tender_token}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.body, 'null')

        # try to access with new token
        response = self.app.patch_json('/contracts/{}?acc_token={}'.format(self.contract['id'], token_1),
                                       {"data": {"title": "New Title"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['title'], "New Title")

        # contract location is stored in Transfer
        response = self.app.get('/transfers/{}'.format(transfer_id_1))
        transfer = response.json['data']
        transfer_modification_date = transfer['date']
        self.assertEqual(transfer['usedFor'], '/contracts/' + self.contract_id)
        self.assertNotEqual(transfer_creation_date, transfer_modification_date)

        # change credentials second time
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        transfer_id_2 = response.json['data']['id']
        token_2 = response.json['access']['token']
        self.assertEqual(response.status, '201 Created')
        self.assertIn('date', response.json['data'])
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer_id_2, "tender_token":test_tender_token}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertNotEqual(token_1, token_2)

        # first access token is non-workable
        response = self.app.patch_json('/contracts/{}?acc_token={}'.format(self.contract_id, token_1),
                                       {"data": {"status": "active"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        # second access token is workable
        response = self.app.patch_json('/contracts/{}?acc_token={}'.format(self.contract['id'], token_2),
                                       {"data": {"title": "New Title 2"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['title'], "New Title 2")

        # try to change contract credentials with wrong owner
        authorization = self.app.authorization
        self.app.authorization = ('Basic', (self.second_owner, ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        self.assertIn('date', response.json['data'])
        transfer_id_1 = response.json['data']['id']
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer_id_1, "tender_token":test_tender_token}}, status = 403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u"Only owner is allowed to generate new credentials.", u'location': u'body', u'name': u'transfer'}])

        # terminated contract is also protected
        self.app.authorization = authorization
        response = self.app.patch_json('/contracts/{}?acc_token={}'.format(self.contract_id, token_2),
                                       {"data": {"status": "terminated", "amountPaid": {"amount": 777}}})
        self.assertEqual(response.status, '200 OK')

        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        transfer_id_3 = response.json['data']['id']
        token_2 = response.json['access']['token']
        self.assertEqual(response.status, '201 Created')
        self.assertIn('date', response.json['data'])
        response = self.app.post_json('/contracts/{}/ownership'.format(self.contract_id),
                                      {"data": {"id": transfer_id_3, "tender_token":test_tender_token}}, status = 403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u"Can't update credentials in current (terminated) contract status", u'location': u'body', u'name': u'data'}])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ContractrOwnershipChangeTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
