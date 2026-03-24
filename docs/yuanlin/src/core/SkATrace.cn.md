# SkATrace

> 源文件
> - src/core/SkATrace.h
> - src/core/SkATrace.cpp

## 概述

`SkATrace` 是 Skia 图形库中用于支持 Android ATrace 性能追踪系统的类。它通过挂钩到 Skia 的 `SkEventTracer` 系统，将 Skia 的性能追踪事件转发到 Android 系统的 ATrace 框架，使开发者能够使用 Android 的 Systrace 工具分析 Skia 的渲染性能。

## 架构位置

`SkATrace` 位于 Skia 的性能监控和调试基础设施层，作为 Android 平台特定的追踪后端实现。它是 `SkEventTracer` 接口的具体实现之一。

```
Skia Core
  └── Performance Monitoring
      └── SkEventTracer (抽象接口)
          ├── SkATrace (Android ATrace 后端)
          └── 其他平台追踪后端
```

## 主要类与结构体

### SkATrace

**继承关系**
- 继承自 `SkEventTracer` 接口

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBeginSection` | `void (*)(const char*)` | 函数指针：开始一个追踪区段 |
| `fEndSection` | `void (*)(void)` | 函数指针：结束当前追踪区段 |
| `fIsEnabled` | `bool (*)(void)` | 函数指针：检查 ATrace 是否启用 |

**设计特点**
- 禁止拷贝构造和赋值操作（不可复制）
- 使用函数指针实现运行时动态绑定到 Android 系统库

## 公共 API 函数

### 构造函数

**SkATrace()**
- **功能**: 初始化 ATrace 追踪器，根据编译环境加载 ATrace 函数
- **平台行为**:
  - **Android Framework 构建**: 直接使用 `<cutils/trace.h>` 的宏
  - **Android NDK 构建**: 动态加载 `libandroid.so` 并获取函数地址
  - **其他平台**: 设置 `fIsEnabled` 返回 false，禁用追踪

### SkEventTracer 接口实现

**addTraceEvent(...)**
- **功能**: 添加追踪事件到 ATrace 系统
- **参数**:
  - `phase`: 事件阶段（`TRACE_EVENT_PHASE_COMPLETE`、`INSTANT`、`BEGIN`、`END`）
  - `categoryEnabledFlag`: 类别启用标志（当前未使用）
  - `name`: 事件名称字符串
  - `id`, `numArgs`, `argNames`, `argTypes`, `argValues`, `flags`: 扩展参数（当前被忽略）
- **返回**: 始终返回 0（ATrace 不需要句柄）
- **行为**:
  - `COMPLETE` 或 `INSTANT` 阶段：调用 `fBeginSection(name)`
  - `INSTANT` 阶段：立即调用 `fEndSection()`
  - 其他参数和值对被丢弃（ATrace 只支持简单的名称追踪）

**updateTraceEventDuration(...)**
- **功能**: 结束当前追踪区段（用于作用域追踪）
- **参数**: `handle` - 事件句柄（ATrace 中未使用）
- **行为**: 如果 ATrace 启用，调用 `fEndSection()`

**getCategoryGroupEnabled(const char* name)**
- **功能**: 检查指定类别是否启用
- **返回**: 始终返回启用标志
- **原因**: Chrome 追踪系统不会重复调用此函数，因此返回启用，在 `addTraceEvent` 中检查实际状态

**getCategoryGroupName(const uint8_t* categoryEnabledFlag)**
- **功能**: 返回类别组名称
- **返回**: 固定字符串 `"skiaATrace"`

**newTracingSection(const char* name)**
- **功能**: 创建新追踪区段（ATrace 不支持）
- **实现**: 空操作

## 内部实现细节

### 平台特定初始化

#### Android Framework 构建 (`SK_BUILD_FOR_ANDROID_FRAMEWORK`)
```cpp
fIsEnabled = []{ return static_cast<bool>(CC_UNLIKELY(ATRACE_ENABLED())); };
fBeginSection = [](const char* name){ ATRACE_BEGIN(name); };
fEndSection = []{ ATRACE_END(); };
```
- 直接使用编译期可用的宏
- `CC_UNLIKELY` 优化分支预测
- `ATRACE_ENABLED()` 检查系统属性

#### Android NDK 构建 (`SK_BUILD_FOR_ANDROID`)
```cpp
void* lib = dlopen("libandroid.so", RTLD_NOW | RTLD_LOCAL);
fBeginSection = dlsym(lib, "ATrace_beginSection");
fEndSection = dlsym(lib, "ATrace_endSection");
fIsEnabled = dlsym(lib, "ATrace_isEnabled");
```
- 运行时动态链接 Android 库
- 避免静态链接依赖
- 支持不同 Android 版本

### 追踪事件映射

Skia 追踪宏到 ATrace 的映射：

| Skia 宏 | ATrace 操作 |
|---------|------------|
| `TRACE_EVENT*` | `beginSection()` + `endSection()` |
| `TRACE_EVENT_INSTANT*` | `beginSection()` + 立即 `endSection()` |
| `TRACE_EVENT_BEGIN` | `beginSection()` |
| `TRACE_EVENT_END` | `endSection()` |

### 简化设计权衡

- **丢弃额外参数**: ATrace 只支持区段名称，所有参数对被忽略
- **全嵌套模型**: ATrace 是栈式追踪系统，要求正确嵌套的 begin/end 调用
- **无分区支持**: `newTracingSection()` 为空实现

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/utils/SkEventTracer.h` | 追踪器抽象接口 |
| `include/utils/SkTraceEventPhase.h` | 追踪事件阶段常量 |
| `<cutils/trace.h>` | Android Framework 追踪宏（Framework 构建） |
| `<dlfcn.h>` | 动态库加载（NDK 构建） |
| `src/core/SkTraceEventCommon.h` | Framework 追踪工具类 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| Skia 初始化代码 | 注册为全局追踪器 |
| Android Framework | 通过 `SkAndroidFrameworkTraceUtil` 控制启用 |
| 性能分析工具 | Systrace/Perfetto 读取追踪数据 |

## 设计模式与设计决策

### 策略模式（Strategy Pattern）
- **接口**: `SkEventTracer` 定义追踪接口
- **具体策略**: `SkATrace` 实现 Android 特定追踪
- **优势**: 不同平台可实现不同追踪后端

### 函数指针动态绑定
- **动机**: 支持不同 Android 构建环境（Framework vs NDK）
- **实现**: 构造函数根据编译宏选择初始化路径
- **优势**: 单一源代码支持多种部署场景

### 适配器模式（Adapter Pattern）
- **角色**: 将 Skia 的通用追踪接口适配到 ATrace 的简单 API
- **转换**: 复杂的参数化事件 → 简单的区段名称
- **权衡**: 牺牲细节信息换取广泛兼容性

### 延迟检查（Lazy Check）
- **特点**: `getCategoryGroupEnabled` 总是返回启用
- **实际检查**: 在 `addTraceEvent` 中调用 `fIsEnabled()`
- **原因**: 适应 Chrome 追踪系统的调用约定

## 性能考量

### 性能优化

1. **动态启用检查**
   - 每次追踪事件都调用 `fIsEnabled()`
   - ATrace 禁用时避免任何开销
   - 利用 CPU 分支预测优化热路径

2. **零拷贝设计**
   - 直接传递名称字符串指针
   - 不进行格式化或字符串构建
   - ATrace 负责字符串的后续处理

3. **轻量级调用**
   - 函数指针直接调用，无虚函数开销
   - 内联 lambda 表达式减少调用层级

4. **条件编译**
   - 非 Android 平台编译出最小代码
   - 避免不必要的库依赖

### 性能特征

| 操作 | 开销 | 说明 |
|------|------|------|
| ATrace 禁用时 | ~1ns | 单次函数指针调用 + 分支 |
| ATrace 启用时 | ~100-500ns | 系统调用写入追踪缓冲区 |
| 动态加载（NDK） | ~1ms | 仅在初始化时一次性开销 |

### 使用建议

- **Android Framework**: 推荐使用，零额外开销
- **Android NDK**: 正常使用，初始化有轻微开销
- **其他平台**: 自动禁用，无性能影响

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/utils/SkEventTracer.h` | 接口定义 | 追踪器抽象基类 |
| `include/utils/SkTraceEventPhase.h` | 依赖 | 追踪事件阶段常量 |
| `src/core/SkTraceEventCommon.h` | 协作 | Framework 追踪工具类 |
| `src/core/SkTraceEvent.h` | 使用者 | Skia 追踪宏定义 |
| Android Systrace | 数据消费者 | 读取和可视化追踪数据 |
| Android Perfetto | 数据消费者 | 新一代追踪系统 |
