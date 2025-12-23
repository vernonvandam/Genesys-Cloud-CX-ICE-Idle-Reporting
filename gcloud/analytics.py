import gcloud
import PureCloudPlatformClientV2

import math
import utils.console as console

from . import helpers
from . import client

from pprint import pprint

def getAnalyticsApi():
    return PureCloudPlatformClientV2.AnalyticsApi(client.gApiClient)

def getConversationsWithAgentEndpointDisconnectConversations(start_date, end_date):

    purpose_is_agent = PureCloudPlatformClientV2.SegmentDetailQueryPredicate()
    purpose_is_agent.dimension = "purpose"
    purpose_is_agent.operator = "matches"
    purpose_is_agent.value = "agent"

    disconnecttype_is_endpoint = PureCloudPlatformClientV2.SegmentDetailQueryPredicate()
    disconnecttype_is_endpoint.dimension = "disconnectType"
    disconnecttype_is_endpoint.operator = "matches"
    disconnecttype_is_endpoint.value = "endpoint"

    sip_response_code_exists = PureCloudPlatformClientV2.SegmentDetailQueryPredicate()
    sip_response_code_exists.dimension = "sipResponseCode"
    sip_response_code_exists.operator = "exists"

    segment_filter = PureCloudPlatformClientV2.SegmentDetailQueryFilter()
    segment_filter.predicates = [purpose_is_agent, disconnecttype_is_endpoint, sip_response_code_exists]
    segment_filter.type = "and"

    body = PureCloudPlatformClientV2.ConversationQuery()
    body.interval = "%s/%s" % (start_date, end_date)
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
        
        console.info('Read %s conversations' % len(api_response.conversations))
        allConversations.extend(api_response.conversations)

        nPageNumber += 1
        
    console.info('Read total %s entities' % len(allConversations))
    return allConversations

def getVoiceConversationsMetrics(start_date, end_date, time_zone = 'Australia/Sydney', granularity = 'P1D'):
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

    body = PureCloudPlatformClientV2.ConversationAggregationQuery()
    body.interval = "%s/%s" % (start_date, end_date)
    body.time_zone = time_zone
    body.granularity = granularity
    body.filter = aggregation_filter
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