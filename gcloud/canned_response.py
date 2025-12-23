import gcloud
import PureCloudPlatformClientV2
from PureCloudPlatformClientV2.rest import ApiException

import utils.console as console

from . import helpers
from . import client

# name -> Lirbary cache used to optimise resolutions by resolveCannedResponse
allLibrariesCache = dict()

def getResponseManagementApi():
    return PureCloudPlatformClientV2.ResponseManagementApi(client.gApiClient)

def getAllLibraries():
    global allLibrariesCache

    allLibrariesCache = helpers.getAll(getResponseManagementApi().get_responsemanagement_libraries)
    return allLibrariesCache

def getLibraryByName(name):
    global allLibrariesCache

    if allLibrariesCache and name in allLibrariesCache:
        return allLibrariesCache[name]
    else:
        allLibraries = getAllLibraries()
        return allLibrariesCache.get(name)

def getCannedResponseByName(library_id, response_name):

    request = PureCloudPlatformClientV2.ResponseQueryRequest()
    request.filters = list()
    library_filter = PureCloudPlatformClientV2.ResponseFilter()
    library_filter.name = "libraryId"
    library_filter.operator = "EQUALS"
    library_filter.values = [ library_id ]
    request.filters.append(library_filter)
    name_filter = PureCloudPlatformClientV2.ResponseFilter()
    name_filter.name = "name"
    name_filter.operator = "EQUALS"
    name_filter.values = [ response_name ]
    request.filters.append(name_filter)

    api_response = getResponseManagementApi().post_responsemanagement_responses_query(request)
    if len(api_response.results.entities) == 0:
        canned_response = None
    else:
        assert(len(api_response.results.entities) == 1)
        canned_response = api_response.results.entities[0]

    return canned_response

def createLibrary(library):
    library = getResponseManagementApi().post_responsemanagement_libraries(library)
    console.ok('Created library [%s]' % library.name)
    return library

def resolveLibrary(library, use_cache=True):
    global allLibrariesCache
    resolved_library = None

    if not library.id:
        if library.name:
            if use_cache:
                if library.name in allLibrariesCache:
                    resolved_library = allLibrariesCache[library.name]
            
            if resolved_library is None:     
                resolved_library = getLibraryByName(library.name)

            if resolved_library is not None:
                library.id = resolved_library.id
            else:
                raise ValueError("Library %s not found" % library.name)

        else:
            raise ValueError("No library id or name defined")

    return library

def createCannedResponse(canned_response, bUpdate = False):

    # Resolve library
    if canned_response.libraries is not None:
        assert(len(canned_response.libraries) == 1)
        resolved_library = getLibraryByName(canned_response.libraries[0].name)
        if resolved_library is not None:
            canned_response.libraries[0].id = resolved_library.id
        else:
            createLibrary(canned_response.libraries[0])
            canned_response.libraries[0] = resolveLibrary(canned_response.libraries[0])
    else:
        raise ValueError("No libraries defined")

    # Check if canned response already exists
    existing_response = getCannedResponseByName(canned_response.libraries[0].id, canned_response.name)

    if existing_response is None:
        # Create
        getResponseManagementApi().post_responsemanagement_responses(canned_response)
        console.ok('Created canned response [%s]' % canned_response.name)

    elif bUpdate:
        # Update
        canned_response.version = existing_response.version
        getResponseManagementApi().put_responsemanagement_response(existing_response.id, canned_response)
        console.ok('Updated canned response [%s]' % canned_response.name)

    else:
        console.info('Canned response [%s] already exists. Skipping...' % canned_response.name)