# Import the Genesys Cloud platform SDK
import PureCloudPlatformClientV2

from utils import console

# Default log settings
PureCloudPlatformClientV2.configuration.logger.log_level = PureCloudPlatformClientV2.logger.LogLevel.LError
PureCloudPlatformClientV2.configuration.logger.log_request_body = True
PureCloudPlatformClientV2.configuration.logger.log_response_body = True
PureCloudPlatformClientV2.configuration.logger.log_format = PureCloudPlatformClientV2.logger.LogFormat.TEXT
PureCloudPlatformClientV2.configuration.logger.log_to_console = True
# PureCloudPlatformClientV2.configuration.logger.log_file_path = "/var/log/pythonsdk.log"

# Initialise your connection to GCloud
def initApiClient(api_host, client_id, client_secret):
    global gApiClient

    # Set the region 
    ## region = PureCloudPlatformClientV2.PureCloudRegionHosts.ap_southeast_2
    PureCloudPlatformClientV2.configuration.host = api_host
    print('Host is %s' % PureCloudPlatformClientV2.configuration.host)

    # Instanciate apiClient
    print('Client Id: %s' % client_id)
    gApiClient = PureCloudPlatformClientV2.api_client.ApiClient().get_client_credentials_token(client_id, client_secret)