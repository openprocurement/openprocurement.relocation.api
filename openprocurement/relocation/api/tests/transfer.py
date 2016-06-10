# -*- coding: utf-8 -*-
import unittest

from openprocurement.relocation.api.models import Transfer
from openprocurement.relocation.api.tests.base import BaseWebTest


class TrensferTest(BaseWebTest):

    def test_simple_add_transfer(self):

        data = {"access_token": "1234",
                "transfer_token": "5678",
                "owner": "Chuck Norris"}

        u = Transfer(data)

        assert u.id is None

        u.store(self.db)

        assert u.id is not None

        fromdb = self.db.get(u.id)

        assert u.transfer_token == fromdb['transfer_token']
        assert u.access_token == fromdb['access_token']
        assert u.owner == fromdb['owner']
        assert u.doc_type == "Transfer"

        u.delete_instance(self.db)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TrensferTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
