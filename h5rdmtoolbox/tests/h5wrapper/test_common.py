"""Testing common funcitonality across all wrapper classs"""

import unittest

from h5rdmtoolbox.h5wrapper import H5Base, H5File, H5Flow, H5PIV
from h5rdmtoolbox.h5wrapper.h5base import H5BaseGroup
from h5rdmtoolbox.h5wrapper.h5file import H5Group
from h5rdmtoolbox.h5wrapper.h5flow import H5FlowGroup


class TestCommon(unittest.TestCase):

    def test_create_group(self):
        """testing the creation of groups"""
        wrapper_classes = (H5Base, H5File, H5Flow, H5PIV)
        wrapper_grouclasses = (H5BaseGroup, H5Group, H5FlowGroup, H5FlowGroup)
        for wc, gc in zip(wrapper_classes, wrapper_grouclasses):
            with wc() as h5:
                grp = h5.create_group('testgrp')
                self.assertIsInstance(grp, gc)
