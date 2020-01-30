import hashlib
import logging
import time
from base64 import b64decode, b64encode
from collections import OrderedDict
from threading import Event
import threading
import sched
import random
import ssl
import requests
import stringcase
import os
import json
import datetime;

from sleekxmppfs import ClientXMPP, Callback, MatchXPath
from sleekxmppfs.exceptions import XMPPError

from paho.mqtt.client import Client  as ClientMQTT
from paho.mqtt import publish as MQTTPublish
from paho.mqtt import subscribe as MQTTSubscribe

_LOGGER = logging.getLogger(__name__)

# These consts define all of the vocabulary used by this library when presenting various states and components.
# Applications implementing this library should import these rather than hard-code the strings, for future-proofing.

CLEAN_MODE_AUTO = 'auto'
CLEAN_MODE_SPOT_AREA = 'spotArea'
CLEAN_MODE_CUSTOM_AREA = 'customArea'

CLEAN_ACTION_START = 'start'
CLEAN_ACTION_PAUSE = 'pause'
CLEAN_ACTION_RESUME = 'resume'

FAN_SPEED_QUIET = 'quiet'
FAN_SPEED_NORMAL = 'normal'
FAN_SPEED_MAX = 'max'
FAN_SPEED_MAXPLUS = 'max+'

CHARGE_MODE_RETURN = 'return'
CHARGE_MODE_RETURNING = 'returning'
CHARGE_MODE_CHARGING = 'charging'
CHARGE_MODE_IDLE = 'idle'

COMPONENT_SIDE_BRUSH = 'sideBrush'
COMPONENT_MAIN_BRUSH = 'brush'
COMPONENT_FILTER = 'heap'

CLEANING_STATES = {CLEAN_MODE_AUTO,CLEAN_MODE_CUSTOM_AREA, CLEAN_MODE_SPOT_AREA}
CHARGING_STATES = {CHARGE_MODE_CHARGING}

CLEAN_MODE_TO_ECOVACS = {
    CLEAN_MODE_AUTO: 'auto',
    CLEAN_MODE_SPOT_AREA: 'SpotArea',
	CLEAN_MODE_CUSTOM_AREA: 'customArea'
}

CLEAN_ACTION_TO_ECOVACS = {
    CLEAN_ACTION_START: 'start',
    CLEAN_ACTION_PAUSE: 'pause',
    CLEAN_ACTION_RESUME: 'resume'
}

CLEAN_ACTION_FROM_ECOVACS = {
    'start': CLEAN_ACTION_START,
    'pause': CLEAN_ACTION_PAUSE,
    'resume': CLEAN_ACTION_RESUME
}

CLEAN_MODE_FROM_ECOVACS = {
    'auto': CLEAN_MODE_AUTO,
    'spotArea': CLEAN_MODE_SPOT_AREA,
    'customArea': CLEAN_MODE_CUSTOM_AREA
}

FAN_SPEED_TO_ECOVACS = {
    FAN_SPEED_QUIET: 1000,
    FAN_SPEED_NORMAL: 0,
    FAN_SPEED_MAX: 1,
    FAN_SPEED_MAXPLUS: 2
}

FAN_SPEED_FROM_ECOVACS = {
    1000: FAN_SPEED_QUIET,
    0: FAN_SPEED_NORMAL,
    1: FAN_SPEED_MAX,
    2: FAN_SPEED_MAXPLUS
}

CHARGE_MODE_TO_ECOVACS = {
    CHARGE_MODE_RETURN: 'go',
    CHARGE_MODE_RETURNING: 'going',
    CHARGE_MODE_CHARGING: 'charging',
    CHARGE_MODE_IDLE: 'idle'
}

CHARGE_MODE_FROM_ECOVACS = {
    'going': CHARGE_MODE_RETURNING,
    'charging': CHARGE_MODE_CHARGING,
    'idle': CHARGE_MODE_IDLE
}

COMPONENT_TO_ECOVACS = {
    COMPONENT_MAIN_BRUSH: 'brush',
    COMPONENT_SIDE_BRUSH: 'sideBrush',
    COMPONENT_FILTER: 'heap'
}

COMPONENT_FROM_ECOVACS = {
    'brush': COMPONENT_MAIN_BRUSH,
    'sideBrush': COMPONENT_SIDE_BRUSH,
    'heap': COMPONENT_FILTER
}

def str_to_bool_or_cert(s):
    if s == 'True' or s == True:
        return True
    elif s == 'False' or s == False:
        return False    
    else:
        if not s == None:
            if os.path.exists(s): # User could provide a path to a CA Cert as well, which is useful for Bumper
                if os.path.isfile(s):
                    return s
                else:                
                    raise ValueError("Certificate path provided is not a file - {}".format(s))
        
        raise ValueError("Cannot covert {} to a bool or certificate path".format(s))
        

class EcoVacsAPI:
    CLIENT_KEY = "eJUWrzRv34qFSaYk"
    SECRET = "Cyu5jcR4zyK6QEPn1hdIGXB5QIDAQABMA0GC"
    PUBLIC_KEY = 'MIIB/TCCAWYCCQDJ7TMYJFzqYDANBgkqhkiG9w0BAQUFADBCMQswCQYDVQQGEwJjbjEVMBMGA1UEBwwMRGVmYXVsdCBDaXR5MRwwGgYDVQQKDBNEZWZhdWx0IENvbXBhbnkgTHRkMCAXDTE3MDUwOTA1MTkxMFoYDzIxMTcwNDE1MDUxOTEwWjBCMQswCQYDVQQGEwJjbjEVMBMGA1UEBwwMRGVmYXVsdCBDaXR5MRwwGgYDVQQKDBNEZWZhdWx0IENvbXBhbnkgTHRkMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDb8V0OYUGP3Fs63E1gJzJh+7iqeymjFUKJUqSD60nhWReZ+Fg3tZvKKqgNcgl7EGXp1yNifJKUNC/SedFG1IJRh5hBeDMGq0m0RQYDpf9l0umqYURpJ5fmfvH/gjfHe3Eg/NTLm7QEa0a0Il2t3Cyu5jcR4zyK6QEPn1hdIGXB5QIDAQABMA0GCSqGSIb3DQEBBQUAA4GBANhIMT0+IyJa9SU8AEyaWZZmT2KEYrjakuadOvlkn3vFdhpvNpnnXiL+cyWy2oU1Q9MAdCTiOPfXmAQt8zIvP2JC8j6yRTcxJCvBwORDyv/uBtXFxBPEC6MDfzU2gKAaHeeJUWrzRv34qFSaYkYta8canK+PSInylQTjJK9VqmjQ'
    MAIN_URL_FORMAT = 'https://eco-{country}-api.ecovacs.com/v1/private/{country}/{lang}/{deviceId}/{appCode}/{appVersion}/{channel}/{deviceType}'
    USER_URL_FORMAT = 'https://users-{continent}.ecouser.net:8000/user.do'
    PORTAL_URL_FORMAT = 'https://portal-{continent}.ecouser.net/api'

    USERSAPI = 'users/user.do'
    IOTDEVMANAGERAPI = 'iot/devmanager.do' # IOT Device Manager - This provides control of "IOT" products via RestAPI
    PRODUCTAPI = 'pim/product' # Leaving this open, the only endpoint known currently is "Product IOT Map" -  pim/product/getProductIotMap - This provides a list of "IOT" products.  Not sure what this provides the app.
        
      
    REALM = 'ecouser.net'

    def __init__(self, device_id, account_id, password_hash, country, continent, verify_ssl=True):
        self.meta = {
            'country': country,
            'lang': 'en',
            'deviceId': device_id,
            'appCode': 'i_eco_e',
            'appVersion': '1.3.5',
            'channel': 'c_googleplay',
            'deviceType': '1'
        }
        
        self.verify_ssl = str_to_bool_or_cert(verify_ssl)
        _LOGGER.debug("Setting up EcoVacsAPI")
        self.resource = device_id[0:8]
        self.country = country
        self.continent = continent
        login_info = self.__call_main_api('user/login',
                                          ('account', self.encrypt(account_id)),
                                          ('password', self.encrypt(password_hash)))
        self.uid = login_info['uid']
        self.login_access_token = login_info['accessToken']
        self.auth_code = self.__call_main_api('user/getAuthCode',
                                              ('uid', self.uid),
                                              ('accessToken', self.login_access_token))['authCode']
        login_response = self.__call_login_by_it_token()
        self.user_access_token = login_response['token']
        if login_response['userId'] != self.uid:
            logging.debug("Switching to shorter UID " + login_response['userId'])
            self.uid = login_response['userId']
        logging.debug("EcoVacsAPI connection complete")

    def __sign(self, params):
        result = params.copy()
        result['authTimespan'] = int(time.time() * 1000)
        result['authTimeZone'] = 'GMT-8'

        sign_on = self.meta.copy()
        sign_on.update(result)
        sign_on_text = EcoVacsAPI.CLIENT_KEY + ''.join(
            [k + '=' + str(sign_on[k]) for k in sorted(sign_on.keys())]) + EcoVacsAPI.SECRET

        result['authAppkey'] = EcoVacsAPI.CLIENT_KEY
        result['authSign'] = self.md5(sign_on_text)
        return result

    def __call_main_api(self, function, *args):
        _LOGGER.debug("calling main api {} with {}".format(function, args))
        params = OrderedDict(args)
        params['requestId'] = self.md5(time.time())
        url = (EcoVacsAPI.MAIN_URL_FORMAT + "/" + function).format(**self.meta)
        api_response = requests.get(url, self.__sign(params), verify=self.verify_ssl)
        json = api_response.json()
        _LOGGER.debug("got {}".format(json))
        if json['code'] == '0000':
            return json['data']
        elif json['code'] == '1005':
            _LOGGER.warning("incorrect email or password")
            raise ValueError("incorrect email or password")
        else:
            _LOGGER.error("call to {} failed with {}".format(function, json))
            raise RuntimeError("failure code {} ({}) for call {} and parameters {}".format(
                json['code'], json['msg'], function, args))

    def __call_user_api(self, function, args):
        _LOGGER.debug("calling user api {} with {}".format(function, args))
        params = {'todo': function}
        params.update(args)
        response = requests.post(EcoVacsAPI.USER_URL_FORMAT.format(continent=self.continent), json=params, verify=self.verify_ssl)
        json = response.json()
        _LOGGER.debug("got {}".format(json))
        if json['result'] == 'ok':
            return json
        else:
            _LOGGER.error("call to {} failed with {}".format(function, json))
            raise RuntimeError(
                "failure {} ({}) for call {} and parameters {}".format(json['error'], json['errno'], function, params))

    def __call_portal_api(self, api, function, args, verify_ssl=True, **kwargs):      
        
        if api == self.USERSAPI:
            params = {'todo': function}
            params.update(args)
        else:
            params = {}
            params.update(args)

        _LOGGER.debug("calling portal api {} function {} with {}".format(api, function, params))            
        
        continent = self.continent
        if 'continent' in kwargs:
            continent = kwargs.get('continent')

        url = (EcoVacsAPI.PORTAL_URL_FORMAT + "/" + api).format(continent=continent, **self.meta)        
        
        response = requests.post(url, json=params, verify=verify_ssl)        

        json = response.json()
        _LOGGER.debug("got {}".format(json))
        if api == self.USERSAPI:    
            if json['result'] == 'ok':
                _LOGGER.debug("RESULT OK")
                return json
            elif json['result'] == 'fail':
                if json['error'] == 'set token error.': # If it is a set token error try again
                    if not 'set_token' in kwargs:      
                        _LOGGER.warning("loginByItToken set token error, trying again (2/3)")              
                        return self.__call_portal_api(self.USERSAPI, function, args, verify_ssl=verify_ssl, set_token=1)
                    elif kwargs.get('set_token') == 1:
                        _LOGGER.warning("loginByItToken set token error, trying again with ww (3/3)")              
                        return self.__call_portal_api(self.USERSAPI, function, args, verify_ssl=verify_ssl, set_token=2, continent="ww")
                    else:
                        _LOGGER.warning("loginByItToken set token error, failed after 3 attempts")
                                    
        if api.startswith(self.PRODUCTAPI):
            if json['code'] == 0:
                return json      

        else:
            _LOGGER.error("call to {} failed with {}".format(function, json))
            raise RuntimeError(
                "failure {} ({}) for call {} and parameters {}".format(json['error'], json['errno'], function, params))

    def __call_login_by_it_token(self):
        return self.__call_portal_api(self.USERSAPI,'loginByItToken',
                                    {'country': self.meta['country'].upper(),
                                     'resource': self.resource,
                                     'realm': EcoVacsAPI.REALM,
                                     'userId': self.uid,
                                     'token': self.auth_code}
                                    , verify_ssl=self.verify_ssl)
  
    def getdevices(self):
        return  self.__call_portal_api(self.USERSAPI,'GetDeviceList', {
            'userid': self.uid,
            'auth': {
                'with': 'users',
                'userid': self.uid,
                'realm': EcoVacsAPI.REALM,
                'token': self.user_access_token,
                'resource': self.resource
            }
        }, verify_ssl=self.verify_ssl)['devices']

    def getiotProducts(self):
        return self.__call_portal_api(self.PRODUCTAPI + '/getProductIotMap','', {
            'channel': '',
            'auth': {
                'with': 'users',
                'userid': self.uid,
                'realm': EcoVacsAPI.REALM,
                'token': self.user_access_token,
                'resource': self.resource
            }
        }, verify_ssl=self.verify_ssl)['data']

    def SetIOTDevices(self, devices, iotproducts):
        #Originally added for D900, and not actively used in code now - Not sure what the app checks the items in this list for
        for device in devices: #Check if the device is part of iotProducts
            device['iot_product'] = False
            for iotProduct in iotproducts:
                if device['class'] in iotProduct['classid']:
                    device['iot_product'] = True
                    
        return devices

    def SetIOTMQDevices(self, devices):
        #Added for devices that utilize MQTT
        for device in devices:
            if device['company'] == 'eco-ng': #Check if the device is part of the list
                device['iotmq'] = True

        return devices
       
    def devices(self):
        return self.SetIOTMQDevices(self.getdevices())

    @staticmethod
    def md5(text):
        return hashlib.md5(bytes(str(text), 'utf8')).hexdigest()

    @staticmethod
    def encrypt(text):
        from Crypto.PublicKey import RSA
        from Crypto.Cipher import PKCS1_v1_5
        key = RSA.import_key(b64decode(EcoVacsAPI.PUBLIC_KEY))
        cipher = PKCS1_v1_5.new(key)
        result = cipher.encrypt(bytes(text, 'utf8'))
        return str(b64encode(result), 'utf8')


class EventEmitter(object):
    """A very simple event emitting system."""
    def __init__(self):
        self._subscribers = []

    def subscribe(self, callback):
        listener = EventListener(self, callback)
        self._subscribers.append(listener)
        return listener

    def unsubscribe(self, listener):
        self._subscribers.remove(listener)

    def notify(self, event):
        for subscriber in self._subscribers:
            subscriber.callback(event)


class EventListener(object):
    """Object that allows event consumers to easily unsubscribe from events."""
    def __init__(self, emitter, callback):
        self._emitter = emitter
        self.callback = callback

    def unsubscribe(self):
        self._emitter.unsubscribe(self)

class VacBot():
    def __init__(self, user, domain, resource, secret, vacuum, continent, server_address=None, monitor=False, verify_ssl=True):

        self.vacuum = vacuum

        # If True, the VacBot object will handle keeping track of all statuses,
        # including the initial request for statuses, and new requests after the
        # VacBot returns from being offline. It will also cause it to regularly
        # request component lifespans
        self._monitor = monitor

        self._failed_pings = 0
        self.is_available = False

        # These three are representations of the vacuum state as reported by the API
        self.battery_status = None

        # This is an aggregate state managed by the deebotozmo library, combining the clean and charge events to a single state
        self.vacuum_status = None
        self.fan_speed = None

        # Populated by component Lifespan reports
        self.components = {}

        self.statusEvents = EventEmitter()
        self.batteryEvents = EventEmitter()
        self.lifespanEvents = EventEmitter()
        self.fanspeedEvents = EventEmitter()
        self.errorEvents = EventEmitter()

        #Set none for clients to start        
        self.iotmq = None
        
        self.iotmq = EcoVacsIOTMQ(user, domain, resource, secret, continent, vacuum, server_address, verify_ssl=verify_ssl)
        self.iotmq.subscribe_to_ctls(self._handle_ctl)

    def connect_and_wait_until_ready(self):
        self.iotmq.connect_and_wait_until_ready()
        self.iotmq.schedule(30, self.send_ping)   

        if self._monitor:
            # Do a first ping, which will also fetch initial statuses if the ping succeeds
            self.send_ping()
            self.iotmq.schedule(300,self.refresh_components)
            self.iotmq.schedule(30,self.refresh_statuses)

    def _handle_ctl(self, ctl):
        method = '_handle_' + ctl['event']
        if hasattr(self, method):
            getattr(self, method)(ctl)

    def _handle_error(self, event):
        if 'error' in event:
            error = event['error']
        elif 'errs' in event:
            error = event['errs']

        if not error == '':
            self.errorEvents.notify(error)
            _LOGGER.warning("*** error = " + error)

    def _handle_life_span(self, event):
        response = event['body']['data'][0]
        type = response['type']

        try:
            type = COMPONENT_FROM_ECOVACS[type]
        except KeyError:
            _LOGGER.warning("Unknown component type: '" + type + "'")
            
        left = int(response['left'])
        total = int(response['total'])
			
        lifespan = (left/total) * 100
       
        self.components[type] = lifespan
        
        lifespan_event = {'type': type, 'lifespan': lifespan}
        self.lifespanEvents.notify(lifespan_event)
        _LOGGER.debug("*** life_span " + type + " = " + str(lifespan))

    def _handle_fan_speed(self, event):
        response = event['body']['data']
        speed = response['speed']

        try:
            speed = FAN_SPEED_FROM_ECOVACS[speed]
        except KeyError:
            _LOGGER.warning("Unknown fan speed: '" + str(speed) + "'")
      
        self.fan_speed = speed
        
        self.fanspeedEvents.notify(speed)
        _LOGGER.debug("*** fan_speed = {}".format(speed))

    def _handle_clean_report(self, event):
        response = event['body']['data']
        if response['state'] == 'clean':
            if response['trigger'] == 'app':
                if response['cleanState']['motionState'] == 'working':
                    self.vacuum_status = 'STATE_CLEANING'
                elif response['cleanState']['motionState'] == 'pause':
                    self.vacuum_status = 'STATE_PAUSED'
                else:
                    self.vacuum_status = 'STATE_RETURNING'
            elif response['trigger'] == 'alert':
                self.vacuum_status = 'STATE_ERROR'

            self.statusEvents.notify(self.vacuum_status)

    def _handle_battery_info(self, event):
        response = event['body']
        try:
            self.battery_status = response['data']['value']
        except ValueError:
            _LOGGER.warning("couldn't parse battery status " + response)
        else:
            self.batteryEvents.notify(self.battery_status)

        _LOGGER.debug("*** battery_status = {} %".format(self.battery_status))

    def _handle_charge_state(self, event):
        response = event['body']
        
        if response['code'] == 0:
            if response['data']['isCharging'] == 1:
                status = 'STATE_DOCKED'
        else:
            if response['msg'] == 'fail' and response['code'] == '30007': #Already charging
                status = 'STATE_DOCKED'
            elif response['msg'] == 'fail' and response['code'] == '5': #Busy with another command
                status = 'STATE_ERROR'
            elif response['msg'] == 'fail' and response['code'] == '3': #Bot in stuck state, example dust bin out
                status = 'STATE_ERROR'
            else: 
                _LOGGER.error("Unknown charging status '" + event['errno'] + "'") #Log this so we can identify more errors    

        if status != '':
            self.vacuum_status = status
            self.statusEvents.notify(self.vacuum_status)
        _LOGGER.debug("*** vacuum_status = " + self.vacuum_status)

    def _vacuum_address(self):
        return self.vacuum['did'] #IOTMQ only uses the did

    def send_ping(self):
        try:
            if not self.iotmq.send_ping():
                raise RuntimeError()                
            else:
                self.is_available = True
        except XMPPError as err:
            _LOGGER.warning("Ping did not reach VacBot. Will retry.")
            _LOGGER.warning("*** Error type: " + err.etype)
            _LOGGER.warning("*** Error condition: " + err.condition)
            self._failed_pings += 1
            if self._failed_pings >= 4:
                self.is_available = False

        except RuntimeError as err:
            _LOGGER.warning("Ping did not reach VacBot. Will retry.")
            self._failed_pings += 1
            if self._failed_pings >= 4:
                self.is_available = False

        else:
            self._failed_pings = 0
            if self._monitor:
                # If we don't yet have a vacuum status, request initial statuses again now that the ping succeeded
                if self.is_available == False or self.vacuum_status is None:
                    self.request_all_statuses()
                    self.is_available == True
            else:
                # If we're not auto-monitoring the status, then just reset the status to None, which indicates unknown
                if self.is_available == False:
                    self.is_available = None

    def refresh_components(self):
        try:
            self.exc_command('getLifeSpan',[COMPONENT_TO_ECOVACS["brush"]])
            self.exc_command('getLifeSpan',[COMPONENT_TO_ECOVACS["sideBrush"]])
            self.exc_command('getLifeSpan',[COMPONENT_TO_ECOVACS["heap"]])
        except XMPPError as err:
            _LOGGER.warning("Component refresh requests failed to reach VacBot. Will try again later.")
            _LOGGER.warning("*** Error type: " + err.etype)
            _LOGGER.warning("*** Error condition: " + err.condition)

    
    def refresh_statuses(self):
        try:
            self.exc_command('getCleanInfo')
            self.exc_command('getChargeState')
            self.exc_command('getBattery')
            self.exc_command('getSpeed')
        except XMPPError as err:
            _LOGGER.warning("Initial status requests failed to reach VacBot. Will try again on next ping.")
            _LOGGER.warning("*** Error type: " + err.etype)
            _LOGGER.warning("*** Error condition: " + err.condition)

    def request_all_statuses(self):
        self.refresh_statuses()
        self.refresh_components()

	#Common ecovacs commands
    def Clean(self, type='auto'):
        self.exc_command('clean', {'act': CLEAN_ACTION_START,'type': type})
        self.refresh_statuses()

    def CleanPause(self):
        self.exc_command('clean', {'act': CLEAN_ACTION_PAUSE})
        self.refresh_statuses()

    def CleanResume(self):
        if self.vacuum_status == 'STATE_PAUSED':
            self.exc_command('clean', {'act': CLEAN_ACTION_RESUME})
        else:
            self.exc_command('clean', {'act': CLEAN_ACTION_START,'type': 'auto'})

        self.refresh_statuses()

    def Charge(self):
        self.exc_command('charge', {'act': CHARGE_MODE_TO_ECOVACS['return']})
        self.refresh_statuses()

    def PlaySound(self):
        self.exc_command('playSound', {'count': 1, 'sid': 30})

    def Relocate(self):
        self.exc_command('setRelocationState', {'mode': 'manu'})
		
    def SpotArea(self, area='', map_position='', cleanings=1):
        if area != '': #For cleaning specified area
            self.exc_command('clean', {'act': 'start', 'content': area, 'count': cleanings, 'type': 'spotArea'})
            self.refresh_statuses()
        elif map_position != '': #For cleaning custom map area, and specify deep amount 1x/2x
            self.exc_command('clean', {'act': 'start', 'content': map_position, 'count': cleanings, 'type': 'customArea'})
            self.refresh_statuses()
        else:
            #no valid entries
            raise ValueError("must provide area or map_position for spotarea clean")

    def SetFanSpeed(self, speed=0):
        self.exc_command('setSpeed', {'speed': FAN_SPEED_TO_ECOVACS[speed]})

    def exc_command(self, action, params=None, **kwargs):
        #_LOGGER.debug(params)
        self.send_command(VacBotCommand(action, params))

    def send_command(self, action):
        #IOTMQ issues commands via RestAPI, and listens on MQTT for status updates
        self.iotmq.send_command(action, self._vacuum_address())  #IOTMQ devices need the full action for additional parsing

    def disconnect(self, wait=False):
        self.iotmq._disconnect()              

#This is used by EcoVacsIOTMQ for _ctl_to_dict
def RepresentsInt(stringvar):
    try: 
        int(stringvar)
        return True
    except ValueError:
        return False

class EcoVacsIOTMQ(ClientMQTT):
    def __init__(self, user, domain, resource, secret, continent, vacuum, server_address=None, verify_ssl=True):
        ClientMQTT.__init__(self)
        self.ctl_subscribers = []        
        self.user = user
        self.domain = str(domain).split(".")[0] #MQTT is using domain without tld extension
        self.resource = resource
        self.secret = secret
        self.continent = continent
        self.vacuum = vacuum
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.scheduler_thread = threading.Thread(target=self.scheduler.run, daemon=True, name="mqtt_schedule_thread")
        self.verify_ssl = str_to_bool_or_cert(verify_ssl)
        
        if server_address is None: 	
            self.hostname = ('mq-{}.ecouser.net'.format(self.continent))
            self.port = 8883
        else:
            saddress = server_address.split(":")
            if len(saddress) > 1:
                self.hostname = saddress[0]
                if RepresentsInt(saddress[1]):
                    self.port = int(saddress[1])
                else:
                    self.port = 8883                    

        self._client_id = self.user + '@' + self.domain.split(".")[0] + '/' + self.resource        
        self.username_pw_set(self.user + '@' + self.domain, secret)

        self.ready_flag = Event()

    def connect_and_wait_until_ready(self):        
        self._on_log = self.on_log #This provides more logging than needed, even for debug
        self._on_message = self._handle_ctl_mqtt
        self._on_connect = self.on_connect        

        #TODO: This is pretty insecure and accepts any cert, maybe actually check?
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        self.tls_set_context(ssl_ctx)
        self.tls_insecure_set(True)
        self.connect(self.hostname, self.port)
        self.loop_start()        
        self.wait_until_ready()

    def subscribe_to_ctls(self, function):
        self.ctl_subscribers.append(function)   

    def _disconnect(self):
        self.disconnect() #disconnect mqtt connection
        self.scheduler.empty() #Clear schedule queue  

    def _run_scheduled_func(self, timer_seconds, timer_function):
        timer_function()
        self.schedule(timer_seconds, timer_function)

    def schedule(self, timer_seconds, timer_function):
        self.scheduler.enter(timer_seconds, 1, self._run_scheduled_func,(timer_seconds, timer_function))
        if not self.scheduler_thread.isAlive():
            self.scheduler_thread.start()
        
    def wait_until_ready(self):
        self.ready_flag.wait()

    def on_connect(self, client, userdata, flags, rc):        
        if rc != 0:
            _LOGGER.error("EcoVacsMQTT - error connecting with MQTT Return {}".format(rc))
            raise RuntimeError("EcoVacsMQTT - error connecting with MQTT Return {}".format(rc))
                 
        else:
            _LOGGER.debug("EcoVacsMQTT - Connected with result code "+str(rc))
            _LOGGER.debug("EcoVacsMQTT - Subscribing to all")        

            self.subscribe('iot/atr/+/' + self.vacuum['did'] + '/' + self.vacuum['class'] + '/' + self.vacuum['resource'] + '/+', qos=0)            
            self.ready_flag.set()

    def send_ping(self):
        _LOGGER.debug("*** MQTT sending ping ***")
        rc = self._send_simple_command(MQTTPublish.paho.PINGREQ)
        if rc == MQTTPublish.paho.MQTT_ERR_SUCCESS:
            return True         
        else:
            return False

    def send_command(self, action, recipient):
        c = self._wrap_command(action, recipient)
        _LOGGER.debug('Sending command {0}'.format(c))        

        self._handle_ctl_api(action, 
            self.__call_iotdevmanager_api(c ,verify_ssl=self.verify_ssl )
            )
			
    def _wrap_command(self, cmd, recipient):
        #All requests need to have this header -- not sure about timezone and ver
        payloadRequest = OrderedDict()
			
        payloadRequest['header'] = OrderedDict()
        payloadRequest['header']['pri'] = '2'
        payloadRequest['header']['ts'] = datetime.datetime.now().timestamp()
        payloadRequest['header']['tmz'] = 480
        payloadRequest['header']['ver'] = '0.0.22'
        
        if len(cmd.args) > 0:
            payloadRequest['body'] = OrderedDict()
            payloadRequest['body']['data'] = cmd.args
			
        payload = payloadRequest
        payloadType = "j"

        return {
            'auth': {
                'realm': EcoVacsAPI.REALM,
                'resource': self.resource,
                'token': self.secret,
                'userid': self.user,
                'with': 'users',
            },
            "cmdName": cmd.name,            
            "payload": payload,  
                      
            "payloadType": payloadType,
            "td": "q",
            "toId": recipient,
            "toRes": self.vacuum['resource'],
            "toType": self.vacuum['class']
        }     

    def __call_iotdevmanager_api(self, args, verify_ssl=True):
        _LOGGER.debug("calling iotdevmanager api with {}".format(args))                
        params = {}
        params.update(args)

        url = (EcoVacsAPI.PORTAL_URL_FORMAT + "/iot/devmanager.do?mid=" + params['toType'] + "&did=" + params['toId'] + "&td=" + params['td'] + "&u=" + params['auth']['userid'] + "&cv=1.67.3&t=a&av=1.3.1").format(continent=self.continent)
        response = None        
        try: #The RestAPI sometimes doesnt provide a response depending on command, reduce timeout to 3 to accomodate and make requests faster
            headers = {
                        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)',
            }
            response = requests.post(url,headers=headers, json=params, timeout=60, verify=verify_ssl) #May think about having timeout as an arg that could be provided in the future
        except requests.exceptions.ReadTimeout:
            _LOGGER.warning("call to iotdevmanager failed with ReadTimeout")
            return {}                
        
        json = response.json()
        if json['ret'] == 'ok':
            return json
        elif json['ret'] == 'fail':
            if 'debug' in json:
                if json['debug'] == 'wait for response timed out': 
                    #TODO - Maybe handle timeout for IOT better in the future
                    _LOGGER.warning("call to iotdevmanager failed with {}".format(json))
                    return {}
            else:
                #TODO - Not sure if we want to raise an error yet, just return empty for now
                _LOGGER.error("call to iotdevmanager failed with {}".format(json))
                return {}

    def _handle_ctl_api(self, action, message):
        if not message == {}:
            resp = self._ctl_to_dict_api(action, message['resp'])
            if resp is not None:
                for s in self.ctl_subscribers:
                    s(resp)       

    def _ctl_to_dict_api(self, action, jsonstring):
        if jsonstring['body']['msg'] == 'ok':
            eventname = action.name 
            _LOGGER.debug('BEFORE Status:' + eventname.lower())
            if 'cleaninfo' in eventname.lower():
                jsonstring['event'] = "clean_report"
            elif 'chargestate' in eventname.lower():
                jsonstring['event'] = "charge_state"
            elif 'battery' in eventname.lower():
                jsonstring['event'] = "battery_info"
            elif 'lifespan' in eventname.lower():
                jsonstring['event'] = "life_span"
            elif 'getspeed' in eventname.lower():
                jsonstring['event'] = "fan_speed"
            else:
                _LOGGER.debug('UKNOWN Status:' + eventname.lower())
                return
				
        else:
            if jsonstring['body']['msg'] == 'fail':
                if action.name == "charge": #So far only seen this with Charge, when already docked
                    jsonstring['event'] = "charge_state"
                return
            else:
                return

        _LOGGER.debug("LOGGED EVENT: " + jsonstring['event'])
        return jsonstring

    def _handle_ctl_mqtt(self, client, userdata, message):
        #_LOGGER.warning("EcoVacs MQTT Received Message on Topic: {} - Message: {}".format(message.topic, str(message.payload.decode("utf-8"))))
        as_dict = self._ctl_to_dict_api(message.topic, str(message.payload.decode("utf-8")))
        if as_dict is not None:
            for s in self.ctl_subscribers:
                s(as_dict)

class VacBotCommand:
    def __init__(self, name, args=None, **kwargs):
        if args is None:
            args = {}
        self.name = name
        self.args = args

    def __str__(self, *args, **kwargs):
        return self.command_name() + " command"

    def command_name(self):
        return self.__class__.__name__.lower()