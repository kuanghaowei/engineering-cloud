#!/bin/bash

###############################################################################
# AEC 协同平台开发环境一键安装脚本
# 适用于: PVE LXC Ubuntu 24.04
# 功能: 安装并配置 Python、PostgreSQL、Redis、MinIO、Celery 等开发环境
###############################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        log_error "请使用 root 权限运行此脚本: sudo bash setup.sh"
        exit 1
    fi
}

# 更新系统
update_system() {
    log_info "更新系统软件包..."
    apt update && apt upgrade -y
    apt install -y curl wget git vim build-essential software-properties-common
}

# 安装 Python 3.12
install_python() {
    log_info "安装 Python 3.12 及开发工具..."
    apt install -y python3.12 python3.12-dev python3.12-venv python3-pip
    
    # 设置 python3 默认版本
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
    
    # 升级 pip
    python3 -m pip install --upgrade pip setuptools wheel
    
    log_info "Python 版本: $(python3 --version)"
}

# 安装 PostgreSQL 16
install_postgresql() {
    log_info "安装 PostgreSQL 16..."
    
    # 添加 PostgreSQL 官方仓库
    sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
    
    apt update
    apt install -y postgresql-16 postgresql-contrib-16 libpq-dev
    
    # 启动并设置开机自启
    systemctl enable postgresql
    systemctl start postgresql
    
    # 创建开发数据库和用户
    sudo -u postgres psql -c "CREATE USER aec_dev WITH PASSWORD 'aec_dev_password';"
    sudo -u postgres psql -c "CREATE DATABASE aec_platform OWNER aec_dev;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE aec_platform TO aec_dev;"
    
    log_info "PostgreSQL 安装完成"
    log_warn "数据库: aec_platform, 用户: aec_dev, 密码: aec_dev_password"
}

# 安装 Redis
install_redis() {
    log_info "安装 Redis..."
    apt install -y redis-server
    
    # 配置 Redis
    sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf
    
    systemctl enable redis-server
    systemctl restart redis-server
    
    log_info "Redis 安装完成"
}

# 安装 MinIO
install_minio() {
    log_info "安装 MinIO 对象存储..."
    
    # 下载 MinIO
    wget https://dl.min.io/server/minio/release/linux-amd64/minio -O /usr/local/bin/minio
    chmod +x /usr/local/bin/minio
    
    # 创建 MinIO 用户和数据目录
    useradd -r minio-user -s /sbin/nologin || true
    mkdir -p /data/minio
    chown minio-user:minio-user /data/minio
    
    # 创建 systemd 服务
    cat > /etc/systemd/system/minio.service <<EOF
[Unit]
Description=MinIO Object Storage
After=network.target

[Service]
Type=notify
User=minio-user
Group=minio-user
Environment="MINIO_ROOT_USER=minioadmin"
Environment="MINIO_ROOT_PASSWORD=minioadmin123"
ExecStart=/usr/local/bin/minio server /data/minio --console-address ":9001"
Restart=always
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable minio
    systemctl start minio
    
    log_info "MinIO 安装完成"
    log_warn "MinIO API: http://localhost:9000, Console: http://localhost:9001"
    log_warn "用户名: minioadmin, 密码: minioadmin123"
}

# 安装 Node.js (用于前端开发)
install_nodejs() {
    log_info "安装 Node.js 20 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs
    
    # 安装 pnpm
    npm install -g pnpm
    
    log_info "Node.js 版本: $(node --version)"
    log_info "npm 版本: $(npm --version)"
}

# 安装 CAD/BIM 转换工具依赖
install_cad_dependencies() {
    log_info "安装 CAD/BIM 转换工具依赖..."
    
    # 安装图形库和字体
    apt install -y \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        fonts-wqy-microhei \
        fonts-wqy-zenhei
    
    log_info "CAD/BIM 依赖安装完成"
}

# 创建项目虚拟环境
setup_python_env() {
    log_info "创建 Python 虚拟环境..."
    
    PROJECT_DIR="/opt/aec-platform"
    mkdir -p $PROJECT_DIR
    cd $PROJECT_DIR
    
    python3 -m venv venv
    source venv/bin/activate
    
    # 安装常用开发包
    pip install \
        fastapi \
        uvicorn[standard] \
        sqlalchemy \
        alembic \
        psycopg2-binary \
        redis \
        celery \
        minio \
        python-multipart \
        pydantic \
        pydantic-settings \
        python-jose[cryptography] \
        passlib[bcrypt] \
        pytest \
        pytest-asyncio \
        httpx
    
    log_info "Python 虚拟环境创建完成: $PROJECT_DIR/venv"
}

# 创建开发配置文件
create_dev_config() {
    log_info "创建开发配置文件..."
    
    cat > /opt/aec-platform/.env.dev <<EOF
# 数据库配置
DATABASE_URL=postgresql://aec_dev:aec_dev_password@localhost:5432/aec_platform

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# MinIO 配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=aec-files
MINIO_SECURE=false

# Celery 配置
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# 应用配置
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=true
ALLOWED_HOSTS=*

# 文件上传配置
MAX_UPLOAD_SIZE=10737418240  # 10GB
CHUNK_SIZE=5242880  # 5MB
EOF
    
    log_info "配置文件已创建: /opt/aec-platform/.env.dev"
}

# 创建快捷启动脚本
create_helper_scripts() {
    log_info "创建辅助脚本..."
    
    # 启动开发服务器脚本
    cat > /opt/aec-platform/start-dev.sh <<'EOF'
#!/bin/bash
cd /opt/aec-platform
source venv/bin/activate
source .env.dev
uvicorn main:app --reload --host 0.0.0.0 --port 8000
EOF
    
    # 启动 Celery Worker 脚本
    cat > /opt/aec-platform/start-celery.sh <<'EOF'
#!/bin/bash
cd /opt/aec-platform
source venv/bin/activate
source .env.dev
celery -A tasks worker --loglevel=info
EOF
    
    # 数据库迁移脚本
    cat > /opt/aec-platform/migrate.sh <<'EOF'
#!/bin/bash
cd /opt/aec-platform
source venv/bin/activate
source .env.dev
alembic upgrade head
EOF
    
    chmod +x /opt/aec-platform/*.sh
    
    log_info "辅助脚本已创建"
}

# 显示安装总结
show_summary() {
    log_info "=========================================="
    log_info "开发环境安装完成！"
    log_info "=========================================="
    echo ""
    log_info "已安装组件:"
    echo "  - Python 3.12 + 虚拟环境"
    echo "  - PostgreSQL 16 (端口: 5432)"
    echo "  - Redis (端口: 6379)"
    echo "  - MinIO (API: 9000, Console: 9001)"
    echo "  - Node.js 20 + pnpm"
    echo ""
    log_info "项目目录: /opt/aec-platform"
    echo ""
    log_info "数据库信息:"
    echo "  数据库: aec_platform"
    echo "  用户名: aec_dev"
    echo "  密码: aec_dev_password"
    echo ""
    log_info "MinIO 信息:"
    echo "  访问地址: http://$(hostname -I | awk '{print $1}'):9001"
    echo "  用户名: minioadmin"
    echo "  密码: minioadmin123"
    echo ""
    log_info "快捷命令:"
    echo "  启动开发服务器: /opt/aec-platform/start-dev.sh"
    echo "  启动 Celery Worker: /opt/aec-platform/start-celery.sh"
    echo "  数据库迁移: /opt/aec-platform/migrate.sh"
    echo ""
    log_warn "请将项目代码放置到 /opt/aec-platform 目录"
    log_warn "激活虚拟环境: source /opt/aec-platform/venv/bin/activate"
}

# 主函数
main() {
    log_info "开始安装 AEC 协同平台开发环境..."
    
    check_root
    update_system
    install_python
    install_postgresql
    install_redis
    install_minio
    install_nodejs
    install_cad_dependencies
    setup_python_env
    create_dev_config
    create_helper_scripts
    show_summary
    
    log_info "安装完成！"
}

# 执行主函数
main
