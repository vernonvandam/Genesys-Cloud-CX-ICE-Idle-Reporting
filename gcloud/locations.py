import PureCloudPlatformClientV2
from PureCloudPlatformClientV2.rest import ApiException

import utils.console as console

from . import client
from . import helpers

# id -> Location cache used to optimise resolutions
allLocationsCache = None

def getLocationsApi():
    return PureCloudPlatformClientV2.LocationsApi(client.gApiClient)

def getAllLocations():
    """
        Returns a dictionary of all Location objects preent in the cloud.
        The method is used to pre-load a cache which can be used to optimise resolutions
    """
    global allLocationsCache

    allLocationsCache = helpers.getAllById(getLocationsApi().get_locations, nPageSize = 100)
    return allLocationsCache

def getLocationByName(name):
    """
        Returns a single Location object referenced by name
        This method updates a cache which can be used to optimise resolutions
    """
    global allLocationsCache

    location = helpers.getByName(getLocationsApi().get_locations, name)
    if allLocationsCache and location is not None:
        allLocationsCache[name] = location
    return location



def resolveLocation(location, use_cache=True):
    resolved_location = None

    if not location.id:
        if location.name:
            if use_cache:
                global allLocationsCache
                if allLocationsCache is None:
                    allLocationsCache = getAllLocations()

                if location.name in allLocationsCache:
                    resolved_location = allLocationsCache[location.name]
            
            if resolved_location is None:     
                resolved_location = getLocationByName(location.name)
                if use_cache:
                    allLocationsCache[resolved_location.name] = resolved_location

            if resolved_location is None:
                raise ValueError("No such location [%s]" % location.name)

            location.id = resolved_location.id
            location.name = None    # Remove name to allow user updates to be processed

        else:
            raise ValueError("No location id or name defined")

    return location