import re
from lxml import etree

NS_XML = 'http://www.w3.org/XML/1998/namespace'
NS_RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'

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
    eur = Namespace('http://vivo.eur.nl/ns/1.0#')



    @classmethod
    def uri_split(cls, uri):
        for sep in ['#', '/', ':']:
            parts = uri.rsplit(sep, 1)
            if len(parts) == 2:
                return parts[0] + sep, parts[1]
        raise ValueError('Can not split uri: %s' % uri)


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

def register_etree_prefix(prefix, ns):
    if hasattr(etree, 'register_namespace'):
        etree.register_namespace(prefix, ns)
    else:
        etree._namespace_map[ns] = prefix

def escape_invalid_unicode_range(value):
    "removes UTF-8 character ranges that are not allowed in XML"
    if not isinstance(value, unicode):
        value = value.decode('utf8')
    return re.sub(
        u'[^\x09\x0A\x0D\u0020-\uD7FF\uE000-\uFFFD]+', '', value)


def pyjson2rdfxml(data):
    for prefix in dir(NS):
        if isinstance(getattr(NS, prefix), Namespace):
            register_etree_prefix(prefix, getattr(NS, prefix).ns)
    doc = etree.Element('{%s}RDF' % NS_RDF)
    for subject in data:
        s_el = etree.SubElement(doc, '{%s}Description' % NS_RDF)
        if subject.startswith('_:'):
            s_el.attrib['{%s}nodeID' % NS_RDF] = subject[2:]
        else:
            s_el.attrib['{%s}about' % NS_RDF] = subject
        for predicate in data[subject]:
            for object in data[subject][predicate]:
                object['value'] = escape_invalid_unicode_range(object['value'])
                ns, tag = NS.uri_split(predicate)
                p_el = etree.SubElement(s_el, '{%s}%s'  % (ns, tag))
                if object['type'] == 'uri':
                    p_el.attrib['{%s}resource' % NS_RDF] = object['value']
                elif object['type'] == 'bnode':
                    assert object['value'].startswith('_:'), (
                        "Blank node should start with '_:'")
                    p_el.attrib['{%s}nodeID' % NS_RDF] = object['value'][2:]
                elif object['type'] == 'literal':
                    p_el.text = object['value']
                    lang = object.get('lang')
                    datatype = object.get('datatype')
                    if lang:
                        p_el.attrib['{%s}lang' % NS_XML] = lang
                    elif datatype:
                        p_el.attrib['{%s}datatype' % NS_RDF] = datatype
    return etree.tostring(doc, encoding='UTF-8')

def rdfxml2pyjson(data):
    result = {}
    if not data:
        return result
    doc = etree.fromstring(data)
    for s_el in doc:
        subject = s_el.attrib.get('{%s}about' % NS_RDF)
        if not subject:
            subject = '_:%s' % s_el.attrib['{%s}nodeID' % NS_RDF]
        predicates = result.get(subject)
        if predicates is None:
            predicates = {}
            result[subject.decode('utf8')] = predicates
        for p_el in s_el:
            ns, tag = p_el.tag[1:].split('}')
            predicate = ns + tag
            objects = predicates.get(predicate)
            if objects is None:
                objects = []
                predicates[predicate.decode('utf8')] = objects
            uri = p_el.attrib.get('{%s}resource' % NS_RDF)
            if not uri is None:
                objects.append(dict(value=uri.decode('utf8'), type='uri'))
                continue
            blank = p_el.attrib.get('{%s}nodeID' % NS_RDF)
            if not blank is None:
                objects.append(dict(value=u'_:%s' % blank, type='bnode'))
                continue
            literal = p_el.text
            if isinstance(literal, str):
                literal = literal.decode('utf8')
            value = dict(value=literal, type='literal')
            lang = p_el.attrib.get('{%s}lang' % NS_XML)
            datatype = p_el.attrib.get('{%s}datatype' % NS_RDF)
            if lang:
                value['lang'] = lang
            elif datatype:
                value['datatype'] = datatype
            objects.append(value)
    return result
