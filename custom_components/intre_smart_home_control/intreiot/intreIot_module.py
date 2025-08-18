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
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, final
from urllib.parse import urlencode
import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import (Entity,DeviceInfo)
from .const import (DOMAIN, SUPPORTED_PLATFORMS)
#from .intreIot_ha import IntreIotHa
#from .intreiot.intre_manage_engine import (IntreManagementEngine)
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
    #_intre_scene:IntreManagementEngine
    #_intre_ha:IntreIotHa
    _entity_id:str
    _module_code:str
    _module_key:str
    _module_name:str
    _moduleEnable:bool
    _propObjList:dict[str, IntreIoTProperty]


    def __init__(self,module_info: dict) -> None:
        self._module_code = module_info['moduleCode']
        self._module_key = module_info['moduleKey']
        self._module_name = module_info['moduleName']
        self._entity_id= module_info['entity_id']
        


    @abstractmethod
    def get_module_json(self) -> dict: ...

    @abstractmethod
    def get_module_prop_json(self) -> dict: ...
    
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

    


class IntreIoTProduct:
    _productKey: str
    _deviceId: str
    _deviceSn: str
    _onlineFlag:bool
    _parent_deviceid:str

    _model: str
    _manufacturer: str
    _fw_version: str
    _version_code:int
    _name:str
    _suggested_area:str
    _productVersion:int
    _sub_module_prop_set:dict[str,list[Callable[list, None]]]
    _sub_module_service_call:dict[str,list[Callable[list, None]]]
    _sub_module_bacth_service_call:dict[str,list[Callable[list, None]]]
    _modules:list[IntreIoTModule]

    def __init__(self,product_info: dict) -> None:
        self._deviceId = None
        self._manufacturer = product_info['productManufacturer']
        self._name = product_info['deviceName']
        self._deviceSn=product_info['deviceId']
        self._modules =[]
        self._version_code=1
        self._productVersion=3
        self._fw_version='v1'
        self._sub_module_prop_set={}
        self._sub_module_service_call={}
        self._sub_module_bacth_service_call={}
    def get_modules(self)->list:
        return self._modules

    def add_modules(self,module:IntreIoTModule)->bool:
        self._modules.append(module)
        
    def set_productKey(self,productKey:str)->bool:
        self._productKey = productKey

    def set_parent_device_id(self,parent_deviceid:str)->None:
        self._parent_deviceid = parent_deviceid
 
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


    def get_product_json(self)->dict:   
        modules_json=[]
        for module in self._modules:
            modules_json.append(module.get_module_json())
    
        return{
            "productKey": self._productKey,
            "deviceSn": self._deviceSn,
            "deviceName":self._name,
            "softVersionCode": self._version_code,
            "productVersion":self._productVersion,
            "parentDeviceId":self._parent_deviceid,
        }

    def get_dynamic_module_json(self)->dict:   
        modules_json=[]
        for module in self._modules:
            
            modules_json.append(module.get_module_json())
            #module_json = module.get_module_json()
        #_LOGGER.debug(modules_json)
        return{
            "deviceId": self.deviceId,
            "dynamicModuleList": modules_json
        }

    def get_haProVerInfo_json(self)->dict:   
        modules_json=[]
        for module in self._modules:
            modules_json.append(module.get_module_json())
            if self._productKey == "Intre.HA-Light":
                self._productVersion = 5
                _LOGGER.debug(f"准备上报属性: productkey={self._productKey} ")
            elif self._productKey == "Intre.HA-Switch":
                self._productVersion = 4
                _LOGGER.debug(f"准备上报属性: productkey={self._productKey} ")
            elif self._productKey == "Intre.HA-Curtain":
                self._productVersion = 5
                _LOGGER.debug(f"准备上报属性: productkey={self._productKey} ")    
        return{
            "parentDeviceId": self._parent_deviceid,
            "parentProductKey": "Intre.BGZ001",
            "subDeviceProductVersions": [
                {
                    "productKey": self._productKey,
                    "targetProductVersion":self._productVersion
                }
            ]
        }

    def get_modules_prop_json(self)->list:
        modules_json=[]
        for module in self._modules:
            modules_json.append(module.get_module_prop_json())
        return modules_json
    #device/{productKey}/{deviceId}/down/tls/property/set
    def prop_set_callback(self,data:dict)->bool:
        _LOGGER.debug('prop_set_callback')
        _LOGGER.debug(data)
        # 提取msgId
        msg_id = data.get('msgId')
        for module_info in data['data']['deviceModuleList']:
            if module_info['moduleKey'] in self._sub_module_prop_set:
                for handler in self._sub_module_prop_set[module_info['moduleKey']]:
                    handler(module_info['propertyList'],msg_id)
        
    
    def sub_prop_set(self,modulekey:str,handler: Callable[[list, Any], None])->None:
        if modulekey in self._sub_module_prop_set:
            self._sub_module_prop_set[modulekey].append(handler)
            _LOGGER.debug('sub_prop_set111')
        else:
            self._sub_module_prop_set[modulekey]=[handler]
            _LOGGER.debug('sub_prop_set222')

    #device/{productKey}/{deviceId}/down/tls/property/report-reply
    def prop_report_rsp_callback(self,data:dict)->bool:
        _LOGGER.debug(data)
    
    #device/{productKey}/{deviceId}/down/tls/event/report-reply
    def event_report_rsp_callback(self,data:dict)->bool:
        _LOGGER.debug(data)

    #device/{productKey}/{deviceId}/down/tls/service/call
    def service_call_callback(self,data:dict)->bool:
        _LOGGER.debug('service_call')
        _LOGGER.debug(data)
        if data['module']['moduleKey'] in self._sub_module_service_call:
            for handler in self._sub_module_service_call[data['module']['moduleKey']]:
                handler(data)

    def sub_service_call(self,modulekey:str,handler: Callable[[list, Any], None])->None:
        if modulekey in self._sub_module_service_call:
            self._sub_module_service_call[modulekey].append(handler)
        else:
            self._sub_module_service_call[modulekey]=[handler]

    def sub_bacth_service_prop_call(self,modulekey:str,handler: Callable[[list, Any], None])->None:
        if modulekey in self._sub_module_bacth_service_call:
            self._sub_module_bacth_service_call[modulekey].append(handler)
        else:
            self._sub_module_bacth_service_call[modulekey]=[handler]
    #device/{productKey}/{deviceId}/down/tls/batch/property/service/set
    '''
    def bacth_service_prop_callback(self,modulekey:str,handler: Callable[[list, Any], None])->None:
        if modulekey in self._sub_module_bacth_service_call:
            self._sub_module_bacth_service_call[modulekey].append(handler)
        else:
            self._sub_module_bacth_service_call[modulekey]=[handler]
    '''
    def bacth_service_prop_callback(self,data:dict)->bool:
        _LOGGER.debug('batch')
        _LOGGER.debug(data)
        for deviceModule in data['deviceModuleList']: 
            if deviceModule['moduleKey'] in self._sub_module_bacth_service_call:
                for handler in self._sub_module_bacth_service_call[deviceModule['moduleKey']]:
                    handler(deviceModule)
        ''' 
        for module_info in data['deviceModuleList']:
            if module_info['moduleKey'] in self._sub_module_bacth_service_call:
                for handler in self._sub_module_bacth_service_call[module_info['moduleKey']]:
                    handler(module_info['serviceList'])
          
        # 遍历 deviceModuleList 和 serviceList
        for module in data.get("deviceModuleList", []):
            for service in module.get("serviceList", []):
                if service.get("serviceKey") == "executeScene":
                    # 解析 serviceInputValue 中的 sceneId
                    service_input_value = service.get("serviceInputValue")
                    if service_input_value:
                        service_input_dict = json.loads(service_input_value)
                        scene_id = service_input_dict.get("sceneId")
                        data={
                            'entity_id':scene_id
                        }
                        if scene_id:
                            _LOGGER.debug(f"收到情景ID: {scene_id}")

                            #self._intre_scene.call_ha_service('scene','turn_on',data)
                        else:
                            _LOGGER.debug("serviceInputValue 中缺少 sceneId 字段")
                    else:
                        print("消息中缺少 serviceInputValue 字段")
        '''
class IntreIotHome:
    homeid:str
    entry_id: str
    productObjList:list[IntreIoTProduct]


    def __init__(self,entry_id:str, homeid:str) -> None:
        self.homeid = homeid
        self.productObjList=[]
        self.entry_id = entry_id
