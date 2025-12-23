import gcloud
import PureCloudPlatformClientV2
from functools import cache

import utils.console as console

from . import helpers
from . import client
from . import divisions

def getArchitectApi():
    return PureCloudPlatformClientV2.ArchitectApi(client.gApiClient)

def getAllIVRs():
    return helpers.getAll(getArchitectApi().get_architect_ivrs)

def getIVRByName(name):
    return helpers.getByName(getArchitectApi().get_architect_ivrs, name)

def createIVR(ivr, bUpdate = False):
    
    # Resolve the division
    ivr.division = divisions.resolveDivision(ivr.division)

    # Check if queue already exists
    existingIVR = getIVRByName(ivr.name)

    if existingIVR is None:
        # Set name for new queue
        getArchitectApi().post_architect_ivrs(ivr)
        console.ok('Created IVR [%s]' % ivr.name)

    elif bUpdate:
        # Set id for queue to update
        ivr.id = existingIVR.id
        getArchitectApi().put_architect_ivr(ivr.id, ivr)
        console.ok('Updated IVR [%s]' % ivr.name)

    else:
        console.info('IVR [%s] already exists. Skipping...' % ivr.name)