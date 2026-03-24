# iOSFlavor

> 源文件: infra/bots/recipe_modules/flavor/ios.py

## 概述

`iOSFlavor` 是 Skia 构建基础设施中用于在 iOS 设备上运行测试和性能基准测试的专用适配器类。它继承自 `DefaultFlavor`,实现了与 iOS 设备交互的特定逻辑,包括设备配对、开发者镜像挂载、应用安装、文件传输等功能。该模块通过 `idevice` 工具集和自定义 Python 脚本实现了完整的 iOS 设备自动化测试流程。

## 架构位置

该类位于 Skia 的 recipe flavor 体系中:
- 继承自 `default.DefaultFlavor`
- 通过 `api.py` 中的工厂方法创建
- 在检测到 iOS 构建器时自动选用
- 与 `xcode` 模块协同工作

**调用链:**
```
SkiaFlavorApi.get_flavor()
  → is_ios() 检测
  → iOSFlavor 实例化
```

## 主要类与结构体

### iOSFlavor

iOS 平台的 flavor 实现类。

**构造函数:**
```python
def __init__(self, m, app_name):
```

**成员变量:**
- `device_dirs`: iOS 设备上的目录结构
- `env`: iOS 特定的环境变量
- `app_name`: 要运行的应用名称

**目录结构:**
```python
device_dirs = DeviceDirs(
    bin_dir='[unused]',
    dm_dir='dm',
    perf_data_dir='perf',
    resource_dir='resources',
    fonts_dir='NOT_SUPPORTED',
    images_dir='images',
    lotties_dir='lotties',
    skp_dir='skps',
    svg_dir='svgs',
    tmp_dir='tmp',
    texttraces_dir=''
)
```

## 公共 API 函数

### 环境与上下文

#### `env` (property)

返回 iOS 特定的环境变量字典:
- `IOS_BUNDLE_ID`: 应用的 bundle ID (`com.google.<app_name>`)
- `IOS_MOUNT_POINT`: iOS 设备的挂载点路径

#### `context()`

返回包含 iOS 环境变量的上下文管理器。

### 设备管理

#### `install()`

安装和配置 iOS 设备,执行以下步骤:
1. 终止 `usbmuxd` 进程(Mac 平台)
2. 验证或配对设备
3. 挂载开发者镜像
4. 安装 Xcode(Mac 平台)
5. 安装应用包

**重试机制:**
- 配对失败会自动重试
- 应用安装失败会先卸载再重试
- 最多 2 次安装尝试

#### `step(name, cmd, **kwargs)`

在 iOS 设备上执行命令:
- Mac 平台: 使用 `ios_xcode_run.py` 脚本通过 Xcode 运行
- 其他平台: 使用 `idevicedebug run` 命令
- 失败时输出完整调试信息

### 文件操作

#### `copy_file_to_device(host, device)`

将文件从主机复制到 iOS 设备。

**实现:**
```python
self._run_ios_script('push_file', host, device)
```

#### `copy_directory_contents_to_device(host, device)`

复制目录内容到设备(仅在需要时复制)。

**实现:**
```python
self._run_ios_script('push_if_needed', host, device)
```

#### `copy_directory_contents_to_host(device, host)`

从设备复制目录内容到主机。

**实现:**
```python
self._run_ios_script('pull_if_needed', device, host)
```

#### `remove_file_on_device(path)`

删除设备上的文件。

#### `create_clean_device_dir(path)`

创建干净的设备目录(先删除再创建)。

#### `read_file_on_device(path, **kwargs)`

读取设备上文件的内容。

**返回值:**
- 成功: 文件内容字符串(去除尾部空白)
- 失败: `None`

## 内部实现细节

### 设备配对流程

```python
try:
    self.m.run(self.m.step, 'check if device is paired',
               cmd=['idevicepair', 'validate'], ...)
except self.m.step.StepFailure:
    self._run('pair device', 'idevicepair', 'pair')
```

**工作原理:**
1. 先检查设备是否已配对
2. 如果未配对,执行配对操作
3. 使用 `_run` 方法实现重试逻辑

### 开发者镜像挂载

**检测逻辑:**
```python
if 'ImageSignature' not in image_info_out:
    # 需要挂载镜像
```

**查找镜像:**
1. 使用 glob 查找 `ios-dev-image*` 包
2. 在包中查找 `.dmg` 和 `.dmg.signature` 文件
3. 调用 `ideviceimagemounter` 挂载

**错误处理:**
- 验证只找到一个镜像包
- 确保镜像和签名文件都存在

### 应用安装策略

**卸载回调:**
```python
def uninstall_app(attempt):
    self.m.run(self.m.step, 'uninstall %s' % self.app_name, ...)
```

**重试安装:**
```python
self.m.run.with_retry(self.m.step, 'install %s' % self.app_name,
                      num_attempts,
                      between_attempts_fn=uninstall_app, ...)
```

**设计理由:**
- App ID 变化会导致升级失败
- 失败时先卸载再重试
- 避免残留安装状态

### iOS 脚本封装

#### `_run_ios_script(script, first, *rest)`

统一的 iOS 脚本调用接口:

**脚本位置:**
```
skia/platform_tools/ios/bin/ios_<script>
```

**支持的脚本:**
- `ios_push_file`: 推送文件
- `ios_push_if_needed`: 条件推送
- `ios_pull_if_needed`: 条件拉取
- `ios_rm`: 删除文件
- `ios_mkdir`: 创建目录
- `ios_cat_file`: 读取文件

### 重试机制

#### `_run(title, *cmd, **kwargs)`

带重试的命令执行:

```python
def sleep(attempt):
    self.m.step('sleep before attempt %d' % attempt,
                cmd=['sleep', '2'])

return self.m.run.with_retry(self.m.step, title, 3, cmd=list(cmd),
                             between_attempts_fn=sleep, **kwargs)
```

**特点:**
- 默认 3 次重试
- 重试间隔 2 秒
- 适用于不稳定的 iOS 操作

## 依赖关系

**外部工具:**
- `idevicepair`: 设备配对
- `ideviceimagemounter`: 挂载开发者镜像
- `ideviceinstaller`: 应用安装
- `idevicedebug`: 应用调试(非 Mac 平台)
- `killall`: 终止进程(Mac 平台)

**Recipe 模块:**
- `xcode`: Xcode 安装和管理
- `run`: 命令执行和重试
- `file`: 文件操作
- `path`: 路径处理

**自定义脚本:**
- `ios_xcode_run.py`: Mac 平台应用运行
- `ios_debug_cmd.py`: 调试输出
- `ios_*.py`: 各种 iOS 操作脚本

## 设计模式与设计决策

### 平台特化模式

通过继承 `DefaultFlavor` 实现平台特化:
- **优点:** 复用通用逻辑
- **优点:** 仅覆盖平台特定方法
- **优点:** 保持接口一致性

### 重试与容错

大量使用重试机制:
- **原因:** iOS 设备连接不稳定
- **策略:** 重试 + 睡眠 + 恢复操作
- **效果:** 提高测试稳定性

### 脚本封装

将复杂操作封装为 Python 脚本:
- **优点:** 简化 recipe 逻辑
- **优点:** 便于单独测试和调试
- **优点:** 跨平台兼容性好

### 条件执行

根据平台执行不同代码:
```python
if self.m.platform.is_mac:
    # Mac 特定逻辑
else:
    # 其他平台逻辑
```

**设计考量:**
- Xcode 仅在 Mac 上可用
- 不同工具的可用性
- 性能和功能权衡

## 性能考量

### 设备初始化开销

**耗时操作:**
1. 终止和重启 `usbmuxd`: ~10 秒
2. 设备配对: 数秒
3. 挂载开发者镜像: 数秒
4. 应用安装: 10-30 秒

**优化策略:**
- 缓存配对状态
- 检查镜像是否已挂载
- 使用 `push_if_needed` 避免重复传输

### 文件传输优化

**条件传输:**
```python
push_if_needed, pull_if_needed
```
- 只传输变化的文件
- 减少网络开销
- 加快测试执行

### 重试代价

**权衡:**
- 重试增加稳定性
- 但延长失败的总时间
- 睡眠间隔需要平衡

## 相关文件

**核心实现:**
- `infra/bots/recipe_modules/flavor/default.py`: 基类实现
- `infra/bots/recipe_modules/flavor/api.py`: Flavor API 入口
- `infra/bots/recipe_modules/flavor/__init__.py`: 模块定义

**iOS 脚本:**
- `platform_tools/ios/bin/ios_push_file`
- `platform_tools/ios/bin/ios_pull_if_needed`
- `platform_tools/ios/bin/ios_rm`
- `platform_tools/ios/bin/ios_mkdir`
- `platform_tools/ios/bin/ios_cat_file`

**资源文件:**
- `ios_xcode_run.py`: Xcode 运行脚本
- `ios_debug_cmd.py`: 调试命令脚本

**其他 Flavor:**
- `android.py`: Android 平台实现
- `chromebook.py`: Chromebook 平台实现
- `ssh.py`: SSH 远程执行基类
