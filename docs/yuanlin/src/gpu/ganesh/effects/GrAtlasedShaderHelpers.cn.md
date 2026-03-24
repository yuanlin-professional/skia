# GrAtlasedShaderHelpers

> 源文件
> - `src/gpu/ganesh/effects/GrAtlasedShaderHelpers.h`

## 概述

`GrAtlasedShaderHelpers` 是 Skia 图形库中用于生成纹理图集(Texture Atlas)着色器代码的辅助函数集合。该模块提供了内联函数用于生成 GLSL/HLSL 着色器代码,处理从打包的坐标中提取纹理索引、计算归一化 UV 坐标、以及执行多纹理查找等操作。

纹理图集是一种将多个小纹理合并到单一大纹理中的技术,广泛用于文本渲染、精灵渲染和 UI 元素绘制。该模块通过生成高效的着色器代码,支持在单次绘制调用中访问图集中的多个区域,并处理跨多个图集页的情况。

## 架构位置

```
Skia GPU Backend (Ganesh)
└── 着色器效果层
    ├── GrGeometryProcessor (几何处理器)
    ├── GrFragmentProcessor (片段处理器)
    └── 着色器辅助工具
        └── GrAtlasedShaderHelpers (当前模块)
            ├── 纹理坐标解包
            ├── 多纹理查找
            └── SDF LCD 特殊处理
```

该模块是着色器代码生成的实用工具层,被各种几何处理器(如文本渲染处理器)使用。

## 主要类与结构体

该模块不包含类定义,仅提供三个内联辅助函数:

### append_index_uv_varyings

生成顶点着色器代码,从打包的坐标中提取纹理索引和 UV 坐标。

### append_multitexture_lookup

生成片段着色器代码,根据纹理索引执行条件纹理查找。

### append_multitexture_lookup_lcd

为 SDF(有向距离场)LCD 文本渲染生成特殊的多纹理查找代码。

## 公共 API 函数

### 索引和 UV 变量生成

```cpp
static inline void append_index_uv_varyings(
    GrGeometryProcessor::ProgramImpl::EmitArgs& args,
    int numTextureSamplers,
    const char* inTexCoordsName,
    const char* atlasDimensionsInvName,
    GrGLSLVarying* uv,
    GrGLSLVarying* texIdx,
    GrGLSLVarying* st);
```

在顶点着色器中生成代码,处理打包的纹理坐标。

**参数说明:**
- `args` - 着色器生成上下文,包含构建器和能力
- `numTextureSamplers` - 图集页数量
- `inTexCoordsName` - 输入的打包坐标变量名
- `atlasDimensionsInvName` - 图集尺寸倒数的 uniform 变量名
- `uv` - 输出的归一化 UV 坐标 varying
- `texIdx` - 输出的纹理索引 varying
- `st` - 可选的整数纹理坐标 varying

**坐标打包格式:**
- X 坐标的第 13-14 位: 纹理页索引(0-3,支持最多 4 个页)
- X 坐标的第 0-12 位: X 纹理坐标(0-8191)
- Y 坐标: 完整的 Y 纹理坐标

**注意:** 不使用第 14-15 位是因为 iPhone 6 在 GLES 模式下对这些位有问题。

### 多纹理查找

```cpp
static inline void append_multitexture_lookup(
    GrGeometryProcessor::ProgramImpl::EmitArgs& args,
    int numTextureSamplers,
    const GrGLSLVarying& texIdx,
    const char* coordName,
    const char* colorName);
```

在片段着色器中生成条件纹理查找代码。

**生成的代码结构:**
```glsl
if (texIdx == 0) { color = texture(sampler0, coord); }
else if (texIdx == 1) { color = texture(sampler1, coord); }
else if (texIdx == 2) { color = texture(sampler2, coord); }
else { color = texture(sampler3, coord); }
```

**边界情况:** 如果 `numTextureSamplers <= 0`,返回白色 `(1,1,1,1)` 避免崩溃。

### SDF LCD 多纹理查找

```cpp
static inline void append_multitexture_lookup_lcd(
    GrGeometryProcessor::ProgramImpl::EmitArgs& args,
    int numTextureSamplers,
    const GrGLSLVarying& texIdx,
    const char* coordName,
    const char* offsetName,
    const char* distanceName);
```

为 LCD 子像素渲染的 SDF 文本生成特殊的三次查找代码。

**输出 `distanceName` 的三个分量:**
- **`.x` (红色)**: 左偏移位置的距离
- **`.y` (绿色)**: 中心位置的距离
- **`.z` (蓝色)**: 右偏移位置的距离

这三个距离值用于实现 LCD 子像素抗锯齿效果。

## 内部实现细节

### 坐标解包策略

代码根据硬件能力选择不同的实现:

**整数支持可用时(现代硬件):**
```glsl
int2 coords = int2(texCoords.x, texCoords.y);
int texIdx = coords.x >> 13;              // 提取第 13-14 位
float2 unormTexCoords = float2(coords.x & 0x1FFF, coords.y);  // 屏蔽高位
```

**无整数支持时(旧硬件):**
```glsl
float texIdx = floor(coord.x * exp2(-13));  // 相当于除以 8192
float2 unormTexCoords = float2(coord.x - texIdx * exp2(13), coord.y);
```

浮点实现通过数学运算模拟位操作。

### 单纹理优化

当 `numTextureSamplers <= 1` 时:
- 直接设置 `texIdx = 0`
- 跳过索引提取逻辑
- 避免不必要的位操作或数学计算

### 纹理坐标归一化

非归一化坐标转换为归一化 UV:
```glsl
uv = unormTexCoords * atlasDimensionsInv;
```

乘以图集尺寸的倒数将像素坐标转换为 [0, 1] 范围。

### 纹理索引的浮点化

即使在整数支持可用时,纹理索引 varying 也声明为浮点:
```glsl
texIdx.reset(SkSLType::kFloat);  // 总是使用浮点
```

**原因:** 在 ANGLE(OpenGL ES on D3D11)中,整数 varying 有显著的性能开销。

### Flat 插值优化

纹理索引使用 flat 插值:
```cpp
Interpolation::kCanBeFlat
```

避免不必要的插值计算,因为索引在整个图元中是恒定的。

### 多纹理查找的级联条件

生成一系列 `if-else` 语句:
- 前 N-1 个采样器: `if (texIdx == i) { ... } else`
- 最后一个采样器: `{ ... }` (省略最后的 else)

这种结构确保总是有一个采样器被选中。

### SDF LCD 三次采样

对每个采样器生成三次纹理查找:
1. **中心采样**: 提取红色通道作为中心距离
2. **左偏移采样**: `uv - offset` 提取红色通道
3. **右偏移采样**: `uv + offset` 提取红色通道

三个距离值组合形成 LCD 子像素抗锯齿所需的数据。

### 可选的整数坐标输出

`st` 参数允许输出未归一化的整数坐标:
- 用于需要像素精确坐标的效果
- 可选参数,不需要时传 `nullptr`

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGeometryProcessor` | 提供着色器生成上下文 |
| `GrShaderCaps` | 查询着色器能力(如整数支持) |
| `GrGLSLFragmentShaderBuilder` | 生成片段着色器代码 |
| `GrGLSLVertexGeoBuilder` | 生成顶点着色器代码 |
| `GrGLSLVarying` | Varying 变量管理 |
| `SkSLTypeShared` | SkSL 类型定义 |
| `SkAssert` | 断言宏 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrBitmapTextGeoProc` | 使用图集着色器辅助函数渲染位图文本 |
| `GrDistanceFieldGeoProc` | 使用 LCD 查找生成 SDF 文本着色器 |
| 其他文本渲染几何处理器 | 处理图集化的字形 |

## 设计模式与设计决策

### 内联函数库

所有函数都是内联的:
- 避免链接依赖
- 允许跨编译单元的优化
- 适合小型代码生成辅助函数

### 代码生成而非运行时逻辑

通过生成着色器代码而非在 CPU 侧处理:
- 将工作负载转移到 GPU
- 利用并行处理能力
- 减少 CPU 到 GPU 的数据传输

### 能力适配

根据 `ShaderCaps` 选择实现:
- 整数支持: 使用位操作(更高效)
- 无整数支持: 使用浮点数学(兼容性)

这确保了在不同硬件上的正确性。

### 位打包优化

使用位打包而非单独变量:
- 原始数据: X 坐标(16 位) + Y 坐标(16 位) + 纹理索引(2 位)
- 打包后: 34 位数据压缩到两个浮点数中
- 减少顶点数据大小和带宽

### 条件链而非数组索引

使用 if-else 链而非动态数组索引:
- **原因**: 某些 GPU(特别是移动设备)不支持动态索引纹理数组
- **权衡**: 代码更长但兼容性更好
- **优化**: 编译器可能将其优化为跳转表

### Flat 插值节省带宽

纹理索引使用 flat 插值:
- 避免透视矫正和线性插值
- 减少 GPU 插值单元的工作量
- 适用于常量值的 varying

### LCD 文本的三次采样

SDF LCD 渲染需要三个距离采样:
- 模拟 LCD 屏幕的 RGB 子像素布局
- 每个子像素位置略有偏移
- 生成更清晰的文本边缘

## 性能考量

### 减少 Varying 数量

通过位打包,仅需三个 varying:
- `uv` - 归一化纹理坐标(2 个浮点)
- `texIdx` - 纹理索引(1 个浮点)
- `st` - 可选的整数坐标(2 个浮点)

相比为每个字段使用独立 varying,节省插值带宽。

### 整数位操作效率

在支持整数的硬件上:
- 右移 13 位提取索引: 单周期指令
- 与运算屏蔽位: 单周期指令
- 避免浮点运算的延迟

### 浮点回退的代价

无整数支持时的浮点实现:
- `floor` 和 `exp2` 是相对昂贵的数学函数
- 但在旧硬件上仍是唯一选择
- 通过在顶点着色器执行,每个顶点仅计算一次

### 多纹理查找的分支

条件纹理查找使用动态分支:
- 现代 GPU 的分支预测较好
- 对于图集页数较少(通常 1-4 个)的情况效率高
- 避免了动态索引的兼容性问题

### LCD 查找的重复代码

`append_multitexture_lookup_lcd` 生成重复的代码块:
- 为每个采样器重复三次查找逻辑
- 增加着色器大小但避免了运行时循环
- 现代 GPU 的指令缓存足以容纳

### Flat 插值的收益

使用 flat 插值的性能优势:
- 跳过插值硬件单元
- 减少插值器的占用
- 在片段着色器中直接使用顶点值

### 坐标归一化的位置

归一化在顶点着色器中完成:
```glsl
uv = unormTexCoords * atlasDimensionsInv;
```
每个顶点执行一次,而非每个片段,节省大量计算。

## 设计模式与设计决策

### 内联辅助函数模式

采用内联函数而非类:
- 无状态,纯函数式接口
- 编译时完全展开
- 零运行时开销

### 代码生成策略

通过 `codeAppendf` 生成字符串化的着色器代码:
- 灵活的代码组合
- 运行时根据配置生成不同代码
- 支持条件编译和优化

### 能力检测驱动实现

通过 `args.fShaderCaps` 查询硬件能力:
- 运行时适配不同的着色器特性
- 保证在各种硬件上的正确性
- 在可能的情况下选择最优实现

### 参数化纹理数量

所有函数接受 `numTextureSamplers` 参数:
- 支持 1 到 N 个图集页
- 单页时生成优化的无分支代码
- 多页时生成条件查找代码

### 防御性编程

检查无效参数并提供回退:
```cpp
if (numTextureSamplers <= 0) {
    args.fFragBuilder->codeAppendf("%s = float4(1);", colorName);
    return;
}
```

虽然理论上不应发生,但避免了崩溃。

### 分离的 LCD 处理

为 LCD 文本提供专门函数:
- LCD 渲染有独特的三次采样需求
- 避免在通用函数中增加复杂性
- 代码重复但职责清晰

### iPhone 6 兼容性处理

特别注释了位选择的原因:
```cpp
// bits 13 & 14 instead of 14 & 15 due to iPhone 6 issues in GLES
```

体现了对真实硬件问题的响应和兼容性考虑。

## 性能考量

### 位打包的权衡

使用位打包技术:
- **收益**: 减少顶点属性大小,降低内存带宽
- **成本**: 顶点着色器中的解包开销
- **结论**: 对于大批量文本渲染(成千上万字形),带宽节省超过解包成本

### 整数 vs 浮点路径

整数路径的性能优势:
- 位操作比浮点数学快
- 现代 GPU 的整数 ALU 与浮点 ALU 并行
- 但浮点路径在旧硬件上必需

### 条件分支的成本

多纹理查找的分支:
- 对于 2-4 个采样器,分支成本可接受
- 现代 GPU 有良好的分支预测
- 相同纹理索引的片段会一起执行(波前一致性)

### Varying 插值成本

不同插值模式的成本:
- **Smooth**: 透视矫正插值(最昂贵)
- **Flat**: 无插值(最便宜)
- **NoPerspective**: 线性插值(中等)

纹理索引使用 flat 节省了插值成本。

### 代码膨胀

SDF LCD 函数生成大量代码:
- 每个采样器 3 次查找 × N 个采样器
- 增加着色器编译时间
- 但提高运行时性能(展开的循环)

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGeometryProcessor.h` | 依赖 | 几何处理器基类和上下文 |
| `src/gpu/ganesh/GrShaderCaps.h` | 依赖 | 着色器能力查询 |
| `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h` | 依赖 | 片段着色器构建器 |
| `src/gpu/ganesh/glsl/GrGLSLVertexGeoBuilder.h` | 依赖 | 顶点着色器构建器 |
| `src/gpu/ganesh/glsl/GrGLSLVarying.h` | 依赖 | Varying 变量管理 |
| `src/core/SkSLTypeShared.h` | 依赖 | SkSL 类型系统 |
| `src/gpu/ganesh/effects/GrBitmapTextGeoProc.cpp` | 被使用 | 位图文本几何处理器 |
| `src/gpu/ganesh/effects/GrDistanceFieldGeoProc.cpp` | 被使用 | 距离场文本几何处理器 |
| `include/private/base/SkAssert.h` | 依赖 | 断言宏 |
