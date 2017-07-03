'''
This module implements the Python wrapper around the UniPAX REST API.

'''
################################################################################

import os
import io
import time
import threading
import webbrowser

import requests
import pandas as pd

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
        self.help = UniPaxRestHelp(self)
        self.get = UniPaxRestGet(self)
        self.download = self.get.download
        self.id = UniPaxRestGet(self)    # <unipax>/get & <unipax>/id do the same thing!?
        # self.datasource = UniPaxDatasource(self)

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

    def __call__(self, *args, **params):
        '''
        Endpoints a callable with the query parameters as arguments.
        '''
        return self.query(*args, **params)

    def _get(self, url, *args, **params):
        '''
        Returns raw http response
        '''
        if args: 
            url += '/'
            url += ','.join([arg for arg in args])
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise UniPaxException
        return response

    def get(self, *args, **params):
        '''
        Returns the raw http response.

        '''
        return self._get(self.url, *args, **params)

    def download(self, path, *args, **params):
        response = self.get(*args, **params)
        with open(path, 'wb') as downloaded_file:
            downloaded_file.write( response.content )

    def query(self, *args, **params):
        '''
        Query method. To be implemented by subclasses (ie physical endpoint classes)
        '''
        raise self.get(*args, **params).content

    def _return_list_from_query(self, *args, **params):
        '''
        Standard implemetation of queries which return a list of items.

        Meant to be used by subclasses to overwrite self.query.
        '''
        response = self.get(*args, **params)
        return [item.strip() for item in response.content.decode('utf-8').split('\n') if item]

################################################################################
################################################################################
 # <unipax>/help #
################################################################################

class UniPaxRestHelp(UniPaxRestEndpoint):
    _append = '/help'

    def query(self, tab=True):
        new = 2 if tab else 1
        thread = threading.Thread(target=lambda: webbrowser.open(self.url, new))
        thread.start()


################################################################################
################################################################################
 # <unipax>/get #
################################################################################

class UniPaxRestGet(UniPaxRestEndpoint):
    '''
    <unipax>/get REST endpoint.

    Original documentation at <unipax>/help:

        Returns one or more objects from the database.

        Syntax: /get/<unipaxId>,<unipaxId>,...?format=(biopax|graphml|gmx|gmt)&recursive=(true|false)

        Parameters:
            format - specifies the output format (for more than one unipaxId gmx format is changed into gmt format)
            recursive - only if format=biopax, whether or not to output referenced objects
    '''

    _append = '/get'

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
    _append = '/'

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
        format_ = params.get('format', 'ids')
        if format_ == 'ids':
            return self._return_list_from_query(**params)
        elif format_ == 'biopax':
            return self.get(**params).content
        elif format_ == 'attributes':
            response = self.get(**params)
            data = io.StringIO(response.content.decode('utf-8'))
            return pd.read_table(data, header=0)

################################################################################
################################################################################
 # <unipax>/info #
################################################################################

class UniPaxRestInfo(UniPaxRestNode):
    '''
    <unipax>/info REST node.
    '''
    _append = '/info'

    def __init__(self, parent):
        super().__init__(parent)
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
    _append = '/xrefdbs'

    def query(self):
        return self._return_list_from_query()

################################################################################
################################################################################
 # <unipax>/graph #
################################################################################

class UniPaxRestGraph(UniPaxRestNode):
    '''
    <unipax>/graph REST node.
    '''
    def __init__(self, parent):
        super().__init__(parent)
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
    _append = '/regulatory'

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

    _append = '/metabolic'

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

    _append = '/ppi'
