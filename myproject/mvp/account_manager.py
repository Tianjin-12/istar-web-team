import json
import os
import sys
from datetime import datetime
from pathlib import Path

ACCOUNTS_DIR = Path(__file__).resolve().parent.parent.parent / "deepseek_accounts"
ACCOUNTS_CONFIG = ACCOUNTS_DIR / "accounts.json"


def get_accounts_dir() -> Path:
    return ACCOUNTS_DIR


def load_accounts_config() -> dict:
    if not ACCOUNTS_CONFIG.exists():
        return {"accounts": []}
    with open(ACCOUNTS_CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def save_accounts_config(config: dict) -> None:
    ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ACCOUNTS_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_auth_state_path(account_name: str) -> Path:
    return ACCOUNTS_DIR / f"{account_name}.json"


def add_account(
    name: str,
    login_method: str,
    phone: str = "",
    enabled: bool = True,
) -> dict:
    config = load_accounts_config()
    for acc in config["accounts"]:
        if acc["name"] == name:
            raise ValueError(f"账号 '{name}' 已存在")

    auth_file = f"{name}.json"
    account = {
        "name": name,
        "auth_file": auth_file,
        "login_method": login_method,
        "phone": phone,
        "enabled": enabled,
        "last_verified": None,
        "created_at": datetime.now().isoformat(),
    }
    config["accounts"].append(account)
    save_accounts_config(config)
    return account


def remove_account(name: str) -> bool:
    config = load_accounts_config()
    original_len = len(config["accounts"])
    config["accounts"] = [acc for acc in config["accounts"] if acc["name"] != name]

    if len(config["accounts"]) == original_len:
        return False

    save_accounts_config(config)

    auth_path = get_auth_state_path(name)
    if auth_path.exists():
        auth_path.unlink()

    return True


def set_account_enabled(name: str, enabled: bool) -> bool:
    config = load_accounts_config()
    for acc in config["accounts"]:
        if acc["name"] == name:
            acc["enabled"] = enabled
            save_accounts_config(config)
            return True
    return False


def load_enabled_accounts() -> list[dict]:
    config = load_accounts_config()
    result = []
    for acc in config["accounts"]:
        if not acc["enabled"]:
            continue
        auth_path = ACCOUNTS_DIR / acc["auth_file"]
        if not auth_path.exists():
            print(f"警告: 账号 '{acc['name']}' 的认证文件不存在，跳过")
            continue
        result.append(
            {
                "name": acc["name"],
                "auth_file_path": str(auth_path),
                "login_method": acc["login_method"],
                "phone": acc.get("phone", ""),
                "last_verified": acc.get("last_verified"),
            }
        )
    return result


def verify_account(account_name: str) -> dict:
    from playwright.sync_api import sync_playwright

    auth_path = get_auth_state_path(account_name)
    if not auth_path.exists():
        return {"name": account_name, "valid": False, "error": "认证文件不存在"}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(auth_path))
            page = context.new_page()
            page.goto("https://chat.deepseek.com", timeout=15000)
            page.wait_for_timeout(3000)

            has_textarea = page.locator("textarea").count() > 0
            current_url = page.url

            context.close()
            browser.close()

            if has_textarea or "chat" in current_url:
                config = load_accounts_config()
                for acc in config["accounts"]:
                    if acc["name"] == account_name:
                        acc["last_verified"] = datetime.now().isoformat()
                save_accounts_config(config)
                return {"name": account_name, "valid": True}
            else:
                return {"name": account_name, "valid": False, "error": "登录已过期"}
    except Exception as e:
        return {"name": account_name, "valid": False, "error": str(e)}


def print_accounts_table() -> None:
    config = load_accounts_config()
    accounts = config["accounts"]

    if not accounts:
        print("暂无账号，请先运行: python scripts/manage_accounts.py login")
        return

    print(f"\n{'名称':<15} {'登录方式':<20} {'状态':<8} {'上次验证':<20}")
    print("-" * 70)
    for acc in accounts:
        status = "启用" if acc["enabled"] else "禁用"
        verified = acc.get("last_verified") or "未验证"
        if verified != "未验证":
            verified = verified[:19]
        method = acc["login_method"]
        if acc.get("phone"):
            method += f" ({acc['phone']})"
        print(f"{acc['name']:<15} {method:<20} {status:<8} {verified:<20}")
    print()
