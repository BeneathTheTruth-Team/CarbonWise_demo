# 碳智评 (CarbonWise) - Docker 一键部署

## 项目结构

```
carbonwise-demo/
├── docker-compose.yml          # Docker Compose 主配置
├── .env.example                # 环境变量模板
├── Dockerfile.api              # Flask API 服务构建文件
├── Dockerfile.engine           # C++ 计算引擎构建文件
├── requirements.txt            # Python 依赖
├── database_schema.sql         # 数据库初始化脚本
├── init-data.sql               # 示例数据
├── nginx.conf                  # Nginx 主配置
├── nginx/
│   └── proxy_params            # 代理参数配置
├── carbon_inversion_engine.cpp # C++ 反演引擎源码
├── carbon_visualization.py     # 数据可视化模块
├── dea_efficiency_engine.py    # DEA 效率评估模块
├── flask_backend_api.py        # Flask 后端 API
├── prometheus/
│   └── prometheus.yml          # 监控配置
├── grafana/
│   ├── dashboards/
│   │   └── dashboard.yml       # 仪表盘配置
│   └── datasources/
│       └── datasource.yml      # 数据源配置
└── README.md                   # 本文件
```

## 快速启动

### 1. 克隆/下载项目

```bash
cd carbonwise-demo
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，修改密码等敏感配置
```

### 3. 启动全部服务

```bash
docker-compose up -d
```

### 4. 查看服务状态

```bash
docker-compose ps
```

### 5. 查看日志

```bash
docker-compose logs -f api
```

## 服务端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| Nginx | 80/443 | 反向代理入口 |
| Flask API | 5000 | RESTful API 服务 |
| C++ Engine | 8080 | 高性能计算引擎 |
| MySQL | 3306 | 数据库 |
| Redis | 6379 | 缓存 |
| Prometheus | 9090 | 监控采集 |
| Grafana | 3000 | 监控可视化 |

## API 接口

### 健康检查
```bash
curl http://localhost/api/v1/health
```

### 用户注册
```bash
curl -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123","email":"test@example.com"}'
```

### 用户登录
```bash
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'
```

## 常用命令

```bash
# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 重建镜像
docker-compose up -d --build

# 进入容器
docker exec -it carbonwise-api bash

# 查看数据库
docker exec -it carbonwise-mysql mysql -ucarbonwise -p carbonwise_db
```

## 注意事项

1. **内存要求**：建议至少 4GB 内存，8GB 更佳
2. **Docker 版本**：需要 Docker 20.10+ 和 Docker Compose 2.0+
3. **首次启动**：MySQL 初始化可能需要 30-60 秒
4. **SSL 证书**：生产环境请替换 `nginx/ssl/` 目录下的证书文件

## 技术栈

- **后端**：Flask + Gunicorn + MySQL + Redis
- **计算引擎**：C++17 + OpenMP
- **可视化**：Plotly + Kaleido
- **分析**：NumPy + Pandas + SciPy
- **监控**：Prometheus + Grafana
- **代理**：Nginx

## 许可证

MIT License
