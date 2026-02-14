"""环境变量设置辅助工具 - 从命令行配置系统环境变量"""

import argparse
import json
import os
import sys
from pathlib import Path

# 添加项目目录到路径
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

import env_manager as ev
import config_manager as cm

# 获取 ANSI 颜色代码
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.OKGREEN}{text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}Error: {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}{text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}{text}{Colors.ENDC}")

def show_vendors():
    """显示所有厂商和配置"""
    vendors = cm.get_vendors()

    print_header("\n可用的厂商配置：")
    print()

    for vendor_key, vendor_data in vendors.items():
        configs = vendor_data.get('configs', [])
        current_id = vendor_data.get('current_config_id')

        print(f"{Colors.BOLD}{vendor_data['display_name']} ({vendor_key}){Colors.ENDC}")

        if configs:
            for cfg in configs:
                is_current = cfg['id'] == current_id
                prefix = "  * " if is_current else "    "
                status = f"{Colors.OKGREEN}[当前]{Colors.ENDC}" if is_current else ""
                print(f"{prefix}{cfg['name']}: '{cfg['api_url'][:50]}...' {status}")
        else:
            print("    (无配置)")
        print()

def deploy_vendor_config(vendor: str, config_name: str = None):
    """部署指定厂商的配置到系统环境变量"""
    vendors = cm.get_vendors()

    if vendor not in vendors:
        print_error(f"不支持的厂商: {vendor}")
        print(f"支持的厂商: {', '.join(vendors.keys())}")
        return False

    vendor_data = vendors[vendor]
    configs = vendor_data.get('configs', [])

    if not configs:
        print_error(f"厂商 {vendor} 没有任何配置")
        return False

    # 选择配置
    config = None
    if config_name:
        config = next((c for c in configs if c['name'] == config_name), None)
        if not config:
            print_error(f"未找到配置: {config_name}")
            return False
    else:
        # 使用当前配置
        current_id = vendor_data.get('current_config_id')
        if current_id:
            config = next((c for c in configs if c['id'] == current_id), None)

        if not config:
            print_warning("没有当前配置，使用第一个配置")
            config = configs[0]

    print_header(f"\n即将部署配置：{config['name']}")
    print(f"厂商: {vendor_data['display_name']}")
    print(f"API 地址: {config.get('api_url', 'N/A')}")
    print(f"API 密钥: {config.get('api_key', '')[:10]}...")
    print(f"模型: {config.get('model', 'N/A')}")
    print()

    # 确认
    response = input(f"{Colors.WARNING}确认部署到系统环境变量? (y/n): {Colors.ENDC}")
    if response.lower() != 'y':
        print_info("已取消")
        return False

    # 执行部署
    print_info("正在部署...")
    result = ev.deploy_to_env_vars(vendor, config)

    if result['success']:
        print_success("部署成功！")
        print()
        print("已设置的环境变量：")
        for var in result.get('set_vars', []):
            print(f"  ✓ {var}")

        if result.get('failed_vars'):
            print()
            print_warning("部分环境变量设置失败：")
            for var in result.get('failed_vars'):
                print(f"  ✗ {var}")

        print()
        print_header("重要提示：")
        print("1. 请关闭当前终端窗口")
        print("2. 重新打开终端，环境变量才会生效")
        print("3. 之后可以正常使用 CLI 工具")
        return True
    else:
        print_error(result.get('message', '部署失败'))
        return False

def show_env_status(vendor: str = None):
    """显示环境变量状态"""
    if vendor:
        print_header(f"\n{vendor.upper()} 环境变量状态：")
        status = ev.get_env_vars_status(vendor)
        for var, value in status.items():
            if value:
                display_value = value[:30] + '...' if len(value) > 30 else value
                print(f"  {var}: {display_value}")
            else:
                print(f"  {var}: (未设置)")
    else:
        print_header("\n所有环境变量状态：")
        for v in ev.VENDOR_ENV_MAP.keys():
            print(f"\n{v.upper()}:")
            status = ev.get_env_vars_status(v)
            for var, value in status.items():
                if value:
                    display_value = value[:30] + '...' if len(value) > 30 else value
                    print(f"  {var}: {display_value}")
                else:
                    print(f"  {var}: (未设置)")
    print()

def main():
    parser = argparse.ArgumentParser(description='环境变量设置辅助工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # list 命令
    subparsers.add_parser('list', help='列出所有厂商和配置')

    # deploy 命令
    deploy_parser = subparsers.add_parser('deploy', help='部署配置到系统环境变量')
    deploy_parser.add_argument('vendor', help='厂商标识 (claude/codex/gemini/opencode)')
    deploy_parser.add_argument('--name', help='配置名称 (不指定则使用当前配置)')

    # status 命令
    status_parser = subparsers.add_parser('status', help='显示环境变量状态')
    status_parser.add_argument('--vendor', help='指定厂商 (不指定则显示所有)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'list':
        show_vendors()
    elif args.command == 'deploy':
        deploy_vendor_config(args.vendor, args.name)
    elif args.command == 'status':
        show_env_status(args.vendor)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
