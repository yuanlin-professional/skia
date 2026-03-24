# Log

> 源文件
> - src/gpu/graphite/Log.h

## 概述

`Log.h` 是 Skia Graphite 渲染引擎的日志宏定义文件，提供了一组统一的日志接口用于记录不同优先级的消息。该文件是对 Skia 基础日志系统的薄包装，为所有日志消息添加 `[graphite]` 前缀以区分来源。

## 架构位置

```
include/private/base/SkLog.h (Skia 基础日志)
  └── src/gpu/graphite/Log.h (Graphite 日志包装)
      └── Graphite 代码库
```

这是一个轻量级的工具头文件，被整个 Graphite 代码库使用。

## 主要宏定义

### SKGPU_LOG

```cpp
#define SKGPU_LOG(priority, fmt, ...) \
    SKIA_LOG((SkLogPriority)priority, "[graphite] " fmt, ##__VA_ARGS__)
```

**功能**：通用日志宏，接受优先级参数

**参数**：
- `priority`：日志优先级（`SkLogPriority` 枚举）
- `fmt`：printf 风格的格式字符串
- `...`：可变参数

**使用示例**：
```cpp
SKGPU_LOG(SkLogPriority::kInfo, "Texture created: %dx%d", width, height);
```

### SKGPU_LOG_F

```cpp
#define SKGPU_LOG_F(fmt, ...) SKIA_LOG(SkLogPriority::kFatal, "[graphite] " fmt, ##__VA_ARGS__)
```

**功能**：致命错误日志（Fatal）

**行为**：记录日志后可能终止程序

**使用场景**：不可恢复的严重错误

**示例**：
```cpp
SKGPU_LOG_F("Failed to create context: out of memory");
```

### SKGPU_LOG_E

```cpp
#define SKGPU_LOG_E(fmt, ...) SKIA_LOG(SkLogPriority::kError, "[graphite] " fmt, ##__VA_ARGS__)
```

**功能**：错误日志（Error）

**使用场景**：操作失败，但程序可以继续

**示例**：
```cpp
SKGPU_LOG_E("Shader compilation failed for: %s", shaderName);
```

### SKGPU_LOG_W

```cpp
#define SKGPU_LOG_W(fmt, ...) SKIA_LOG(SkLogPriority::kWarning, "[graphite] " fmt, ##__VA_ARGS__)
```

**功能**：警告日志（Warning）

**使用场景**：潜在问题或次优情况

**示例**：
```cpp
SKGPU_LOG_W("Texture size exceeds recommended limit: %d", size);
```

### SKGPU_LOG_D

```cpp
#define SKGPU_LOG_D(fmt, ...) SKIA_LOG(SkLogPriority::kDebug, "[graphite] " fmt, ##__VA_ARGS__)
```

**功能**：调试日志（Debug）

**使用场景**：开发和调试信息（通常在发布版本中禁用）

**示例**：
```cpp
SKGPU_LOG_D("Cache hit for key: %u", keyHash);
```

## 内部实现细节

### 前缀注入

所有宏在格式字符串前添加 `[graphite]` 前缀：

```cpp
"[graphite] " fmt
```

**效果**：
```
输入：SKGPU_LOG_E("Error: %d", code)
输出：[graphite] Error: 42
```

### 可变参数处理

使用 `##__VA_ARGS__` 处理可变参数：

```cpp
#define SKGPU_LOG_E(fmt, ...) SKIA_LOG(..., fmt, ##__VA_ARGS__)
```

**`##` 的作用**：
- 如果 `__VA_ARGS__` 为空，删除前面的逗号
- 允许无参数调用：`SKGPU_LOG_E("Simple message")`

### 底层实现

所有宏最终调用 `SKIA_LOG`（定义在 `include/private/base/SkLog.h`）：

```cpp
#define SKIA_LOG(priority, fmt, ...) \
    // 根据构建配置和优先级过滤
    // 调用平台特定的日志函数（printf、NSLog、Android Log等）
```

## 依赖关系

### 核心依赖

| 依赖项 | 作用 |
|--------|------|
| `include/private/base/SkLog.h` | Skia 基础日志系统 |
| `SkLogPriority` | 日志优先级枚举 |

## 设计模式与设计决策

### 1. 宏包装模式

使用宏而非函数，保留：
- 源文件位置信息
- 零开销（条件编译）
- printf 风格的类型安全

### 2. 统一前缀

`[graphite]` 前缀提供：
- 清晰的日志来源标识
- 方便过滤 Graphite 相关日志
- 与 Ganesh 等其他后端区分

### 3. 分级日志

提供四个优先级：
- **Fatal**：不可恢复
- **Error**：操作失败
- **Warning**：潜在问题
- **Debug**：调试信息

### 4. 最小化设计

仅定义必要的宏，其他功能委托给 `SKIA_LOG`：
- 平台适配
- 过滤控制
- 输出重定向

## 性能考量

### 编译时过滤

根据构建配置，某些日志可能在编译时完全移除：

```cpp
#if defined(NDEBUG)
    #define SKGPU_LOG_D(fmt, ...) ((void)0)  // 发布版本：无操作
#endif
```

### 零开销抽象

宏展开为内联代码，无函数调用开销。

### 条件求值

可变参数仅在日志实际输出时求值：

```cpp
SKGPU_LOG_D("Value: %d", expensiveCalculation());
// 如果 DEBUG 日志禁用，expensiveCalculation() 不会被调用
```

**注意**：这依赖于 `SKIA_LOG` 的实现细节。

## 使用示例

### 错误处理

```cpp
if (!context->initialize()) {
    SKGPU_LOG_E("Failed to initialize Graphite context");
    return nullptr;
}
```

### 资源创建

```cpp
sk_sp<TextureProxy> proxy = TextureProxy::Make(...);
if (!proxy) {
    SKGPU_LOG_W("Texture proxy creation failed, falling back to smaller size");
    proxy = TextureProxy::Make(..., smallerSize);
}
```

### 调试信息

```cpp
#ifdef SK_DEBUG
    SKGPU_LOG_D("Shader cache size: %d entries", cache.count());
#endif
```

### 致命错误

```cpp
if (criticalResourceMissing) {
    SKGPU_LOG_F("Critical resource not found: %s", resourceName);
    // 程序可能在此终止
}
```

## 扩展和自定义

### 添加新优先级

如果需要新的日志级别（如 Info、Verbose）：

```cpp
#define SKGPU_LOG_I(fmt, ...) SKIA_LOG(SkLogPriority::kInfo, "[graphite] " fmt, ##__VA_ARGS__)
#define SKGPU_LOG_V(fmt, ...) SKIA_LOG(SkLogPriority::kVerbose, "[graphite] " fmt, ##__VA_ARGS__)
```

### 条件日志

结合宏创建条件日志：

```cpp
#define SKGPU_LOG_IF(condition, priority, fmt, ...) \
    do { if (condition) SKGPU_LOG(priority, fmt, ##__VA_ARGS__); } while(0)
```

### 结构化日志

可以扩展为结构化日志：

```cpp
#define SKGPU_LOG_STRUCT(priority, category, ...) \
    SKIA_LOG(priority, "[graphite:%s] " fmt, category, ##__VA_ARGS__)
```

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `include/private/base/SkLog.h` | Skia 基础日志系统 |
| `include/private/base/SkDebug.h` | 调试断言和检查 |

## 最佳实践

### 1. 选择合适的优先级

- **Fatal**：仅用于无法继续的情况
- **Error**：操作失败但程序可恢复
- **Warning**：非预期但可处理的情况
- **Debug**：开发调试信息

### 2. 提供上下文信息

```cpp
// 好：提供详细上下文
SKGPU_LOG_E("Failed to allocate texture: size=%dx%d, format=%s", width, height, formatName);

// 差：信息不足
SKGPU_LOG_E("Allocation failed");
```

### 3. 避免敏感信息

不要记录敏感数据（如用户输入、密钥）。

### 4. 性能敏感路径

避免在性能关键路径使用日志，或仅在 Debug 构建启用。

### 5. 使用断言替代日志

对于编程错误，使用 `SkASSERT` 而非日志：

```cpp
// 好：断言
SkASSERT(index < size);

// 差：日志
if (index >= size) {
    SKGPU_LOG_E("Index out of bounds");
}
```
