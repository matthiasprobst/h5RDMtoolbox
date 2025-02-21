import ssnolib.ssno.standard_name
from ontolutils.namespacelib import M4I
from ontolutils.namespacelib import SCHEMA
from ssnolib import SSNO

from h5rdmtoolbox.wrapper.ld.hdf.file import get_ld as hdf_get_ld
from h5rdmtoolbox.wrapper.ld.user.attributes import process_attribute
from h5rdmtoolbox.wrapper.ld.user.file import get_ld as user_get_ld
from h5rdmtoolbox.wrapper.ld.user.groups import process_group
from h5rdmtoolbox.wrapper.ld.utils import optimize_context

if __name__ == "__main__":
    import h5rdmtoolbox as h5tbx

    with h5tbx.File() as h5:
        grp = h5.create_group("h5rdmtoolbox")
        grp.rdf.type = SCHEMA.SoftwareSourceCode
        grp.attrs["version", SCHEMA.version] = "1.2.3"

        ds = h5.create_dataset("a/b/ds", data=[[1, 2], [3, 4]],
                               chunks=(1, 2), compression="gzip", compression_opts=2)
        ds2 = h5.create_dataset("nochunk", data=[[1, 2], [3, 4]], chunks=None)
        ds.rdf.type = M4I.NumericalVariable
        ds.attrs["standard_name", SSNO.hasStandardName] = "x_velocity"
        ds.rdf["standard_name"].object = ssnolib.ssno.standard_name.StandardName(id="_:123",
                                                                                 standardName="x_velocity",
                                                                                 unit="m/s")

    graph1 = user_get_ld(str(h5.hdf_filename))
    graph2 = hdf_get_ld(str(h5.hdf_filename))

    graph1.bind("ssno", str(SSNO))
    graph1.bind("m4i", str(M4I))

    combined_graph = graph2 + graph1
    context = optimize_context(combined_graph, context={"ssno": str(SSNO), "m4i": str(M4I)})
    print(combined_graph.serialize(format="ttl", indent=2, auto_compact=True,
                                   context=context))

    # print(graph2.serialize(format="ttl", indent=2, auto_compact=True,
    #                                context=context))
    # print(graph1.serialize(format="ttl", indent=2, auto_compact=True,
    #                                context=context))
    # print(combined_graph.serialize(format="ttl", indent=2, auto_compact=True,
    #                                context=context))
    # print(combined_graph.serialize(format="json-ld", indent=2, auto_compact=True,
    #                                context=context))
