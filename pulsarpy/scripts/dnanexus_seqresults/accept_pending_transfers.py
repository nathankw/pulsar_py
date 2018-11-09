#!/usr/bin/env python3

###
#Nathaniel Watson
#Stanford School of Medicine
#Nov. 6, 2018
#nathankw@stanford.edu
###

"""
Accepts DNAnexus projects pending transfer to the ENCODE org, then downloads each of the projects to the 
local host at the designated output directory. In DNAnexus, a project property will be added to the 
project; this property is 'scHub' and will be set to True to indicate that the project was 
downloaded to the SCHub pod. Project downloading is handled by the script download_cirm_dx-project.py,
which sends out notification emails as specified in the configuration file {} in both successful 
and unsuccessful circomstances.".format(conf_file). See more details at 
https://docs.google.com/document/d/1ykBa2D7kCihzIdixiOFJiSSLqhISSlqiKGMurpW5A6s/edit?usp=sharing 
and https://docs.google.com/a/stanford.edu/document/d/1AxEqCr4dWyEPBfp2r8SMtz8YE_tTTme730LsT_3URdY/edit?usp=sharing.
"""

import os
import sys
import subprocess
import logging
import argparse
import json

import dxpy

import pulsarpy.models
import scgpm_seqresults_dnanexus.dnanexus_utils as du


#The environment module gbsc/gbsc_dnanexus/current should also be loaded in order to log into DNAnexus

ENCODE_ORG = "org-snyder_encode"


def get_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    return parser

def main():
    get_parser()
    #parser.parse_args()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:   %(message)s')
    chandler = logging.StreamHandler(sys.stdout)
    chandler.setLevel(logging.DEBUG)
    chandler.setFormatter(formatter)
    logger.addHandler(chandler)
    
    # Add debug file handler
    fhandler = logging.FileHandler(filename="log_debug_dx-seq-import.txt",mode="a")
    fhandler.setLevel(logging.DEBUG)
    fhandler.setFormatter(formatter)
    logger.addHandler(fhandler)

    # Add error file handler
    err_h = logging.FileHandler(filename="log_error_dx-seq-import.txt" ,mode="a")
    err_h.setLevel(logging.ERROR)
    err_h.setFormatter(formatter)
    logger.addHandler(err_h)

    #accept pending transfers
    transferred = du.accept_project_transfers(dx_username=DX_USER,access_level="ADMINISTER",queue="ENCODE",org=ENCODE_ORG,share_with_org="CONTRIBUTE")
    #transferred is a dict. identifying the projects that were transferred to the specified billing account. Keys are the project IDs, and values are the project names.
    logger.debug("The following projects were transferred to {org}:".format(org=ENCODE_ORG))
    logger.debug(transferred)
    
    if not transferred: #will be an empty dict otherwise.
        return
    transferred_proj_ids = transferred.keys()
    for t in transferred_proj_ids:
        dxres = du.DxSeqResults(dx_project_id=t)
        proj_props = dxres.dx_project.describe(input_params={"properties": True})["properties"]
        library_name = proj_props["library_name"]
        # First search by name, then by ID if the former fails.
        # Lab members submit a name by the name of SREQ-ID, where SREQ is Pulsar's 
        # abbreviation for the SequencingRequest model, and ID is the database ID of a
        # SequencingRequest record. This gets stored into the library_name property of the 
        # corresponding DNanexus project. Problematically, this was also done in the same way when
        # we were on Syapse, and we have backported some Sypase sequencing requests into Pulsar. Such
        # SequencingRequests have been given the name as submitted in Syapse times, and this is
        # evident when the SequencingRequest's ID is different from the ID in the SREQ-ID part. 
        # Find pulsar SequencingRequest with library_name
        sreq = ppy_models.SequencingRequest(library_name})
        if not sreq:
            # Search by ID. The lab sometimes doen't add a value for SequencingRequest.name.
            sreq = ppy_models.SequencingRequest(library_name.split("-")[1])
        if not sreq:
            logger.debug("Can't find Pulsar SequencingRequest for DNAnexus project {} ({}).".format(t, dxres.name))
            continue
        # Check if there is a SequencingRun object for this already
        srun = models.SequencingRun(...)
        if not srun:
            # Create SequencingRun
            srun_json = create_srun(sreq, dxres)
            srun = models.SequencingRun(srun_json["id"])
        # Check if DataStorage is aleady linked to SequencingRun object. May be if user created it
        # manually in the past. 
        if not srun.data_storage_id:
            ds_json = create_data_storage(srun, dxres)
        if srun.status != "finished":
            srun.patch({"status": "finished"})

def create_srun(sreq, dxres):
    """
    Creates a SequencingRun record to be linked to the given SequencingResult object. 
    """
    payload = {}
    payload["name"] = proj_props["seq_run_name"]
    payload["sequencing_request_id"] = sreq.id
    # 'status' is a required attribute. Set initially to 'started'; it will be set to finished
    # a step later when creating the associated DataStorage record.
    return models.SequencingRun.post(payload)
        
def create_data_storage(srun, dxres):
    """
    Creates a DataStorage record for the given SequencingRun record based on the given DNAnexus 
    sequencing results. After the DataStorage record is created, a few attribuets of the SequencingRun
    object will then be set:

        1. `SequencingRun.data_storage_id`: Link to newly creatd DataStroage record.
        2. `SequencingRun.lane`: Set to the value of the DNAnexus project property "seq_lane_index". 
        3. `SequencingRun.status`: Set to "finished". 


     Note that I would also like to try and set the attributes `SequencingRun.forward_read_len` and
     `SequencingRun.reverse_read_len`, however, I can't obtain these results from DNAnexus based on
     the existing metadata that's sent there via GSSC. 

    key in the SequeningRun record. 

    Args: 
        srun - A `pulsarpy.models.SequencingRun` instance whose `data_storage_id` foreign key 
               should be associated with the newly created DataStorage.
        dxres - `scgpm_seqresults_dnanexus.dnanexus_utils.du.DxSeqResults()` instance that contains
               sequencing results metadata in DNAnexus for the given srun. 
    
    Returns:
        `dict`. The response from the server containing the JSON serialization of the new 
            DataStorage record. 
    """
    payload = {}
    payload["name"] = dxres.dx_project_name
    payload["project_identifier"] = dxres.dx_project_id
    payload["data_storage_provider_id"] = models.DataStorage("DNAnexus")["id"]
    # Create DataStorage
    res_json = models.DataStorage.post(ds_payload)
    # Udate srun's data_storage_id fkey:
    srun.patch({"data_storage_id": res_json["id"], "lane": dxres.dx_project_props["seq_lane_index"]})
    return res_json

if __name__ == "__main__":
    main()