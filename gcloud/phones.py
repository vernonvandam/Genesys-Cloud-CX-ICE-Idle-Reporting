import PureCloudPlatformClientV2
from PureCloudPlatformClientV2.rest import ApiException

import utils.console as console

from . import client
from . import helpers
from . import divisions
from . import locations

# name -> Phone cache used to optimise resolutions
allPhonesCache = None

def getTelephonyProvidersEdgeApi():
    return PureCloudPlatformClientV2.TelephonyProvidersEdgeApi(client.gApiClient)

def getAllPhones():
    global allPhonesCache

    allPhonesCache = helpers.getAll(getTelephonyProvidersEdgeApi().get_telephony_providers_edges_phones, nPageSize = 100, fields = ["webRtcUser"])
    return allPhonesCache

def getAllPhonesByWebRtcUserId():

    allPhonesCache = helpers.getAll(getTelephonyProvidersEdgeApi().get_telephony_providers_edges_phones, nPageSize = 100, fields = ["webRtcUser"])
    allPhonesByWebRtcUserId = dict()

    for name in allPhonesCache:
        phone = allPhonesCache[name]
        webRtcUserId = phone[""]
    return allPhonesCache

def getPhoneByName(name):
    global allPhonesCache

    phone = helpers.getByName(getTelephonyProvidersEdgeApi().get_telephony_providers_edges_phones, name)
    if allPhonesCache and phone is not None:
        allPhonesCache[name] = phone
    return phone

def createPhone(phone, bUpdate = False):

    # Resolve the site
    if phone.site is not None:
        phone.site = resolveSite(phone.site)

    # Resolve the phone base settings
    if phone.phone_base_settings is not None:
        phone.phone_base_settings = resolvePhoneBaseSettings(phone.phone_base_settings)

    # Resolve the line base settings
    if phone.lines is not None:
        for line in phone.lines:
                if line.line_base_settings is not None:
                    line.line_base_settings = resolveLineBaseSettings(line.line_base_settings)

    # Check if phone already exists
    existing_phone = getPhoneByName(phone.name)

    if existing_phone is None:
        # Create
        getTelephonyProvidersEdgeApi().post_telephony_providers_edges_phones(phone)
        console.ok('Created phone [%s]' % phone.name)

    elif bUpdate:
        # Update
        getTelephonyProvidersEdgeApi().put_telephony_providers_edges_phone(existing_phone.id, phone)
        console.ok('Updated phone [%s]' % phone.name)

    else:
        console.info('Phone [%s] already exists. Skipping...' % phone.name)

def createPhoneForUser(name, base_settings_name, site_name, user, bUpdate = False):
    phone = PureCloudPlatformClientV2.Phone()
    phone.name = name

    phone.phone_base_settings = PureCloudPlatformClientV2.PhoneBaseSettings()
    phone.phone_base_settings.name = base_settings_name


    line = PureCloudPlatformClientV2.Line()
    line.line_base_settings = PureCloudPlatformClientV2.DomainEntity()
    line.line_base_settings.name = "%s_1" % base_settings_name
    phone.lines = [line]
    
    phone.site = PureCloudPlatformClientV2.Site()
    phone.site.name = site_name

    phone.web_rtc_user = PureCloudPlatformClientV2.DomainEntity()
    phone.web_rtc_user.id = user.id
    phone.web_rtc_user.name = user.name

    createPhone(phone, bUpdate)

# name -> Site cache used to optimise resolutions
allSitesCache = None

def getAllSites():
    global allSitesCache

    allSitesCache = helpers.getAll(getTelephonyProvidersEdgeApi().get_telephony_providers_edges_sites, nPageSize = 100)
    return allSitesCache

def getSiteByName(name):
    global allSitesCache

    site = helpers.getByName(getTelephonyProvidersEdgeApi().get_telephony_providers_edges_sites, name)
    if allSitesCache and site is not None:
        allSitesCache[name] = site
    return site

def resolveSite(site, use_cache=True):
    resolved_site = None

    if not site.id:
        if site.name:

            if use_cache:
                global allSitesCache
                if allSitesCache is None:
                    allSitesCache = getAllSites()

                if site.name in allSitesCache:
                    resolved_site = allSitesCache[site.name]
            
            if resolved_site is None:
                resolved_site = getSiteByName(site.name)
                if use_cache:
                    allSitesCache[resolved_site.name] = resolved_site
            
            if resolved_site is None:
                raise ValueError("No such site [%s]" % site.name)

            site.id = resolved_site.id

        else:
            raise ValueError("No site id or name defined")

    return site

# name -> PhoneBaseSettings cache used to optimise resolutions
allPhoneBaseSettingsCache = None

def getAllPhoneBaseSettings():
    global allPhoneBaseSettingsCache

    allPhoneBaseSettingsCache = helpers.getAll(getTelephonyProvidersEdgeApi().get_telephony_providers_edges_phonebasesettings, nPageSize = 100)
    return allPhoneBaseSettingsCache

def getPhoneBaseSettingsByName(name):
    global allPhoneBaseSettingsCache

    base_settings = helpers.getByName(getTelephonyProvidersEdgeApi().get_telephony_providers_edges_phonebasesettings, name)
    if allPhoneBaseSettingsCache and base_settings is not None:
        allPhoneBaseSettingsCache[name] = base_settings
    return base_settings

def resolvePhoneBaseSettings(base_settings, use_cache=True):
    resolved_base_settings = None

    if not base_settings.id:
        if base_settings.name:

            if use_cache:
                global allPhoneBaseSettingsCache
                if allPhoneBaseSettingsCache is None:
                    allPhoneBaseSettingsCache = getAllPhoneBaseSettings()

                if base_settings.name in allPhoneBaseSettingsCache:
                    resolved_base_settings = allPhoneBaseSettingsCache[base_settings.name]
            
            if resolved_base_settings is None:
                resolved_base_settings = getPhoneBaseSettingsByName(base_settings.name)
                if use_cache:
                    allPhoneBaseSettingsCache[resolved_base_settings.name] = resolved_base_settings
            
            if resolved_base_settings is None:
                raise ValueError("No such phone base settings [%s]" % base_settings.name)

            base_settings.id = resolved_base_settings.id

        else:
            raise ValueError("No phone base settings id or name defined")

    return base_settings

# name -> LineBaseSettings cache used to optimise resolutions
allLineBaseSettingsCache = None

def getAllLineBaseSettings():
    global allLineBaseSettingsCache

    allLineBaseSettingsCache = helpers.getAll(getTelephonyProvidersEdgeApi().get_telephony_providers_edges_linebasesettings, nPageSize = 100)
    return allLineBaseSettingsCache

def getLineBaseSettingsByName(name):
    global allLineBaseSettingsCache

    base_settings = helpers.getByName(getTelephonyProvidersEdgeApi().get_telephony_providers_edges_linebasesettings, name)
    if allLineBaseSettingsCache and base_settings is not None:
        allLineBaseSettingsCache[name] = base_settings
    return base_settings

def resolveLineBaseSettings(base_settings, use_cache=True):
    resolved_base_settings = None

    if not base_settings.id:
        if base_settings.name:

            if use_cache:
                global allLineBaseSettingsCache
                if allLineBaseSettingsCache is None:
                    allLineBaseSettingsCache = getAllLineBaseSettings()

                if base_settings.name in allLineBaseSettingsCache:
                    resolved_base_settings = allLineBaseSettingsCache[base_settings.name]
            
            if resolved_base_settings is None:
                resolved_base_settings = getLineBaseSettingsByName(base_settings.name)
                if use_cache:
                    allLineBaseSettingsCache[resolved_base_settings.name] = resolved_base_settings
            
            if resolved_base_settings is None:
                raise ValueError("No such line base setting [%s]" % base_settings.name)

            base_settings.id = resolved_base_settings.id

        else:
            raise ValueError("No line base settings id or name defined")

    return base_settings