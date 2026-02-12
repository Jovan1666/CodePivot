"""CodePivot — AI 编程工具配置切换器"""

import sys
import webview
from pathlib import Path
from api import Api


def _get_base_path() -> Path:
    """获取资源根目录：打包后用 sys._MEIPASS，开发时用脚本所在目录"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


BASE_DIR = _get_base_path()
FRONTEND_DIR = BASE_DIR / "frontend"


def main():
    api = Api()
    window = webview.create_window(
        title="CodePivot",
        url=str(FRONTEND_DIR / "index.html"),
        js_api=api,
        width=1050,
        height=620,
        resizable=True,
        text_select=True,
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
