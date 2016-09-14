.. _tutorial:

Tutorial
========

When customer needs to change current broker this customer should provide new preferred broker with ``transfer`` key for an object (tender, bid, complaint, etc.). Then new broker should create `Transfer` object and send request with `Transfer` ``id`` and ``transfer`` key (received from customer) in order to change object's owner.

Tender ownership change
-----------------------

Let's view transfer example for tender.


Tender creation
~~~~~~~~~~~~~~~

At first let's create a tender:

.. include:: tutorial/create-tender.http
   :code:

`broker` is current tender's ``owner``.

Note that response's `access` section contains a ``transfer`` key which is used to change tender ownership. 

After tender's registration in CDB broker has to provide its customer with ``transfer`` key.

Transfer creation
~~~~~~~~~~~~~~~~~

Broker that is going to become new tender owner should create a `Transfer`.

.. include:: tutorial/create-transfer.http
   :code:

`Transfer` object contains new access ``token`` and new ``transfer`` token for the object that will be transferred to new broker.

`Transfer` can be retrieved by `id`:

.. include:: tutorial/get-transfer.http
   :code:

Changing tender's owner
~~~~~~~~~~~~~~~~~~~~~~~

Pay attention that only broker with appropriate accreditation level can become new owner. Otherwise broker will be forbidden from this action.

To change tender's ownership new broker should send POST request to appropriate `/tenders/id/` with `data` section containing ``id`` of `Transfer` and ``transfer`` token received from customer:

.. include:: tutorial/change-tender-ownership.http
   :code:

Updated ``owner`` value indicates that ownership is successfully changed. 

Note that new broker has to provide its customer with new ``transfer`` key (generated in `Transfer` object).

After `Transfer` is applied it stores tender path in ``usedFor`` property:

.. include:: tutorial/get-used-transfer.http
   :code:

'Used' `Transfer` can't be applied to any other object.

Let's try to change the tender using ``token`` received on `Transfer` creation:

.. include:: tutorial/modify-tender.http
   :code:
   

Bid ownership change
--------------------

Let's submit a bid via current broker:

.. include:: tutorial/create-bid.http
   :code:

Response contains `access` section with a ``transfer`` key that can be used to change bid ownership.

Current broker has to provide its customer with ``transfer`` key for the bid. Then customer can pass it to new broker.
   
Transfer creation
~~~~~~~~~~~~~~~~~

Note that each `Transfer` can be applied only once. New broker (that is going to become new bid owner) should create separate `Transfer` for each owner change:

.. include:: tutorial/create-bid-transfer.http
   :code:

`Transfer` object contains new access ``token`` and new ``transfer`` key for the object that will be transferred to new broker.
   
Changing bid's owner
~~~~~~~~~~~~~~~~~~~~

Pay attention that only broker with appropriate accreditation level can become new owner. Otherwise broker will be forbidden from this action.

New broker should send POST request to appropriate `/tenders/id/bids/id` with `data` section containing ``id`` of `Transfer` and ``transfer`` key for the bid received from customer:

.. include:: tutorial/change-bid-ownership.http
   :code:

Now new broker became bid owner. Check whether new owner is able to change the bid:

.. include:: tutorial/modify-bid.http
   :code:
   
New broker should provide its customer with new ``transfer`` key (received within `Transfer` object).

Check whether `Transfer` object has successfuly stored bid path in ``usedFor`` property:

.. include:: tutorial/get-used-bid-transfer.http
   :code:

Contracting ownership change
----------------------------

Let's view transfer example for  contracting transfer.

Transfer creation 
~~~~~~~~~~~~~~~~~

At the first you must know the contract id which you want to transfer

Broker that is going to become new contract owner should create a `Transfer`.

.. include:: tutorial/create-contract-transfer.http
   :code:

`Transfer` object contains new access ``token`` and new ``transfer`` token for the object that will be transferred to new broker.

Changing contract's owner
~~~~~~~~~~~~~~~~~~~~~~~~~

To change contract's ownership new broker should send POST request to appropriate `/contracts/id/` with `data` section containing ``id`` of `Transfer` and ``transfer`` token received from customer:

.. include:: tutorial/change-contract-ownership.http
   :code:

Updated ``owner`` value indicates that ownership is successfully changed. 

Note that new broker has to provide its customer with new ``transfer`` key (generated in `Transfer` object).

After `Transfer` is applied it stores contract path in ``usedFor`` property:

.. include:: tutorial/get-used-contract-transfer.http
   :code:

Let's try to change the contract using ``token`` received on `Transfer` creation:

.. include:: tutorial/modify-contract.http
   :code:

   
Complaint ownership change
--------------------------

Comming soon
