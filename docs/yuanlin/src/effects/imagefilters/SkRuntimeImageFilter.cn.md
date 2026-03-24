# SkRuntimeImageFilter

> 源文件: `src/effects/imagefilters/SkRuntimeImageFilter.cpp`

## 概述

`SkRuntimeImageFilter` 是基于 SkSL 运行时着色器(Runtime Shader)的图像滤镜实现。它允许用户提供自定义的 SkSL 着色器代码作为图像滤镜的处理逻辑,将一个或多个输入图像滤镜的结果作为着色器的子着色器输入。这是 Skia 图像滤镜系统中最灵活的滤镜类型,使用户可以实现任意的像素级变换效果。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkRuntimeImageFilter (本文件)
            ├─ 持有 SkRuntimeShaderBuilder (含 SkSL 代码和 uniforms)
            ├─ 子着色器名称映射 (fChildShaderNames)
            └─ 最大采样半径 (fMaxSampleRadius)

工厂方法: SkImageFilters::RuntimeShader()
```

## 主要类与结构体

### `SkRuntimeImageFilter`
- 继承自 `SkImageFilter_Base`
- **注意**: 不在匿名命名空间中,以便 `SkRuntimeShaderBuilder` 能声明其为友元类
- **成员变量**:
  - `fRuntimeEffectLock` (`SkSpinlock`): 保护运行时效果构建器的自旋锁
  - `fRuntimeEffectBuilder` (`mutable SkRuntimeShaderBuilder`): 运行时着色器构建器
  - `fChildShaderNames` (`STArray<1, SkString>`): 子着色器名称列表
  - `fMaxSampleRadius` (`float`): 最大采样半径,控制输入扩展量

## 公共 API 函数

### `SkImageFilters::RuntimeShader(builder, sampleRadius, childShaderName, input) -> sk_sp<SkImageFilter>`
单输入版本的工厂方法。若未提供 `childShaderName`,自动使用效果中唯一的子着色器。

### `SkImageFilters::RuntimeShader(builder, maxSampleRadius, childShaderNames[], inputs[], inputCount) -> sk_sp<SkImageFilter>`
多输入版本的工厂方法。验证逻辑包括:
- `maxSampleRadius` 必须非负
- 所有子着色器名称必须非空且存在于效果定义中
- 子着色器名称不允许重复
- 子着色器类型必须为 `kShader`

## 内部实现细节

### 滤镜核心逻辑
`onFilterImage()` 的工作流程:
1. 扩展期望输出区域,增加 `maxSampleRadius` 的图层空间偏移量
2. 使用 `FilterResult::Builder` 收集所有子滤镜输出
3. 每个子输入使用扩展后的区域作为采样边界,并标记 `ShaderFlags::kNonTrivialSampling`
4. 在 eval 回调中:
   - 获取自旋锁
   - 将子着色器设置到构建器中
   - 创建最终着色器
   - 清除子着色器引用(避免延长生命周期)
   - 释放自旋锁
5. 设置 `evaluateInParameterSpace=true`,在参数空间中求值

### 线程安全
使用 `SkSpinlock` 保护 `fRuntimeEffectBuilder` 的修改和着色器创建过程。由于构建器是 `mutable` 的且包含状态修改(设置子着色器),需要同步来确保多线程安全。

### 矩阵能力限制
声明 `MatrixCapability::kTranslate`,仅支持平移变换。注释说明这是一个保守的选择:由于无法知道用户 SkSL 中几何 uniform 的语义,限制为仅平移可确保输出正确,但在大量缩放时会损失分辨率。(参见 skbug.com/40044507)

### 边界计算
- `onGetOutputLayerBounds()`: 返回 `Unbounded()`,因为无法预测运行时着色器会生成什么内容
- `onGetInputLayerBounds()`: 对期望输出应用 `maxSampleRadius` 扩展后,返回所有子输入的联合边界
- `computeFastBounds()`: 返回 `SkRectPriv::MakeLargeS32()`(悲观估计)

### 序列化
序列化内容包括:SkSL 源码字符串、uniform 数据、子着色器名称列表、所有子 flattenable 对象、最大采样半径。反序列化时使用 `SkMakeCachedRuntimeEffect` 进行 SkSL 编译结果缓存。

## 依赖关系

- `include/effects/SkRuntimeEffect.h` - 运行时效果 API
- `src/base/SkSpinlock.h` - 轻量级自旋锁
- `src/core/SkRuntimeEffectPriv.h` - `SkMakeCachedRuntimeEffect` 缓存编译
- `include/core/SkShader.h` - 着色器接口
- `src/core/SkImageFilterTypes.h` - FilterResult、Context 等
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkRectPriv.h` - `MakeLargeS32` 无限边界工具

## 设计模式与设计决策

### Builder 模式
使用 `SkRuntimeShaderBuilder` 封装 SkSL 效果、uniform 和子着色器,简化了运行时效果的构建和管理。

### 名称绑定
通过字符串名称将图像滤镜输入绑定到 SkSL 中声明的子着色器,这比基于索引的绑定更灵活,但需要额外的名称验证。

### 悲观边界估计
由于无法静态分析 SkSL 代码的行为,输出边界被悲观地设为无界。这确保了正确性,但可能导致不必要的像素处理。

### 采样半径参数
`maxSampleRadius` 参数允许用户告知系统着色器可能会从距当前像素多远的位置采样,使系统能够提供足够的输入数据。这是用户 SkSL 代码和系统边界管理之间的契约。

## 性能考量

- 自旋锁开销:每次滤镜求值都需要获取和释放锁,但自旋锁在无竞争时开销极小(仅一次原子操作)
- SkSL 编译缓存:通过 `SkMakeCachedRuntimeEffect` 避免重复编译相同的 SkSL 代码,编译结果全局缓存
- 悲观边界:无界输出可能导致处理区域大于实际需要,但这是正确性的代价
- 参数空间求值:设置 `evaluateInParameterSpace=true` 避免了不必要的坐标变换开销
- 子着色器生命周期管理:eval 后清除引用,防止不必要的资源保持(图像纹理等)
- 输入扩展:每个子输入使用 `maxSampleRadius` 扩展的区域作为采样边界,确保着色器有足够的边界数据
- ShaderFlags::kNonTrivialSampling 标记提示后端为非平凡采样提供足够的纹理边界

## 线程安全注意事项

由于 `fRuntimeEffectBuilder` 是 mutable 的且在 `onFilterImage()` 中被修改,必须使用锁保护:
- `fRuntimeEffectLock.acquire()` 在设置子着色器前获取
- 着色器创建后清除子着色器引用(避免延长生命周期)
- `fRuntimeEffectLock.release()` 在清理完成后释放
- `flatten()` 也需要获取锁来安全读取构建器状态

这种设计允许单个 SkRuntimeImageFilter 实例在多线程绘制中安全使用。

## 与标准图像滤镜的对比

| 特性 | RuntimeImageFilter | 标准内置滤镜 |
|------|-------------------|-------------|
| 效果定义 | 用户 SkSL 代码 | 固定实现 |
| 输出边界 | 无界(悲观) | 通常可精确计算 |
| 矩阵能力 | kTranslate(保守) | 通常 kComplex |
| 序列化大小 | 较大(含 SkSL 源码) | 较小 |
| 编译开销 | 首次编译 SkSL | 无 |

## 序列化格式详解

写入顺序:
1. 基类数据 (子滤镜)
2. SkSL 源码字符串
3. uniform 数据 (字节数组)
4. 子着色器名称列表 (每个为字符串)
5. 所有效果子对象 (blender, colorfilter, shader)
6. maxSampleRadius (浮点数)

反序列化时通过 `SkMakeCachedRuntimeEffect` 编译 SkSL,该函数维护一个全局缓存,避免对相同 SkSL 源码的重复编译。

注意:反序列化时需要验证 uniform 数据大小与效果定义匹配,以及所有子着色器名称都有效。

## maxSampleRadius 的语义

`maxSampleRadius` 告诉系统:SkSL 着色器可能会采样距当前像素最多 `maxSampleRadius` 个参数空间单位远的位置。系统据此:
1. 扩展子滤镜的输入请求范围
2. 将扩展后的区域作为子着色器的采样边界
3. 确保着色器在边缘处不会采样到无效数据

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `include/effects/SkRuntimeEffect.h` - 运行时效果 API
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
- `src/core/SkRuntimeEffectPriv.h` - 运行时效果内部工具
