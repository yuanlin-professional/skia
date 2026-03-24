# SkBlurMaskFilter

> 源文件: `include/effects/SkBlurMaskFilter.h`

## 概述
SkBlurMaskFilter 提供了创建浮雕(emboss)蒙版滤镜的工厂方法。该模块是 Skia 遗留 API 的一部分,主要用于向后兼容,当前仅在定义 SK_SUPPORT_LEGACY_EMBOSSMASKFILTER 宏时可用。现代 Skia 代码应使用 SkMaskFilter 的其他实现。

## 架构位置
SkBlurMaskFilter 位于 Skia 的效果(effects)模块,属于蒙版滤镜(SkMaskFilter)子系统的扩展功能。它为绘制对象提供浮雕效果,通过模拟光照在模糊表面上的反射来创建立体感。

## 主要类与结构体

### SkBlurMaskFilter
静态工厂类,用于创建浮雕蒙版滤镜。

**继承关系**: 无(静态工厂类)

**设计说明**:
- 该类不包含实例成员或方法
- 所有功能通过静态工厂方法提供
- 实际的滤镜对象类型为 sk_sp<SkMaskFilter>

## 公共 API 函数

### `MakeEmboss()`
```cpp
#ifdef SK_SUPPORT_LEGACY_EMBOSSMASKFILTER
static sk_sp<SkMaskFilter> MakeEmboss(SkScalar blurSigma,
                                      const SkScalar direction[3],
                                      SkScalar ambient,
                                      SkScalar specular);
#endif
```
- **功能**: 创建浮雕蒙版滤镜
- **参数**:
  - `blurSigma`: 高斯模糊的标准差(在应用光照前模糊),例如 3.0
  - `direction`: 长度为 3 的数组 [x, y, z],指定光源方向向量
  - `ambient`: 环境光量(范围 0.0 到 1.0)
  - `specular`: 镜面高光系数,控制高光强度(例如 8.0)
- **返回值**: sk_sp<SkMaskFilter> 智能指针,失败时可能返回 nullptr
- **可用性**: 仅在定义 SK_SUPPORT_LEGACY_EMBOSSMASKFILTER 时可用

## 内部实现细节

### 浮雕效果原理
浮雕滤镜通过以下步骤创建立体效果:
1. **模糊**: 使用高斯模糊软化图像边缘(blurSigma 控制)
2. **法线计算**: 从模糊后的 alpha 通道推导表面法线
3. **光照计算**: 使用 Phong 光照模型:
   - **环境光**: `ambient` 参数控制基础亮度
   - **漫反射**: 根据 direction 和法线计算
   - **镜面反射**: `specular` 系数控制高光强度
4. **最终合成**: 将光照结果应用到原始图像

### direction 参数详解
direction[3] 数组定义光源方向:
- **direction[0]**: X 分量(正值为从左向右)
- **direction[1]**: Y 分量(正值为从上到下)
- **direction[2]**: Z 分量(正值为从屏幕外指向内)

典型值示例:
```cpp
// 从左上方 45 度角照射
SkScalar direction[3] = {1.0f, 1.0f, 1.0f};

// 从正上方垂直照射
SkScalar direction[3] = {0.0f, 0.0f, 1.0f};

// 从右侧照射
SkScalar direction[3] = {1.0f, 0.0f, 0.5f};
```

### 参数范围建议
| 参数 | 典型范围 | 说明 |
|------|----------|------|
| blurSigma | 1.0 - 10.0 | 值越大,模糊越明显,浮雕越柔和 |
| ambient | 0.0 - 1.0 | 0.0 = 仅高光,1.0 = 完全环境光 |
| specular | 0.0 - 16.0 | 值越大,高光越强烈 |

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkBlurTypes.h | 模糊相关的类型定义 |
| include/core/SkMaskFilter.h | MaskFilter 基类 |
| include/core/SkRect.h | 矩形定义(可能用于边界计算) |
| include/core/SkScalar.h | 浮点类型定义 |

### 被依赖的模块
由于是遗留 API,现代代码很少直接使用:
- 旧版示例代码
- 向后兼容层
- 特定平台的遗留渲染路径

## 设计模式与设计决策

### 条件编译保护
使用 `#ifdef SK_SUPPORT_LEGACY_EMBOSSMASKFILTER` 包裹整个实现:
- **优点**: 默认不编译,减小二进制大小
- **用途**: 仅在明确需要时启用
- **迁移策略**: 鼓励使用现代替代方案

### 静态工厂模式
不直接暴露实现类,通过静态工厂方法创建:
- 隐藏实现细节
- 返回基类指针,保持灵活性
- 便于未来替换实现

### 遗留 API 标记
类名包含 "Blur" 但实际实现浮雕效果,反映了历史演变:
- 早期 Skia 将浮雕视为模糊的一种变体
- 现代设计已将概念分离

## 性能考量

### 计算成本
浮雕滤镜相对昂贵:
1. **高斯模糊**: O(n) 复杂度,取决于 blurSigma
2. **法线计算**: 需要梯度计算(相邻像素差分)
3. **光照计算**: 每像素的向量运算

### 优化建议
- 使用较小的 blurSigma(1-3)以提高性能
- 在静态内容上缓存结果
- 考虑使用预渲染的浮雕纹理

### GPU 加速
该滤镜可能不支持 GPU 加速(取决于后端实现),在 GPU 路径上可能回退到 CPU。

## 替代方案

### 现代替代方法
推荐使用以下替代方案:

#### 1. SkImageFilters 组合
```cpp
// 使用图像滤镜实现类似效果
auto blur = SkImageFilters::Blur(sigma, sigma, nullptr);
auto lighting = SkImageFilters::DistantLitSpecular(direction, color,
                                                    surfaceScale, ks,
                                                    shininess, blur);
```

#### 2. 自定义 SkShader
使用 SkRuntimeEffect 实现自定义光照 shader。

#### 3. 图层合成
通过多个图层和混合模式手动合成浮雕效果。

## 使用场景

### 适用场景(如果启用)
- 文本浮雕效果
- UI 元素的立体感
- 模拟物理材质(皮革、金属)

### 不适用场景
- 高性能实时渲染(考虑性能开销)
- 现代应用(应使用新 API)
- 需要 GPU 加速的场景

## 平台相关说明

### 编译配置
要使用此 API,需要在编译时定义:
```cpp
#define SK_SUPPORT_LEGACY_EMBOSSMASKFILTER
```

通常在 `SkUserConfig.h` 或编译选项中设置。

### 平台差异
- **移动平台**: 可能因性能原因被禁用
- **Web 平台**: SkiaWasm 可能不包含此功能
- **桌面平台**: 通常支持,但不推荐使用

## 示例代码

### 基础浮雕效果
```cpp
#ifdef SK_SUPPORT_LEGACY_EMBOSSMASKFILTER
SkPaint paint;
SkScalar direction[3] = {1.0f, 1.0f, 1.0f};  // 从左上方照射
auto emboss = SkBlurMaskFilter::MakeEmboss(3.0f,    // blurSigma
                                           direction,
                                           0.4f,     // ambient
                                           8.0f);    // specular
paint.setMaskFilter(emboss);
canvas->drawText("Embossed", 7, 100, 100, paint);
#endif
```

### 参数调整示例
```cpp
// 柔和浮雕
MakeEmboss(5.0f, direction, 0.6f, 4.0f);  // 高模糊,低高光

// 锐利浮雕
MakeEmboss(1.5f, direction, 0.2f, 12.0f); // 低模糊,高高光
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkMaskFilter.h | 基类定义 |
| src/effects/SkEmbossMaskFilter.cpp | 可能的实现文件(如果存在) |
| include/core/SkBlurTypes.h | 模糊类型定义 |
| include/effects/SkImageFilters.h | 现代替代方案(光照滤镜) |
| src/core/SkMaskBlurFilter.cpp | 相关的模糊实现 |
