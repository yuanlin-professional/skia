# SkiaFlavorApi

> 源文件: infra/bots/recipe_modules/flavor/api.py

## 概述

`SkiaFlavorApi` 是 Skia 构建基础设施中用于抽象不同平台差异的核心 API 类。它提供了统一的接口来处理跨平台的代码执行、文件操作和设备管理,支持桌面、Android、iOS 和 Chromebook 等平台。通过工厂模式根据构建配置自动选择合适的 Flavor 实现,使得上层 recipe 代码无需关心平台细节。该模块还管理测试资源(SKP、图片、Lottie 动画等)的版本化和增量同步。

## 架构位置

`SkiaFlavorApi` 是 flavor 系统的中心枢纽:
- 作为 Recipe API 暴露给其他 recipe
- 持有具体 Flavor 实现的引用
- 协调资源管理和文件同步
- 与 `vars` 和 `run` 模块紧密协作

**架构层次:**
```
Recipe (test.py, perf.py, etc.)
    ↓
SkiaFlavorApi (api.py)
    ↓
具体 Flavor (DefaultFlavor, AndroidFlavor, iOSFlavor, etc.)
    ↓
设备/系统调用
```

## 主要类与结构体

### SkiaFlavorApi

继承自 `recipe_api.RecipeApi` 的核心 API 类。

**关键属性:**
- `_f`: 当前使用的 Flavor 实例
- `device_dirs`: 设备端目录结构
- `host_dirs`: 主机端目录结构
- `_skia_dir`: Skia 源码目录

**版本文件常量:**
```python
VERSION_FILE_LOTTIE = 'LOTTIE_VERSION'
VERSION_FILE_SK_IMAGE = 'SK_IMAGE_VERSION'
VERSION_FILE_SKP = 'SKP_VERSION'
VERSION_FILE_SVG = 'SVG_VERSION'
VERSION_FILE_TEXTTRACES = 'TEXTTRACES_VERSION'
VERSION_NONE = -1
```

### 平台检测函数

#### `is_android(vars_api)`
检查是否为 Android 平台。

**判断依据:**
- `extra_tokens` 中包含 'Android'
- 或 `builder_cfg['os']` 为 'Android'

#### `is_chromebook(vars_api)`
检查是否为 Chromebook 平台。

**判断依据:**
- `extra_tokens` 中包含 'Chromebook'
- 或 `builder_cfg['os']` 为 'ChromeOS'

#### `is_ios(vars_api)`
检查是否为 iOS 平台。

**判断依据:**
- `extra_tokens` 中包含 'iOS'
- 或 `builder_cfg['os']` 为 'iOS'

## 公共 API 函数

### 初始化与配置

#### `get_flavor(vars_api, app_name)`

工厂方法,根据平台返回相应的 Flavor 实例。

**参数:**
- `vars_api`: 构建器变量 API
- `app_name`: 应用名称(如 'dm', 'nanobench')

**返回:**
- `ChromebookFlavor`, `AndroidFlavor`, `iOSFlavor`, 或 `DefaultFlavor`

**选择逻辑:**
```python
if is_chromebook(vars_api):
    return chromebook.ChromebookFlavor(self, app_name)
if is_android(vars_api):
    return android.AndroidFlavor(self, app_name)
elif is_ios(vars_api):
    return ios.iOSFlavor(self, app_name)
else:
    return default.DefaultFlavor(self, app_name)
```

#### `setup(app_name)`

设置 Flavor 系统并初始化目录结构。

**功能:**
1. 调用 `get_flavor` 创建 Flavor 实例
2. 设置 `device_dirs` 和 `host_dirs`
3. 记录 Skia 源码目录

### 命令执行

#### `step(name, cmd, **kwargs)`

在设备上执行命令,委托给具体 Flavor 实现。

**参数:**
- `name`: 步骤名称
- `cmd`: 命令列表
- `**kwargs`: 额外参数

### 文件与目录操作

#### `device_path_join(*args)`

拼接设备端路径。

#### `copy_directory_contents_to_device(host_dir, device_dir)`

从主机复制目录内容到设备。

#### `copy_directory_contents_to_host(device_dir, host_dir)`

从设备复制目录内容到主机。

#### `copy_file_to_device(host_path, device_path)`

复制单个文件到设备。

#### `create_clean_host_dir(path)`

创建干净的主机目录。

#### `create_clean_device_dir(path)`

创建干净的设备目录。

#### `read_file_on_device(path, **kwargs)`

读取设备上文件的内容。

#### `remove_file_on_device(path)`

删除设备上的文件。

### 资源安装

#### `install(skps=False, images=False, lotties=False, svgs=False, resources=False, texttraces=False)`

安装测试资源到设备。

**参数:**
- `skps`: 是否安装 SKP 文件
- `images`: 是否安装测试图片
- `lotties`: 是否安装 Lottie 动画
- `svgs`: 是否安装 SVG 文件
- `resources`: 是否安装资源文件
- `texttraces`: 是否安装文本追踪文件

**执行流程:**
1. 调用 Flavor 的 `install()` 方法
2. 根据参数复制相应资源
3. 使用版本控制避免重复传输

#### `cleanup_steps()`

执行清理步骤,委托给 Flavor 实现。

## 内部实现细节

### 版本化资源管理

#### `_copy_dir(host_version, version_file, tmp_dir, host_path, device_path)`

智能复制目录,仅在版本不匹配时传输。

**工作原理:**
1. 读取设备上的版本文件
2. 比较主机和设备版本
3. 如果不同,删除旧内容并复制新内容
4. 更新设备上的版本文件

**优化效果:**
- 避免重复传输大量文件
- 加快测试启动速度
- 减少网络和存储开销

#### 资源复制方法

##### `_copy_images()`
复制测试图片。

**版本管理:**
- 从 `skimage` asset 读取版本
- 写入 `SK_IMAGE_VERSION` 文件
- 调用 `_copy_dir` 实现增量复制

##### `_copy_lotties()`
复制 Lottie 动画文件。

**版本管理:**
- 从 `lottie-samples` asset 读取版本
- 写入 `LOTTIE_VERSION` 文件

##### `_copy_skps()`
复制 SKP 文件。

**版本管理:**
- 从 `skp` asset 读取版本
- 写入 `SKP_VERSION` 文件

##### `_copy_svgs()`
复制 SVG 文件。

**版本管理:**
- 从 `svg` asset 读取版本
- 写入 `SVG_VERSION` 文件

##### `_copy_texttraces()`
复制文本 blob 追踪文件。

**版本管理:**
- 从 `text_blob_traces` asset 读取版本
- 写入 `TEXTTRACES_VERSION` 文件

### 版本比较逻辑

```python
device_version_file = self.device_path_join(
    self.device_dirs.tmp_dir, version_file)
if str(actual_version_file) != str(device_version_file):
    device_version = self.read_file_on_device(device_version_file, ...)
    if not device_version:
        device_version = VERSION_NONE
    if device_version != host_version:
        # 执行复制
```

**特殊处理:**
- 桌面平台:主机和设备路径相同,跳过版本检查
- 远程设备:比较版本号,仅在不匹配时复制

## 依赖关系

**直接依赖:**
- Flavor 实现类(default, android, ios, chromebook)
- `vars`: 获取构建器配置
- `run`: 执行命令和 asset 管理
- `path`: 路径处理

**被依赖:**
- `recipes/test.py`: DM 测试
- `recipes/perf.py`: 性能基准测试
- `recipes/compile.py`: 编译流程

## 设计模式与设计决策

### 工厂模式

`get_flavor()` 方法实现工厂模式:
- **优点:** 集中创建逻辑
- **优点:** 易于添加新平台
- **优点:** 客户端代码平台无关

### 委托模式

API 方法委托给具体 Flavor:
```python
def step(self, name, cmd, **kwargs):
    return self._f.step(name, cmd, **kwargs)
```

**优点:**
- 保持接口一致性
- 实现灵活性
- 降低耦合度

### 版本控制策略

使用版本文件控制资源同步:
- **效率:** 避免重复传输
- **可靠性:** 确保版本一致
- **灵活性:** 支持增量更新

### 惰性资源加载

仅在需要时复制资源:
```python
install(skps=True, images=False, ...)
```

**优点:**
- 减少不必要的传输
- 加快任务启动
- 节省存储空间

## 性能考量

### 资源传输优化

**版本检查开销:**
- 读取版本文件: 毫秒级
- 字符串比较: 微秒级
- 跳过传输节省: 秒到分钟级

**传输量:**
- SKP 文件: 数百 MB
- 图片: 数十 MB
- Lottie: 数 MB

**优化效果:**
- 首次传输: 完整复制
- 后续运行: 仅在版本变化时传输
- 典型节省: 80-90% 的传输时间

### 平台检测开销

**检测成本:**
- 字符串比较: O(1)
- 字典查找: O(1)
- 总开销: 微秒级

**优化:**
- 仅在 `setup()` 时检测一次
- 后续使用缓存的 Flavor 实例

### 目录操作开销

**批量文件操作:**
- 使用目录级操作而非逐文件
- 减少 RPC 调用(远程设备)
- 利用设备端脚本批处理

## 相关文件

**Flavor 实现:**
- `default.py`: 桌面平台
- `android.py`: Android 平台
- `ios.py`: iOS 平台
- `chromebook.py`: Chromebook 平台
- `ssh.py`: SSH 基类

**依赖模块:**
- `vars/api.py`: 构建器变量
- `run/api.py`: 命令执行
- `recipe_engine/path.py`: 路径处理

**使用示例:**
- `examples/full.py`: 完整功能示例
- `recipes/test.py`: DM 测试 recipe
- `recipes/perf.py`: 性能测试 recipe
