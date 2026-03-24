# GrUserStencilSettings — 用户模板缓冲区设置

> 源文件: `src/gpu/ganesh/GrUserStencilSettings.h`

## 概述

`GrUserStencilSettings` 是 Ganesh GPU 渲染管线中用于描述绘制操作如何使用模板缓冲区 (stencil buffer) 的编译时常量结构体。它以抽象的方式表达模板测试和操作，并在管线最终化时被翻译为具体的 GPU 状态。该文件同时定义了模板测试枚举 (`GrUserStencilTest`)、模板操作枚举 (`GrUserStencilOp`)、模板标志 (`GrStencilFlags`) 以及面设置模板 (`GrTStencilFaceSettings`)。

Ganesh 使用模板缓冲区实现复杂裁剪 (clipping)，将模板位分为"裁剪位"和"用户位"两部分。客户端代码只能操作用户位，并且必须在使用完毕后将其清零。

## 架构位置

```
OpsTask (裁剪管理)
    └── GrPipeline (渲染管线)
        └── GrStencilSettings (具体模板设置)
            └── GrUserStencilSettings (本文件 - 抽象模板配置)
                ├── GrUserStencilTest (测试函数)
                ├── GrUserStencilOp (模板操作)
                └── GrStencilFlags (优化标志)
```

`GrUserStencilSettings` 是编译时描述层；`GrStencilSettings` 是运行时在管线最终化时根据实际裁剪状态生成的具体设置。

## 主要类与结构体

### GrStencilFlags 枚举

| 标志 | 值 | 描述 |
|------|----|------|
| `kDisabled_StencilFlag` | `1<<0` | 模板操作完全禁用 |
| `kTestAlwaysPasses_StencilFlag` | `1<<1` | 模板测试总是通过 |
| `kNoModifyStencil_StencilFlag` | `1<<2` | 不修改模板缓冲区 |
| `kNoWrapOps_StencilFlag` | `1<<3` | 不使用环绕操作 |
| `kSingleSided_StencilFlag` | `1<<4` | 单面模板（CW/CCW 相同） |

### GrTStencilFaceSettings<TTest, TOp>

模板化的面设置结构体：

| 成员 | 类型 | 描述 |
|------|------|------|
| `fRef` | `uint16_t` | 模板测试和操作的参考值 |
| `fTest` | `TTest` | 模板测试函数（fRef 在左侧） |
| `fTestMask` | `uint16_t` | 测试前对 fRef 和模板值进行按位与的掩码 |
| `fPassOp` | `TOp` | 测试通过时执行的操作 |
| `fFailOp` | `TOp` | 测试失败时执行的操作 |
| `fWriteMask` | `uint16_t` | 指示哪些模板位可以被更新 |

### GrUserStencilTest 枚举

分为两类：

**尊重裁剪位的测试**（当无裁剪时忽略 "IfInClip" 条件）：
- `kAlwaysIfInClip` — 在裁剪区域内总是通过
- `kEqualIfInClip` — 在裁剪区域内相等则通过
- `kLessIfInClip` — 在裁剪区域内小于则通过
- `kLEqualIfInClip` — 在裁剪区域内小于等于则通过

**忽略裁剪位的测试**：
- `kAlways`, `kNever`, `kGreater`, `kGEqual`, `kLess`, `kLEqual`, `kEqual`, `kNotEqual`

### GrUserStencilOp 枚举

分为三类：

**仅修改用户位**：`kKeep`, `kZero`, `kReplace`, `kInvert`, `kIncWrap`, `kDecWrap`, `kIncMaybeClamp`, `kDecMaybeClamp`

**仅修改裁剪位**：`kZeroClipBit`, `kSetClipBit`, `kInvertClipBit`

**同时修改裁剪和用户位**：`kSetClipAndReplaceUserBits`, `kZeroClipAndUserBits`

### GrUserStencilSettings 结构体

核心结构体，包含成员：

| 成员 | 类型 | 描述 |
|------|------|------|
| `fCWFlags[2]` | `uint16_t[2]` | 顺时针面标志，索引 0 为无裁剪，索引 1 为有裁剪 |
| `fCWFace` | `Face` | 顺时针面的模板设置 |
| `fCCWFlags[2]` | `uint16_t[2]` | 逆时针面标志 |
| `fCCWFace` | `Face` | 逆时针面的模板设置 |

## 公共 API 函数

### 静态工厂方法

```cpp
template<...> constexpr static Init<...> StaticInit();
template<...> constexpr static InitSeparate<...> StaticInitSeparate();
```

返回用于构造函数的标签类型，强制编译时常量初始化。`StaticInit` 用于单面设置，`StaticInitSeparate` 用于双面设置。

### 构造函数

```cpp
template<...> constexpr explicit GrUserStencilSettings(const Init<...>&);
template<...> constexpr explicit GrUserStencilSettings(const InitSeparate<...>&);
```

仅接受模板参数标签类型构造。`Init` 版本为两面设置相同参数并标记为单面；`InitSeparate` 版本为 CW/CCW 面设置独立参数。

### 查询方法

| 方法 | 描述 |
|------|------|
| `flags(bool hasStencilClip)` | 返回 CW 和 CCW 标志的交集 |
| `isDisabled(bool hasStencilClip)` | 模板操作是否完全禁用 |
| `testAlwaysPasses(bool hasStencilClip)` | 测试是否总是通过 |
| `isTwoSided(bool hasStencilClip)` | 是否为双面模板 |
| `usesWrapOp(bool hasStencilClip)` | 是否使用环绕操作 |
| `isUnused()` | 是否为静态 `kUnused` 哨兵实例 |

## 内部实现细节

### Attrs 模板特化

`Attrs<Test, PassOp, FailOp>` 是编译时属性计算器，通过 `static_assert` 和 `constexpr` 函数实现：

1. **操作配对验证**: 通过 `static_assert` 确保：
   - 仅修改用户位的操作不与仅修改裁剪位的操作配对
   - 仅修改裁剪位的操作不与同时修改裁剪和用户位的操作配对

2. **编译时标志计算**:
   - `TestAlwaysPasses()`: 判断测试是否总通过（考虑裁剪状态）
   - `DoesNotModifyStencil()`: 判断是否不修改模板缓冲区
   - `IsDisabled()`: 测试总通过且不修改 = 禁用
   - `UsesWrapOps()`: 是否包含 IncWrap/DecWrap 操作
   - `TestIgnoresRef()`: Always/Never 测试不需要参考值

3. **有效掩码优化**:
   - `EffectiveTestMask()`: 若测试忽略参考值，掩码归零
   - `EffectiveWriteMask()`: 若不修改模板，写掩码归零

### 裁剪位与用户位分离

标志数组 `fCWFlags[2]` / `fCCWFlags[2]` 以 `hasStencilClip` 布尔值为索引，允许同一设置在有裁剪和无裁剪时表现不同。例如 `kAlwaysIfInClip` 在无裁剪时退化为 `kAlways`。

### 构造限制

默认构造和拷贝构造均被 `delete`，强制只能通过模板 `Init`/`InitSeparate` 标签构造，确保所有实例都是编译时常量。

## 依赖关系

- **`include/gpu/ganesh/GrTypes.h`**: 基本 Ganesh 类型

## 设计模式与设计决策

1. **编译时常量设计**: 通过模板参数传递所有配置值，利用 `constexpr` 构造函数和 `static_assert`，确保模板设置在编译时完全确定和验证。这消除了运行时配置错误的可能性。

2. **标签分发 (Tag Dispatch)**: `Init` 和 `InitSeparate` 空结构体作为标签类型，是将模板参数传递给构造函数的唯一方式，因为 C++ 不支持直接为构造函数指定模板参数。

3. **两阶段翻译**: 用户级抽象设置 (`GrUserStencilSettings`) 在管线最终化时根据实际裁剪状态被翻译为具体的 GPU 模板状态，将抽象描述与具体实现分离。

4. **裁剪感知设计**: 测试枚举中的 "IfInClip" 变体使得同一设置可以在有裁剪和无裁剪场景下自动适配，避免维护两套配置。

5. **操作分类安全**: 将操作分为用户位操作、裁剪位操作和混合操作三类，通过 `static_assert` 在编译时防止不兼容的操作配对。

## 性能考量

- **零运行时开销构造**: 所有构造和标志计算在编译时完成，运行时只有成员访问和简单位操作。
- **标志预计算**: `fCWFlags`/`fCCWFlags` 在构造时预计算好两种裁剪状态下的标志，查询时只需一次数组索引和位与操作。
- **有效掩码优化**: 当测试或操作被编译时证明为无效时，对应的掩码归零，允许 GPU 驱动层进一步优化。
- **单面优化**: 单面设置通过 `kSingleSided_StencilFlag` 标记，允许后端省略逆时针面的状态设置。
- **环绕操作标记**: `kNoWrapOps_StencilFlag` 帮助后端判断是否需要配置模板环绕行为，某些 GPU 上环绕操作比钳位操作更昂贵。

## 相关文件

- `src/gpu/ganesh/GrStencilSettings.h` — 运行时具体模板设置
- `src/gpu/ganesh/GrPipeline.h` — 渲染管线，使用模板设置
- `src/gpu/ganesh/GrOpsTask.h` — 操作任务，管理裁剪和模板缓冲区
- `src/gpu/ganesh/ops/StencilMaskHelper.h` — 模板裁剪辅助工具
- `src/gpu/ganesh/PathRenderer.h` — 路径渲染器，大量使用模板设置
