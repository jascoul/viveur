#!/usr/bin/env python

# Imports
import base64
from collections import defaultdict
import cStringIO
import cx_Oracle
from datetime import datetime, timedelta
from HTMLParser import HTMLParser
from jnius import autoclass
import logging
import pickle
import os
from pprint import pprint
from pytz import timezone
import pytz
from rdflib import Namespace
from rdfalchemy import rdfSingle
from rdfalchemy.rdfSubject import rdfSubject
from rdflib import Literal, BNode, Namespace, URIRef
from rdflib import RDF, RDFS, Graph, OWL
from rdflib.namespace import XSD
import shutil
from suds.client import Client
import sys
import urllib
from xml.dom import minidom

# Logging & timestamp
timeStamp = datetime.now(pytz.timezone('Europe/Amsterdam')).isoformat()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fName = datetime.now(pytz.timezone('Europe/Amsterdam')).strftime('vivoharvester-%H:%M %d-%m-%Y.log')
handler = logging.FileHandler(fName)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
 
# Jnius autoclasses (java => python)
SDBJenaConnect = autoclass('org.vivoweb.harvester.util.repo.SDBJenaConnect')
SimpleSelector = autoclass('com.hp.hpl.jena.rdf.model.SimpleSelector')
DBConnection = autoclass('com.hp.hpl.jena.db.DBConnection')
LayoutType = autoclass('com.hp.hpl.jena.sdb.store.LayoutType')
DatabaseType = autoclass('com.hp.hpl.jena.sdb.store.DatabaseType')
SDBConnection = autoclass('com.hp.hpl.jena.sdb.sql.SDBConnection')
SDBFactory = autoclass('com.hp.hpl.jena.sdb.SDBFactory')
ModelFactory = autoclass('com.hp.hpl.jena.rdf.model.ModelFactory')
StoreDesc = autoclass('com.hp.hpl.jena.sdb.StoreDesc')
QueryFactory = autoclass('com.hp.hpl.jena.query.QueryFactory')
QueryExecutionFactory = autoclass('com.hp.hpl.jena.query.QueryExecutionFactory')
QueryExecution = autoclass('com.hp.hpl.jena.query.QueryExecution')
QuerySolution = autoclass('com.hp.hpl.jena.query.QuerySolution')
StringReader = autoclass('java.io.StringReader')
FileManager = autoclass('com.hp.hpl.jena.util.FileManager')
Resource = autoclass('com.hp.hpl.jena.rdf.model.Resource')

#sensitive stuff!
produrl = 'http://..'
testurl = 'http://..'
DB_URL = 'jdbc:mysql://127.0.0.1:3306/vivo?useUnicode=true&characterEncoding=UTF-8'
DB_USER = 'XXX'
DB_PASSWD = 'XXX'
O_USER = 'XXX'
O_PASSWD = 'XXX'
O_URL = '....tue.nl'
O_PORT = '1521'
O_SN = '.....tue.nl'
#sensitive stuff! 
 
# Global variables
vivo_app_url = 'http://vivo.libr.tue.nl/individual/'
VIVO_LOCATION_IN_TOMCAT_DIR='/var/lib/tomcat6/webapps/vivo'
app = Namespace(vivo_app_url)
harvesttag = 'TUE.PythonHarvester'
debug = False
Client.timeout = 120
client = Client(produrl)
client.set_options(retxml=True)
removeArray = []
expertiseRemoveArray = []
organizationsRemoveArray = []
organizationStructure = defaultdict(dict)
StaffList = [] # checkList for related data
WorkplacesList = {}
Counters = {}
PublicationsCount = {}
ResearcherList = {}
TuePublications = []



# Namespace declarations
foaf = Namespace('http://xmlns.com/foaf/0.1/')
core = Namespace('http://vivoweb.org/ontology/core#')
vitro = Namespace('http://vitro.mannlib.cornell.edu/ns/vitro/0.7')
skos = Namespace('http://www.w3.org/2004/02/skos/core#')
local = Namespace('http://localhost/core/ontology/core-local#')
localVivo = Namespace('http://vivo.libr.tue.nl/ontology/')
tue = Namespace('http://vivo.libr.tue.nl/ontology/tue#')
public = Namespace('http://vitro.mannlib.cornell.edu/ns/vitro/public#')
event = Namespace('http://purl.org/NET/c4dm/event.owl#')
bibo = Namespace('http://purl.org/ontology/bibo/')
dcterms = Namespace('http://purl.org/dc/terms/')
owl = Namespace('http://www.w3.org/2002/07/owl#')
score = Namespace('http://vivoweb.org/ontology/score#')
event = Namespace('http://purl.org/NET/c4dm/event.owl#')

# Jena triplestore connection
storeDesc = StoreDesc(LayoutType.LayoutTripleNodesHash, DatabaseType.MySQL)
conn = SDBConnection(DB_URL, DB_USER, DB_PASSWD)
store = SDBFactory.connectStore(conn, storeDesc)
dataset = SDBFactory.connectDataset(store)
model = dataset.getNamedModel('http://vitro.mannlib.cornell.edu/default/vitro-kb-2')
 

 
def oracleConnect():
    connection = cx_Oracle.connect(O_USER, O_PASSWD, O_URL+":"+O_PORT+"/"+O_SN)
    return connection
 
 
def getTagData(xml,tagName):
    EmptyTest = xml.getElementsByTagNameNS("*",tagName)
    if len(EmptyTest)> 0:
	if xml.getElementsByTagNameNS('*', tagName)[0].firstChild:
	    return xml.getElementsByTagNameNS('*', tagName)[0].firstChild.data.strip()
    return None

def contains_digits(s):
    for char in list(s):
        if char.isdigit():
            return True
            break
    return False

def copyImages():
    logger.info('Copying images')
    baseDir = VIVO_LOCATION_IN_TOMCAT_DIR+'/harvestedImages'
    fullDir = VIVO_LOCATION_IN_TOMCAT_DIR+'/harvestedImages/fullImages'
    thumbDir = VIVO_LOCATION_IN_TOMCAT_DIR+'/harvestedImages/thumbnails'   
    try:
	#if not os.path.exists(baseDir): os.mkdir(baseDir)
	if os.path.exists(fullDir): shutil.rmtree(fullDir)
	if os.path.exists(thumbDir): shutil.rmtree(thumbDir)
	shutil.copytree('images/fullImages',fullDir)
	shutil.copytree('images/thumbnails',thumbDir)
    except Exception, err:
	logger.error('Image copy failed: %s\n' % str(err))    
    logger.info('Copying images done')


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def handle_entityref(self, name):
        self.fed.append('&%s;' % name)
    def get_data(self):
        return ''.join(self.fed)

def html_to_text(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def storeList(itemlist,name):
    if os.path.exists('data/'+name+'.list'):
	os.remove('data/'+name+'.list')   
    f = open('data/'+name+'.list','wb')
    pickle.dump(itemlist, f)

def loadList(name):
    f = open('data/'+name+'.list','rb')
    return pickle.load(f)

def get_graph():
    g = Graph()
    g.bind('foaf', foaf)
    g.bind('core', core)
    g.bind('vitro', vitro)
    g.bind('local', local)
    g.bind('tue', tue)
    g.bind('localVivo', localVivo)
    return g

def writetriplestofile(string,filename):
    file = open("data/"+filename+".n3", "w")
    file.write(string)
    file.close()

def deleteTriplesFile(filename):
    if os.path.exists("data/"+filename+".n3"):
	os.remove("data/"+filename+".n3")
    
def processExpertises():
    logger.info('Processing expertise list')
    deleteTriplesFile("expertises")
    g = get_graph()
    connection = oracleConnect()
    cursor = connection.cursor()
    cursor.execute('SELECT EXPERTISE_ID,EXP_GEBIED_EN FROM EP_XEXPERTISE')
    rows = cursor.fetchall()
    global Counters
    Counters["Expertise"] = len(rows)
    for row in rows:
	eid = str(row[0])
	uri = URIRef("%sexpertise%s" % (app, eid))
	g.add( (uri, RDF.type ,skos.Concept) )
	g.add( (uri, RDFS.label, Literal(row[1].encode('utf-8')) ))
	g.add( (uri, tue.conceptId, Literal(eid.encode('utf-8')) ))
	g.add( (uri, localVivo.harvestedBy, Literal(harvesttag) ))
    connection.close()    
    gn3 = g.serialize(format='n3')
    writetriplestofile(gn3,"expertises")
    g.close()
    logger.info('Processing expertise list done')


def handleExpertisesForStaffmember(sid,g):
    property1 = client.factory.create('ns0:Property')
    property1._Naam = "TaalCode"
    property1.Waarde = "EN"
    property2 = client.factory.create('ns0:Property')
    property2._Naam = "RelatieNummer"
    property2.Waarde = sid
    result = client.service.VraagEnAntwoord('GeefMedewerkerExpertise',[property1,property2])
    xmldoc = minidom.parseString(result)
    itemlist = xmldoc.getElementsByTagNameNS('*', 'MedewerkerExpertise') 
    for exp in itemlist :
     	LabelDataR = getTagData(exp,"Omschrijving")
	if LabelDataR:
	    LabelDataR.replace("-", "")
	    LabelData = LabelDataR.lstrip()
	    LabelDataArray = LabelData.split(' ', 1)
	    ExpId = LabelDataArray[0].strip()
	    if contains_digits(ExpId): # wat te doen, expertises zonder id...
		staffUri = URIRef("%sstaff%s" % (app, sid))
		expUri = URIRef("%sexpertise%s" % (app, ExpId))
		g.add( (expUri, core.researchAreaOf, staffUri ))
    

def processExpertisesForStaffmembers():
    logger.info('Processing expertise per staffmember')
    deleteTriplesFile("staffexpertise")
    g = get_graph()
    StaffList_L = loadList("StaffList")
    global Counters
    Counters["ExpertiseAtStaff"] = 0
    connection = oracleConnect()
    cursor = connection.cursor()
    cursor.execute('SELECT RELATIENR, EXPERTISE_ID FROM EP_MDW_EXPERTISE')
    rows = cursor.fetchall()
    Count = 0
    for row in rows:
	relNr = str(row[0])
	expId = str(row[1])
	if relNr in StaffList_L:
	    Counters["ExpertiseAtStaff"] +=1
	    staffUri = URIRef("%sstaff%s" % (app, relNr))
	    expUri = URIRef("%sexpertise%s" % (app, expId))
	    g.add( (expUri, core.researchAreaOf, staffUri ))
    gn3 = g.serialize(format='n3')
    writetriplestofile(gn3,"staffexpertise")	    
    g.close()	
    connection.close()
    logger.info('Processing expertise list done')


def handleStaffId(person,g):
    if len(person.getElementsByTagNameNS("*","Relatienummer"))> 0:
	IdData = getTagData(person,"Relatienummer")
	StaffList.append(IdData)
	uri = URIRef("%sstaff%s" % (app, IdData))
	g.add( (uri, RDF.type ,foaf.Person) )
	g.add( (uri, tue.relatieNr, Literal(IdData.encode('utf-8')) ))
	g.add( (uri, localVivo.harvestedBy, Literal(harvesttag) ))
 
def processStaffIds():
    logger.info('Processing staff ids')
    deleteTriplesFile("staffids") 
    g = get_graph()
    global Counters
    Counters["StaffIds"] = 0
    property1 = client.factory.create('ns0:Property')
    property1._Naam = "TaalCode"
    property1.Waarde = "EN"
    property2 = client.factory.create('ns0:Property')
    property2._Naam = "OrganisatieId"
    #werkplekbijmedewerker heeft herhaalde personen voor 2e werkplek, dan geen naam!
    for orgid in organizationStructure["Departments"]:
        property2.Waarde = orgid
        result = client.service.VraagEnAntwoord('ZoekMedewerkers',[property1,property2])    
	xmldoc = minidom.parseString(result)
	stafflist = xmldoc.getElementsByTagNameNS('*', 'WerkplekBijMedewerker') 
	for s in stafflist :
	    handleStaffId(s,g)
	    Counters["StaffIds"] +=1
    for orgid in organizationStructure["Services"]:
        property2.Waarde = orgid
        result = client.service.VraagEnAntwoord('ZoekMedewerkers',[property1,property2])
	xmldoc = minidom.parseString(result)
	stafflist = xmldoc.getElementsByTagNameNS('*', 'WerkplekBijMedewerker') 
	for s in stafflist :
	    handleStaffId(s,g)
	    Counters["StaffIds"] +=1
    gn3 = g.serialize(format='n3')
    writetriplestofile(gn3,"staffids")
    StaffList.sort()
    storeList(StaffList,"StaffList")
    g.close()
    logger.info('Processing staff ids done')

def staffType(sid):
    options = {0 : tue.otherStaff,
                1 : tue.professor,
                10 : tue.associateProfessor,
                15 : tue.fullProfessorEmeritus,
                20 : tue.assistantProfessor,
                25 : tue.postdoc,
                30 : tue.universityTeacherResearcher,
                40 : tue.doctoralCandidatePhD,
		41 : tue.postgraduateDesignEngineer,
		50 : tue.studentAssistent,
		60 : tue.stagiaire,
		100 : tue.supportiveAndManagementStaff,
		110 : tue.secretary,
		200 : tue.otherJobsServ,
		300 : tue.otherJobsTech
    }
    staffType = None
    if sid: staffType = options.get(int(sid))
    if not staffType: staffType = foaf.Person
    return staffType

def staffTypeLabel(sid):
    options = {0 : 'Other staff',
                1 : 'Professor',
                10 : 'Associate Professor',
                15 : 'Full Professor emeritus',
                20 : 'Assistant Professor',
                25 : 'Postdoc',
                30 : 'University Teacher / Researcher',
                40 : 'doctoral candidate (PhD)',
		41 : 'Postgraduate Design Engineer',
		50 : 'Student-assistent',
		60 : 'Intern',
		100 : 'Supportive and management staff',
		110 : 'Secretary',
		200 : 'Other jobs - serv',
		300 : 'Other jobs - tech'
    }
    staffType = None
    if sid: staffType = options.get(int(sid))
    if not staffType: staffType = ""
    return staffType
 
def retrieveImage(StaffId):
    property1 = client.factory.create('ns0:Property')
    property1._Naam = "TaalCode"
    property1.Waarde = "EN"
    property2 = client.factory.create('ns0:Property')
    property2._Naam = "RelatieNummer"
    property2.Waarde = StaffId
    result = client.service.VraagEnAntwoord('GeefMedewerkerDetail',[property1,property2])    
    xmldoc = minidom.parseString(result)
    FotoData = getTagData(xmldoc, 'Foto')
    fileName = StaffId+'.jpg'
    out_gif = file('images/fullImages/'+ fileName, 'wb') 
    out_gif.write(base64.decodestring(FotoData)) 
    out_gif.close()
    out_tgif = file('images/thumbnails/thumbnail'+ fileName, 'wb') 
    out_tgif.write(base64.decodestring(FotoData)) 
    out_tgif.close()

def processStaffDetails():
    
    logger.info('Processing staff details')
    deleteTriplesFile("staffdetails")
    #if os.path.exists('images'):
    #	shutil.rmtree('images') # remove previous images
    g = get_graph()
    webg = get_graph()
    StaffList_L = loadList("StaffList")    
    global Counters
    Counters["StaffDetail"]=0
    Counters["NewImages"] = 0
    global ResearcherList
    connection = oracleConnect()
    cursor = connection.cursor()
    Query = 'SELECT emp.RELATIENR,emp.VOORNAAM,emp.ROEPNAAM,'
    Query = Query+'emp.OVERIGE_VOORNAMEN,emp.ACHTERNAAM,emp.VOORVOEGSELS,'
    Query = Query+'emp2.PRESENTATIENAAM_FORMEEL_NAAM,emp2.PRESENTATIENAAM_FORMEEL_TITEL,'
    Query = Query+'emp.TITEL_VOOR  ,emp.TITEL_NA,emp2.EMAIL AS,emp2.BIOGRAFIE_EN,'
    Query = Query+'emp2.PERSOONLIJKE_URL,emp.DATUM_IN_DIENST ,emp.DATUM_UIT_DIENST,'
    Query = Query+'workplace.TELEFOONNR ,workplace.KAMERNR,workplace.FAX_NR,'
    Query = Query+'workplace.FUNCTIE_ID ,emp3.ONDERZOEKERNR ,emp3.PRESENTATIENAAM_PROMOTOR,'
    Query = Query+'ancillary.NEVENWERKZAAMHEDEN,emp2.TONEN_FOTO,ancillary.PUBLICEREN_TOEGESTAAN ' #,empid.FNC_ID_EP '
    Query = Query+'FROM EP_T_PERSONEN_HRM emp LEFT JOIN EP_V_PERSONEN emp2 '
    Query = Query+'ON emp.RELATIENR = emp2.RELATIENR '
    Query = Query+'LEFT JOIN (Select DISTINCT ONDERZOEKERNR,RELATIENR, PRESENTATIENAAM_PROMOTOR '
    Query = Query+'FROM EP_TUE_ONDERZOEKMEDEWERKER_V) emp3 on emp.RELATIENR = emp3.RELATIENR '
    Query = Query+'LEFT JOIN EP_V_PERS_WERKPLEK workplace ON emp.RELATIENR = workplace.RELATIENR '
    Query = Query+'LEFT JOIN EP_V_NEVENWERKZAAMHEDEN ancillary ON emp.RELATIENR = ancillary.RELATIENR'
    cursor.execute(Query)
    rows = cursor.fetchall()
    ImageFetchList = []
    for row in rows:
	StaffId = str(row[0])
	functieid = row[18] # int
	if StaffId in StaffList_L: #soms zit pers niet in werkplek tabel..
	    Counters["StaffDetail"] +=1
	    voornaam = row[1]
	    roepnaam = row[2]
	    overigevoornamen = row[3]
	    achternaam = row[4]
	    voorvoegsels = row[5]
	    presnaamformeelNaam = row[6]
	    if not presnaamformeelNaam: presnaamformeelNaam = achternaam + ', ' + voornaam
	    presnaamformeelTitel = row[7]
	    titelvoor = row[8]
	    titelna = row[9]
	    email = row[10]
	    biografie = row[11]
	    if biografie: biografie = html_to_text(biografie)
	    URL = row[12]
	    datumindienst = row[13]
	    datumuitdienst = row[14]
	    telefoon = row[15]
	    kamernummer = row[16]
	    fax = row[17]	    
	    onderzoekernr = row[19]
	    presentatienaampromotor = row[20]
	    nevenwerkzaamheden = row[21]  
	    toonfoto = row[22]
	    nevenpublicerenok = row[23]
	    staffUri = URIRef("%sstaff%s" % (app, StaffId))
	    g.add( (staffUri, RDF.type, tue.tueIndividual))
	    g.add( (staffUri, RDF.type, foaf.Person)) # is specified in positions
	    g.add( (staffUri, RDFS.label, Literal(presnaamformeelNaam.encode('utf-8')) ))
	    g.add( (staffUri, tue.relatieNr, Literal(StaffId.encode('utf-8')) ))
	    g.add( (staffUri, localVivo.harvestedBy, Literal(harvesttag) ))
	    if onderzoekernr:
		g.add( (staffUri, tue.onderzoekerNr, Literal(onderzoekernr) ))
		ResearcherList[onderzoekernr] = StaffId
	    if email: g.add( (staffUri, core.primaryEmail, Literal(email.encode('utf-8')) ))
	    if telefoon: g.add( (staffUri, core.phoneNumber, Literal(telefoon.encode('utf-8')) ))
	    if fax: g.add( (staffUri, core.faxNumber, Literal(fax.encode('utf-8')) ))
	    if voornaam: g.add( (staffUri, foaf.firstName, Literal(voornaam.encode('utf-8')) ))
	    if achternaam: g.add( (staffUri, foaf.lastName, Literal(achternaam.encode('utf-8')) ))
	    if overigevoornamen: g.add( (staffUri, core.middleName, Literal(overigevoornamen.encode('utf-8')) ))
	    if voorvoegsels: g.add( (staffUri, bibo.prefixName, Literal(voorvoegsels.encode('utf-8')) ))
	    if titelvoor: g.add( (staffUri, core.preferredTitle, Literal(titelvoor.encode('utf-8')) ))
	    if biografie: g.add( (staffUri, core.overview, Literal(biografie.encode('utf-8')) ))
	    if URL:
		webUri = URIRef("%swebsite%s" % (app, StaffId))
		webg.add( (webUri, RDF.type ,core.URLLink) )
		webg.add( (webUri, core.webpageOf ,staffUri) )
		webg.add( (webUri, core.rank, Literal(1)) )
		webg.add( (webUri, core.linkURI , Literal(URL.encode('utf-8')) ))
		webg.add( (webUri, core.linkAnchorText, Literal("Personal site") ))
		webg.add( (webUri, localVivo.harvestedBy, Literal(harvesttag) ))
	    if toonfoto == "J":
		ImageFetchList.append(StaffId)
    gn3 = g.serialize(format='n3')
    writetriplestofile(gn3,"staffdetails")	    
    g.close()	
    webgn3 = webg.serialize(format='n3')
    writetriplestofile(webgn3,"webpages")	    
    webg.close()
    storeList(ResearcherList,"ResearcherList")
    storeList(ImageFetchList,"ImageFetchList")

    # to do obsolete image removal
    logger.info('Processing staff details done')



def processImages():
    logger.info('Processing images')
    if not os.path.exists('images'):
	os.makedirs('images/fullImages')
	os.makedirs('images/thumbnails') 
    
    imgg = get_graph()  
    ImageFetchList = loadList("ImageFetchList")
    for StaffId in ImageFetchList:
	fileName = StaffId +'.jpg'
	if not os.path.exists('images/fullImages/'+ fileName):
	    Counters["NewImages"] += 1 
	    retrieveImage(StaffId)
	imgUri = URIRef("%simage%s" % (app, StaffId))
	staffUri = URIRef("%sstaff%s" % (app, StaffId))
	imgg.add( (staffUri, public.mainImage, imgUri))
	imgThumbUri = URIRef("%sthumbimage%s" % (app, StaffId))
	imgDLUri = URIRef("%simage%s" % (app, 'dl-'+StaffId))
	imgThumbDLUri = URIRef("%simage%s" % (app, 'dlt-'+StaffId))
	imgg.add ( (imgUri, public.thumbnailImage, imgThumbUri))
	imgg.add ( (imgUri, RDF.type, public.File))
	imgg.add ( (imgUri, public.downloadLocation, imgDLUri))
	imgg.add ( (imgUri, public.filename, Literal(fileName)))
	imgg.add ( (imgUri, public.mimeType, Literal('image/jpg')))
	imgg.add ( (imgDLUri,public.directDownloadUrl , Literal("/harvestedImages/fullImages/"+fileName)))
	imgg.add ( (imgDLUri,RDF.type, public.FileByteStream))
	imgg.add ( (imgDLUri,vitro.modTime, Literal(timeStamp)))
	imgg.add ( (imgThumbUri, RDF.type, public.File ))
	imgg.add ( (imgThumbUri, public.downloadLocation, imgThumbDLUri))
	imgg.add ( (imgThumbUri, public.filename, Literal('thumbnail'+fileName)))
	imgg.add ( (imgThumbUri, public.mimeType, Literal('image/jpg')))
	imgg.add ( (imgThumbDLUri,public.directDownloadUrl , Literal("/harvestedImages/thumbnails/thumbnail"+fileName)))
	imgg.add ( (imgThumbDLUri,RDF.type , public.FileByteStream))
	imgg.add ( (imgThumbDLUri,vitro.modTime , Literal(timeStamp)))
	imgg.add ( (imgUri, localVivo.harvestedBy, Literal(harvesttag) ))
	imgg.add ( (imgDLUri, localVivo.harvestedBy, Literal(harvesttag) ))
	imgg.add ( (imgThumbUri, localVivo.harvestedBy, Literal(harvesttag) ))
	imgg.add ( (imgThumbDLUri, localVivo.harvestedBy, Literal(harvesttag) ))
    imggn3 = imgg.serialize(format='n3')
    writetriplestofile(imggn3,"images")
    imgg.close()
    logger.info('Processing images done')

def processOrganizationImages():
    logger.info('Processing organization images')
    imgg = get_graph()  
    if not os.path.exists('images'):
	os.makedirs('images/fullImages')
	os.makedirs('images/thumbnails') 
    for fn in os.listdir('defaultimages/organizations/'):
	orgId = fn.split('.')[0]
	fileName = 'Organization'+ orgId +'.jpg'
	if not os.path.exists('images/fullImages/'+ fileName):
	    shutil.copyfile('defaultimages/organizations/'+fn, 'images/fullImages/'+fileName )
	    shutil.copyfile('defaultimages/organizations/'+fn, 'images/thumbnails/thumbnail'+fileName )
	imgUri = URIRef("%simageorg%s" % (app, orgId))
	orgUri = URIRef("%sorganization%s" % (app, orgId))
	imgg.add( (orgUri, public.mainImage, imgUri))
	imgThumbUri = URIRef("%sthumbimageorg%s" % (app, orgId))
	imgDLUri = URIRef("%simageorg%s" % (app, 'dl-'+orgId))
	imgThumbDLUri = URIRef("%simageorg%s" % (app, 'dlt-'+orgId))
	imgg.add ( (imgUri, public.thumbnailImage, imgThumbUri))
	imgg.add ( (imgUri, RDF.type, public.File))
	imgg.add ( (imgUri, public.downloadLocation, imgDLUri))
	imgg.add ( (imgUri, public.filename, Literal(fileName)))
	imgg.add ( (imgUri, public.mimeType, Literal('image/jpg')))
	imgg.add ( (imgDLUri,public.directDownloadUrl , Literal("/harvestedImages/fullImages/"+fileName)))
	imgg.add ( (imgDLUri,RDF.type, public.FileByteStream))
	imgg.add ( (imgDLUri,vitro.modTime, Literal(timeStamp)))
	imgg.add ( (imgThumbUri, RDF.type, public.File ))
	imgg.add ( (imgThumbUri, public.downloadLocation, imgThumbDLUri))
	imgg.add ( (imgThumbUri, public.filename, Literal('thumbnail'+fileName)))
	imgg.add ( (imgThumbUri, public.mimeType, Literal('image/jpg')))
	imgg.add ( (imgThumbDLUri,public.directDownloadUrl , Literal("/harvestedImages/thumbnails/thumbnail"+fileName)))
	imgg.add ( (imgThumbDLUri,RDF.type , public.FileByteStream))
	imgg.add ( (imgThumbDLUri,vitro.modTime , Literal(timeStamp)))
	imgg.add ( (imgUri, localVivo.harvestedBy, Literal(harvesttag) ))
	imgg.add ( (imgDLUri, localVivo.harvestedBy, Literal(harvesttag) ))
	imgg.add ( (imgThumbUri, localVivo.harvestedBy, Literal(harvesttag) ))
	imgg.add ( (imgThumbDLUri, localVivo.harvestedBy, Literal(harvesttag) ))
    imggn3 = imgg.serialize(format='n3')
    writetriplestofile(imggn3,"organizationimages")
    imgg.close()	
	
	
    logger.info('Processing organization images done')
    
def handleDepartments(department,g):
    LabelData = getTagData(department,"Naam")
    IdData = getTagData(department,"OrganisatieId")
    uri = URIRef("%sorganization%s" % (app, IdData))
    g.add( (uri, RDF.type ,tue.department) )
    g.add( (uri, RDFS.label, Literal(LabelData.encode('utf-8')) ))
    g.add( (uri, localVivo.deptId, Literal(IdData.encode('utf-8')) ))
    g.add( (uri, localVivo.harvestedBy, Literal(harvesttag) ))
    return IdData

def processDepartments():
    logger.info('Processing departments')
    deleteTriplesFile("departments")
    g = get_graph()
    property1 = client.factory.create('ns0:Property')
    property1._Naam = "Taalcode"
    property1.Waarde = "EN"
    result = client.service.VraagEnAntwoord('GeefFaculteiten',[property1])
    xmldoc = minidom.parseString(result)
    itemlist = xmldoc.getElementsByTagNameNS('*', 'Werkplek') 
    departmentList = []
    for s in itemlist :
        depid = handleDepartments(s,g)
        departmentList.append(depid)
    organizationStructure["Departments"] = departmentList
    gn3 = g.serialize(format='n3')
    writetriplestofile(gn3,"departments")
    storeList(organizationStructure,"organizationStructure")
    g.close()
    logger.info('Processing departments done')
    

def handleServices(service,g):
    LabelData = getTagData(service,"Naam")
    IdData = getTagData(service,"OrganisatieId")
    uri = URIRef("%sorganization%s" % (app, IdData))
    retid = ""
    if IdData not in organizationStructure["Departments"]:
	g.add( (uri, RDF.type ,tue.service) )
	g.add( (uri, RDFS.label, Literal(LabelData.encode('utf-8')) ))
	g.add( (uri, localVivo.deptId, Literal(IdData.encode('utf-8')) ))
	retid = IdData.encode('utf-8')
	g.add( (uri, localVivo.harvestedBy, Literal(harvesttag) ))
    return retid

def processServices():
    logger.info('Processing services')
    deleteTriplesFile("services") 
    g = get_graph()
    property1= client.factory.create('ns0:Property')
    property1._Naam = "TaalCode"
    property1.Waarde = "EN"
    result = client.service.VraagEnAntwoord('GeefWerkplekken',property1)
    xmldoc = minidom.parseString(result)
    itemlist = xmldoc.getElementsByTagNameNS('*', 'Werkplek') 
    servicesList=[]
    for s in itemlist :
   	IdData = handleServices(s,g)
        if IdData != "":
	    servicesList.append(IdData)
    organizationStructure["Services"] = servicesList
    gn3 = g.serialize(format='n3')
    writetriplestofile(gn3,"services")
    storeList(organizationStructure,"organizationStructure")
    g.close()
    logger.info('Processing services done')

def processSubOrganizations():
    logger.info('Processing suborganizations')
    deleteTriplesFile("suborganizations")
    global Counters
    Counters["Suborganizations"] = 0
    g = get_graph()
    connection = oracleConnect()
    cursor = connection.cursor()
    cursor.execute('SELECT ORG_ID,ORG_NAAM_EN,ORG_CODE_HRM, ORG_SOORT,PARENT_ID FROM EP_V_ORG_EENHEDEN')
    rows = cursor.fetchall()
    for row in rows:
	orgId = str(row[0])
	orgNaam = row[1]
	orgCode = row[2]
	orgSoort = row[3]
	orgParent = str(row[4])
	if orgParent:
	    if orgParent != orgId: #main faculty and services excluded
		Counters["Suborganizations"] +=1
		orgUri = URIRef("%sorganization%s" % (app, orgId))
		superOrgUri = URIRef("%sorganization%s" % (app, orgParent))	
		g.add( (orgUri, RDFS.label, Literal(orgNaam.encode('utf-8')) ))
		g.add( (orgUri, localVivo.deptId, Literal(orgId.encode('utf-8')) ))
		#if orgSoort == 'D': g.add( (orgUri, RDF.type ,tue.service) )
		#if orgSoort == 'F': g.add( (orgUri, RDF.type ,tue.department) )
	    	#g.add( (orgUri, RDF.type ,core.Division) )    
		g.add( (orgUri, RDF.type ,foaf.Organization) )    
		g.add( (orgUri, core.subOrganizationWithin, superOrgUri ))
		g.add( (orgUri, localVivo.harvestedBy, Literal(harvesttag) ))
    connection.close()    
    gn3 = g.serialize(format='n3')
    writetriplestofile(gn3,"suborganizations")
    g.close()
    logger.info('Processing suborganizations done')
  
def teacherType(sid):
    options = {100 : 'Teacher',
                110 : 'Co-teacher',
                120 : 'Coordinator',
                130 : 'Lab teacher',
                140 : 'Instructor',
                150 : 'Mentor',
                160 : 'Tutor',
                200 : 'Trainer',
		220 : 'Trainer',
		300 : 'Student assistant',
		400 : 'Support teacher',
		410 : 'Observer',
    }
    teacherType = None
    if sid: teacherType = options.get(int(sid))
    return teacherType    
    
    
def processEducationForStaffmembers():
    logger.info('Processing education for staff')
    deleteTriplesFile("courses")
    global Counters
    Counters["Education"] = 0
    g = get_graph()
    prevYear = ''
    StaffList_L = loadList("StaffList")
    StaffTotal = len(StaffList)    
    connection = oracleConnect()
    cursor = connection.cursor()
    cursor.execute('SELECT RELATIENR,VAKCODE,VAKNAAM_EN, URL_STUDIEWIJZER_EN,ROL_CODE FROM EP_V_VAK_VERANTW_DOCENT')
    rows = cursor.fetchall()
    for row in rows:
	eid = str(row[0])
	Vakcode = row[1]
	Vaknaam = row[2]
	VakUrl = row[3]
	Role = row[4]
	RoleWording = teacherType(int(Role))
	if eid in StaffList_L:
	    Counters["Education"] +=1
	    staffUri = URIRef("%sstaff%s" % (app, eid))
	    courseUri = URIRef("%scourse%s" % (app, Vakcode.encode('utf-8')))
	    courseStaffUri = URIRef("%scourse%s" % (app, Vakcode.encode('utf-8')+'-'+eid))
	    g.add( (courseUri, RDFS.label, Literal(Vaknaam.encode('utf-8')) ))
	    g.add( (courseUri, localVivo.harvestedBy, Literal(harvesttag) ))
	    g.add( (courseUri, RDF.type ,core.Course) )
	    g.add( (courseUri, RDF.type ,event.Event) )
	    g.add( (courseUri,core.realizedRole, courseStaffUri) )
	    if RoleWording:
		g.add( (courseStaffUri,RDFS.label, Literal(RoleWording)) )
	    else:
		g.add( (courseStaffUri,RDFS.label, Literal(Vaknaam.encode('utf-8'))) )
	    g.add( (courseStaffUri, RDF.type ,core.TeacherRole) )
	    g.add( (courseStaffUri, core.teacherRoleOf, staffUri) )
	    g.add( (courseStaffUri, localVivo.harvestedBy, Literal(harvesttag) ))
	    g.add( (courseUri, localVivo.harvestedBy, Literal(harvesttag) ))
	    g.add( (staffUri, localVivo.harvestedBy, Literal(harvesttag) ))
    connection.close()    
    gn3 = g.serialize(format='n3')
    writetriplestofile(gn3,"courses")
    g.close()
    logger.info('Processing education for staff members done')


def processPositionsForStaffmembers():
    logger.info('Processing positions for staff members')
    deleteTriplesFile("positions")
    global Counters
    Counters["Positions"] = 0
    g = get_graph()
    prevYear = ''
    StaffList_L = loadList("StaffList")
    connection = oracleConnect()
    cursor = connection.cursor()
    cursor.execute('SELECT RELATIENR, FNC_ID_EP, ORG_ID, FNC_OMS_EN, INTERN_ADRES FROM EP_MDW_AANV_ORG')  
    rows = cursor.fetchall()
    for row in rows:
	relId = str(row[0])
        functieId = row[1]
	if relId in StaffList_L and functieId: # Query with not null not working?
	    Counters["Positions"] +=1
	    deptId = str(row[2])
	    WorkplacesList[relId]=deptId
	    workTitle = str(row[3])
	    KamerNummer = str(row[4])
	    staffUri = URIRef("%sstaff%s" % (app, relId))
	    positionUri = URIRef("%sposition%s" % (app, deptId.encode('utf-8')+'-'+relId.encode('utf-8')))
	    orgUri = URIRef("%sorganization%s" % (app, deptId.encode('utf-8')))
	    g.add( (staffUri, core.personInPosition, positionUri) )
	    g.add( (staffUri, RDF.type ,staffType(functieId)) )
	    if KamerNummer: g.add( (staffUri, core.address1, Literal(KamerNummer.encode('utf-8')) )) 
	    g.add( (positionUri, RDFS.label, Literal(workTitle.encode('utf-8')) ))
	    g.add( (positionUri, RDF.type, core.Position) )
	    g.add( (positionUri, RDF.type, core.FacultyPosition) )
	    g.add( (positionUri, localVivo.positionDeptId, Literal(deptId.encode('utf-8')) ))
	    g.add( (positionUri, core.positionInOrganization, orgUri) )
	    g.add( (positionUri, core.positionForPerson, staffUri) )
	    g.add( (positionUri, localVivo.harvestedBy, Literal(harvesttag) ))
	    g.add( (staffUri, localVivo.harvestedBy, Literal(harvesttag) ))
    connection.close()    
    gn3 = g.serialize(format='n3')
    writetriplestofile(gn3,"positions")
    storeList(WorkplacesList,"WorkplacesList")
    g.close()
    logger.info('Processing positions for staff members done')

def publicationType(sid):
    options = {1 : bibo.AcademicArticle,
                2: bibo.Book,
                3 : bibo.Chapter,
                4 : bibo.EditedBook,
                5 : tue.bookReview,
                6 : tue.journalEditorship,
                8 : bibo.Report,
                9 : tue.journalContribution,
		11 : bibo.Proceedings,
		12 : tue.inauguralSpeech,
		16 : tue.audiovisualAids,
		17 : tue.software,
		18 : bibo.Website,
		19 : tue.dataset,
		20 : bibo.Thesis,
		30 : bibo.Patent,
		40 : tue.presentation,
		50 : tue.otherDocuments,
		60 : tue.relevantPositions,
		70 : core.Award,
		81 : tue.design,
		82 : tue.mediaAppearance,
		83 : tue.internetArticle		
    }
    pubType = None
    if sid: pubType = options.get(int(sid))
    if not pubType: pubType = foaf.Document
    return pubType

def ProcessPublications():
    logger.info('Processing publications')
    deleteTriplesFile("publications")
    g = get_graph()
    prevYear = ''
    global PublicationsCount
    global TuePublications
    connection = oracleConnect()
    cursor = connection.cursor()
    ResearcherList_L = loadList("ResearcherList")
    StaffList_L = loadList("StaffList")
    Query = "SELECT DISTINCT res.VOLGNR, res.CODE_OUTPUT, res.STATUS, res.VERSLAGJAAR, "
    Query = Query+"res.TITEL, res.CODE_TIJDSCHRIFT,res.VOLUME_NR,res.SERIE_NR,res.JAAR_UITGAVE, "
    Query = Query+"res.AANTAL_PAGINA,res.PAGINA_VANAF,res.PAGINA_TM,res.PLAATS_V_UITGIFTE, "
    Query = Query+"res.UITGEVER, res.ISBN_NR, res.REEKS, res.REEKS_NR, res.GEBEURTENIS, "
    Query = Query+"res.TITEL_BIJDRAGE, res.CODE_VAKGROEP, res.OPMERKING, res.JAAR_UITGAVE_BOEK, "
    Query = Query+"res.ID_NUMMER, res.EXTERNAL_ID, res.ID_REPOSITORY, tijd.NAAM_TIJDSCHRIFT, "
    Query = Query+"tijd.ISSN_NR, prod.ONDERZOEKERNR "
    Query = Query+"FROM EP_RESULTATEN_V res INNER JOIN EP_PRODUCENT_V prod ON res.VOLGNR = prod.VOLGNR "
    Query = Query+"LEFT JOIN EP_YM_TIJDSCHRIFT tijd ON res.CODE_TIJDSCHRIFT = tijd.CODE_TIJDSCHRIFT "
    Query = Query+"WHERE res.STATUS <> '4' AND res.VOLGNR <> '271480'"
    cursor.execute(Query)  
    rows = cursor.fetchall()
    for row in rows:
	OnderzoekerNr = row[27]
	if OnderzoekerNr:
	    StaffId = ResearcherList_L.get(OnderzoekerNr, None)
	    if StaffId and StaffId in StaffList_L:
		VolgNr = str(row[0])
		TuePublications.append(VolgNr)
		PubType = row[1]
		Status = row[2]
		VerslagJaar = row[3]
		Titel = row[4]
		CodeTijdschrift = row[5]
		VolumeNr = row[6]
		SerieNr = row[7]
		JaarUitgave = row[8]
		Pages = row[9]
		PagesFrom = row[10]
		PagesTil = row[11]
		PlacePub = row[12]
		Publisher = row[13]
		ISBN = row[14]
		Reeks = row[15]
		ReeksNr = row[16]
		Gebeurtenis = row[17]
		TitelBijdrage = row[18]
		CodeVakgroep = row[19]
		Remarks = row[20]
		JaarUitgaveBoek = row[21]
		IdNumber = row[22]
		DOI = row[23]
		VubisId = row[24]
		TitelTijdschrift = row[25]
		ISSNTijdschrift = row[26]
		pubUri = URIRef("%spublication%s" % (app, VolgNr.encode('utf-8')))
		PubTypeNS = publicationType(PubType)
		Value = PublicationsCount.get(str(PubTypeNS),None)
		if not Value: PublicationsCount[str(PubTypeNS)] = 0
		PublicationsCount[str(PubTypeNS)] +=1
		g.add( (pubUri, RDF.type , PubTypeNS))
		g.add( (pubUri, tue.documentNr ,Literal(VolgNr.encode('utf-8')) ))
		if Titel == None: Titel = 'No Title'
		g.add( (pubUri, RDFS.label, Literal(Titel.encode('utf-8')) ))
		if PlacePub: g.add( (pubUri, core.placeOfPublication, Literal(str(PlacePub).encode('utf-8')) ))
		if Publisher: g.add( (pubUri, core.publisher, Literal(str(Publisher).encode('utf-8')) ))
		if PagesFrom: g.add( (pubUri, bibo.pageStart, Literal(str(PagesFrom).encode('utf-8')) ))
		if PagesTil: g.add( (pubUri, bibo.pageEnd, Literal(str(PagesTil).encode('utf-8')) ))
		if Pages: g.add( (pubUri, bibo.numPages, Literal(Pages.encode('utf-8')) ))
    		if DOI: g.add( (pubUri, bibo.doi, Literal(str(DOI).encode('utf-8')) ))	
		if VolumeNr: g.add( (pubUri, bibo.volume, Literal(str(VolumeNr).encode('utf-8')) ))	
		if ReeksNr: g.add( (pubUri, bibo.issue, Literal(str(ReeksNr).encode('utf-8')) ))
		if VubisId: g.add( (pubUri, core.LinkURI, Literal(('http://repository.tue.nl/'+str(VubisId)).encode('utf-8')) ))		
		if JaarUitgave:
		    JaarUitgave = str(JaarUitgave)
		    dtvUri = URIRef("%sdtv%s" % (app, JaarUitgave.encode('utf-8')))
		    g.add( (pubUri, core.dateTimeValue, dtvUri))
		    #g.add( (dtvUri, RDF.type, owl.Thing))
		    g.add( (dtvUri, RDF.type, core.DateTimeInterval))
		    g.add( (dtvUri, core.dateTimePrecision, core.yearPrecision))
		    g.add( (dtvUri, core.dateTime, Literal(JaarUitgave+'-01-01T00:00:00') ))
		    g.add( (dtvUri, score.label, Literal(JaarUitgave.encode('utf-8'))))
		    g.add( (dtvUri, localVivo.harvestedBy, Literal(harvesttag) ))
		if Gebeurtenis:
		    Gebeurtenis = str(Gebeurtenis)
		    evtUri = URIRef("%sevent%s" % (app, VolgNr.encode('utf-8')))
		    g.add( (pubUri, event.produced_in, evtUri ))
		    g.add( (evtUri, localVivo.harvestedBy, Literal(harvesttag) ))
		    g.add( (evtUri, RDF.type, owl.Event))
		    g.add( (evtUri, RDF.type, bibo.Conference))
		    g.add( (evtUri, RDFS.label, Literal(Gebeurtenis.encode('utf-8'))))
		    g.add( (evtUri, event.product, pubUri))
		g.add( (pubUri, localVivo.harvestedBy, Literal(harvesttag) ))
		if CodeTijdschrift:
		    CodeTijdschrift = str(CodeTijdschrift)
		    pvUri =  URIRef("%spublicationvenue%s" % (app, '-journal-'+CodeTijdschrift.encode('utf-8')))
		    g.add( (pubUri, core.hasPublicationVenue, pvUri ))
		    g.add( (pvUri, RDF.type, bibo.Journal))
		    g.add( (pvUri, RDF.type, core.InformationResource ))
		    g.add( (pvUri, RDF.type, bibo.Collection ))
		    g.add( (pvUri, localVivo.harvestedBy, Literal(harvesttag) ))
		    g.add( (pvUri, RDFS.label, Literal(TitelTijdschrift.encode('utf-8')) ))
		    if ISSNTijdschrift: g.add( (pvUri, bibo.ISSN, Literal(ISSNTijdschrift.encode('utf-8')) ))
		if TitelBijdrage:
		    TaUri =  URIRef("%spublicationvenue%s" % (app, '-book-'+VolgNr.encode('utf-8')))
		    g.add( (pubUri, core.hasPublicationVenue, TaUri ))
		    g.add( (TaUri, RDF.type, bibo.Book))
		    g.add( (TaUri, RDF.type, core.InformationResource ))
		    g.add( (TaUri, RDF.type, bibo.Collection ))
		    g.add( (TaUri, localVivo.harvestedBy, Literal(harvesttag) ))
		    g.add( (TaUri, RDFS.label, Literal(TitelBijdrage.encode('utf-8')) ))
		if IdNumber: g.add( (pubUri, core.patentNumber, Literal(IdNumber) ))
    connection.close()    
    gn3 = g.serialize(format='n3')
    writetriplestofile(gn3,"publications")
    storeList(TuePublications,"TuePublications")
    g.close()
    logger.info('Processing publications done')     



def processAuthorShips():
    logger.info('Processing authorships')
    deleteTriplesFile("authorships")
    g = get_graph()
    prevYear = ''
    global Counters
    Counters["Authorships"] = 0
    connection = oracleConnect()
    cursor = connection.cursor()
    TuePublications_L = loadList("TuePublications")
    ResearcherList_L = loadList("ResearcherList")
    Query = "SELECT DISTINCT res.VOLGNR, res.STATUS, prod.ONDERZOEKERNR, "
    Query = Query+"prod.PRESENTATIENAAM_PRODUCENT,prod.RANG,ozmw.RELATIENR, "
    Query = Query+"ozmw.PRESENTATIENAAM_PROMOTOR,ozmw.NAAM,ozmw.VOORV,ozmw.VOORL, "
    Query = Query+"ozmw.TITEL FROM EP_RESULTATEN_V res INNER JOIN EP_PRODUCENT_V prod "
    Query = Query+"ON res.VOLGNR = prod.VOLGNR INNER JOIN EP_TUE_ONDERZOEKMEDEWERKER_V ozmw "
    Query = Query+"ON prod.ONDERZOEKERNR = ozmw.ONDERZOEKERNR "
    Query = Query+"WHERE res.STATUS <> '4' AND RELATIENR IS NOT null"
    cursor.execute(Query)  
    rows = cursor.fetchall()
    for row in rows:
	VolgNr = str(row[0])
	Rank = str(row[4])
	OnderzoekerNr = str(row[2])
	RelatieNr = str(row[5])
	PresNaam = str(row[3])
	if VolgNr in TuePublications_L and OnderzoekerNr in ResearcherList_L:
	    Counters["Authorships"] += 1
	    asUri = URIRef("%sauthorship%s" % (app, VolgNr.encode('utf-8')+'-'+Rank.encode('utf-8')))
	    g.add( (asUri, RDF.type, core.Authorship))
	    staffUri = URIRef("%sstaff%s" % (app, RelatieNr.encode('utf-8')))
	    g.add( (asUri, core.linkedAuthor, staffUri))
	    pubUri = URIRef("%spublication%s" % (app, VolgNr.encode('utf-8')))
	    g.add( (asUri, core.linkedInformationResource, pubUri))
	    g.add( (pubUri, dcterms.creator, staffUri))
	    g.add( (asUri, RDFS.label, Literal('Authorship for '+PresNaam.encode('utf-8'))))
	    g.add( (asUri, core.authorRank, Literal(Rank.encode('utf-8')) ))
	    g.add( (asUri, localVivo.harvestedBy, Literal(harvesttag) ))
    connection.close()    
    gn3 = g.serialize(format='n3')
    writetriplestofile(gn3,"authorships")
    g.close()
    logger.info('Processing authorships done')

def processPromotors():
    logger.info('Processing promotors')
    deleteTriplesFile("promotors")
    g = get_graph()
    prevYear = ''
    global Counters
    Counters["Promotors"] = 0
    TuePublications_L = loadList("TuePublications")
    ResearcherList_L = loadList("ResearcherList")    
    connection = oracleConnect()
    cursor = connection.cursor()
    Query = "SELECT DISTINCT promv.VOLGNR, aut.RELATIENUMMER, promv.ONDERZOEKERNR, "
    Query = Query+"promv.RANG, promv.PRESENTATIENAAM_PROMOTOR, ymprom.PROMOTOR, res.TITEL "
    Query = Query+"FROM EP_PROMOTOR_V promv INNER JOIN EP_YM_PROMOTOR ymprom "
    Query = Query+"ON ymprom.VOLGNUMMER = promv.VOLGNR AND ymprom.ONDERZOEKERNUMMER = promv.ONDERZOEKERNR "
    Query = Query+"INNER JOIN EP_RESULTATEN_V res ON promv.VOLGNR = res.VOLGNR INNER JOIN (SELECT DISTINCT ozmw2.RELATIENR AS RELATIENUMMER, "
    Query = Query+"ozmw2.ONDERZOEKERNR AS ONDERZOEKERNR FROM EP_TUE_ONDERZOEKMEDEWERKER_V ozmw2) aut "
    Query = Query+"ON promv.ONDERZOEKERNR = aut.ONDERZOEKERNR AND aut.RELATIENUMMER IS NOT NULL"
    cursor.execute(Query)  
    rows = cursor.fetchall()
    for row in rows:
	VolgNr = str(row[0])
	Rank = str(row[3])
	OnderzoekerNr = str(row[2])
	RelatieNr = str(row[1])
	PromotorNaam = str(row[4])
	PromotorRol = str(row[5])
	PresNaam = str(row[3])
	Title = str(row[6])
	if VolgNr in TuePublications_L and OnderzoekerNr in ResearcherList_L:
	    Counters["Promotors"] += 1
	    promUri = URIRef("%sadvising%s" % (app, VolgNr.encode('utf-8')+'-'+RelatieNr.encode('utf-8')))
	    g.add( (promUri, RDF.type, core.AdvisingRelationship))
	    pubUri = URIRef("%spublication%s" % (app, VolgNr.encode('utf-8')))
	    g.add( (promUri, core.advisingContributionTo, pubUri))
	    if PromotorRol == 'P':
		g.add( (promUri, RDFS.label, Literal(PromotorNaam.encode('utf-8')+' (Promotor)')))		
	    elif PromotorRol == 'C':
		g.add( (promUri, RDFS.label, Literal(PromotorNaam.encode('utf-8')+' (Copromotor)')))	    
	    else:
		g.add( (promUri, RDFS.label, Literal(PromotorNaam.encode('utf-8')+' (Unknown promotor role)')))
	    g.add( (promUri, core.rank, Literal(Rank.encode('utf-8'))))
	    staffUri = URIRef("%sstaff%s" % (app, RelatieNr.encode('utf-8')))
	    g.add( (promUri, core.advisor, staffUri))
	    g.add( (promUri, localVivo.harvestedBy, Literal(harvesttag) ))
    connection.close()    
    gn3 = g.serialize(format='n3')
    writetriplestofile(gn3,"promotors")
    g.close()
    logger.info('Processing promotors done')

def loadModel(name):
    loadedModel = FileManager.get().loadModel("file:data/"+name+".n3");
    logger.info('Loading data/%s.n3 into Vivo',name)
    model.begin()
    model.add(loadedModel)
    model.commit()
    logger.info('Loading data/%s.n3 done',name)
        
def doQuery(queryString):
    tmpArray = []
    query = QueryFactory.create(queryString)
    #qexec = QueryExecutionFactory.create(query, model)
    qexec = QueryExecutionFactory.sparqlService("http://vivo.libr.tue.nl:3030/VIVO/query", query);
    results = qexec.execSelect()
    while results.hasNext():
	soln = results.nextSolution()
	r = soln.getResource("?s")
	tmpArray.append(r.getURI())
    qexec.close()
    return tmpArray    
    
def removeType(what):
    logger.info('Removing data type: %s',what)
    queryString = ""
    if what == "Organization":
	queryString = "SELECT ?s WHERE { ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://xmlns.com/foaf/0.1/Organization>}"
    if what == "Expertise":
	queryString = "SELECT ?s WHERE { ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2004/02/skos/core#Concept>}"
    if what == "Staff":
	queryString = "SELECT ?s WHERE { ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vivo.libr.tue.nl/ontology/tue#tueIndividual>}"
    if what == "All":
	queryString = "SELECT ?s WHERE { ?s <http://vivo.libr.tue.nl/ontology/harvestedBy> '"+harvesttag+"'}"
    if what == "Images":
	queryString = "SELECT ?s WHERE {{ ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vitro.mannlib.cornell.edu/ns/vitro/public#File>} UNION { ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vitro.mannlib.cornell.edu/ns/vitro/public#FileByteStream>}}"
    removeArray = doQuery(queryString)
    model.begin()
    for uri in removeArray:
	res = model.createResource(uri)
	model.removeAll(res,None,None)
    model.commit()


def doStats():
    global Counters
    Counters["NoWorkPlace"] = 0
    StaffList_L = loadList("StaffList")
    WorkplacesList_L = loadList("WorkplacesList")
    organizationStructure_L = loadList("organizationStructure")
    for Person in StaffList_L:
	workPlace = WorkplacesList_L.get(Person, None)
	if not workPlace: Counters["NoWorkPlace"] +=1
    logger.info('Total departments count: %s',len(organizationStructure_L["Departments"]))	
    logger.info('Total services count: %s',len(organizationStructure_L["Services"]))	
    logger.info('Total suborganizations count: %s',Counters["Suborganizations"])	
    logger.info('Total staff count: %s',len(StaffList_L))
    logger.info('Total expertise at added to staffcount: %s',Counters["ExpertiseAtStaff"])
    for DocType in PublicationsCount:
	logger.info('Document type %s added: %s',DocType, PublicationsCount[DocType])
    for counter in Counters:
	logger.info('%s added: %s',counter, Counters[counter])
    

removeType("All")
#removeType("Images")
#removeType("Organization")
loadModels = True # set to False if you want to examine n3 files only

# Expertises
processExpertises()
if loadModels: loadModel("expertises")

# Organization structure
processDepartments()
processServices()
processSubOrganizations()
processOrganizationImages()
if loadModels: loadModel("departments")
if loadModels: loadModel("services")
if loadModels: loadModel("suborganizations")
if loadModels: loadModel("organizationimages")


# Staff data
processStaffIds()
processStaffDetails()
processImages()
if loadModels: loadModel("staffdetails")
if loadModels: loadModel("webpages")
if loadModels: loadModel("images")

# Staff expertise
processExpertisesForStaffmembers()
if loadModels: loadModel("staffexpertise")

# Staff education
processEducationForStaffmembers()
if loadModels: loadModel("courses")

# Staff positions
processPositionsForStaffmembers()
if loadModels: loadModel("positions")

# Publications
ProcessPublications()
if loadModels: loadModel("publications")

# Authorships
processAuthorShips()
if loadModels: loadModel("authorships")

# Promotors
processPromotors()
if loadModels: loadModel("promotors")

copyImages()

#close model and connection
model.close()
store.close()
conn.close()

#Log stats
doStats()








