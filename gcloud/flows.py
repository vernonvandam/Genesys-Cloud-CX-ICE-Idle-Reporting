import gcloud
import PureCloudPlatformClientV2

import utils.console as console

from . import helpers
from . import client

# name -> Flow cache used to optimise resolutions
allFlowsCache = dict()

def getArchitectApi():
    return PureCloudPlatformClientV2.ArchitectApi(client.gApiClient)

def getAllFlows():
    global allFlowsCache

    allFlowsCache = helpers.getAll(getArchitectApi().get_flows)
    return allFlowsCache

def getFlowByName(name):
    global allFlowsCache

    flow = helpers.getByName(getArchitectApi().get_flows, name)
    if allFlowsCache and flow is not None:
        allFlowsCache[name] = flow
    return flow

def resolveFlow(flow, use_cache=True):
    global allFlowsCache
    resolved_flow = None

    if not flow.id:
        if flow.name:
            if use_cache:
                if flow.name in allFlowsCache:
                    resolved_flow = allFlowsCache[flow.name]
            
            if resolved_flow is None:     
                resolved_flow = getFlowByName(flow.name)

            if resolved_flow is not None:
                flow.id = resolved_flow.id
            else:
                raise ValueError("Flow %s not found" % flow.name)

        else:
            raise ValueError("No flow id or name defined")

    return flow