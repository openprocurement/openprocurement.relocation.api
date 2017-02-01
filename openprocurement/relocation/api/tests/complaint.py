# -*- coding: utf-8 -*-
import unittest

from openprocurement.relocation.api.tests.base import OwnershipWebTest, OpenUAOwnershipWebTest, OpenEUOwnershipWebTest
from openprocurement.relocation.api.tests.base import (
    test_tender_data,
    test_ua_tender_data,
    test_uadefense_tender_data,
    test_eu_tender_data,
    test_tender_stage2_data_ua,
    test_tender_stage2_data_eu,
    test_transfer_data)
from openprocurement.relocation.api.tests.base import (
    test_bid_data,
    test_ua_bid_data,
    test_uadefense_bid_data,
    test_eu_bid_data,
    author,
    test_organization)


class ComplaintOwnershipChangeTest(OwnershipWebTest):
    initial_data = test_tender_data
    initial_bid = test_bid_data
    first_owner = 'broker'
    owner2 = 'broker1'
    test_owner = 'broker1t'
    invalid_owner = 'broker3'
    First_provider = 'broker'
    second_provider = 'broker2'
    invalid_provider = 'broker4'
    initial_auth = ('Basic', (first_owner, ''))

    def test_change_complaint_ownership(self):
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
        self.assertEqual(tender_doc['complaints'][0]['owner'], self.First_provider)

        self.app.authorization = ('Basic', (self.second_provider, ''))

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        # try to change ownership with invalid transfer token
        response = self.app.post_json('/tenders/{}/complaints/{}/ownership'.format(self.tender_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': "fake_transfer_token"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/complaints/{}/ownership'.format(self.tender_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer}})
        self.assertEqual(response.status, '200 OK')
        complaint_transfer = transfer_tokens['transfer']

        # check complaint owner
        tender_doc = self.db.get(self.tender_id)
        self.assertEqual(tender_doc['complaints'][0]['owner'], self.second_provider)

        self.app.authorization = ('Basic', (self.invalid_provider, ''))
        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer2 = response.json['data']

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/complaints/{}/ownership'.format(self.tender_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])

        # try to use already applied transfer
        self.app.authorization = ('Basic', (self.First_provider, ''))

        response = self.app.post_json('/tenders/{}/complaints'.format(
            self.tender_id), {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        complaint2 = response.json['data']
        complaint2_transfer = response.json['access']['transfer']
        self.assertNotEqual(complaint['id'], complaint2['id'])

        self.app.authorization = ('Basic', (self.second_provider, ''))
        response = self.app.post_json('/tenders/{}/complaints/{}/ownership'.format(self.tender_id, complaint2['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint2_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
        ])


class OpenUAComplaintOwnershipChangeTest(OpenUAOwnershipWebTest, ComplaintOwnershipChangeTest):
    tender_type = "aboveThresholdUA"
    initial_data = test_ua_tender_data
    initial_bid = test_ua_bid_data
    first_owner = 'broker'
    owner2 = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    First_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'

    def test_change_complaint_ownership(self):
        super(OpenUAComplaintOwnershipChangeTest, self).test_change_complaint_ownership()


class OpenUADefenseComplaintOwnershipChangeTest(OpenUAOwnershipWebTest, ComplaintOwnershipChangeTest):
    tender_type = "aboveThresholdUA.defense"
    initial_data = test_uadefense_tender_data
    initial_bid = test_uadefense_bid_data
    first_owner = 'broker'
    owner2 = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    First_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'

    def test_change_complaint_ownership(self):
        super(OpenUADefenseComplaintOwnershipChangeTest, self).test_change_complaint_ownership()


class OpenUACompetitiveDialogueStage2ComplaintOwnershipChangeTest(OpenUAOwnershipWebTest):
    tender_type = "competitiveDialogueUA.stage2"
    initial_data = test_tender_stage2_data_ua
    initial_bid = test_eu_bid_data
    first_owner = 'broker'
    owner2 = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    First_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'
    initial_auth = ('Basic', ('competitive_dialogue', ''))

    def test_change_complaint_ownership(self):
        self.app.authorization = ('Basic', ('broker', ''))
        self.set_tendering_status()
        response = self.app.post_json('/tenders/{}/complaints'.format(self.tender_id),
                                      {'data': {'title': 'complaint title',
                                                'description': 'complaint description',
                                                'author': author,
                                                'status': 'claim'}})
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
        self.assertEqual(tender_doc['complaints'][0]['owner'], self.First_provider)

        self.app.authorization = ('Basic', (self.second_provider, ''))

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        # try to change ownership with invalid transfer token
        response = self.app.post_json('/tenders/{}/complaints/{}/ownership'.format(self.tender_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': "fake_transfer_token"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/complaints/{}/ownership'.format(self.tender_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer}})
        self.assertEqual(response.status, '200 OK')
        complaint_transfer = transfer_tokens['transfer']

        # check complaint owner
        tender_doc = self.db.get(self.tender_id)
        self.assertEqual(tender_doc['complaints'][0]['owner'], self.second_provider)

        self.app.authorization = ('Basic', (self.invalid_provider, ''))
        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer2 = response.json['data']

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/complaints/{}/ownership'.format(self.tender_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])

        # try to use already applied transfer
        self.app.authorization = ('Basic', (self.First_provider, ''))

        response = self.app.post_json('/tenders/{}/complaints'.format(self.tender_id),
                                      {'data': {'title': 'complaint title',
                                                'description': 'complaint description',
                                                'author': author,
                                                'status': 'claim'}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        complaint2 = response.json['data']
        complaint2_transfer = response.json['access']['transfer']
        self.assertNotEqual(complaint['id'], complaint2['id'])

        self.app.authorization = ('Basic', (self.second_provider, ''))
        response = self.app.post_json('/tenders/{}/complaints/{}/ownership'.format(self.tender_id, complaint2['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint2_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
        ])


class OpenEUCompetitiveDialogueStage2ComplaintOwnershipChangeTest(OpenEUOwnershipWebTest,
                                                                  OpenUACompetitiveDialogueStage2ComplaintOwnershipChangeTest):
    tender_type = "competitiveDialogueEU.stage2"
    initial_data = test_tender_stage2_data_eu
    first_owner = 'broker'
    owner2 = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    First_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'
    initial_auth = ('Basic', ('competitive_dialogue', ''))

    def test_change_complaint_ownership(self):
        super(OpenEUCompetitiveDialogueStage2ComplaintOwnershipChangeTest, self).test_change_complaint_ownership()


class OpenEUComplaintOwnershipChangeTest(OpenEUOwnershipWebTest, ComplaintOwnershipChangeTest):
    tender_type = "aboveThresholdEU"
    initial_data = test_eu_tender_data
    initial_bid = test_eu_bid_data
    first_owner = 'broker'
    owner2 = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    First_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'

    def test_change_complaint_ownership(self):
        super(OpenEUComplaintOwnershipChangeTest, self).test_change_complaint_ownership()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ComplaintOwnershipChangeTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
