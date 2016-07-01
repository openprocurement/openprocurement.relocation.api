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
    validate_ownership_data, validate_bid_accreditation_level
)


@opresource(name='Bid ownership',
            path='/tenders/{tender_id}/bids/{bid_id}/ownership',
            description="Bid Ownership")
class BidResource(APIResource):

    @json_view(permission='create_bid',
               validators=(validate_bid_accreditation_level,
                           validate_ownership_data,))
    def post(self):
        bid = self.request.context
        tender = self.request.validated['tender']
        data = self.request.validated['ownership_data']

        if bid.transfer_token == sha512(data['transfer']).hexdigest():
            location = self.request.route_path('Tender Bids', tender_id=tender.id, bid_id=bid.id)
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

        update_ownership(bid, transfer)

        transfer.usedFor = location
        self.request.validated['transfer'] = transfer
        if save_transfer(self.request):
            self.LOGGER.info('Updated transfer relation {}'.format(transfer.id),
                             extra=context_unpack(self.request, {'MESSAGE_ID': 'transfer_relation_update'}))

            if save_tender(self.request):
                self.LOGGER.info('Updated bid {} ownership of tender {}'.format(bid.id, tender.id),
                                 extra=context_unpack(self.request, {'MESSAGE_ID': 'bid_ownership_update'}, {'bid_id': bid.id, 'tender_id': tender.id}))

                return {'data': bid.serialize('view')}
