# Composition - Skottie 合成构建器

> 源文件: [`modules/skottie/src/Composition.h`](../../../modules/skottie/src/Composition.h), [`modules/skottie/src/Composition.cpp`](../../../modules/skottie/src/Composition.cpp)

## 概述

CompositionBuilder 负责构建 Skottie 的合成（Composition），即将 Lottie JSON 中的图层数组解析为完整的场景图渲染树。它管理图层索引映射、相机变换初始化以及两阶段图层构建流程。每个 Lottie 合成（包括预合成资产）都对应一个 CompositionBuilder 实例。

## 架构位置

位于 Skottie 内部实现层，是图层系统的顶层管理者：

- **调用者**: AnimationBuilder（构建主合成和预合成资产时）
- **管理对象**: LayerBuilder（图层构建器）
- **协作组件**: CameraAdaper（相机）
- **输出**: sksg::RenderNode（场景图渲染树根节点）

## 主要类与结构体

### `CompositionBuilder` 类

```cpp
class CompositionBuilder final : SkNoncopyable {
public:
    CompositionBuilder(const AnimationBuilder&, const SkSize&, const ObjectValue&);
    sk_sp<sksg::RenderNode> build(const AnimationBuilder&);
    LayerBuilder* layerBuilder(int layer_index);
    sk_sp<sksg::RenderNode> layerContent(const AnimationBuilder&, int layer_index);
};
```

### `ScopedAssetRef` 内部类
资产引用管理器，处理资产查找和循环引用检测。在构造时查找资产并设置 `fIsAttaching` 标记，析构时清除。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `build(abuilder)` | 执行两阶段构建，返回场景图根节点 |
| `layerBuilder(layer_index)` | 根据图层索引查找 LayerBuilder |
| `layerContent(abuilder, layer_index)` | 获取指定图层的内容树（用于蒙版引用） |

## 内部实现细节

### 构造过程
1. 遍历 JSON "layers" 数组，为每个图层创建 LayerBuilder
2. 建立图层索引 -> LayerBuilder 索引的映射表（fLayerIndexMap）
3. 识别相机层（仅支持第一个）
4. 提前构建相机变换（3D 图层依赖相机变换）
5. 若无显式相机但有 3D 标记，使用默认相机

### 两阶段构建（build 方法）
1. **第一遍 - 变换链**: 遍历所有图层调用 buildTransform，递归解析父层关系
2. **第二遍 - 渲染树**: 遍历所有图层调用 buildRenderTree，构建完整渲染节点
3. 反转图层顺序（Lottie 是底部到顶部绘制）
4. 包装为 sksg::Group 或直接返回单图层

### 循环引用检测
ScopedAssetRef 通过 `fIsAttaching` 标志检测资产循环引用，防止无限递归。

## 依赖关系

- `modules/skottie/src/Layer.h` - LayerBuilder
- `modules/skottie/src/Camera.h` - CameraAdaper
- `modules/skottie/src/SkottiePriv.h` - AnimationBuilder
- `modules/sksg/include/SkSGGroup.h` - 场景图组节点

## 设计模式与设计决策

### 两阶段构建模式
分离变换和内容的构建解决了图层父子关系的前向依赖问题——子图层可能在父图层之前出现。

### 索引映射
fLayerIndexMap 将 Lottie 的 "ind" 索引映射到数组位置，支持非连续和非有序的图层索引。

### 不可复制设计
CompositionBuilder 继承 SkNoncopyable，防止意外复制导致的状态不一致。

## 性能考量

- fLayerBuilders 使用 vector 连续存储，缓存友好
- fLayerIndexMap 使用 THashMap 提供 O(1) 查找
- 单图层合成直接返回，不创建 Group 包装

## 相关文件

- `modules/skottie/src/Layer.h` - 图层构建器
- `modules/skottie/src/Camera.h` - 相机系统
- `modules/skottie/src/SkottiePriv.h` - 动画构建器
