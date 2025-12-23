import gcloud
import PureCloudPlatformClientV2

import time
import utils.console as console
import urllib.request

import webbrowser

from . import helpers
from . import client

from pprint import pprint

# name -> datatable cache used to optimise resolutions
allDataTablesCache = None

def getArchitectApi():
    return PureCloudPlatformClientV2.ArchitectApi(client.gApiClient)

def getAllDataTables():
    """
        Returns a dictionary of all Table objects preent in the cloud.
        The method is used to pre-load a cache which can be used to optimise resolutions
    """
    global allDataTablesCache

    allDataTablesCache = helpers.getAll(getArchitectApi().get_flows_datatables, nPageSize = 100)
    return allDataTablesCache

def getDataTableByName(name):
    """
        Returns a single Queue object referenced by name
        This method updates a cache which can be used to optimise resolutions
    """
    global allDataTablesCache

    datatable = helpers.getByName(getArchitectApi().get_flows_datatables, name)
    if allDataTablesCache and datatable is not None:
        allDataTablesCache[name] = datatable
    return datatable

def getDataTableSchema(id):
    result = getArchitectApi().get_flows_datatable(datatable_id=id, expand='schema')
    return result.schema

def updateDataTableSchema(id, schema):
    result = getArchitectApi().put_flows_datatable(id, schema)
    return result

def exportDataTableRows(id, filename, timeout = 30):
    """
    Function to export the rows of a data table to a file
    """
    job = getArchitectApi().post_flows_datatable_export_jobs(id)
    start_time = time.time()

    # Poll for completion of the export job
    while job.status == "Processing":
        now = time.time()
        if (now - start_time) > timeout:
            raise TimeoutError()

        time.sleep(1)
        job = getArchitectApi().get_flows_datatable_export_job(id, job.id)

    if job.status != "Succeeded":
        raise RuntimeError("Export job completed with status %s" & job.status)

    # Save URL to file
    webbrowser.open(job.download_uri)

#    with urllib.request.urlopen(job.download_uri) as source:
#        with open(filename, "w", encoding = 'utf-8', buffering = True) as dest:
#            bytes = ""
#            while not bytes:
#                bytes = source.read(4096).decode('utf-8')
#                dest.write(bytes)

    return

