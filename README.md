[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
<br><a href="https://www.buymeacoffee.com/4nd3rs" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-black.png" width="150px" height="35px" alt="Buy Me A Coffee" style="height: 35px !important;width: 150px !important;" ></a>

# Home Assistant Custom Component for Ecovacs vacuum cleaner

![Preview](images/prev.jpg)

# Know working models:
* Deebot ozmo T8+
* Deebot ozmo T8
* Deebot ozmo T8 AIVI
* Deebot ozmo T5
* Deebot ozmo 960
* Deebot ozmo 950
* Deebot ozmo 920
* .. Possibly all models after 2019

### Other models:
- All non-ozmo devices may not work
- If your robot is working with Native Home Assistant integration that means it will not work with this custom component. please don't open an issue or ask for it.

## Description
With this Home Assistant Custom Component you'll be able to 

* play/pause
* locate
* send to home
* clean[auto|map|area]
* track live map
* sensors
* and much more...

## Configuration
To add your Ecovacs devices into your Home Assistant installation, add the following to your configuration.yaml file:

```
# required fields
deebot:
  username: YOUR_ECOVACS_USERNAME
  password: YOUR_ECOVACS_PASSWORD
  country: YOUR_TWO_LETTER_COUNTRY_CODE
  continent: YOUR_TWO_LETTER_CONTINENT_CODE
  deviceid:
    - YOUR_ROBOT_ID
    - YOUR_ROBOT_ID2
    - etc...
  # Optional
  live_map: True                    # Enable Live Map.. may cause issues on low power hardware | Default: True
  show_color_rooms: False           # Enable draw room colors as in the app.. BE Carefull, very experimental. first thing to disable if there is any issue | Default: False
  livemappath: 'www/'   # Path where to save live_map (Each bot will have XXX_liveMap.png where XXX is the vacbot name)
``` 

### Chinese server Configuration
For chinese server username you require "short id" and password. short id look like "EXXXXXX". DO NOT USE YOUR MOBILE PHONE NUMBER, it wont work.

country: cn
continent: as (or ww)

Since these servers are in china and unless you are close to china, don't expect very fast response.

### DeviceID
You can find your robot id under settings and "About Deebot" or inside the robot (normally under dust bin)

![Preview](images/deviceid.jpg)

### Country and Continent code
#### country:
Your two-letter country code (us, uk, etc).

#### continent:
Your two-letter continent code (as, na, eu, ww).

```
TW, MY, JP, SG, TH, HK, IN, KR -> AS
US -> NA
FR, ES, UK, NO, MX, DE, PT, CH, AU, IT, NL, SE, BE, DK -> EU
Any other country -> WW
```

For some countries, you will need to set continent to ww (meaning worldwide.) There is unfortunately no way to know the correct settings other than guessing and checking.

Additional note: There are some issues during the password encoding. Using some special characters (e.g., -) in your password does not work.

### Sensors
This integration expose a number of sensors

* sensor.last_clean_image (A URL to the last success clean -- the image is on the ecovacs servers)
* sensor.ROBOTNAME_brush (% main brush)
* sensor.ROBOTNAME_heap (% Filter)
* sensor.ROBOTNAME_sidebrush (% Side Brush)
* sensor.ROBOTNAME_stats_area (Last or in cleaning Mq2 area)
* sensor.ROBOTNAME_stats_time (Last or in cleaning Time)
* sensor.ROBOTNAME_stats_type (Clean Type - Auto|Manual|Custom)
* sensor.ROBOTNAME_water_level (Current set water level, you can get fan speed by vacuum attributes)
* binary_sensor.ROBOTNAME_mop_attached (On/off is mop is attached)

### Live Map:
If is true live_map it will try to generate a live map in the specified folder
you can set a generic camera example:

Add Camera in configuration.yaml

```
camera:
  - platform: generic
    name: Deebot_live_map
    still_image_url: "http://YOURLOCALIP:8123/local/YOUR_ROBOT_NAME_liveMap.png" #Example configuration for livemappath: 'www/'
    verify_ssl: false
```

YAML interface:
```
type: picture-entity
entity: vacuum.YOUR_ROBOT_NAME
aspect_ratio: 50%
camera_image: camera.deebot_live_map
```

### Suggested yaml component
A suggested custom lovelace card that i use is: vacuum-card by denysdovhan link: https://github.com/denysdovhan/vacuum-card

My configuration:
```
type: 'custom:vacuum-card'
entity: vacuum.YOURROBOTNAME
image: default
compact_view: false
show_name: true
show_toolbar: true
show_status: true
stats:
  default:
    - entity_id: sensor.YOURROBOTNAME_sidebrush
      unit: '%'
      subtitle: Side Brush
    - entity_id: sensor.YOURROBOTNAME_brush
      unit: '%'
      subtitle: Main Brush
    - entity_id: sensor.YOURROBOTNAME_heap
      unit: '%'
      subtitle: Heap
  cleaning:
    - entity_id: sensor.YOURROBOTNAME_stats_area
      unit: m2
      subtitle: Area
    - entity_id: sensor.YOURROBOTNAME_stats_time
      unit: min
      subtitle: Time
actions:
  - service: script.CLEAN_LIVINGROOM
    icon: 'mdi:sofa'
  - service: script.CLEAN_BEDROOM
    icon: 'mdi:bed-empty'
  - service: script.CLEAN_ALL
    icon: 'mdi:robot-vacuum-variant'
map: camera.YOURLIVEMAP_CAMERA

```

Something like this should be the result:

![Preview](images/custom_vacuum_card.jpg)

### Templates
Example for fan_speed: 
```
{{ states.vacuum.YOUR_ROBOT_NAME.attributes['fan_speed'] }}
```

Get room numbers dynamically, very helpfull if your robot is multi-floor or if your robot lose the map and you don't want to change automations every time:
```
{{ states.vacuum.YOURROBOTNAME.attributes.room_bathroom }}
```

## Example commands:
Relocate Robot (the little GPS icon in the APP)

```
# Relocate Robot
entity_id: vacuum.YOUR_ROBOT_NAME
command: relocate
```

You can clean certain area by specify it in rooms params, you can find room number under vacuum attributes

```
# Clean Area
entity_id: vacuum.YOUR_ROBOT_NAME
command: spot_area
params:
  rooms: 10,14
  cleanings: 1
```

```
# Customize Clean
# You can get coordinates with fiddler and the official APP [Advance User]
entity_id: vacuum.YOUR_ROBOT_NAME
command: custom_area
params:
  coordinates: -1339,-1511,296,-2587
```

```
# Set Water Level
Possible amount values: low|medium|high|ultrahigh
example:

entity_id: vacuum.YOUR_ROBOT_NAME
command: set_water
params:
  amount: ultrahigh
```

```
# Clean
Possible values: auto
example:

entity_id: vacuum.YOUR_ROBOT_NAME
command: auto_clean
params:
  type: auto
```

### Issues
If you have an issue with this component, please file a GitHub Issue and include your Home Assistant logs in the report. To get full debug output from both the Ecovacs integration and the underlying deebotozmo library, place this in your configuration.yaml file:

```
logger:
  logs:
    homeassistant.components.deebot: debug
    homeassistant.components.vacuum.deebotozmo: debug
    deebotozmo: debug
```

YAML
Warning: doing this will cause your authentication token to visible in your log files. Be sure to remove any tokens and other authentication details from your log before posting them in an issue.

### Misc

An SVG of the Deebot 950 can be found under [images](images/deeboot950.svg)
