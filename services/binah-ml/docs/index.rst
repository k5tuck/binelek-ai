Binah ML API Documentation
==========================

Welcome to the Binah ML (Machine Learning) Service API documentation.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api/index
   modules

Overview
--------

The Binah ML service provides machine learning model training, inference, and
management capabilities for the Binelek platform.

Key Features
~~~~~~~~~~~~

* **Model Training** - Train custom ML models on tenant data
* **Inference API** - Real-time and batch prediction endpoints
* **Model Management** - Version control and deployment
* **FastAPI Framework** - Modern async Python web framework
* **Multi-tenant Support** - Isolated ML models per tenant
* **Kafka Integration** - Event-driven model updates

Quick Links
-----------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Architecture
------------

The service is built with:

* **Python 3.11** - Modern Python runtime
* **FastAPI** - Async web framework
* **Kafka** - Event streaming
* **PostgreSQL** - Model metadata storage
* **Redis** - Caching layer
* **TensorFlow/PyTorch** - ML frameworks

API Reference
-------------

See :doc:`api/index` for detailed API documentation.
