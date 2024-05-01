import numpy as np
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import File
from h5rdmtoolbox import _repr
from h5rdmtoolbox._repr import process_string_for_link
# noinspection PyUnresolvedReferences
from h5rdmtoolbox.database import mongo


class TestRepr(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_hide_uri(self):
        with h5tbx.File() as h5:
            h5.attrs['orcid', 'https://example.ord/hasOrcid'] = h5tbx.__author_orcid__

            ssr = _repr.HDF5StructureStrRepr()
            ssr(h5)

            s = ssr.__attrs__('orcid', h5['/'])
            self.assertEqual(
                s,
                '\x1b[3ma: orcid (p=https://example.ord/hasOrcid)\x1b[0m: https://orcid.org/0000-0001-8729-0482'
            )

            ssr = _repr.HDF5StructureStrRepr(hide_uri=True)
            ssr(h5)
            self.assertEqual(
                ssr.__attrs__('orcid', h5['/']),
                '\x1b[3ma: orcid (p=https://example.ord/hasOrcid)\x1b[0m: https://orcid.org/0000-0001-8729-0482'
            )

            def test_process_string_for_link(self):
                string_without_url = "This is a string without a web URL"
                processed_string, has_url = process_string_for_link(string_without_url)
                self.assertFalse(has_url)
                self.assertEqual(processed_string, string_without_url)

                zenodo_url = 'https://zenodo.org/record/10428822'
                img_url = f'https://zenodo.org/badge/DOI/10.5281/zenodo.10428822.svg'
                self.assertEqual(f'<a href="{zenodo_url}"><img src="{img_url}" alt="DOI"></a>',
                                 process_string_for_link(zenodo_url)[0])

                zenodo_url = 'https://doi.org/10.5281/zenodo.10428822'
                img_url = f'https://zenodo.org/badge/DOI/10.5281/zenodo.10428822.svg'
                self.assertEqual(f'<a href="{zenodo_url}"><img src="{img_url}" alt="DOI"></a>',
                                 process_string_for_link('10.5281/zenodo.10428822')[0])

                string_with_url = "This is a string with a web URL: https://www.example.com which goes on and on and on"
                string_with_href = 'This is a string with a web URL: ' \
                                   '<a href="https://www.example.com">https://www.example.com</a> which goes on and on and on'
                processed_string, has_url = process_string_for_link(string_with_url)
                self.assertTrue(has_url)
                self.assertEqual(processed_string, string_with_href)

        def test_dump_orcid(self):
            # with File() as h5:
            #     h5.attrs['orcid'] = h5tbx.__author_orcid__
            #     h5.dump()
            with File() as h5:
                h5.attrs['orcid'] = [h5tbx.__author_orcid__, h5tbx.__author_orcid__, ]
                h5.dump()

        def test_repr_def(self):
            with File() as h5:
                h5.attrs['orcid'] = h5tbx.__author_orcid__
                h5.rdf['orcid'].definition = 'https://example.com/hasOrcid'

                ssr = _repr.HDF5StructureStrRepr()
                ssr(h5)

                s = ssr.__attrs__('orcid', h5['/'])
                self.assertEqual(
                    s,
                    '\x1b[3ma: orcid (def=https://example.com/hasOrcid)\x1b[0m: https://orcid.org/0000-0001-8729-0482')

        def test_repr(self):
            with File(h5tbx.utils.generate_temporary_filename(), 'w') as h5:
                h5.create_dataset('ds', data=3, dtype='int64')
                h5.create_dataset('dsfloat', data=3.0, dtype='float64')
                h5.create_dataset('str', data='str')
                h5.create_dataset('bool', data=True)
                h5.create_dataset('arr',
                                  data=np.random.random((4, 5, 3)),
                                  chunks=(4, 5, 1),
                                  maxshape=(4, 5, 3))

                ssr = _repr.HDF5StructureStrRepr()
                ssr(h5, preamble='My preamble')

                self.assertEqual(ssr.__0Ddataset__('ds0', h5['str']),
                                 '\x1b[1mds0\x1b[0m ?type?, dtype: |S3')

                s = ssr.__dataset__('ds', h5['ds'])
                self.assertEqual(s, '\x1b[1mds\x1b[0m 3, dtype: int64')

                s = ssr.__0Ddataset__('dsbool', h5['bool'])
                self.assertEqual(s, '\x1b[1mdsbool\x1b[0m True, dtype: bool')

                s = ssr.__dataset__('dsfloat', h5['dsfloat'])
                self.assertEqual(s, '\x1b[1mdsfloat\x1b[0m 3.000000, dtype: float64')

                s = ssr.__dataset__('str', h5['str'])
                self.assertEqual(s, "\x1b[1mstr\x1b[0m: b'str'")

                shr = _repr.HDF5StructureHTMLRepr()
                shr(h5)

                shr.__dataset__('ds', h5['ds'])
                shr.__dataset__('dsfloat', h5['dsfloat'])
