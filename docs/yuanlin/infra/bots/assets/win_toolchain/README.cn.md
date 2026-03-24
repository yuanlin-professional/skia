# win_toolchain - Windows 工具链

## 概述

Windows SDK 和 Visual Studio 构建工具链资源，包含 Windows 编译所需的头文件、库和工具。

## 目录结构

```
win_toolchain/
├── __init__.py              # Python 包标识
├── create.py                # 自动化创建脚本
├── create_and_upload.py     # 创建并上传便捷脚本
└── VERSION                  # 当前版本号
```

## 依赖关系

- 被 Windows 编译任务使用
- 与 `clang_win` 编译器配合使用

## 相关文档与参考

- [Windows SDK 文档](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/)
