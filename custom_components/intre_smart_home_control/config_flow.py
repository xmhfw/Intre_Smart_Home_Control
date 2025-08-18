# custom_components/my_integration/config_flow.py
from typing import Optional, Set, Tuple
import voluptuous as vol
import traceback
import qrcode
from io import BytesIO
import base64
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow
import homeassistant.helpers.config_validation as cv
from .intreiot.intreIot_cloud import IntreIotHttpClient
import logging
from .intreiot.const import (
    DOMAIN,
    DEFAULT_CLOUD_SERVER,
    DEFAULT_CTRL_MODE,
    DEFAULT_INTEGRATION_LANGUAGE,
    DEFAULT_NICK_NAME,
    DEFAULT_OAUTH2_API_HOST,
    DOMAIN,
    OAUTH2_AUTH_URL,
    OAUTH2_CLIENT_ID,
    CLOUD_SERVERS,
    OAUTH_REDIRECT_URL,
    INTEGRATION_LANGUAGES,
    SUPPORT_CENTRAL_GATEWAY_CTRL,
    NETWORK_REFRESH_INTERVAL,
    SYNC_FUN_TYPE,
    SYNC_AREA_TYPE,
)


_LOGGER = logging.getLogger(__name__)
class IntreHomeControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for My Integration."""
    
    VERSION = 2

    _device_sync:bool
    _scene_sync:bool
    _show_qr_code:bool
    
    def __init__(self) -> None:
        self._cc_home_list_show = {}
        self._device_sync = False
        self._scene_sync=False
        self._show_qr_code=False

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        return await self.async_step_eula(user_input)

    async def async_step_eula(
        self, user_input: Optional[dict] = None
    ):
        if user_input:
            if user_input.get('eula', None) is True:
                return await self.async_step_configs_select(user_input)
            return await self.__show_eula_form('eula_not_agree')
        return await self.__show_eula_form('')

    async def __show_eula_form(self, reason: str):
        return self.async_show_form(
            step_id='eula',
            data_schema=vol.Schema({
                vol.Required('eula', default=False): bool,  # type: ignore
            }),
            last_step=False,
            errors={'base': reason},
        )
    
    async def async_step_configs_select(
        self, user_input: Optional[dict] = None
    ):
        _LOGGER.debug('async_step_configs_select')
        try:
            if user_input.get('device', None) is None:
                if user_input.get('scene', None) is None:
                    return await self.__show_configs_select_form('')
            if user_input.get('device', None) is False:
                if user_input.get('scene', None) is False: 
                    return await self.__show_configs_select_form('请至少选择一种类型！')
            self._device_sync = user_input.get('device', False)
            self._scene_sync = user_input.get('scene', False)
            return self.async_show_progress_done(next_step_id='show_qrcode') 
 
        except Exception as err:
            _LOGGER.debug(
                'async_step_configs_select, %s, %s',
                err, traceback.format_exc())
            raise AbortFlow(
                reason='config_flow_error',
                description_placeholders={
                    'error': f'config_flow error, {err}'}
            ) from err

    async def __show_configs_select_form(self, reason: str):
        return self.async_show_form(
            step_id='configs_select',
            data_schema=vol.Schema({
                vol.Required('device', default=False): bool,
                vol.Required('scene', default=False): bool,
            }),
            errors={'base': reason},
            last_step=False,
        )
    def generate_qr_code_base64(self,data):
        """Generate a QR code and return it as a Base64-encoded string."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Save the image to a BytesIO buffer
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return img_str
    
    async def async_step_show_qrcode(
        self, user_input: Optional[dict] = None
    ):
        """Show the QR code step."""
        if self._show_qr_code:
            return await self.config_flow_done()
        self._show_qr_code = True
        return await self.__show_show_qrcode_form('')

    async def __show_show_qrcode_form(self, reason: str):
        client = IntreIotHttpClient()
        lanip=client.get_local_ip()
        devicesn=self.flow_id
        _LOGGER.debug('--------------------------------------------------')
        _LOGGER.debug(devicesn)
        await client.getToken(devicesn=devicesn)
        qr_code_rsp = await client.getQRcode()
        await client.deinit_async()
        qr_code_data=self.generate_qr_code_base64(qr_code_rsp['qrCode'])
        return self.async_show_form(
            step_id='show_qrcode',
            description_placeholders={
                "qr_code":"请使用盈趣智能APP扫码添加\r\n ![](data:image/png;base64,"+qr_code_data+")",
            },
            errors={'base': reason},
            last_step=False,
        )
    async def config_flow_done(self):
        return self.async_create_entry(title="IntreHomeControl", data={
            'device_sync':self._device_sync,
            'scene_sync':self._scene_sync,
            'devicesn':self.flow_id
        })
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return IntreHomeControlOptionsFlow(config_entry)
    
    

class IntreHomeControlOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for My Integration."""
    _device_sync:bool
    _scene_sync:bool
    def __init__(self, config_entry):
        """Initialize options flow."""
        
        self.config_entry = config_entry
        self._device_sync =self.config_entry.data['device_sync']
        self._scene_sync =self.config_entry.data['scene_sync']
        self._show_qr_code = False

    async def async_step_init(self, user_input=None):
        return await self.async_step_configs_select()
        
    async def async_step_configs_select(
        self, user_input: Optional[dict] = None
    ):
        _LOGGER.debug('async_step_configs_select')
        try:
            if user_input is None:
                 return await self.__show_configs_select_form('')
            if user_input.get('device', None) is False:
                if user_input.get('scene', None) is False: 
                    return await self.__show_configs_select_form('请至少选择一种类型！')
            self._device_sync = user_input.get('device', False)
            self._scene_sync = user_input.get('scene', False)
            return self.async_show_progress_done(next_step_id='show_qrcode') 
 
        except Exception as err:
            _LOGGER.debug(
                'async_step_configs_select, %s, %s',
                err, traceback.format_exc())
            raise AbortFlow(
                reason='config_flow_error',
                description_placeholders={
                    'error': f'config_flow error, {err}'}
            ) from err

    async def __show_configs_select_form(self, reason: str):
        return self.async_show_form(
            step_id='configs_select',
            data_schema=vol.Schema({
                vol.Required('device', default=self._device_sync): bool,
                vol.Required('scene', default=self._scene_sync): bool,
            }),
            errors={'base': reason},
            last_step=False,
        )
    def generate_qr_code_base64(self,data):
        """Generate a QR code and return it as a Base64-encoded string."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Save the image to a BytesIO buffer
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return img_str
    
    async def async_step_show_qrcode(
        self, user_input: Optional[dict] = None
    ):
        """Show the QR code step."""
        if self._show_qr_code:
            # Update entry config
            self.hass.config_entries.async_update_entry(
                self._config_entry, title="IntreHomeControl", data={
                'device_sync':self._device_sync,
                'scene_sync':self._scene_sync
                })
            # Reload later
            self._main_loop.call_later(
                0, lambda: self._main_loop.create_task(
                    self.hass.config_entries.async_reload(
                        entry_id=self._config_entry.entry_id)))
            return self.async_create_entry(title='', data={})
        self._show_qr_code = True
        return await self.__show_show_qrcode_form('')

    async def __show_show_qrcode_form(self, reason: str):
        client:IntreIotHttpClient = IntreIotHttpClient()
        qrcodestr = await client.getQRcode()
        qr_code_data=self.generate_qr_code_base64(qrcodestr)
        return self.async_show_form(
            step_id='show_qrcode',
            description_placeholders={
                "qr_code":"请使用盈趣智能APP扫码添加\r\n ![](data:image/png;base64,"+qr_code_data+")",
            },
            errors={'base': reason},
            last_step=False,
        )
    