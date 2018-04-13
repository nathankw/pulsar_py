# -*- coding: utf-8 -*-                                                                                
                                                                                                       
###Author                                                                                              
#Nathaniel Watson                                                                                      
#2017-09-18                                                                                            
#nathankw@stanford.edu                                                                                 
###                                                                                                    

import json
import pdb
import re

import encode_utils.connection as euc
import encode_utils.utils as euu
import pulsarpy.models as models
import pulsarpy.utils

protocol_regx = re.compile(r'protocol', re.IGNORECASE)

UPSTREAM_PROP = "upstream_identifier"
ENC_CONN = euc.Connection("prod")


def biosample_term_name(biosample_term_name, biosample_term_id):
    """
    On the ENCODE Portal, a biosample record has a biosample_term_name property and a biosample_term_id
    property. These two properties in Pulsar fall under the BiosampleTermName model with names
    'biosample_term_name' and 'accession', respectivly. 
    There isn't a corresponding model for BiosampleTermName on the ENCODE Portal, and to be able to 
    determine whether Pulsar already has the provided biosample_term_name, a lookup in Pulsar will
    be done to try and match up the provided biosample_term_id with BiosampleTermName.accession.

    Args:
        biosample_term_id: `str`. The value of a biosample's 'biosample_term_id' property on the Portal. 
        biosample_term_name: `str`. The value of a biosample's 'biosample_term_name' property on the Portal. 
    """
    payload = {}
    payload["name"] = biosample_term_name
    payload["accession"] = biosample_term_id
    pulsar_rec = models.BiosampleTermName.find_by({"accession": biosample_term_id})
    if pulsar_rec:
        return pulsar_rec
    return models.BiosampleTermName.post(payload)

def document(rec_id): 
    """
    Example document: https://www.encodeproject.org/documents/716003cd-3ce7-41ce-b1e3-6f203b6632a0/?format=json

    Args:
        rec_id: `str`. An identifier for a document record on the ENCODE Portal. 
    """
    raise Exception("Due to a bug in the ENCODE Portal, can't fetch document '{}' via the REST API.".format(rec))
    rec = ENC_CONN.get(rec_id, ignore404=False)
    aliases = rec["aliases"]
    if aliases:
        upstream_identifier = aliases[0]
    else:
        upstream_identifier = rec["uuid"]
    payload = {}
    payload["description"] = rec["description"]
    payload[UPSTREAM_PROP] = upstream_identifier
    document_type = rec["document_type"]
    # Determine whether this is a protocol document and set Document.is_protocol accordingly. 
    protocol = False
    if protocol_regx.search(document_type):
        protocol = True
    payload["is_protocol"] = protocol

def treatment(rec_id):
    """
    The required properties in the ENCODE Portal are:
    
    1. treatment_term_name, 
    2. treatment_type. 

    Args:
        rec_id: `str`. An identifier (alias or uuid) for a treatment record on the ENCODE Portal. 

    Example on the Portal: https://www.encodeproject.org/treatments/933a1ff2-43a2-4a54-9c87-aad228d0033e/.
    """
    rec = ENC_CONN.get(rec_id, ignore404=False)
    payload = {}
    #check if upstream exists already in Pulsar:
    upstream = rec["aliases"][0]
    pulsar_rec = models.Treatment.find_by({UPSTREAM_PROP: upstream})
    if pulsar_rec:
        return pulsar_rec 

    documents = rec["documents"]
    # Add any linked documents that aren't in Pulsar already:
    for doc in documents:
        document(doc)
    payload[UPSTREAM_PROP] = upstream
    payload["concentration"] = rec["amount"]
    amount_units = rec["amount_units"]
    pulsar_amount_units_rec = models.ConcentrationUnit.find_by(payload={"name": amount_units})
    if not pulsar_amount_units_rec:
        raise Exception("ConcentrationUnit '{}' couldn't be found.".format(amount_units))
    pulsar_amount_units_rec = pulsar_amount_units_rec["concentration_unit"]
    payload["concentration_unit_id"] = pulsar_amount_units_rec["id"]
    payload["duration"] = rec["duration"]
    payload["duration_units"] = rec["duration_units"]
    temp_prop_name = "temperature"
    if temp_prop_name  in rec:
        temp = rec[temp_prop_name]
        temp_units = rec["temperature_units"]
        if temp_units == "Kelvin":
            temp = pulsarpy.utils.kelvin_to_celsius(temp)
        elif temp_units == "Fahrenheit":
            temp = pulsarpy.utils.fahrenheit_to_celsius(temp)
        payload[temp_prop_name] = rec[temp_prop_name]
    ttn = rec["treatment_term_name"]
    tti = rec["treatment_term_id"]
    #Create new TreatmentTermName if not found in Pulsar.
    pulsar_ttn_rec = treatment_term_name(ttn, tti)["treatment_term_name"]
    payload["treatment_term_name_id"] = pulsar_ttn_rec["id"]
    payload["treatment_type"] = rec["treatment_type"]
    #The Portal's treatment model doesn't include a name prop or a description prop. 
    # Thus, 'name' shall be set to be equal to 'upstream_identifier'.
    payload["name"] = euu.strip_alias_prefix(upstream)
    return models.Treatment.post(payload)

def treatment_term_name(treatment_term_name, treatment_term_id):
    """
    On the ENCODE Portal, a treatment record has a treatment_term_name property and a treatment_term_id
    property. These two properties in Pulsar fall under the TreatmentTermName model with names
    'treatment_term_name' and 'accession', respectivly. 

    There isn't a corresponding model for TreatmentTermName on the ENCODE Portal, and to be able to 
    determine whether Pulsar already has the provided treatment_term_name, a lookup in Pulsar will
    be done to try and match up the provided treatment_term_id with TreatmentTermName.accession.

    Args:
        treatment_term_id: `str`. The value of a treatment's 'treatment_term_id' property on the Portal. 
        treatment_term_name: `str`. The value of a treatment's 'treatment_term_name' property on the Portal. 
    """
    payload = {}
    payload["name"] = treatment_term_name
    payload["accession"] = treatment_term_id
    pulsar_rec = models.TreatmentTermName.find_by({"accession": treatment_term_id})
    if pulsar_rec:
        return pulsar_rec
    return models.TreatmentTermName.post(payload)
    
    
