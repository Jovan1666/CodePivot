"""暴露给前端的 PyWebView API"""

import traceback
import config_manager as cm


def _safe_call(func, *args, error_return=None):
    """包装调用，捕获异常返回友好提示而不是原始 traceback"""
    try:
        return func(*args)
    except Exception as e:
        traceback.print_exc()  # 服务端日志保留完整堆栈
        if error_return == "dict":
            return {"success": False, "message": f"操作失败: {e}", "details": []}
        raise RuntimeError(str(e))  # 返回简洁错误信息给前端


class Api:
    """PyWebView API — 前端通过 window.pywebview.api.xxx() 调用"""

    def get_vendors(self) -> dict:
        return _safe_call(cm.get_vendors)

    def save_vendor_config(self, vendor: str, config_data: dict) -> dict:
        return _safe_call(cm.save_vendor_config, vendor, config_data)

    def delete_vendor_config(self, vendor: str, config_id: str) -> bool:
        return _safe_call(cm.delete_vendor_config, vendor, config_id)

    def switch_vendor_config(self, vendor: str, config_id: str) -> dict:
        return _safe_call(cm.switch_vendor_config, vendor, config_id, error_return="dict")

    def detect_clients(self) -> dict:
        return _safe_call(cm.detect_clients)
