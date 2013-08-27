class Namespace(object):
    def __init__(self, ns):
        self.ns = ns

    def __getattr__(self, el):
        return self.ns + el

    def __getitem__(self, el):
        return self.ns + el

class NS(object):
    rdf = Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
    rdfs = Namespace('http://www.w3.org/2000/01/rdf-schema#')
    xsd = Namespace('http://www.w3.org/2001/XMLSchema#')
    viveur = Namespace('http://vivo.eur.nl/individual/')
    foaf = Namespace('http://xmlns.com/foaf/0.1/')
    core = Namespace('http://vivoweb.org/ontology/core#')
    vitro = Namespace('http://vitro.mannlib.cornell.edu/ns/vitro/0.7')
    skos = Namespace('http://www.w3.org/2004/02/skos/core#')
    local = Namespace('http://localhost/core/ontology/core-local#')
    localVivo = Namespace('http://vivo.libr.tue.nl/ontology/')
    tue = Namespace('http://vivo.libr.tue.nl/ontology/tue#')
    eur = Namespace('http://vivo.eur.nl/ontology#')
    public = Namespace('http://vitro.mannlib.cornell.edu/ns/vitro/public#')
    event = Namespace('http://purl.org/NET/c4dm/event.owl#')
    bibo = Namespace('http://purl.org/ontology/bibo/')
    dcterms = Namespace('http://purl.org/dc/terms/')
    dctype = Namespace('http://purl.org/dc/dcmitype/')
    owl = Namespace('http://www.w3.org/2002/07/owl#')
    score = Namespace('http://vivoweb.org/ontology/score#')
    event = Namespace('http://purl.org/NET/c4dm/event.owl#')

def uris(*values):
    return [{'type': 'uri', 'value': value} for value in values]

def literals(*values, **args):
    if 'datatype' in args:
        return [{'type': 'literal',
                 'value': v,
                 'datatype': args['datatype']} for v in values]
    elif 'lang' in args:
        return [{'type': 'literal',
                 'value': v,
                 'lang': args['lang']} for v in values]
    else:
        return [{'type': 'literal',
                 'value': v} for v in values]
