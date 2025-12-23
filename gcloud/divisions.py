from ast import Nonlocal
import gcloud
import PureCloudPlatformClientV2

import utils.console as console

from . import helpers
from . import client

allDivisionsCache = None

def getAuthorizationApi():
    return PureCloudPlatformClientV2.AuthorizationApi(client.gApiClient)

def getAllDivisions():
    return helpers.getAll(getAuthorizationApi().get_authorization_divisions)

def getDivisionByName(name):
    return helpers.getByName(getAuthorizationApi().get_authorization_divisions)

"""def getDivisionByName(name):

    # Otherwise we read from GCloud
    api_response = getAuthorizationApi().get_authorization_divisions(name=name)
    
    if api_response.total == 1:
        division = api_response.entities[0]

    elif api_response.total > 1:
        for e in api_response.entities:
            if e.name == name:
                division = e
                break

    if division is None: console.fail('Division %s not found' % name)
    return division"""

def resolveDivision(division, use_cache=True):
    resolved_division = None

    if not division.id:
        if division.name:

            if use_cache:
                global allDivisionsCache
                if allDivisionsCache is None:
                    allDivisionsCache = getAllDivisions()

                if division.name in allDivisionsCache:
                    resolved_division = allDivisionsCache[division.name]
            
            if resolved_division is None:
                resolved_division = getDivisionByName(division.name)
                if use_cache:
                    allDivisionsCache[resolved_division.name] = resolved_division
            
            if resolved_division is None:
                raise ValueError("No such division [%s]" % division.name)

            division.id = resolved_division.id

        else:
            raise ValueError("No division id or name defined")

    return division