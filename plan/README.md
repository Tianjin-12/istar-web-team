istar-website-test-v0.1

Introduction for cooperation hi! I am Tianjin, the guy you have known, I am here to introduce the git, the standard and modern framework for coding cooperation. 
Pick up this tool would let us work as a close and professional team. On this project, we would use git and docker to convey the correction and the code we build. 
The only thing Git can convey is JUST pure text such as code! You can't test it immediately. It can't transfer the software and background set so you have to install them by yourself then anyway.
If you want to test in your own computer, we need docker, you need to sign in the DockerHub and I would transfer the whole subject to you. Be aware of the requirement! 
Check out the README text when you get a subject and if you make any correction, remember to record in the README text. 
By the way, remember that if you make your own correction, you need to submit it to Github or Dockerhub and remind us in our WeChat group.

Version record 
v0.1 2026.1.13 "the beginning"
v0.2 2026.1.19 "base,and it is more stable"

默认docker compose up 时，立刻定时beat 和worker都会启动
注意！！！！：每次都必须先开worker再开beat，先关beat再关worker,不然消息队列会爆炸！！！！
windows
手动控制方式
1. Docker 环境下
# 启动所有服务（包括 celery-beat）
docker-compose up -d
# 只启动 celery-beat 服务
docker-compose up -d celery-beat
# 停止 celery-beat
docker-compose stop celery-beat
# 重启 celery-beat
docker-compose restart celery-beat
# 完全移除容器（停止）
docker-compose down
# 启动所有服务但排除 celery-beat
docker-compose up -d web celery db redis
2. 本地开发环境
# 启动 celery beat
celery -A myproject beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
# 启动 celery worker
celery -A myproject worker -l info
# 停止所有 celery 进程
pkill -f celery