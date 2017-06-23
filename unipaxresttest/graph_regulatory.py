import os
import itertools
import unittest

import unipax.api

class RegulatoryGraphFormatConsistency(unittest.TestCase):

    formats = ['gml', 'sif', 'graphml']          # lemon reader not implemented yet; (TODO: formats = unipax.api.UniPaxRestApi.graphs.regulatory.formats)

    def setUp(self):
        self.graphs = {}
        api = unipax.api.UniPaxRestApi()
        for frmt in self.formats:
            self.graphs[frmt] = api.graph.regulatory(format=frmt)

    def test_equal_number_of_nodes(self):
        for format1, format2 in itertools.combinations(self.formats, 2):
            self.assertEqual(len(self.graphs[format1].vs), len(self.graphs[format2].vs),
                             'unequal number of nodes: {} {}'.format(format1, format2))

    def test_equal_number_of_edges(self):
        for format1, format2 in itertools.combinations(self.formats, 2):
            self.assertEqual(len(self.graphs[format1].es), len(self.graphs[format2].es),
                             'unequal number of edges: {} {}'.format(format1, format2))
