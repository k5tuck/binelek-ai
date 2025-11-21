Binah AIP API Documentation
============================

Welcome to the Binah AIP (AI Processing) Service API documentation.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api/index
   modules

Overview
--------

The Binah AIP service provides AI processing capabilities for the Binelek platform,
including autonomous ontology generation, LLM integration, and agent-based processing.

Key Features
~~~~~~~~~~~~

* **Autonomous Ontology Generation** - AI-powered ontology creation
* **LLM Provider Abstraction** - Support for multiple LLM providers (OpenAI, Anthropic, Azure)
* **Agent-Based Processing** - Multi-agent system for complex tasks
* **FastAPI Framework** - Modern async Python web framework
* **Multi-tenant Support** - Isolated AI processing per tenant
* **Kafka Integration** - Event-driven architecture

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
* **PostgreSQL** - Metadata storage
* **Redis** - Caching layer

API Reference
-------------

See :doc:`api/index` for detailed API documentation.
