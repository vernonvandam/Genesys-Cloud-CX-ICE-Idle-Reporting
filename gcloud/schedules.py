import gcloud
import PureCloudPlatformClientV2
from functools import cache

import utils.console as console

from . import helpers
from . import client
from . import divisions

def getArchitectApi():
    return PureCloudPlatformClientV2.ArchitectApi(client.gApiClient)

# Return all schedules from GCloud

def getAllSchedules():
    return helpers.getAll(getArchitectApi().get_architect_schedules)

def getScheduleByName(name):
    return helpers.getByName(getArchitectApi().get_architect_schedules, name)

def createSchedule(schedule):
    return getArchitectApi().post_architect_schedules(schedule)

def createScheduleGroup(schedule, bUpdate = False):
    
    # Resolve the division
    schedule.division = divisions.resolveDivision(schedule.division)

    # Check if queue already exists
    existingSchedule = getScheduleByName(schedule.name)

    if existingSchedule is None:
        # Set name for new queue
        getArchitectApi().post_architect_schedules(schedule)
        console.ok('Created schedule [%s]' % schedule.name)

    elif bUpdate:
        # Set id for queue to update
        schedule.id = existingSchedule.id
        getArchitectApi().put_architect_schedule(schedule.id, schedule)
        console.ok('Updated schedule [%s]' % schedule.name)

    else:
        console.info('Schedule [%s] already exists. Skipping...' % schedule.name)

def getScheduleGroupByName(name):
    return helpers.getByName(getArchitectApi().get_architect_schedulegroups, name)

def createScheduleGroup(group, bUpdate = False):
    
    # Resolve the division
    group.division = divisions.resolveDivision(group.division)

    # Check if queue already exists
    existingGroup = getScheduleGroupByName(group.name)

    if existingGroup is None:
        # Set name for new queue
        getArchitectApi().post_architect_schedulegroups(group)
        console.ok('Created schedule group [%s]' % group.name)

    elif bUpdate:
        # Set id for queue to update
        group.id = existingGroup.id
        getArchitectApi().put_architect_schedulegroup(group.id, group)
        console.ok('Updated schedule group [%s]' % group.name)

    else:
        console.info('Schedule group [%s] already exists. Skipping...' % group.name)

def resolveScheduleGroup(group):
    if group.id is None:
        if group.name is not None:
            resolved_group = getScheduleGroupByName(group.name)
            group.id = resolved_group.id
        else:
            raise ValueError("No Schedule Group id or name defined")

    return group