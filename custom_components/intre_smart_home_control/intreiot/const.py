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
DOMAIN: str = 'intre_smart_home_control'
DEFAULT_NAME: str = 'Intre Home Control'

DEFAULT_NICK_NAME: str = 'Intretech'
INTRE_HA_CONTROL_VERSION:int = 7
INTREHOME_HTTP_API_TIMEOUT: int = 30
INTREHOME_MQTT_KEEPALIVE: int = 60
# seconds, 3 days

NETWORK_REFRESH_INTERVAL: int = 30

OAUTH2_CLIENT_ID: str = '2882303761520251711'
OAUTH2_AUTH_URL: str = 'https://account.Intretech.com/oauth2/authorize'
DEFAULT_OAUTH2_API_HOST: str = 'ha.api.io.mi.com'

INTRE_HA_PRODUCT_KEY="Intre.BGZ001"
INTRE_PHYSICAL_MODEL_CONTROL_VERSION:int = 2

#MQTT_ToH ='test/'
#INTRE_SECURE_KEY ="123456"
#INTREIOT_HTTP_SERVER_URL = 'https://server1.intreplus.com:4432'
MQTT_ToH =''
INTRE_SECURE_KEY ="intre-prod"
INTREIOT_HTTP_SERVER_URL = 'https://mars.intreplus.com'

# seconds, 14 days
SPEC_STD_LIB_EFFECTIVE_TIME = 3600*24*14
# seconds, 14 days
MANUFACTURER_EFFECTIVE_TIME = 3600*24*14

MODULE_PRIORITY_DB:list=[
    'airConditioner',
    'floorHeating',
    'freshAir',  
    'draperyCurtain',
    'dualColorTemperatureLight',
    'singleColorTemperatureLight',
    'RGBWLight',
    'RGBCWLight',
    'switch',
]

PRODUCT_KEY_DB:dict ={
    'switch':'Intre.HA-Switch',
    'draperyCurtain':'Intre.HA-Curtain',
    'dualColorTemperatureLight':'Intre.HA-Light',
    'singleColorTemperatureLight':'Intre.HA-Light',
    'RGBWLight':'Intre.HA-Light',
    'RGBCWLight':'Intre.HA-Light', 
}

SUPPORTED_PLATFORMS: list = [
    'switch',
    'cover',
    'light',
]

DEFAULT_CLOUD_SERVER: str = 'cn'
CLOUD_SERVERS: dict = {
    'cn': '中国大陆'
}

SYNC_FUN_TYPE:dict={
    'device':'设备',
    'scene':'情景'
}

SYNC_AREA_TYPE:dict={
    'no':'不同步',
    'room':'楼层房间名称',
    'home':'家庭和楼层房间名称',
}
SUPPORT_CENTRAL_GATEWAY_CTRL: list = ['cn']

DEFAULT_INTEGRATION_LANGUAGE: str = 'en'
INTEGRATION_LANGUAGES = {
    'de': 'Deutsch',
    'en': 'English',
    'es': 'Español',
    'fr': 'Français',
    'ja': '日本語',
    'nl': 'Nederlands',
    'pt': 'Português',
    'pt-BR': 'Português (Brasil)',
    'ru': 'Русский',
    'zh-Hans': '简体中文',
    'zh-Hant': '繁體中文'
}

MQTT_MSG_CODE_TEXT={
    '1':'成功'
}

DEFAULT_CTRL_MODE: str = 'auto'

# Registered in Intretech OAuth 2.0 Service
# DO NOT CHANGE UNLESS YOU HAVE AN ADMINISTRATOR PERMISSION
OAUTH_REDIRECT_URL: str = 'http://homeassistant.local:8123'

INTREHOME_CA_CERT_STR: str = """-----BEGIN CERTIFICATE-----
MIIDjTCCAnWgAwIBAgIUbwjXwSdo05JahQRjB+NGDFZ1+MMwDQYJKoZIhvcNAQEL
BQAwVTELMAkGA1UEBhMCQ04xDzANBgNVBAgMBkZ1amlhbjEPMA0GA1UEBwwGeGlh
bWVuMRIwEAYDVQQKDAlJTlRSRVRFQ0gxEDAOBgNVBAMMB3Jvb3RfY2EwIBcNMjMx
MjIyMTAzOTE1WhgPMjEyMzExMjgxMDM5MTVaMFUxCzAJBgNVBAYTAkNOMQ8wDQYD
VQQIDAZGdWppYW4xDzANBgNVBAcMBnhpYW1lbjESMBAGA1UECgwJSU5UUkVURUNI
MRAwDgYDVQQDDAdyb290X2NhMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKC
AQEAv6XAoXDhYtm6l5RrbaKs55bw73GQfTZfHMR/yPvC+nrtxTO6kPXrM+JBkcH3
k3S7jR7C9QdOjLChoQl8vBfPYrIZjb0Wgn1Ih7MRaog9KqzgrcymKxFiipfO+sjb
oBBnSE4sgkoKXeS2FSjw4edQ7riqSWrwt6nXxwL+R5UXExHHaiRkGgxx7h/DAvaG
xbB7kp45LYa0OtBXoJ+QmjCW7PtMyuJk377s7LEdvKqcX1EURB9aAq3ObUUbiQFR
0kxEKKuLpycsmJARfMMtuZpvZ2OiYWeLV+4qoEtXNk/eUmL8xL4nHPgrSWeNky0m
0heR93hF2yqFAkCgnVsqYKCdbQIDAQABo1MwUTAdBgNVHQ4EFgQU/Rjl7nYfkwk2
QVCIZPxbhS9pPkEwHwYDVR0jBBgwFoAU/Rjl7nYfkwk2QVCIZPxbhS9pPkEwDwYD
VR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAmc5pPp+QqP1BOD7tAMpk
INipvlX1kctm/qj7puVERnTVwmFjFexRi4DKlNmuo9iYxYqR8TVbwunbNYYBJvZP
2KYTmUImqJP/mnLSyxrOOo+uqpDsvnknEizkbfV30cqd2VdpDkK9UL0+fkcowOdp
RwfW307ykB69OOMJ4CwkMPcTwzgcLWxcQIwAkyDVzD0mG2EV4wmHLILsLNMLdqC5
GbP3N9anZefMmbWBUwS0a6//t9+y0T69cooeULUbhOsnagGnLKbJwaScpwJgbks/
AZmuHyeEjGPvVcfGkshEv0pyLN4OVCqJ+BfFFTpWfua3tJ0q4e+ks6Yn04v7Fngg
5g==
-----END CERTIFICATE-----
"""


