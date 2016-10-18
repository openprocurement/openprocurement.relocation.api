# -*- coding: utf-8 -*-
import unittest

from openprocurement.relocation.api.tests.base import OwnershipWebTest, OpenUAOwnershipWebTest, OpenEUOwnershipWebTest
from openprocurement.relocation.api.tests.base import test_uadefense_tender_data, test_eu_tender_data, test_transfer_data
from openprocurement.relocation.api.tests.base import test_eu_bid_data, test_organization, complaint



class OpenEUQualificationComplaintOwnershipChangeTest(OpenEUOwnershipWebTest):
    tender_type = "aboveThresholdEU"
    initial_data = test_eu_tender_data
    initial_bid = test_eu_bid_data
    first_owner = 'broker'
    second_provider = 'broker4'
        
    def test_change_qualification_complaint_ownership(self):

        self.set_tendering_status()

        #broker(tender owner)create bid 
        response = self.app.post_json('/tenders/{}/bids'.format(
            self.tender_id), self.initial_bid)
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        bid1_id =   response.json['data']['id']
        bid1_token = response.json['access']['token']
        
        #broker4 create bid
        auth = self.app.authorization
        self.app.authorization = ('Basic', (self.second_provider, ''))
        response = self.app.post_json('/tenders/{}/bids'.format(
            self.tender_id), self.initial_bid)
        bid2_id =   response.json['data']['id']
        bid2_token =  response.json['access']['token']

        #broker change status to pre-qualification  
        self.set_pre_qualification_status()

        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {"data": {"id": self.tender_id}})
        self.app.authorization = auth
    
        #qualifications
        response = self.app.get('/tenders/{}/qualifications'.format(self.tender_id))
        self.assertEqual(response.status, "200 OK")
        qualifications = response.json['data']

        for qualification in qualifications:
            response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(self.tender_id, qualification['id'], self.tender_token),
                                           {"data": {"status": "active", "qualified": True, "eligible": True}})
            self.assertEqual(response.status, "200 OK")

        # active.pre-qualification.stand-still
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
                                       {"data": {"status": "active.pre-qualification.stand-still"}})
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(response.json['data']['status'], "active.pre-qualification.stand-still")

        qualification_id = qualifications[0]['id']

        # broker4 create complaint
        self.app.authorization = ('Basic', (self.second_provider, ''))
        response = self.app.post_json('/tenders/{}/qualifications/{}/complaints?acc_token={}'.format(self.tender_id, qualification_id, bid2_token), complaint)
        self.assertEqual(response.status, '201 Created')
        complaints = response.json["data"]
        complaint_transfer = response.json['access']['transfer']
        print complaint_transfer
          
        # check complaint owner
        tender_doc = self.db.get(self.tender_id)
        self.assertEqual(tender_doc['qualifications'][0]['complaints'][0]['owner'], self.second_provider)

        # broker4 create Transfer
        self.app.authorization = ('Basic', (self.second_provider, ''))
        response = self.app.post_json('/transfers', {"data": test_transfer_data})
        self.assertEqual(response.status, '201 Created')
        transfer = response.json['data']
        transfer_tokens = response.json['access']

        # try to change ownership with invalid transfer token
        response = self.app.post_json('/tenders/{}/qualifications/{}/complaints/{}/ownership'.format(self.tender_id, qualification_id, complaints['id']),
                                      {"data": {"id": transfer['id'], 'transfer': "fake_transfer_token"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Invalid transfer', u'location': u'body', u'name': u'transfer'}
        ])

        # change complaint ownership
        response = self.app.post_json('/tenders/{}/qualifications/{}/complaints/{}/ownership'.format(self.tender_id, qualification_id, complaints['id']), 
                                       {"data": {"id": transfer['id'], 'transfer': complaint_transfer}})
        self.assertEqual(response.status, '200 OK')
        complaint_transfer = transfer_tokens['transfer']
        
        # check complaint owner
        tender_doc = self.db.get(self.tender_id)
        self.assertEqual(tender_doc['qualifications'][0]['complaints'][0]['owner'], self.second_provider)

        # try to use already applied transfer
        self.app.authorization = ('Basic', (self.first_owner, ''))

        response = self.app.post_json('/tenders/{}/qualifications/{}/complaints?acc_token={}'.format(self.tender_id, qualification_id, bid1_token), complaint)
        self.assertEqual(response.status, '201 Created')
        complaints = response.json["data"]
        complaint_transfer = response.json['access']['transfer']

        response = self.app.post_json('/tenders/{}/qualifications/{}/complaints/{}/ownership'.format(self.tender_id, qualification_id, complaints['id']), 
                                       {"data": {"id": transfer['id'], 'transfer': complaint_transfer}}, status = 403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Transfer already used', u'location': u'body', u'name': u'transfer'}
        ])
