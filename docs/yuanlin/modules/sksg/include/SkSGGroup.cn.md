# SkSGGroup

> 源文件: modules/sksg/include/SkSGGroup.h

## 概述

SkSGGroup 是 Skia 场景图系统中的容器节点，用于组合多个渲染节点（RenderNode）形成树状或有向无环图（DAG）结构。Group 节点本身不产生可视内容，而是作为子节点的组织者，管理子节点的渲染顺序、边界计算和失效传播。

Group 类继承自 RenderNode，提供了添加、删除、清空子节点的接口，支持动态修改场景图结构。它是构建复杂场景层次的基础组件，类似于 HTML DOM 中的容器元素或 SVG 中的 g 元素。

## 架构位置

在 Skia 场景图架构中的位置：

- **继承关系**: Group → RenderNode → Node
- **功能定位**: 组合型渲染节点，实现场景图的层次结构
- **子节点类型**: 持有 RenderNode 子节点（Image、Draw、其他 Group 等）
- **设计模式**: 组合模式（Composite Pattern）的典型实现
- **模块位置**: modules/sksg 核心模块

Group 是场景图树结构的关键，支持：
- 嵌套分组（Group 可包含 Group）
- 子节点的批量管理
- 统一的变换和效果应用（通过包装 Group）

## 主要类与结构体

### Group 类

```cpp
class Group : public RenderNode {
public:
    // 工厂方法
    static sk_sp<Group> Make();
    static sk_sp<Group> Make(std::vector<sk_sp<RenderNode>> children);

    // 子节点管理
    void addChild(sk_sp<RenderNode>);
    void removeChild(const sk_sp<RenderNode>&);
    void clear();

    // 查询接口
    size_t size() const { return fChildren.size(); }
    bool empty() const { return fChildren.empty(); }

protected:
    Group();
    explicit Group(std::vector<sk_sp<RenderNode>>);
    ~Group() override;

    void onRender(SkCanvas*, const RenderContext*) const override;
    const RenderNode* onNodeAt(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;

private:
    std::vector<sk_sp<RenderNode>> fChildren;
    bool fRequiresIsolation = true;

    using INHERITED = RenderNode;
};
```

**关键成员**:
- `fChildren`: 子节点向量，按渲染顺序存储
- `fRequiresIsolation`: 是否需要渲染隔离（图层分离）

## 公共 API 函数

### 工厂方法

#### Make()
```cpp
static sk_sp<Group> Make();
```
创建空的 Group 节点，可后续添加子节点。

#### Make(children)
```cpp
static sk_sp<Group> Make(std::vector<sk_sp<RenderNode>> children);
```
创建包含初始子节点集合的 Group。参数使用移动语义，避免拷贝。

**使用示例**:
```cpp
auto group = sksg::Group::Make({
    sksg::Image::Make(image1),
    sksg::Image::Make(image2),
    sksg::Draw::Make(geometry, paint)
});
```

### 子节点管理

#### addChild()
```cpp
void addChild(sk_sp<RenderNode>);
```
添加子节点到 Group 末尾。新节点将在现有子节点之后渲染。

**副作用**:
- 建立父子观察关系（observeInval）
- 触发 Group 失效
- 子节点失效会传播到 Group

#### removeChild()
```cpp
void removeChild(const sk_sp<RenderNode>&);
```
从 Group 中移除指定子节点。

**参数**: 要移除节点的智能指针引用（通过指针相等性查找）

**副作用**:
- 解除父子观察关系（unobserveInval）
- 触发 Group 失效
- 若节点不存在，通常为空操作

#### clear()
```cpp
void clear();
```
移除所有子节点，Group 变为空。

**副作用**:
- 批量解除观察关系
- 触发 Group 失效
- 释放子节点引用（可能触发析构）

### 查询接口

#### size()
```cpp
size_t size() const;
```
返回子节点数量。

#### empty()
```cpp
bool empty() const;
```
检查 Group 是否为空（无子节点）。

## 内部实现细节

### 渲染实现 (onRender)

Group 的渲染逻辑：
1. 遍历 fChildren 向量
2. 按顺序调用每个子节点的 render() 方法
3. 传递相同的 SkCanvas 和 RenderContext
4. 子节点的渲染相互叠加（画家算法）

**渲染隔离**:
- 如果 fRequiresIsolation 为 true，可能创建独立图层
- 隔离用于处理复杂混合模式或透明度效果
- 防止子节点与外部内容的非预期混合

### 命中测试 (onNodeAt)

实现从后向前的命中测试：
1. 反向遍历 fChildren（后渲染的在上层）
2. 对每个子节点调用 nodeAt()
3. 返回第一个命中的节点
4. 若无命中返回 nullptr

这符合视觉层叠顺序的直觉：上层元素优先响应点击。

### 重验证 (onRevalidate)

边界计算逻辑：
1. 初始化空边界框
2. 遍历所有子节点
3. 调用子节点的 revalidate() 获取边界
4. 使用 SkRect::join() 合并所有子边界
5. 返回联合边界框

**变换传递**:
- 将当前变换矩阵传递给子节点
- 子节点在各自坐标系计算边界
- Group 收集并统一到自己的坐标系

### 观察者管理

- addChild() 时调用 `observeInval(child)`
- removeChild() 时调用 `unobserveInval(child)`
- 确保子节点失效能正确传播到 Group
- Group 失效进一步传播到其父节点

### 析构处理

析构函数需要：
1. 遍历所有子节点
2. 解除观察关系
3. 释放智能指针引用
4. 调用基类析构函数

## 依赖关系

### 核心依赖
- **include/core/SkRect.h**: 边界框
- **include/core/SkRefCnt.h**: 引用计数
- **modules/sksg/include/SkSGRenderNode.h**: 渲染节点基类

### 渲染依赖
- **SkCanvas**: 画布，用于渲染
- **SkMatrix**: 变换矩阵
- **SkPoint**: 点坐标（命中测试）

### 场景图依赖
- **InvalidationController**: 失效管理

### 标准库
- **<cstddef>**: size_t 类型
- **<utility>**: std::move
- **<vector>**: 子节点存储

## 设计模式与设计决策

### 1. 组合模式（Composite Pattern）
Group 实现了经典的组合模式：
- 统一对待单个节点和节点集合
- Group 本身也是 RenderNode，可作为其他 Group 的子节点
- 递归结构天然支持树状场景图

### 2. 顺序渲染（Painter's Algorithm）
子节点按添加顺序渲染：
- 后添加的节点覆盖先添加的节点
- 直观符合图层堆叠的概念
- 简单高效，无需 Z-ordering

### 3. 动态数组存储
使用 vector 而非链表存储子节点：
- 缓存友好，遍历性能优
- 随机访问能力（虽然当前未暴露）
- 添加/删除可能触发重新分配，但通常不频繁

### 4. 智能指针管理
使用 sk_sp 管理子节点：
- 自动生命周期管理
- 支持子节点共享（DAG 而非纯树）
- 防止循环引用（通过观察者模式而非父指针）

### 5. 工厂方法隐藏构造
构造函数为 protected/private：
- 强制使用 Make() 工厂方法
- 确保对象通过智能指针管理
- 提供不同初始化方式的统一接口

### 6. 渲染隔离标志
fRequiresIsolation 提供优化机会：
- 简单场景可避免图层创建
- 复杂混合模式强制隔离
- 平衡性能和正确性

## 性能考量

### 1. 子节点遍历
渲染和重验证都需要遍历子节点：
- 时间复杂度 O(n)，n 为子节点数量
- vector 的连续内存布局提升缓存性能
- 对于大量子节点，考虑分组优化

### 2. 边界计算累积
每个子节点的边界计算可能触发递归：
- 深层嵌套可能影响性能
- 缓存机制减轻影响（只重验证失效节点）
- 扁平化结构可能更高效

### 3. 添加/删除开销
- addChild: O(1) 均摊（vector push_back）
- removeChild: O(n) 查找 + O(n) 删除
- clear: O(n) 遍历解除观察

频繁修改不推荐，场景图通常相对静态。

### 4. 渲染隔离代价
创建图层（saveLayer）有显著开销：
- 额外的绘制表面分配
- Alpha 合成操作
- 只在必要时使用

### 5. 智能指针开销
每个子节点的引用计数操作：
- 添加/删除时原子增减
- 对于大量子节点累积开销明显
- 相比手动内存管理，简洁性值得

### 6. 反向遍历命中测试
onNodeAt 反向遍历：
- 最坏 O(n) 检查所有子节点
- 早期退出优化（找到即返回）
- 对于深层 Group 可能慢，考虑空间分区

## 相关文件

### 头文件
- **modules/sksg/include/SkSGRenderNode.h**: RenderNode 基类
- **modules/sksg/include/SkSGNode.h**: Node 基类

### 实现文件
- **modules/sksg/src/SkSGGroup.cpp**: Group 类实现

### 相关节点
- **SkSGImage.h**: 可作为 Group 子节点的图像节点
- **SkSGDraw.h**: 可作为子节点的绘制节点
- **SkSGTransform.h**: 可包装 Group 应用变换
- **SkSGOpacityEffect.h**: 可包装 Group 应用透明度
- **SkSGClipEffect.h**: 可包装 Group 应用裁剪

### 使用场景
- **modules/skottie**: Lottie 动画中的图层组合
- UI 布局系统中的容器
- 复杂图形的模块化组织
- 动画中的关键帧插值（整组变换）

### 示例模式
```cpp
// 创建分组场景
auto background = sksg::Group::Make();
background->addChild(createSkyNode());
background->addChild(createGroundNode());

auto foreground = sksg::Group::Make();
foreground->addChild(createCharacterNode());
foreground->addChild(createUINode());

auto scene = sksg::Group::Make();
scene->addChild(std::move(background));
scene->addChild(std::move(foreground));
```
