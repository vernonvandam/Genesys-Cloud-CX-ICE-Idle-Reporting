import PureCloudPlatformClientV2
from PureCloudPlatformClientV2.rest import ApiException

import utils.console as console

from . import client
from . import helpers
from . import divisions
from . import locations
from . import phones

def getUsersApi():
    return PureCloudPlatformClientV2.UsersApi(client.gApiClient)

def getAllUsers(user_state="active", expand_fields=None):
    allEntities = dict()

    nPageNumber = 1
    nPageCount = 1
    while nPageNumber <= nPageCount:
        api_response = getUsersApi().get_users(page_size=100, page_number=nPageNumber, state=user_state, expand=expand_fields)
        console.info('Read %s users' % len(api_response.entities))
        for entity in api_response.entities:
            allEntities[entity.username] = entity
            
        nPageCount = api_response.page_count if api_response.page_count else 1
        nPageNumber += 1
        
    console.info('Read total %s entities' % len(allEntities))
    return allEntities

def getAllUsersByUsername(user_state="active"):
    allUsers = getAllUsers(user_state)
    allUsersByUsername = dict()

    for user_name in allUsers:
        user = allUsers[user_name]
        user_username = user["username"]
        allUsersByUsername[user_username] = user

    return allUsersByUsername

def getAllUsersById(user_state="active", expand_fields = None):
    allUsers = getAllUsers(user_state, expand_fields)
    allUsersByUserId = dict()

    for user_name in allUsers:
        user = allUsers[user_name]
        user_id = user.id
        if user.id == "fb5298ba-0644-4847-bc8e-d015a7f25ff9":
            a=1
    
        allUsersByUserId[user_id] = user

    return allUsersByUserId

def getUserByName(name):
    result = None

    search_criteria = PureCloudPlatformClientV2.UserSearchCriteria()
    search_criteria.fields = [ "username"]
    search_criteria.value = name
    search_criteria.type = "EXACT"

    body = PureCloudPlatformClientV2.UserSearchRequest()
    body.query = [ search_criteria ]

    api_response = getUsersApi().post_users_search(body=body)
    if api_response.total == 1:
        result = api_response.results[0]
    elif api_response.total > 1:
        for r in api_response.results:
            if r.name == name:
                result = r
                break
    
    return result

def updateUser(id, body):
    getUsersApi().patch_user(id, body)

usersCache = None

def initUserCache():
    global usersCache
    usersCache = dict()
    for u in getAllUsers(user_state="any").values():
        usersCache[u.username.lower()] = u

def resolveUser(user, use_cache=True):
    resolved_user = None

    if not user.id:
        if user.username:
            user_name = user.username.lower()
            if use_cache:
                global usersCache
                if usersCache is None:
                    initUserCache()

                if user_name in usersCache:
                    resolved_user = usersCache[user_name]
            
            if resolved_user is None:     
                resolved_user = getUserByName(user_name)
                if use_cache and resolved_user:
                    usersCache[user_name] = resolved_user

            if resolved_user is not None:
                user.id = resolved_user.id
                user.version = resolved_user.version
            else:
                raise ValueError("User [%s] not found" % user_name)

        else:
            raise ValueError("No user id or username defined")

    return user

def createUser(user, bUpdate = False, use_cache=True):

    # Resolve division
    if user.division is not None:
        user.division = divisions.resolveDivision(user.division)
    else:
        raise ValueError("No division defined")

    # Resolve location
    if user.locations is not None and len(user.locations) > 0:
        for i in range(len(user.locations)):
            user.locations[i].location_definition = locations.resolveLocation(user.locations[i].location_definition)

    # Resolve Manager (if defined)
    if user.manager is not None:
        resolved_manager = resolveUser(user.manager)
        user.manager = resolved_manager.id

    # Check if user already exists
    resolved_user = resolveUser(user)

    if resolved_user.id is None:
        # Set name for new queue
        api_response = getUsersApi().post_users(resolved_user)
        console.ok('Created user [%s]' % resolved_user.username)

    elif bUpdate:
        # Set id for queue to update
        api_response = getUsersApi().patch_user(resolved_user.id, resolved_user)
        console.ok('Updated user [%s]' % resolved_user.username)

    else:
        console.info('User [%s] already exists. Skipping...' % resolved_user.username)


def updateUserAutoAnswer(users):
    allPatchUsers = list()

    assert isinstance(users, list)
    assert len(users) > 0 and (isinstance(users[0], PureCloudPlatformClientV2.User) or (isinstance(users[0], PureCloudPlatformClientV2.PatchUser)))

    for user in users:
        p = PureCloudPlatformClientV2.PatchUser()
        p.id = user.id
        p.acd_auto_answer = user.acd_auto_answer
        allPatchUsers.append(p)

    try:
        getUsersApi().patch_users_bulk(allPatchUsers)

    except ApiException as e:
        console.fail("User auto-answer update failed: %s" % e)
        raise

def updateUserEmployeeInfo(user):

   # Resolve division
    if user.division is not None:
        user.division = divisions.resolveDivision(user.division)
    else:
        raise ValueError("No division defined")

    # Resolve location
    if user.locations is not None and len(user.locations) > 0:
        for i in range(len(user.locations)):
            user.locations[i].location_definition = locations.resolveLocation(user.locations[i].location_definition)

    # Resolve Manager (if defined)
    if user.manager is not None:
        resolved_manager = resolveUser(user.manager)
        user.manager = resolved_manager.id

    try:
        upd_user = getUsersApi().patch_user(user.id, user)
        if upd_user.division.id != user.division.id:
            divisions.getAuthorizationApi().post_authorization_division_object(user.division.id, 'USER', [user.id])

        console.ok('Updated user [%s]' % user.username)

    except ApiException as e:
        console.fail("User employee info update failed: %s" % e)
        raise

def assignStationToUser(station, user):
    user = resolveUser(user)
    #TODO phone = phones.resolvePhone(phone)
    getUsersApi().put_user_station_defaultstation_station_id(user.id, station.id)