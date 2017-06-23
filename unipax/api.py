import os
import time

import requests

import unipax.graph

DEFAULT_UNIPAX_ROOT_URL = 'http://unipax.informatik.uni-tuebingen.de'

__unipax_tmp__ = os.path.expanduser('~/.unipax/tmp')

if not os.path.isdir(__unipax_tmp__):
    os.makedirs(__unipax_tmp__)

def time_stamp():
    return time.strftime('%Y%m%d%H%M%S', time.gmtime())

class UniPaxException(Exception):
    pass

class UniPaxRestApi(object):
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

class UniPaxRestNode(object):
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

class UniPaxRestEndpoint(UniPaxRestNode):
    def __init__(self, parent):
        super().__init__(parent)

    def __call__(self, **params):
        return self.call(**params)

    def _call(self, **params):
        response = requests.get(self.url, params=params)
        if response.status_code != 200:
            raise UniPaxException
        return response

    def raw(self, **params):
        self._call(**params)

    def call(self, **params):
        raise NotImplementedError


class UniPaxRestAll(UniPaxRestNode):
    def __init__(self, parent):
        super().__init__(parent)


class UniPaxRestInfo(UniPaxRestNode):
    def __init__(self, api):
        super().__init__(api)
        self._append = '/info'
        self.xrefdbs = UniPaxRestInfoXRefDBs(self)

class UniPaxRestInfoXRefDBs(UniPaxRestEndpoint):
    def __init__(self, node):
        super().__init__(node)
        self._append = '/xrefdbs'

    def call(self):
        response = self._call()
        return [db.strip() for db in response.content.decode('utf-8').split('\n') if db]


class UniPaxRestGraph(UniPaxRestNode):
    def __init__(self, api):
        super().__init__(api)
        self._append = '/graph'
        self.regulatory = UniPaxRestGraphRegulatory(self)
        self.metabolic = UniPaxRestGraphMetabolic(self)
        self.ppi = UniPaxRestGraphPpi(self)

class UniPaxRestGraphEndpoint(UniPaxRestEndpoint):
    def __init__(self, node):
        super().__init__(node)

    def call(self, **params):
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
        response = self._call(**params)
        with open(path, 'wb') as downloaded_file:
            downloaded_file.write( response.content )

class UniPaxRestGraphRegulatory(UniPaxRestGraphEndpoint):
    '''
    <unipax>/graph/regulatory endpoint.

    Original documentation:

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

class UniPaxRestGraphMetabolic(UniPaxRestGraphEndpoint):
    '''
    <unipax>/graph/metabolic endpoint.

    Original documentation:

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

class UniPaxRestGraphPpi(UniPaxRestGraphEndpoint):
    def __init__(self, node):
        super().__init__(node)
        self._append = '/ppi'
