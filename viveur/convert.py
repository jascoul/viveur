from viveur.utils import NS, uris, literals

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

class VivoConverter(object):
    def __init__(self, metis_db, publication_ids):
        self.db = metis_db

        self.journals = {}
        self.works = {}
        self.organisations = {}
        self.persons = {}

    def convert(self, work_id):
        work = self.db.worklication(work_id)
        if (work['status'] == 'Work in progress' or
            work['type'] == 'Other output'):
            return

        if work['type'] == 'Scientific position':
            # TODO: position should be added to a person, it's not a work
            return
        work_uri = NS.viveur['work/%s' % work['id']]
        predicates = {}
        predicates[NS.rdf.type] = uris(VIVOTYPES[work['type']])
        if work['title']:
            predicates[NS.rdfs.label] = literals(work['title'])
        if work['publisher_loc']:
            predicates[
                NS.core.placeOfPublication] = literals(work['publisher_loc'])
        if work['publisher']:
            predicates[NS.core.publisher] = literals(work['publisher'])
        if work['start_page']:
            predicates[NS.bibo.pageStart] = literals(work['start_page'])
        if work['end_page']:
            predicates[NS.bibo.pageEnd] = literals(work['end_page'])
        if work['num_pages']:
            predicates[NS.bibo.numPages] = literals(work['num_pages'])
        if work['volume']:
            predicates[NS.bibo.volume] = literals(work['volume'])
        if work['issue']:
            predicates[NS.bibo.volume] = literals(work['issue'])
        if work['abstract']:
            predicates[NS.bibo.abstract] = literals(work['abstract'])
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

        self.works[work_uri] = predicates


