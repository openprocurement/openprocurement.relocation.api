# -*- coding: utf-8 -*-
from openprocurement.api.utils import update_logging_context
from openprocurement.api.validation import validate_json_data, validate_data
from openprocurement.relocation.api.models import Transfer


def validate_transfer_data(request):
    update_logging_context(request, {'transfer_id': '__new__'})
    data = validate_json_data(request)
    if data is None:
        return
    model = Transfer
    return validate_data(request, model, data=data)


def validate_ownership_data(request):
    if request.errors:
        # do not run validation if some errors are already detected
        return
    data = validate_json_data(request)

    for field in ['id', 'transfer']:
        if not data.get(field):
            request.errors.add('body', field, 'This field is required.'.format(field))
    if request.errors:
        request.errors.status = 422
        return
    request.validated['ownership_data'] = data


def validate_accreditation_level(request, tender, level_name):
    level = getattr(type(tender), level_name)
    if not request.check_accreditation(level):
        request.errors.add('procurementMethodType', 'accreditation', 'Broker Accreditation level does not permit ownership activation')
        request.errors.status = 403
        return

    if tender.get('mode', None) is None and request.check_accreditation('t'):
        request.errors.add('procurementMethodType', 'mode', 'Broker Accreditation level does not permit ownership activation')
        request.errors.status = 403
        return


def validate_tender_accreditation_level(request):
    tender = request.validated['tender']
    model = type(tender)
    if not request.check_accreditation(model.edit_accreditation):
        request.errors.add('procurementMethodType', 'accreditation', 'Broker Accreditation level does not permit ownership activation')
        request.errors.status = 403
        return

    if tender.get('mode', None) is None and request.check_accreditation('t'):
        request.errors.add('procurementMethodType', 'mode', 'Broker Accreditation level does not permit ownership activation')
        request.errors.status = 403
        return


def validate_bid_accreditation_level(request):
    validate_accreditation_level(request, request.validated['tender'], 'edit_accreditation')
