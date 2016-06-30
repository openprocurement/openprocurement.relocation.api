.. _tutorial:

Tutorial
========

Tender creation
---------------

Let's create a tender:

.. include:: tutorial/create-tender.http
   :code:


Take a look at response `access` section. There is a `transfer` value which is used to change tender ownership.


Transfer creation
-----------------

Create new Transfer object:

.. include:: tutorial/create-transfer.http
   :code:


Changing tender ownership
-------------------------

To change tender ownership you should to send POST request with `transfer.id` and `tender.transfer` in request data:

.. include:: tutorial/change-tender-ownership.http
   :code:
