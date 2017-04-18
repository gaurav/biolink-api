"""
Factory class for generating ontology objects based on a variety of handle types
"""

import networkx as nx
import logging
import ontobio.obograph_util as obograph_util
import ontobio.sparql.sparql_ontology
from ontobio.ontol import Ontology
from ontobio.sparql.sparql_ontology import EagerRemoteSparqlOntology
import os
import subprocess
import hashlib
from cachier import cachier
import datetime

SHELF_LIFE = datetime.timedelta(days=3)

# TODO
default_ontology_handle = 'cache/ontologies/pato.json'
#if not os.path.isfile(ontology_handle):
#    ontology_handle = None

global default_ontology
default_ontology = None


class OntologyFactory():
    """
    Creates an ontology
    """

    # class variable - reuse the same object throughout
    test = 0
    
    def __init__(self, handle=None):
        """
        initializes based on an ontology name
        """
        self.handle = handle

    def create(self, handle=None):
        """
        Creates an ontology based on a handle

         - FILENAME.json : creates an ontology from an obographs json file
         - obo:ONTID     : E.g. obo:pato - creates an ontology from obolibrary PURL (requires owltools)
         - ONTID         : E.g. 'pato' - creates an ontology from a remote SPARQL query

        """
        if handle == None:
            self.test = self.test+1
            logging.info("T: "+str(self.test))                
            global default_ontology
            if default_ontology == None:
                logging.info("Creating new instance of default ontology")
                default_ontology = create_ontology(default_ontology_handle)
            logging.info("Using default_ontology")                
            return default_ontology
        return create_ontology(handle)
    
#@cachier(stale_after=SHELF_LIFE)
def create_ontology(handle=None):
    ont = None
    logging.info("Determining strategy to load '{}' into memory...".format(handle))
    
    if handle.find(".") > 0 and os.path.isfile(handle):
        logging.info("Fetching obograph-json file from filesystem")
        g = translate_file(handle)
        ont = Ontology(handle=handle, payload=g)
    elif handle.startswith("obo:"):
        logging.info("Fetching from OBO PURL")
        if handle.find(".") == -1:
            handle += '.owl'
        fn = '/tmp/'+handle
        if not os.path.isfile(fn):
            url = handle.replace("obo:","http://purl.obolibrary.org/obo/")
            cmd = ['owltools',url,'-o','-f','json',fn]
            cp = subprocess.run(cmd, check=True)
            logging.info(cp)
        else:
            logging.info("using cached file: "+fn)
        g = obograph_util.convert_json_file(fn)
        ont = Ontology(handle=handle, payload=g)
    elif handle.startswith("http:"):
        logging.info("Fetching from Web PURL: "+handle)
        encoded = hashlib.sha256(handle.encode()).hexdigest()
        #encoded = binascii.hexlify(bytes(handle, 'utf-8'))
        #base64.b64encode(bytes(handle, 'utf-8'))
        logging.info(" encoded: "+str(encoded))
        fn = '/tmp/'+encoded
        if not os.path.isfile(fn):
            cmd = ['owltools',handle,'-o','-f','json',fn]
            cp = subprocess.run(cmd, check=True)
            logging.info(cp)
        else:
            logging.info("using cached file: "+fn)
        g = obograph_util.convert_json_file(fn)
        ont = Ontology(handle=handle, payload=g)
    else:
        logging.info("Fetching from SPARQL")
        ont = EagerRemoteSparqlOntology(handle=handle)
        #g = get_digraph(handle, None, True)
    return ont

def translate_file(handle, **args):
    if handle.endswith(".json"):
        return obograph_util.convert_json_file(handle, **args)
    else:
        if not (handle.endswith(".obo") or handle.endswith(".owl")):
            logging.info("Attempting to parse non obo or owl file with owltools: "+handle)
        encoded = hashlib.sha256(handle.encode()).hexdigest()
        logging.info(" encoded: "+str(encoded))
        fn = '/tmp/'+encoded
        if not os.path.isfile(fn):
            cmd = ['owltools',handle,'-o','-f','json',fn]
            cp = subprocess.run(cmd, check=True)
            logging.info(cp)
        else:
            logging.info("using cached file: "+fn)
        return obograph_util.convert_json_file(fn, **args)
    
