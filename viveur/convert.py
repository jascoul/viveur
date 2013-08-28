from viveur.utils import NS, uris, literals, pyjson2rdfxml

VIVOTYPES = {'Article/Letter to the editor': NS.bibo.AcademicArticle,
             'Part of book - chapter': NS.bibo.Chapter,
             'Article in volume - proceedings': NS.bibo.Proceedings,
             'Doctoral thesis': NS.bibo.Thesis,
             'Contribution weekly / daily journal':NS.bibo.Article,
             'Book - monograph - book editorial': NS.bibo.BookSection,
             'Report': NS.bibo.Report,
             'Book review': NS.core.Review,
             'Award': NS.core.Award,
             'internet article': NS.bibo.Webpage,
             'Book editorship': NS.bibo.Book,
             'Lecture': NS.core.Presentation,
             'Inaugural speech': NS.core.Presentation,
             'television or radio appearance': NS.bibo.Interview,
             'Computer program / software': NS.dctype.Software}

# XXX: Book editorship is a contributor role, not a type..

ONTOLOGY = {
  NS.eur.EURAcademicEmployee: {
    NS.rdf.type: uris(NS.owl.Class),
    NS.rdfs.subClassOf: uris(NS.foaf.Person),
    NS.rdfs.label: literals("EUR Academic Employee")},
  NS.eur.AcademicDepartment: {
    NS.rdf.type: uris(NS.owl.Class),
    NS.rdfs.subClassOf: uris(NS.foaf.Organization),
    NS.rdfs.label: literals("EUR Department")},
  NS.eur.AcademicFaculty: {
    NS.rdf.type: uris(NS.owl.Class),
    NS.rdfs.subClassOf: uris(NS.foaf.Organization),
    NS.rdfs.label: literals("EUR Faculty")},
    }


class VIVOConverter(object):
    def __init__(self, metis_db, publication_ids):
        self.db = metis_db
        self.graph = {}
        self.graph.update(ONTOLOGY)

    def convert(self, work_id):
        work = self.db.publication(work_id)
        if (work['status'] == 'Work in progress' or
            work['type'] == 'Other output'):
            return

        if work['type'] == 'Scientific position':
            # TODO: position should be added to a person, it's not a work
            return
        work_uri = NS.viveur['work-%s' % work['id']]
        predicates = {}
        predicates[NS.rdf.type] = uris(VIVOTYPES[work['type']])
        if work['title']:
            predicates[NS.rdfs.label] = literals(work['title'],
                                                 datatype=NS.xsd.string)
            predicates[NS.dcterms.title] = literals(work['title'],
                                                    datatype=NS.xsd.string)
        if work['publisher_loc']:
            predicates[
                NS.core.placeOfPublication] = literals(work['publisher_loc'])
        if work['publisher']:
            predicates[NS.core.publisher] = literals(work['publisher'])
        if work['start_page']:
            predicates[NS.bibo.pageStart] = literals(work['start_page'],
                                                     datatype=NS.xsd.string)
        if work['end_page']:
            predicates[NS.bibo.pageEnd] = literals(work['end_page'],
                                                   datatype=NS.xsd.string)
        if work['num_pages']:
            predicates[NS.bibo.numPages] = literals(work['num_pages'])
        if work['volume']:
            predicates[NS.bibo.volume] = literals(work['volume'],
                                                  datatype=NS.xsd.string)
        if work['issue']:
            predicates[NS.bibo.volume] = literals(work['issue'],
                                                  datatype=NS.xsd.string)
        if work['abstract']:
            predicates[NS.bibo.abstract] = literals(work['abstract'],
                                                    datatype=NS.xsd.string)
        if work['issued_year']:
            dt_uri = NS.viveur['datetime-%s' % work['id']]
            predicates[NS.core.dateTimeValue] = uris(dt_uri)
            self.graph[dt_uri] = {
                NS.rdf.type: uris(NS.core.DateTimeValue),
                NS.core.dateTimePrecision: uris(NS.core.yearPrecision),
                NS.core.dateTime: literals(
                '%s-01-01T00:00:00' % work['issued_year'],
                datatype=NS.xsd.dateTime)}
        urls = [url for url in (work['url'], work['repository_url']) if url]
        for url in urls:
            if url.startswith('http://dx.doi.org'):
                predicates[NS.bibo.doi] = literals(
                    url.replace('http://dx.doi.org/', 'doi:'),
                    datatype=NS.xsd.anyURI)
            elif url.startswith('http://hdl.handle.net'):
                predicates[NS.bibo.handle] = literals(
                    url.replace('http://hdl.handle.net/', 'hdl:'),
                    datatype=NS.xsd.anyURI)
        if urls:
            predicates[NS.core.linkURI] = literals(*urls,
                                                   datatype=NS.xsd.anyURI)
        for rank, author in enumerate(work['author']):
            person_uri = NS.viveur['person-%s' % author['researcher_id']]
            author_uri = NS.viveur['author-%s-%s' % (work_id, rank + 1)]
            if rank == 0:
                predicates[NS.dcterms.created] = uris(person_uri)
            predicates.setdefault(NS.core.informationResourceInAuthorship,
                                  []).append({'type': 'uri',
                                              'value': author_uri})
            author_predicates = {
                NS.rdf.type: uris(NS.core.Authorship),
                NS.core.linkedAuthor: uris(person_uri),
                NS.core.linkedInformationResource: uris(work_uri),
                NS.core.authorRank: literals(str(rank+1), datatype=NS.xsd.int)}
            self.graph[author_uri] = author_predicates
            if not person_uri in self.graph:
                person_predicates = {
                    NS.rdf.type: uris(NS.foaf.Person)
                    }
                if author['family_name']:
                    person_predicates[
                        NS.foaf.lastName] = literals(author['family_name'])
                if author['initials']:
                    person_predicates[
                        NS.foaf.firstName] = literals(author['initials'])
                if author['prefix']:
                    person_predicates[
                        NS.foaf.prefix] = literals(author['prefix'])
                if author['honorific']:
                    person_predicates[
                        NS.core.preferredTitle] = literals(author['honorific'])

                fullname = [author['family_name']]
                if author['initials']:
                    fullname.append(', %s' % author['initials'])
                if author['prefix']:
                    fullname.append(' %s' % author['prefix'])
                if author['honorific']:
                    fullname.insert(0, '%s ' % author['honorific'])
                person_predicates[NS.rdfs.label] = literals(' '.join(fullname))
                position_uri = NS.viveur['position-%s' % author['researcher_id']]
                person_predicates[NS.core.personInPosition] = uris(position_uri)
                position_predicates = {
                    NS.rdf.type: uris(NS.core.PrimaryPosition),
                    NS.core.positionForPerson: uris(person_uri),
                    NS.rdfs.label: literals(author['type'])}
                if author['affiliation']['name'] == 'Extern':
                    org_uri = None
                    faculty_uri = None
                else:
                    org_uri = NS.viveur['org-%s' % author['affiliation']['id']]
                    faculty_uri = NS.viveur['org-%s' % author['faculty']['id']]
                    person_predicates[NS.rdf.type].append(
                        {'type': 'uri',
                         'value': NS.eur.EURAcademicEmployee})
                    position_predicates[
                        NS.core.positionInOrganization] = uris(org_uri)
                self.graph[person_uri] = person_predicates
                self.graph[position_uri] = position_predicates
                if org_uri and org_uri not in self.graph:
                    name = (author['affiliation']['name_english'] or
                            author['affiliation']['name'])
                    org_type_uri = NS.eur[
                        'Academic%s' % author['affiliation']['type']]
                    org_predicates = {
                        NS.rdf.type: uris(NS.foaf.Organization,
                                          org_type_uri),
                        NS.rdfs.label: literals(name),
                        NS.foaf.name: literals(name),
                        NS.core.subOrganizationWithin: uris(faculty_uri)}
                    self.graph[org_uri] = org_predicates
                if org_uri and faculty_uri not in self.graph:
                    name = (author['faculty']['name_english'] or
                            author['faculty']['name'])
                    org_type_uri = NS.eur[
                        'Academic%s' % author['affiliation']['type']]
                    org_predicates = {
                        NS.rdf.type: uris(NS.foaf.Organization,
                                          org_type_uri),
                        NS.rdfs.label: literals(name),
                        NS.foaf.name: literals(name)}
                    self.graph[faculty_uri] = org_predicates

        self.graph[work_uri] = predicates

    def write(self, filename):
        with open(filename, 'w') as f:
            f.write(pyjson2rdfxml(self.graph))
