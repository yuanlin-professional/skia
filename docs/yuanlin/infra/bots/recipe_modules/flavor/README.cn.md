# flavor - 平台特定行为抽象模块

## 概述

`flavor` 模块提供了平台无关的高级命令抽象层，允许调用者指定要执行的操作（如安装、运行测试、复制结果等），而将平台特定的实现细节交给具体的 flavor 子模块处理。这是 Skia 跨平台 CI 支持的关键模块。

## 目录结构

```
flavor/
├── __init__.py    # DEPS 依赖声明
├── api.py         # FlavorApi 核心类
├── android.py     # Android 平台实现
├── chromebook.py  # Chromebook 平台实现
├── default.py     # 默认桌面平台实现
├── ios.py         # iOS 平台实现
├── ssh.py         # SSH 远程执行实现
├── examples/      # 使用示例和测试
└── resources/     # 辅助资源脚本
```

## 关键文件

### api.py
定义通用接口，包括：
- 设备设置和清理
- 安装构建产物到目标设备
- 运行测试/基准测试
- 复制结果文件

### android.py / ios.py / chromebook.py / default.py
分别为 Android、iOS、Chromebook 和桌面平台提供具体的命令实现。

### ssh.py
通过 SSH 协议在远程设备上执行命令，用于 Chromebook 等远程目标。

## 依赖关系

DEPS: 依赖 `recipe_engine` 和其他 Skia Recipe 模块。

## 相关文档与参考

- `infra/bots/README.recipes.md` 中 `flavor` 模块的 API 文档
