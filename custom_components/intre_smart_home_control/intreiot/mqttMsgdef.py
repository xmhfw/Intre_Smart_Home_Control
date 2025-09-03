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

Constants.
"""
import json
import time
import logging
import hmac
import hashlib
from .const import (MQTT_MSG_CODE_TEXT,MQTT_ToH,INTRE_SECURE_KEY)
_LOGGER = logging.getLogger(__name__)

def __calculate_checksum(topic:str, timestamp: str,msg_id: str,token:str) -> str:
        input_string = topic + timestamp + msg_id + token
        hmac_sha1 = hmac.new(
            #key='A0123456789'.encode('utf-8'),  # 密钥
            key=INTRE_SECURE_KEY.encode('utf-8'),  # 密钥
            msg=input_string.encode('utf-8'),  # 输入字符串
            digestmod=hashlib.sha1  # 使用 SHA1 算法
        )
        desiget=hmac_sha1.hexdigest()
        return desiget

def MQTT_SET_PROPERTY(token,deviceid, moduleKey, propKey, propValue):
    timestamp_ms = str(int(time.time() * 1000))
    return {
        "topic":'home/'+token+'/up/device/property/set',
        "payload": {
            "token": token,
            "msgId": "1",
            "sign":__calculate_checksum(MQTT_ToH+'device/'+productkey+'/'+deviceid+'/up/device/property/set',timestamp_ms,'1',token),
            "timestamp": timestamp_ms,
            "data": {
                "deviceId": deviceid,
                "deviceModuleList": [
                    {
                        "moduleKey": moduleKey,
                        "propertyList": [
                            {
                                "propertyKey": propKey,
                                "propertyValue": propValue,
                                "timestamp": timestamp_ms
                            }
                        ]
                    }
                ]
            }
        }
    }

def MQTT_BATCH_MODULE_PROP_REPORT(token,productkey:str,deviceid:str, batch_modules:list):
    timestamp_ms = str(int(time.time() * 1000))
    mqtt_message =  {
        "topic":'device/'+productkey+'/'+deviceid+'/up/tls/property/report',
        "payload": {
            "token": token,
            "msgId": "1",
            "timestamp": timestamp_ms,
            "sign":__calculate_checksum(MQTT_ToH+'device/'+productkey+'/'+deviceid+'/up/tls/property/report',timestamp_ms,'1',token),
            "data": {
                "deviceModuleList": batch_modules
            }
        }
    }
    # 打印MQTT消息（格式化输出）
    _LOGGER.debug(f"生成的MQTT属性上报消息:")
    _LOGGER.debug(json.dumps(mqtt_message, indent=2))
    
    return mqtt_message

def MQTT_DEVICE_TLS_LOG_REPORT(token,productkey:str,deviceid:str, tls_logs:list):
    timestamp_ms = str(int(time.time() * 1000))
    mqtt_message =  {
        "topic":'device/'+productkey+'/'+deviceid+'/up/tls/device-tsl-log/report',
        "payload": {
            "token": token,
            "msgId": "1",
            "timestamp": timestamp_ms,
            "sign":__calculate_checksum(MQTT_ToH+'device/'+productkey+'/'+deviceid+'/up/tls/device-tsl-log/report',timestamp_ms,'1',token),
            "data": {
                "deviceModuleList": tls_logs
            }
        }
    }
    # 打印MQTT消息（格式化输出）
    _LOGGER.debug(f"生成的MQTT属性上报消息:")
    _LOGGER.debug(json.dumps(mqtt_message, indent=2))
    
    return mqtt_message

def MQTT_DEVICE_DOWN_TLS_LOG_REPORT(token,productkey:str,deviceid:str):
    timestamp_ms = str(int(time.time() * 1000))
    mqtt_message =  {
        "topic":'device/'+productkey+'/'+deviceid+'/down/tls/device-tsl-log/report',
        "payload": {
            "token": token,
            "msgId": "1",
            "timestamp": timestamp_ms,
            "sign":__calculate_checksum(MQTT_ToH+'device/'+productkey+'/'+deviceid+'/down/tls/device-tsl-log/report',timestamp_ms,'1',token),
        }
    }
    # 打印MQTT消息（格式化输出）
    _LOGGER.debug(f"生成的MQTT属性上报消息:")
    _LOGGER.debug(json.dumps(mqtt_message, indent=2))
    
    return mqtt_message

def MQTT_PROPERTY_REPORT(token,productkey:str,deviceid:str, modulekey:str,propkey:str,prop_value:str):
    timestamp_ms = str(int(time.time() * 1000))
    mqtt_message =  {
        "topic":'device/'+productkey+'/'+deviceid+'/up/tls/property/report',
        "payload": {
            "token": token,
            "msgId": "1",
            "timestamp": timestamp_ms,
            "sign":__calculate_checksum(MQTT_ToH+'device/'+productkey+'/'+deviceid+'/up/tls/property/report',timestamp_ms,'1',token),
            "data": {
                "deviceModuleList": [
                {
                    "moduleKey": modulekey,
                    "propertyList": [
                    {
                        "propertyKey": propkey,
                        "propertyValue": prop_value,
                        "timestamp": timestamp_ms
                    }
                    ]
                }
                ]
            }
        }
    }
    # 打印MQTT消息（格式化输出）
    _LOGGER.debug(f"生成的MQTT属性上报消息:")
    _LOGGER.debug(json.dumps(mqtt_message, indent=2))
    
    return mqtt_message

def MQTT_EVENT_REPORT(token,productkey:str,deviceid:str, modulekey:str,eventkey:str,event_value:str):
    timestamp_ms = str(int(time.time() * 1000))
    mqtt_message =  {
        "topic":'device/'+productkey+'/'+deviceid+'/up/tls/event/report',
        "payload": {
            "msgId": "1",
            "timestamp": timestamp_ms,
            "sign":__calculate_checksum(MQTT_ToH+'device/'+productkey+'/'+deviceid+'/up/tls/event/report',timestamp_ms,'1',token),
            "data": {
                "deviceModuleList": [
                {
                    "moduleKey": modulekey,
                    "eventList": [
                    {
                        "eventKey": eventkey,
                        "timestamp": timestamp_ms,
                        "eventValue": event_value
                    }
                    ]
                }
                ]
            },
            "token": token
        }
    }
    # 打印MQTT消息（格式化输出）
    _LOGGER.debug(f"生成的MQTT属性上报消息:")
    _LOGGER.debug(json.dumps(mqtt_message, indent=2))
    
    return mqtt_message

def MQTT_PROPERTY_SET_REPLY(token,productkey:str,deviceid:str,msgid:str,code:str):
    timestamp_ms = str(int(time.time() * 1000))
    mqtt_message = {
        "topic":'device/'+productkey+'/'+deviceid+'/up/tls/property/set-reply', 
        "payload": {
            "token": token,
            "msgId": msgid,
            "timestamp": timestamp_ms,    
            "sign":__calculate_checksum(MQTT_ToH+'device/'+productkey+'/'+deviceid+'/up/tls/property/set-reply',timestamp_ms,msgid,token),
            "code": code,
            "msg": "1",
            "data": {}
        }
    }
    # 打印MQTT消息（格式化输出）
    _LOGGER.debug(f"生成的MQTT属性上报消息:")
    _LOGGER.debug(json.dumps(mqtt_message, indent=2))
    
    return mqtt_message

def MQTT_BATCH_PROPERTY_SERVICE_REPLY(token:str,productkey:str,deviceid:str,msgid:str,code:str):
    timestamp_ms = str(int(time.time() * 1000))
    return {
        "topic":'device/'+productkey+'/'+deviceid+'/up/tls/batch/property/service/set-reply',
        "payload": {
            "token": token,
            "msgId": msgid,
            "sign":__calculate_checksum(MQTT_ToH+'device/'+productkey+'/'+deviceid+'/up/tls/batch/property/service/set-reply',timestamp_ms,'1',token),
            "code": code,
            "msg": MQTT_MSG_CODE_TEXT.get(code,' '),
            "timestamp": timestamp_ms,
            "data": {}
        }
    }  

def MQTT_SERVER_SET_REPLY(token,productkey:str,deviceid:str,moduleKey:str,serviceKey:str,msgid:str,code:str):
    timestamp_ms = str(int(time.time() * 1000))
    mqtt_message = {
        "topic":'device/'+productkey+'/'+deviceid+'/up/tls/service/call-reply',
        "payload": {
            "token": token,
            "msgId": msgid,
            "timestamp": timestamp_ms,    
            "sign":__calculate_checksum(MQTT_ToH+'device/'+productkey+'/'+deviceid+'/up/tls/service/call-reply',timestamp_ms,msgid,token),
            "code": code,
            "msg": "1",
            "data": {
                "module": {
                    "moduleKey": moduleKey,
                    "service": {
                        "serviceKey": serviceKey,
                        "serviceOutputValue": ""
                    }
                }
            }
        }
    }
    # 打印MQTT消息（格式化输出）
    _LOGGER.debug(f"生成的MQTT属性上报消息:")
    _LOGGER.debug(json.dumps(mqtt_message, indent=2))
    
    return mqtt_message

def MQTT_ONLINE_REPORT(token:str,productkey:str,deviceid:str,onlinestatus:int):
    timestamp_ms = str(int(time.time() * 1000))

    mqtt_message = {
        "topic":'device/'+productkey+'/'+deviceid+'/up/online/report',
        "payload": {
            "token": token,
            "msgId": '1',
            "timestamp": timestamp_ms,
            "sign":__calculate_checksum(MQTT_ToH+'device/'+productkey+'/'+deviceid+'/up/online/report',timestamp_ms,'1',token),
            "data":{
                "online": onlinestatus,
                "timestamp": timestamp_ms,
                "reasonType": 1 
            } 
        }
    }
    # 打印MQTT消息（格式化输出）
    _LOGGER.debug(f"生成的MQTT属性上报消息:")
    _LOGGER.debug(json.dumps(mqtt_message, indent=2))
    return mqtt_message

def MQTT_ONLINE_SET_WILL_REPORTT(token:str,productkey:str,deviceid:str,onlinestatus:int):
    timestamp_ms = str(int(time.time() * 1000))

    mqtt_message = {
        "topic":MQTT_ToH+'device/'+productkey+'/'+deviceid+'/up/online/report',
        "payload": {
            "token": token,
            "msgId": '1',
            "timestamp": timestamp_ms,
            "sign":__calculate_checksum(MQTT_ToH+'device/'+productkey+'/'+deviceid+'/up/online/report',timestamp_ms,'1',token),
            "data":{
                "online": onlinestatus,
                "timestamp": timestamp_ms,
                "reasonType": 1 
            } 
        }
    }
    # 打印MQTT消息（格式化输出）
    _LOGGER.debug(f"生成的MQTT属性上报消息:")
    _LOGGER.debug(json.dumps(mqtt_message, indent=2))
    return mqtt_message

def MQTT_DATA_DEFINE_REPORT(token,productkey:str,deviceid:str, data_define:list):
    timestamp_ms = str(int(time.time() * 1000))

    mqtt_message = {
        "topic":'device/'+productkey+'/'+deviceid+'/up/tls/data-define/report',
        "payload": {
            "token": token,
            "msgId": '1',
            "timestamp": timestamp_ms,
            "sign":__calculate_checksum(MQTT_ToH+'device/'+productkey+'/'+deviceid+'/up/tls/data-define/report',timestamp_ms,'1',token),
             "data": {
                "deviceModuleList": data_define
            } 
        }
    }
    # 打印MQTT消息（格式化输出）
    _LOGGER.debug(f"生成的MQTT属性上报消息:")
    _LOGGER.debug(json.dumps(mqtt_message, indent=2))
    return mqtt_message

def HTTP_DEL_SCENE_REQ(entity_id:str):
    return {
            "identifier":entity_id 
        }  

def HTTP_ADD_SCENE_REQ(name:str,entity_id:str,parent_id):
    service_input_dict = {
        "sceneId": entity_id
    }
    service_input_value = json.dumps(service_input_dict)
    return{
        "identifier":entity_id ,
        "sceneName": name,
        "execution": [
            {
            "device": {
                "deviceId":parent_id,
                "moduleKey":"deviceInfo",
                "propertyList":self._propertylist,
                "serviceList": [
                {
                    "serviceKey":  "executeScene",
                    "serviceInputValue": service_input_value
                }
                ]
            }
            }
        ]
    }  