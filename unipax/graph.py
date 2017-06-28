'''
Graph utilites for UniPAX graph queries.

'''

import re

import igraph as ig

def read_graphml(path):
    '''
    GraphML (Graph Markup Language) Reader.

    http://graphml.graphdrawing.org/

    https://en.wikipedia.org/wiki/GraphML

    Args:

        path (str) : Path of GraphML file

    Returns:

        ig.Graph : Graph encoded in the GraphML file (hopefully;)
    '''
    return ig.Graph.Read_GraphML(path)

def read_lemon(path):
    '''
    Lemon (LGF, Lemon Graph Format) Reader.

    http://lemon.cs.elte.hu/pub/doc/1.2.3/a00002.html

    http://lemon.cs.elte.hu/pub/tutorial/a00018.html

    Args:

        path (str) : Path of LGF file

    Returns:

        ig.Graph : Graph encoded in the LGF file (hopefully;)
    '''
    # TODO
    pass

def read_gml(path):
    '''
    GML (Graph Modelling Language) Reader.

    https://en.wikipedia.org/wiki/Graph_Modelling_Language

    Args:

        path (str) : Path of GML file

    Returns:

        ig.Graph : Graph encoded in the GML file (hopefully;)
    '''
    return ig.Graph.Read_GML(path)

def read_sif(path, directed=True):
    '''
    SIF (Simple Interaction Format) Reader.

    http://wiki.cytoscape.org/Cytoscape_User_Manual/Network_Formats

    Args:

        path (str) : Path of sif file
        directed (bool) : Whether to interpret the graph as directed

    Returns:

        ig.Graph : Graph encoded in the SIF file (hopefully;)
    '''
    nodes = set()
    edges = list()
    interactions = list()
    with open(path, 'r') as sif:
        for line in sif:
            items = [item.strip() for item in re.split('\s+', line) if item]
            if len(items) == 1:    # isolated nodes
                nodes.add(source)
                continue
            source, interaction, targets = items[0], items[1], items[2:]
            nodes.add(source)
            nodes |= {target for target in targets}
            edges.extend([(source, target) for target in targets])
            interactions.extend( len(targets) * [interaction] )
    nodes = list(nodes)
    node2index = { node : nodes.index(node) for node in nodes }
    edges = [(node2index[edge[0]], node2index[edge[1]]) for edge in edges]
    graph = ig.Graph(directed=directed)
    graph.add_vertices(len(nodes))
    graph.vs['name'] = nodes
    graph.add_edges(edges)
    graph.es['interaction'] = interactions
    return graph
