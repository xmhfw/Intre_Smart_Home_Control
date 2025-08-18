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
from .util import StateUtils
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
            #_LOGGER.debug('cover create11111'+entity['entry'].entity_id)
            if entity_id.split(".")[0]== 'cover':
                #state = hass.states.get(entity_id)
                #_LOGGER.debug(state)
                #if entity['entry'].supported_features & 7:
                module_info={}
                module_info['moduleCode']='draperyCurtain'
                module_info['moduleKey']=entity['entry'].entity_id
                module_info['moduleName']= entity['entry'].name
                module_info['entity_id']= entity['entry'].entity_id
                cover :IntreCover = IntreCover(intre_ss=intre_ss,product=product,module_info=module_info)
                #_LOGGER.debug(product.deviceSn)
                #_LOGGER.debug(product._name)
                product.add_modules(cover)
                    
class IntreCover(IntreIoTModule):
    _product:IntreIoTProduct
    _intre_ss:IntreManagementEngine
    _positionPercentage:str
    _service_close_cover:int
    def __init__(self,intre_ss:IntreManagementEngine,product:IntreIoTProduct,module_info:dict) -> None:
        super().__init__(module_info=module_info)
        _LOGGER.debug('Initializing IntreCover...')
        self._intre_ss=intre_ss
        self._product=product
        self.state = None
        self.attributes = dict
        self._service_close_cover = 0
        self._positionPercentage = StateUtils.util_get_state_positionPercentage(intre_ss._intre_ha.get_entity_state(self._entity_id))
        self._intre_ss.sub_entity(self._entity_id,self._entity_state_notify)
        self._product.sub_prop_set(self._module_key,self.attr_change_req)
        self._product.sub_service_call(self._module_key,self.service_call_req)
        self._product.sub_bacth_service_prop_call(self._module_key,self.batch_service_prop_call_req)
        _LOGGER.debug(self._positionPercentage)

    @final
    def get_module_prop_json(self)->dict:
        timestamp_ms = str(int(time.time() * 1000))
        return {
            "moduleKey":self._module_key,
            "propertyList": [
                {
                "propertyKey": "positionPercentage",
                "propertyValue": str(int(self._positionPercentage)),  
                "timestamp": timestamp_ms
                }
            ]
        }
   
    @final
    def get_tls_log_json(self,serverkey:str)->list:
        timestamp_ms = str(int(time.time() * 1000))
        return[{
            "moduleKey":self._module_key,
            "service": 
                {
                "serviceKey": serverkey,
                "serviceOutputValue": "",  
                "timestamp": timestamp_ms
                }
        }]
        
    @final
    def get_module_json(self)->dict:
        timestamp_ms = str(int(time.time() * 1000))
        match = re.search(r'_(\d+)$', self._module_key)
        if match:
            index = match.group(1)
            instance_module_name = f"卷帘1"
        else:
            # 匹配失败时使用默认名称
            instance_module_name = "未知设备"
        return {
            "templateModuleKey":'liftCurtain_2',
            "instanceModuleKey": self._module_key,
            "instanceModuleName": instance_module_name,  # 动态生成的名称
            "propertyList": [
                {
                "propertyKey": "positionPercentage",
                "propertyValue": str(int(self._positionPercentage)),  
                "timestamp": timestamp_ms
                }
            ]
        } 
    async def _entity_state_notify(self,newstate)->None:
         #_LOGGER.debug(f"窗帘新状态: {newstate.state,newstate.entity_id,newstate.attributes['current_position']}")   
         #await self._intre_ss.report_prop_async(self._product.productKey,self._product.deviceId,self._module_key,'positionPercentage',newstate.attributes['current_position'])
        #supported_features = attributes.get('supported_features', 'N/A')
        #_LOGGER.debug(f"Supported features for : {supported_features}")


        self._positionPercentage=StateUtils.util_get_state_positionPercentage(newstate)
        _LOGGER.debug(
            f"Curtain Current state: {newstate.state}, Entity ID: {newstate.entity_id}, "
            f"Current_position= : {self._positionPercentage},service_close_cover= : {self._service_close_cover}"
        )


        if 'current_position' not in newstate.attributes:
            _LOGGER.debug("current_position key not found in state attributes.")
        else:
            current_position= newstate.attributes['current_position']
            current_position_int = int(current_position)

            complementary_value = 100 - current_position_int
            if not isinstance(current_position, (int, float)):
                _LOGGER.debug("current_position value is not a number.")
            _LOGGER.debug(
                f"complementary_value= : {complementary_value}"
            )
            if self._service_close_cover != 0:
                self._service_close_cover -= 1
                # 可选：确保值不会小于0（双重保险）
                if self._service_close_cover < 0:
                    self._service_close_cover = 0
            else:
                await self._intre_ss.report_prop_async(
                    self._product.productKey,
                    self._product.deviceId,
                    self._module_key,
                    'positionPercentage',
                    complementary_value
                )
            
        return   
             
    def service_call_req(self, service_call_data: list) -> None:
        data = {
            'entity_id': self._entity_id
        }
        
        service_mapping = {
            'close': 'close_cover',
            'open': 'open_cover',
            'pause': 'stop_cover'
        }
        
        try:
            service_key = service_call_data['module']['service']['serviceKey']
            _LOGGER.debug(f"service_call_data: {service_call_data}") 
            
            if service_key not in service_mapping:
                _LOGGER.debug(f'Unsupported serviceKey: {service_key}')
                return
                
            service = service_mapping[service_key]
            
            # Handle services that need TSL log reporting
            if service_key in ['open', 'close']:
                try:
                    # Check if we're already in an event loop
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        # No event loop exists, create a new one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        run_new_loop = True
                    else:
                        run_new_loop = False

                    # Check if loop is running
                    if loop.is_running():
                        # If loop is running, use create_task instead
                        loop.create_task(
                            self._intre_ss.report_device_tsl_log_async(
                                self._product.productKey,
                                self._product.deviceId,
                                self.get_tls_log_json(service_key)
                            )
                        )
                    else:
                        # Run the coroutine normally
                        loop.run_until_complete(
                            self._intre_ss.report_device_tsl_log_async(
                                self._product.productKey,
                                self._product.deviceId,
                                self.get_tls_log_json(service_key)
                            )
                        )
                        # Close the loop if we created it
                        if run_new_loop:
                            loop.close()
                    
                except Exception as e:
                    _LOGGER.error(f"Error reporting TSL log: {str(e)}")
            
            # Call the HA service
            self._intre_ss.call_ha_service('cover', service, data)
            self._service_close_cover = 3
        except KeyError as e:
            _LOGGER.error(f"Missing key in service_call_data: {str(e)}")
        except Exception as e:
            _LOGGER.error(f"Error in service_call_req: {str(e)}")

    def batch_service_prop_call_req(self,batch_service_prop_data:dict)->None:
        data={
            'entity_id':self._entity_id
        }
        for prop in batch_service_prop_data['propertyList']:
            if prop['propertyKey']=='positionPercentage':
                data['position'] = prop['propertyValue']
                _LOGGER.debug("batch1_service=%s ",data)  
                self._intre_ss.call_ha_service('cover', 'set_cover_position', data)
        
        for service in batch_service_prop_data['serviceList']:
            if service['serviceKey']=='close':
                service='close_cover'
                self._intre_ss.call_ha_service('cover',service,data)
                _LOGGER.debug("batch2_service=%s %s",service,data)  
            elif service['serviceKey']=='open':
                service='open_cover'
                self._intre_ss.call_ha_service('cover',service,data)
                _LOGGER.debug("batch2_service=%s %s",service,data) 
            elif service['serviceKey']=='stop':
                service='stop_cover'
                self._intre_ss.call_ha_service('cover',service,data)
                _LOGGER.debug("batch2_service=%s %s",service,data) 
            else:
                _LOGGER.debug('Unsupported serviceKey')   

    def attr_change_req(self, properlist: list,msg_id: str) -> None:
        _LOGGER.debug(f"properlist: {properlist}")
        data={
            'entity_id':self._entity_id
        }
        for prop in properlist:
            if prop['propertyKey'] == 'positionPercentage':
                position = int(prop['propertyValue'])  
                if 0 <= position <= 100: 
                    data['position'] = 100 - position
                    _LOGGER.debug("Setting cover position to %d", position)
                    self._service_close_cover = 1
                    self._intre_ss.call_ha_service('cover', 'set_cover_position', data)
                else:
                    _LOGGER.debug("Invalid position percentage: %d", prop['propertyValue'])
        return

async def test_fun()->bool:
    _LOGGER.debug("test-curtain")  