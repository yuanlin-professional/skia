# DawnTypes

> 源文件: `include/gpu/graphite/dawn/DawnTypes.h`

## 概述

DawnTypes.h 是一个已弃用的头文件,仅包含一个重定向到 DawnGraphiteTypes.h 的 include 指令。该文件保留用于向后兼容,新代码应直接使用 DawnGraphiteTypes.h。

## 架构位置

该文件位于 Skia Graphite GPU 后端的 Dawn/WebGPU 平台特定接口层。它是类型系统重构过程中的过渡性文件,用于在不破坏现有代码的情况下完成 API 演进。

## 文件内容

```cpp
/*
 * Copyright 2022 Google LLC
 *
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// DEPRECRATED: DawnTypes.h will be removed in the future, please include DawnGraphiteTypes.h
#include "include/gpu/graphite/dawn/DawnGraphiteTypes.h"
```

## 弃用说明

### 弃用原因

1. **命名一致性**: "GraphiteTypes" 明确表示这是 Graphite 使用的类型,而非通用 Dawn 类型
2. **避免混淆**: Dawn 项目本身也有 DawnTypes,Graphite 特定类型应有明确命名
3. **API 组织**: 与 Metal 后端的命名保持一致(MtlGraphiteTypes)

### 迁移指南

**旧代码**:
```cpp
#include "include/gpu/graphite/dawn/DawnTypes.h"
```

**新代码**:
```cpp
#include "include/gpu/graphite/dawn/DawnGraphiteTypes.h"
```

### 移除时间线

- **当前状态**: 已弃用但通过重定向仍可用
- **预期移除**: 未来主版本更新
- **兼容性保证**: 当前无需立即修改即可编译
- **建议**: 尽快迁移以避免未来问题

## 功能说明

该文件重定向到的 DawnGraphiteTypes.h 提供:

### 主要内容

1. **DawnTextureInfo**: Dawn 纹理信息类
   - 封装 wgpu::TextureFormat, TextureUsage 等
   - 实现 TextureInfo::Data 接口
   - 支持 YCbCr 采样(Android Vulkan)

2. **TextureInfos 命名空间**:
   - `MakeDawn`: 从 DawnTextureInfo 创建 TextureInfo
   - `GetDawnTextureInfo`: 提取 Dawn 特定信息

3. **BackendTextures 命名空间**:
   - `MakeDawn`: 从 WGPUTexture 创建 BackendTexture
   - 支持多平面纹理和 TextureView

### 类型细节

```cpp
// 主要类型(在 DawnGraphiteTypes.h 中定义)
class DawnTextureInfo : public TextureInfo::Data {
    wgpu::TextureFormat fFormat;
    wgpu::TextureFormat fViewFormat;
    wgpu::TextureUsage fUsage;
    wgpu::TextureAspect fAspect;
    uint32_t fSlice;
    // ...
};
```

## 与其他类型文件的对比

| 文件 | 状态 | 用途 |
|------|------|------|
| DawnTypes.h | 已弃用 | 旧名称,重定向 |
| DawnGraphiteTypes.h | 当前使用 | Graphite Dawn 类型定义 |
| DawnUtils.h | 已弃用 | 旧工具函数,重定向到 BackendContext |
| DawnBackendContext.h | 当前使用 | Context 创建接口 |

**模式**: Graphite 前缀明确表示 Skia Graphite 专用。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/gpu/graphite/dawn/DawnGraphiteTypes.h` | 实际类型定义 |

### 被依赖的模块

- 旧版 Dawn 应用代码
- 可能的第三方库
- 新代码应直接使用 DawnGraphiteTypes.h

## 迁移策略

### 批量替换

```bash
# 在整个项目中替换
find . -type f \( -name "*.cpp" -o -name "*.h" -o -name "*.mm" \) \
  -exec sed -i '' 's|dawn/DawnTypes.h|dawn/DawnGraphiteTypes.h|g' {} +
```

### 验证迁移

```bash
# 确认没有残留引用
grep -r "dawn/DawnTypes.h" --include="*.cpp" --include="*.h" .
```

### 构建测试

```bash
# 重新编译验证
mkdir build && cd build
cmake .. && make
./run_tests
```

## 设计模式与设计决策

### 渐进式弃用

Skia 的弃用策略:
1. **阶段一**: 创建新文件(DawnGraphiteTypes.h)
2. **阶段二**: 旧文件重定向到新文件
3. **阶段三**: 标记 DEPRECATED
4. **阶段四**: (未来)移除旧文件

**优势**:
- 不破坏现有代码
- 给予充足迁移时间
- 清晰的演进路径

### 命名空间隔离

Graphite 前缀避免命名冲突:
- **Dawn 项目**: 可能有自己的 DawnTypes
- **Skia Graphite**: DawnGraphiteTypes 明确表示所属
- **好处**: 可以同时使用 Dawn 和 Skia

## 使用示例对比

### 旧代码 (使用 DawnTypes.h)

```cpp
#include "include/gpu/graphite/dawn/DawnTypes.h"

using namespace skgpu::graphite;

// 创建纹理信息
DawnTextureInfo info(
    SampleCount::k1,
    Mipmapped::kNo,
    wgpu::TextureFormat::RGBA8Unorm,
    wgpu::TextureUsage::RenderAttachment
);
```

### 新代码 (使用 DawnGraphiteTypes.h)

```cpp
#include "include/gpu/graphite/dawn/DawnGraphiteTypes.h"

using namespace skgpu::graphite;

// 完全相同的代码
DawnTextureInfo info(
    SampleCount::k1,
    Mipmapped::kNo,
    wgpu::TextureFormat::RGBA8Unorm,
    wgpu::TextureUsage::RenderAttachment
);
```

**注意**: API 完全兼容,只是 include 文件名不同。

## 平台相关说明

### Desktop (Dawn Native)

在 Desktop 平台使用 Dawn Native:
```cpp
#include "include/gpu/graphite/dawn/DawnGraphiteTypes.h"
// 完整的 WebGPU 特性支持
```

### Web (Emscripten)

在 Web 平台使用浏览器 WebGPU:
```cpp
#include "include/gpu/graphite/dawn/DawnGraphiteTypes.h"
// 功能取决于浏览器实现
```

### 跨平台考虑

```cpp
// 条件编译保护
#if defined(SK_DAWN)
    #include "include/gpu/graphite/dawn/DawnGraphiteTypes.h"
    // Dawn 特定代码
#elif defined(SK_METAL)
    #include "include/gpu/graphite/mtl/MtlGraphiteTypes_cpp.h"
    // Metal 特定代码
#endif
```

## 常见问题

### Q: 必须立即迁移吗?

A: 不必须,但强烈推荐。当前重定向机制保证兼容,但未来版本可能移除旧文件。

### Q: 迁移后需要修改代码逻辑吗?

A: 不需要。两个文件定义了完全相同的 API,只是文件名不同。

### Q: 为什么不直接删除旧文件?

A: Skia 重视向后兼容性,通过渐进式弃用减少对现有项目的影响。

### Q: 如何知道是否还在使用旧文件?

A: 使用 grep 或 IDE 的全局搜索功能检查项目。

### Q: 旧文件何时会被删除?

A: 没有具体时间表,但可能在下一个主版本更新。关注 Skia 的 release notes。

## 编译器和工具支持

### IDE 重构

现代 IDE 支持批量重命名:

**Visual Studio**:
1. 搜索 "dawn/DawnTypes.h"
2. 使用 Find and Replace
3. 替换为 "dawn/DawnGraphiteTypes.h"

**CLion/VSCode**:
1. Ctrl/Cmd + Shift + F
2. Find: `dawn/DawnTypes\.h`
3. Replace: `dawn/DawnGraphiteTypes.h`

### 静态分析

某些工具可能报告弃用警告:
```cpp
// 可能的编译器警告(未来版本)
#warning "DawnTypes.h is deprecated, use DawnGraphiteTypes.h"
```

## 最佳实践

1. **新项目**: 直接使用 DawnGraphiteTypes.h
2. **现有项目**: 安排迁移,但不紧急
3. **第三方库**: 检查依赖是否使用旧文件
4. **文档**: 更新项目文档指向新文件
5. **CI/CD**: 添加检查防止新代码使用旧文件

## 检查清单

迁移前的检查步骤:

- [ ] 搜索项目中所有 DawnTypes.h 引用
- [ ] 确认替换为 DawnGraphiteTypes.h 的位置
- [ ] 更新 CMakeLists.txt 或其他构建文件(如果硬编码)
- [ ] 重新编译所有目标
- [ ] 运行完整测试套件
- [ ] 更新代码注释和文档
- [ ] 提交代码审查

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/graphite/dawn/DawnGraphiteTypes.h` | 替代文件,实际类型定义 |
| `include/gpu/graphite/dawn/DawnUtils.h` | 另一个弃用文件 |
| `include/gpu/graphite/dawn/DawnBackendContext.h` | Dawn Context 创建 |
| `webgpu/webgpu_cpp.h` | WebGPU C++ API |

## 总结

DawnTypes.h 是一个弃用的重定向头文件:

**关键点**:
- **当前**: 通过重定向仍可用
- **推荐**: 使用 DawnGraphiteTypes.h
- **未来**: 该文件将被移除
- **迁移**: 简单的 include 路径替换

**价值**:
- 体现良好的 API 演进策略
- 保证向后兼容性
- 提供清晰的迁移路径

虽然这是一个简单的重定向文件,但它展示了 Skia 团队对 API 设计和用户体验的考虑,通过渐进式变更最小化破坏性影响。
