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
    validate_ownership_data, validate_tender_accreditation_level
)


@opresource(name='Tender ownership',
            path='/tenders/{tender_id}/ownership',
            description="Tenders Ownership")
class TenderResource(APIResource):

    @json_view(permission='create_tender',
               validators=(validate_tender_accreditation_level,
                           validate_ownership_data,))
    def post(self):
        tender = self.request.validated['tender']
        data = self.request.validated['ownership_data']

        if tender.transfer_token == sha512(data['transfer']).hexdigest():
            transfer_id = data['id']
            transfer = extract_transfer(self.request, transfer_id=transfer_id)
            update_ownership(tender, transfer)
            self.request.validated['tender'] = tender
        else:
            self.request.errors.add('body', 'transfer', 'Invalid transfer')
            self.request.errors.status = 403
            return

        location = self.request.route_path('Tender', tender_id=tender.id)
        location = location[len(ROUTE_PREFIX):]  # strips /api/<version>
        transfer.usedFor = location
        self.request.validated['transfer'] = transfer
        if save_transfer(self.request):
            self.LOGGER.info('Updated transfer relation {}'.format(transfer.id),
                             extra=context_unpack(self.request, {'MESSAGE_ID': 'transfer_relation_update'}))

            if save_tender(self.request):
                self.LOGGER.info('Updated ownership of tender {}'.format(tender.id),
                                extra=context_unpack(self.request, {'MESSAGE_ID': 'tender_ownership_update'}))

                return {'data': tender.serialize('view')}
