# -*- coding: utf-8 -*-
import unittest

from openprocurement.relocation.api.tests.base import OwnershipWebTest, OpenUAOwnershipWebTest, OpenEUOwnershipWebTest
from openprocurement.relocation.api.tests.base import (
    test_tender_data,
    test_ua_tender_data,
    test_uadefense_tender_data,
    test_eu_tender_data,
    test_tender_data_competitive_ua,
    test_tender_data_competitive_eu,
    test_tender_stage2_data_ua,
    test_tender_stage2_data_eu,
    test_transfer_data)
from openprocurement.relocation.api.tests.base import (
    test_bid_data,
    test_ua_bid_data,
    test_uadefense_bid_data,
    author,
    test_eu_bid_data)


class BidOwnershipChangeTest(OwnershipWebTest):
    initial_data = test_tender_data
    initial_bid = test_bid_data
    first_owner = 'broker'
    second_owner = 'broker1'
    test_owner = 'broker1t'
    invalid_owner = 'broker3'
    first_provider = 'broker'
    second_provider = 'broker2'
    invalid_provider = 'broker4'
    initial_auth = ('Basic', (first_owner, ''))

    def test_change_bid_ownership(self):

        self.set_tendering_status()
        self.app.authorization = ('Basic', (self.first_provider, ''))
        response = self.app.post_json('/tenders/{}/bids'.format(
            self.tender_id), self.initial_bid)
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        bid = response.json['data']
        bid_tokens = response.json['access']

        # current owner can change his bid
        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bid['id'], bid_tokens['token']), {"data": {'value': {"amount": 499}}})
        self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', (self.second_provider, ''))

        # other broker can't change the bid
        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bid['id'], bid_tokens['token']), {"data": {'value': {"amount": 498}}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        # try to change ownership with invalid transfer token
        response = self.app.post_json('/tenders/{}/bids/{}/ownership'.format(self.tender_id, bid['id']),
                                      {"data": {"id": transfer['id'], 'transfer': "fake_transfer_token"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])
        # change bid ownership
        response = self.app.post_json('/tenders/{}/bids/{}/ownership'.format(self.tender_id, bid['id']),
                                      {"data": {"id": transfer['id'], 'transfer': bid_tokens['transfer']}})
        self.assertEqual(response.status, '200 OK')

        # new owner can change the bid using new credentials
        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bid['id'], transfer_tokens['token']), {"data": {'value': {"amount": 495}}})
        self.assertEqual(response.status, '200 OK')

        # try to use already applied transfer
        self.app.authorization = ('Basic', (self.first_provider, ''))

        response = self.app.post_json('/tenders/{}/bids'.format(
            self.tender_id), self.initial_bid)
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        bid2 = response.json['data']
        bid2_transfer = response.json['access']['transfer']
        self.assertNotEqual(bid['id'], bid2['id'])

        self.app.authorization = ('Basic', (self.second_provider, ''))
        response = self.app.post_json('/tenders/{}/bids/{}/ownership'.format(self.tender_id, bid2['id']),
                                      {"data": {"id": transfer['id'], 'transfer': bid2_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
        ])


class OpenUABidOwnershipChangeTest(OpenUAOwnershipWebTest, BidOwnershipChangeTest):
    tender_type = "aboveThresholdUA"
    initial_data = test_ua_tender_data
    initial_bid = test_ua_bid_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    first_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'

    def test_change_bid_ownership(self):
        super(OpenUABidOwnershipChangeTest, self).test_change_bid_ownership()


class OpenUADefenseBidOwnershipChangeTest(OpenUAOwnershipWebTest, BidOwnershipChangeTest):
    tender_type = "aboveThresholdUA.defense"
    initial_data = test_uadefense_tender_data
    initial_bid = test_uadefense_bid_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    first_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'

    def test_change_bid_ownership(self):
        super(OpenUADefenseBidOwnershipChangeTest, self).test_change_bid_ownership()


class OpenUACompatitiveDialogueBidOwnershipChangeTest(OpenUAOwnershipWebTest, BidOwnershipChangeTest):
    tender_type = "competitiveDialogueUA"
    initial_data = test_tender_data_competitive_ua
    initial_bid = test_ua_bid_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    first_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'

    def test_change_bid_ownership(self):
        super(OpenUACompatitiveDialogueBidOwnershipChangeTest, self).test_change_bid_ownership()


class OpenUACompatitiveDialogueStage2BidOwnershipChangeTest(OpenUAOwnershipWebTest):
    tender_type = "competitiveDialogueUA.stage2"
    initial_data = test_tender_stage2_data_ua
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    first_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'
    initial_auth = ('Basic', ('competitive_dialogue', ''))

    def test_change_bid_ownership(self):
        self.set_tendering_status()
        self.app.authorization = ('Basic', (self.first_provider, ''))
        response = self.app.post_json('/tenders/{}/bids'.format(self.tender_id),
                                      {'data': {'selfEligible': True, 'selfQualified': True,
                                                'tenderers': [author], "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        bid = response.json['data']
        bid_tokens = response.json['access']

        # current owner can change his bid
        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bid['id'], bid_tokens['token']), {"data": {'value': {"amount": 499}}})
        self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', (self.second_provider, ''))

        # other broker can't change the bid
        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bid['id'], bid_tokens['token']), {"data": {'value': {"amount": 498}}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        # try to change ownership with invalid transfer token
        response = self.app.post_json('/tenders/{}/bids/{}/ownership'.format(self.tender_id, bid['id']),
                                      {"data": {"id": transfer['id'], 'transfer': "fake_transfer_token"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])
        # change bid ownership
        response = self.app.post_json('/tenders/{}/bids/{}/ownership'.format(self.tender_id, bid['id']),
                                      {"data": {"id": transfer['id'], 'transfer': bid_tokens['transfer']}})
        self.assertEqual(response.status, '200 OK')

        # new owner can change the bid using new credentials
        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bid['id'], transfer_tokens['token']), {"data": {'value': {"amount": 495}}})
        self.assertEqual(response.status, '200 OK')

        # try to use already applied transfer
        self.app.authorization = ('Basic', (self.first_provider, ''))

        response = self.app.post_json('/tenders/{}/bids'.format(self.tender_id),
                                      {'data': {'selfEligible': True, 'selfQualified': True,
                                                'tenderers': [author], "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        bid2 = response.json['data']
        bid2_transfer = response.json['access']['transfer']
        self.assertNotEqual(bid['id'], bid2['id'])

        self.app.authorization = ('Basic', (self.second_provider, ''))
        response = self.app.post_json('/tenders/{}/bids/{}/ownership'.format(self.tender_id, bid2['id']),
                                      {"data": {"id": transfer['id'], 'transfer': bid2_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
        ])


class OpenEUCompatitiveDialogueBidOwnershipChangeTest(OpenEUOwnershipWebTest, BidOwnershipChangeTest):
    tender_type = "competitiveDialogueEU"
    initial_data = test_tender_data_competitive_ua
    initial_bid = test_eu_bid_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    first_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'

    def test_change_bid_ownership(self):
        super(OpenEUCompatitiveDialogueBidOwnershipChangeTest, self).test_change_bid_ownership()


class OpenEUCompatitiveDialogueStage2BidOwnershipChangeTest(OpenEUOwnershipWebTest,
                                                            OpenUACompatitiveDialogueStage2BidOwnershipChangeTest):
    tender_type = "competitiveDialogueEU.stage2"
    initial_data = test_tender_stage2_data_eu
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    first_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'
    initial_auth = ('Basic', ('competitive_dialogue', ''))

    def test_change_bid_ownership(self):
        super(OpenEUCompatitiveDialogueStage2BidOwnershipChangeTest, self).test_change_bid_ownership()


class OpenEUBidOwnershipChangeTest(OpenEUOwnershipWebTest, BidOwnershipChangeTest):
    tender_type = "aboveThresholdEU"
    initial_data = test_eu_tender_data
    initial_bid = test_eu_bid_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    first_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'

    def test_change_bid_ownership(self):
        super(OpenEUBidOwnershipChangeTest, self).test_change_bid_ownership()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BidOwnershipChangeTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
