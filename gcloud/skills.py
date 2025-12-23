import gcloud
import PureCloudPlatformClientV2

import utils.console as console

from . import helpers

def getRoutingApi():
    return PureCloudPlatformClientV2.RoutingApi(gcloud.gApiClient)

def getAllRoutingSkills():
    allSkills = dict()

    api_response = getRoutingApi().get_routing_skills(page_size=500)

    if api_response.total > 1:
        for skill in api_response.entities:
            allSkills[skill.name] = skill
    
    console.info('Found %d Routing Skills' % len(allSkills))
    return allSkills

def getRoutingSkillByName(name):
    skill = None

    api_response = getRoutingApi().get_routing_skills(name=name)

    if api_response.total == 1:
        queue = api_response.entities[0]
    elif api_response.total > 1:
        for e in api_response.entities:
            if e.name == name:
                skill = e
                break
    
    if skill is None: console.info('Routing Skill %s not found' % name)
    return skill

def createRoutingSkills(skills):
    
    # Read the list of existing skills
    allSkills = getAllRoutingSkills()

    for skill in skills:

        existingSkill = allSkills.get(skill.name)

        if existingSkill is None:
            getRoutingApi().post_routing_skills(skill)
            console.ok('Created routing skill [%s]' % skill.name)

        else:
            console.info('Routing Skill [%s] already exists. Skipping...' % skill.name)