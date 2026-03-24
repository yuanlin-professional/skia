# create_and_upload.py

> 源文件: infra/bots/assets/chromebook_arm64_gles/create_and_upload.py

## 概述

`create_and_upload.py` 为 Chromebook ARM64（64位 ARM）GLES 资产的创建和上传入口脚本。ARM64 是 ARMv8 架构，相比 ARMv7（32位 ARM）提供更好的性能和更大的地址空间。

## 架构位置

```
infra/bots/assets/chromebook_arm64_gles/
├── create_and_upload.py          # 本文件：上传入口
├── create.py                     # 资产创建逻辑
└── __init__.py                   # 包标识
```

## 公共 API 函数

### main()
执行以下操作：
1. 平台检查（仅 Linux）
2. 解析 `--lib_path` 参数
3. 设置环境变量 `CHROMEBOOK_ARM64_GLES_LIB_PATH`
4. 定位并调用 `sk asset upload chromebook_arm64_gles`

## 内部实现细节

### 环境变量传递
```python
os.environ[create.ENV_VAR] = args.lib_path
```
将库路径通过环境变量传递给 `create.py`，因为 `sk` 工具作为中间层无法直接传递自定义参数。

### sk 工具定位
```python
sk = os.path.realpath(os.path.join(
    FILE_DIR, os.pardir, os.pardir, os.pardir, os.pardir, 'bin', 'sk'))
```
通过相对路径导航：`assets/chromebook_arm64_gles/ -> infra/ -> skia/ -> bin/sk`

### 平台限制
只允许在 Linux 运行，因为 `create.py` 需要使用 `apt-get` 安装依赖包。

## 依赖关系

- **sk 工具**: CIPD 资产管理工具
- **create.py**: 同目录的资产创建模块
- **Linux 系统**: 必需（apt-get 包管理）

## 设计模式与设计决策

### 与其他 Chromebook 版本的对比

| 版本 | 架构 | 特有库 | 复杂度 |
|------|------|--------|--------|
| chromebook_arm_gles | ARMv7 32位 | libmali | 中等 |
| chromebook_arm64_gles | ARMv8 64位 | libmali + apitrace | 高 |
| chromebook_x86_64_gles | x86_64 | libdrm | 中等 |

ARM64 版本的特殊性：
- 更复杂的库路径结构（`/usr/lib64`, `/usr/local/lib64`）
- 包含 apitrace 包装器（用于 OpenGL 调试）
- 需要创建符号链接

## 性能考量

- **执行时间**: 2-5 分钟
- **网络上传**: 资产大小约 20-30 MB

## 相关文件

- **`create.py`**: ARM64 资产创建实现（更复杂的库收集逻辑）
- **`chromebook_arm_gles/`**: 32位 ARM 版本
- **`chromebook_x86_64_gles/`**: x86_64 版本
- **`bin/sk`**: Skia 资产管理工具
