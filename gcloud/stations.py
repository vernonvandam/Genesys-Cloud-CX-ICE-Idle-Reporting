import PureCloudPlatformClientV2
from PureCloudPlatformClientV2.rest import ApiException

import utils.console as console

from . import client
from . import helpers


def getStationsApi():
    return PureCloudPlatformClientV2.StationsApi(client.gApiClient)

def getStationByName(name):

    station = helpers.getByName(getStationsApi().get_stations, name)
    return station