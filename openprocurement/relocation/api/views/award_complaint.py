# -*- coding: utf-8 -*-
from hashlib import sha512
from openprocurement.api.utils import (
    json_view,
    opresource,
    APIResource,
    save_tender,
    ROUTE_PREFIX,
    context_unpack
)
from openprocurement.relocation.api.utils import (
    extract_transfer, update_ownership, save_transfer
)
from openprocurement.relocation.api.validation import (
    validate_ownership_data, validate_complaint_accreditation_level
)


@opresource(name='Award complaint ownership',
            path='/tenders/{tender_id}/awards/{award_id}/complaints/{complaint_id}/ownership',
            description="Award complaint Ownership")
class AwardComplaintOwnershipResource(APIResource):

    @json_view(permission='create_complaint',
               validators=(validate_complaint_accreditation_level,
                           validate_ownership_data,))
    def post(self):
        complaint = self.request.context
        tender = self.request.validated['tender']
        award_id = self.request.validated['award_id']
        data = self.request.validated['ownership_data']

        if complaint.transfer_token == sha512(data['transfer']).hexdigest():
            location = self.request.route_path('Tender Award Complaints', tender_id=tender.id, award_id=award_id, complaint_id=complaint.id)
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
                self.LOGGER.info('Updated award {} complaint {} ownership of tender {}'.format(complaint.id, award_id, tender.id),
                                 extra=context_unpack(self.request, {'MESSAGE_ID': 'award_complaint_ownership_update'}, {'complaint_id': complaint.id, 'award_id': award_id, 'tender_id': tender.id}))

                return {'data': complaint.serialize('view')}
