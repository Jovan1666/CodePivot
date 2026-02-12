# CodePivot

A lightweight desktop tool for switching AI coding tool configurations with one click.

轻量级 AI 编程工具配置一键切换器，支持多个 AI CLI 工具的 API 配置管理与快速切换。

## Supported Tools

- **Claude Code** — CLI + VSCode Extension
- **Codex** — CLI + IDE Extension
- **Gemini CLI** — Google AI Terminal Agent
- **OpenCode** — Open-source Terminal AI Assistant

## Features

- One-click switch between multiple API providers / relay services
- Manage multiple configurations per tool
- Auto-backup before switching
- Atomic file writes to prevent config corruption
- Lightweight — Python + PyWebView, no heavy frameworks

## Quick Start

### Run from Source

```bash
pip install -r requirements.txt
python main.py
```

### Build Installer

```bash
# Requires PyInstaller + Inno Setup 6
build.bat
```

Output:
- **Portable**: `dist\AI模型切换器\AI模型切换器.exe`
- **Installer**: `installer_output\CodePivot_Setup_1.0.0.exe`

## Tech Stack

- **Backend**: Python 3.11+
- **Frontend**: HTML + Tailwind CSS + Vanilla JS
- **Window**: PyWebView (EdgeChromium on Windows)
- **Packaging**: PyInstaller + Inno Setup

## Screenshot

![CodePivot](https://via.placeholder.com/800x500?text=CodePivot+Screenshot)

## License

MIT
