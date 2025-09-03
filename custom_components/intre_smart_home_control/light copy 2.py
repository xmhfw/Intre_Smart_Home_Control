"""Platform for light integration.
from __future__ import annotations
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
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
"""
import asyncio
import base64
import json
import logging
import re
import time
import hmac
import hashlib
import paho.mqtt.client as mqtt
from typing import Any, Callable, Optional, final
from urllib.parse import urlencode
import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntries
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import (Entity,DeviceInfo)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .intreiot.intreIot_module import (IntreIoTProduct,IntreIoTModule)
from .intreiot.intre_manage_engine import (IntreManagementEngine)
from .intreiot.const   import (DOMAIN, SUPPORTED_PLATFORMS)
from .intreiot.intreIot_client import IntreIoTClient
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    intre_ss:IntreManagementEngine =hass.data[DOMAIN]['intre_ss'][config_entry.entry_id]
    _hadevices = hass.data[DOMAIN]['config_data']['_hadevices']

    for hadevice in _hadevices:
        product = hadevice['product']
        entitys = hadevice['entitys']
        for entity in entitys:
            entity_entry = entity.get('entry')
            entity_id = entity_entry.entity_id
            
            #_LOGGER.debug('light create11111'+entity['entry'].entity_id)
            if entity_id.split(".")[0]== 'light':
                _LOGGER.debug(f"entity_id: {entity_id}")
                state = hass.states.get(entity_id)
                _LOGGER.debug("Brightness light.")
                _LOGGER.debug(state)
                if state is not None:
                    attributes = state.attributes
                    supported_color_modes = attributes.get('supported_color_modes', 'N/A')
                    brightness = attributes.get('brightness', 'N/A')
                    color_temp_support = "color_temp" in supported_color_modes
                    rgb_support = "rgb_color" in supported_color_modes

                    module_info={}
                    # 判断逻辑
                    if color_temp_support and not rgb_support:
                        # 纯色温调节（双色温或单色温）
                        min_kelvin = attributes.get("min_color_temp_kelvin", 0)
                        max_kelvin = attributes.get("max_color_temp_kelvin", 0)
                        if max_kelvin - min_kelvin > 2000:  # 宽色温范围（如1600K-7042K）
                            light_type = "高性能双色温灯（支持宽色温调节）"
                            module_info['moduleCode'] = 'dualColorTemperatureLight'
                        else:
                            light_type = "单色温可调灯"
                            module_info['moduleCode'] = 'singleColorTemperatureLight'  
                    elif rgb_support:
                        # RGB全彩灯
                        if color_temp_support:
                            light_type = "RGBCW"
                            module_info['moduleCode'] = 'RGBCWLight' 
                        else:
                            light_type = "RGBW"
                            module_info['moduleCode'] = 'RGBWLight' 
                    else:
                        light_type = "基础单色灯（仅亮度调节）"
                        module_info['moduleCode'] = 'singleColorTemperatureLight' 
                    _LOGGER.debug(f"灯具类型：{light_type} | 支持模式：{supported_color_modes}")
                '''
                _LOGGER.debug(state)
                #if state is not None:
                attributes = state.attributes
                brightness = attributes.get('brightness', 'N/A')
                color_temp = attributes.get('color_temp', 'N/A')
                hs_color = attributes.get('hs_color', 'N/A')
                rgb_color = attributes.get('rgb_color', 'N/A')
                max_color_temp_kelvin = attributes.get('max_color_temp_kelvin', 'N/A')
                min_color_temp_kelvin = attributes.get('min_color_temp_kelvin', 'N/A') 
                supported_color_modes = attributes.get('supported_color_modes', 'N/A') 
                
                if 
                _LOGGER.debug(f"实体 {entity_id} 的颜色属性:")
                _LOGGER.debug(f"  hs_color: {attributes.get('hs_color')}")
                _LOGGER.debug(f"  rgb_color: {attributes.get('rgb_color')}")
                _LOGGER.debug(f"  xy_color: {attributes.get('xy_color')}")
                '''

                #if 'brightness' in supported_features and 'color_temp' in supported_features and 'color' not in supported_features:
                #    _LOGGER.debug(f'{entity_name} 是双色温灯')
                module_info['moduleKey']=entity['entry'].entity_id
                module_info['moduleName']= entity['entry'].name
                module_info['entity_id']= entity['entry'].entity_id
                light :IntreLight = IntreLight(intre_ss=intre_ss,product=product,module_info=module_info)
                product.add_modules(light)

class IntreLight(IntreIoTModule):
    _product:IntreIoTProduct
    _intre_ss:IntreManagementEngine

    def __init__(self,intre_ss:IntreManagementEngine,product:IntreIoTProduct,module_info:dict) -> None:
        super().__init__(module_info=module_info)
        _LOGGER.debug('Initializing IntreLight...')
        self._intre_ss=intre_ss
        self._product=product
        self.state = None
        self.attributes = dict
        self.module_info={}
        self._intre_ss.sub_entity(self._entity_id,self._entity_state_notify)
        self._product.sub_prop_set(self._module_key,self.attr_change_req)
        self._product.sub_service_call(self._module_key,self.service_call_req)

    @final
    def get_module_json(self)->dict:
        timestamp_ms = str(int(time.time() * 1000))
        return {
            "templateModuleKey":'dualColorTemperatureLight_1',
            "instanceModuleKey": self._module_key,
            "propertyList": [
                {
                "propertyKey": "onOff",
                "propertyValue": "1",
                "timestamp": timestamp_ms
                },
                {
                "propertyKey": "brightness",
                "propertyValue": "0",
                "timestamp": timestamp_ms
                },
                {
                "propertyKey": "colorTemperature",
                "propertyValue": "4000",
                "dataDefineValue": {
                        "dataType": "int",
                        "required": 1,
                        "specs": {
                            "min": "1600",
                            "max": "7042",
                            "unit": "K",
                            "unitName": "开尔文",
                            "step": "1"
                    },
                    "specsExt": {
                        "minmin": "1600",
                        "minmax": "7042",
                        "maxmin": "1600",
                        "maxmax": "7042"
                    },
                "timestamp": timestamp_ms
                }
                }                            
            ]
        }   

    async def _entity_state_notify(self,newstate)->None:
        _LOGGER.debug(newstate)
        attributes = newstate.attributes
        brightness = attributes.get('brightness', 'N/A')
        color_temp = attributes.get('color_temp', 'N/A')
        color = attributes.get('color', 'N/A')
        max_color_temp_kelvin = attributes.get('max_color_temp_kelvin', 'N/A')
        min_color_temp_kelvin = attributes.get('min_color_temp_kelvin', 'N/A')       
        supported_color_modes = attributes.get('supported_color_modes', 'N/A') 
        _LOGGER.debug(
            f"Light Current state: {newstate.state}, Entity ID: {newstate.entity_id},Color: {color} "
            f"Brightness: {brightness}, Color Temp: {color_temp}, Max Color Temp Kelvin: {max_color_temp_kelvin},Min: {min_color_temp_kelvin}"
            f"supported_color_modes: {supported_color_modes}"           
        )

        #_LOGGER.debug(f"Light Current state: {newstate.state,newstate.entity_id,newstate.attributes['brightness'],newstate.attributes['color_temp'],newstate.attributes['max_color_temp_kelvin']}")   
        #OnOff
        if newstate.state =='on':
            await self._intre_ss.report_prop_async(self._product.productKey,self._product.deviceId,self._module_key,'onOff','1')
        else:
            await self._intre_ss.report_prop_async(self._product.productKey,self._product.deviceId,self._module_key,'onOff','0')
        #brightness
        if 'brightness' not in newstate.attributes:
            _LOGGER.debug("Brightness key not found in state attributes.")
        else:
            # 获取 brightness 值并检查类型
            brightness_value = newstate.attributes['brightness']
            if not isinstance(brightness_value, (int, float)):
                _LOGGER.debug("Brightness value is not a number.")
            else:
                brightness_normalized = int(brightness_value / 2.55)
            # 调用报告属性方法
            await self._intre_ss.report_prop_async(
                self._product.productKey,
                self._product.deviceId,
                self._module_key,
                'brightness',
                brightness_normalized
            )
        #await self._intre_ss.report_prop_async(self._product.productKey,self._product.deviceId,self._module_key,'brightness',int(newstate.attributes['brightness'] / 2.55))
        #colorTemperature
        color_temp_value = newstate.attributes.get('color_temp')
        if color_temp_value is None:
            print("Color temperature key not found in state attributes. Using default value of 5000K.")
        else:
            color_temperature_normalized = int((int(10 ** 6 / float(color_temp_value))) / 50) * 50
            # 调用报告属性方法
            await self._intre_ss.report_prop_async(
                self._product.productKey,
                self._product.deviceId,
                self._module_key,
                'colorTemperature',
                color_temperature_normalized
            )
        #await self._intre_ss.report_prop_async(self._product.productKey,self._product.deviceId,self._module_key,'colorTemperature',int((int(10 ** 6 /float(newstate.attributes['color_temp']))) / 50) * 50)
        return                      

    def service_call_req(self,serice_call_data:list)->None:
        data={
            'entity_id':self._entity_id
        }
        _LOGGER.debug(f"serice_call_data: {serice_call_data}") 
        service_input_value = serice_call_data['module']['service']['serviceInputValue']
        input_data = json.loads(service_input_value)
        brightness_data  = input_data.get('brightness')
        colorTemperature_data = input_data.get('colorTemperature')

        if 'brightness' in input_data:
            data['brightness'] = float(brightness_data * 2.55)
            self._intre_ss.call_ha_service('light','turn_on',data)
            _LOGGER.debug("BRIGHTNESS888888888888=   %d", brightness_data)
            _LOGGER.debug(data['brightness'])
        elif 'colorTemperature' in input_data:
            result = 10 ** 6
            data['color_temp'] =float (result /colorTemperature_data)
            _LOGGER.debug(data['color_temp'])
            self._intre_ss.call_ha_service('light','turn_on',data)
            _LOGGER.debug("colorTemperature999999999=  %d",colorTemperature_data)    
        
    def attr_change_req(self,properlist:list)->None:
        _LOGGER.debug(f"properlist: {properlist}") 
        data={
            'entity_id':self._entity_id
        }
        service='turn_on'
        for prop in properlist:
            if prop['propertyKey']=='onOff':
                if prop['propertyValue']=='0':
                    service='turn_off'
                _LOGGER.debug("onOffservice=%s %s",service,data)  
                self._intre_ss.call_ha_service('light',service,data)
            elif prop.get('propertyKey') == 'brightness':
                data['brightness'] = int(prop.get('propertyValue', 255))
                _LOGGER.debug("brightservice=%d ",data)  
                self._intre_ss.call_ha_service('light','brightness',data)
            elif prop.get('propertyKey') == 'colorTemperature':
                data['color_temp'] = int(prop.get('propertyValue', 255))
                _LOGGER.debug("brightservice=%d ",data)  
                self._intre_ss.call_ha_service('light','color_temp',data)    
        return

async def test_fun()->bool:
    _LOGGER.debug("test-light")  
