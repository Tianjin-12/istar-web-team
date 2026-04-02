# 数据库备份指南

## 备份重要性

定期备份是确保数据安全的关键措施。建议至少每天备份一次数据库，并在重大操作前手动备份。

## 备份方法

### 方法1：使用pg_dump命令行工具（推荐）

#### 备份单个数据库

```bash
# 备份到压缩文件
pg_dump -U postgres -d mvpdb -h localhost -p 5432 | gzip > mvpdb_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# 备份到普通SQL文件
pg_dump -U postgres -d mvpdb -h localhost -p 5432 > mvpdb_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 参数说明
- `-U postgres`: 指定数据库用户（根据实际配置修改）
- `-d mvpdb`: 指定数据库名称
- `-h localhost`: 数据库主机地址
- `-p 5432`: 数据库端口
- `| gzip`: 压缩备份文件
- `> filename`: 输出到文件

### 方法2：使用Django管理命令

```bash
# 进入项目目录
cd /var/www/myproject/myproject

# 使用Django的dumpdata命令（备份数据为JSON格式）
sudo -u www-data ../venv/bin/python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json

# 只备份特定应用的数据
sudo -u www-data ../venv/bin/python manage.py dumpdata accounts mvp > partial_backup.json
```

### 方法3：使用自动化脚本

创建备份脚本 `/usr/local/bin/backup_db.sh`：

```bash
#!/bin/bash

# 备份配置
BACKUP_DIR="/backup"
DB_NAME="mvpdb"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"
RETENTION_DAYS=7

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份文件名
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql.gz"

# 执行备份
pg_dump -U $DB_USER -d $DB_NAME -h $DB_HOST -p $DB_PORT | gzip > $BACKUP_FILE

# 检查备份是否成功
if [ $? -eq 0 ]; then
    echo "备份成功: $BACKUP_FILE"
else
    echo "备份失败!"
    exit 1
fi

# 清理旧备份（保留7天）
find $BACKUP_DIR -name "${DB_NAME}_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "备份完成，保留了最近 $RETENTION_DAYS 天的备份"
```

设置脚本权限：
```bash
sudo chmod +x /usr/local/bin/backup_db.sh
```

## 自动化备份

### 使用Cron定时任务

```bash
# 编辑crontab
sudo crontab -e

# 添加定时任务（每天凌晨2点备份）
0 2 * * * /usr/local/bin/backup_db.sh >> /var/log/db_backup.log 2>&1
```

### 使用Supervisor（推荐）

创建Supervisor配置 `/etc/supervisor/conf.d/db-backup.conf`：

```ini
[program:db-backup]
command=/usr/local/bin/backup_db.sh
user=postgres
autostart=true
autorestart=true
startsecs=0
startretries=0
stdout_logfile=/var/log/db-backup.log
stderr_logfile=/var/log/db-backup-err.log
```

然后在crontab中只每天执行一次：
```bash
# 编辑crontab
sudo crontab -e

# 每天凌晨2点重启备份任务
0 2 * * * sudo supervisorctl restart db-backup
```

## 恢复数据库

### 从SQL文件恢复

```bash
# 从压缩文件恢复
gunzip < mvpdb_backup_20240101_020000.sql.gz | psql -U postgres -d mvpdb -h localhost -p 5432

# 从普通SQL文件恢复
psql -U postgres -d mvpdb -h localhost -p 5432 < mvpdb_backup_20240101_020000.sql
```

### 从JSON文件恢复（Django）

```bash
# 进入项目目录
cd /var/www/myproject/myproject

# 加载数据
sudo -u www-data ../venv/bin/python manage.py loaddata backup.json
```

### 注意事项

1. **恢复前备份现有数据**：在恢复之前，先备份当前数据库，以防恢复失败
2. **清空现有数据**：如果要完全恢复，需要先清空现有数据
   ```bash
   # 删除所有表和数据（谨慎使用！）
   sudo -u postgres psql -d mvpdb -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
   sudo -u postgres psql -d mvpdb -c "GRANT ALL ON SCHEMA public TO postgres;"
   ```
3. **检查迁移**：恢复后运行迁移
   ```bash
   sudo -u www-data ../venv/bin/python manage.py migrate
   ```

## 备份验证

定期验证备份文件的完整性：

```bash
# 检查压缩文件是否完整
gzip -t mvpdb_backup_20240101_020000.sql.gz

# 测试恢复到临时数据库
createdb test_restore
gunzip < mvpdb_backup_20240101_020000.sql.gz | psql -d test_restore
# 检查数据
psql -d test_restore -c "SELECT COUNT(*) FROM mvp_order;"
# 删除测试数据库
dropdb test_restore
```

## 备份存储

### 本地存储

```bash
# 创建备份目录
sudo mkdir -p /backup
sudo chown postgres:postgres /backup
```

### 远程存储（推荐）

使用rsync同步到远程服务器：

```bash
# 同步备份文件到远程服务器
rsync -avz /backup/ user@remote-server:/remote-backup/mvp/
```

### 云存储

使用云存储服务（如AWS S3、阿里云OSS、腾讯云COS）：

```bash
# 安装AWS CLI
pip install awscli

# 配置AWS CLI
aws configure

# 上传备份文件到S3
aws s3 cp /backup/mvpdb_backup_20240101.sql.gz s3://my-backup-bucket/mvpdb/
```

## 监控和告警

### 检查备份日志

```bash
# 查看备份日志
tail -f /var/log/db_backup.log
```

### 设置备份失败告警

在备份脚本中添加告警逻辑：

```bash
# 在backup_db.sh中添加
if [ $? -ne 0 ]; then
    # 发送邮件告警
    echo "数据库备份失败!" | mail -s "备份失败告警" admin@example.com
fi
```

## 最佳实践

1. **定期备份**：建议每天至少备份一次
2. **多地存储**：保留多个备份副本，包括本地和远程
3. **定期测试**：定期测试备份恢复流程，确保备份可用
4. **保留策略**：根据业务需求制定保留策略（如保留7天、30天）
5. **加密备份**：对敏感数据备份进行加密
6. **文档化**：记录备份和恢复流程，确保团队成员都能操作

## 紧急情况处理

### 数据库损坏

```bash
# 1. 停止应用服务
sudo supervisorctl stop myproject:*

# 2. 备份损坏的数据库
pg_dump -U postgres -d mvpdb > damaged_backup.sql

# 3. 恢复最近的备份
gunzip < /backup/mvpdb_backup_20240101_020000.sql.gz | psql -U postgres -d mvpdb

# 4. 运行迁移
cd /var/www/myproject/myproject
sudo -u www-data ../venv/bin/python manage.py migrate

# 5. 收集静态文件
sudo -u www-data ../venv/bin/python manage.py collectstatic --noinput

# 6. 重启服务
sudo supervisorctl start myproject:*
```

### 完全恢复

```bash
# 1. 重新创建数据库
sudo -u postgres psql -c "DROP DATABASE mvpdb;"
sudo -u postgres psql -c "CREATE DATABASE mvpdb;"

# 2. 恢复备份
gunzip < /backup/mvpdb_backup_20240101_020000.sql.gz | psql -U postgres -d mvpdb

# 3. 运行迁移
cd /var/www/myproject/myproject
sudo -u www-data ../venv/bin/python manage.py migrate

# 4. 创建超级用户（如果需要）
sudo -u www-data ../venv/bin/python manage.py createsuperuser
```

## 联系方式

如有问题，请联系系统管理员。
