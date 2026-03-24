# DawnUtils

> 源文件: `include/gpu/graphite/dawn/DawnUtils.h`

## 概述

DawnUtils.h 是一个已弃用的头文件,仅包含一个重定向到 DawnBackendContext.h 的 include 指令。该文件保留用于向后兼容,新代码应直接使用 DawnBackendContext.h。

## 架构位置

该文件位于 Skia Graphite GPU 后端的 Dawn/WebGPU 平台特定接口层。它是 API 演进过程中的遗留兼容层,在未来版本中将被移除。

## 文件内容

```cpp
/*
 * Copyright 2022 Google LLC
 *
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// DEPRECRATED: DawnUtils.h will be removed in the future, please include DawnBackendContext.h
#include "include/gpu/graphite/dawn/DawnBackendContext.h"
```

## 弃用说明

### 弃用原因

1. **命名清晰化**: "Utils" 过于宽泛,"BackendContext" 更准确描述文件内容
2. **API 一致性**: 与其他后端(Metal, Vulkan)保持命名一致
3. **职责明确**: BackendContext 专注于 Context 创建,而非通用工具函数

### 迁移指南

**旧代码**:
```cpp
#include "include/gpu/graphite/dawn/DawnUtils.h"
```

**新代码**:
```cpp
#include "include/gpu/graphite/dawn/DawnBackendContext.h"
```

### 移除时间线

- **当前状态**: 已弃用但通过重定向仍可用
- **预期移除**: 未来某个主版本更新
- **影响范围**: 仅影响直接 include 该头文件的代码
- **兼容性**: 当前无需立即修改即可编译

## 功能说明

该文件重定向到的 DawnBackendContext.h 提供:

### 主要功能

1. **DawnBackendContext 结构体**: 封装 WebGPU Instance, Device, Queue
2. **ContextFactory::MakeDawn**: 创建 Dawn 后端的 Graphite Context
3. **DawnTickFunction**: 事件循环处理函数类型定义
4. **DawnNativeProcessEventsFunction**: Desktop 平台的默认 tick 实现

### 使用场景

- 初始化 Graphite Dawn 后端
- WebGPU/Dawn 应用程序启动
- 跨平台图形应用(Desktop 和 Web)

## 与其他弃用文件的对比

| Dawn 文件 | Metal 等价文件 | 状态 |
|-----------|---------------|------|
| DawnUtils.h | MtlGraphiteUtils.h | 已弃用 |
| DawnTypes.h | MtlGraphiteTypes.h | 已弃用 |
| DawnBackendContext.h | MtlBackendContext.h | 当前使用 |
| DawnGraphiteTypes.h | MtlGraphiteTypes_cpp.h | 当前使用 |

**模式**: Skia 正在统一各后端的命名约定。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/gpu/graphite/dawn/DawnBackendContext.h` | 实际功能提供者 |

### 被依赖的模块

- 旧版 Dawn 应用代码
- 第三方库可能仍在使用
- 新代码应避免依赖

## 迁移策略

### 自动化迁移

```bash
# 批量替换项目中的 include
find . -type f \( -name "*.cpp" -o -name "*.h" \) -exec sed -i '' \
  's|include/gpu/graphite/dawn/DawnUtils.h|include/gpu/graphite/dawn/DawnBackendContext.h|g' {} +
```

### 手动验证

```bash
# 搜索残留引用
grep -r "DawnUtils.h" --include="*.cpp" --include="*.h" .
```

### Git 历史保持

```bash
# 使用 git mv 保持历史
git mv src/MyDawnUtils.cpp src/MyDawnBackend.cpp
# 然后更新 include 语句
```

## 使用建议

### 对于新项目

```cpp
// 不要这样
#include "include/gpu/graphite/dawn/DawnUtils.h"  // 已弃用!

// 应该这样
#include "include/gpu/graphite/dawn/DawnBackendContext.h"
```

### 对于现有项目

1. **评估影响**: 搜索项目中的使用情况
2. **计划迁移**: 在下一个重构周期完成迁移
3. **测试验证**: 确保迁移后功能正常
4. **文档更新**: 更新项目文档和示例

### 检查清单

- [ ] 搜索所有 `DawnUtils.h` 引用
- [ ] 替换为 `DawnBackendContext.h`
- [ ] 重新编译所有目标
- [ ] 运行单元测试
- [ ] 更新 README 和文档
- [ ] 提交代码审查

## 历史背景

### API 演进

**早期阶段** (2022 年):
- DawnUtils.h 包含各种 Dawn 相关工具函数
- 文件职责不够清晰

**重构阶段** (2022-2023 年):
- 将 Context 创建逻辑分离到 DawnBackendContext.h
- 保留 DawnUtils.h 作为兼容层

**当前阶段**:
- 推荐使用 DawnBackendContext.h
- DawnUtils.h 标记为弃用

**未来计划**:
- 最终移除 DawnUtils.h

### 命名约定变化

Skia 团队的命名演进:
- **旧**: Utils (通用、模糊)
- **新**: BackendContext (具体、清晰)
- **趋势**: 更倾向于描述性命名

## 编译器行为

### 重定向 Include

大多数编译器对 include 重定向的处理:
```cpp
// DawnUtils.h
#include "DawnBackendContext.h"
```

- **预处理阶段**: 直接替换为目标文件内容
- **编译时间**: 可能多一次文件打开操作(微不足道)
- **二进制输出**: 完全相同,无运行时差异

### 构建系统

- **CMake**: 依赖关系保持不变
- **Bazel**: 可能需要更新 BUILD 文件中的 hdrs
- **Make**: 通常无需改动

## 常见问题

### Q: 何时必须迁移?

A: 当前不强制,但推荐尽快迁移以避免未来版本删除该文件时的破坏性变更。

### Q: 迁移会破坏 API 吗?

A: 不会。DawnBackendContext.h 提供了完全相同的 API。

### Q: 为什么不直接删除?

A: Skia 采用渐进式弃用策略,给用户足够的迁移时间。

### Q: 如何知道何时会被删除?

A: 关注 Skia 的 release notes 和 deprecation 公告。

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/graphite/dawn/DawnBackendContext.h` | 替代文件 |
| `include/gpu/graphite/dawn/DawnTypes.h` | 另一个弃用文件 |
| `include/gpu/graphite/dawn/DawnGraphiteTypes.h` | Dawn 类型定义 |

## 总结

DawnUtils.h 是一个简单的重定向头文件,用于 API 向后兼容:

**开发者应该**:
- 新代码: 直接使用 DawnBackendContext.h
- 旧代码: 计划迁移,当前仍可工作
- 注意: 该文件将在未来版本移除

该文件体现了良好的 API 演进实践:
1. **明确弃用**: 清晰的注释说明
2. **平滑过渡**: 重定向机制保证兼容
3. **充足时间**: 给予开发者迁移时间
4. **一致性**: 与其他后端保持命名一致

虽然文件很小,但它展示了 Skia 团队对 API 稳定性和用户体验的重视。
