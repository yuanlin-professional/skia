# GrBitmapTextGeoProc

> 源文件
> - src/gpu/ganesh/effects/GrBitmapTextGeoProc.h
> - src/gpu/ganesh/effects/GrBitmapTextGeoProc.cpp

## 概述

`GrBitmapTextGeoProc` 是 Ganesh GPU 后端中专门用于位图文本渲染的几何处理器 (Geometry Processor)。它将输入颜色与纹理采样结果进行调制,生成最终的像素颜色和覆盖率。该处理器支持多纹理图集采样、自定义坐标属性、颜色空间转换以及多种蒙版格式,是 Skia 文本渲染管线中的核心组件。

此模块的主要职责是在顶点着色器阶段处理文本字形的位置变换和纹理坐标映射,在片段着色器阶段从纹理图集中采样字形像素并应用颜色调制,最终输出用于文本渲染的颜色和覆盖率值。

## 架构位置

`GrBitmapTextGeoProc` 位于 Skia 图形管线的几何处理器层,专注于文本渲染:

```
skia/
└── src/gpu/ganesh/
    └── effects/
        ├── GrBitmapTextGeoProc.h    (头文件 - 几何处理器定义)
        └── GrBitmapTextGeoProc.cpp  (实现文件 - 着色器代码生成)
```

在渲染管线中的位置:
- **输入**: 顶点数据 (位置、颜色、纹理坐标)、纹理图集
- **层级**: 几何处理器阶段,负责顶点变换和属性传递
- **输出**: 经过插值的片段属性,供后续混合使用

文本渲染流程:
1. **文本布局**: 上层系统计算字形位置和纹理坐标
2. **几何处理**: `GrBitmapTextGeoProc` 变换顶点并传递属性
3. **片段处理**: 从纹理图集采样字形像素
4. **混合输出**: 将采样结果与颜色混合,输出到帧缓冲

## 主要类与结构体

### GrBitmapTextGeoProc

```cpp
class GrBitmapTextGeoProc : public GrGeometryProcessor {
    SkPMColor4f              fColor;              // 统一颜色
    sk_sp<GrColorSpaceXform> fColorSpaceXform;   // 颜色空间转换
    SkMatrix                 fLocalMatrix;        // 局部坐标变换矩阵
    bool                     fUsesW;              // 是否使用齐次坐标
    SkISize                  fAtlasDimensions;    // 图集尺寸
    TextureSampler           fTextureSamplers[4]; // 纹理采样器数组
    Attribute                fInPosition;         // 位置属性
    Attribute                fInColor;            // 颜色属性
    Attribute                fInTextureCoords;    // 纹理坐标属性
    skgpu::MaskFormat        fMaskFormat;         // 蒙版格式
};
```

**核心职责**:
- 管理顶点属性 (位置、颜色、纹理坐标)
- 配置纹理采样器 (最多 4 个纹理)
- 生成顶点和片段着色器代码
- 处理颜色空间转换

**关键成员**:
- `fColor`: 当没有顶点颜色时使用的统一颜色
- `fColorSpaceXform`: 用于 sRGB/线性颜色空间转换
- `fLocalMatrix`: 应用到局部坐标的变换矩阵
- `fUsesW`: 支持透视投影 (3D 坐标)
- `fAtlasDimensions`: 纹理图集的宽高,必须是 2 的幂
- `fMaskFormat`: 支持 A8 (灰度)、A565 (彩色) 和 ARGB (全彩) 三种格式

### GrBitmapTextGeoProc::Impl

```cpp
class Impl : public ProgramImpl {
    SkPMColor4f   fColor;              // 缓存的颜色值
    SkISize       fAtlasDimensions;    // 缓存的图集尺寸
    SkMatrix      fLocalMatrix;        // 缓存的局部矩阵
    UniformHandle fColorUniform;       // 颜色统一变量句柄
    UniformHandle fAtlasDimensionsInvUniform; // 图集尺寸倒数
    UniformHandle fLocalMatrixUniform; // 局部矩阵统一变量
    GrGLSLColorSpaceXformHelper fColorSpaceXformHelper; // 颜色空间转换辅助器
};
```

**核心职责**:
- 生成 GLSL 着色器代码
- 管理统一变量的更新
- 处理顶点和片段着色器的数据传递

## 公共 API 函数

### Make (静态工厂方法)

```cpp
static GrGeometryProcessor* Make(
    SkArenaAlloc* arena,
    const GrShaderCaps& caps,
    const SkPMColor4f& color,
    bool wideColor,
    sk_sp<GrColorSpaceXform> colorSpaceXform,
    const GrSurfaceProxyView* views,
    int numActiveViews,
    GrSamplerState p,
    skgpu::MaskFormat format,
    const SkMatrix& localMatrix,
    bool usesW);
```

**功能**: 创建位图文本几何处理器实例

**参数详解**:
- `arena`: 内存分配器,使用对象池模式避免频繁分配
- `caps`: 着色器能力查询接口,判断硬件特性
- `color`: 预乘 alpha 颜色,用于非顶点颜色模式
- `wideColor`: 是否使用宽色域 (16 位浮点颜色)
- `colorSpaceXform`: 颜色空间转换对象,用于 sRGB <-> 线性转换
- `views`: 纹理图集视图数组 (最多 4 个)
- `numActiveViews`: 活动纹理数量
- `p`: 采样器状态 (过滤模式和包裹模式)
- `format`: 蒙版格式 (A8/A565/ARGB)
- `localMatrix`: 局部坐标变换矩阵
- `usesW`: 是否使用齐次坐标 (透视投影)

**返回值**: 配置好的几何处理器指针

**使用场景**: 在文本绘制操作准备阶段,根据字形类型和渲染需求创建处理器

### addNewViews

```cpp
void addNewViews(const GrSurfaceProxyView* views,
                 int numActiveViews,
                 GrSamplerState params);
```

**功能**: 动态添加新的纹理图集视图

**参数**:
- `views`: 新的纹理视图数组
- `numActiveViews`: 新纹理的数量
- `params`: 采样器参数

**使用场景**: 当文本渲染需要更多纹理图集时,动态扩展纹理采样器

**注意事项**:
- 最多支持 4 个纹理
- 所有纹理必须具有相同的尺寸
- 只初始化未初始化的采样器槽位

### addToKey

```cpp
void addToKey(const GrShaderCaps& caps, skgpu::KeyBuilder* b) const override;
```

**功能**: 生成着色器缓存键值

**编码信息**:
- 是否使用齐次坐标 (1 位)
- 蒙版格式 (2 位)
- 局部矩阵类型 (用于优化矩阵运算)
- 纹理数量 (32 位)
- 颜色空间转换键 (32 位)

**作用**: 确保相同配置的处理器共享编译好的着色器程序

### makeProgramImpl

```cpp
std::unique_ptr<ProgramImpl> makeProgramImpl(const GrShaderCaps& caps) const override;
```

**功能**: 创建程序实现对象,负责着色器代码生成和数据绑定

**返回值**: `Impl` 对象的智能指针

## 内部实现细节

### 顶点属性配置

根据不同的配置,处理器设置不同的顶点属性:

**位置属性**:
```cpp
// 2D 坐标 (普通投影)
fInPosition = {"inPosition", kFloat2_GrVertexAttribType, SkSLType::kFloat2};

// 3D 坐标 (透视投影)
fInPosition = {"inPosition", kFloat3_GrVertexAttribType, SkSLType::kFloat3};
```

**颜色属性**:
- 仅在 A8 和 A565 格式时启用
- 支持标准和宽色域两种模式
- ARGB 格式不使用顶点颜色 (直接从纹理读取)

**纹理坐标属性**:
```cpp
// 整数支持: 使用 ushort2 压缩坐标 (节省带宽)
fInTextureCoords = {"inTextureCoords", kUShort2_GrVertexAttribType, SkSLType::kUShort2};

// 无整数支持: 回退到 float2
fInTextureCoords = {"inTextureCoords", kUShort2_GrVertexAttribType, SkSLType::kFloat2};
```

### 着色器代码生成

**顶点着色器**:
1. 发射顶点属性声明
2. 计算图集纹理坐标 (归一化到 [0, 1])
3. 传递纹理索引 (用于多纹理采样)
4. 应用局部坐标变换
5. 输出裁剪空间位置

**片段着色器**:
1. 接收插值后的纹理坐标和索引
2. 从多纹理图集中采样 (`append_multitexture_lookup`)
3. 应用颜色空间转换 (如果需要)
4. 根据蒙版格式生成最终输出:
   - **ARGB 格式**: `outputColor = inputColor * texColor; outputCoverage = 1`
   - **A8/A565 格式**: `outputCoverage = texColor; outputColor = inputColor`

### 多纹理图集采样

使用 `append_multitexture_lookup` 辅助函数:
- 根据纹理索引选择对应的采样器
- 支持最多 4 个纹理图集
- 生成条件分支或数组索引代码 (取决于硬件支持)

代码示例:
```glsl
// 简化的多纹理采样逻辑
if (texIdx == 0) {
    texColor = texture(sampler0, uv);
} else if (texIdx == 1) {
    texColor = texture(sampler1, uv);
} // ... 最多 4 个纹理
```

### 统一变量管理

`Impl::setData` 函数高效更新统一变量:
- **脏检查**: 只在值变化时更新,避免不必要的 GPU 状态切换
- **图集尺寸倒数**: 预计算 `1/width` 和 `1/height`,用于坐标归一化
- **矩阵优化**: 使用 `SetTransform` 辅助函数,根据矩阵类型选择最优上传方式

### 蒙版格式处理

| 格式 | 用途 | 顶点颜色 | 输出逻辑 |
|-----|------|---------|---------|
| A8 | 灰度文本 | 是 | 纹理作为覆盖率,颜色独立 |
| A565 | LCD 次像素渲染 | 是 | 纹理作为覆盖率,颜色独立 |
| ARGB | 彩色 Emoji | 否 | 纹理直接调制颜色 |

**设计原因**:
- A8 和 A565 需要顶点颜色来指定文本颜色
- ARGB 直接包含颜色信息,无需额外顶点数据

## 依赖关系

### 内部依赖

- `GrGeometryProcessor`: 基类,定义几何处理器接口
- `GrColorSpaceXform`: 颜色空间转换工具
- `GrSamplerState`: 纹理采样参数封装
- `GrSurfaceProxyView`: 纹理资源的抽象视图
- `GrAtlasedShaderHelpers`: 图集采样辅助函数
- `GrGLSLColorSpaceXformHelper`: GLSL 颜色转换代码生成器

### 外部依赖

- `SkMatrix`: 矩阵变换
- `SkPMColor4f`: 预乘 alpha 颜色
- `SkArenaAlloc`: 对象池分配器
- `skgpu::MaskFormat`: 蒙版格式枚举
- `skgpu::KeyBuilder`: 着色器缓存键构建器

### 依赖关系图

```
GrBitmapTextGeoProc
    ├── GrGeometryProcessor (基类)
    ├── GrColorSpaceXform (颜色转换)
    ├── GrSamplerState (采样配置)
    ├── GrSurfaceProxyView (纹理访问)
    ├── GrAtlasedShaderHelpers (图集工具)
    └── GrGLSLColorSpaceXformHelper (GLSL 生成)
```

## 设计模式与设计决策

### 1. 工厂方法模式

使用 `Make` 静态方法配合 `SkArenaAlloc`:
- **优点**: 对象池分配,避免堆碎片
- **实现**: 使用 placement new 在预分配内存中构造对象
- **生命周期**: 对象随 Arena 一起销毁,无需手动释放

### 2. PImpl 模式 (程序实现分离)

`Impl` 类封装着色器代码生成逻辑:
- **优点**: 分离接口和实现,减少头文件依赖
- **实现**: `makeProgramImpl` 创建实现对象
- **作用**: 支持不同 GPU 后端的多态实现

### 3. 缓存与脏检查策略

`Impl::setData` 缓存统一变量值:
- **优点**: 减少 GPU 状态更改,提升性能
- **实现**: 成员变量存储上次设置的值,新值与旧值比较
- **适用场景**: 连续渲染相同配置的文本

### 4. 编译期类型安全

使用 `constexpr` 和 `static_assert`:
```cpp
inline static constexpr int kMaxTextures = 4;
static_assert(static_cast<int>(MaskFormat::kLast) < (1u << 2));
```
- **优点**: 编译期检查,避免运行时错误
- **示例**: 确保蒙版格式能用 2 位编码

### 5. 顶点属性优化

根据硬件能力选择属性类型:
- **整数支持**: 使用 `ushort2` 压缩纹理坐标 (4 字节)
- **无整数支持**: 回退到 `float2` (8 字节)
- **影响**: 减少 50% 的顶点数据带宽

### 6. 多纹理策略

最多支持 4 个纹理图集:
- **原因**: 平衡性能和资源消耗
- **权衡**: 更多纹理增加寄存器压力和状态切换
- **实践**: 4 个纹理足够覆盖常见的文本渲染场景

## 性能考量

### 1. 内存效率

- **对象池分配**: 使用 `SkArenaAlloc`,批量释放,无碎片
- **顶点数据压缩**: `ushort2` 纹理坐标减少 50% 带宽
- **属性对齐**: 使用 `setVertexAttributesWithImplicitOffsets` 自动对齐

### 2. GPU 状态切换开销

- **脏检查**: 避免冗余的统一变量更新
- **图集尺寸缓存**: 二次幂尺寸验证仅在变化时执行
- **颜色空间转换**: 仅在需要时生成转换代码

### 3. 着色器编译优化

- **键值缓存**: 相同配置共享编译好的着色器
- **条件编译**: 根据蒙版格式生成不同的片段代码
- **矩阵优化**: `ComputeMatrixKey` 识别单位矩阵/平移矩阵等特殊情况

### 4. 纹理采样优化

- **图集合并**: 多个字形共享纹理,减少绑定操作
- **坐标归一化**: 预计算 `1/atlasDimensions`,顶点着色器中乘法代替除法
- **采样器配置**: 复用相同配置的采样器状态

### 5. 带宽优化

- **顶点属性最小化**: 仅在需要时启用颜色属性
- **纹理格式选择**: A8 格式 (1 字节) vs ARGB (4 字节)
- **齐次坐标选择**: 2D 路径使用 `float2` 节省 33% 带宽

### 6. 测试支持

`TestCreate` 函数用于随机化测试:
- 随机纹理视图、采样器状态、蒙版格式
- 覆盖各种配置组合
- 仅在 `GPU_TEST_UTILS` 宏定义时编译

### 7. 实际性能指标

典型文本渲染场景:
- **顶点数据**: 每字形 4 顶点 × (8-12 字节) = 32-48 字节
- **纹理带宽**: A8 格式每像素 1 字节,ARGB 4 字节
- **状态切换**: 每批次 1-2 次纹理绑定,2-3 次统一变量更新

## 相关文件

### 同目录文件
- `GrDistanceFieldGeoProc`: 距离场文本渲染处理器 (SDF)
- `GrTextureEffect`: 通用纹理采样效果
- `GrAtlasedShaderHelpers.h`: 图集采样辅助工具

### 依赖的核心文件
- `src/gpu/ganesh/GrGeometryProcessor.h`: 几何处理器基类
- `src/gpu/ganesh/GrColorSpaceXform.h`: 颜色空间转换
- `src/gpu/ganesh/GrSamplerState.h`: 采样器状态
- `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h`: 片段着色器构建器

### 使用此文件的上层模块
- `GrTextContext`: 文本绘制上下文
- `GrAtlasTextOp`: 图集文本绘制操作
- `GrOpsTask`: 渲染任务调度器

### 测试文件
- `tests/ProcessorTest.cpp`: 几何处理器单元测试
- `tests/TextBlobTest.cpp`: 文本块渲染测试
