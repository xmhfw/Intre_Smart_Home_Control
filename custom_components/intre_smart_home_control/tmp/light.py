"""Platform for light integration."""
from __future__ import annotations

import logging
import json
from homeassistant.helpers.entity import DeviceInfo
# Import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_EFFECT,
    LightEntity,
    LightEntityFeature,
    ColorMode
)
from homeassistant.util.color import (
    value_to_brightness,
    brightness_to_value
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .intreiot.const import (DOMAIN, SUPPORTED_PLATFORMS)
from .intreiot.intreIot_module import (IntreIoTProduct,IntreIoTModule,IntreIotHome)
from .intreiot.intreIot_device import (IntreIotEntity)
from .intreiot.const import (DOMAIN, SUPPORTED_PLATFORMS)
from .intreiot.intreIot_client import IntreIoTClient
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    homes_info:dict = hass.data[DOMAIN]['products'][config_entry.entry_id]
    intreIot_client: IntreIoTClient = hass.data[DOMAIN]['intreIot_clients'][config_entry.entry_id]

    new_entities = []
    for homeid in homes_info:
        for productObj in homes_info[homeid].productObjList:
            for moduleObj in productObj._moduleObjList:
                if moduleObj.moduleEnable == 0:
                    continue
                if moduleObj.module_code == 'singleColorTemperatureLight':
                    new_entities.append(IntreLight(intreIot_client=intreIot_client,productObj=productObj,moduleObj=moduleObj,lightType='W'))
                elif moduleObj.module_code == 'dualColorTemperatureLight':
                    new_entities.append(IntreLight(intreIot_client=intreIot_client,productObj=productObj,moduleObj=moduleObj,lightType='CW'))
                elif moduleObj.module_code == 'RGBCWLight':
                    new_entities.append(IntreLight(intreIot_client=intreIot_client,productObj=productObj,moduleObj=moduleObj,lightType='CW'))
                    new_entities.append(IntreLight(intreIot_client=intreIot_client,productObj=productObj,moduleObj=moduleObj,lightType='RGB'))
                elif moduleObj.module_code == 'RGBWLight':
                    new_entities.append(IntreLight(intreIot_client=intreIot_client,productObj=productObj,moduleObj=moduleObj,lightType='W'))
                    new_entities.append(IntreLight(intreIot_client=intreIot_client,productObj=productObj,moduleObj=moduleObj,lightType='RGB'))
    if new_entities:
        async_add_entities(new_entities)

class IntreLight(IntreIotEntity,LightEntity):

    def __init__(self, intreIot_client:IntreIoTClient,productObj:IntreIoTProduct,moduleObj:IntreIoTModule,lightType:str) -> None:
        super().__init__(intreIot_client=intreIot_client,productObj=productObj, moduleObj=moduleObj,uniqueStr=lightType)
        self._attr_supported_color_modes = set()
        self._attr_color_mode = ColorMode.ONOFF
        self._onoff =self.getPropValue('onOff')=='1'
        self._brightness = int(self.getPropValue('brightness'))
        self._lightType = lightType
        if lightType== 'w':
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
            self._attr_color_mode = ColorMode.BRIGHTNESS  
        elif lightType== 'CW':
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._colortemp = int(self.getPropValue('colorTemperature'))
        elif lightType=='RGB':
            self._attr_supported_color_modes.add(ColorMode.RGB)
            self._attr_color_mode = ColorMode.RGB
            value = json.loads(self.getPropValue('rgb'))
            r= value['red']
            g= value['green']
            b= value['blue']
            self._rgb = (r<<16)|(g<<8)|(b<<0)

    def propValueNotify(self)->None:
        _LOGGER.error("propValueNotify->type=%s",self._lightType)
        self._onoff =self.getPropValue('onOff')=='1'
        self._brightness = int(self.getPropValue('brightness'))

        if self._lightType==1:
            self._colortemp = int(self.getPropValue('colorTemperature'))
        elif self._lightType==2:
            value = json.loads(self.getPropValue('rgb'))
            r= value['red']
            g= value['green']
            b= value['blue']
            self._rgb = (r<<16)|(g<<8)|(b<<0)
        return     

  
    @property
    def color_mode(self):
        return self._attr_color_mode
    
    @property
    def supported_color_modes(self):
        return self._attr_supported_color_modes
    
    @property
    def is_on(self) -> bool | None:
        return self._onoff

    @property
    def brightness(self) -> Optional[int]:
        return round(self._brightness*255/100,0) 

    @property
    def color_temp_kelvin(self) -> Optional[int]:
        return self._colortemp

    @property
    def rgb_color(self) -> Optional[tuple[int, int, int]]:
        """Return the rgb color value."""
        
        r = (self._rgb >> 16) & 0xFF
        g = (self._rgb >> 8) & 0xFF
        b = self._rgb & 0xFF
        _LOGGER.error("get rgb="+str(r)+" "+str(g)+" "+str(b))
        return r, g, b

    async def async_turn_on(self, **kwargs) -> None:
        #_LOGGER.error("get _colortemp %d",self._colortemp)
        await self.set_property_async(propKey='onOff',value=str(int(True)))
        self._onoff =True
        # brightness
        if ATTR_BRIGHTNESS in kwargs:
            brightness = round(kwargs[ATTR_BRIGHTNESS]*100/255,0)
            result = await self.set_property_async(propKey='brightness', value=brightness)
            self._brightness =brightness
        # color-temperature
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            result = await self.set_property_async(
                propKey='colorTemperature',
                value=kwargs[ATTR_COLOR_TEMP_KELVIN])
        # rgb color
        if ATTR_RGB_COLOR in kwargs:
            r = kwargs[ATTR_RGB_COLOR][0]
            g = kwargs[ATTR_RGB_COLOR][1]
            b = kwargs[ATTR_RGB_COLOR][2]
            self._rgb = (r << 16) | (g << 8) | b
            value={
                "red":r,
                "green":g,
                "blue":b
            }
            
            result = await self.set_property_async(propKey='rgb',value=json.dumps(value, ensure_ascii=False))

    async def async_turn_off(self, **kwargs) -> None:
        await self.set_property_async(propKey='onOff',value=str(int(False)))
        self._onoff =False


        