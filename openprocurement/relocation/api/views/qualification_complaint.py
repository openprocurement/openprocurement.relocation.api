# -*- coding: utf-8 -*-
from hashlib import sha512
from openprocurement.api.utils import (
    json_view,
    APIResource,
    save_tender,
    ROUTE_PREFIX,
    context_unpack
)
from openprocurement.tender.openeu.utils import qualifications_resource
from openprocurement.relocation.api.utils import (
    extract_transfer, update_ownership, save_transfer
)
from openprocurement.relocation.api.validation import (
    validate_ownership_data, validate_complaint_accreditation_level
)


@qualifications_resource(name='Qualification complaint ownership',
            path='/tenders/{tender_id}/qualifications/{qualification_id}/complaints/{complaint_id}/ownership',
            description="Qualification complaint Ownership")
class QualificationComplaintOwnershipResource(APIResource):

    @json_view(permission='create_complaint',
        validators=(validate_complaint_accreditation_level,
                           validate_ownership_data,))
    def post(self):
        complaint = self.request.context
        tender = self.request.validated['tender']
        award_id = self.request.validated['qualification_id']
        qualification_id = self.request.validated['qualification_id']
        data = self.request.validated['ownership_data']
        
        if complaint.transfer_token == sha512(data['transfer']).hexdigest():
            location = self.request.route_path('Tender EU Qualification Complaints', tender_id=tender.id, qualification_id=qualification_id, complaint_id=complaint.id)
            location = location[len(ROUTE_PREFIX):]  # strips /api/<version>
            transfer = extract_transfer(self.request, transfer_id=data['id'])
            if transfer.get('usedFor') and transfer.get('usedFor') != location:
                self.request.errors.add('body', 'transfer', 'Transfer already used')
                self.request.errors.status = 403
                return
        else:
            self.request.errors.add('body', 'transfer', 'Invalid transfer')
            self.request.errors.status = 403
            return

        update_ownership(complaint, transfer)

        transfer.usedFor = location
        self.request.validated['transfer'] = transfer
        if save_transfer(self.request):
            self.LOGGER.info('Updated transfer relation {}'.format(transfer.id),
                             extra=context_unpack(self.request, {'MESSAGE_ID': 'transfer_relation_update'}))

            if save_tender(self.request):
                self.LOGGER.info('Updated qualification {} complaint {} ownership of tender {}'.format(complaint.id, qualification_id, tender.id),
                                 extra=context_unpack(self.request, {'MESSAGE_ID': 'qualification_complaint_ownership_update'}, {'complaint_id': complaint.id, 'qualification_id': qualification_id, 'tender_id': tender.id}))

                return {'data': complaint.serialize('view')}
        
