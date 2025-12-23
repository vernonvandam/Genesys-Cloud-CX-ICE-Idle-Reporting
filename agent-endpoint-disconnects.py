import csv
from datetime import date, datetime, timedelta
import math
import os
import tempfile
from zoneinfo import ZoneInfo

import tkinter
import tkinter.filedialog

from pprint import pprint

from dotenv import load_dotenv

import gcloud
import utils.console as console
import PureCloudPlatformClientV2
from PureCloudPlatformClientV2.rest import ApiException

import requests

import pyshark

load_dotenv()

# Report start/end time
szTimeZone = 'Australia/Sydney'
tzinfo = ZoneInfo(szTimeZone)
now = datetime.now(tzinfo)

# Use the analytics API to retrieve possible agent call drops
nDayIntervals = 7
dtEndDate = datetime(now.year, now.month, now.day, tzinfo = tzinfo) + timedelta(days=1)
#dtEndDate = datetime(2023,5,31, tzinfo=tzinfo)
dtStartDate = dtEndDate - timedelta(days=nDayIntervals)

# Test users to be excluded from reporting
exclude_user_ids = dict()

exclude_test_users = False
if exclude_test_users:
    exclude_user_ids['c3b73119-419e-4d0c-9eb9-b1d92d5d6b8d']='mark.goldsmith@global.ntt'

def init():
    required_vars = ["API_HOST", "GENESYS_CLOUD_CLIENT_ID", "GENESYS_CLOUD_CLIENT_SECRET"]
    missing_vars = [ v for v in required_vars if v not in os.environ ]

    if len(missing_vars) > 0:
        console.fail("Unable to initialise Genesys Cloud API. The following vars are undefined: %s" % missing_vars)
        raise RuntimeError("Unable to initialise Genesys Cloud API")

    gcloud.client.initApiClient(os.getenv("API_HOST"), os.getenv("GENESYS_CLOUD_CLIENT_ID"), os.getenv("GENESYS_CLOUD_CLIENT_SECRET"))

def getAnalyticsApi():
    return PureCloudPlatformClientV2.AnalyticsApi(gcloud.client.gApiClient)

def getVoiceConversationsMetrics(start_date, end_date, time_zone, granularity = 'P1D'):
    '''
    Returns count metrics for all voice interactions
    '''

    media_type_voice = PureCloudPlatformClientV2.ConversationAggregateQueryPredicate()
    media_type_voice.type = "dimension"
    media_type_voice.dimension = "mediaType"
    media_type_voice.operator = "matches"
    media_type_voice.value = "voice"

    aggregation_filter = PureCloudPlatformClientV2.ConversationAggregateQueryFilter()
    aggregation_filter.predicates = [media_type_voice]
    aggregation_filter.type = "and"

    PureCloudPlatformClientV2.ConversationAggregate

    body = PureCloudPlatformClientV2.ConversationAggregationQuery()
    body.interval = "%s/%s" % (start_date.isoformat(), end_date.isoformat())
    body.time_zone = time_zone
    body.granularity = granularity
    body.filter = aggregation_filter
    # body.group_by = [ "userId" ]
    body.metrics = [ "nConnected", "nOffered", "nBlindTransferred", "nConsult", "nConsultTransferred", "nError", "nTransferred", "tConnected", "tIvr", "tAlert", "tAnswered", "tHandle", "tNotResponding" ]

    api_response = getAnalyticsApi().post_analytics_conversations_aggregates_query(body)

    results = []
    for result in api_response.results[0].data:
        interval = result.interval
        
        voiceConversationsMetrics = dict()
        for metric in result.metrics:
            voiceConversationsMetrics[metric.metric] = metric.stats.count

        results.append({
            "interval" : interval,
            "metrics" : voiceConversationsMetrics
        })

    return results;

def getVoiceConversationsHandledByUser(start_date, end_date, time_zone, granularity = 'P1D', excludingUserIds = {}):
    '''
    Returns the tHandled voice conversation metrics grouped by UserId.
    The results for particular users may be excluded by including their userId in the excludingUserIds dict
    '''

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
    body.group_by = [ "userId" ]
    body.metrics = [ "tHandle" ]

    api_response = getAnalyticsApi().post_analytics_conversations_aggregates_query(body)
    results = api_response.results
    if results is None:
        return None
    
    # Now iterate through the results to exclude users
    if excludingUserIds is not None and len(excludingUserIds) > 0:
        filteredResults = []
        for e in results:
            if e.group is not None and e.group['userId'] is not None and e.group['userId'] not in excludingUserIds:
                filteredResults.append(e)

        return filteredResults;

    else:
        return results

def getTotalVoiceConversationsHandledByIntervalExcludingUsers(start_date, end_date, time_zone, granularity = 'P1D', excludingUserIds = {}):
    '''
    Returns a dictionary containing summarised metrics per interval:
    {
        '2023-06-23T00:00:00.000+10:00/2023-06-24T00:00:00.000+10:00': {
            'nUserIds': 45,
            'metrics': {
                'tHandle': {
                    'count': 3505,
                    'max': 2081223.0,
                    'min': 7506.0,
                    'sum': 168544522.0
                }
            },
        },
        ...
    }
    '''

    # Get the voice conversation handled data excluding the excluded users
    results = getVoiceConversationsHandledByUser(start_date, end_date, time_zone, granularity, excludingUserIds)
    if results is None:
        return None

    # Next iterate through the results to summarise the voice conversation stats per interval and track the number of unique users per interval
    summarised_metrics_per_interval = dict()
    for user_result in results:
        for user_interval_result in user_result.data:
            interval = user_interval_result.interval

            # Get interval statistics or initialise if not present
            summarised_metrics_this_interval = summarised_metrics_per_interval[interval] if interval in summarised_metrics_per_interval else { 'nUserIds' : 0, 'metrics' : {} }

            # Update the summarised metrics for this interval
            summarised_metrics_this_interval['nUserIds'] += 1

            summarised_stats_by_metric = summarised_metrics_this_interval['metrics']
            for m in user_interval_result.metrics:

                if m.metric not in summarised_stats_by_metric:
                    # This is the first metric for this interval. Initialise
                    summarised_stats = dict()
                    summarised_stats['count'] = m.stats.count
                    summarised_stats['sum'] = m.stats.sum
                    summarised_stats['max'] = m.stats.max
                    summarised_stats['min'] = m.stats.min

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
    #pprint(summarised_metrics_per_interval)
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
    #segment_filter.predicates = [purpose_is_agent, disconnecttype_is_endpoint, sip_response_code_exists]
    segment_filter.predicates = [segmenttype_is_interact, disconnecttype_is_error]
    segment_filter.type = "and"

    body = PureCloudPlatformClientV2.ConversationQuery()
    body.interval = "%s/%s" % (start_date.isoformat(), end_date.isoformat())
    body.conversation_filters = [ conversation_filter ]
    body.segment_filters = [ segment_filter ]
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

    # Get call volume metrics excluding users
    #voiceConversationMetrics = getVoiceConversationsMetrics(dtStartDate, dtEndDate, szTimeZone)
    
    console.info(f"Retrieving daily conversations between {dtStartDate} and {dtEndDate}")
    voiceConversationMetrics = getTotalVoiceConversationsHandledByIntervalExcludingUsers(dtStartDate, dtEndDate, szTimeZone, 'P1D', exclude_user_ids)
    #pprint(voiceConversationMetrics)

    # Retrieve detailed information for each interaction and check whether purpose = agent, disconnectType = endpoint and report on SIP & Q850 cause codes)
    agentEndpointDisconnections = list()
    console.info(f"Retrieving error disconnections between {dtStartDate} and {dtEndDate}")
    conversations = getConversationsWithInteractErrorSegment(dtStartDate, dtEndDate)
    console.info("Received %s conversations with error disconnections" % len(conversations))

    if len(conversations) == 0:
        console.ok("No error disconnections found")
        exit()

    # All users to resolve the agents involve in each conversation
    allUsersById = gcloud.users.getAllUsersById(user_state="any", expand_fields="locations")

    for conversation in conversations:
        conversationId = conversation.conversation_id

        if conversationId == "339d73c6-a313-4a66-9a93-1fff5a8a7326":
            pass

        conversationStart = conversation.conversation_start
        conversationEnd = conversation.conversation_end
        originatingDirection = conversation.originating_direction
        for participant in conversation.participants:
            if (participant.purpose in ["agent", "user"]) and participant.user_id not in exclude_user_ids:

                agentUserId = participant.user_id
                user = allUsersById[agentUserId]
                username = user.username if agentUserId in allUsersById else agentUserId
                division = user._division.name if agentUserId in allUsersById else "(unknown)"

                # Check disconenct type
                for session in participant.sessions:
                    if session.media_type == "voice" and session.dnis != "tel:*86":     # Exclude calls to WebRTC test tool
                        for segment in session.segments:
                            if segment.segment_type == "interact" and segment.disconnect_type == "error" and "webrtc.endpoint.disconnect" in segment.error_code:

                                reason = segment.error_code.split(".")[-1]
                                #reason = "skipped"
                                #console.info("BYE reason for conversationId %s is %s" % (conversationId, reason))

                                #console.info("ConvId: %s, conversationStart: %s, conversationDuration: %s, originatingDirection: %s, Username: %s, sipResponseCodes: %s, q850ResponseCodes: %s" % (conversationId, conversationStart, conversationEnd - conversationStart, originatingDirection, username, sipResponseCode, q850ResponseCode))
                                agentEndpointDisconnections.append({
                                    "conversationId" : conversationId,
                                    "conversationStart" : conversationStart.astimezone(tzinfo),
                                    "conversationDuration" : conversationEnd - conversationStart,
                                    "originatingDirection" : originatingDirection,
                                    "agentName" : username,
                                    "agentUserId" : agentUserId,
                                    "division" : division,
                                    "error_code" : segment.error_code
                                })

    # Add the number of SIP failures to our metrics
    for interval, interval_metrics in voiceConversationMetrics.items():
        (start_interval,end_interval) = interval.split("/")
        dtStartInterval = datetime.fromisoformat(start_interval)
        dtEndInterval = datetime.fromisoformat(end_interval)

        failureReasonMetrics = dict()
        nFailures = 0
        nFailuresByUser = dict()
        for disconnection in agentEndpointDisconnections:
            if dtStartInterval <= disconnection['conversationStart'] <= dtEndInterval:
                nFailures += 1

                # Track unique users
                agentName = disconnection['agentName']
                if agentName in nFailuresByUser:
                    nFailuresByUser[agentName] += 1
                else:
                    nFailuresByUser[agentName] = 1

                error_code = disconnection['error_code'] if disconnection['error_code'] is not None else "Other"
                if error_code in failureReasonMetrics:
                    failureReasonMetrics[error_code] += 1
                else:
                    failureReasonMetrics[error_code] = 1

        failureReasonMetrics['nTotal'] = nFailures
        failureReasonMetrics['nTotalByUser'] = nFailuresByUser
        interval_metrics["failureReasonMetrics"] = failureReasonMetrics

    # Export results to CSV
    tkroot = tkinter.Tk()
    output_path = tkinter.filedialog.asksaveasfilename(title="Summary Metrics", confirmoverwrite=True,defaultextension="csv",parent=tkroot)
    
    with open(output_path, 'w', encoding='UTF-8', newline='') as f:
        
        # Daily Summary
        header = ['Start Interval', 'End Interval', 'nHandled', 'nUsers', 'nFailures', 'nUsersImpacted']
        writer = csv.writer(f)
        writer.writerow(header)

        rows = list()
        for interval, interval_metrics in voiceConversationMetrics.items():
            row = list()
            (start_interval,end_interval) = interval.split("/")
            row.append(start_interval)
            row.append(end_interval)

            tHandle = interval_metrics['metrics']['tHandle']['count'] if 'tHandle' in interval_metrics['metrics'] else 0
            row.append(tHandle)

            nUsers = interval_metrics['nUserIds']
            row.append(nUsers)

            nFailures = interval_metrics['failureReasonMetrics']['nTotal'] if 'nTotal' in interval_metrics['failureReasonMetrics'] else 0
            row.append(nFailures)

            nUsersImpacted = len(interval_metrics['failureReasonMetrics']['nTotalByUser']) if 'nTotalByUser' in interval_metrics['failureReasonMetrics'] else 0
            row.append(nUsersImpacted)

            rows.append(row)

        rows.append(list()) # Add a blank row
        writer.writerows(rows)

        # Detailed Incidents
        header = ['ConversationId', 'Start Time', 'Duration', 'Direction', 'Agent Name', 'Agent Id', 'Division', 'Error Code']
        writer.writerow(header)

        rows = list()
        for endpoint_disconnect in agentEndpointDisconnections:
            row = list()
            row.append(endpoint_disconnect['conversationId'])
            row.append(endpoint_disconnect['conversationStart'])
            row.append(endpoint_disconnect['conversationDuration'])
            row.append(endpoint_disconnect['originatingDirection'])
            row.append(endpoint_disconnect['agentName'])            
            row.append(endpoint_disconnect['agentUserId'])
            row.append(endpoint_disconnect['division'])
            row.append(endpoint_disconnect['error_code'])

            rows.append(row)

        rows.append(list()) # Add a blank row
        writer.writerows(rows)

        # Excluded users
        writer.writerow(['The following list of users were excluded from the report:'])

        header = ['Agent Name', 'Agent Id']
        writer.writerow(header)

        rows = list()
        for agent_id,agent_name in exclude_user_ids.items():
            row = list()
            row.append(agent_name)
            row.append(agent_id)

            rows.append(row)

        writer.writerows(rows)


if __name__ == "__main__":
    main()
    #test()