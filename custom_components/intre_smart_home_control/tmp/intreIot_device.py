# -*- coding: utf-8 -*-
"""
Copyright (C) 2024 Intretech Corporation.

The ownership and intellectual property rights of Intretech Home Assistant
Integration and related Intretech cloud service API interface provided under this
license, including source code and object code (collectively, "Licensed Work"),
are owned by Intretech. Subject to the terms and conditions of this License, Intretech
hereby grants you a personal, limited, non-exclusive, non-transferable,
non-sublicensable, and royalty-free license to reproduce, use, modify, and
distribute the Licensed Work only for your use of Home Assistant for
non-commercial purposes. For the avoidance of doubt, Intretech does not authorize
you to use the Licensed Work for any other purpose, including but not limited
to use Licensed Work to develop applications (APP), Web services, and other
forms of software.

You may reproduce and distribute copies of the Licensed Work, with or without
modifications, whether in source or object form, provided that you must give
any other recipients of the Licensed Work a copy of this License and retain all
copyright and disclaimers.

Intretech provides the Licensed Work on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied, including, without
limitation, any warranties, undertakes, or conditions of TITLE, NO ERROR OR
OMISSION, CONTINUITY, RELIABILITY, NON-INFRINGEMENT, MERCHANTABILITY, or
FITNESS FOR A PARTICULAR PURPOSE. In any event, you are solely responsible
for any direct, indirect, special, incidental, or consequential damages or
losses arising from the use or inability to use the Licensed Work.

Intretech reserves all rights not expressly granted to you in this License.
Except for the rights expressly granted by Intretech under this License, Intretech
does not authorize you in any form to use the trademarks, copyrights, or other
forms of intellectual property rights of Intretech and its affiliates, including,
without limitation, without obtaining other written permission from Intretech, you
shall not use "Intretech", "Mijia" and other words related to Intretech or words that
may make the public associate with Intretech in any form to publicize or promote
the software or hardware devices that use the Licensed Work.

Intretech has the right to immediately terminate all your authorization under this
License in the event:
1. You assert patent invalidation, litigation, or other claims against patents
or other intellectual property rights of Intretech or its affiliates; or,
2. You make, have made, manufacture, sell, or offer to sell products that knock
off Intretech or its affiliates' products.

IntreIoT http client.
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
from homeassistant.helpers.entity import (Entity,DeviceInfo)
from .const import (DOMAIN, SUPPORTED_PLATFORMS,MODULE_MAP_PLATFORMS)
_LOGGER = logging.getLogger(__name__)
from .intreIot_client import IntreIoTClient
from .intreIot_module import (IntreIoTProduct,IntreIoTModule,IntreIotHome)



class IntreIotEntity(Entity):
    intreIot_client:IntreIoTClient
    _main_loop: asyncio.AbstractEventLoop

    productObj:IntreIoTProduct
    moduleObj:IntreIoTModule
    
    _pending_write_ha_state_timer: Optional[asyncio.TimerHandle]

    def __init__(self,intreIot_client:IntreIoTClient,productObj:IntreIoTProduct, moduleObj: IntreIoTModule,uniqueStr='') -> None:
        self.intreIot_client = intreIot_client
        self._main_loop = self.intreIot_client._main_loop
        self.productObj=productObj
        self.moduleObj=moduleObj
        self._pending_write_ha_state_timer=None

        self._name = moduleObj.module_name
        self._unique_id = productObj.deviceId+moduleObj.module_key+ uniqueStr
        self._attr_device_info = productObj.device_info  # 关联设备信息


    @property
    def unique_id(self) -> str:
        return self._unique_id
    @property
    def name(self) -> str:
        return self._name
    def propValueNotify(self)->None:
        return 

    async def async_added_to_hass(self) -> None:
        self.intreIot_client.sub_prop_notify(deviceId=self.productObj.deviceId,moduleKey=self.moduleObj.module_key, handler=self.__on_properties_changed)
        return 
        #
        #return self.intreIot_client.sub_prop(deviceId=self.deviceId, handler=handler, moduleKey=moduleKey,handler_ctx=handler_ctx)
    
    async def set_property_async(self,propKey:str, value: str) -> bool:
        self.__request_refresh_prop()
        await self.intreIot_client.set_prop_async(deviceid=self.productObj.deviceId,moduleKey=self.moduleObj.module_key,propKey=propKey,propValue=value)
        return True
    
    def getPropValue(self,propKey:str) -> str:
        return self.moduleObj.props[propKey].propValue

    def __on_properties_changed(self, props: dict) -> None:
        self.moduleObj.update_props(props)
        if not self._pending_write_ha_state_timer:
            self.propValueNotify()
            self.async_write_ha_state()
    
    def __request_refresh_prop(self) -> None:
        if self._pending_write_ha_state_timer:
            self._pending_write_ha_state_timer.cancel()
        self._pending_write_ha_state_timer = self._main_loop.call_later(
            10, self.__write_ha_state_handler)
    
    def __write_ha_state_handler(self) -> None:
        self._pending_write_ha_state_timer = None
        _LOGGER.debug('__write_ha_state_handler %s')
        self.propValueNotify()
        self.async_write_ha_state()


'''
class IntreIoTModule(Entity):
    _module_code:str
    _module_key:str
    _unique_id:str
    _main_loop: asyncio.AbstractEventLoop
    product:IntreIoTProduct
    _prop_changed_subs: dict[str, IntreIoTProperty]
    _pending_write_ha_state_timer: Optional[asyncio.TimerHandle]
    def __init__(
            self,product:IntreIoTProduct, module: dict,
    ) -> None:
        self._name = module['moduleName']
        self._unique_id = product.deviceId+module['moduleKey']
        self._attr_device_info = product.device_info  # 关联设备信息
        self._module_code = module['moduleCode']
        self._module_key = module['moduleKey']
        self.product=product
        self._prop_changed_subs = {}
        self._main_loop = product.intreIot_client._main_loop
        self._pending_write_ha_state_timer=None

    async def async_added_to_hass(self) -> None:
        self.product.sub_property(handler=self.__on_properties_changed,moduleKey=self._module_key)

    def sub_prop_changed(
        self, prop: dict,handler:Callable[[dict], None]
    ) -> None:
        propObj=IntreIoTProperty(prop,handler)
        self._prop_changed_subs[prop['propertyKey']] = propObj

    def unsub_prop_changed(self, propKey: str) -> None:
        self._prop_changed_subs.pop(propKey, None)


    def __on_properties_changed(self, props: dict, ctx: Any) -> None:
        _LOGGER.debug('properties changed, %s', props)
        for prop in props:
            propObj = IntreIoTProperty(prop,None)
            if (pid:=propObj.pid) in self._prop_changed_subs:
                if self._prop_changed_subs[pid].update(propObj):
                    self._prop_changed_subs[pid].handler(propObj)
        if not self._pending_write_ha_state_timer:
            self.async_write_ha_state()

    def __request_refresh_prop(self) -> None:
        if self._pending_write_ha_state_timer:
            self._pending_write_ha_state_timer.cancel()
        self._pending_write_ha_state_timer = self._main_loop.call_later(
            10, self.__write_ha_state_handler)
    
    def __write_ha_state_handler(self) -> None:
        self._pending_write_ha_state_timer = None
        _LOGGER.debug('__write_ha_state_handler %s')
        for pid in self._prop_changed_subs:
            self._prop_changed_subs[pid].handler(self._prop_changed_subs[pid])
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        return self._unique_id
    @property
    def name(self) -> str:
        return self._name

    @property
    def moduleName(self) -> str:
        
        """information about this entity/device."""
        return self._module_name
    
    @property
    def moduleCode(self) -> str:
        """information about this entity/device."""
        return self._module_code

    @property
    def moduleKey(self) -> str:
        """information about this entity/device."""
        return self._module_key

    async def set_property_async(self,propKey:str, value: str) -> bool:
        self.__request_refresh_prop()
        await self.product.intreIot_client.set_prop_async(deviceid=self.product.deviceId,moduleKey=self.moduleKey,propKey=propKey,propValue=value)
        return True
'''