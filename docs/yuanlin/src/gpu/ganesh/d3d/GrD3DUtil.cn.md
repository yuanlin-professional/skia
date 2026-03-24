# GrD3DUtil

> 源文件
> - `src/gpu/ganesh/d3d/GrD3DUtil.h`
> - `src/gpu/ganesh/d3d/GrD3DUtil.cpp`

## 概述

`GrD3DUtil` 是 Skia 图形库 Direct3D 12 后端的实用工具模块,提供了一系列用于 DXGI 格式处理、错误检查、字符串转换等功能的辅助函数和宏定义。该模块作为 D3D12 后端的公共工具库,被其他 D3D12 相关类广泛使用。

该文件包含了 DXGI 格式的元数据查询函数(通道信息、字节大小、模板位等)、格式字符串转换、多字节到宽字符转换,以及 D3D12 API 调用的错误检查宏,是 D3D12 后端实现中不可或缺的基础设施。

## 架构位置

```
Skia GPU Backend (Ganesh)
└── Direct3D 12 后端
    ├── GrD3DUtil (当前模块 - 工具函数集)
    ├── GrD3DGpu (使用工具函数)
    ├── GrD3DTexture (使用格式查询)
    ├── GrD3DRenderTarget (使用格式信息)
    └── 其他 D3D12 模块
```

该模块是横切关注点,为整个 D3D12 后端提供支撑功能。

## 主要类与结构体

该模块不包含类定义,仅提供自由函数和宏:

### 宏定义

**GR_D3D_CALL_ERRCHECK**
```cpp
#define GR_D3D_CALL_ERRCHECK(X)
```
用于包装 D3D12 API 调用,自动检查 `HRESULT` 返回值并在失败时输出错误信息。

### 运算符重载

```cpp
static constexpr bool operator==(const D3D12_CPU_DESCRIPTOR_HANDLE& first,
                                 const D3D12_CPU_DESCRIPTOR_HANDLE& second);
```
为 CPU 描述符句柄提供相等性比较,基于 `ptr` 成员进行比较。

## 公共 API 函数

### 格式压缩查询

```cpp
bool GrDxgiFormatIsCompressed(DXGI_FORMAT format);
```

判断 DXGI 格式是否为压缩纹理格式。

**支持的压缩格式:**
- `DXGI_FORMAT_BC1_UNORM` (DXT1)

### 格式通道信息

```cpp
static constexpr uint32_t GrDxgiFormatChannels(DXGI_FORMAT format);
```

返回格式包含的颜色通道标志位(红、绿、蓝、透明)。

**返回值类型:**
- `kRed_SkColorChannelFlag` - 单红色通道
- `kRG_SkColorChannelFlags` - 红绿通道
- `kRGB_SkColorChannelFlags` - RGB 通道
- `kRGBA_SkColorChannelFlags` - RGBA 通道
- `0` - 无颜色通道(如深度模板格式)

### 格式描述符

```cpp
static constexpr GrColorFormatDesc GrDxgiFormatDesc(DXGI_FORMAT format);
```

返回详细的格式描述,包括每个通道的位数和编码类型。

**编码类型:**
- `kUnorm` - 无符号归一化 [0, 1]
- `kFloat` - 浮点数
- `kSRGBUnorm` - sRGB 色彩空间的归一化值

### 格式字节大小

```cpp
static constexpr size_t GrDxgiFormatBytesPerBlock(DXGI_FORMAT format);
```

返回每个像素块的字节数。对于非压缩格式,等于每像素字节数;对于压缩格式(如 BC1),返回 4x4 块的字节数。

### 模板位数查询

```cpp
static constexpr int GrDxgiFormatStencilBits(DXGI_FORMAT format);
```

返回深度模板格式中的模板位数。

**支持的格式:**
- `DXGI_FORMAT_D24_UNORM_S8_UINT` - 8 位模板
- `DXGI_FORMAT_D32_FLOAT_S8X24_UINT` - 8 位模板

### 格式字符串转换

```cpp
static constexpr const char* GrDxgiFormatToStr(DXGI_FORMAT dxgiFormat);
```

将 DXGI 格式枚举转换为可读的字符串表示,仅在调试模式或测试环境中可用。

### 字符串编码转换

```cpp
std::wstring GrD3DMultiByteToWide(const std::string& str);
```

将 UTF-8 多字节字符串转换为 Windows 宽字符字符串,用于 D3D12 API 调用(如设置调试名称)。

## 内部实现细节

### 错误检查宏实现

```cpp
GR_D3D_CALL_ERRCHECK(X)
```

宏展开为:
1. 执行 D3D12 API 调用并存储 `HRESULT`
2. 断言结果成功(`SkASSERT(SUCCEEDED(result))`)
3. 在发布版本中,失败时输出十六进制错误代码
4. 使用 do-while(false) 包装确保单语句语义

**使用示例:**
```cpp
GR_D3D_CALL_ERRCHECK(device->CreateFence(0, D3D12_FENCE_FLAG_NONE, IID_PPV_ARGS(&fence)));
```

### 支持的 DXGI 格式

该模块支持以下 DXGI 格式类别:

**8 位归一化格式:**
- `R8_UNORM`, `R8G8_UNORM`, `R8G8B8A8_UNORM`, `R8G8B8A8_UNORM_SRGB`
- `B8G8R8A8_UNORM`

**16 位格式:**
- `R16_UNORM`, `R16G16_UNORM`, `R16G16B16A16_UNORM` (归一化)
- `R16_FLOAT`, `R16G16_FLOAT`, `R16G16B16A16_FLOAT` (浮点)

**特殊格式:**
- `B5G6R5_UNORM` - 5:6:5 打包格式
- `B4G4R4A4_UNORM` - 4:4:4:4 打包格式
- `R10G10B10A2_UNORM` - 10:10:10:2 打包格式
- `R32G32B32A32_FLOAT` - 高精度浮点

**压缩格式:**
- `BC1_UNORM` - DXT1 压缩

**深度模板格式:**
- `D24_UNORM_S8_UINT` - 24 位深度 + 8 位模板
- `D32_FLOAT_S8X24_UINT` - 32 位浮点深度 + 8 位模板

### UTF-8 到宽字符转换

`GrD3DMultiByteToWide` 使用 Windows API:
1. **第一次调用**: `MultiByteToWideChar` 计算所需宽字符数
2. **分配缓冲区**: 创建适当大小的 `std::wstring`
3. **第二次调用**: 执行实际转换填充缓冲区

**参数:**
- `CP_UTF8` - 输入编码为 UTF-8
- 输出为 UTF-16(Windows 宽字符标准)

### constexpr 函数优化

大多数查询函数声明为 `constexpr`:
- 编译时计算,零运行时开销
- 支持在常量表达式中使用
- 生成最优化的查表代码

### 不完整的格式支持

某些函数对未知格式返回默认值:
- `GrDxgiFormatChannels` - 返回 0
- `GrDxgiFormatBytesPerBlock` - 返回 0
- `GrDxgiFormatStencilBits` - 返回 0
- `GrDxgiFormatToStr` - 返回 "Unknown"

这提供了防御性的默认行为。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrD3DTypes` | D3D12 基础类型定义 |
| `GrTypes` | Ganesh 通用类型 |
| `GrTypesPriv` | Ganesh 私有类型(如 `GrColorFormatDesc`) |
| `SkImage` | 图像类型定义 |
| Windows API | `MultiByteToWideChar` 函数 |
| `<string>` | 标准字符串类型 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrD3DGpu` | 使用错误检查宏和格式查询 |
| `GrD3DTexture` | 查询格式是否压缩 |
| `GrD3DRenderTarget` | 查询格式通道和字节信息 |
| `GrD3DPipelineState` | 使用格式描述符 |
| `GrD3DCaps` | 检查格式能力 |
| 所有 D3D12 模块 | 使用错误检查和工具函数 |

## 设计模式与设计决策

### 头文件工具库模式

将常用工具集中在单一头文件:
- 减少重复代码
- 统一格式处理逻辑
- 便于维护和更新

### constexpr 查表

使用 constexpr switch-case 而非数据结构:
- 编译时优化为跳转表或常量
- 不占用运行时内存
- 类型安全的编译时检查

### 宏 vs 内联函数

使用宏而非内联函数进行错误检查:
- **优点**: 可以捕获调用点的上下文(表达式文本)
- **缺点**: 缺少类型安全
- **权衡**: 在简单的 HRESULT 检查场景中可接受

### 防御性默认值

未知格式返回安全的默认值:
- 通道数: 0 (无颜色)
- 字节数: 0 (避免内存计算错误)
- 字符串: "Unknown"

防止级联错误并提供调试线索。

### 分离的字符串转换

格式字符串转换仅在调试/测试中编译:
```cpp
#if defined(SK_DEBUG) || defined(GPU_TEST_UTILS)
```
避免在发布版本中包含不必要的字符串常量。

## 性能考量

### 编译时计算

所有格式查询函数都是 `constexpr`:
- 编译器可以在编译时计算结果
- 生成最优化的机器码
- 可能内联为单个指令(如常量加载)

### 零运行时开销抽象

通过内联和 constexpr:
- 函数调用开销为零
- 不需要查找表或间接访问
- 与手写 switch-case 性能相同

### 描述符句柄比较

CPU 描述符句柄的相等性比较:
```cpp
return first.ptr == second.ptr;
```
仅比较指针值,这是一个简单的整数比较,非常高效。

### 字符串转换性能

`GrD3DMultiByteToWide` 需要两次 API 调用:
- 第一次计算所需大小
- 第二次执行转换
- 这是 Windows API 的标准模式,无法避免
- 通常仅用于调试标签设置,不在热路径上

### Switch-Case 优化

现代编译器对 constexpr switch-case 的优化:
- 小范围: 编译为跳转表(O(1) 查找)
- 大范围: 编译为二分查找或哈希表
- 对于该模块的格式数量,通常生成跳转表

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 依赖 | D3D12 基础类型定义 |
| `include/gpu/ganesh/GrTypes.h` | 依赖 | Ganesh 通用类型 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | 私有类型如 `GrColorFormatDesc` |
| `include/core/SkImage.h` | 依赖 | 图像类型 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h` | 被使用 | GPU 实现使用工具函数 |
| `src/gpu/ganesh/d3d/GrD3DTexture.h` | 被使用 | 纹理使用格式查询 |
| `src/gpu/ganesh/d3d/GrD3DRenderTarget.h` | 被使用 | 渲染目标使用格式信息 |
| `src/gpu/ganesh/d3d/GrD3DCaps.h` | 被使用 | 能力检测使用格式查询 |
| `src/gpu/ganesh/GrDataUtils.h` | 依赖 | 数据处理工具 |
| `src/gpu/ganesh/GrDirectContextPriv.h` | 依赖 | 上下文私有接口 |
| `src/sksl/SkSLCompiler.h` | 依赖 | SkSL 编译器 |

## 设计模式与设计决策

### 实用工具模式

采用实用工具类的设计:
- 所有函数都是静态的或自由函数
- 不包含状态或成员变量
- 纯函数式接口,易于测试和理解

### 条件编译

格式字符串转换函数使用条件编译:
- 仅在需要时包含(调试和测试)
- 减少发布版本的代码大小
- 避免不必要的字符串常量

### 内联友好设计

所有查询函数定义在头文件中:
- 支持跨编译单元的内联优化
- 编译器可以看到完整实现进行优化
- 对于简单的查表操作非常合适

### 格式覆盖策略

选择性支持 DXGI 格式:
- 仅包含 Skia 实际使用的格式
- 避免维护不必要的格式数据
- 未知格式返回安全默认值

### 错误处理哲学

`GR_D3D_CALL_ERRCHECK` 的设计:
- 调试版本断言失败(快速失败)
- 发布版本记录错误并继续(容错性)
- 平衡了开发时的严格性和生产环境的健壮性

### constexpr 优先

优先使用 constexpr 而非运行时计算:
- 将工作从运行时转移到编译时
- 生成更小、更快的代码
- 支持编译时验证

## 性能考量

### 编译时格式验证

constexpr 函数允许编译时验证:
```cpp
static_assert(GrDxgiFormatBytesPerBlock(DXGI_FORMAT_R8G8B8A8_UNORM) == 4);
```
错误可以在编译时发现。

### 内联消除

对于简单的格式查询,编译器通常能将整个函数调用优化为单个常量:
```cpp
size_t bytes = GrDxgiFormatBytesPerBlock(DXGI_FORMAT_R8G8B8A8_UNORM);
// 优化为: size_t bytes = 4;
```

### 跳转表生成

Switch-case 语句在现代编译器中高效:
- 格式枚举值通常是连续或稀疏连续的
- 编译器生成优化的跳转表
- 访问时间接近 O(1)

### 字符串转换缓存

`GrD3DMultiByteToWide` 不进行缓存:
- 主要用于设置调试标签(低频操作)
- 缓存的复杂性不值得
- 简单实现更易维护

### 最小化头文件依赖

工具函数避免引入重量级依赖:
- 主要依赖标准库和 D3D12 头文件
- 减少编译时间
- 降低模块间耦合

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 依赖 | DXGI 格式和 D3D12 类型 |
| `include/gpu/ganesh/GrTypes.h` | 依赖 | Ganesh 类型系统 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | `GrColorFormatDesc` 等私有类型 |
| `src/gpu/ganesh/d3d/GrD3DGpu.cpp` | 被使用 | 使用错误检查宏 |
| `src/gpu/ganesh/d3d/GrD3DTexture.cpp` | 被使用 | 检查压缩格式和转换字符串 |
| `src/gpu/ganesh/d3d/GrD3DCaps.cpp` | 被使用 | 格式能力检测 |
| `src/gpu/ganesh/GrDataUtils.h` | 依赖 | 数据处理实用工具 |
