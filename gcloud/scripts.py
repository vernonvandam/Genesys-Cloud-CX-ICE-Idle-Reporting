import gcloud
import PureCloudPlatformClientV2

import utils.console as console

from . import helpers
from . import client

# name -> script cache used to optimise resolutions
allScriptsCache = dict()

def getScriptsApi():
    return PureCloudPlatformClientV2.ScriptsApi(client.gApiClient)

def getArchitectApi():
    return PureCloudPlatformClientV2.ArchitectApi(client.gApiClient)

"""
    Returns a dictionary of all Script objects preent in the cloud.
    The method is used to pre-load the allScriptsCache which can be used to optimise resolutions
"""
def getAllScripts():
    global allScriptsCache

    allScriptsCache = helpers.getAll(getScriptsApi().get_scripts)
    return allScriptsCache

"""
    Returns a single script object referenced by name
    This method updates the allScriptsCache allowing the system to learn of objects to optimise resolutions
"""
def getScriptByName(name):
    global allScriptsCache

    script = helpers.getByName(getScriptsApi().get_scripts, name)
    if allScriptsCache and script is not None:
        allScriptsCache[name] = script
    return script

def resolveScript(script, use_cache=True):
    global allScriptsCache
    resolved_script = None

    if not script.id:
        if script.name:
            if use_cache:
                if script.name in allScriptsCache:
                    resolved_script = allScriptsCache[script.name]
            
            if resolved_script is None:     
                resolved_script = getScriptByName(script.name)

            if resolved_script is not None:
                script.id = resolved_script.id
            else:
                raise ValueError("Script %s not found" % script.name)

        else:
            raise ValueError("No script id or name defined")

    return script