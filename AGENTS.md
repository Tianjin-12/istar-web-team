【本项目agent指导文件】
这个文件用于管理模型的长期记忆
请在执行完任务以后，在此文件的末尾添加数条你认为需要被记住的关于项目的事项
如果你是plan模式，请先记住，当你是Build模式时再添加
【在下面添加】

1. 服务器环境信息
   - 云服务商：腾讯云
   - 操作系统：Ubuntu Server 24.04 LTS 64bit
   - 项目部署路径：/var/www/myproject
   - 用户权限：www-data
   - 虚拟环境：/var/www/myproject/venv

2. 关键文件位置
   - 搜索功能：/var/www/myproject/myproject/mvp/searching.py
   - 仪表盘应用：/var/www/myproject/myproject/mvp/dash_apps.py
   - Celery 任务：/var/www/myproject/myproject/mvp/tasks.py
   - Django 设置：/var/www/myproject/myproject/myproject/settings.py
   - 视图函数：/var/www/myproject/myproject/mvp/views.py
   - 测试脚本：/var/www/myproject/test_searching.py（新创建）

3. 技术栈和架构
   - 后端框架：Django 4.2.26
   - 数据库：PostgreSQL 16
   - 缓存/队列：Redis（端口 6380）
   - 任务队列：Celery
   - 前端可视化：Plotly Dash
   - 网页爬虫：Playwright（无头浏览器）
   - Web 服务器：Gunicorn
   - 反向代理：Nginx
   - 进程管理：Supervisor

4. 服务配置
   - Gunicorn 配置文件：/etc/supervisor/conf.d/myproject.conf
   - Nginx 配置文件：/etc/nginx/sites-available/myproject
   - 日志目录：/var/log/myproject/
   - Gunicorn 日志：/var/log/gunicorn/
   - Celery 日志：/var/log/celery/
   - Flower 监控：http://42.193.136.148:5555 或 https://istar-geo.com/flower/

5. 数据库配置
   - 数据库名：mvpdb
   - 用户：postgres
   - 密码：mvp123
   - 连接超时：10秒
   - 连接池最大连接数：CONN_MAX_AGE = 600

6. 任务链流程（订单处理）
   阶段1: schedule_order_processing (每天00:00触发)
     ↓
   阶段2: search_questions - 搜索知乎问题
     ↓
   阶段3: build_question_bank - 构建问题库
     ↓
   阶段4: collect_ai_answers - 收集AI回答
     ↓
   阶段5: score_questions - 评分问题
     ↓
   阶段6: analyze_orders_by_keyword - 分析订单

7. 重要配置文件
   - 环境变量：/var/www/myproject/.env
   - 部署脚本：/var/www/myproject/deploy/
   - 静态文件：/var/www/myproject/staticfiles/
   - Cookie 文件：/var/www/myproject/cookies.txt（如果有）
   - Stealth.js：/var/www/myproject/stealth.min.js（反爬虫脚本）

8. 常见问题解决方案
   - Playwright 浏览器未安装：sudo -u www-data /var/www/myproject/venv/bin/playwright install chromium
   - 查看任务日志：sudo tail -f /var/log/celery/worker.log
   - 重启服务：sudo supervisorctl restart myproject:*
   - 查看服务状态：sudo supervisorctl status
   - 查看失败任务：访问 Flower 界面或查询 Django Admin 的 TaskLog 表

19. 域名和IP
    - 主域名：https://istar-geo.com
    - 服务器IP：42.193.136.148
    - DEBUG模式：False（生产环境）
    - ALLOWED_HOSTS：istar-geo.com,localhost,127.0.0.1

10. 缓存机制
    - ZhihuQuestion 缓存期：7天
    - dashboard-data 缓存期：3600秒（1小时）
    - Django 默认缓存：300秒（5分钟）

11. 重要提醒
    - 修改 searching.py 时必须确保兼容 Linux 服务器环境
    - 所有脚本必须使用 sudo -u www-data 执行
    - 不要硬编码 Windows 路径
    - 部署前必须测试 Playwright 浏览器是否能正常启动

12. TaskLog 模型字段名（2025-03-19）
    - 使用 started_at 而不是 created_at
    - started_at: 任务开始时间
    - completed_at: 任务完成时间
    - 可用字段：id, task_type, status, started_at, completed_at, duration, error_message, order_id, retry_count

13. 测试脚本位置（2025-03-19）
    - 测试脚本：/var/www/myproject/test_searching.py
    - 服务器适配版：/var/www/myproject/searching_server.py
    - 日志文件：/var/log/myproject/test_searching.log

14. Playwright API 注意事项（2026-04-02）
    - `no_viewport` 参数只在 `launch_persistent_context()` 上可用，`browser.launch()` 不支持
    - `scripts/` 目录在项目根目录下，`mvp/` 包在 `myproject/` 子目录下
    - sys.path 需要指向 `myproject/` 才能导入 `mvp.account_manager`
    - 编写代码时必须区分 `browser.launch()` 和 `launch_persistent_context()` 的 API 差异

15. 项目目录结构（2026-04-02）
    - 项目根目录：MVP2/
    - Django 项目目录：MVP2/myproject/
    - Django 应用目录：MVP2/myproject/mvp/
    - 脚本目录：MVP2/scripts/
    - 账号认证目录：MVP2/deepseek_accounts/
    - 导入 mvp 包时，sys.path 需要包含 MVP2/myproject/

16. 低级错误反省（2026-04-02）
    - 写代码前必须先确认目录结构，不能凭猜测设置 sys.path
    - 使用 Playwright API 前必须确认参数是否存在于对应方法上
    - `launch()` vs `launch_persistent_context()` 参数不同，不能混用
    - 修改代码后应自行检查是否有明显错误再提交

