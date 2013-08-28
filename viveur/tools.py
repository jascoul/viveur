import os
import sys
import ConfigParser

from viveur.metis import MetisDB
from viveur.convert import VIVOConverter

import sqlalchemy as sql

ERIM = '45530000'
RSM = '45000000'

def metis_dumper():
    config_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'buildout.cfg')
    config = ConfigParser.ConfigParser()
    config.read(config_file)

    db = MetisDB.from_cache()
    if db is None:
        print 'populating from metis db'
        db = MetisDB(config)
        db.populate()
    else:
        print 'using cached metis db'
    print 'loaded %s publications' % len(db.publications)

    publications = set()
    for year in ['2012', '2011', '2010']:
        publications = publications.union(db.publications_by_year[year])
    publications = publications.intersection(
        db.publications_by_organisation[RSM])

    print 'converting %s publications' % len(publications)
    converter = VIVOConverter(db, publications)
    for pub_id in publications:
        converter.convert(pub_id)

    converter.write('vivo.xml')

def vivo_ingester():
    from viveur.vivo import VIVOIngester
    config_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'buildout.cfg')
    config = ConfigParser.ConfigParser()
    config.read(config_file)

    ingester = VIVOIngester(config)
    ingester.ingest(sys.argv[1])

def drop_vivo_tables():
    config_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'buildout.cfg')
    config = ConfigParser.ConfigParser()
    config.read(config_file)

    engine = sql.create_engine('mysql://%s:%s@localhost/%s' % (
        config.get('config', 'mysql_user'),
        config.get('config', 'mysql_password'),
        config.get('config', 'mysql_database')))
    metadata = sql.MetaData(engine)
    metadata.reflect()
    print 'Dropping %s tables' % len(metadata.tables)
    metadata.drop_all()



