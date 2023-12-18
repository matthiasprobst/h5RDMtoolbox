Glossary
========


.. glossary::

    metadata
        "Information about data" :cite:t:`michener2006meta` o higher level descriptions of data sets. In HDF5
        files, attributes are used to describe data. Standardized attribute names like **long_name** or
        **standard_name** are special meta data descriptors that follow a specific standard and allow
        automated exploration and analysis.

    convention
        Set of "standard attributes" used to describe data. A convention can be enabled, which will
        automatically add the standard attributes as parameters to the methods like e.g. `create_dataset`.

    standard attributes
        Attributes that are used to describe data. Standard attributes are defined by a convention.
        Standard attributes validate the user input, which is done using the `pydantic` package.

    layout
        Layouts define the structure of an HDF5 file. It may define exact content, e.g. attribute name and value or
        define expected dataset dimensions or shape. It cannot specify the array data of datasets.

    repository
        A repository is a storage place for data, usually online, which assigns a unique identifier to the uploaded
        data. An popular example is Zenodo. Typically, a repository can be queried for metadata such as author,
        title, description, type of data, but not for the content of the data (see database).

    database
        A database hosts data and allows to query the content of the data. Examples for databases in the context
        ofHDF5 is mongoDB.