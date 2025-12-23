import gcloud
import PureCloudPlatformClientV2

import utils.console as console

from . import helpers
from . import client
from . import divisions
from . import flows
from . import scripts
from . import emails

from pprint import pprint

# name -> queue cache used to optimise resolutions
allQueuesCache = None

def getRoutingApi():
    return PureCloudPlatformClientV2.RoutingApi(client.gApiClient)

def getAllQueues():
    """
        Returns a dictionary of all Queue objects preent in the cloud.
        The method is used to pre-load a cache which can be used to optimise resolutions
    """
    global allQueuesCache

    allQueuesCache = helpers.getAll(getRoutingApi().get_routing_queues, nPageSize = 100)
    return allQueuesCache

def getQueueByName(name):
    """
        Returns a single Queue object referenced by name
        This method updates a cache which can be used to optimise resolutions
    """
    global allQueuesCache

    Queue = helpers.getByName(getRoutingApi().get_routing_queues, name)
    if allQueuesCache and Queue is not None:
        allQueuesCache[name] = Queue
    return Queue

def getQueueMembers(queue):
    """
    Returns the list of users who are members of this queue
    """
    #TODO: Fix this to support pagination
    api_response =  getRoutingApi().get_routing_queue_members(queue.id, page_size=500)
    return api_response.entities

def addQueueMembers(queue, members):
    api_response = getRoutingApi().post_routing_queue_members(queue.id, members)

def resolveQueue(queue, use_cache=True):
    global allQueuesCache
    resolved_queue = None

    if not queue.id:
        if queue.name:
            if use_cache:
                if queue.name in allQueuesCache:
                    resolved_queue = allQueuesCache[queue.name]
            
            if resolved_queue is None:     
                resolved_queue = getQueueByName(queue.name)

            if resolved_queue is not None:
                queue.id = resolved_queue.id
            else:
                raise ValueError("Queue %s not found" % queue.name)

        else:
            raise ValueError("No Queue id or name defined")

    return queue

def createQueue(queue, bUpdate = False):

    # Resolve division
    if queue.division is not None:
        queue.division = divisions.resolveDivision(queue.division)
    else:
        raise ValueError("No division defined")

    # Resolve the voice in-queue flow
    if queue.queue_flow is not None:
        queue.queue_flow = flows.resolveFlow(queue.queue_flow)

    # Resolve the scripts
    if queue.default_scripts is not None:
        for channel in ["CALL", "EMAIL", "CHAT"]:
            script = queue.default_scripts.get(channel)
            if script is not None:
                resolved_script = scripts.resolveScript(script)
                                
            queue.default_scripts[channel] = script 

    # Resolve the outbound email address
    if queue.outbound_email_address is not None:
        emails.resolveEmailDomainRoute(queue.outbound_email_address.domain.id, queue.outbound_email_address.route)

    # Check if queue already exists
    existing_queue = getQueueByName(queue.name)

    if existing_queue is None:
        # Create
        getRoutingApi().post_routing_queues(queue)
        console.ok('Created queue [%s]' % queue.name)

    elif bUpdate:
        # Update
        getRoutingApi().put_routing_queue(existing_queue.id, queue)
        console.ok('Updated queue [%s]' % queue.name)

    else:
        console.info('Queue [%s] already exists. Skipping...' % queue.name)