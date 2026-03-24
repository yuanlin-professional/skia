# GrDrawOpTest

> 源文件: src/gpu/ganesh/GrDrawOpTest.h, src/gpu/ganesh/GrDrawOpTest.cpp

## 概述

`GrDrawOpTest` 模块提供了 Ganesh GPU 后端绘制操作(GrDrawOp)的测试工具和宏定义。该模块仅在 `GPU_TEST_UTILS` 定义时编译,用于随机化测试、模糊测试(Fuzzing)和单元测试。主要功能是生成随机配置的绘制操作,帮助发现边界情况和潜在 bug。

主要功能包括:
- **随机操作生成**: 创建随机配置的绘制操作用于测试
- **测试工厂宏**: 提供标准化的测试工厂函数定义
- **随机模板设置**: 生成多种模板缓冲区配置用于测试
- **Friend 声明宏**: 简化测试工厂的 friend 声明

该模块不参与正常的渲染流程,仅用于开发和测试阶段。

## 架构位置

该模块位于 Ganesh 测试基础设施层:

```
src/gpu/ganesh/
├── GrDrawOpTest.h/cpp         # 绘制操作测试工具(当前模块)
├── GrOp.h                     # 操作基类
└── ops/
    ├── GrDrawOp.cpp           # 绘制操作基类
    └── *Op.cpp                # 各种操作实现(定义测试工厂)

tests/
└── OpTest.cpp                 # 使用测试工具的测试
```

**编译条件**: 仅在定义 `GPU_TEST_UTILS` 时编译,发布版本中不包含。

## 主要类与结构体

### GrDrawRandomOp
生成随机配置的绘制操作并执行。

```cpp
void GrDrawRandomOp(SkRandom* random,
                    skgpu::ganesh::SurfaceDrawContext* sdc,
                    GrPaint&& paint)
```

**功能**: 从已注册的绘制操作测试工厂中随机选择一个,生成操作并添加到绘制上下文。

**用途**: 模糊测试,发现渲染管线的边界情况。

### GR_DRAW_OP_TEST_DEFINE
定义绘制操作测试工厂的宏。

```cpp
#define GR_DRAW_OP_TEST_DEFINE(Op)                     \
    GrOp::Owner Op##__Test(GrPaint&& paint,            \
                           SkRandom* random,           \
                           GrRecordingContext* context,\
                           skgpu::ganesh::SurfaceDrawContext* sdc, \
                           int numSamples)
```

**展开示例**:
```cpp
// GR_DRAW_OP_TEST_DEFINE(MyDrawOp) 展开为:
GrOp::Owner MyDrawOp__Test(GrPaint&& paint,
                           SkRandom* random,
                           GrRecordingContext* context,
                           skgpu::ganesh::SurfaceDrawContext* sdc,
                           int numSamples) {
    // 测试工厂实现
}
```

**用途**: 标准化测试工厂函数签名。

### GR_DRAW_OP_TEST_FRIEND
声明测试工厂为 friend 的宏。

```cpp
#define GR_DRAW_OP_TEST_FRIEND(Op)   \
    friend GrOp::Owner Op##__Test(   \
            GrPaint&&, SkRandom*, GrRecordingContext*, \
            skgpu::ganesh::SurfaceDrawContext*, int)
```

**用途**: 在操作类中声明测试工厂为 friend,允许访问私有构造函数和成员。

**使用示例**:
```cpp
class MyDrawOp : public GrDrawOp {
    GR_DRAW_OP_TEST_FRIEND(MyDrawOp);
    // ...
};
```

### GrGetRandomStencil
生成随机的模板缓冲区设置。

```cpp
const GrUserStencilSettings* GrGetRandomStencil(SkRandom* random,
                                                GrContext_Base* context)
```

**返回值**: 从 4 种预定义模板设置中随机选择一种:
1. `kUnused`: 不使用模板
2. `kReads`: 只读模板(测试 `kLess`)
3. `kWrites`: 只写模板(测试 `kReplace`)
4. `kReadsAndWrites`: 读写模板(测试 `kEqual`, `kIncWrap`, `kInvert`)

**特殊处理**: 如果硬件避免使用模板缓冲区,总是返回 `kUnused`。

## 公共 API 函数

### GrGetRandomStencil
生成随机模板设置用于测试。

```cpp
const GrUserStencilSettings* GrGetRandomStencil(SkRandom* random,
                                                GrContext_Base* context)
```

**实现细节**:
```cpp
if (context->priv().caps()->avoidStencilBuffers()) {
    return &GrUserStencilSettings::kUnused;
}
// 从 4 种预定义设置中随机选择
```

**模板设置示例**:
- **kReads**: 参考值 0x8080,测试 `kLess`,保持原值
- **kWrites**: 参考值 0xffff,始终通过,替换为参考值
- **kReadsAndWrites**: 参考值 0x8000,测试 `kEqual`,通过时递增,失败时反转

## 内部实现细节

### 预定义模板设置

使用 `constexpr` 静态定义模板设置:

```cpp
static constexpr GrUserStencilSettings kReads(
    GrUserStencilSettings::StaticInit<
        0x8080,                      // 参考值
        GrUserStencilTest::kLess,    // 测试函数
        0xffff,                      // 读取掩码
        GrUserStencilOp::kKeep,      // 通过操作
        GrUserStencilOp::kKeep,      // 失败操作
        0xffff>()                    // 写入掩码
);
```

**优势**: 编译期构造,零运行时开销。

### 随机选择算法

使用数组和随机索引实现:

```cpp
static const GrUserStencilSettings* kStencilSettings[] = {
    &GrUserStencilSettings::kUnused,
    &kReads,
    &kWrites,
    &kReadsAndWrites,
};
return kStencilSettings[random->nextULessThan(std::size(kStencilSettings))];
```

**均匀分布**: 每种设置被选中的概率相等(25%)。

### 宏展开机制

`GR_DRAW_OP_TEST_DEFINE` 通过 `##` 连接生成函数名:

```cpp
#define GR_DRAW_OP_TEST_DEFINE(Op) \
    GrOp::Owner Op##__Test(...)
```

**示例**: `GR_DRAW_OP_TEST_DEFINE(CircleOp)` 生成 `CircleOp__Test` 函数。

**命名约定**: `__Test` 后缀避免与正常工厂函数冲突。

## 依赖关系

### 外部依赖
```cpp
#include "src/base/SkRandom.h"                        // 随机数生成器
#include "src/gpu/ganesh/GrUserStencilSettings.h"     // 模板设置
#include "include/private/gpu/ganesh/GrContext_Base.h" // 上下文基类
#include "src/gpu/ganesh/GrCaps.h"                    // GPU 能力
```

### 被依赖模块
- `src/gpu/ganesh/ops/*.cpp` - 各种操作的测试工厂实现
- `tests/OpTest.cpp` - 操作单元测试
- `tests/ProcessorTest.cpp` - 处理器测试

## 设计模式与设计决策

### 1. 宏驱动的代码生成
使用宏定义标准化测试工厂:

```cpp
GR_DRAW_OP_TEST_DEFINE(MyOp) {
    // 实现
}
```

**优势**:
- 统一函数签名
- 减少样板代码
- 易于维护

### 2. Friend 测试模式
测试工厂作为 friend 函数访问私有成员:

```cpp
GR_DRAW_OP_TEST_FRIEND(MyOp);
```

**优势**:
- 避免为测试增加公共 API
- 保持类接口简洁
- 测试代码与生产代码分离

### 3. 编译期条件化
使用 `#if defined(GPU_TEST_UTILS)` 完全排除测试代码:

```cpp
#if defined(GPU_TEST_UTILS)
// 测试代码
#endif
```

**优势**:
- 发布版本无额外开销
- 减小二进制大小
- 提高安全性(测试接口不暴露)

### 4. 静态预定义配置
使用 `constexpr` 定义测试配置:

```cpp
static constexpr GrUserStencilSettings kReads(...);
```

**优势**:
- 零运行时初始化开销
- 编译期错误检测
- 内存占用小

### 5. 随机化测试
使用 `SkRandom` 生成随机配置:

```cpp
random->nextULessThan(...)
```

**优势**:
- 覆盖多种参数组合
- 发现边界情况
- 自动化测试

## 性能考量

### 1. 仅测试编译
测试代码完全不包含在发布版本中:
- 零运行时开销
- 不影响二进制大小
- 不增加攻击面

### 2. 静态初始化
模板设置使用 `constexpr`:
- 编译期构造
- 无动态分配
- 数据段存储(共享内存)

### 3. 轻量级随机选择
使用数组索引而非复杂逻辑:

```cpp
return kStencilSettings[random->nextULessThan(4)];
```

O(1) 时间复杂度。

### 4. 避免冗余检查
硬件能力检查提前返回:

```cpp
if (context->priv().caps()->avoidStencilBuffers()) {
    return &GrUserStencilSettings::kUnused;
}
```

避免在不支持模板的硬件上生成无效设置。

## 相关文件

### 测试基础设施
- `src/base/SkRandom.h` - 随机数生成器
- `src/gpu/ganesh/GrUserStencilSettings.h` - 模板设置

### 操作实现
- `src/gpu/ganesh/ops/CircleOp.cpp` - 圆形操作测试工厂
- `src/gpu/ganesh/ops/RRectOp.cpp` - 圆角矩形操作测试工厂
- `src/gpu/ganesh/ops/PathInnerTriangulateOp.cpp` - 路径三角化操作测试工厂

### 测试用例
- `tests/OpTest.cpp` - 操作单元测试
- `tests/ProcessorTest.cpp` - 处理器测试
- `fuzz/FuzzCanvas.cpp` - 模糊测试

### 配置
- `BUILD.gn` - 定义 `GPU_TEST_UTILS` 编译标志
