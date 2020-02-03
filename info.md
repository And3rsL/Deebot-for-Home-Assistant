Home Assistant Custom Component for Ecovacs Deebot Ozmo 950

![Preview](prev.jpg)

With this Home Assistant Custom Component you'll be able to 
* play/pause
* locate
* send to home
* clean[auto|map|area]

You can use it with this configuration (same values as for the [official integration](https://www.home-assistant.io/integrations/ecovacs/) but the integration is called *deebot* instead of *ecovacs*:

```
# required fields
deebot:
  username: YOUR_ECOVACS_USERNAME
  password: YOUR_ECOVACS_PASSWORD
  country: YOUR_TWO_LETTER_COUNTRY_CODE
  continent: YOUR_TWO_LETTER_CONTINENT_CODE
``` 
