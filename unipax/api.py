'''
This module implements the Python wrapper around the UniPAX REST API.

'''
################################################################################

import os
import time

import requests

import unipax.graph

################################################################################

DEFAULT_UNIPAX_ROOT_URL = 'http://unipax.informatik.uni-tuebingen.de'
'''
Default root url for the UniPAX REST Service.
'''

################################################################################
 # Define (and make) default temporary data directories #
################################################################################

__unipax_tmp__ = os.path.expanduser('~/.unipax/tmp')

if not os.path.isdir(__unipax_tmp__):
    os.makedirs(__unipax_tmp__)

################################################################################
 # Utility functions #
################################################################################

def time_stamp():
    '''
    Get time stamp, for example for temporary files etc.
    '''
    return time.strftime('%Y%m%d%H%M%S', time.gmtime())

################################################################################
 # Exceptions #
################################################################################

class UniPaxException(Exception):
    pass

################################################################################
################################################################################
 # Core #
################################################################################

################################################################################
 # The API #
################################################################################

class UniPaxRestApi(object):
    '''
    Top-level API class. Contains the REST nodes which again contain REST nodes, etc.
    '''
    def __init__(self, root_url=DEFAULT_UNIPAX_ROOT_URL, tmpdir=__unipax_tmp__):
        if not root_url.startswith('http://'):
            root_url = 'http://'+root_url
        self.root_url = root_url
        self.tmpdir = tmpdir

        self.graph = UniPaxRestGraph(self)
        self.all = UniPaxRestAll(self)
        self.info = UniPaxRestInfo(self)

    @property
    def url(self):
        return self.root_url

################################################################################
 # REST node #
################################################################################

class UniPaxRestNode(object):
    '''
    A REST node.
    '''
    def __init__(self, parent):
        self.parent = parent

    @property
    def tmpdir(self):
        return self.parent.tmpdir

    @property
    def url(self):
        return self.parent.url + self.append

    @property
    def append(self):
        return self._append

################################################################################
 # REST endpoint #
################################################################################

class UniPaxRestEndpoint(UniPaxRestNode):
    '''
    A REST endpoint (something you can query).
    '''
    def __init__(self, parent):
        super().__init__(parent)

    def __call__(self, **params):
        '''
        Endpoints a callable with the query parameters as arguments.
        '''
        return self.query(**params)

    def _query(self, **params):
        '''
        Send GET request to <unipax>/(node/)*/endpoint with query parameters params.

        Returns raw http response.
        '''
        response = requests.get(self.url, params=params)
        if response.status_code != 200:
            raise UniPaxException
        return response

    def raw(self, **params):
        '''
        Returns the raw http response.

        Strictly speaking redundant, see self._query
        '''
        self._query(**params)

    def query(self, **params):
        '''
        Query method. To be implemented by subclasses (ie physical endpoint classes)
        '''
        raise NotImplementedError

    def _return_list_from_query(self, **params):
        '''
        Standard implemetation of queries which return a list of items.

        Meant to be used by subclasses to implement self.query.
        '''
        response = self._query(**params)
        return [item.strip() for item in response.content.decode('utf-8').split('\n') if item]

################################################################################
################################################################################
 # <unipax>/all #
################################################################################

class UniPaxRestAll(UniPaxRestNode):
    '''
    <unipax>/all REST node.
    '''
    def __init__(self, parent):
        super().__init__(parent)
        self._append = '/all'
        self.types = UniPaxRestAllTypes(self)
        all_types = self.types()
        for typ in all_types:
            self.__dict__[typ] = UniPaxRestType(self, typ)

################################################################################
 # <unipax>/all/ #
################################################################################

class UniPaxRestAllTypes(UniPaxRestEndpoint):
    '''
    <unipax>/all/ endpoint.

    Original documentation at <unipax>/help:

        Returns a list of all types.

        Syntax: /all/?filter=(biopax|sbml|none)

        Parameters:
            filter - restrict to BioPAX or SBML objects
    '''
    def __init__(self, parent):
        super().__init__(parent)
        self._append = '/'

    def query(self, **params):
        return self._return_list_from_query(**params)

################################################################################
 # <unipax>/all/<type> #
################################################################################

class UniPaxRestType(UniPaxRestEndpoint):
    '''
    <unipax>/all/<type> endpoint.

    Original documentation at <unipax>/help:

        Returns a list of all objects of the given type.

        Syntax: /all/<type>?format=(biopax|attributes|ids)&recursive=(true|false)&derived=(true|false)&attributes=(<attr>:<attr>:...)

        Parameters:
            format - specifies the output format
            derived - output all objects derived from
            recursive - only if format=biopax, whether or not to output referenced objects
            attributes - only if format=attributes, which attributes to show, separated by ':'.
            Available attributes: type, name/standardName, organism, displayName
    '''
    def __init__(self, parent, name):
        super().__init__(parent)
        self._name = name
        self._append = '/'+name

    def query(self, **params):
        return self._return_list_from_query(**params)

################################################################################
################################################################################
 # <unipax>/info #
################################################################################

class UniPaxRestInfo(UniPaxRestNode):
    '''
    <unipax>/info REST node.
    '''
    def __init__(self, api):
        super().__init__(api)
        self._append = '/info'
        self.xrefdbs = UniPaxRestInfoXRefDBs(self)

################################################################################
 # <unipax>/info/xrefdbs #
################################################################################

class UniPaxRestInfoXRefDBs(UniPaxRestEndpoint):
    '''
    <unipax>/info/xrefdbs endpoint.

    Original documentation at <unipax>/help:

        Returns a list of all databases referenced
    '''
    def __init__(self, node):
        super().__init__(node)
        self._append = '/xrefdbs'

    def query(self):
        return self._return_list_from_query(**params)

################################################################################
################################################################################
 # <unipax>/graph #
################################################################################

class UniPaxRestGraph(UniPaxRestNode):
    '''
    <unipax>/graph REST node.
    '''
    def __init__(self, api):
        super().__init__(api)
        self._append = '/graph'
        self.regulatory = UniPaxRestGraphRegulatory(self)
        self.metabolic = UniPaxRestGraphMetabolic(self)
        self.ppi = UniPaxRestGraphPpi(self)

################################################################################
 # <unipax>/graph/<endpoint> #
################################################################################

class UniPaxRestGraphEndpoint(UniPaxRestEndpoint):
    '''
    Base class for <unipax>/graph endpoints.
    '''
    def __init__(self, node):
        super().__init__(node)

    def query(self, **params):
        tmpfile = self.tmpdir+'unipax_tmp_'+time_stamp()+'.'+params.get('format', 'gml')
        self.download(tmpfile, **params)
        if not 'format' in params or params['format'] == 'gml':
            graph = unipax.graph.read_gml(tmpfile)
        elif params['format'] == 'graphml':
            graph = unipax.graph.read_graphml(tmpfile)
        elif params['format'] == 'lemon':
            graph = unipax.graph.read_lemon(tmpfile)
        elif params['format'] == 'sif':
            graph = unipax.graph.read_sif(tmpfile)
        os.remove(tmpfile)
        return graph

    def download(self, path, **params):
        response = self._query(**params)
        with open(path, 'wb') as downloaded_file:
            downloaded_file.write( response.content )

################################################################################
 # <unipax>/graph/regulatory #
################################################################################

class UniPaxRestGraphRegulatory(UniPaxRestGraphEndpoint):
    '''
    <unipax>/graph/regulatory endpoint.

    Original documentation at <unipax>/help:

        Returns a regulatory network.

        Syntax: /graph/regulatory?<parameters>

        Parameters:
            format - specifies the output format (gml | sif | lemon | gmx | graphml)
            nodelabel - assign node labels (xref!<dbname> | type | name)
            edgelabel - assign edge labels (xref!<dbname> | type | relation)
            result - id of a result object from which to construct the network
            filter - filter the network by (pathway!<id> | organism!<id> | nodetype!<type> | edgetype!<type>)(,<more filter>)*

    '''
    def __init__(self, node):
        super().__init__(node)
        self._append = '/regulatory'

################################################################################
 # <unipax>/graph/metabolic #
################################################################################

class UniPaxRestGraphMetabolic(UniPaxRestGraphEndpoint):
    '''
    <unipax>/graph/metabolic endpoint.

    Original documentation at <unipax>/help:

        Returns a metabolic network.

        Syntax: /graph/metabolic?<parameters>

        Parameters:
            format - specifies the output format (gml | sif | lemon | gmx | graphml)
            nodelabel - assign node labels (xref!<dbname> | type | name)
            edgelabel - assign edge labels (xref!<dbname> | type | relation)
            result - id of a result object from which to construct the network
            filter - filter the network by (pathway!<id> | organism!<id> | nodetype!<type> | edgetype!<type>)(,<more filter>)*
    '''
    def __init__(self, node):
        super().__init__(node)
        self._append = '/metabolic'

################################################################################
 # <unipax>/graph/ppi #
################################################################################

class UniPaxRestGraphPpi(UniPaxRestGraphEndpoint):
    '''
    <unipax>/graph/ppi endpoint.

    Original documentation at <unipax>/help:

        Returns a protein-protein interaction network.

        Syntax: /graph/ppi?<parameters>

        Parameters:
            format - specifies the output format (gml | sif | lemon | gmx | graphml)
            nodelabel - assign node labels (xref!<dbname> | type | name | data)
            edgelabel - assign edge labels (xref!<dbname> | type | relation)
            result - id of a result object from which to construct the network
            filter - filter the network by (pathway!<id> | organism!<id> | nodetype!<type> | edgetype!<type>)(,<more filter>)*
    '''
    def __init__(self, node):
        super().__init__(node)
        self._append = '/ppi'
