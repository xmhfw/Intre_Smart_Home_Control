import logging
from typing import Dict, Type, Optional

_LOGGER = logging.getLogger(__name__)

class EngineManager:
    """全局引擎管理器，用于存储和获取各种引擎实例"""
    _instance = None
    _engines: Dict[str, object] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EngineManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register_instance(cls, name: str, instance: object) -> None:
        """注册引擎实例"""
        if name in cls._engines:
            _LOGGER.warning(f"Engine {name} already registered, overwriting")
        cls._engines[name] = instance
        _LOGGER.debug(f"Registered engine: {name}")

    @classmethod
    def get_instance(cls, name: str) -> Optional[object]:
        """获取引擎实例"""
        instance = cls._engines.get(name)
        if not instance:
            _LOGGER.debug(f"Engine {name} not found")
        return instance

    @classmethod
    def unregister_instance(cls, name: str) -> None:
        """注销引擎实例"""
        if name in cls._engines:
            del cls._engines[name]
            _LOGGER.debug(f"Unregistered engine: {name}")
