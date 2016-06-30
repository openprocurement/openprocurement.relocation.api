.. _tutorial:

Tutorial
========

Tender creation
---------------

At first let's create a tender:

.. include:: tutorial/create-tender.http
   :code:

Take a look at response `access` section. There is a `transfer` value which is used to change tender ownership.

Notice that `broker` is a tender owner.


Transfer creation
-----------------

Broker which is going to take tender ownership should create a Transfer.

.. include:: tutorial/create-transfer.http
   :code:

Transfer object contains new access ``token``, and new ``transfer`` to the object on which it will be applied.

Changing tender ownership
-------------------------

To change tender ownership you should send POST request with data containing `id` of Transfer and `transfer` token got from tender owner:

.. include:: tutorial/change-tender-ownership.http
   :code:

Updated ``owner`` value indicates that ownership is successfully applied.

Let's try to change the tender using `token` got on transfer creation:

.. include:: tutorial/modify-tender.http
   :code:
