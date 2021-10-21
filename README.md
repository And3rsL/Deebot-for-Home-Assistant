[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
<br><a href="https://www.buymeacoffee.com/edenhaus" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-black.png" width="150px" height="35px" alt="Buy Me A Coffee" style="height: 35px !important;width: 150px !important;" ></a>

# Home Assistant Custom Component for Ecovacs vacuum cleaner

![Preview](docs/images/prev.jpg)

# Know working models:

- Deebot ozmo T8+
- Deebot ozmo T8
- Deebot ozmo T8 AIVI
- Deebot ozmo T5
- Deebot ozmo 960
- Deebot ozmo 950
- Deebot ozmo 920
- .. Possibly all models after 2019

### Other models:

- All non-ozmo devices may not work
- If your robot is working with Native Home Assistant integration that means it will not work with this custom component. please don't open an issue or ask for it.

## Description

With this Home Assistant Custom Component you'll be able to

- play/pause
- locate
- send to home
- clean[auto|map|area]
- track live map
- sensors
- and much more...

## Configuration

### Installation

To add your Ecovacs devices into your Home Assistant:

1. Install [HACS](https://hacs.xyz)
2. In HACS: Go to Integrations and search and install **Deebot for Home Assistant**
3. Setup the integration (HA Settings -> Integration -> Add -> Deebot for Home Assistant)
4. Configure as described below

### Chinese server Configuration

For chinese server username you require "short id" and password. short id look like "EXXXXXX". DO NOT USE YOUR MOBILE PHONE NUMBER, it won't work.

country: cn
continent: as (or ww)

Since these servers are in china and unless you are close to china, don't expect very fast response.

### Country and Continent code

#### country:

Your two-letter country code (us, uk, etc).

#### continent:

Your two-letter continent code (as, na, eu, ww).

```
TW, MY, JP, SG, TH, HK, IN, KR -> AS
US -> NA
FR, ES, UK, NO, MX, DE, PT, CH, AT, IT, NL, SE, BE, DK -> EU
Any other country -> WW
```

For some countries, you will need to set continent to ww (meaning worldwide.) There is unfortunately no way to know the correct settings other than guessing and checking.

Additional note: There are some issues during the password encoding. Using some special characters (e.g., -) in your password does not work.

### Sensors

This integration expose a number of sensors
**All sensors are disabled by default.** You can enable only the required ones.

- sensor.ROBOTNAME_last_clean_image (A URL to the last success clean -- the image is on the ecovacs servers)
- sensor.ROBOTNAME_brush (% main brush)
- sensor.ROBOTNAME_heap (% Filter)
- sensor.ROBOTNAME_sidebrush (% Side Brush)
- sensor.ROBOTNAME_stats_area (Last or in cleaning Mq2 area)
- sensor.ROBOTNAME_stats_time (Last or in cleaning Time)
- sensor.ROBOTNAME_stats_type (Clean Type - Auto|Manual|Custom)
- sensor.ROBOTNAME_water_level (Current set water level, you can get fan speed by vacuum attributes)
- binary_sensor.ROBOTNAME_mop_attached (On/off is mop is attached)
- camera.ROBOTNAME_liveMap The live map

## UI examples

UI examples can be found in the [examples folder](docs/examples)

## Templates

Example for fan_speed:

```
{{ states.vacuum.YOUR_ROBOT_NAME.attributes['fan_speed'] }}
```

Get room numbers dynamically, very helpful if your robot is multi-floor or if your robot lose the map and you don't want to change automations every time:

```
{{ states.vacuum.YOURROBOTNAME.attributes.room_bathroom }}
```

## Example commands:

```yaml
# Clean all
service: vacuum.start
target:
  entity_id: vacuum.YOUR_ROBOT_NAME
```

Relocate Robot (the little GPS icon in the APP)

```yaml
# Relocate Robot
service: vacuum.send_command
target:
  entity_id: vacuum.YOUR_ROBOT_NAME
data:
  command: relocate
```

You can clean certain area by specify it in rooms params, you can find room number under vacuum attributes

```yaml
# Clean Area
service: vacuum.send_command
target:
  entity_id: vacuum.YOUR_ROBOT_NAME
data:
  command: spot_area
  params:
    rooms: 10,14
    cleanings: 1
```

```yaml
# Customize Clean
service: vacuum.send_command
target:
  entity_id: vacuum.YOUR_ROBOT_NAME
data:
  command: custom_area
  params:
    coordinates: -1339,-1511,296,-2587
```

Use the app to send the vacuum to a custom area and afterwards search your logs for `Last custom area values (x1,y1,x2,y2):` entries to get the coordinates.

```yaml
# Set Water Level
# Possible amount values: low|medium|high|ultrahigh
service: vacuum.send_command
target:
  entity_id: vacuum.YOUR_ROBOT_NAME
data:
  command: set_water
  params:
    amount: ultrahigh
```

### Custom commands

It's also possible to send commands, which are not officially supported by this integration yet.
For that use also the `vacuum.send_command` service and you will get the response as `deebot_custom_command` event.

Example with the command `getAdvancedMode`

```yaml
service: vacuum.send_command
target:
  entity_id: vacuum.YOUR_ROBOT_NAME
data:
  command: getAdvancedMode
```

When calling the above example you will get the event `deebot_custom_command` similar to:

```json
{
  "event_type": "deebot_custom_command",
  "data": {
    "name": "getAdvancedMode",
    "response": {
      "header": {
        "pri": 1,
        "tzm": 480,
        "ts": "1295442034442",
        "ver": "0.0.1",
        "fwVer": "1.8.2",
        "hwVer": "0.1.1"
      },
      "body": {
        "code": 0,
        "msg": "ok",
        "data": {
          "enable": 1
        }
      }
    }
  },
  "origin": "LOCAL",
  "time_fired": "2021-10-05T21:45:40.294958+00:00",
  "context": {
    "id": "[REMOVED]",
    "parent_id": null,
    "user_id": null
  }
}
```

The interesting part is normally inside `response->body->data`. In the example above it means I have enabled the advanced mode.

## Services

This integration adds the service `deebot.refresh`, which allows to manually refresh some parts of the vacuum.
In addition to the vacuum entity you must specify part you want to refresh.
An example call looks like:

```yaml
service: deebot.refresh
data:
  part: Status
target:
  entity_id: vacuum.YOUR_ROBOT_NAME
```

## Issues

If you have an issue with this component, please create a GitHub Issue and include your Home Assistant logs in the report. To get full debug output from both the Ecovacs integration and the underlying deebotozmo library, place this in your configuration.yaml file:

```yaml
logger:
  logs:
    homeassistant.components.vacuum: debug
    custom_components.deebot: debug
    deebotozmo: debug
```

**Warning: Doing this will cause your authentication token to visible in your log files. Be sure to remove any tokens and other authentication details from your log before posting them in an issue.**

More information can be found in the [HA logger documentation](https://www.home-assistant.io/integrations/logger/)

## Misc

An SVG of the Deebot 950 can be found under [images](docs/images/deebot950.svg)
