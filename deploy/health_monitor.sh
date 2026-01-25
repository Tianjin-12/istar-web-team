#!/bin/bash
# 健康检查脚本
# 每30秒检查一次系统状态

VENV_PATH="/var/www/myproject/venv"
CELERY_CMD="$VENV_PATH/bin/celery -A myproject"
LOG_DIR="/var/log/health-monitor"

mkdir -p $LOG_DIR

while true; do
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

  # 检查 Celery Worker 状态
  if ! $CELERY_CMD inspect ping &> /dev/null; then
    echo "[$TIMESTAMP] [ALERT] Celery Worker is not responding!" >> $LOG_DIR/monitor.log
  fi

  # 检查 Beat 主节点
  MASTER=$(redis-cli -p 6380 GET redbeat:master 2>/dev/null)
  if [ -z "$MASTER" ]; then
    echo "[$TIMESTAMP] [ALERT] No active Beat master found!" >> $LOG_DIR/monitor.log
  else
    echo "[$TIMESTAMP] [INFO] Beat master: $MASTER" >> $LOG_DIR/monitor.log
  fi

  # 检查 Redis 状态
  if ! redis-cli -p 6380 PING &> /dev/null; then
    echo "[$TIMESTAMP] [ALERT] Redis is not responding!" >> $LOG_DIR/monitor.log
  fi

  # 检查 PostgreSQL 状态
  if ! sudo -u postgres psql -c "SELECT 1" &> /dev/null; then
    echo "[$TIMESTAMP] [ALERT] PostgreSQL is not responding!" >> $LOG_DIR/monitor.log
  fi

  # 检查 Supervisor 状态
  if ! supervisorctl status celery-worker &> /dev/null; then
    echo "[$TIMESTAMP] [ALERT] Celery Worker not running under Supervisor!" >> $LOG_DIR/monitor.log
    supervisorctl start celery-worker:* &>> $LOG_DIR/monitor.log
  fi

  sleep 30
done
