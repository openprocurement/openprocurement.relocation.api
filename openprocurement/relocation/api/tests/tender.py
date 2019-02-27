# -*- coding: utf-8 -*-
import unittest

from openprocurement.relocation.api.tests.base import (OwnershipWebTest, OpenUAOwnershipWebTest,
                                                       OpenEUOwnershipWebTest,
                                                       CompatitiveDialogueOwnershipWebTest)
from openprocurement.relocation.api.tests.base import (
    test_tender_data,
    test_ua_tender_data,
    test_uadefense_tender_data,
    test_eu_tender_data,
    test_tender_reporting_data,
    test_tender_negotiation_data,
    test_tender_negotiation_quick_data,

    test_tender_stage2_data_ua,
    test_tender_stage2_data_eu,
    test_access_token_stage1,
    test_tender_data_competitive_ua,
    test_tender_data_competitive_eu,
    test_transfer_data)
from openprocurement.tender.openeu.models import TENDERING_DURATION
from openprocurement.api.models import get_now


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
        self.assertEqual(response.json['data']['description'], "broker2 now can change the tender")
        self.assertEqual(response.json['data']['owner'], self.second_owner)

        self.app.authorization = authorization

        # old owner now can`t change tender
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

        # test accreditation levels are also separated
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


class OpenUACompatitiveTenderOwnershipChangeTest(OpenUAOwnershipWebTest, TenderOwnershipChangeTest):
    tender_type = "competitiveDialogueUA"
    initial_data = test_tender_data_competitive_ua
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'
    def test_change_tender_ownership(self):
        super(OpenUACompatitiveTenderOwnershipChangeTest, self).test_change_tender_ownership()


class OpenEUCompatitiveTenderOwnershipChangeTest(OpenEUOwnershipWebTest, TenderOwnershipChangeTest):
    tender_type = "competitiveDialogueEU"
    initial_data = test_tender_data_competitive_eu
    first_owner = 'broker'
    second_owner = 'broker3'
    test_owner = 'broker3t'
    invalid_owner = 'broker1'

    def test_change_tender_ownership(self):
        super(OpenEUCompatitiveTenderOwnershipChangeTest, self).test_change_tender_ownership()


class OpenUACompatitiveDialogueStage2TenderOwnershipChangeTest(CompatitiveDialogueOwnershipWebTest, TenderOwnershipChangeTest):
    tender_type = "competitiveDialogueUA.stage2"
    initial_data = test_tender_stage2_data_ua
    first_owner = 'broker'
    second_owner = 'broker3'
    invalid_owner = 'broker1'
    test_owner1 = 'broker1t'
    test_owner2 = 'broker3t'

    def test_change_tender_ownership(self):

        # try to change ownership with fake data
        self.app.authorization = ('Basic', (self.first_owner, ''))
        tender1_stage2_id = self.tender_id
        response = self.app.post_json('/tenders/{}/ownership'.format(tender1_stage2_id), {"data": {"id": 12}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Request must contain either "id and transfer" or "id and tender_token".', u'location': u'body', u'name': u'name'}
        ])

        # check first tender created
        response = self.app.get('/tenders/{}'.format(tender1_stage2_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['owner'], self.first_owner)

        # create Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        credentials_transfer = response.json['data']
        self.assertIn('date', credentials_transfer)
        credentials_transfer_id = credentials_transfer['id']
        tender_access_token = response.json['access']['token']
        tender_transfer_token = response.json['access']['transfer']

        # apply Transfer on tender to change its credentials
        response = self.app.post_json('/tenders/{}/ownership?pretty_opt=1'.format(tender1_stage2_id),
                              {"data": {"id": credentials_transfer_id, "tender_token":test_access_token_stage1}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender1_stage2_id, tender_access_token),
                                       {'data': {'status': 'active.tendering'}})

        # create Transfer with second owner to change tender owner
        self.app.authorization = ('Basic', (self.second_owner, ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        self.assertIn('date', transfer)
        transfer_creation_date = transfer['date']
        new_access_token = response.json['access']['token']
        new_transfer_token = response.json['access']['transfer']

        # change tender ownership
        response = self.app.post_json('/tenders/{}/ownership'.format(tender1_stage2_id),
                                      {"data": {"id": transfer['id'], 'transfer': tender_transfer_token}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertEqual(self.second_owner, response.json['data']['owner'])

        # tender location is stored in Transfer
        response = self.app.get('/transfers/{}'.format(transfer['id']))
        transfer = response.json['data']
        transfer_modification_date = transfer['date']
        self.assertEqual(transfer['usedFor'], '/tenders/' + tender1_stage2_id)
        self.assertNotEqual(transfer_creation_date, transfer_modification_date)

        # second owner can change the tender
        now = get_now()
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender1_stage2_id, new_access_token),
                                       {"data": {"tenderPeriod": {"endDate": (now + TENDERING_DURATION).isoformat()}}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertIn('owner', response.json['data'])
        self.assertEqual(response.json['data']['owner'], self.second_owner)
        self.assertEqual(response.json['data']["tenderPeriod"]['endDate'], (now + TENDERING_DURATION).isoformat())


        # first owner now can`t change tender
        self.app.authorization = ('Basic', (self.first_owner, ''))

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender1_stage2_id, new_access_token),
                                       {"data": {"tenderPeriod": {"endDate": (now + TENDERING_DURATION).isoformat()}}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        response = self.app.post_json('/tenders/{}/ownership'.format(tender1_stage2_id),
                                      {"data": {"id": 'fake id', 'transfer': 'fake transfer'}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer or tender token', u'location': u'body', u'name': u'transfer'}
        ])

        # try to use already applied transfer on new tender created by bridge
        self.app.authorization = ('Basic', ('competitive_dialogue', ''))

        response = self.app.post_json('/tenders', {'data': self.initial_data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('transfer', response.json['access'])
        self.assertNotIn('transfer_token', response.json['data'])
        tender2_stage2 = response.json['data']
        tender2_stage2_id = tender2_stage2['id']
        self.tender_id = tender2_stage2_id
        self.set_status('draft.stage2')

        # create Transfer to get tender credentials
        self.app.authorization = ('Basic', (self.first_owner, ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        credentials_transfer = response.json['data']
        self.assertIn('date', credentials_transfer)
        credentials_transfer_id = credentials_transfer['id']
        tender2_transfer_token = response.json['access']['transfer']

        # apply Transfer on tender to get its credentials
        response = self.app.post_json('/tenders/{}/ownership?pretty_opt=1'.format(tender2_stage2_id),
                              {"data": {"id": credentials_transfer_id, "tender_token":test_access_token_stage1}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])

        self.app.authorization = ('Basic', (self.second_owner, ''))
        response = self.app.post_json('/tenders/{}/ownership'.format(tender2_stage2['id']),
                                      {"data": {"id": transfer['id'], 'transfer': tender2_transfer_token}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
        ])

        # simulate half-applied transfer activation process (i.e. transfer
        # is successfully applied to a tender and relation is saved in transfer,
        # but tender is not stored with new credentials)
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer2 = response.json['data']
        self.assertIn('date', transfer2)
        transfer_doc = self.db.get(transfer2['id'])
        transfer_doc['usedFor'] = '/tenders/' + tender2_stage2['id']
        self.db.save(transfer_doc)
        response = self.app.post_json('/tenders/{}/ownership'.format(tender2_stage2['id']),
                                      {"data": {"id": transfer2['id'], 'transfer': tender2_transfer_token}}, status=200)
        self.assertEqual(self.second_owner, response.json['data']['owner'])

        # try to use transfer by broker without appropriate accreditation level
        self.app.authorization = ('Basic', (self.invalid_owner, ''))

        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        response = self.app.post_json('/tenders/{}/ownership'.format(tender1_stage2_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])

        # test level permits to change ownership for 'test' tenders
        # first try on non-test tender
        self.app.authorization = ('Basic', (self.test_owner2, ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        response = self.app.post_json('/tenders/{}/ownership'.format(tender1_stage2_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'mode'}
        ])

        # set test mode and try to change ownership
        self.app.authorization = ('Basic', ('administrator', ''))
        response = self.app.patch_json('/tenders/{}'.format(tender1_stage2_id), {'data': {'mode': 'test'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['mode'], 'test')

        self.app.authorization = ('Basic', (self.test_owner2, ''))
        response = self.app.post_json('/tenders/{}/ownership'.format(tender1_stage2_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token}})
        self.assertEqual(response.status, '200 OK')
        self.assertIn('owner', response.json['data'])
        self.assertEqual(response.json['data']['owner'], self.test_owner2)

        # test accreditation levels are also separated
        self.app.authorization = ('Basic', (self.test_owner1, ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']

        new_transfer_token = transfer_tokens['transfer']
        response = self.app.post_json('/tenders/{}/ownership'.format(tender1_stage2_id),
                                      {"data": {"id": transfer['id'], 'transfer': new_transfer_token}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Broker Accreditation level does not permit ownership change',
             u'location': u'procurementMethodType', u'name': u'accreditation'}
        ])

    def test_generate_credentials_with_transfer(self):

        self.app.authorization = ('Basic', (self.first_owner, ''))

        # create Transfer to get new credentials
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        self.assertIn('date', transfer)
        transfer_creation_date = transfer['date']
        transfer_id_1 = transfer['id']
        new_access_token_1 = response.json['access']['token']
        new_transfer_token = response.json['access']['transfer']

        # try to generate new tender creadentials without tender token
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer_id_1}}, status = 422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Request must contain either "id and transfer" or "id and tender_token".', u'location': u'body', u'name': u'name'}
        ])

        # apply Transfer on tender to change its credentials
        response = self.app.post_json('/tenders/{}/ownership?pretty_opt=1'.format(self.tender_id),
                              {"data": {"id": transfer_id_1, "tender_token":test_access_token_stage1}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])

        # check whether the owner has remained the same
        self.assertEqual(self.first_owner, response.json['data']['owner'])

        # try to access tender with new credentials
        now = get_now()
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, new_access_token_1),
                                        {"data": {"tenderPeriod": {"endDate": (now + TENDERING_DURATION).isoformat()}}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['tenderPeriod']['endDate'], (now + TENDERING_DURATION).isoformat())

        # apply the same Transfer twice
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer_id_1, "tender_token":test_access_token_stage1}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.body, 'null')

        # tender location is stored in Transfer
        response = self.app.get('/transfers/{}'.format(transfer_id_1))
        transfer = response.json['data']
        transfer_modification_date = transfer['date']
        self.assertEqual(transfer['usedFor'], '/tenders/' + self.tender_id)
        self.assertNotEqual(transfer_creation_date, transfer_modification_date)

        # create another Transfer
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        self.assertIn('date', transfer)
        transfer_creation_date = transfer['date']
        transfer_id_2 = transfer['id']
        new_access_token_2 = response.json['access']['token']
        new_transfer_token_2 = response.json['access']['transfer']

        # try to apply Transfer on tender with both tender_token and transfer token
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer_id_2, "tender_token":test_access_token_stage1, "transfer": new_transfer_token_2}}, status = 422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Request must contain either "id and transfer" or "id and tender_token".', u'location': u'body', u'name': u'name'}
        ])

        # try to apply transfer on tender without transfer id 
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"tender_token":test_access_token_stage1, "transfer": new_transfer_token_2}}, status = 422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'],[
            {u'description': u'This field is required.', u'location':u'body', u'name': u'id'}
        ])

        # change credentials second time
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer_id_2, "tender_token":test_access_token_stage1}})
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('transfer', response.json['data'])
        self.assertNotIn('transfer_token', response.json['data'])
        self.assertNotEqual(new_access_token_1, new_access_token_2)

        # first access token is non-workable
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, new_access_token_1),
                                       {"data": {"status": "active"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        # second access token is workable
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, new_access_token_2),
                                       {"data": {"tenderPeriod": {"endDate": (now + TENDERING_DURATION).isoformat()}}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['tenderPeriod']['endDate'], (now + TENDERING_DURATION).isoformat())

        # try to change tender credentials with wrong owner
        authorization = self.app.authorization
        self.app.authorization = ('Basic', (self.second_owner, ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        self.assertIn('date', response.json['data'])
        transfer_id_3 = response.json['data']['id']
        new_access_token_3 = response.json['access']['token']
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer_id_3, "tender_token":test_access_token_stage1}}, status = 403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u"Only owner is allowed to generate new credentials.", u'location': u'body', u'name': u'transfer'}])

        # tender not in draft.stage2 status is protected
        self.app.authorization = authorization
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, new_access_token_2),
                                       {"data": {"status": "active.tendering"}})
        self.assertEqual(response.status, '200 OK')
        response = self.app.post_json('/tenders/{}/ownership'.format(self.tender_id),
                                      {"data": {"id": transfer_id_3, "tender_token":test_access_token_stage1}}, status = 403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u"Can't generate credentials in current (active.tendering) tender status", u'location': u'body', u'name': u'data'}])


class OpenEUCompatitiveDialogueStage2TenderOwnershipChangeTest(OpenUACompatitiveDialogueStage2TenderOwnershipChangeTest):
    tender_type = "competitiveDialogueEU.stage2"
    initial_data = test_tender_stage2_data_eu
    first_owner = 'broker'
    second_owner = 'broker3'
    invalid_owner = 'broker1'
    test_owner = 'broker3t'

    def test_change_tender_ownership(self):
        super(OpenEUCompatitiveDialogueStage2TenderOwnershipChangeTest, self).test_change_tender_ownership()


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
    tender_type = "negotiation.quick"
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
