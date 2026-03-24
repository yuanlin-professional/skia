# SkSLEffect - Skottie 自定义 SkSL 着色器效果

> 源文件: `modules/skottie/src/effects/SkSLEffect.cpp`

## 概述

SkSLEffect 实现了在 Lottie 动画中使用自定义 SkSL（Skia Shading Language）着色器和颜色滤镜的功能。该模块支持从 Lottie JSON 中加载 SkSL 着色器代码，动态绑定 uniform 参数、图像纹理和图层内容，在运行时编译并应用着色器效果。整个功能通过编译宏 `SK_ENABLE_SKOTTIE_SKSLEFFECT` 控制，可在构建时禁用。

## 架构位置

SkSLEffect 位于 Skottie 效果子系统中，是最灵活的效果实现，支持任意 SkSL 程序。

```
EffectBuilder
  |
  +-> attachSkSLShader() [着色器模式]
  |     +-> SkSLShaderNode (自定义渲染节点)
  |     +-> SkSLShaderAdapter (属性适配器)
  |           +-> SkSLEffectBase (共享逻辑)
  |
  +-> attachSkSLColorFilter() [颜色滤镜模式]
        +-> sksg::ExternalColorFilter
        +-> SkSLColorFilterAdapter (属性适配器)
              +-> SkSLEffectBase (共享逻辑)
```

## 主要类与结构体

### SkSLShaderNode
- 继承自 `sksg::CustomRenderNode`
- 管理效果着色器和内容着色器（子图层的 Picture 着色器快照）
- `contentShader()` - 将子渲染节点捕获为 SkPicture 并转换为可重复平铺的着色器
- `onRender()` - SaveLayer + SrcIn 混合模式应用着色器
- `SG_ATTRIBUTE(Shader, ...)` - 外部设置的效果着色器

### SkSLEffectBase
- 着色器/颜色滤镜共享的基类（非继承关系，两个适配器同时继承此类）
- 负责 SkSL 代码编译（`SkRuntimeEffect::MakeForShader`）
- `bindUniforms()` - 从 JSON props 动态绑定 uniform 变量
- `buildUniformData()` - 构建 uniform 数据块
- `buildChildrenData()` - 构建子着色器数据（图像/图层引用）
- 属性类型枚举：
  - `kSkSLProp_uniform = 0` - 数值 uniform
  - `kSkSLProp_image = 98` - 图像资源引用
  - `kSkSLProp_layer = 99` - 图层内容引用

### ChildData（结构体）
- `type` - 子输入类型（image 或 layer）
- `name` - SkSL 中的子着色器名称
- `child` - `SkRuntimeEffect::ChildPtr` 着色器引用

### SkSLShaderAdapter
- 多重继承 `DiscardableAdapterBase` 和 `SkSLEffectBase`
- `onSync()` 使用 `buildUniformData()` 和 `buildChildrenData()` 重建着色器
- 将结果着色器设置到 `SkSLShaderNode`

### SkSLColorFilterAdapter
- 多重继承 `DiscardableAdapterBase` 和 `SkSLEffectBase`
- `onSync()` 使用 `buildUniformData()` 创建颜色滤镜
- 将结果颜色滤镜设置到 `sksg::ExternalColorFilter`

## 公共 API 函数

### `EffectBuilder::attachSkSLShader`
```cpp
sk_sp<sksg::RenderNode> attachSkSLShader(const skjson::ArrayValue& jprops,
                                          sk_sp<sksg::RenderNode> layer) const;
```
- 着色器模式：创建 SkSLShaderNode + SkSLShaderAdapter
- 当 `SK_ENABLE_SKOTTIE_SKSLEFFECT` 未定义时直接返回原图层

### `EffectBuilder::attachSkSLColorFilter`
```cpp
sk_sp<sksg::RenderNode> attachSkSLColorFilter(const skjson::ArrayValue& jprops,
                                               sk_sp<sksg::RenderNode> layer) const;
```
- 颜色滤镜模式：创建 ExternalColorFilter + SkSLColorFilterAdapter
- 当 `SK_ENABLE_SKOTTIE_SKSLEFFECT` 未定义时直接返回原图层

## 内部实现细节

### SkSL 代码加载
- JSON props 的第一个元素（index 0）包含着色器代码
- 从 `(*jSkSL)["sh"]` 字段提取 SkSL 源码
- 使用 `SkRuntimeEffect::MakeForShader()` 编译
- 编译失败时记录错误日志，`fEffect` 保持为空

### Uniform 绑定
- JSON props 从 index 1 开始遍历
- 每个 prop 的 `"nm"` 字段为 uniform 名称，`"ty"` 字段为类型
- 类型路由：
  - uniform (0)：创建 VectorValue 并通过 `container->bind()` 绑定动画
  - image (98)：通过 ScopedAssetRef 加载图像资产，创建图像着色器
  - layer (99)：标记为图层内容引用，延迟到 `onSync` 时获取

### Uniform 数据构建
```cpp
sk_sp<SkData> buildUniformData() const;
```
- 零初始化 `fEffect->uniformSize()` 大小的数据块
- 通过 `fEffect->findUniform(name)` 查找 metadata（偏移和大小）
- 使用 `memcpy` 将 VectorValue 数据拷贝到正确偏移
- uniform 大小不匹配时输出调试信息

### 子着色器构建
- 图像类型：直接使用预加载的着色器
- 图层类型：调用 `node->contentShader()` 获取当前子内容的着色器快照
- 通过 `fEffect->findChild(name)` 定位子着色器在 children 数组中的位置

### 内容着色器捕获
```cpp
sk_sp<SkShader> contentShader();
```
- 使用 `SkPictureRecorder` 将子渲染节点录制为 SkPicture
- 转换为带 kRepeat 平铺的着色器
- 仅在子节点失效时重新捕获（`hasChildrenInval()` 检查）

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkRuntimeEffect.h` | SkSL 运行时编译和着色器创建 |
| `SkPicture.h` / `SkPictureRecorder.h` | 子内容捕获 |
| `SkCanvas.h` / `SkPaint.h` | 渲染和混合 |
| `SkData.h` | Uniform 数据块 |
| `SkResources.h` | 图像资产加载 |
| `SkSGColorFilter.h` | ExternalColorFilter |
| `Adapter.h` | DiscardableAdapterBase |
| `Effects.h` | EffectBinder |
| `Animator.h` | AnimatablePropertyContainer |
| `SkottiePriv.h` | AnimationBuilder、ScopedAssetRef |

## 设计模式与设计决策

- **多重继承组合**：SkSLShaderAdapter 和 SkSLColorFilterAdapter 同时继承适配器基类和 SkSLEffectBase，共享编译和 uniform 管理逻辑。
- **编译宏守护**：整个功能通过 `SK_ENABLE_SKOTTIE_SKSLEFFECT` 宏控制，禁用时效果直接透传原图层，零开销。
- **延迟着色器捕获**：图层内容着色器仅在子节点失效时重建，缓存到 `fContentShader`。
- **动态 Uniform 发现**：uniform 列表从 JSON 动态构建，运行时通过名称匹配 SkSL 中的声明，提供高度灵活性。
- **SrcIn 混合**：与 FractalNoiseEffect 相同的 SaveLayer + SrcIn 模式，将着色器效果限制在子内容的不透明区域。

## 性能考量

- SkSL 着色器在加载时一次性编译，运行时仅设置 uniform 和子着色器。
- `contentShader()` 缓存机制避免每帧重新捕获未变化的子内容。
- SkPicture 着色器可被 GPU 高效处理。
- 图像资产着色器在加载时预创建（TODO 注释指出应改为按帧动态创建）。
- Uniform 数据块使用 `SkData::MakeZeroInitialized` 分配，每帧重建但大小固定（不触发重分配）。
- 颜色滤镜模式比着色器模式更轻量（无需 Picture 捕获和 SaveLayer）。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBinder、效果注册
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase
- `modules/sksg/include/SkSGColorFilter.h` - ExternalColorFilter
- `include/effects/SkRuntimeEffect.h` - SkSL 运行时效果 API
- `modules/skottie/src/effects/FractalNoiseEffect.cpp` - 类似的 SkSL 着色器效果
- `modules/skresources/include/SkResources.h` - 图像资源加载
