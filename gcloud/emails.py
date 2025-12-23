import gcloud
import PureCloudPlatformClientV2
from functools import cache

import utils.console as console

from . import helpers
from . import client
from . import queues
from . import flows

from pprint import pprint
import functools


def getRoutingApi():
    return PureCloudPlatformClientV2.RoutingApi(client.gApiClient)

def getAllEmailDomains():
    allEntities = dict()

    api_response = getRoutingApi().get_routing_email_domains()
    pprint(api_response)
    console.info('Read %s entites' % len(api_response.entities))
    for entity in api_response.entities:
        allEntities[entity.id] = entity
        
    console.info('Read total %s entities' % len(allEntities))
    return allEntities

def getAllEmailDomainRoutes(a_domain_name, nPageSize = 200):
    allEntities = dict()

    nPageNumber = 1
    nPageCount = 1
    while nPageNumber <= nPageCount:
        api_response = getRoutingApi().get_routing_email_domain_routes(domain_name=a_domain_name, page_size=nPageSize, page_number=nPageNumber)
        console.info('Read %s entites' % len(api_response.entities))
        for entity in api_response.entities:
            allEntities[entity.pattern] = entity
            
        nPageCount = api_response.page_count
        nPageNumber += 1
        
    console.info('Read total %s entities' % len(allEntities))
    return allEntities

def getEmailDomainRouteByName(a_domain_name, a_pattern):
    entity = None

    api_response = getRoutingApi().get_routing_email_domain_routes(domain_name=a_domain_name, pattern=a_pattern)
    if api_response.total == 1:
        entity = api_response.entities[0]
    elif api_response.total > 1:
        for e in api_response.entities:
            if e.pattern == a_pattern:
                entity = e
                break
    
    return entity

def resolveEmailDomainRoute(domain_name, route):
    resolved_route = None

    if not route.id:
        if route.pattern:
            resolved_route = getEmailDomainRouteByName(domain_name, route.pattern)
            if resolved_route is not None:
                route.id = resolved_route.id
            else:
                raise ValueError("Email domain route %s@%s not found" % (domain_name, route.pattern))

        else:
            raise ValueError("No route id or pattern defined")

    return route

def createEmailDomainRoute(domain_name, route, bUpdate = False):
    # Resolve the queue
    if route.queue is not None:
        route.queue = queues.resolveQueue(route.queue)

    # Resolve the flow
    if route.flow is not None:
        route.flow = flows.resolveFlow(route.flow)

    # Resolve the spam_flow
    if route.spam_flow is not None:
        route.spam_flow = flows.resolveFlow(route.spam_flow)

    # Resovle reply address
    if route.reply_email_address is not None:
        if route.reply_email_address.route is not None:
            resolved_route = getEmailDomainRouteByName(route.reply_email_address.domain.id, route.reply_email_address.route.pattern)
            if resolved_route is not None:
                route.reply_email_address.route.id = resolved_route.id
            else:
                createEmailDomainRoute(route.reply_email_address.domain.id, route.reply_email_address.route)
                route.reply_email_address.route = resolveEmailDomainRoute(route.reply_email_address.domain.id, route.reply_email_address.route)

    # Check if route already exists
    existing_route = getEmailDomainRouteByName(domain_name, route.pattern)

    if existing_route is None:
        # Create
        getRoutingApi().post_routing_email_domain_routes(domain_name, route)
        console.ok('Created e-mail domain route [%s@%s]' % (route.pattern, domain_name))

    elif bUpdate:
        # Update
        # route.id = existing_route.id
        getRoutingApi().put_routing_email_domain_route(domain_name, existing_route.id, route)
        console.ok('Updated e-mail domain route [%s@%s]' % (route.pattern, domain_name))

    else:
        console.info('E-Mail domain route [%s@%s] already exists. Skipping...' % (route.pattern, domain_name))