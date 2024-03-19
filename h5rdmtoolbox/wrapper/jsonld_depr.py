def serialize_depr(grp,
              iri_only=False,
              local=None,
              recursive: bool = True,
              compact: bool = False,
              context: Dict = None
              ) -> Dict:
    """using rdflib graph"""
    if isinstance(grp, (str, pathlib.Path)):
        from .core import File
        with File(grp) as h5:
            return serialize(h5,
                             iri_only,
                             local,
                             recursive=recursive,
                             compact=compact,
                             context=context)

    hasParameter = URIRef('http://w3id.org/nfdi4ing/metadata4ing#hasParameter')

    # global _context
    _context = {'hdf': str(HDF5._NS)}
    context = context or {}
    _context.update(context)  # = context or {}

    def add_node(name, obj):
        node = rdflib.URIRef(_get_id(obj, local=local))
        # node = rdflib.URIRef(f'_:{obj.name}')
        if isinstance(obj, h5py.File):
            g.add(
                (node,
                 RDF.type,
                 HDF5.rootGroup  # this is a root group!
                 )
            )
        else:
            node_type = obj.iri.subject
            if node_type:
                g.add((node, RDF.type, rdflib.URIRef(obj.iri.subject)))
        if isinstance(obj, h5py.Dataset):
            # node is Parameter
            g.add((node, RDF.type, URIRef("http://www.molmod.info/semantics/pims-ii.ttl#Variable")))
            # g.add((node, RDF.type, URIRef("hdf:Dataset")))
            # parent gets "hasParameter"
            # parent_node = f'_:{obj.parent.name}'# _get_id(obj.parent, local)
            parent_node = _get_id(obj.parent, local)
            g.add((parent_node, hasParameter, node))

        for ak, av in obj.attrs.items():
            if not ak.isupper() and not ak.startswith('@'):
                if isinstance(av, (list, tuple)):
                    value = [_get_id_from_attr_value(_av, local) for _av in av]
                else:
                    value = _get_id_from_attr_value(av, local)

                # g.add((node, URIRef(ak), Literal(av)))
                predicate = obj.iri.predicate.get(ak, None)

                # only add if not defined in context:
                if predicate and predicate not in _context:
                    # irikey = str(obj.iri.predicate[ak])
                    if isinstance(value, (list, tuple)):
                        for v in value:
                            g.add((node, URIRef(predicate), v))
                    else:
                        g.add((node, URIRef(predicate), value))

                # context_iri = context.get(ak, None)
                # if context_iri:
                #     g.add((node, URIRef(context_iri), value))

                if predicate is None and not iri_only:
                    g.add((node, URIRef(ak), value))
        # if isinstance(obj, h5py.Group):
        #     for name, sub_obj in obj.items():
        #         add_node(sub_obj, graph)
        # else:
        #     # has parameter
        #     graph.add((node, hasParameter, node))

    g = Graph()

    g.add(
        (URIRef(f'file://{grp.filename}'),
         RDF.type,
         HDF5.File)
    )

    add_node(grp.name, grp)

    if recursive:
        grp.visititems(add_node)

    return g.serialize(
        format='json-ld',
        context=_context,
        compact=compact
    )