# -*- coding: utf-8 -*-
import unittest

from openprocurement.relocation.api.tests.base import OwnershipWebTest, OpenUAOwnershipWebTest, OpenEUOwnershipWebTest
from openprocurement.relocation.api.tests.base import (
    test_tender_data,
    test_ua_tender_data,
    test_uadefense_tender_data,
    test_eu_tender_data,
    test_tender_reporting_data,
    test_tender_negotiation_data,
    test_tender_negotiation_quick_data,
    test_transfer_data)


class TenderOwnershipChangeTest(OwnershipWebTest):
    initial_data = test_tender_data
    first_owner = 'broker'
    second_owner = 'broker1'
    test_owner = 'broker1t'
    invalid_owner = 'broker3'
    initial_auth = ('Basic', (first_owner, ''))

    def test_change_tender_ownership(self):
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id), {"data": {"id": 12}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'], [
            {u'description': u'This field is required.', u'location': u'body', u'name': u'transfer'}
        ])

        response = self.app.get('/tenders/{}'.format(self.tender_id))
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

        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer['id'], 'transfer': self.tender_transfer}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertEqual(self.second_owner, response.json['data']['owner'])

        # tender location is stored in Transfer
        response = self.app.get('/transfers/{}'.format(transfer['id']))
        transfer = response.json['data']
        transfer_modification_date = transfer['date']
        self.assertEqual(transfer['usedFor'], '/tenders/' + self.tender_id)
        self.assertNotEqual(transfer_creation_date, transfer_modification_date)

        # try to use already applied transfer
        self.app.authorization = authorization
        response = self.app.post_json('/tenders', {'data': self.initial_data})
        tender = response.json['data']
        access = response.json['access']
        self.app.authorization = ('Basic', (self.second_owner, ''))
        response = self.app.post_json('/tenders/{}/ownership'.format(tender['id']),
                                      {"data": {"id": transfer['id'], 'transfer': access['transfer']}}, status=403)
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
                                      {"data": {"id": transfer['id'], 'transfer': access['transfer']}}, status=200)
        self.assertEqual(self.second_owner, response.json['data']['owner'])

        # broker2 can change the tender (first tender which created in test setup)
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, new_access_token),
                                       {"data": {"description": "broker2 now can change the tender"}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertIn('owner', response.json['data'])
        self.assertEqual(response.json['data']['owner'], self.second_owner)

        self.app.authorization = authorization
        # old ownfer now can`t change tender
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, new_access_token),
                                       {"data": {"description": "yummy donut"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
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

        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])

        # test level permits to change ownership for 'test' tenders
        # first try on non-test tender
        self.app.authorization = ('Basic', (self.test_owner, ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'mode'}
        ])

        # set test mode and try to change ownership
        self.app.authorization = ('Basic', ('administrator', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'mode': 'test'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['mode'], 'test')

        self.app.authorization = ('Basic', (self.test_owner, ''))
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
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
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])


class OpenUATenderOwnershipChangeTest(OpenUAOwnershipWebTest, TenderOwnershipChangeTest):
    tender_type = "aboveThresholdUA"
    initial_data = test_ua_tender_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'

    def test_change_tender_ownership(self):
        super(OpenUATenderOwnershipChangeTest, self).test_change_tender_ownership()


class OpenUADefenseTenderOwnershipChangeTest(OpenUAOwnershipWebTest, TenderOwnershipChangeTest):
    tender_type = "aboveThresholdUA.defense"
    initial_data = test_uadefense_tender_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'

    def test_change_tender_ownership(self):
        super(OpenUADefenseTenderOwnershipChangeTest, self).test_change_tender_ownership()


class OpenEUTenderOwnershipChangeTest(OpenEUOwnershipWebTest, TenderOwnershipChangeTest):
    tender_type = "aboveThresholdEU"
    initial_data = test_eu_tender_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'

    def test_change_tender_ownership(self):
        super(OpenEUTenderOwnershipChangeTest, self).test_change_tender_ownership()


class ReportingTenderOwnershipChangeTest(OpenUAOwnershipWebTest, TenderOwnershipChangeTest):
    tender_type = "reporting"
    initial_data = test_tender_reporting_data
    first_owner = 'broker'
    second_owner = 'broker1'
    test_owner = 'broker1t'
    invalid_owner = 'broker3'

    def test_change_tender_ownership(self):
        super(ReportingTenderOwnershipChangeTest, self).test_change_tender_ownership()


class NegotiationTenderOwnershipChangeTest(OpenUAOwnershipWebTest, TenderOwnershipChangeTest):
    tender_type = "negotioation"
    initial_data = test_tender_negotiation_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'

    def test_change_tender_ownership(self):
        super(NegotiationTenderOwnershipChangeTest, self).test_change_tender_ownership()


class NegotiationQuickTenderOwnershipChangeTest(OpenUAOwnershipWebTest, TenderOwnershipChangeTest):
    tender_type = "negotioation.quick"
    initial_data = test_tender_negotiation_quick_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'

    def test_change_tender_ownership(self):
        super(NegotiationQuickTenderOwnershipChangeTest, self).test_change_tender_ownership()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderOwnershipChangeTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
