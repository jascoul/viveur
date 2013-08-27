import os
import ConfigParser

from viveur.metis import MetisDB
from viveur.convert import VivoConverter

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
    for year in ['2012', '2011', '2010', '2009', '2008']:
        publications = publications.union(db.publications_by_year[year])
    publications = publications.intersection(
        db.publications_by_organisation[RSM])

    print 'converting %s publications' % len(publications)
    converter = VivoConverter(db, publications)
    for pub_id in publications:
        converter.convert(pub_id)




