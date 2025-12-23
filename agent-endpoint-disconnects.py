
import csv
from datetime import date, datetime, timedelta
import math
import os
import tempfile
from zoneinfo import ZoneInfo

import tkinter
import tkinter.filedialog

from pprint import pprint

import gcloud
import utils.console as console
import PureCloudPlatformClientV2
from PureCloudPlatformClientV2.rest import ApiException

import requests
import pyshark

from dotenv import load_dotenv

# Force .env to override any already-set environment variables
load_dotenv(override=True)



# -----------------------------------------------------------------------------------
# Region & timezone configuration
# -----------------------------------------------------------------------------------
# If your org is in Sydney, set GENESYS_CLOUD_REGION=ap_southeast_2 in your .env
# Alternatively, you can provide API_HOST=https://api.mypurecloud.com.au (legacy/manual)
# See Genesys region guidance: https://help.mypurecloud.com/faqs/how-do-i-select-my-region/
# SDK usage examples (Python): https://github.com/MyPureCloud/platform-client-sdk-python
# -----------------------------------------------------------------------------------

def resolve_region_host():
    """
    Resolve the SDK API host from GENESYS_CLOUD_REGION, or fall back to API_HOST.
    Returns a fully-qualified API base URL like 'https://api.mypurecloud.com.au'.
    """
    region_env = os.getenv("GENESYS_CLOUD_REGION", "").strip().lower()
    api_host_env = os.getenv("API_HOST", "").strip()

    # Map common region codes to SDK constants
    region_map = {
        "us_east_1": PureCloudPlatformClientV2.PureCloudRegionHosts.us_east_1,
        "us_east_2": PureCloudPlatformClientV2.PureCloudRegionHosts.us_east_2,
        "us_west_2": PureCloudPlatformClientV2.PureCloudRegionHosts.us_west_2,
        "eu_west_1": PureCloudPlatformClientV2.PureCloudRegionHosts.eu_west_1,
        "eu_central_1": PureCloudPlatformClientV2.PureCloudRegionHosts.eu_central_1,
        "ap_southeast_1": PureCloudPlatformClientV2.PureCloudRegionHosts.ap_southeast_1,
        "ap_southeast_2": PureCloudPlatformClientV2.PureCloudRegionHosts.ap_southeast_2,  # Sydney
        "ap_northeast_1": PureCloudPlatformClientV2.PureCloudRegionHosts.ap_northeast_1,
        "ap_northeast_2": PureCloudPlatformClientV2.PureCloudRegionHosts.ap_northeast_2,
        "ca_central_1": PureCloudPlatformClientV2.PureCloudRegionHosts.ca_central_1,
        "sa_east_1": PureCloudPlatformClientV2.PureCloudRegionHosts.sa_east_1,
        # add more if needed as supported by your SDK version
    }

    if region_env:
        host_obj = region_map.get(region_env)
        if not host_obj:
            console.fail(f"Unknown GENESYS_CLOUD_REGION '{region_env}'. "
                         f"Use one of: {', '.join(region_map.keys())}.")
            raise RuntimeError("Invalid region code")
        # NB: some SDK versions support .get_api_host(); otherwise assign the object directly.
        try:
            resolved_host = host_obj.get_api_host()
        except AttributeError:
            # older SDKs may expect direct assignment of the host object
            resolved_host = host_obj
        console.info(f"Resolved region '{region_env}' to API host '{resolved_host}'")
        return resolved_host

    if api_host_env:
        console.info(f"Using API_HOST from environment: '{api_host_env}'")
        return api_host_env

    console.fail("No region or API host provided. "
                 "Set GENESYS_CLOUD_REGION (e.g. ap_southeast_2) or API_HOST.")
    raise RuntimeError("Missing region/API host configuration")

# Report start/end time
szTimeZone = 'Australia/Sydney'
tzinfo = ZoneInfo(szTimeZone)
now = datetime.now(tzinfo)

# Use the analytics API to retrieve possible agent call drops
nDayIntervals = 7
dtEndDate = datetime(now.year, now.month, now.day, tzinfo=tzinfo) + timedelta(days=1)
dtStartDate = dtEndDate - timedelta(days=nDayIntervals)

# Test users to be excluded from reporting
exclude_user_ids = dict()

exclude_test_users = True
if exclude_test_users:
    exclude_user_ids['c3b73119-419e-4d0c-9eb9-b1d92d5d6b8d'] = 'mark.goldsmith@global.ntt'

def init():
    # --- Resolve API host from region or env ---
    api_host = resolve_region_host()

    # --- Credentials ---
    required_vars = ["GENESYS_CLOUD_CLIENT_ID", "GENESYS_CLOUD_CLIENT_SECRET"]
    missing_vars = [v for v in required_vars if not os.getenv(v)]
    if len(missing_vars) > 0:
        console.fail("Unable to initialise Genesys Cloud API. "
                     f"The following vars are undefined: {missing_vars}")
        raise RuntimeError("Unable to initialise Genesys Cloud API")

    client_id = os.getenv("GENESYS_CLOUD_CLIENT_ID")
    client_secret = os.getenv("GENESYS_CLOUD_CLIENT_SECRET")

    # --- Set SDK base host (critical step) ---
    # This ensures the SDK targets the correct environment for your org.
    # Docs show environment/host must match region: https://help.mypurecloud.com/faqs/how-do-i-select-my-region/
    PureCloudPlatformClientV2.configuration.host = api_host

    # --- Initialise your wrapper client with the resolved host ---
    # gcloud.client.initApiClient(api_host, client_id, client_secret)
    gcloud.client.initApiClient()
    console.ok(f"Genesys Cloud SDK initialised for host: {api_host}")

def getAnalyticsApi():
    return PureCloudPlatformClientV2.AnalyticsApi(gcloud.client.gApiClient)

def getVoiceConversationsMetrics(start_date, end_date, time_zone, granularity='P1D'):
    """
    Returns count metrics for all voice interactions
    """
    media_type_voice = PureCloudPlatformClientV2.ConversationAggregateQueryPredicate()
    media_type_voice.type = "dimension"
    media_type_voice.dimension = "mediaType"
    media_type_voice.operator = "matches"
    media_type_voice.value = "voice"

    aggregation_filter = PureCloudPlatformClientV2.ConversationAggregateQueryFilter()
    aggregation_filter.predicates = [media_type_voice]
    aggregation_filter.type = "and"

    body = PureCloudPlatformClientV2.ConversationAggregationQuery()
    body.interval = "%s/%s" % (start_date.isoformat(), end_date.isoformat())
    body.time_zone = time_zone
    body.granularity = granularity
    body.filter = aggregation_filter
    body.metrics = [
        "nConnected", "nOffered", "nBlindTransferred", "nConsult",
        "nConsultTransferred", "nError", "nTransferred",
        "tConnected", "tIvr", "tAlert", "tAnswered", "tHandle", "tNotResponding"
    ]

    api_response = getAnalyticsApi().post_analytics_conversations_aggregates_query(body)

    results = []
    for result in api_response.results[0].data:
        interval = result.interval

        voiceConversationsMetrics = dict()
        for metric in result.metrics:
            voiceConversationsMetrics[metric.metric] = metric.stats.count

        results.append({
            "interval": interval,
            "metrics": voiceConversationsMetrics
        })

    return results

def getVoiceConversationsHandledByUser(start_date, end_date, time_zone, granularity='P1D', excludingUserIds={}):
    """
    Returns the tHandled voice conversation metrics grouped by UserId.
    The results for particular users may be excluded by including their userId in the excludingUserIds dict
    """
    media_type_voice = PureCloudPlatformClientV2.ConversationAggregateQueryPredicate()
    media_type_voice.type = "dimension"
    media_type_voice.dimension = "mediaType"
    media_type_voice.operator = "matches"
    media_type_voice.value = "voice"

    aggregation_filter = PureCloudPlatformClientV2.ConversationAggregateQueryFilter()
    aggregation_filter.predicates = [media_type_voice]
    aggregation_filter.type = "and"

    body = PureCloudPlatformClientV2.ConversationAggregationQuery()
    body.interval = "%s/%s" % (start_date.isoformat(), end_date.isoformat())
    body.time_zone = time_zone
    body.granularity = granularity
    body.filter = aggregation_filter
    body.group_by = ["userId"]
    body.metrics = ["tHandle"]

    api_response = getAnalyticsApi().post_analytics_conversations_aggregates_query(body)
    results = api_response.results
    if results is None:
        return None

    # Exclude users
    if excludingUserIds is not None and len(excludingUserIds) > 0:
        filteredResults = []
        for e in results:
            if e.group is not None and e.group.get('userId') is not None and e.group['userId'] not in excludingUserIds:
                filteredResults.append(e)
        return filteredResults
    else:
        return results

def getTotalVoiceConversationsHandledByIntervalExcludingUsers(start_date, end_date, time_zone, granularity='P1D', excludingUserIds={}):
    """
    Summarise metrics per interval and track unique users per interval.
    """
    results = getVoiceConversationsHandledByUser(start_date, end_date, time_zone, granularity, excludingUserIds)
    if results is None:
        return None

    summarised_metrics_per_interval = dict()
    for user_result in results:
        for user_interval_result in user_result.data:
            interval = user_interval_result.interval

            summarised_metrics_this_interval = summarised_metrics_per_interval.get(
                interval, {'nUserIds': 0, 'metrics': {}}
            )

            summarised_metrics_this_interval['nUserIds'] += 1

            summarised_stats_by_metric = summarised_metrics_this_interval['metrics']
            for m in user_interval_result.metrics:
                if m.metric not in summarised_stats_by_metric:
                    summarised_stats = {
                        'count': m.stats.count,
                        'sum': m.stats.sum,
                        'max': m.stats.max,
                        'min': m.stats.min
                    }
                else:
                    summarised_stats = summarised_stats_by_metric[m.metric]
                    if m.stats.count is not None: summarised_stats['count'] += m.stats.count
                    if m.stats.sum is not None: summarised_stats['sum'] += m.stats.sum
                    if m.stats.max is not None and m.stats.max > summarised_stats['max']: summarised_stats['max'] = m.stats.max
                    if m.stats.min is not None and m.stats.min < summarised_stats['min']: summarised_stats['min'] = m.stats.min

                summarised_stats_by_metric[m.metric] = summarised_stats

            summarised_metrics_this_interval['metrics'] = summarised_stats_by_metric
            summarised_metrics_per_interval[interval] = summarised_metrics_this_interval

    summarised_metrics_per_interval = dict(sorted(summarised_metrics_per_interval.items()))
    return summarised_metrics_per_interval

def getConversationsWithInteractErrorSegment(start_date, end_date):
    conversation_complete = PureCloudPlatformClientV2.ConversationDetailQueryPredicate()
    conversation_complete.dimension = "conversationEnd"
    conversation_complete.operator = "exists"

    conversation_filter = PureCloudPlatformClientV2.ConversationDetailQueryFilter()
    conversation_filter.predicates = [conversation_complete]
    conversation_filter.type = "and"

    segmenttype_is_interact = PureCloudPlatformClientV2.SegmentDetailQueryPredicate()
    segmenttype_is_interact.dimension = "segmentType"
    segmenttype_is_interact.operator = "matches"
    segmenttype_is_interact.value = "interact"

    disconnecttype_is_error = PureCloudPlatformClientV2.SegmentDetailQueryPredicate()
    disconnecttype_is_error.dimension = "disconnectType"
    disconnecttype_is_error.operator = "matches"
    disconnecttype_is_error.value = "error"

    segment_filter = PureCloudPlatformClientV2.SegmentDetailQueryFilter()
    segment_filter.predicates = [segmenttype_is_interact, disconnecttype_is_error]
    segment_filter.type = "and"

    body = PureCloudPlatformClientV2.ConversationQuery()
    body.interval = "%s/%s" % (start_date.isoformat(), end_date.isoformat())
    body.conversation_filters = [conversation_filter]
    body.segment_filters = [segment_filter]
    body.paging = PureCloudPlatformClientV2.PagingSpec()
    body.paging.page_size = 100

    nPageNumber = 1
    nPageCount = 1
    allConversations = list()
    while nPageNumber <= nPageCount:
        body.paging.page_number = nPageNumber
        api_response = getAnalyticsApi().post_analytics_conversations_details_query(body)
        nPageCount = math.ceil(api_response.total_hits / body.paging.page_size)
        console.info('Total Hits: %s, calc page count %s' % (api_response.total_hits, nPageCount))

        if api_response.conversations is not None:
            console.info('Read %s conversations' % len(api_response.conversations))
            allConversations.extend(api_response.conversations)

        nPageNumber += 1

    console.info('Read total %s entities' % len(allConversations))
    return allConversations

def main():
    init()

    console.info(f"Retrieving daily conversations between {dtStartDate} and {dtEndDate}")
    voiceConversationMetrics = getTotalVoiceConversationsHandledByIntervalExcludingUsers(
        dtStartDate, dtEndDate, szTimeZone, 'P1D', exclude_user_ids
    )

    console.info(f"Retrieving error disconnections between {dtStartDate} and {dtEndDate}")
    conversations = getConversationsWithInteractErrorSegment(dtStartDate, dtEndDate)
    console.info("Received %s conversations with error disconnections" % len(conversations))

    if len(conversations) == 0:
        console.ok("No error disconnections found")
        exit()

    # All users to resolve the agents involve in each conversation
    allUsersById = gcloud.users.getAllUsersById(user_state="any", expand_fields="locations")

    agentEndpointDisconnections = list()
    for conversation in conversations:
        conversationId = conversation.conversation_id
        conversationStart = conversation.conversation_start
        conversationEnd = conversation.conversation_end
        originatingDirection = conversation.originating_direction
        for participant in conversation.participants:
            if (participant.purpose in ["agent", "user"]) and participant.user_id not in exclude_user_ids:

                agentUserId = participant.user_id
                user = allUsersById[agentUserId]
                username = user.username if agentUserId in allUsersById else agentUserId
                division = user._division.name if agentUserId in allUsersById else "(unknown)"

                for session in participant.sessions:
                    if session.media_type == "voice" and session.dnis != "tel:*86":
                        for segment in session.segments:
                            if segment.segment_type == "interact" and segment.disconnect_type == "error" and "webrtc.endpoint.disconnect" in segment.error_code:
                                reason = segment.error_code.split(".")[-1]
                                agentEndpointDisconnections.append({
                                    "conversationId": conversationId,
                                    "conversationStart": conversationStart.astimezone(tzinfo),
                                    "conversationDuration": conversationEnd - conversationStart,
                                    "originatingDirection": originatingDirection,
                                    "agentName": username,
                                    "agentUserId": agentUserId,
                                    "division": division,
                                    "error_code": segment.error_code
                                })

    for interval, interval_metrics in voiceConversationMetrics.items():
        (start_interval, end_interval) = interval.split("/")
        dtStartInterval = datetime.fromisoformat(start_interval)
        dtEndInterval = datetime.fromisoformat(end_interval)

        failureReasonMetrics = dict()
        nFailures = 0
        nFailuresByUser = dict()
        for disconnection in agentEndpointDisconnections:
            if dtStartInterval <= disconnection['conversationStart'] <= dtEndInterval:
                nFailures += 1
                agentName = disconnection['agentName']
                nFailuresByUser[agentName] = nFailuresByUser.get(agentName, 0) + 1

                error_code = disconnection['error_code'] if disconnection['error_code'] is not None else "Other"
                failureReasonMetrics[error_code] = failureReasonMetrics.get(error_code, 0) + 1

        failureReasonMetrics['nTotal'] = nFailures
        failureReasonMetrics['nTotalByUser'] = nFailuresByUser
        interval_metrics["failureReasonMetrics"] = failureReasonMetrics

    tkroot = tkinter.Tk()
    output_path = tkinter.filedialog.asksaveasfilename(title="Summary Metrics", confirmoverwrite=True, defaultextension="csv", parent=tkroot)

    with open(output_path, 'w', encoding='UTF-8', newline='') as f:
        header = ['Start Interval', 'End Interval', 'nHandled', 'nUsers', 'nFailures', 'nUsersImpacted']
        writer = csv.writer(f)
        writer.writerow(header)

        rows = list()
        for interval, interval_metrics in voiceConversationMetrics.items():
            row = list()
            (start_interval, end_interval) = interval.split("/")
            row.append(start_interval)
            row.append(end_interval)

            tHandle = interval_metrics['metrics'].get('tHandle', {}).get('count', 0)
            row.append(tHandle)

            nUsers = interval_metrics['nUserIds']
            row.append(nUsers)

            nFailures = interval_metrics['failureReasonMetrics'].get('nTotal', 0)
            row.append(nFailures)

            nUsersImpacted = len(interval_metrics['failureReasonMetrics'].get('nTotalByUser', {}))
            row.append(nUsersImpacted)

            rows.append(row)

        rows.append(list())
        writer.writerows(rows)

        header = ['ConversationId', 'Start Time', 'Duration', 'Direction', 'Agent Name', 'Agent Id', 'Division', 'Error Code']
        writer.writerow(header)

        rows = list()
        for endpoint_disconnect in agentEndpointDisconnections:
            row = [
                endpoint_disconnect['conversationId'],
                endpoint_disconnect['conversationStart'],
                endpoint_disconnect['conversationDuration'],
                endpoint_disconnect['originatingDirection'],
                endpoint_disconnect['agentName'],
                endpoint_disconnect['agentUserId'],
                endpoint_disconnect['division'],
                endpoint_disconnect['error_code'],
            ]
            rows.append(row)

        rows.append(list())
        writer.writerows(rows)

        writer.writerow(['The following list of users were excluded from the report:'])
        header = ['Agent Name', 'Agent Id']
        writer.writerow(header)

        rows = list()
        for agent_id, agent_name in exclude_user_ids.items():
            rows.append([agent_name, agent_id])

        writer.writerows(rows)

if __name__ == "__main__":
    main()
