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
import math
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
            entity_state = entity.get('state')
            entity_id = entity_entry.entity_id
            #_LOGGER.debug(f"entity_state1111111111: {entity_state}")
            #_LOGGER.debug('light dualColorTemperatureLight'+entity['entry'].entity_id)
            if entity_id.split(".")[0]== 'light':
                
                _LOGGER.debug(f"entity_id: {entity_id}")
                _LOGGER.debug(f"entity_state: {entity_state}")
                state = hass.states.get(entity_id)
                _LOGGER.debug("Brightness light.")
                _LOGGER.debug(state)
                if state is not None:
                    attributes = state.attributes
                    supported_color_modes = attributes.get('supported_color_modes', 'N/A')
                    if 'color_temp' in supported_color_modes:# 判断是否双色温灯
                        module_info={}
                        _LOGGER.debug('dualColorTemperatureLight create')
                        module_info['moduleCode']='dualColorTemperatureLight'
                        module_info['moduleKey']=entity['entry'].entity_id
                        module_info['moduleName']= entity['entry'].name
                        module_info['entity_id']= entity['entry'].entity_id
                        light :IntreTempLight = IntreTempLight(hass=hass,intre_ss=intre_ss,product=product,module_info=module_info)
                        #_LOGGER.debug(product.deviceSn)
                        #_LOGGER.debug(product._name)
                        product.add_modules(light)


class IntreTempLight(IntreIoTModule):
    _product:IntreIoTProduct
    _intre_ss:IntreManagementEngine
    _min_color_temp_kelvin:str
    _max_color_temp_kelvin:str
    _brightness:str
    _colorTemperature:str
    _hass:HomeAssistant
    _onOff:bool
    def __init__(self,hass,intre_ss:IntreManagementEngine,product:IntreIoTProduct,module_info:dict) -> None:
        super().__init__(module_info=module_info)
        _LOGGER.debug('Initializing dualColorTemperatureLight...')
        self._hass=hass
        self._intre_ss=intre_ss
        self._product=product
        self.state = None
        self._brightness =StateUtils.util_get_state_brightness(intre_ss._intre_ha.get_entity_state(self._entity_id))
        self._colorTemperature =StateUtils.util_get_state_colorTemperature(intre_ss._intre_ha.get_entity_state(self._entity_id))
        self._onOff =StateUtils.util_get_state_onoff(intre_ss._intre_ha.get_entity_state(self._entity_id))
        self._min_color_temp_kelvin =StateUtils.util_get_min_color_temperature(intre_ss._intre_ha.get_entity_state(self._entity_id))
        self._max_color_temp_kelvin =StateUtils.util_get_max_color_temperature(intre_ss._intre_ha.get_entity_state(self._entity_id))
        self.attributes = dict
        self.module_info={}
        self._intre_ss.sub_entity(self._entity_id,self._entity_state_notify)
        self._product.sub_prop_set(self._module_key,self.attr_change_req)
        self._product.sub_service_call(self._module_key,self.service_call_req)
        self._product.sub_bacth_service_prop_call(self._module_key,self.batch_service_prop_call_req)
        _LOGGER.debug(self._brightness) 
        _LOGGER.debug(self._colorTemperature) 
        _LOGGER.debug(self._onOff) 
        _LOGGER.debug(self._min_color_temp_kelvin) 
        _LOGGER.debug(self._max_color_temp_kelvin)


    @final
    def get_module_prop_json(self)->dict:
        timestamp_ms = str(int(time.time() * 1000))
        return {
            "moduleKey":self._module_key,
            "propertyList": [
                {
                "propertyKey": "onOff",
                "propertyValue": str(int(self._onOff)),  
                "timestamp": timestamp_ms
                },
                {
                "propertyKey": "brightness",
                "propertyValue": str(self._brightness),
                "timestamp": timestamp_ms
                },
                {
                "propertyKey": "colorTemperature",
                "propertyValue": str(self._colorTemperature),
                "timestamp": timestamp_ms
                }  
            ]
        }
        
    @final
    def get_data_define_json(self) -> list:
        timestamp_ms = str(int(time.time() * 1000))
        return [{
            "moduleKey": self._module_key,
            "propertyKey": "colorTemperature",
            "dataDefineValue": f"{{\"dataType\":\"int\",\"specs\":{{\"min\":\"{self._min_color_temp_kelvin}\",\"max\":\"{self._max_color_temp_kelvin}\",\"step\":\"100\",\"unit\":\"K\",\"unitName\":\"开尔文\"}},\"required\":1}}",
            "timestamp": timestamp_ms
        }]
    @final
    def get_module_json(self) -> dict:
        timestamp_ms = str(int(time.time() * 1000))
        _LOGGER.debug('Initializing dual color temperature light module...')
        _LOGGER.debug(f'Product Key: {self._product.productKey}')
        _LOGGER.debug(f'Device ID: {self._product.deviceId}')
        match = re.search(r'_(\d+)$', self._module_key)
        if match:
            index = match.group(1)
            instance_module_name = f"双色温1"
        else:
            # 匹配失败时使用默认名称
            instance_module_name = "未知设备"
        # 验证关键参数是否有效
        product_key = self._product.productKey
        device_id = self._product.deviceId
        
        # 仅在参数有效时执行异步上报
        if isinstance(product_key, str) and product_key and isinstance(device_id, str) and device_id:
            self._report_data_define(product_key, device_id)
        else:
            _LOGGER.warning(f"Skipping data report - invalid parameters (productKey: {product_key}, deviceId: {device_id})")
        
        # 构建并返回模块JSON数据
        return {
            "templateModuleKey": "dualColorTemperatureLight_1",
            "instanceModuleKey": self._module_key,
            "instanceModuleName": instance_module_name,  # 动态生成的名称
            "propertyList": [
                {
                    "propertyKey": "onOff",
                    "propertyValue": str(int(self._onOff)),  
                    "timestamp": timestamp_ms
                },
                {
                    "propertyKey": "brightness",
                    "propertyValue": str(self._brightness),
                    "timestamp": timestamp_ms
                },
                {
                    "propertyKey": "colorTemperature",
                    "propertyValue": str(self._colorTemperature),
                    "timestamp": timestamp_ms
                }                            
            ]
        }

    def _report_data_define(self, product_key: str, device_id: str) -> None:
        """封装数据上报逻辑，提高代码可读性"""
        try:
            # 使用更安全的方式获取事件循环
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # 没有运行中的循环时创建新循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                run_manually = True
            else:
                run_manually = False

            # 准备异步任务
            report_task = self._intre_ss.data_define_report_async(
                product_key,
                device_id,
                self.get_data_define_json()
            )

            # 执行异步任务
            if loop.is_running():
                loop.create_task(report_task)
                _LOGGER.debug(f"Scheduled data define report for {product_key} (device {device_id})")
            else:
                loop.run_until_complete(report_task)
                _LOGGER.debug(f"Completed data define report for {product_key} (device {device_id})")

        except Exception as e:
            _LOGGER.error(f"Failed to report data define: {str(e)}", exc_info=True)
        finally:
            # 清理手动创建的事件循环
            if 'run_manually' in locals() and run_manually:
                loop.close()
    

    async def _entity_state_notify(self,newstate)->None:
        _LOGGER.debug(newstate)
        attributes = newstate.attributes
        brightness = attributes.get('brightness', 'N/A')
        color_temp = attributes.get('color_temp', 'N/A')

        _LOGGER.debug(
            f"Light Current state: {newstate.state}, Entity ID: {newstate.entity_id} "
            f"Brightness: {brightness}, Color Temp: {color_temp}"          
        )

        #OnOff
        self._onOff=StateUtils.util_get_state_onoff(newstate)
        self._brightness=StateUtils.util_get_state_brightness(newstate)
        await self._intre_ss.report_prop_async(self._product.productKey,self._product.deviceId,self._module_key,'onOff',str(int(self._onOff)))
     
        #brightness
        if 'brightness' not in newstate.attributes:
            _LOGGER.debug("Brightness key not found in state attributes.")
            brightness_normalized = 0  # 设置默认值
        else:
            # 获取 brightness 值并检查类型
            brightness_value = newstate.attributes['brightness']
            if not isinstance(brightness_value, (int, float)):
                _LOGGER.debug("Brightness value is not a number.")
                brightness_normalized = 0  # 设置默认值
            else:
                brightness_normalized = round(brightness_value / 2.55)
                _LOGGER.debug(brightness_normalized)
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
            _LOGGER.debug("Color temperature key not found in state attributes. Using default value of 5000K.")
            color_temperature_normalized = 0
        else:
            color_temperature_normalized = int((int(10 ** 6 / float(color_temp_value))) / 50) * 50
            _LOGGER.debug(color_temperature_normalized)
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

    def service_call_req(self, service_call_data: list) -> None:
        """处理服务调用请求，包括亮度和色温调节"""
        data = {'entity_id': self._entity_id}
        _LOGGER.debug(f"service_call_data: {service_call_data}")
        
        try:
            # 获取服务输入值
            service_input_value = service_call_data.get('module', {}).get('service', {}).get('serviceInputValue')
            service_key = service_call_data.get('module', {}).get('service', {}).get('serviceKey')

            # 处理toggleOnOff服务 - 反转开关状态
            if service_key == 'toggleOnOff':
                service='turn_on'
                if self._onOff==True:
                    service='turn_off'
                _LOGGER.debug("service_call_service=%s %s",service,data)  
                self._intre_ss.call_ha_service('light',service,data)
            else:
                _LOGGER.error("未找到开关状态属性_onOff,无法执行toggleOnOff")
            
            # 检查service_input_value是否有效
            if service_input_value is None:
                _LOGGER.error("serviceInputValue不存在或为None")
                return
                
            # 确保输入是字符串类型，如果是字节则转换为字符串
            if isinstance(service_input_value, bytes):
                service_input_value = service_input_value.decode('utf-8')
            elif not isinstance(service_input_value, str):
                _LOGGER.error(f"serviceInputValue类型无效: {type(service_input_value)}, 值: {service_input_value}")
                return
            
            # 解析JSON
            input_data = json.loads(service_input_value)
            _LOGGER.debug(f"解析到的输入数据: {input_data}")
    
            # 处理开关控制：onOff为1时开灯，0时关灯
            if 'onOff' in input_data:
                on_off_status = input_data['onOff']
                if on_off_status == 1:
                    service = 'turn_on'
                    _LOGGER.debug("收到开灯指令")
                elif on_off_status == 0:
                    service = 'turn_off'
                    _LOGGER.debug("收到关灯指令")
                else:
                    _LOGGER.error(f"无效的onOff值: {on_off_status}，仅支持0或1")
                    return
                self._intre_ss.call_ha_service('light', service, data)
            # 处理亮度调节
            if 'brightness' in input_data:
                brightness_data = input_data['brightness']
                if isinstance(brightness_data, (int, float)) and 0 <= brightness_data <= 100:
                    data['brightness'] = math.ceil(brightness_data * 2.55)
                    self._intre_ss.call_ha_service('light', 'turn_on', data)
                    _LOGGER.debug(f"亮度调节: 原始值={brightness_data}, 转换后={data['brightness']}")
                else:
                    _LOGGER.error(f"无效的亮度值: {brightness_data}，必须是0-100之间的数字")
            
            # 处理色温调节
            if 'colorTemperature' in input_data:
                color_temp_data = input_data['colorTemperature']
                if isinstance(color_temp_data, (int, float)) and 2500 <= color_temp_data <= 20000:
                    data['color_temp'] = float(10**6 / color_temp_data)
                    self._intre_ss.call_ha_service('light', 'turn_on', data)
                    _LOGGER.debug(f"色温调节: 原始值={color_temp_data}K, 转换后={data['color_temp']}mired")
                else:
                    _LOGGER.error(f"无效的色温值: {color_temp_data}，必须是2700-6500之间的数字")
        
        except KeyError as e:
            _LOGGER.error(f"服务调用数据缺少必要的键: {e}")
        except json.JSONDecodeError as e:
            _LOGGER.error(f"解析服务输入值JSON失败: {e}, 原始数据: {service_input_value}")
        except Exception as e:
            _LOGGER.error(f"处理服务调用请求时发生错误: {e}")   

    def batch_service_prop_call_req(self,batch_service_prop_data:dict)->None:
        data={
            'entity_id':self._entity_id
        }
        _LOGGER.debug(f"batch_service_prop_data: {batch_service_prop_data}")
        for service_item in batch_service_prop_data['serviceList']:
            # 1检查是否只有toggleOnOff参数    
            if service_item['serviceKey']=='toggleOnOff':
                service='turn_on'
                if self._onOff==True:
                    service='turn_off'
                _LOGGER.debug("batch_service=%s %s",service,data)  
                self._intre_ss.call_ha_service('light',service,data)
                continue  # 执行完后结束当前服务项的处理 
            if service_item['serviceKey'] == 'lightControlByBatch':
                try:
                    # 先将JSON字符串解析为字典
                    input_values = json.loads(service_item['serviceInputValue'])
                    _LOGGER.debug(f"len(input_values): {len(input_values)}")
                except json.JSONDecodeError as e:
                    _LOGGER.error(f"Failed to parse serviceInputValue: {e}")
                    continue  # 解析失败则跳过当前服务
 
                # 2检查是否只有onOff参数
                if len(input_values) == 1 and 'onOff' in input_values:
                    _LOGGER.debug("Only onOff parameter provided")
                    
                    # 根据onOff值执行相应操作
                    if input_values['onOff'] == 1:
                        _LOGGER.debug("Calling service turn_on with basic data")
                        self._intre_ss.call_ha_service('light', 'turn_on', data)
                    else:
                        _LOGGER.debug("Calling service turn_off with basic data")
                        self._intre_ss.call_ha_service('light', 'turn_off', data)
                    
                    continue  # 执行完后结束当前服务项的处理  
                # 情况3：同时包含onOff、colorTemperature和transitionTime三个参数
                required_keys = {'onOff', 'colorTemperature', 'transitionTime'}
                if required_keys.issubset(input_values.keys()) and len(input_values) == 3:
                    _LOGGER.debug("Found onOff, colorTemperature and transitionTime - special handling")
                    service = 'turn_on'
                    
                    if service == 'turn_on':
                        # 处理色温
                        try:
                            kelvin_temp = input_values['colorTemperature']
                            mired_value = 10**6 / float(kelvin_temp)
                            min_mired = 50
                            max_mired = 400
                            data['color_temp'] = max(min_mired, min(max_mired, int(mired_value)))
                            _LOGGER.debug(f"Converted {kelvin_temp}K to {data['color_temp']} mired")
                        except (ZeroDivisionError, ValueError):
                            _LOGGER.error(f"Invalid color temperature value: {kelvin_temp}")
                        
                        # 处理过渡时间
                        data['transition'] = input_values['transitionTime'] 
                        # 处理亮度（保持不变）
                        data['brightness'] = int((self._brightness) * 2.55) if service == 'turn_on' else None
                    
                    _LOGGER.debug(f"Calling service {service} with special data: {data}")
                    self._intre_ss.call_ha_service('light', service, data)
                    continue   
                
                # 确定开关服务类型
                service = 'turn_on' if input_values.get('onOff', 0) else 'turn_off'
                
                # 处理亮度（保持不变）
                brightness = int(input_values.get('brightness', 0) * 2.55) if service == 'turn_on' else None
                
                # 处理色温（将开尔文转换为Mired值）
                color_temp = None
                if service == 'turn_on':
                    kelvin_temp = input_values.get('colorTemperature')
                    if kelvin_temp is not None:
                        try:
                            # 转换公式：Mired = 1,000,000 / 开尔文
                            mired_value = 10**6 / float(kelvin_temp)
                            
                            # 大多数灯具的Mired值范围在153-500之间（对应约6500K-2000K）
                            # 根据实际设备支持范围调整这个区间
                            min_mired = 153
                            max_mired = 500
                            color_temp = max(min_mired, min(max_mired, int(mired_value)))
                            
                            _LOGGER.debug(f"Converted {kelvin_temp}K to {color_temp} mired")
                        except (ZeroDivisionError, ValueError):
                            _LOGGER.error(f"Invalid color temperature value: {kelvin_temp}")
                
                # 处理过渡时间（毫秒转秒）
                transition = input_values.get('transitionTime', 0) // 1000 if service == 'turn_on' else None
                
                # 构建服务数据
                service_data = {
                    'entity_id': self._entity_id,
                    'brightness': brightness,
                    'color_temp': color_temp,
                    'transition': transition
                }
                
                # 过滤掉None值
                service_data = {k: v for k, v in service_data.items() if v is not None}
                
                _LOGGER.debug(f"Calling service {service} with data: {service_data}")
                self._intre_ss.call_ha_service('light', service, service_data)


        '''
        for prop in batch_service_prop_data['propertyList']:
            if prop['propertyKey']=='onOff':
                service='turn_on'
                if prop['propertyValue']=='0':
                    service='turn_off'
                _LOGGER.debug("batch1_service=%s %s",service,data)  
                self._intre_ss.call_ha_service('switch',service,data)
        

        '''
    def attr_change_req(self, properlist: list,msg_id: str) -> None:
        _LOGGER.debug(f"properlist: {properlist}")
        
        data={
            'entity_id':self._entity_id
        }
        service='turn_on'
        for prop in properlist:
            prop_key = prop.get('propertyKey')
            prop_value = prop.get('propertyValue')
            if prop['propertyKey']=='onOff':
                if prop['propertyValue']=='0':
                    service='turn_off'
                _LOGGER.debug("onOffservice=%s %s",service,data)  
                self._intre_ss.call_ha_service('light',service,data)
            elif prop.get('propertyKey') == 'brightness':
                brightness = int(prop_value)
                if 0 <= brightness <= 100:
                    data['brightness'] = int(brightness * 2.55)
                _LOGGER.debug("bright service=%d ",data)  
                self._intre_ss.call_ha_service('light',service,data)
            elif prop.get('propertyKey') == 'colorTemperature':
                kelvin = int(prop_value)
                if 2000 <= kelvin <= 6500:  # 常见色温范围
                    mired = int(10**6 / kelvin)
                    # 限制Mired值在大多数设备支持的范围内
                    mired = max(153, min(500, mired))
                    data['color_temp'] = mired
                _LOGGER.debug("colorTemperature service=%d ",data)  
                self._intre_ss.call_ha_service('light',service,data)    
        return

async def test_fun()->bool:
    _LOGGER.debug("test-light")  
