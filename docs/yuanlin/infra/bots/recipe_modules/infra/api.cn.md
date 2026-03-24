# Infra Recipe Module API

> 源文件: `infra/bots/recipe_modules/infra/api.py`

## 概述

`api.py` 实现了 `InfraApi` 配方模块，提供 Go 语言开发环境的配置。核心功能是解析符号链接以获取真实的 GOROOT 路径，并组合 Go 工具链所需的环境变量。

## 架构位置

位于 `infra/bots/recipe_modules/infra/` 目录，被需要 Go 环境的配方任务使用。

## 主要类与结构体

- **`InfraApi`** (recipe_api.RecipeApi): 基础设施 API

## 公共 API 函数

- **`goroot`** (属性): 返回 Go 安装根路径（解析符号链接后的真实路径）
- **`go_bin`** (属性): 返回 Go 二进制文件路径
- **`go_env`** (属性): 返回 Go 环境变量字典 (GOCACHE, GOPATH, GOROOT, PATH)
- **`gopath`** (属性): 返回 GOPATH 路径

## 内部实现细节

1. **GOROOT 符号链接解析**: Go 1.18+ 的 `//go:embed` 不支持符号链接，因此使用 `realpath` 命令获取真实路径
2. **go_env** 组合: GOCACHE=cache/go_cache, GOPATH=cache/gopath, GOROOT=解析后路径, PATH 包含 go/bin 和 gopath/bin
3. 测试兼容性: 当 workdir 未设置时回退到原始 GOROOT

## 依赖关系

- `recipe_engine/path`, `recipe_engine/raw_io`, `recipe_engine/step`
- `vars`: 获取 workdir 和 cache_dir

## 设计模式与设计决策

- 符号链接解析解决了 Go 1.18+ 的 embed 兼容性问题
- 属性模式提供惰性求值的环境配置

## 性能考量

- GOROOT 通过 `realpath` 系统调用获取，每次属性访问执行两个步骤
- go_env 适合在 `with api.context(env=...)` 中使用

## 相关文件

- `infra/bots/recipe_modules/infra/__init__.py`: 模块初始化
- `infra/bots/recipe_modules/infra/examples/full.py`: 测试示例
