"""暴露给前端的 PyWebView API"""

import config_manager as cm


class Api:
    """PyWebView API — 前端通过 window.pywebview.api.xxx() 调用"""

    def get_vendors(self) -> dict:
        return cm.get_vendors()

    def save_vendor_config(self, vendor: str, config_data: dict) -> dict:
        return cm.save_vendor_config(vendor, config_data)

    def delete_vendor_config(self, vendor: str, config_id: str) -> bool:
        return cm.delete_vendor_config(vendor, config_id)

    def switch_vendor_config(self, vendor: str, config_id: str) -> dict:
        return cm.switch_vendor_config(vendor, config_id)

    def detect_clients(self) -> dict:
        return cm.detect_clients()
