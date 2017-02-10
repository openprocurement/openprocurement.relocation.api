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
    validate_ownership_data, validate_tender_accreditation_level, validate_set_or_change_ownership_data
)


@opresource(name='Tender ownership',
            path='/tenders/{tender_id}/ownership',
            description="Tenders Ownership")
class TenderResource(APIResource):

    @json_view(permission='create_tender',
               validators=(validate_tender_accreditation_level,
                           validate_set_or_change_ownership_data,))
    def post(self):
        tender = self.request.validated['tender']
        data = self.request.validated['ownership_data']
        token = getattr(tender, 'dialogue_token', 'token')
        # TODO think about restricting ownership change in curtain statuses
        if data.get('tender_token') and tender.status != "draft.stage2":
            self.request.errors.add('body', 'data', 
                                    'Can\'t generate credentials in current ({}) tender status'.format(
                                        tender.status))
            self.request.errors.status = 403
            return

        if tender.transfer_token == sha512(data.get('transfer','')).hexdigest() or token == sha512(data.get('tender_token', '')).hexdigest():

            transfer = extract_transfer(self.request, transfer_id=data['id'])
            if data.get('tender_token') and tender.owner != transfer.owner:
                self.request.errors.add('body', 'transfer', 'Only owner is allowed to generate new credentials.')
                self.request.errors.status = 403
                return

            location = self.request.route_path('Tender', tender_id=tender.id)
            location = location[len(ROUTE_PREFIX):]  # strips /api/<version>
            if transfer.get('usedFor') and transfer.get('usedFor') != location:
                self.request.errors.add('body', 'transfer', 'Transfer already used')
                self.request.errors.status = 403
                return
        else:
            self.request.errors.add('body', 'transfer', 'Invalid transfer or tender token')
            self.request.errors.status = 403
            return

        update_ownership(tender, transfer)
        self.request.validated['tender'] = tender

        transfer.usedFor = location
        self.request.validated['transfer'] = transfer
        if save_transfer(self.request):
            self.LOGGER.info('Updated transfer relation {}'.format(transfer.id),
                             extra=context_unpack(self.request, {'MESSAGE_ID': 'transfer_relation_update'}))

            if save_tender(self.request):
                self.LOGGER.info('Updated ownership of tender {}'.format(tender.id),
                                extra=context_unpack(self.request, {'MESSAGE_ID': 'tender_ownership_update'}))

                return {'data': tender.serialize('view')}
