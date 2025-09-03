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
from .const import (DOMAIN, SUPPORTED_PLATFORMS)
_LOGGER = logging.getLogger(__name__)

class IntreIoTProperty:
    _propKey: str
    _propType:int
    _propName:str
    _propValue: str
    _propEnumList:str
    _properValueMin:str
    _properValueMax:str
    _timestamp:str
    def __init__(self,prop: dict) -> None:
        self._propKey = prop['propertyKey']
        self._propName = prop['propertyName']
        self._propValue = prop['propertyValue']
        self._propType = prop['dataDefine']['dataType']
        self._timestamp = prop['timestamp']

    @property
    def propKey(self) -> str:
        return self._propKey
    @property
    def propType(self) -> int:
        return self._propType
    @property
    def propName(self) -> str:
        return self._propName
    @property
    def propValue(self) -> str:
        return self._propValue
    @property
    def timestamp(self) -> str:
        return self._timestamp
    @property
    def propEnumList(self) -> str:
        return self._propEnumList

    def updateValue(self,prop:dict)->bool:
        oldtime=int(self.timestamp)
        newtime=int(prop.get('timestamp','0'))
        if oldtime<newtime:
            self._timestamp = prop.get('timestamp','0')
            if self.propValue != prop['propertyValue']:
                self._propValue = prop['propertyValue']
                return True
        return False

class IntreIoTModule:
    _module_code:str
    _module_key:str
    _module_name:str
    _moduleEnable:bool
    _propObjList:dict[str, IntreIoTProperty]

    def __init__(self,module: dict) -> None:
        self._module_code = module['moduleCode']
        self._module_key = module['moduleKey']
        self._module_name = module['moduleName']
        self._moduleEnable = module['moduleEnable']
        self._propObjList={}
        for prop in module['propertyList']:
            if prop['propertyKey'] in SUPPORT_MODULE_DB[self._module_code]:
                propObj =IntreIoTProperty(prop)
                self._propObjList[prop['propertyKey']] = propObj
    @property
    def module_code(self) -> str:
        return self._module_code
    @property
    def module_key(self) -> int:
        return self._module_key
    @property
    def module_name(self) -> int:
        return self._module_name
    @property
    def moduleEnable(self) -> int:
        return self._moduleEnable
    @property
    def props(self) -> dict[str, IntreIoTProperty]:
        return self._propObjList
    def update_props(self,props:dict)->bool:
        updateFlag = False
        for prop in props:
            if self.props.get(prop['propertyKey'],None):
                if self.props[prop['propertyKey']].updateValue(prop):
                    updateFlag = True
        return updateFlag


class IntreIoTProduct:
    _productKey: str
    _deviceId: str
    _deviceSn: str
    _onlineFlag:bool

    _model: str
    _manufacturer: str
    _fw_version: str
    _name:str
    _suggested_area:str
    _moduleObjList:list[IntreIoTModule]

    def __init__(self,product: dict) -> None:
        self._productKey = product['productKey']
        self._deviceId = product['deviceId']
        self._manufacturer = product['productManufacturer']
        self._name = product['deviceName']
        self._moduleObjList =[]
        self._fw_version='v1'
        self._suggested_area=product['deviceName']
        for module in product['deviceModuleList']:
            if module['moduleCode'] in SUPPORT_MODULE_DB:
                moduleObj =IntreIoTModule(module)
                self._moduleObjList.append(moduleObj)
    
    

    @property
    def device_info(self) -> DeviceInfo:
        """information about this entity/device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._deviceId)},
            name=self._name,
            sw_version=self._fw_version,
            suggested_area=self._suggested_area,
            model=self._productKey,
            manufacturer=self._manufacturer
        )

    @property
    def productKey(self) -> str:
        return self._productKey
    @property
    def deviceId(self) -> int:
        return self._deviceId
    @property
    def deviceSn(self) -> str:
        return self._deviceSn
    @property
    def onlineFlag(self) -> int:
        return self._onlineFlag
        
class IntreIotHome:
    homeid:str
    entry_id: str
    productObjList:list[IntreIoTProduct]


    def __init__(self,entry_id:str, homeid:str) -> None:
        self.homeid = homeid
        self.productObjList=[]
        self.entry_id = entry_id
