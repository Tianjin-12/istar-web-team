"""
DeepSeek 多账号管理 CLI

用法:
  python scripts/manage_accounts.py login          登录新账号并保存认证状态
  python scripts/manage_accounts.py list           查看所有账号
  python scripts/manage_accounts.py verify         验证所有已启用账号
  python scripts/manage_accounts.py verify <name>  验证指定账号
  python scripts/manage_accounts.py enable <name>  启用账号
  python scripts/manage_accounts.py disable <name> 禁用账号
  python scripts/manage_accounts.py remove <name>  删除账号
"""

import sys
import os
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "myproject"))

from mvp.account_manager import (
    add_account,
    remove_account,
    set_account_enabled,
    get_auth_state_path,
    verify_account,
    print_accounts_table,
)
from playwright.sync_api import sync_playwright


def cmd_login():
    print("=== 添加 DeepSeek 账号 ===\n")

    name = input("输入账号名称(如 account_1): ").strip()
    if not name:
        print("错误: 名称不能为空")
        return
    if " " in name:
        print("错误: 名称不能包含空格")
        return

    print("\n登录方式:")
    print("  1. 手机号 + 密码")
    print("  2. 第三方登录 (Google/微信等，需要手动操作)")
    choice = input("选择 (1/2): ").strip()

    login_method = ""
    phone = ""
    password = ""

    if choice == "1":
        login_method = "phone"
        phone = input("输入手机号: ").strip()
        if not phone:
            print("错误: 手机号不能为空")
            return
        password = input("输入密码: ").strip()
    elif choice == "2":
        login_method = "third_party"
        print("将使用第三方登录，请在弹出的浏览器中手动完成登录")
    else:
        print("无效选择")
        return

    print(f"\n正在启动浏览器登录账号: {name}")
    print("登录成功后将自动保存认证状态...\n")

    try:
        with sync_playwright() as p:
            stealth_js_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "stealth.min.js"
            )

            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            if os.path.exists(stealth_js_path):
                with open(stealth_js_path, "r", encoding="utf-8") as f:
                    page.add_init_script(f.read())

            page.goto("https://chat.deepseek.com")
            page.wait_for_timeout(3000)

            if login_method == "phone":
                try:
                    page.click(
                        "//div[@class='ds-sign-in-form__social-buttons-container']/button[1]"
                    )
                    page.wait_for_timeout(1000)
                    page.fill(
                        "//div[@class='ds-form-item__content']//input[@type='text']",
                        phone,
                    )
                    page.fill(
                        "//div[@class='ds-form-item__content']//input[@type='password']",
                        password,
                    )
                    page.click("//div[@class='ds-auth-form__main-hero']/button")
                    print("已自动填入手机号和密码...")
                except Exception as e:
                    print(f"自动填充失败，请手动登录: {e}")

            if login_method == "third_party":
                try:
                    page.click(
                        "//div[@class='ds-sign-in-form__social-buttons-container']/button[1]"
                    )
                except Exception:
                    pass

            print("\n--- 请在浏览器中完成登录 ---")
            print("登录成功后页面会显示聊天输入框")
            print("脚本会自动检测登录状态...\n")

            max_wait = 120
            start_time = time.time()
            logged_in = False

            while time.time() - start_time < max_wait:
                try:
                    has_textarea = page.locator("textarea").count() > 0
                    current_url = page.url
                    if has_textarea or "chat" in current_url:
                        logged_in = True
                        break
                except Exception:
                    pass
                time.sleep(2)

            if not logged_in:
                print("超时: 120秒内未检测到登录成功")
                browser.close()
                return

            print("检测到登录成功! 正在保存认证状态...")
            page.wait_for_timeout(2000)

            auth_path = get_auth_state_path(name)
            context.storage_state(path=str(auth_path))

            context.close()
            browser.close()

        add_account(name=name, login_method=login_method, phone=phone)

        print(f"\n账号 '{name}' 添加成功!")
        print(f"认证文件已保存到: {auth_path}")
        print("\n所有账号列表:")
        print_accounts_table()

    except Exception as e:
        print(f"登录过程出错: {e}")
        import traceback

        traceback.print_exc()


def cmd_list():
    print_accounts_table()


def cmd_verify(account_name=None):
    if account_name:
        print(f"正在验证账号: {account_name} ...")
        result = verify_account(account_name)
        status = (
            "有效" if result["valid"] else f"无效 ({result.get('error', '未知原因')})"
        )
        print(f"  {account_name}: {status}")
    else:
        config = __import__(
            "mvp.account_manager", fromlist=["load_accounts_config"]
        ).load_accounts_config()
        enabled = [acc for acc in config["accounts"] if acc["enabled"]]
        if not enabled:
            print("没有已启用的账号")
            return

        print(f"正在验证 {len(enabled)} 个已启用账号...\n")
        for acc in enabled:
            result = verify_account(acc["name"])
            status = (
                "有效"
                if result["valid"]
                else f"无效 ({result.get('error', '未知原因')})"
            )
            print(f"  {acc['name']}: {status}")


def cmd_enable(name):
    if set_account_enabled(name, True):
        print(f"已启用账号: {name}")
    else:
        print(f"未找到账号: {name}")


def cmd_disable(name):
    if set_account_enabled(name, False):
        print(f"已禁用账号: {name}")
    else:
        print(f"未找到账号: {name}")


def cmd_remove(name):
    if remove_account(name):
        print(f"已删除账号: {name}")
    else:
        print(f"未找到账号: {name}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "login":
        cmd_login()
    elif command == "list":
        cmd_list()
    elif command == "verify":
        account_name = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_verify(account_name)
    elif command == "enable":
        if len(sys.argv) < 3:
            print("用法: python manage_accounts.py enable <name>")
            sys.exit(1)
        cmd_enable(sys.argv[2])
    elif command == "disable":
        if len(sys.argv) < 3:
            print("用法: python manage_accounts.py disable <name>")
            sys.exit(1)
        cmd_disable(sys.argv[2])
    elif command == "remove":
        if len(sys.argv) < 3:
            print("用法: python manage_accounts.py remove <name>")
            sys.exit(1)
        cmd_remove(sys.argv[2])
    else:
        print(f"未知命令: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
