# DebugUtils

> 源文件: src/gpu/graphite/DebugUtils.h

## 概述

`DebugUtils.h` 是 Skia Graphite GPU 后端的调试工具头文件，定义了条件编译宏 `SK_DUMP_TASKS_CODE`，用于在调试构建中启用任务转储功能。该文件极其简洁，仅包含 19 行代码，但为 Graphite 的任务系统调试提供了关键支持。

该宏允许开发者在调试模式下插入任务转储代码，这些代码在发布构建中会被完全移除，实现零开销的调试功能。

## 架构位置

在 Skia Graphite 调试系统中的位置：

```
skia/
├── include/
│   └── private/base/
│       └── SkDebug.h               # 基础调试宏
├── src/
    └── gpu/
        └── graphite/
            ├── DebugUtils.h        # 本文件
            ├── Task.h              # 任务系统
            └── TaskGraph.cpp       # 任务图实现（使用 SK_DUMP_TASKS_CODE）
```

## 主要宏定义

### SK_DUMP_TASKS_CODE

```cpp
#if defined(SK_DEBUG) && defined(SK_DUMP_TASKS)
    #define SK_DUMP_TASKS_CODE(...)  __VA_ARGS__
#else
    #define SK_DUMP_TASKS_CODE(...)
#endif
```

**功能：** 条件编译调试代码

**启用条件：**
- 必须同时定义 `SK_DEBUG` 和 `SK_DUMP_TASKS`
- 通常在 Debug 构建 + 显式启用任务转储时

**使用方式：**
```cpp
SK_DUMP_TASKS_CODE(
    SkDebugf("Task: %s\n", task->name());
    task->dumpInfo();
);
```

**展开结果：**

**调试模式（SK_DEBUG && SK_DUMP_TASKS）：**
```cpp
SkDebugf("Task: %s\n", task->name());
task->dumpInfo();
```

**其他模式：**
```cpp
// 代码被完全移除，无任何开销
```

## 使用场景

### 1. 任务执行跟踪

```cpp
void executeTask(Task* task) {
    SK_DUMP_TASKS_CODE(
        SkDebugf("Executing task: %s\n", task->name());
    );
    task->execute();
}
```

### 2. 任务图转储

```cpp
void TaskGraph::dump() {
    SK_DUMP_TASKS_CODE(
        SkDebugf("Task Graph:\n");
        for (const auto& task : fTasks) {
            SkDebugf("  - %s (deps: %d)\n",
                     task->name(), task->numDependencies());
        }
    );
}
```

### 3. 资源跟踪

```cpp
void bindTexture(Texture* texture) {
    SK_DUMP_TASKS_CODE(
        SkDebugf("Binding texture %p (size: %dx%d)\n",
                 texture, texture->width(), texture->height());
    );
    // 实际绑定代码...
}
```

### 4. 性能分析

```cpp
void performHeavyOperation() {
    SK_DUMP_TASKS_CODE(
        auto start = std::chrono::high_resolution_clock::now();
    );

    // 实际操作...

    SK_DUMP_TASKS_CODE(
        auto end = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
        SkDebugf("Operation took: %lld us\n", duration.count());
    );
}
```

## 内部实现细节

### 可变参数宏

```cpp
#define SK_DUMP_TASKS_CODE(...)  __VA_ARGS__
```

**功能：** 支持多行代码和任意表达式

**示例：**
```cpp
SK_DUMP_TASKS_CODE(
    int x = 10;
    printf("x = %d\n", x);
    if (x > 5) {
        doSomething();
    }
);
```

### 双重条件检查

```cpp
#if defined(SK_DEBUG) && defined(SK_DUMP_TASKS)
```

**原因：**
- `SK_DEBUG`: 确保在调试构建中
- `SK_DUMP_TASKS`: 显式启用任务转储（可选功能）

**灵活性：** 即使在调试构建中，也可以选择性启用任务转储

### 头文件依赖

```cpp
#include "include/private/base/SkDebug.h"
```

**提供：**
- `SkDebugf` 调试输出函数
- 其他调试宏定义

## 依赖关系

### 直接依赖

1. **SkDebug.h** (include/private/base/SkDebug.h)
   - 提供 `SkDebugf` 等调试函数
   - 基础调试基础设施

### 被依赖模块

1. **任务系统**
   - `Task.cpp` - 任务基类实现
   - `TaskGraph.cpp` - 任务图管理
   - `CommandBuffer.cpp` - 命令缓冲区

2. **渲染管线**
   - `DrawPass.cpp` - 绘制通道
   - `RenderPassTask.cpp` - 渲染通道任务

3. **资源管理**
   - `ResourceProvider.cpp` - 资源提供者
   - `Texture.cpp` - 纹理管理

## 设计模式与设计决策

### 1. 零开销抽象

**原理：**
```cpp
SK_DUMP_TASKS_CODE(expensive_debug_operation());
// 在发布构建中完全消失，无分支，无函数调用
```

**优势：**
- 发布构建零性能影响
- 无需运行时检查
- 代码可读性强

### 2. 显式启用

需要定义两个宏：

**原因：**
- `SK_DEBUG` 默认在调试构建启用
- `SK_DUMP_TASKS` 需要显式启用
- 避免输出过多调试信息

**启用方式：**
```bash
# CMake
cmake -DSK_DEBUG=1 -DSK_DUMP_TASKS=1 ..

# GN
gn gen out/Debug --args='is_debug=true extra_cflags=["-DSK_DUMP_TASKS"]'
```

### 3. 可变参数支持

使用 `...` 和 `__VA_ARGS__`：

**优势：**
- 支持任意代码
- 支持多行语句
- 支持复杂逻辑

### 4. 条件编译而非运行时检查

**替代方案（不推荐）：**
```cpp
if (gEnableTaskDump) {
    dumpTaskInfo();  // 运行时分支
}
```

**当前方案（推荐）：**
```cpp
SK_DUMP_TASKS_CODE(
    dumpTaskInfo();  // 编译时移除
);
```

**优势：**
- 无运行时分支
- 无分支预测失败
- 编译器可完全优化掉

## 性能考量

### 1. 零开销原则

**发布构建：**
```cpp
// 源代码
SK_DUMP_TASKS_CODE(SkDebugf("Task executed\n"));

// 预处理后
// （空白，完全移除）
```

**性能影响：** 零

### 2. 调试构建开销

**开销来源：**
- `SkDebugf` 调用：~1-10 μs
- 字符串格式化：~5-50 μs
- I/O 操作：~100-1000 μs

**可接受：** 调试构建不关注性能

### 3. 代码大小

**影响：**
- 调试构建：增加代码大小
- 发布构建：零影响

### 4. 编译时间

**影响：**
- 轻微增加（预处理宏展开）
- 通常可忽略

## 相关文件

### 核心依赖
- `include/private/base/SkDebug.h` - 调试基础设施

### 使用者
- `src/gpu/graphite/Task.cpp` - 任务系统
- `src/gpu/graphite/TaskGraph.cpp` - 任务图
- `src/gpu/graphite/CommandBuffer.cpp` - 命令缓冲
- `src/gpu/graphite/DrawPass.cpp` - 绘制通道
- `src/gpu/graphite/RenderPassTask.cpp` - 渲染通道任务

### 类似工具
- `SK_DEBUG` - 通用调试宏
- `SK_DEVELOPER` - 开发者模式宏
- `GPU_TEST_UTILS` - GPU 测试工具宏

### 文档
- Skia 调试指南
- 构建配置文档
