Repository
==========

As part of the `h5rdmtoolbox` a repository is understood as an (online) storage place for data.
It assigns a unique identifier to the data deposit and provides a way to retrieve the data set by its identifier.
The `repository` module provides interfaces to different repositories. An abstract class `RepositoryInterface` is
implemented. It defines the methods that a repository interface has to implement. Currently, only the Zenodo repository
interface is implemented. It is a popular choice among scientists. Please feel free to contribute other repository
interfaces.


.. toctree::
    :titlesonly:
    :glob:

    zenodo.ipynb