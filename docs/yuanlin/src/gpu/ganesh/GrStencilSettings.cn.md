# GrStencilSettings

> 源文件
> - src/gpu/ganesh/GrStencilSettings.h
> - src/gpu/ganesh/GrStencilSettings.cpp

## 概述

`GrStencilSettings` 是 Ganesh GPU 后端中用于表示具体模板测试（stencil test）设置的类。它将用户级的模板设置（`GrUserStencilSettings`）转换为可以直接映射到硬件的具体配置，包括测试函数、操作、参考值和掩码。模板测试是 GPU 渲染管道中的关键功能，用于实现复杂的裁剪、阴影、轮廓等效果。

该类处理了模板裁剪（stencil clip）的集成、单面/双面模板测试的配置，以及将用户模板操作转换为硬件操作。它支持生成紧凑的缓存键，使得具有相同模板配置的绘制操作可以共享渲染管道状态。

## 架构位置

`GrStencilSettings` 位于 Ganesh 渲染管道配置层：

```
Skia 绘制流程
├── 用户绘制操作
│   └── GrUserStencilSettings (用户级模板设置)
│       └── GrStencilSettings (硬件级模板设置)
│           └── GrProgramInfo (渲染管道配置)
│               └── GrOpsRenderPass (渲染通道)
│                   └── GPU 硬件模板测试
```

转换流程：
```
GrUserStencilSettings + StencilClip + NumStencilBits
  └── GrStencilSettings::reset()
      └── 生成具体的硬件配置
```

## 主要类与结构体

### GrStencilSettings

表示具体的硬件模板测试设置。

**继承关系：**
- 无继承关系，值类型

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFlags` | `uint32_t` | 状态标志（禁用、单面、只读等） |
| `fCWFace` | `Face` | 顺时针面的模板设置 |
| `fCCWFace` | `Face` | 逆时针面的模板设置 |

### Face

嵌套结构体，表示单个面的模板测试配置。

**继承关系：**
- 继承自 `GrTStencilFaceSettings<GrStencilTest, GrStencilOp>`

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRef` | `uint16_t` | 参考值 |
| `fTest` | `GrStencilTest` | 测试函数（Always、Never、Equal 等） |
| `fTestMask` | `uint16_t` | 测试掩码 |
| `fPassOp` | `GrStencilOp` | 测试通过时的操作 |
| `fFailOp` | `GrStencilOp` | 测试失败时的操作 |
| `fWriteMask` | `uint16_t` | 写入掩码 |

**内存布局：** 紧凑打包为 10 字节，便于高效比较和键生成。

### 枚举类型

#### GrStencilTest

```cpp
enum class GrStencilTest : uint16_t {
    kAlways,    // 总是通过
    kNever,     // 总是失败
    kGreater,   // 大于参考值
    kGEqual,    // 大于等于参考值
    kLess,      // 小于参考值
    kLEqual,    // 小于等于参考值
    kEqual,     // 等于参考值
    kNotEqual   // 不等于参考值
};
```

#### GrStencilOp

```cpp
enum class GrStencilOp : uint8_t {
    kKeep,       // 保持当前值
    kZero,       // 设置为 0
    kReplace,    // 替换为参考值
    kInvert,     // 按位取反
    kIncWrap,    // 递增（回绕）
    kDecWrap,    // 递减（回绕）
    kIncClamp,   // 递增（钳位）
    kDecClamp    // 递减（钳位）
};
```

## 公共 API 函数

### 构造函数

```cpp
GrStencilSettings()  // 默认禁用模板测试
GrStencilSettings(const GrUserStencilSettings& user,
                  bool hasStencilClip,
                  int numStencilBits)
GrStencilSettings(const GrStencilSettings& that)
```

### 状态管理

```cpp
void invalidate()     // 标记为无效
void setDisabled()    // 禁用模板测试
void reset(const GrUserStencilSettings& user, bool hasStencilClip, int numStencilBits)
void reset(const GrStencilSettings& that)
```

### 状态查询

```cpp
bool isValid() const       // 是否有效
bool isDisabled() const    // 是否禁用
bool doesWrite() const     // 是否写入模板缓冲
bool isTwoSided() const    // 是否双面测试
bool usesWrapOp() const    // 是否使用回绕操作
```

### 面访问

```cpp
const Face& singleSidedFace() const
const Face& postOriginCWFace(GrSurfaceOrigin origin) const
const Face& postOriginCCWFace(GrSurfaceOrigin origin) const
```

根据表面原点和面朝向获取对应的模板设置。

### 键生成

```cpp
void genKey(skgpu::KeyBuilder* b, bool includeRefs) const
```

生成用于缓存和管道状态去重的键。

**参数：**
- `b`: 键构建器
- `includeRefsAndMasks`: 是否包含参考值和掩码（某些情况下可以忽略以提高缓存命中率）

### 比较运算符

```cpp
bool operator==(const GrStencilSettings& that) const
bool operator!=(const GrStencilSettings& that) const
```

### 静态工具函数

```cpp
static const GrUserStencilSettings* SetClipBitSettings(bool setToInside)
```

返回用于直接设置裁剪位的用户模板设置。

## 内部实现细节

### 用户设置到硬件设置的转换

`reset` 方法执行复杂的转换逻辑：

```cpp
void GrStencilSettings::reset(const GrUserStencilSettings& user,
                              bool hasStencilClip,
                              int numStencilBits) {
    uint16_t cwFlags = user.fCWFlags[hasStencilClip];

    // 处理单面情况
    if (cwFlags & kSingleSided_StencilFlag) {
        fFlags = cwFlags;
        if (!this->isDisabled()) {
            fCWFace.reset(user.fCWFace, hasStencilClip, numStencilBits);
        }
        return;
    }

    // 处理双面情况
    uint16_t ccwFlags = user.fCCWFlags[hasStencilClip];
    fFlags = cwFlags & ccwFlags;  // 取公共标志

    if (!this->isDisabled()) {
        if (!(cwFlags & kDisabled_StencilFlag)) {
            fCWFace.reset(user.fCWFace, hasStencilClip, numStencilBits);
        }
        if (!(ccwFlags & kDisabled_StencilFlag)) {
            fCCWFace.reset(user.fCCWFace, hasStencilClip, numStencilBits);
        }
    }
}
```

### Face 的转换逻辑

`Face::reset` 处理裁剪位和用户位的组合：

```cpp
void GrStencilSettings::Face::reset(const GrUserStencilSettings::Face& user,
                                    bool hasStencilClip,
                                    int numStencilBits) {
    int clipBit = 1 << (numStencilBits - 1);  // 最高位用作裁剪位
    int userMask = clipBit - 1;               // 低位用作用户位

    // 根据操作类型确定写入掩码
    GrUserStencilOp maxOp = std::max(user.fPassOp, user.fFailOp);
    if (maxOp <= kLastUserOnlyStencilOp) {
        fWriteMask = user.fWriteMask & userMask;  // 仅用户位
    } else if (maxOp <= kLastClipOnlyStencilOp) {
        fWriteMask = clipBit;  // 仅裁剪位
    } else {
        fWriteMask = clipBit | (user.fWriteMask & userMask);  // 两者都有
    }

    // 转换操作
    fFailOp = gUserStencilOpToRaw[(int)user.fFailOp];
    fPassOp = gUserStencilOpToRaw[(int)user.fPassOp];

    // 处理测试函数和掩码
    if (!hasStencilClip || user.fTest > kLastClippedStencilTest) {
        fTestMask = user.fTestMask & userMask;  // 忽略裁剪
        fTest = gUserStencilTestToRaw[(int)user.fTest];
    } else if (GrUserStencilTest::kAlwaysIfInClip != user.fTest) {
        fTestMask = clipBit | (user.fTestMask & userMask);  // 包含裁剪
        fTest = gUserStencilTestToRaw[(int)user.fTest];
    } else {
        fTestMask = clipBit;  // 仅测试裁剪位
        fTest = GrStencilTest::kEqual;
    }

    // 设置参考值
    fRef = (clipBit | user.fRef) & (fTestMask | fWriteMask);
}
```

**关键点：**
- 模板缓冲的最高位用作裁剪位
- 低位用作用户自定义的模板位
- 根据操作类型动态调整掩码

### 用户操作到硬件操作的映射

```cpp
static constexpr GrStencilOp gUserStencilOpToRaw[kGrUserStencilOpCount] = {
    GrStencilOp::kKeep,      // kKeep
    GrStencilOp::kZero,      // kZero (用户位)
    GrStencilOp::kReplace,   // kReplace (用户位)
    GrStencilOp::kInvert,    // kInvert (用户位)
    GrStencilOp::kIncWrap,   // kIncWrap
    GrStencilOp::kDecWrap,   // kDecWrap
    GrStencilOp::kIncClamp,  // kIncMaybeClamp
    GrStencilOp::kDecClamp,  // kDecMaybeClamp
    GrStencilOp::kZero,      // kZeroClipBit
    GrStencilOp::kReplace,   // kSetClipBit
    GrStencilOp::kInvert,    // kInvertClipBit
    GrStencilOp::kReplace,   // kSetClipAndReplaceUserBits
    GrStencilOp::kZero       // kZeroClipAndUserBits
};
```

### 相等性比较

使用 `memcmp` 进行高效的二进制比较：

```cpp
bool GrStencilSettings::operator==(const GrStencilSettings& that) const {
    // 处理无效和禁用情况
    if ((kInvalid_PrivateFlag | kDisabled_StencilFlag) & (fFlags | that.fFlags)) {
        // ...
    }

    // 单面比较
    if (kSingleSided_StencilFlag & (fFlags & that.fFlags)) {
        return 0 == memcmp(&fCWFace, &that.fCWFace, sizeof(Face));
    }

    // 双面比较
    return 0 == memcmp(&fCWFace, &that.fCWFace, 2 * sizeof(Face));
}
```

利用 `Face` 的紧凑布局（10 字节，无填充），直接进行内存比较。

### 键生成

```cpp
void GrStencilSettings::genKey(skgpu::KeyBuilder* b, bool includeRefs) const {
    b->addBits(6, fFlags, "stencilFlags");
    if (this->isDisabled()) {
        return;
    }

    if (!this->isTwoSided()) {
        if (includeRefs) {
            b->addBytes(sizeof(Face), &fCWFace, "stencilCWFace");
        } else {
            Face tempFace = fCWFace;
            tempFace.fRef = 0;  // 清零参考值
            b->addBytes(sizeof(Face), &tempFace, "stencilCWFace");
        }
    } else {
        // 双面情况类似
    }
}
```

**优化：** 可选地排除参考值，因为在某些情况下参考值不影响渲染结果（如总是通过的测试）。

## 依赖关系

### 依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| `GrUserStencilSettings` | 转换源 | 用户级模板设置 |
| `skgpu::KeyBuilder` | 工具 | 键生成工具 |
| `GrTypesPriv.h` | 类型定义 | 定义 GrStencilFlags |
| `GrSurfaceOrigin` | 参数 | 表面原点枚举 |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|------|---------|------|
| `GrProgramInfo` | 配置 | 渲染管道信息包含模板设置 |
| `GrOpsRenderPass` | 执行 | 渲染通道应用模板设置 |
| `GrGpu` | 硬件配置 | GPU 实现将设置应用到硬件 |
| 各后端实现 | 转换 | OpenGL/Vulkan/Metal 转换为 API 调用 |

## 设计模式与设计决策

### 分层设计

用户层 → 中间层 → 硬件层：
- **GrUserStencilSettings**: 用户意图（如 "绘制到裁剪区域内"）
- **GrStencilSettings**: 硬件配置（具体的测试函数和掩码）
- **后端 API 调用**: OpenGL 的 `glStencilFunc` 等

### 裁剪位分离

使用模板缓冲的最高位作为裁剪位：
- **优势**：裁剪和用户模板功能可以共存
- **实现**：通过掩码操作隔离裁剪位和用户位
- **灵活性**：支持复杂的裁剪 + 用户模板组合

### 双面模板支持

分别配置顺时针和逆时针面：
- 支持渲染阴影体积等算法
- 根据表面原点动态选择面配置
- 可以优化为单面以减少状态切换

### 紧凑内存布局

`Face` 结构体精确控制内存布局：
```cpp
static_assert(0 == offsetof(Face, fRef));
static_assert(2 == sizeof(Face::fRef));
static_assert(2 == offsetof(Face, fTest));
static_assert(2 == sizeof(Face::fTest));
// ... 总共 10 字节，无填充
```

**优势：**
- 高效的 `memcmp` 比较
- 紧凑的键生成
- 减少缓存未命中

### 状态标志优化

使用位标志而非布尔值：
```cpp
enum GrStencilFlags {
    kDisabled_StencilFlag         = 0x1,
    kNoModifyStencil_StencilFlag  = 0x2,
    kSingleSided_StencilFlag      = 0x4,
    kNoWrapOps_StencilFlag        = 0x8,
    // ...
};
```

**优势：**
- 快速的状态查询（位测试）
- 紧凑的存储（多个标志用一个整数）
- 便于键生成（直接包含标志位）

## 性能考量

### 内存比较优化

使用 `memcmp` 而非逐字段比较：
- **前提**：结构体紧凑打包，无填充字节
- **性能**：单次 `memcmp` 比多次字段比较快
- **安全性**：通过 `static_assert` 确保布局正确

### 键生成效率

直接拷贝 `Face` 结构体字节到键：
```cpp
b->addBytes(sizeof(Face), &fCWFace, "stencilCWFace");
```

避免了逐字段序列化的开销。

### 可选参考值

`genKey` 的 `includeRefs` 参数允许排除参考值：
- 对于某些测试函数（如 `kAlways`），参考值不影响结果
- 排除参考值可以提高缓存命中率
- 需要调用者根据实际情况决定

### 用户设置缓存

`GrUserStencilSettings` 通常为静态常量：
```cpp
static constexpr GrUserStencilSettings gZeroStencilClipBit(...);
```

避免重复构造，`GrStencilSettings` 从缓存的用户设置转换。

### 操作映射表

使用静态 `constexpr` 数组映射用户操作到硬件操作：
- 编译时初始化，无运行时开销
- O(1) 查找复杂度
- 类型安全（枚举索引）

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrUserStencilSettings.h` | 转换源 | 用户级模板设置 |
| `include/gpu/ganesh/GrTypes.h` | 类型定义 | 表面原点等公共类型 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 类型定义 | GrStencilFlags 等私有类型 |
| `src/gpu/KeyBuilder.h` | 工具 | 键生成辅助类 |
| `src/gpu/ganesh/GrProgramInfo.h` | 使用者 | 渲染管道配置 |
| `src/gpu/ganesh/GrOpsRenderPass.h` | 使用者 | 渲染通道 |
| `src/gpu/ganesh/GrGpu.h` | 使用者 | GPU 抽象接口 |
| `src/gpu/ganesh/gl/GrGLGpu.cpp` | 后端实现 | OpenGL 模板设置应用 |
| `src/gpu/ganesh/vk/GrVkGpu.cpp` | 后端实现 | Vulkan 模板设置应用 |
