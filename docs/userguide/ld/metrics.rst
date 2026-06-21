.. _ld_metrics:

Graph Metrics
=============

The web viewer exposes RDF knowledge-graph metrics for each file and for the
combined graph. Metrics include graph size, predicate and class usage,
connectivity, datatype distribution, label coverage, and external namespace
usage.

Combined metrics skip exact largest-distance computation for large resource
networks and show this explicitly on the metrics page.

The same metrics are available from Python:

.. code-block:: python

   import h5rdmtoolbox as h5tbx

   metrics = h5tbx.compute_metrics("example.h5")

   with h5tbx.File("example.h5") as h5:
       metrics = h5.metrics()
