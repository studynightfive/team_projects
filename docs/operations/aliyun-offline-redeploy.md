# 阿里云 ECS 离线重部署清单

本文用于将智能知识库平台以离线镜像方式部署到一台全新的 Linux 云主机，不迁移旧数据库和测试数据。

## 1. 本地交付文件

本次离线目录：

```text
D:\projects\team_work\artifacts\kb-offline-v0.1.0-54b982e-20260731
```

应包含：

```text
kb-images-v0.1.0-54b982e.tar
kb-source-v0.1.0-54b982e.tar.gz
bootstrap_admin.py
docker-compose.cloud.yml
SHA256SUMS
```

`kb-images` 包含 Web、API、Worker、PostgreSQL/pgvector 和 Redis 五个镜像。源码包由 Git 归档生成，不包含 `deploy/env/.env`。

## 2. 新服务器预检

```bash
whoami
cat /etc/os-release
uname -m
free -h
df -hT /
docker --version
docker compose version
systemctl is-active docker
```

要求使用 `x86_64` Linux，Docker 服务为 `active`，Docker Compose 不低于项目基线 `2.32.4`，磁盘建议至少保留 10 GiB。

## 3. 上传离线目录

先在服务器创建接收目录：

```bash
mkdir -p /home/kb-upload
chmod 700 /home/kb-upload
```

在本地 Windows PowerShell 执行，将 `<新服务器公网IP>` 替换为实际地址：

```powershell
scp -r "D:\projects\team_work\artifacts\kb-offline-v0.1.0-54b982e-20260731" `
  root@<新服务器公网IP>:/home/kb-upload/
```

首次连接必须先在已可信的 SSH 会话中核对服务器 ED25519 指纹，再接受 `scp` 的主机确认。

## 4. 校验并安装文件

回到服务器：

```bash
cd /home/kb-upload/kb-offline-v0.1.0-54b982e-20260731
sha256sum -c SHA256SUMS
```

五项均应显示 `OK`。然后安装源码及云端覆盖文件：

```bash
mkdir -p /home/knowledge-base
tar -xzf kb-source-v0.1.0-54b982e.tar.gz -C /home/knowledge-base

install -m 0644 bootstrap_admin.py \
  /home/knowledge-base/backend/scripts/bootstrap_admin.py
install -m 0644 docker-compose.cloud.yml \
  /home/knowledge-base/deploy/docker-compose.cloud.yml
```

导入离线镜像：

```bash
docker image load -i kb-images-v0.1.0-54b982e.tar

docker image ls | grep -E \
  'knowledge-base-platform|pgvector/pgvector|redis'
```

## 5. 配置环境变量

```bash
cd /home/knowledge-base
cp deploy/env/.env.example deploy/env/.env
chmod 600 deploy/env/.env
nano deploy/env/.env
```

至少确认以下配置：

```dotenv
POSTGRES_PASSWORD=<独立随机数据库密码>
SECRET_KEY=<不少于32位的独立随机密钥>
MODEL_KEY_FERNET_KEY=<Fernet格式独立密钥>
EXPORT_DOWNLOAD_SIGNING_KEY=<独立随机签名密钥>

APP_ENVIRONMENT=development
AUTO_SEED_DEMO_DATA=false
COOKIE_SECURE=false
DEBUG=false
APP_IMAGE_TAG=v0.1.0-54b982e

DEEPSEEK_API_KEY=<聊天模型API Key>
DASHSCOPE_API_KEY=<Embedding和Rerank API Key>

NATIVE_CORE_REQUIRED=true
NATIVE_CORE_LICENSE_REQUIRED=false
```

当前离线镜像没有注入正式许可证公钥，因此客户测试阶段使用上述开发环境与禁用许可证校验配置；正式生产前必须重新构建带许可证公钥的镜像并启用生产校验。不要启用演示数据播种。云端覆盖文件沿用已验证的宿主机端口 `18080`，无需修改基础编排文件。

## 6. 启动与健康检查

```bash
cd /home/knowledge-base

docker compose --env-file deploy/env/.env \
  -f deploy/docker-compose.yml \
  -f deploy/docker-compose.cloud.yml \
  config --quiet

docker compose --env-file deploy/env/.env \
  -f deploy/docker-compose.yml \
  -f deploy/docker-compose.cloud.yml \
  up -d --no-build --pull never

sleep 60

docker compose --env-file deploy/env/.env \
  -f deploy/docker-compose.yml \
  -f deploy/docker-compose.cloud.yml \
  ps -a
```

`web`、`api-server`、`worker`、`postgres` 和 `redis` 应为 `healthy`；`migrate` 显示 `Exited (0)` 表示迁移成功。

```bash
curl -i http://127.0.0.1:18080/api/v1/health/live
curl -i http://127.0.0.1:18080/api/v1/health/ready
```

两个接口均应返回 HTTP 200。

## 7. 创建首管理员

镜像内仍是原始脚本，因此把已修复脚本临时复制到运行容器：

```bash
cd /home/knowledge-base
docker cp backend/scripts/bootstrap_admin.py \
  kb-api-server:/tmp/bootstrap_admin.py

docker compose --env-file deploy/env/.env \
  -f deploy/docker-compose.yml \
  -f deploy/docker-compose.cloud.yml \
  exec api-server \
  /app/backend/.venv/bin/python /tmp/bootstrap_admin.py
```

管理员口令必须为 12–128 位，输入不回显。成功后清理临时文件：

```bash
docker exec -u 0 kb-api-server rm -f /tmp/bootstrap_admin.py
```

## 8. 开放测试入口

在 ECS 关联安全组中增加入方向规则：

```text
协议：TCP
端口：18080/18080
来源：测试人员公网IP/32
策略：允许
```

不要开放宿主机的 PostgreSQL `5432`、Redis `6379` 或 API 内部端口 `8000`。浏览器访问：

```text
http://<新服务器公网IP>:18080
```

## 9. 最终冒烟测试

依次验证管理员登录、模型配置、创建部门和用户、创建知识库、批量上传文档、文档处理完成、单库与多库 RAG 问答、引用来源、答案导出、删除与回收站恢复。

所有后续 Compose 命令都必须同时加载基础文件和 `deploy/docker-compose.cloud.yml`，否则 `18080` 端口、离线 pgvector 镜像和 Worker 健康检查覆盖会失效。
