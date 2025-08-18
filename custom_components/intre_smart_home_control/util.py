import asyncio
import base64
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntries
from homeassistant.config_entries import ConfigEntry




_LOGGER = logging.getLogger(__name__)


class StateUtils:
    @staticmethod
    def util_get_state_onoff(state) -> bool:
        if state is not None:
            return state.state == 'on'
        return False

    @staticmethod
    def util_get_state_brightness(state) -> int:
        """安全获取亮度并转换为百分比"""
        # 先检查状态是否有效，以及是否存在 brightness 属性
        if not state or state.attributes.get('brightness') is None:
            return 0  # 或其他默认值，如 100
        
        # 确保获取到的值是数字类型
        brightness = state.attributes.get('brightness', 0)
        try:
            # 转换为 0-100 范围（HA 中亮度通常为 0-255）
            return round(brightness / 2.55)
        except (TypeError, ValueError):
            # 处理非数字的异常情况
            return False
    @staticmethod
    def util_get_state_colorTemperature(state) -> int:
        """安全获取色温并转换"""
        # 检查状态是否有效以及 color_temp 是否存在且不为 None
        if not state or state.attributes.get('color_temp') is None:
            _LOGGER.debug("No color_temp attribute found in state")
            return 0  # 或返回一个默认的色温值，如 3000（根据设备默认值调整）
        
        try:
            # 确保 color_temp 是有效的数值
            color_temp = state.attributes['color_temp']
            # 进行转换计算（开尔文 = 1,000,000 / mired值）
            kelvin = 10 ** 6 / float(color_temp)
            # 按原逻辑取50的倍数
            return int(kelvin / 50) * 50
        except (TypeError, ValueError, ZeroDivisionError) as e:
            _LOGGER.error(f"Error calculating color temperature: {e}")
            return 0  # 出错时返回默认值
    @staticmethod
    def util_get_min_color_temperature(state) -> int:
        """获取最小色温（开尔文）"""
        if not state or 'min_color_temp_kelvin' not in state.attributes:
            _LOGGER.debug("No min_color_temp_kelvin attribute found in state")
            return 0
        
        try:
            min_kelvin = state.attributes['min_color_temp_kelvin']
            return int(min_kelvin / 50) * 50
        except (TypeError, ValueError) as e:
            _LOGGER.error(f"Error getting min color temperature: {e}")
            return 0

    @staticmethod
    def util_get_max_color_temperature(state) -> int:
        """获取最大色温（开尔文）"""
        if not state or 'max_color_temp_kelvin' not in state.attributes:
            _LOGGER.debug("No max_color_temp_kelvin attribute found in state")
            return 0
        
        try:
            max_kelvin = state.attributes['max_color_temp_kelvin']
            return int(max_kelvin / 50) * 50
        except (TypeError, ValueError) as e:
            _LOGGER.error(f"Error getting max color temperature: {e}")
            return 0
     
        
    @staticmethod
    def util_get_state_positionPercentage(state) -> int:
        """安全获取位置百分比（适用于窗帘、百叶窗等设备）"""
        # 检查状态是否有效
        if not state:
            _LOGGER.debug("Invalid or empty state object")
            return 0  # 返回默认值或根据业务逻辑调整
        
        # 尝试从常见属性中获取位置信息（不同设备可能使用不同属性名）
        position_attrs = ['position', 'current_position', 'position_percentage']
        position = None
        
        for attr in position_attrs:
            if attr in state.attributes and state.attributes[attr] is not None:
                position = state.attributes[attr]
                break
        
        if position is None:
            _LOGGER.debug("No position attribute found in state")
            return 0  # 无位置信息时返回默认值
        
        try:
            # 转换为数值并校验范围（百分比通常为0-100）
            position_val = float(position)
            if not (0 <= position_val <= 100):
                _LOGGER.warning(f"Position value {position_val} out of 0-100 range")
                # 限制值在有效范围内
                clamped_val = max(0, min(100, position_val))
                return int(round(clamped_val))
            
            # 返回四舍五入后的整数百分比
            return int(round(position_val))
        
        except (TypeError, ValueError) as e:
            _LOGGER.error(f"Error parsing position value: {e}")
            return 0  # 解析失败时返回默认值
