# 部署指南

## 文件说明

- `deploy/Dockerfile` - Docker 镜像构建文件
- `deploy/myproject.conf` - Supervisor 进程管理配置
- `deploy/nginx.conf` - Nginx 反向代理配置
- `deploy/health_monitor.sh` - 健康检查脚本
- `deploy/deploy.sh` - 自动化部署脚本
- `.env.production` - 生产环境环境变量模板

## 部署前准备

### 1. 服务器环境

```bash
# Ubuntu
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3-pip
sudo apt install -y postgresql-15 postgresql-contrib
sudo apt install -y redis-server
sudo apt install -y supervisor
sudo apt install -y nginx
sudo apt install -y build-essential
```

### 2. PostgreSQL 配置

```bash
# 设置密码
sudo -u postgres psql
ALTER USER postgres WITH PASSWORD 'your_password';
\q

# 创建数据库
sudo -u postgres createdb mvpdb

# 配置监听地址
sudo nano /etc/postgresql/15/main/postgresql.conf
# 修改: listen_addresses = '*'

# 配置 pg_hba.conf
sudo nano /etc/postgresql/15/main/pg_hba.conf
# 添加: host all all 0.0.0.0/0 md5

# 重启 PostgreSQL
sudo systemctl restart postgresql
```

### 3. Redis 配置

```bash
# 修改端口为 6380（避免与默认 6379 冲突）
sudo nano /etc/redis/redis.conf
# 修改: port 6380

# 重启 Redis
sudo systemctl restart redis
```

## 部署步骤

### 方式一：使用自动化脚本（推荐）

```bash
# 1. 上传项目到服务器
rsync -avz --exclude '__pycache__' --exclude 'venv' --exclude '.git' \
  /path/to/local/MVP2/ user@server:/tmp/MVP2/

# 2. 登录服务器
ssh user@server

# 3. 进入项目目录
cd /tmp/MVP2

# 4. 执行部署脚本
chmod +x deploy/deploy.sh
sudo bash deploy/deploy.sh

# 5. 配置环境变量
sudo nano /var/www/myproject/.env
# 修改以下配置：
# SECRET_KEY=your_random_secret_key
# POSTGRES_PASSWORD=your_password
# API_KEY=your_openai_api_key
# DEBUG=False
# ALLOWED_HOSTS=istar-geo.com,your-server-ip

# 6. 创建超级用户
cd /var/www/myproject/myproject
sudo -u www-data /var/www/myproject/venv/bin/python manage.py createsuperuser

# 7. 启动服务
sudo supervisorctl start myproject:*

# 8. 检查状态
sudo supervisorctl status
```

### 方式二：手动部署

```bash
# 1. 创建目录
sudo mkdir -p /var/www/myproject
sudo mkdir -p /var/log/myproject
sudo mkdir -p /var/log/gunicorn
sudo mkdir -p /var/log/celery
sudo mkdir -p /var/log/flower
sudo mkdir -p /var/log/health-monitor
sudo mkdir -p /var/archive/tasks
sudo mkdir -p /var/www/myproject/scripts

# 2. 复制项目文件
sudo cp -r myproject /var/www/myproject/
sudo cp requirements.txt /var/www/myproject/
sudo cp .env.production /var/www/myproject/.env
sudo cp deploy/health_monitor.sh /var/www/myproject/scripts/
sudo chmod +x /var/www/myproject/scripts/health_monitor.sh

# 3. 创建虚拟环境
cd /var/www/myproject
sudo python3 -m venv venv

# 4. 设置权限
sudo chown -R www-data:www-data /var/www/myproject
sudo chown -R www-data:www-data /var/log/myproject
sudo chown -R www-data:www-data /var/log/gunicorn
sudo chown -R www-data:www-data /var/log/celery
sudo chown -R www-data:www-data /var/log/flower
sudo chown -R www-data:www-data /var/log/health-monitor
sudo chown -R www-data:www-data /var/archive/tasks
sudo chmod -R 755 /var/www/myproject

# 5. 安装依赖
sudo -u www-data /var/www/myproject/venv/bin/pip install --upgrade pip
sudo -u www-data /var/www/myproject/venv/bin/pip install -r /var/www/myproject/requirements.txt

# 6. 安装 Playwright 浏览器
sudo -u www-data /var/www/myproject/venv/bin/playwright install chromium

# 7. 数据库迁移
cd /var/www/myproject/myproject
sudo -u www-data /var/www/myproject/venv/bin/python manage.py migrate --noinput

# 8. 收集静态文件
sudo -u www-data /var/www/myproject/venv/bin/python manage.py collectstatic --noinput

# 9. 配置 Supervisor
sudo cp deploy/myproject.conf /etc/supervisor/conf.d/myproject.conf
sudo supervisorctl reread
sudo supervisorctl update

# 10. 配置 Nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/myproject
sudo ln -sf /etc/nginx/sites-available/myproject /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 11. 创建超级用户
sudo -u www-data /var/www/myproject/venv/bin/python manage.py createsuperuser

# 12. 启动服务
sudo supervisorctl start myproject:*
```

## 服务管理

### Supervisor 常用命令

```bash
# 查看所有服务状态
sudo supervisorctl status

# 启动所有服务
sudo supervisorctl start myproject:*

# 停止所有服务
sudo supervisorctl stop myproject:*

# 重启所有服务
sudo supervisorctl restart myproject:*

# 查看单个服务日志
sudo supervisorctl tail -f gunicorn
sudo supervisorctl tail -f celery-worker
sudo supervisorctl tail -f celery-beat-1
sudo supervisorctl tail -f celery-beat-2
sudo supervisorctl tail -f flower

# 重新加载配置
sudo supervisorctl reread
sudo supervisorctl update
```

### Celery 管理命令

```bash
# 查看正在执行的任务
cd /var/www/myproject
sudo -u www-data venv/bin/celery -A myproject inspect active

# 检查 worker 状态
sudo -u www-data venv/bin/celery -A myproject inspect ping

# 清空队列
sudo -u www-data venv/bin/celery -A myproject purge
```

### 查看日志

```bash
# Django 日志
sudo tail -f /var/log/myproject/django.log

# Gunicorn 日志
sudo tail -f /var/log/gunicorn/myproject.log

# Celery Worker 日志
sudo tail -f /var/log/celery/worker.log

# Celery Beat 日志
sudo tail -f /var/log/celery/beat1.log
sudo tail -f /var/log/celery/beat2.log

# Flower 日志
sudo tail -f /var/log/flower/flower.log

# 健康检查日志
sudo tail -f /var/log/health-monitor/monitor.log

# Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 监控面板

### Flower (Celery 监控)

访问地址: http://your-server-ip:5555 或 https://your-domain.com/flower/

功能：
- 实时查看任务执行状态
- Worker 状态监控
- 任务队列长度
- 任务执行时间统计

### Django Admin

访问地址: https://your-domain.com/admin/

功能：
- 订单管理
- 查看任务日志
- 管理用户

## 常见问题排查

### 1. 服务启动失败

```bash
# 查看详细错误日志
sudo supervisorctl tail -f <服务名> stderr

# 检查配置文件
sudo supervisorctl reread
sudo supervisorctl update
```

### 2. 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
sudo systemctl status postgresql

# 测试连接
sudo -u postgres psql -U postgres -d mvpdb -c "SELECT 1"

# 检查密码和主机配置
sudo cat /var/www/myproject/.env | grep POSTGRES
```

### 3. Redis 连接失败

```bash
# 检查 Redis 是否运行
sudo systemctl status redis

# 测试连接
redis-cli -p 6380 PING

# 检查端口配置
redis-cli -p 6380 INFO server | grep port
```

### 4. Worker 不执行任务

```bash
# 检查 worker 是否在线
sudo -u www-data /var/www/myproject/venv/bin/celery -A myproject inspect ping

# 检查队列配置
sudo -u www-data /var/www/myproject/venv/bin/celery -A myproject inspect active_queues

# 检查 Beat 主节点
redis-cli -p 6380 GET redbeat:master
```

### 5. 任务执行失败

```bash
# 查看任务日志
sudo tail -f /var/log/celery/worker.log | grep ERROR

# 检查 Django Admin 中的任务日志
# 访问 https://your-domain.com/admin/mvp/tasklog/

# 手动重试失败任务
# 在 Django Admin 中操作
```

## 安全建议

1. **使用 HTTPS**
   ```bash
   # 安装 Let's Encrypt 证书
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

2. **定期更新系统和依赖**
   ```bash
   sudo apt update && sudo apt upgrade
   cd /var/www/myproject
   sudo -u www-data venv/bin/pip install --upgrade pip
   sudo -u www-data venv/bin/pip install -r requirements.txt --upgrade
   ```

3. **定期备份数据库**
   ```bash
   # 创建备份脚本
   sudo nano /usr/local/bin/backup_db.sh
   # 添加内容:
   # pg_dump -U postgres mvpdb | gzip > /backup/mvpdb_$(date +%Y%m%d).sql.gz

   # 设置定时任务
   sudo crontab -e
   # 添加: 0 2 * * * /usr/local/bin/backup_db.sh
   ```

4. **配置防火墙**
   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw enable
   ```

5. **限制数据库和 Redis 远程访问**
   - PostgreSQL：只在 localhost 监听
   - Redis：配置密码或禁用远程访问

## 性能优化

### 调整 Worker 数量

编辑 `/etc/supervisor/conf.d/myproject.conf`：
```ini
[program:celery-worker]
numprocs=10  # 根据服务器配置调整
```

### 调整 Gunicorn Worker 数量

编辑 `/etc/supervisor/conf.d/myproject.conf`：
```ini
[program:gunicorn]
command=/var/www/myproject/venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 4 --threads 4 --timeout 120 myproject.wsgi:application
```

### 数据库连接池优化

编辑 `/var/www/myproject/myproject/settings.py`：
```python
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
            'MAX_CONNS': 20,
        },
    }
}
```

## 回滚操作

如果部署后出现问题，可以快速回滚：

```bash
# 1. 停止所有服务
sudo supervisorctl stop myproject:*

# 2. 恢复之前的代码版本
cd /var/www/myproject
sudo git checkout <previous-commit>

# 3. 恢复数据库备份
sudo -u postgres psql -d mvpdb < /backup/mvpdb_backup.sql

# 4. 重新部署
sudo bash deploy/deploy.sh

# 5. 重启服务
sudo supervisorctl start myproject:*
```

## 注意事项

1. **启动顺序**：先启动 Worker，再启动 Beat
2. **停止顺序**：先停止 Beat，再停止 Worker
3. **环境变量**：确保 `.env` 文件配置正确
4. **权限设置**：所有文件和日志目录必须属于 www-data 用户
5. **磁盘空间**：定期清理日志和归档文件，避免磁盘满
