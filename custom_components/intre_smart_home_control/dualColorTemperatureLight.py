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
        s = self._module_key
        if s.startswith("light."):
            instance_module_name = s.split("light.")[1]
        else:
            instance_module_name = "双色温"  # 或者根据需要设置默认值
        _LOGGER.debug(f'instance_module_name={instance_module_name}')
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
            "templateModuleKey": "dualColorTemperatureLight_2",
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
        if newstate is None:
            _LOGGER.debug("Received None as newstate in _entity_state_notify")
            return
        
        # 初始化缓存（如果不存在）
        if not hasattr(self, '_state_cache'):
            self._state_cache = {
                'onOff': None,
                'brightness': None,
                'colorTemperature': None
            }

        attributes = newstate.attributes
        brightness = attributes.get('brightness', 'N/A')
        color_temp = attributes.get('color_temp', 'N/A')

        _LOGGER.debug(
            f"Light Current state: {newstate.state}, Entity ID: {newstate.entity_id} "
            f"Brightness: {brightness}, Color Temp: {color_temp}"          
        )

        # 处理开关状态
        current_on_off = StateUtils.util_get_state_onoff(newstate)
        if current_on_off is not None:
            try:
                on_off_str = str(int(current_on_off))
                # 对比缓存，不同时才上报
                if on_off_str != self._state_cache['onOff']:
                    await self._intre_ss.report_prop_async(
                        self._product.productKey,
                        self._product.deviceId,
                        self._module_key,
                        'onOff',
                        on_off_str
                    )
                    self._state_cache['onOff'] = on_off_str  # 更新缓存
                    _LOGGER.debug(f"上报开关状态: {on_off_str}")
                else:
                    _LOGGER.debug("开关状态未变化，无需上报")
            except (ValueError, TypeError) as e:
                _LOGGER.error(f"转换开关状态失败 {current_on_off}: {str(e)}")

        # 处理亮度
        if 'brightness' in newstate.attributes:
            brightness_value = newstate.attributes['brightness']
            if isinstance(brightness_value, (int, float)):
                brightness_normalized = round(brightness_value / 2.55)
                # 对比缓存，不同时才上报
                if brightness_normalized != self._state_cache['brightness']:
                    await self._intre_ss.report_prop_async(
                        self._product.productKey,
                        self._product.deviceId,
                        self._module_key,
                        'brightness',
                        brightness_normalized
                    )
                    self._state_cache['brightness'] = brightness_normalized  # 更新缓存
                    _LOGGER.debug(f"上报亮度: {brightness_normalized}")
                else:
                    _LOGGER.debug("亮度未变化，无需上报")
            else:
                _LOGGER.debug("亮度值不是数字，无法处理")
        else:
            _LOGGER.debug("未找到亮度属性")

        # 处理色温
        color_temp_value = newstate.attributes.get('color_temp')
        if color_temp_value is not None:
            try:
                color_temperature_normalized = int((int(10 **6 / float(color_temp_value))) / 50) * 50
                # 对比缓存，不同时才上报
                if color_temperature_normalized != self._state_cache['colorTemperature']:
                    await self._intre_ss.report_prop_async(
                        self._product.productKey,
                        self._product.deviceId,
                        self._module_key,
                        'colorTemperature',
                        color_temperature_normalized
                    )
                    self._state_cache['colorTemperature'] = color_temperature_normalized  # 更新缓存
                    _LOGGER.debug(f"上报色温: {color_temperature_normalized}")
                else:
                    _LOGGER.debug("色温未变化，无需上报")
            except (ValueError, TypeError) as e:
                _LOGGER.error(f"转换色温失败 {color_temp_value}: {str(e)}")
        else:
            _LOGGER.debug("未找到色温属性")

        return
        
    def service_call_req(self, service_call_data: list) -> None:
        """处理服务调用请求，包括亮度和色温调节"""
        data = {'entity_id': self._entity_id}
        _LOGGER.debug(f"service_call_data: {service_call_data}")
        
        try:
            # 1. 先获取嵌套在data里的module
            module = service_call_data.get('data', {}).get('module', {})
            if not module:
                _LOGGER.warning("未从service_call_data中获取到有效的module信息")
                return
            
            # 2. 从module中提取服务键和输入值
            service_key = module.get('service', {}).get('serviceKey')
            service_input_value = module.get('service', {}).get('serviceInputValue')

            # 3. 解析service_input_value，判断是否包含brightness
            is_brightness_request = False
            input_data = None
            if service_input_value:
                if isinstance(service_input_value, bytes):
                    service_input_value = service_input_value.decode('utf-8')
                if isinstance(service_input_value, str):
                    try:
                        input_data = json.loads(service_input_value)
                        # 核心判断：是否包含 'brightness' 字段
                        if 'brightness' in input_data:
                            is_brightness_request = True
                            _LOGGER.debug("检测到亮度调节请求，准备进行时间戳校验")
                    except json.JSONDecodeError as e:
                        _LOGGER.error(f"解析serviceInputValue失败: {e}")

            # 4. 仅对brightness请求执行时间戳对比
            current_timestamp = None
            if is_brightness_request:
                current_timestamp = service_call_data.get('timestamp')
                if not current_timestamp:
                    _LOGGER.warning("亮度调节请求中未包含timestamp，无法进行校验，将执行请求")
                else:
                    try:
                        current_timestamp = int(current_timestamp)
                    except (ValueError, TypeError):
                        _LOGGER.error(f"亮度调节请求的timestamp格式无效: {current_timestamp}，将执行请求")
                        current_timestamp = None

                    # 时间戳对比逻辑
                    if current_timestamp is not None:
                        # 初始化时间戳（如果不存在）
                        if not hasattr(self, '_last_brightness_timestamp'):
                            self._last_brightness_timestamp = 0
                        
                        if current_timestamp <= self._last_brightness_timestamp:
                            _LOGGER.debug(
                                f"亮度调节请求时间戳({current_timestamp})过期（上次：{self._last_brightness_timestamp}），丢弃该请求"
                            )
                            return  # 丢弃过期请求
                        else:
                            # 更新亮度请求的最新时间戳
                            self._last_brightness_timestamp = current_timestamp
                            _LOGGER.debug(f"更新亮度请求最新时间戳为: {current_timestamp}")

            
            # 1. 先获取嵌套在data里的module（关键修复点）
            module = service_call_data.get('data', {}).get('module', {})
            if not module:  # 若未获取到module，直接返回避免后续报错
                _LOGGER.warning("未从service_call_data中获取到有效的module信息")
                return
            
            # 2. 从module中提取服务键和输入值
            service_key  = module.get('service', {}).get('serviceKey')
            service_input_value  = module.get('service', {}).get('serviceInputValue')

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

            # 执行日光效果设置
            daylight_effect = input_data.get('daylightEffect')
            if daylight_effect is not None:
                _LOGGER.debug(f"设置日光效果: {daylight_effect}")
                # 这里添加设置日光效果的业务逻辑...
                if daylight_effect == 1:
                    _LOGGER.debug("执行日光效果 1(明亮)")
                    # 业务逻辑1：色温6000K，亮度100%，若最大色温值小于6000则直接使用色温最大值执行
                    target_brightness = 100  # 目标亮度100%
                    target_temp = 6000       # 目标色温6000K
                    # 校验色温：若最大色温<6000，使用最大值
                    final_temp = min(target_temp, self._max_color_temp_kelvin) if hasattr(self, '_max_color_temp_kelvin') else target_temp
                    data['brightness'] = math.ceil(target_brightness * 2.55)
                    self._intre_ss.call_ha_service('light', 'turn_on', data)
                    data['color_temp'] = float(10**6 / final_temp)
                    self._intre_ss.call_ha_service('light', 'turn_on', data)
                    _LOGGER.debug(f"明亮模式：亮度{target_brightness}%，色温{final_temp}K")
                elif daylight_effect == 2:
                    _LOGGER.debug("执行日光效果 1(温馨)")
                    # 业务逻辑2：色温4500K，亮度60%，若色温可控范围不在4500内，则只控制亮度
                    target_brightness = 60   # 目标亮度60%
                    target_temp = 4500       # 目标色温4500K
                    # 校验色温：仅当设备支持4500K（在上下限内）时才控制色温
                    if hasattr(self, '_min_color_temp_kelvin') and hasattr(self, '_max_color_temp_kelvin'):
                        if self._min_color_temp_kelvin <= target_temp <= self._max_color_temp_kelvin:
                            data['color_temp'] = float(10**6 / target_temp)
                            self._intre_ss.call_ha_service('light', 'turn_on', data)
                            _LOGGER.debug(f"温馨模式：亮度{target_brightness}%，色温{target_temp}K")
                        else:
                            _LOGGER.debug(f"温馨模式：色温{target_temp}K超出设备范围,仅控制亮度{target_brightness}%")
                    else:
                        _LOGGER.warning("未定义设备色温范围，温馨模式仅控制亮度")
                    # 无论色温是否生效，均执行亮度控制
                    data['brightness'] = math.ceil(target_brightness * 2.55)
                    self._intre_ss.call_ha_service('light', 'turn_on', data)
                elif daylight_effect == 3:
                    _LOGGER.debug("执行日光效果 3(夜光)")
                    # 业务逻辑3：色温3500K，亮度20%，若最小色温值大于3500则直接使用色温最小值执行
                    target_brightness = 20   # 目标亮度20%
                    target_temp = 3500       # 目标色温3500K
                    # 校验色温：若最小色温>3500，使用最小值
                    final_temp = max(target_temp, self._min_color_temp_kelvin) if hasattr(self, '_min_color_temp_kelvin') else target_temp
                    # 执行控制
                    data['brightness'] = math.ceil(target_brightness * 2.55)
                    self._intre_ss.call_ha_service('light', 'turn_on', data)
                    data['color_temp'] = float(10**6 / final_temp)
                    self._intre_ss.call_ha_service('light', 'turn_on', data)
                    _LOGGER.debug(f"夜光模式：亮度{target_brightness}%，色温{final_temp}K")

            else:
                _LOGGER.debug("输入数据中未包含daylightEffect参数")

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
                    # 初始化上次亮度缓存（如果不存在）
                    if not hasattr(self, '_brightness'):
                        self._brightness = None
                    
                    # 计算转换后的亮度值（与实际发送的值保持一致）
                    converted_brightness = math.ceil(brightness_data * 2.55)
                    
                    # 与上次亮度对比，不同时才发送指令
                    if converted_brightness != self._brightness:
                        data['brightness'] = converted_brightness
                        self._intre_ss.call_ha_service('light', 'turn_on', data)
                        # 更新缓存的上次亮度值
                        self._brightness = converted_brightness
                        _LOGGER.debug(f"亮度调节: 原始值={brightness_data}, 转换后={data['brightness']}")
                    else:
                        _LOGGER.debug(f"亮度值与上次相同({brightness_data})，无需重复发送指令")
                else:
                    _LOGGER.error(f"无效的亮度值: {brightness_data},必须是0-100之间的数字")
            
            # 处理色温调节
            if 'colorTemperature' in input_data:
                color_temp_data = input_data['colorTemperature']
                # 检查数据类型和范围有效性
                if isinstance(color_temp_data, (int, float)) and self._min_color_temp_kelvin <= color_temp_data <= self._max_color_temp_kelvin:
                    # 初始化上次色温缓存（如果不存在）
                    if not hasattr(self, '_colorTemperature'):
                        self._colorTemperature = None
                    _LOGGER.debug(f"新色温={color_temp_data}K, 旧色温={self._colorTemperature}K")
                    # 与上次色温对比，不同时才发送指令
                    if color_temp_data != self._colorTemperature:
                        data['color_temp'] = float(10**6 / color_temp_data)
                        self._intre_ss.call_ha_service('light', 'turn_on', data)
                        # 更新缓存的上次色温值
                        self._colorTemperature = color_temp_data
                        _LOGGER.debug(f"色温调节: 原始值={color_temp_data}K, 转换后={data['color_temp']}mired")
                    else:
                        _LOGGER.debug(f"色温值与上次相同({color_temp_data}K)，无需重复发送指令")
                else:
                    _LOGGER.error(f"无效的色温值: {color_temp_data},必须是{self._min_color_temp_kelvin}-{self._max_color_temp_kelvin}之间的数字")
        
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
        try:
            # 1. 先获取嵌套在data里的module
            module = service_call_data.get('data', {}).get('module', {})
            if not module:
                _LOGGER.warning("未从service_call_data中获取到有效的module信息")
                return
            
            # 2. 从module中提取服务键和输入值
            service_key = module.get('service', {}).get('serviceKey')
            service_input_value = module.get('service', {}).get('serviceInputValue')

            # 3. 解析service_input_value，判断是否包含brightness
            is_brightness_request = False
            input_data = None
            if service_input_value:
                if isinstance(service_input_value, bytes):
                    service_input_value = service_input_value.decode('utf-8')
                if isinstance(service_input_value, str):
                    try:
                        input_data = json.loads(service_input_value)
                        # 核心判断：是否包含 'brightness' 字段
                        if 'brightness' in input_data:
                            is_brightness_request = True
                            _LOGGER.debug("检测到亮度调节请求，准备进行时间戳校验")
                    except json.JSONDecodeError as e:
                        _LOGGER.error(f"解析serviceInputValue失败: {e}")

            # 4. 仅对brightness请求执行时间戳对比
            current_timestamp = None
            if is_brightness_request:
                current_timestamp = service_call_data.get('timestamp')
                if not current_timestamp:
                    _LOGGER.warning("亮度调节请求中未包含timestamp，无法进行校验，将执行请求")
                else:
                    try:
                        current_timestamp = int(current_timestamp)
                    except (ValueError, TypeError):
                        _LOGGER.error(f"亮度调节请求的timestamp格式无效: {current_timestamp}，将执行请求")
                        current_timestamp = None

                    # 时间戳对比逻辑
                    if current_timestamp is not None:
                        # 初始化时间戳（如果不存在）
                        if not hasattr(self, '_last_brightness_timestamp'):
                            self._last_brightness_timestamp = 0
                        
                        if current_timestamp <= self._last_brightness_timestamp:
                            _LOGGER.debug(
                                f"亮度调节请求时间戳({current_timestamp})过期（上次：{self._last_brightness_timestamp}），丢弃该请求"
                            )
                            return  # 丢弃过期请求
                        else:
                            # 更新亮度请求的最新时间戳
                            self._last_brightness_timestamp = current_timestamp
                            _LOGGER.debug(f"更新亮度请求最新时间戳为: {current_timestamp}")

            

            for service_item in batch_service_prop_data['serviceList']:
                # 1检查是否只有toggleOnOff参数    
                if service_item['serviceKey']=='toggleOnOff':
                    service='turn_on'
                    if self._onOff==True:
                        service='turn_off'
                    _LOGGER.debug("batch_service=%s %s",service,data)  
                    self._intre_ss.call_ha_service('light',service,data)
                    continue  # 执行完后结束当前服务项的处理 
                if service_item['serviceKey'] == 'lightControlByBatchWithoutTransitionTime':
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
                    # 情况3：同时包含onOff、colorTemperature 2个参数
                    required_keys = {'onOff', 'colorTemperature'}
                    if required_keys.issubset(input_values.keys()) and len(input_values) == 2:
                        _LOGGER.debug("Found onOff, colorTemperature  - special handling")
                        service = 'turn_on'
                        
                        if service == 'turn_on':
                            # 处理色温
                            try:
                                kelvin_temp = input_values['colorTemperature']
                                mired_value = 10**6 / float(kelvin_temp)
                                data['color_temp'] = mired_value
                                _LOGGER.debug(f"Converted {kelvin_temp}K to {data['color_temp']} mired")
                            except (ZeroDivisionError, ValueError):
                                _LOGGER.error(f"Invalid color temperature value: {kelvin_temp}")
                            
                            # 处理亮度（保持不变）
                            #data['brightness'] = int((input_values.get('brightness', 0) * 255)/100) if service == 'turn_on' else None
                            #_LOGGER.debug(data['brightness'])
                        _LOGGER.debug(f"Calling service {service} with special data: {data}")
                        self._intre_ss.call_ha_service('light', service, data)
                        continue   
                    
                    # 确定开关服务类型
                    service = 'turn_on' if input_values.get('onOff', 0) else 'turn_off'
                    
                    # 处理亮度（保持不变）  
                    brightness = int((input_values.get('brightness', 0) * 255)/100) if service == 'turn_on' else None
                    _LOGGER.debug(brightness)
                    _LOGGER.debug(input_values.get('brightness'))
                    # 处理色温（将开尔文转换为Mired值）
                    color_temp = None
                    if service == 'turn_on':
                        kelvin_temp = input_values.get('colorTemperature')
                        if kelvin_temp is not None:
                            try:
                                # 转换公式：Mired = 1,000,000 / 开尔文
                                mired_value = 10**6 / float(kelvin_temp)

                                color_temp = mired_value
                                
                                _LOGGER.debug(f"Converted {kelvin_temp}K to {color_temp} mired")
                            except (ZeroDivisionError, ValueError):
                                _LOGGER.error(f"Invalid color temperature value: {kelvin_temp}")
                    
                    # 构建服务数据
                    service_data = {
                        'entity_id': self._entity_id,
                        'brightness': brightness,
                        'color_temp': color_temp,
                    }
                    
                    # 过滤掉None值
                    service_data = {k: v for k, v in service_data.items() if v is not None}
                    
                    _LOGGER.debug(f"Calling service {service} with data: {service_data}")
                    self._intre_ss.call_ha_service('light', service, service_data)
        except KeyError as e:
            _LOGGER.error(f"批量服务数据缺少必要的键: {e}")
        except Exception as e:
            _LOGGER.error(f"处理批量服务请求时发生错误: {e}")  

    def attr_change_req(self, properlist: list, msg_id: str) -> None:
        _LOGGER.debug(f"properlist: {properlist}")
        try:
            # 从列表中提取时间戳（适配实际数据结构）
            # 1. 检查列表是否为空
            if not properlist:
                _LOGGER.warning("properlist为空，无法处理属性变更请求")
                return
            
            # 2. 从列表的第一个元素中获取timestamp（根据实际数据确定）
            first_item = properlist[0]
            current_timestamp = first_item.get('timestamp')
            if not current_timestamp:
                _LOGGER.warning("属性变更数据的第一个元素中未包含timestamp，无法进行时间戳校验")
                return
            
            # 3. 转换为整数便于比较
            try:
                current_timestamp = int(current_timestamp)
            except (ValueError, TypeError):
                _LOGGER.error(f"无效的timestamp格式: {current_timestamp}，应为整数")
                return
            
            # 4. 时间戳校验（与上次请求比较）
            if hasattr(self, '_last_service_timestamp'):
                if current_timestamp <= self._last_service_timestamp:
                    _LOGGER.debug(
                        f"当前时间戳({current_timestamp})小于等于上次时间戳({self._last_service_timestamp})，丢弃该请求"
                    )
                    return
            
            # 5. 更新最后一次请求的时间戳
            self._last_brightness_timestamp = current_timestamp

            # 处理属性变更逻辑
            data = {'entity_id': self._entity_id}
            service = 'turn_on'  # 默认开灯光服务

            for prop in properlist:
                prop_key = prop.get('propertyKey')
                prop_value = prop.get('propertyValue')

                if not prop_key or prop_value is None:
                    _LOGGER.warning(f"属性数据不完整: {prop}，跳过处理")
                    continue

                # 处理开关状态
                if prop_key == 'onOff':
                    if prop_value == '0':
                        service = 'turn_off'
                        _LOGGER.debug("收到关灯指令")
                    else:
                        service = 'turn_on'
                        _LOGGER.debug("收到开灯指令")
                    self._intre_ss.call_ha_service('light', service, data)

                # 处理亮度调节
                elif prop_key == 'brightness':
                    try:
                        brightness = int(prop_value)
                        if 0 <= brightness <= 100:
                            # 转换为Home Assistant的亮度范围（0-255）
                            data['brightness'] = int((brightness * 255) / 100)
                            self._intre_ss.call_ha_service('light', 'turn_on', data)
                            _LOGGER.debug(f"亮度调节至: {brightness}% (转换后: {data['brightness']})")
                        else:
                            _LOGGER.error(f"亮度值超出范围(0-100): {brightness}")
                    except (ValueError, TypeError):
                        _LOGGER.error(f"无效的亮度值: {prop_value}，应为整数")

                # 处理色温调节
                elif prop_key == 'colorTemperature':
                    try:
                        kelvin = int(prop_value)
                        # 检查设备是否定义了色温范围
                        if not (hasattr(self, '_min_color_temp_kelvin') and hasattr(self, '_max_color_temp_kelvin')):
                            _LOGGER.warning("设备未定义色温范围，无法调节色温")
                            continue
                        # 检查色温是否在有效范围内
                        if self._min_color_temp_kelvin <= kelvin <= self._max_color_temp_kelvin:
                            # 转换为Mired值（Home Assistant使用）
                            data['color_temp'] = int(10**6 / kelvin)
                            self._intre_ss.call_ha_service('light', 'turn_on', data)
                            _LOGGER.debug(f"色温调节至: {kelvin}K (转换后: {data['color_temp']} mired)")
                        else:
                            _LOGGER.error(
                                f"色温值超出设备范围({self._min_color_temp_kelvin}-{self._max_color_temp_kelvin}K): {kelvin}"
                            )
                    except (ValueError, TypeError):
                        _LOGGER.error(f"无效的色温值: {prop_value}，应为整数")

                # 处理未知属性
                else:
                    _LOGGER.debug(f"忽略未知属性: {prop_key}")

        except IndexError:
            _LOGGER.error("properlist索引错误，可能列表为空或元素不存在")
        except KeyError as e:
            _LOGGER.error(f"属性数据缺少必要的键: {e}")
        except Exception as e:
            _LOGGER.error(f"处理属性变更请求时发生错误: {e}")

async def test_fun()->bool:
    _LOGGER.debug("test-light")  
