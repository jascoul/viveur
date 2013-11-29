import sys
import os
from operator import itemgetter
import cPickle as pickle
from collections import defaultdict

try:
    import cx_Oracle
except ImportError:
    print >> sys.stderr, ('WARNING: No Oracle support. '
                          'Export path to instantclient to enable')

import sqlalchemy as sql

class MetisDB(object):
    """This class is useful for exporting large ammounts of data
    from the Oracle Metis database.

    Since the Metis database is a bit fragemented, this class loads complete
    tables into memory and converts them into something more sane,
    instead of doing lots of small queries.

    After populating, the entire class is cached to disk, which can be
    reloaded with the `from_cache()` method.

    The `publication(pub_id)` method returns a big blob of metadata with
    everything we know about a publication.

    The `xxx_by_xxx` attributes can be used for id lookup.
    """

    def __init__(self, config):
        self.config = config
        self.db = self._connect()

        self.publications = {}
        self.researchers = {}
        self.organisations = {}
        self.projects = {}
        self.contributors = {}
        self.journals = {}

        self.publications_by_year = defaultdict(set)
        self.publications_by_organisation = defaultdict(set)
        self.contributors_by_publication = defaultdict(set)


    @classmethod
    def from_cache(cls):
        if os.path.isfile('metis.pickle'):
            with open('metis.pickle', 'r') as f:
                return pickle.load(f)

    def _connect(self):
        dsn_tns = cx_Oracle.makedsn(self.config.get('metis', 'database'),
                                    int(self.config.get('metis', 'port')),
                                    self.config.get('metis', 'sid'))
        engine = sql.create_engine('oracle+cx_oracle://%s:%s@%s' % (
            self.config.get('metis', 'user'),
            self.config.get('metis', 'password'),
            dsn_tns))

        db = sql.MetaData(engine, schema='sysozis')
        sql.Table('resultaten', db, autoload=True)
        sql.Table('tijdschrift', db, autoload=True)
        sql.Table('producent', db, autoload=True)
        sql.Table('persoon', db, autoload=True)
        sql.Table('werkverband', db, autoload=True)
        sql.Table('medewerker', db, autoload=True)
        sql.Table('organisatiedeel', db, autoload=True)
        sql.Table('all_output', db, autoload=True)
        sql.Table('all_klas_ex', db, autoload=True)
        sql.Table('all_functie', db, autoload=True)
        sql.Table('all_rollen', db, autoload=True)
        sql.Table('all_status', db, autoload=True)
        sql.Table('all_niveau_organisatie', db, autoload=True)
        sql.Table('all_soort_organisatie', db, autoload=True)
        sql.Table('all_taal', db, autoload=True)
        sql.Table('rest_ondz', db, autoload=True)
        sql.Table('document', db, autoload=True)

        return db

    def populate(self):
        self.populate_organisations()
        self.populate_researchers()
        self.populate_contributors()
        self.populate_journals()
        self.populate_publications()

        with open('metis.pickle', 'w') as f:
            return pickle.dump(self, f)

    def populate_organisations(self):
        table = self.db.tables
        joined_tables = table['sysozis.organisatiedeel'].outerjoin(
            table['sysozis.all_niveau_organisatie'],
            sql.and_(table['sysozis.organisatiedeel'].c.code_niveau==
                     table['sysozis.all_niveau_organisatie'].c.code_niveau,
                     table['sysozis.all_niveau_organisatie'].c.taal == 'EN'))
        joined_tables = joined_tables.outerjoin(
            table['sysozis.all_soort_organisatie'],
            sql.and_(table['sysozis.organisatiedeel'].c.code_soort==
                     table['sysozis.all_soort_organisatie'].c.code_soort,
                     table['sysozis.all_soort_organisatie'].c.taal == 'EN'))

        for row in  joined_tables.select().execute():
            data = {'id': row[0],
                    'type': row.oms_soort,
                    'name': row.naam,
                    'name_english': row.naam_eng,
                    'level': row.oms_niveau}
            self.organisations[data['id']] = data

    def populate_journals(self):
        table = self.db.tables
        for row in  table['sysozis.tijdschrift'].select().execute():
            data = {'id': row[0],
                    'name': row.naam_tijdschrift,
                    'issn': row.issn_nr}
            self.journals[data['id']] = data

    def populate_researchers(self):
        table = self.db.tables
        joined_tables = table['sysozis.medewerker'].outerjoin(
            table['sysozis.persoon'],
            (table['sysozis.medewerker'].c.onderzoekernummer==
             table['sysozis.persoon'].c.onderzoekernummer))
        for row in joined_tables.select().execute():
            if row.voorkeur != 'J':
                continue
            data = {'id': row[0],
                    'employee_id': row.persoonsnummer,
                    'family_name': row.naam,
                    'prefix': row.vv,
                    'initials': row.vlt,
                    'honorific': row.tt}
            self.researchers[data['id']] = data

    def populate_contributors(self):
        table = self.db.tables
        joined_tables = table['sysozis.producent'].outerjoin(
            table['sysozis.all_functie'],
            sql.and_(table['sysozis.producent'].c.code_functie==
                     table['sysozis.all_functie'].c.code_functie,
                     table['sysozis.all_functie'].c.taal == 'EN'))

        for row in joined_tables.select().execute():
            data = {'id': (row.volgnummer, row.onderzoekernummer),
                    'type': row.oms_functie,
                    'researcher_id': row.onderzoekernummer,
                    'organisation_id': row.code_organisatie_a,
                    'order': row.rang}
            self.contributors[data['id']] = data
            self.contributors_by_publication[row.volgnummer].add(data['id'])

    def populate_publications(self):
        table = self.db.tables
        pub = table['sysozis.resultaten']
        joined_tables = pub.join(
            table['sysozis.all_output'],
            sql.and_(pub.c.code_output==table['sysozis.all_output'].c.code_output,
                     table['sysozis.all_output'].c.taal == 'EN'))
        joined_tables = joined_tables.outerjoin(
            table['sysozis.all_klas_ex'],
            sql.and_(
              pub.c.code_klas_ex==table['sysozis.all_klas_ex'].c.code_klas_ex,
              table['sysozis.all_klas_ex'].c.taal == 'EN'))
        joined_tables = joined_tables.outerjoin(
            table['sysozis.all_taal'],
            sql.and_(
              pub.c.code_taal==table['sysozis.all_taal'].c.code_taal,
              table['sysozis.all_taal'].c.taal == 'EN'))

        joined_tables = joined_tables.outerjoin(
            table['sysozis.all_status'],
            sql.and_(
              pub.c.status==table['sysozis.all_status'].c.status,
              table['sysozis.all_status'].c.taal == 'EN'))

        joined_tables = joined_tables.outerjoin(
            table['sysozis.document'],
            pub.c.volgnummer==table['sysozis.document'].c.volgnummer)

        query = joined_tables.select()
        for row in query.execute():
            metis_id = row[0]
            data = {'id': row[0],
                    'journal_id': row.code_tijdschrift,
                    'status': row.oms_status,
                    'language': row.oms_taal,
                    'type': row.oms_output,
                    'audience': row.oms_klas_ex,
                    'abstract': row.document,
                    'url': row.url,
                    'repository_url': row.url_dare,
                    'title': row.titel,
                    'isbn': row.isbn_nr,
                    'num_pages': row.aantal_pagina,
                    'start_page': row.pagina_vanaf,
                    'end_page': row.pagina_tm,
                    'volume': row.volume_nr,
                    'issue': row.reeks_nr,
                    'modified': row.mutatiedatum_2 or row.mutatiedatum,
                    'issued': row.datum_2 or row.datum,
                    'issued_year': row.jaar_uitgave or row.verslagjaar,
                    'publisher': row.uitgever,
                    'publisher_loc': row.plaats_v_uitgifte}
            if data['abstract']:
                data['abstract'] = data['abstract'].replace('\x00', '')
            self.publications[metis_id] = data
            self.publications_by_year[row.verslagjaar].add(metis_id)
            organisations = set()
            for contributor_id in self.contributors_by_publication[data['id']]:
                contributor = self.contributors[contributor_id]
                organisations.add(contributor['organisation_id'])
                organisations.add(
                    '%s0000' % contributor['organisation_id'][:4])
                organisations.add(
                    '%s00000' % contributor['organisation_id'][:3])
                organisations.add(
                    '%s000000' % contributor['organisation_id'][:2])
            for org_id in organisations:
                self.publications_by_organisation[org_id].add(data['id'])

    def publication(self, pub_id):
        "return everything we know about a single publication"
        result = self.publications[pub_id].copy()
        result['author'] = []
        contributors = [self.contributors[i]
                        for i in self.contributors_by_publication[pub_id]]
        contributors.sort(key=itemgetter('order'))
        for contributor in contributors:
            try:
                researcher = self.researchers[
                    contributor['researcher_id']].copy()
            except KeyError:
                print >> sys.stderr, (
                    'WARNING: publication %s references unknown '
                    'researcher %s' % (pub_id, contributor['researcher_id']))
                continue
            researcher.update(contributor)
            researcher['affiliation'] = self.organisations[
                researcher['organisation_id']]
            try:
                researcher['faculty'] = self.organisations[
                    researcher['organisation_id'][:2] + '000000']
            except:
                pass
            result['author'].append(researcher)
        if result['journal_id']:
            result['journal'] = self.journals[result['journal_id']]
        return result


