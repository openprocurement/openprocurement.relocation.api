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
    test_tender_stage2_data_eu,
    test_tender_stage2_data_ua,
    test_transfer_data)
from openprocurement.relocation.api.tests.base import (
    test_bid_data,
    test_ua_bid_data,
    test_uadefense_bid_data,
    test_eu_bid_data,
    test_organization,
    author)


class AwardComplaintOwnershipChangeTest(OwnershipWebTest):
    initial_data = test_tender_data
    initial_bid = test_bid_data
    first_owner = 'broker'
    second_owner = 'broker1'
    test_owner = 'broker1t'
    invalid_owner = 'broker3'
    First_provider = 'broker'
    second_provider = 'broker2'
    invalid_provider = 'broker4'
    initial_auth = ('Basic', (first_owner, ''))

    def test_change_award_complaint_ownership(self):

        self.set_tendering_status()
        authorization = self.app.authorization
        self.app.authorization = ('Basic', (self.First_provider, ''))

        response = self.app.post_json('/tenders/{}/bids'.format(
            self.tender_id), self.initial_bid)
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        first_bid = response.json['data']

        self.app.authorization = ('Basic', (self.second_provider, ''))

        response = self.app.post_json('/tenders/{}/bids'.format(
            self.tender_id), self.initial_bid)
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        bid = response.json['data']
        bid_token = response.json['access']['token']

        # submit award
        self.app.authorization = authorization
        self.set_qualification_status()
        self.app.authorization = ('Basic', ('token', ''))
        response = self.app.post_json('/tenders/{}/awards'.format(
            self.tender_id), {'data': {'suppliers': [test_organization], 'status': 'pending', 'bid_id': first_bid['id']}})
        award = response.json['data']
        self.award_id = award['id']

        # submit complaint from broker
        self.app.authorization = ('Basic', (self.second_provider, ''))

        response = self.app.post_json('/tenders/{}/awards/{}/complaints?acc_token={}'.format(
            self.tender_id, self.award_id, bid_token), {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}})
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
        self.assertEqual(tender_doc['awards'][0]['complaints'][0]['owner'], self.second_provider)

        self.app.authorization = ('Basic', (self.second_provider, ''))

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        # try to change ownership with invalid transfer token
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': "fake_transfer_token"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer}})
        self.assertEqual(response.status, '200 OK')
        complaint_transfer = transfer_tokens['transfer']

        # check complaint owner
        tender_doc = self.db.get(self.tender_id)
        self.assertEqual(tender_doc['awards'][0]['complaints'][0]['owner'], self.second_provider)

        self.app.authorization = ('Basic', (self.invalid_provider, ''))
        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer2 = response.json['data']

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])

        # try to use already applied transfer
        self.app.authorization = ('Basic', (self.second_provider, ''))

        response = self.app.post_json('/tenders/{}/awards/{}/complaints?acc_token={}'.format(
            self.tender_id, self.award_id, bid_token), {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        complaint2 = response.json['data']
        complaint2_transfer = response.json['access']['transfer']
        self.assertNotEqual(complaint['id'], complaint2['id'])

        self.app.authorization = ('Basic', (self.First_provider, ''))
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint2['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint2_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
        ])


class OpenUAAwardComplaintOwnershipChangeTest(OpenUAOwnershipWebTest, AwardComplaintOwnershipChangeTest):
    tender_type = "aboveThresholdUA"
    initial_data = test_ua_tender_data
    initial_bid = test_ua_bid_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    First_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'

    def test_change_award_complaint_ownership(self):
        super(OpenUAAwardComplaintOwnershipChangeTest, self).test_change_award_complaint_ownership()


class OpenUADefenseAwardComplaintOwnershipChangeTest(OpenUAOwnershipWebTest, AwardComplaintOwnershipChangeTest):
    tender_type = "aboveThresholdUA.defense"
    initial_data = test_uadefense_tender_data
    initial_bid = test_uadefense_bid_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    First_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'

    def test_change_award_complaint_ownership(self):
        super(OpenUADefenseAwardComplaintOwnershipChangeTest, self).test_change_award_complaint_ownership()


class OpenUACompatitiveDialogueAwardComplaintOwnershipChangeTest(OpenUAOwnershipWebTest):
    tender_type = "competitiveDialogueUA.stage2"
    initial_data = test_tender_stage2_data_ua
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    First_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'
    initial_auth = ('Basic', ('competitive_dialogue', ''))

    def test_change_award_complaint_ownership(self):
        authorization = self.app.authorization
        self.set_tendering_status()
        self.app.authorization = ('Basic', (self.First_provider, ''))
        response = self.app.post_json('/tenders/{}/bids'.format(self.tender_id),
                                      {'data': {'selfEligible': True, 'selfQualified': True,
                                                'tenderers': [author], "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        first_bid = response.json['data']

        self.app.authorization = ('Basic', (self.second_provider, ''))

        response = self.app.post_json('/tenders/{}/bids'.format(self.tender_id),
                                      {'data': {'selfEligible': True, 'selfQualified': True,
                                                'tenderers': [author], "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        bid = response.json['data']
        bid_token = response.json['access']['token']

        # submit award
        self.app.authorization = authorization
        self.set_qualification_status()
        self.app.authorization = ('Basic', ('token', ''))
        response = self.app.post_json('/tenders/{}/awards'.format(
            self.tender_id), {'data': {'suppliers': [test_organization], 'status': 'pending', 'bid_id': first_bid['id']}})
        award = response.json['data']
        self.award_id = award['id']

        # submit complaint from broker
        self.app.authorization = ('Basic', (self.second_provider, ''))

        response = self.app.post_json('/tenders/{}/awards/{}/complaints?acc_token={}'.format(
            self.tender_id, self.award_id, bid_token), {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}})
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
        self.assertEqual(tender_doc['awards'][0]['complaints'][0]['owner'], self.second_provider)

        self.app.authorization = ('Basic', (self.second_provider, ''))

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        # try to change ownership with invalid transfer token
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': "fake_transfer_token"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer}})
        self.assertEqual(response.status, '200 OK')
        complaint_transfer = transfer_tokens['transfer']

        # check complaint owner
        tender_doc = self.db.get(self.tender_id)
        self.assertEqual(tender_doc['awards'][0]['complaints'][0]['owner'], self.second_provider)

        self.app.authorization = ('Basic', (self.invalid_provider, ''))
        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer2 = response.json['data']

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])

        # try to use already applied transfer
        self.app.authorization = ('Basic', (self.second_provider, ''))

        response = self.app.post_json('/tenders/{}/awards/{}/complaints?acc_token={}'.format(
            self.tender_id, self.award_id, bid_token), {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        complaint2 = response.json['data']
        complaint2_transfer = response.json['access']['transfer']
        self.assertNotEqual(complaint['id'], complaint2['id'])

        self.app.authorization = ('Basic', (self.First_provider, ''))
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint2['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint2_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
        ])


class OpenEUAwardComplaintOwnershipChangeTest(OpenEUOwnershipWebTest):
    tender_type = "aboveThresholdEU"
    initial_data = test_eu_tender_data
    initial_bid = test_eu_bid_data
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    First_provider = 'broker'
    second_provider = 'broker4'
    invalid_provider = 'broker2'

    def test_change_award_complaint_ownership(self):

        self.set_tendering_status()
        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('broker', ''))

        # create bids
        response = self.app.post_json('/tenders/{}/bids'.format(
            self.tender_id), self.initial_bid)
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        first_bid = response.json['data']

        self.app.authorization = ('Basic', ('broker4', ''))

        response = self.app.post_json('/tenders/{}/bids'.format(
            self.tender_id), self.initial_bid)
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        bid = response.json['data']
        bid_token = response.json['access']['token']

        # switch to active.pre-qualification
        self.set_pre_qualification_status({"id": self.tender_id, 'status': 'active.tendering'})
        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(
            self.tender_id), {"data": {"id": self.tender_id}})
        self.assertEqual(response.json['data']['status'], 'active.pre-qualification')

        # qualify bids
        response = self.app.get('/tenders/{}/qualifications'.format(self.tender_id))
        self.app.authorization = authorization
        for qualification in response.json['data']:
            response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(
            self.tender_id, qualification['id'], self.tender_token), {"data": {"status": "active", "qualified": True, "eligible": True}})
            self.assertEqual(response.status, "200 OK")

        # switch to active.pre-qualification.stand-still
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(
            self.tender_id, self.tender_token), {"data": {"status": 'active.pre-qualification.stand-still'}})
        self.assertEqual(response.json['data']['status'], 'active.pre-qualification.stand-still')

        # switch to active.auction
        self.set_auction_status({"id": self.tender_id, 'status': 'active.pre-qualification.stand-still'})
        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(
            self.tender_id), {"data": {"id": self.tender_id}})
        self.assertEqual(response.json['data']['status'], "active.auction")

        # submit award
        self.app.authorization = authorization
        self.set_qualification_status()
        self.app.authorization = ('Basic', ('token', ''))
        response = self.app.post_json('/tenders/{}/awards'.format(
            self.tender_id), {'data': {'suppliers': [test_organization], 'status': 'pending', 'bid_id': first_bid['id']}})
        award = response.json['data']
        self.award_id = award['id']

        # submit complaint from broker
        self.app.authorization = ('Basic', ('broker4', ''))

        response = self.app.post_json('/tenders/{}/awards/{}/complaints?acc_token={}'.format(
            self.tender_id, self.award_id, bid_token), {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}})
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
        self.assertEqual(tender_doc['awards'][0]['complaints'][0]['owner'], self.second_provider)

        self.app.authorization = ('Basic', ('broker4', ''))

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        # try to change ownership with invalid transfer token
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': "fake_transfer_token"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer}})
        self.assertEqual(response.status, '200 OK')
        complaint_transfer = transfer_tokens['transfer']

        # check complaint owner
        tender_doc = self.db.get(self.tender_id)
        self.assertEqual(tender_doc['awards'][0]['complaints'][0]['owner'], self.second_provider)

        self.app.authorization = ('Basic', ('broker2', ''))
        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer2 = response.json['data']

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])

        # try to use already applied transfer
        self.app.authorization = ('Basic', ('broker4', ''))

        response = self.app.post_json('/tenders/{}/awards/{}/complaints?acc_token={}'.format(
            self.tender_id, self.award_id, bid_token), {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        complaint2 = response.json['data']
        complaint2_transfer = response.json['access']['transfer']
        self.assertNotEqual(complaint['id'], complaint2['id'])

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint2['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint2_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
        ])


class NegotiationAwardComplaintOwnershipChangeTest(OpenUAOwnershipWebTest):
    tender_type = "negotioation"
    initial_data = test_tender_negotiation_data

    def test_change_award_complaint_ownership(self):
        # Create award
        request_path = '/tenders/{}/awards?acc_token={}'.format(self.tender_id, self.tender_token)
        response = self.app.post_json(request_path, {'data': {'suppliers': [test_organization], 'qualified': True,
                                                              'status': 'pending'}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        award = response.json['data']
        self.award_id = award['id']

        # submit complaint from broker
        self.app.authorization = ('Basic', ('broker4', ''))

        response = self.app.post_json('/tenders/{}/awards/{}/complaints'.format(
            self.tender_id, self.award_id), {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}})
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
        self.assertEqual(tender_doc['awards'][0]['complaints'][0]['owner'], 'broker4')

        self.app.authorization = ('Basic', ('broker', ''))

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        # try to change ownership with invalid transfer token
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': "fake_transfer_token"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])
        # change complaint ownership
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer}})
        self.assertEqual(response.status, '200 OK')
        complaint_transfer = transfer_tokens['transfer']

        # check complaint owner
        tender_doc = self.db.get(self.tender_id)
        self.assertEqual(tender_doc['awards'][0]['complaints'][0]['owner'], 'broker')

        self.app.authorization = ('Basic', ('broker2', ''))
        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer2 = response.json['data']

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])

        # try to use already applied transfer
        self.app.authorization = ('Basic', ('broker', ''))

        response = self.app.post_json('/tenders/{}/awards/{}/complaints'.format(
            self.tender_id, self.award_id), {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        complaint2 = response.json['data']
        complaint2_transfer = response.json['access']['transfer']
        self.assertNotEqual(complaint['id'], complaint2['id'])

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/awards/{}/complaints/{}/ownership'.format(self.tender_id, self.award_id, complaint2['id']),
                                      {"data": {"id": transfer['id'], 'transfer': complaint2_transfer}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
        ])


class NegotiationQuickAwardComplaintOwnershipChangeTest(NegotiationAwardComplaintOwnershipChangeTest):
    tender_type = "negotioation.quick"
    initial_data = test_tender_negotiation_quick_data

    def test_change_award_complaint_ownership(self):
        super(NegotiationQuickAwardComplaintOwnershipChangeTest, self).test_change_award_complaint_ownership()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(AwardComplaintOwnershipChangeTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
