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
    if hasattr(request, 'check_accreditation') and not request.check_accreditation(model.create_accreditation):
        request.errors.add('transfer', 'accreditation', 'Broker Accreditation level does not permit transfer creation')
        request.errors.status = 403
        return
    return validate_data(request, model, data=data)


def validate_ownership_data(request):
    data = validate_json_data(request)

    for field in ['id', 'transfer']:
        if not data.get(field):
            request.errors.add('body', field, 'This field is required.'.format(field))
        if request.errors:
            request.errors.status = 422
            return
    request.validated['ownership_data'] = data
