#!/bin/bash
# 部署脚本

set -e

echo "=========================================="
echo "AI可见度评估系统 - 部署脚本"
echo "=========================================="

# 部署目录
DEPLOY_DIR="/var/www/myproject"

# 创建必要的目录
echo "[1/8] 创建目录..."
sudo mkdir -p $DEPLOY_DIR
sudo mkdir -p /var/log/myproject
sudo mkdir -p /var/log/gunicorn
sudo mkdir -p /var/log/celery
sudo mkdir -p /var/log/flower
sudo mkdir -p /var/log/health-monitor
sudo mkdir -p /var/archive/tasks
sudo mkdir -p /var/www/myproject/scripts

# 复制项目文件
echo "[2/8] 复制项目文件..."
sudo cp -r myproject $DEPLOY_DIR/
sudo cp requirements.txt $DEPLOY_DIR/
sudo cp .env.production $DEPLOY_DIR/.env
sudo cp deploy/health_monitor.sh $DEPLOY_DIR/scripts/
sudo chmod +x $DEPLOY_DIR/scripts/health_monitor.sh

# 创建虚拟环境
echo "[3/8] 创建虚拟环境..."
cd $DEPLOY_DIR
if [ ! -d "venv" ]; then
    sudo python3 -m venv venv
fi

# 设置权限
echo "[4/8] 设置权限..."
sudo chown -R www-data:www-data $DEPLOY_DIR
sudo chown -R www-data:www-data /var/log/myproject
sudo chown -R www-data:www-data /var/log/gunicorn
sudo chown -R www-data:www-data /var/log/celery
sudo chown -R www-data:www-data /var/log/flower
sudo chown -R www-data:www-data /var/log/health-monitor
sudo chown -R www-data:www-data /var/archive/tasks
sudo chmod -R 755 $DEPLOY_DIR

# 安装依赖
echo "[5/8] 安装 Python 依赖..."
sudo -u www-data $DEPLOY_DIR/venv/bin/pip install --upgrade pip
sudo -u www-data $DEPLOY_DIR/venv/bin/pip install -r $DEPLOY_DIR/requirements.txt

# 安装 Playwright 浏览器
echo "[6/8] 安装 Playwright 浏览器..."
sudo -u www-data $DEPLOY_DIR/venv/bin/playwright install chromium

# 数据库迁移
echo "[7/8] 执行数据库迁移..."
cd $DEPLOY_DIR/myproject
sudo -u www-data $DEPLOY_DIR/venv/bin/python manage.py migrate --noinput

# 收集静态文件
echo "[7/8] 收集静态文件..."
sudo -u www-data $DEPLOY_DIR/venv/bin/python manage.py collectstatic --noinput

# 复制 Supervisor 配置
echo "[8/8] 配置 Supervisor..."
sudo cp deploy/myproject.conf /etc/supervisor/conf.d/myproject.conf
sudo supervisorctl reread
sudo supervisorctl update

# 配置 Nginx
echo "[8/8] 配置 Nginx..."
sudo cp deploy/nginx.conf /etc/nginx/sites-available/myproject
sudo ln -sf /etc/nginx/sites-available/myproject /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "接下来需要手动完成："
echo "1. 创建超级用户: cd $DEPLOY_DIR/myproject && sudo -u www-data ../venv/bin/python manage.py createsuperuser"
echo "2. 配置环境变量: 编辑 $DEPLOY_DIR/.env 文件"
echo "3. 启动服务: sudo supervisorctl start myproject:*"
echo "4. 检查状态: sudo supervisorctl status"
echo "5. 查看日志: sudo tail -f /var/log/myproject/django.log"
echo ""
