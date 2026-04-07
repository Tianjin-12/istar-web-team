import asyncio
import os
import sys
import time
from datetime import datetime, timedelta

from playwright.async_api import async_playwright, BrowserContext, Page

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

import django

django.setup()

from mvp.models import QuestionBank, AIAnswer, AILink
from mvp.account_manager import load_enabled_accounts

SEND_DS = "//div[@class='_7436101 ds-icon-button ds-icon-button--l ds-icon-button--sizing-container']"

STEALTH_JS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "stealth.min.js",
)

BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
]

MAX_RETRIES = 3
WAIT_STABLE_SECONDS = 10


async def load_stealth_js() -> str:
    if os.path.exists(STEALTH_JS_PATH):
        with open(STEALTH_JS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""


async def wait_for_response(page: Page, total_timeout: int = 120) -> None:
    last_text = ""
    same_count = 0
    start_time = time.time()
    while same_count < WAIT_STABLE_SECONDS:
        if time.time() - start_time > total_timeout:
            print("  等待响应超时，强制结束")
            break
        messages = await page.query_selector_all('[class*="message"]')
        if messages:
            current_text = await messages[-1].inner_text()
            if current_text == last_text:
                same_count += 1
            else:
                same_count = 0
                last_text = current_text
                print(f"  生成中... ")
        else:
            same_count += 1
        await asyncio.sleep(1)


async def collect_url(page: Page) -> list[str]:
    try:
        selectors = [
            "//div[@class='f93f59e4']",
            "._source-links-button",
            "[class*='source-links']",
        ]

        element_found = False
        for selector in selectors:
            try:
                if selector.startswith("//"):
                    element_count = await page.locator(selector).count()
                    if element_count > 0:
                        await page.click(selector)
                        element_found = True
                        print(f"  通过XPath {selector} 找到并点击了元素")
                        break
                else:
                    element_count = await page.locator(selector).count()
                    if element_count > 0:
                        await page.click(selector)
                        element_found = True
                        print(f"  通过CSS选择器 {selector} 找到并点击了元素")
                        break
            except Exception:
                continue

        if not element_found:
            print("  未找到相关元素，尝试直接查找链接")
            link_selectors = [
                "//div[@class='dc433409']/a",
                "a[href*='http']",
                "[class*='source-link'] a",
            ]

            links_found = []
            for link_selector in link_selectors:
                try:
                    links = await page.query_selector_all(link_selector)
                    if links:
                        links_found = links
                        print(
                            f"  通过选择器 {link_selector} 找到了 {len(links)} 个链接"
                        )
                        break
                except Exception:
                    continue

            if not links_found:
                print("  未找到任何链接")
                return []
        else:
            await page.wait_for_timeout(2000)
            links_found = await page.query_selector_all("//div[@class='dc433409']/a")
            print(f"  找到 {len(links_found)} 个链接元素")

        links: list[str] = []
        for i, element in enumerate(links_found):
            try:
                href = await element.get_attribute("href")
                if href and href.startswith(("http://", "https://")):
                    links.append(href)
            except Exception as e:
                print(f"  处理链接 {i} 时出错: {e}")

        print(f"  成功收集 {len(links)} 个链接")
        return links
    except Exception as e:
        print(f"  收集链接时出错: {e}")
        return []


async def process_single_question(
    context: BrowserContext,
    account_name: str,
    question: dict,
    question_index: int,
    total_questions: int,
    stealth_js: str,
) -> tuple[str, str, list[str]]:
    """
    处理单个问题，返回 (question_id, answer_text, links)

    每次调用创建一个新 page，处理完后关闭。
    """
    page = await context.new_page()

    if stealth_js:
        await page.add_init_script(stealth_js)

    try:
        print(
            f"\n[{account_name}] 问题 {question_index}/{total_questions}: {question['question'][:50]}..."
        )

        await page.goto("https://chat.deepseek.com", timeout=30000)
        await page.wait_for_selector("textarea", state="visible", timeout=10000)

        try:
            clear_button = page.locator("//button[contains(@class, 'clear')]")
            if await clear_button.count() > 0 and await clear_button.is_visible():
                await clear_button.click()
                await page.wait_for_selector("textarea", state="visible", timeout=10000)
        except Exception:
            await page.reload()
            await page.wait_for_selector("textarea", state="visible", timeout=10000)

        textarea = page.locator("//textarea")
        await textarea.fill("")
        await textarea.fill(question["question"])

        button_selector = "//div[@class='ec4f5d61']/div[1]"
        button_fallbacks = [
            "button:has-text('深度思考')",
            "[data-testid='toggle-deep-think']",
            "//button[contains(text(), '深度思考')]",
        ]
        button = None
        for sel in [button_selector] + button_fallbacks:
            try:
                btn = page.locator(sel)
                if await btn.count() > 0:
                    button = btn
                    break
            except Exception:
                continue

        if button is None:
            print("  未找到深度思考按钮，跳过")
        else:
            class_name = await button.get_attribute("class")
            if class_name and "selected" in class_name:
                await button.click()
                print("  深度思考按钮已关闭")

        button_selector2 = "//div[@class='ec4f5d61']/div[2]"
        button_fallbacks2 = [
            "button:has-text('联网搜索')",
            "[data-testid='toggle-search']",
            "//button[contains(text(), '联网搜索')]",
        ]
        button2 = None
        for sel in [button_selector2] + button_fallbacks2:
            try:
                btn = page.locator(sel)
                if await btn.count() > 0:
                    button2 = btn
                    break
            except Exception:
                continue

        if button2 is None:
            print("  未找到联网搜索按钮，跳过")
        else:
            class_name2 = await button2.get_attribute("class")
            if class_name2 and "selected" in class_name2:
                print("  联网搜索按钮已处于按下状态")
            else:
                await button2.click()
                print("  联网搜索按钮已点击")

        await page.click(SEND_DS)

        await wait_for_response(page)

        result_list = await page.locator(
            "//div[@class='ds-message _63c77b1']/div[@class='ds-markdown']"
        ).all()

        if not result_list:
            result_list = await page.locator(
                ".ds-markdown--user, [class*='ds-markdown']"
            ).all()

        if not result_list:
            result_list = await page.locator(
                "//div[contains(@class, 'ds-message')]//div[contains(@class, 'markdown')]"
            ).all()

        answer_text = ""
        for res in result_list:
            text = await res.inner_text()
            answer_text += text + "\n\n"

        links = await collect_url(page)

        num_extra = 1
        all_links = list(links)

        for i in range(num_extra):
            try:
                continue_selectors = [
                    "//div[@class='ds-icon-button db183363'][2]",
                    "button:has-text('继续生成')",
                    "//div[contains(@class, 'ds-icon-button')][2]",
                ]
                continue_button = None
                for sel in continue_selectors:
                    try:
                        btn = page.locator(sel)
                        if await btn.count() > 0 and await btn.is_visible():
                            continue_button = btn
                            break
                    except Exception:
                        continue

                if continue_button:
                    await continue_button.click()
                else:
                    retry_selectors = [
                        "//div[@class='_5a8ac7a a084f19e']",
                        "button:has-text('重新生成')",
                        "//div[contains(@class, 'a084f19e')]",
                    ]
                    retry_button = None
                    for sel in retry_selectors:
                        try:
                            btn = page.locator(sel)
                            if await btn.count() > 0:
                                retry_button = btn
                                break
                        except Exception:
                            continue
                    if retry_button:
                        await retry_button.click()
                await page.fill("//textarea", question["question"])
                await page.click(SEND_DS)
                await wait_for_response(page)
                result_list = await page.locator(
                    "//div[@class='ds-message _63c77b1']/div[@class='ds-markdown']"
                ).all()
                if not result_list:
                    result_list = await page.locator(
                        "//div[contains(@class, 'ds-message')]//div[contains(@class, 'markdown')]"
                    ).all()
                for res in result_list:
                    text = await res.inner_text()
                    answer_text += text + "\n\n"
                more_links = await collect_url(page)
                all_links.extend(more_links)
            except Exception as e:
                print(f"  继续生成回答时出错: {e}")
                break

        print(f"[{account_name}] 问题 {question_index}/{total_questions} 完成")
        await page.wait_for_timeout(2000)

        return question["index"], answer_text, all_links

    finally:
        await page.close()


async def process_with_retry(
    context: BrowserContext,
    browser,
    account_name: str,
    question: dict,
    question_index: int,
    total_questions: int,
    stealth_js: str,
    storage_state_path: str,
) -> tuple[str, str, list[str]]:
    for attempt in range(MAX_RETRIES):
        try:
            return await process_single_question(
                context,
                account_name,
                question,
                question_index,
                total_questions,
                stealth_js,
            )
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(
                    f"[{account_name}] 问题 {question_index} 第{attempt + 1}次失败，重试... 错误: {e}"
                )
                await asyncio.sleep(5 * (attempt + 1))
                try:
                    test_page = await context.new_page()
                    await test_page.goto("https://chat.deepseek.com", timeout=10000)
                    await test_page.close()
                    print(f"[{account_name}] context 正常，继续重试")
                except Exception:
                    print(f"[{account_name}] context 已损坏，重建 context")
                    try:
                        await context.close()
                    except Exception:
                        pass
                    new_ctx = await browser.new_context(
                        storage_state=storage_state_path
                    )
                    return await process_with_retry(
                        new_ctx,
                        browser,
                        account_name,
                        question,
                        question_index,
                        total_questions,
                        stealth_js,
                        storage_state_path,
                    )
            else:
                print(f"[{account_name}] 问题 {question_index} 最终失败: {e}")
                raise


def save_answer_to_db(
    keyword: str, question_id: str, question_text: str, answer_text: str
) -> AIAnswer:
    today = datetime.now().date()
    answer, created = AIAnswer.objects.get_or_create(
        keyword=keyword,
        question_id=question_id,
        question_text=question_text,
        answer_date=today,
        defaults={"answer_text": answer_text},
    )
    return answer


def save_links_to_db(answer: AIAnswer, links: list[str]) -> None:
    if not links:
        return
    link_objs = [AILink(answer=answer, link_url=link) for link in links]
    AILink.objects.bulk_create(link_objs, batch_size=50)


def load_questions_for_crabbing(keyword: str) -> list[dict]:
    questions = list(
        QuestionBank.objects.filter(keyword=keyword)
        .order_by("cluster_id")
        .values("cluster_id", "generated_question")
    )
    formatted: list[dict] = []
    for i, q in enumerate(questions, 1):
        formatted.append(
            {
                "index": str(i),
                "cluster_id": q["cluster_id"],
                "question": q["generated_question"],
            }
        )
    return formatted


def check_ai_answer_cache(keyword: str) -> tuple[bool, int]:
    threshold = datetime.now() - timedelta(days=1)
    cached_count = AIAnswer.objects.filter(
        keyword=keyword, answer_date=datetime.now().date(), created_at__gte=threshold
    ).count()
    return cached_count > 0, cached_count


async def collect_answers_parallel_async(
    keyword: str, concurrency: int | None = None
) -> bool:
    try:
        has_cache, count = check_ai_answer_cache(keyword)
        if has_cache:
            print(f"使用缓存: 找到 {count} 个回答")
            return True

        accounts = load_enabled_accounts()
        if not accounts:
            raise Exception(
                "没有可用的 DeepSeek 账号，请先运行: python scripts/manage_accounts.py login"
            )

        actual_concurrency = concurrency or len(accounts)
        actual_concurrency = min(actual_concurrency, len(accounts))
        print(f"可用账号: {len(accounts)} 个，并发数: {actual_concurrency}")

        questions = load_questions_for_crabbing(keyword)
        if not questions:
            print("没有需要处理的问题")
            return True

        print(f"从数据库加载了 {len(questions)} 个问题")
        stealth_js = await load_stealth_js()

        async with async_playwright() as p:
            is_headless = os.getenv("CRABBING_HEADLESS", "true").lower() == "true"
            browser = await p.chromium.launch(
                headless=is_headless,
                args=BROWSER_ARGS,
            )

            contexts: list[BrowserContext] = []
            for account in accounts[:actual_concurrency]:
                ctx = await browser.new_context(storage_state=account["auth_file_path"])
                contexts.append(ctx)

            total_count = len(questions)
            success_count = 0
            fail_count = 0
            start_time = time.time()

            try:
                for batch_start in range(0, total_count, actual_concurrency):
                    batch = questions[batch_start : batch_start + actual_concurrency]

                    tasks = []
                    for i, q in enumerate(batch):
                        real_index = batch_start + i + 1
                        ctx = contexts[i % len(contexts)]
                        acc = accounts[i % len(accounts)]
                        acc_name = acc["name"]
                        tasks.append(
                            process_with_retry(
                                ctx,
                                browser,
                                acc_name,
                                q,
                                real_index,
                                total_count,
                                stealth_js,
                                acc["auth_file_path"],
                            )
                        )

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for result in results:
                        if isinstance(result, Exception):
                            print(f"处理失败: {result}")
                            fail_count += 1
                        else:
                            question_id, answer_text, links = result
                            try:
                                answer = save_answer_to_db(
                                    keyword=keyword,
                                    question_id=question_id,
                                    question_text=next(
                                        (
                                            q["question"]
                                            for q in batch
                                            if q["index"] == question_id
                                        ),
                                        "",
                                    ),
                                    answer_text=answer_text,
                                )
                                if links:
                                    save_links_to_db(answer, links)
                                success_count += 1
                            except Exception as e:
                                print(f"保存数据库失败: {e}")
                                fail_count += 1

                    elapsed = time.time() - start_time
                    done = batch_start + len(batch)
                    eta = (elapsed / done) * (total_count - done) if done > 0 else 0
                    print(
                        f"\n--- 进度: {done}/{total_count} "
                        f"成功: {success_count} 失败: {fail_count} "
                        f"耗时: {elapsed:.0f}s 预计剩余: {eta:.0f}s ---"
                    )

            finally:
                for ctx in contexts:
                    await ctx.close()
                await browser.close()

        elapsed = time.time() - start_time
        print(
            f"\n所有问题处理完成! 成功: {success_count}, 失败: {fail_count}, 总耗时: {elapsed:.0f}s"
        )
        return True

    except Exception as e:
        print(f"收集AI回答时出错: {str(e)}")
        import traceback

        traceback.print_exc()
        raise e
