# SkAndroidFrameworkUtils

> 源文件: `include/android/SkAndroidFrameworkUtils.h`, `src/android/SkAndroidFrameworkUtils.cpp`

## 概述

SkAndroidFrameworkUtils 暴露仅供 Android 框架使用的私有 API 集合。这些工具函数提供模板缓冲区裁剪、安全网日志记录、画布操作、着色器信息提取等功能,是 Skia 与 Android 平台深度集成的桥梁。

## 架构位置

- **所属子系统**: Android 平台集成层
- **层级**: 平台适配 - 框架工具
- **作用域**: 仅限 Android 框架内部使用的辅助函数

## 主要类与结构体

### SkAndroidFrameworkUtils

纯静态工具类,所有方法为静态。

**继承关系**: 无

### LinearGradientInfo

用于从 SkShader 提取线性渐变信息的结构体。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fColorCount | int | 输入/输出,颜色数量 |
| fColors | SkColor4f* | 颜色数组指针 |
| fColorOffsets | SkScalar* | 颜色偏移数组指针(0-1) |
| fPoints[2] | SkPoint | 渐变起点和终点 |
| fTileMode | SkTileMode | 平铺模式 |
| fGradientFlags | uint32_t | 渐变标志(premul 等) |

## 公共 API 函数

### `static bool clipWithStencil(SkCanvas* canvas)` [仅 SK_GANESH]
- **功能**: 使用模板缓冲区绘制当前裁剪区域
- **参数**: `canvas` - GPU 画布,必须有非空裁剪
- **返回值**: 成功返回 true,裁剪为空或非 GPU 画布返回 false
- **条件编译**: 仅在 SK_GANESH 定义时可用
- **实现**: 调用 `canvas->rootDevice()->android_utils_clipWithStencil()`
- **用途**: Android 框架在某些混合模式下使用模板缓冲区

### `static void SafetyNetLog(const char* bugNumber)`
- **功能**: 记录安全网日志(仅在 Android 框架构建时生效)
- **参数**: `bugNumber` - bug 编号字符串
- **返回值**: 无
- **条件编译**: 仅在 SK_BUILD_FOR_ANDROID_FRAMEWORK 定义时有效
- **实现**: 调用 `android_errorWriteLog(0x534e4554, bugNumber)`
- **用途**: 追踪安全漏洞利用尝试

### `static sk_sp<SkSurface> getSurfaceFromCanvas(SkCanvas* canvas)`
- **功能**: 从画布获取底层 SkSurface
- **参数**: `canvas` - 目标画布
- **返回值**: SkSurface 智能指针,可能为空
- **实现**: `SkSafeRef(canvas->getSurfaceBase())`
- **用途**: 访问画布的像素缓冲区

### `static int SaveBehind(SkCanvas* canvas, const SkRect* subset)`
- **功能**: 保存画布区域用于后续恢复(用于优化某些绘制操作)
- **参数**:
  - `canvas` - 目标画布
  - `subset` - 要保存的区域,nullptr 表示整个画布
- **返回值**: 保存层的 ID
- **实现**: 调用 `canvas->only_axis_aligned_saveBehind(subset)`
- **用途**: Android 视图系统的优化渲染

### `static void ResetClip(SkCanvas* canvas)`
- **功能**: 重置画布裁剪栈,使其完全打开(除了设备裁剪限制)
- **参数**: `canvas` - 目标画布
- **返回值**: 无
- **实现**: 调用 `canvas->internal_private_resetClip()`
- **用途**: 框架需要绕过常规裁剪逻辑

### `static SkCanvas* getBaseWrappedCanvas(SkCanvas* canvas)`
- **功能**: 递归解包嵌套的 SkPaintFilterCanvas,返回最底层画布
- **参数**: `canvas` - 可能被包装的画布
- **返回值**: 最内层的 SkCanvas 指针
- **实现**:
  ```cpp
  auto pfc = canvas->internal_private_asPaintFilterCanvas();
  while (pfc) {
      result = pfc->proxy();
      pfc = result->internal_private_asPaintFilterCanvas();
  }
  return result;
  ```
- **用途**: 访问原始画布,绕过过滤器层

### `static bool ShaderAsALinearGradient(SkShader* shader, LinearGradientInfo* info)`
- **功能**: 检查着色器是否为线性渐变,并提取参数
- **参数**:
  - `shader` - 要检查的着色器
  - `info` - 输出参数,可为 nullptr 仅检查类型
- **返回值**: 是线性渐变返回 true
- **实现**: 调用 `as_SB(shader)->asGradient()`
- **用途**: Android 框架优化渐变绘制

## 内部实现细节

### SafetyNet 日志机制

```cpp
void SkAndroidFrameworkUtils::SafetyNetLog(const char* bugNumber) {
#ifdef SK_BUILD_FOR_ANDROID_FRAMEWORK
    android_errorWriteLog(0x534e4554, bugNumber);
#endif
}
```

**0x534e4554 含义**: ASCII 编码的 "SNET"(SafetyNet)

**使用场景**:
- 检测到已知安全漏洞的利用尝试
- 记录异常 API 使用模式
- 用于 Android 安全团队分析

### 画布解包算法

```cpp
SkCanvas* getBaseWrappedCanvas(SkCanvas* canvas) {
    auto pfc = canvas->internal_private_asPaintFilterCanvas();
    auto result = canvas;
    while (pfc) {
        result = pfc->proxy();
        pfc = result->internal_private_asPaintFilterCanvas();
    }
    return result;
}
```

**解包层次示例**:
```
FilterCanvas1(Alpha=0.5)
  └─ FilterCanvas2(ColorMatrix)
      └─ FilterCanvas3(Blur)
          └─ BaseCanvas (返回此)
```

### 线性渐变信息提取

```cpp
bool ShaderAsALinearGradient(SkShader* shader, LinearGradientInfo* info) {
    std::optional<SkShaderBase::GradientInfo> baseInfo;
    if (info) {
        baseInfo.emplace();
        baseInfo->fColorCount = info->fColorCount;
        baseInfo->fColors = info->fColors;
        baseInfo->fColorOffsets = info->fColorOffsets;
    }

    if (as_SB(shader)->asGradient(baseInfo) != GradientType::kLinear) {
        return false;
    }

    if (info) {
        info->fColorCount = baseInfo->fColorCount;  // inout
        info->fPoints[0] = baseInfo->fPoint[0];
        info->fPoints[1] = baseInfo->fPoint[1];
        info->fTileMode = baseInfo->fTileMode;
        info->fGradientFlags = baseInfo->fPremulInterp ?
            gSkGradientShader_Legacy_PremulFlag : 0;
    }
    return true;
}
```

**旧版标志兼容**:
```cpp
constexpr uint8_t gSkGradientShader_Legacy_PremulFlag = 1;
```
Skia 现在使用 bool,但 Android 框架期望旧的位标志。

### ResetClip 工作原理

正常裁剪栈:
```
Device Clip (屏幕边界)
  └─ ClipRect(10, 10, 100, 100)
      └─ ClipPath(圆形)
```

调用 ResetClip() 后:
```
Device Clip (屏幕边界)
  └─ (清空所有用户裁剪)
```

用途: 允许框架在特定场景下绘制到整个屏幕。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkCanvas | 画布操作 |
| SkDevice | 设备层访问 |
| SkShaderBase | 着色器类型检测 |
| SkSurface_Base | Surface 内部接口 |
| SkPaintFilterCanvas | 画布解包 |
| SkGradient | 渐变着色器 |

### 被依赖的模块
- **Android Framework**: 通过 JNI 调用这些工具函数
- **HWUI (Android Hardware UI)**: 图形渲染管道
- **Android 系统服务**: 特殊效果和优化

## 设计模式与设计决策

### 设计模式
1. **门面模式**: 隐藏 Skia 内部 API,提供简化接口
2. **适配器模式**: 转换 Skia 数据结构到 Android 期望格式

### 设计决策

**为什么独立于公共 API?**
- 这些功能不应暴露给第三方应用
- 允许 Skia 修改内部实现而不影响公共 API
- 明确标记为框架专用

**为什么使用条件编译?**
- 某些功能仅在特定后端可用(如 Ganesh GPU)
- 减少非 Android 平台的二进制大小
- 避免链接不必要的依赖

**为什么需要 getBaseWrappedCanvas?**
- Android 框架大量使用 PaintFilterCanvas 应用效果
- 某些操作需要访问原始画布
- 提供统一的解包机制

**为什么保留旧版渐变标志?**
- 二进制兼容性:Android 框架依赖旧的位标志
- 避免大规模重构 Android 代码
- 内部转换,不影响 Skia 现代化

## 性能考量

### 时间复杂度
- `clipWithStencil()`: O(pixels) - GPU 渲染
- `SafetyNetLog()`: O(1) - 日志写入
- `getSurfaceFromCanvas()`: O(1) - 指针访问
- `SaveBehind()`: O(1) - 保存层元数据
- `ResetClip()`: O(1) - 清空栈
- `getBaseWrappedCanvas()`: O(N) - N 为包装层数,通常 ≤ 3
- `ShaderAsALinearGradient()`: O(1) - 类型检查和拷贝

### 性能影响
- **clipWithStencil**: GPU 密集,但避免 CPU 裁剪开销
- **SaveBehind**: 优化重绘,减少不必要的绘制
- **ResetClip**: 极快,仅修改栈指针

### 优化策略
- 最小化包装层深度
- 缓存解包后的画布指针
- 避免频繁调用 SafetyNetLog

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkCanvas.h | 画布公共接口 |
| src/core/SkDevice.h | 设备层实现 |
| include/utils/SkPaintFilterCanvas.h | 过滤画布 |
| src/shaders/SkShaderBase.h | 着色器基类 |

## 使用示例(Android 框架内部)

### 示例 1: 使用模板缓冲区裁剪
```cpp
// Android HWUI 代码
if (SkAndroidFrameworkUtils::clipWithStencil(canvas)) {
    // 成功写入模板,使用模板测试绘制
    canvas->drawPaint(paint);
} else {
    // 回退到传统裁剪
    canvas->clipPath(complexPath);
    canvas->drawPaint(paint);
}
```

### 示例 2: 记录安全网日志
```cpp
// 检测到可疑操作
if (suspiciousBehavior) {
    SkAndroidFrameworkUtils::SafetyNetLog("123456789");
}
```

### 示例 3: 解包过滤画布
```cpp
SkCanvas* filtered = createFilteredCanvas(...);
SkCanvas* base = SkAndroidFrameworkUtils::getBaseWrappedCanvas(filtered);
// 直接操作底层画布
```

### 示例 4: 提取渐变信息
```cpp
SkAndroidFrameworkUtils::LinearGradientInfo info;
info.fColorCount = 10;
SkColor4f colors[10];
SkScalar offsets[10];
info.fColors = colors;
info.fColorOffsets = offsets;

if (SkAndroidFrameworkUtils::ShaderAsALinearGradient(shader, &info)) {
    // 使用硬件加速渐变
    for (int i = 0; i < info.fColorCount; ++i) {
        useColor(colors[i], offsets[i]);
    }
}
```

### 示例 5: 保存背后内容
```cpp
SkRect dirtyRect = SkRect::MakeXYWH(10, 10, 100, 100);
int saveId = SkAndroidFrameworkUtils::SaveBehind(canvas, &dirtyRect);
// 绘制新内容
canvas->drawRect(dirtyRect, paint);
canvas->restoreToCount(saveId);
```

## 安全考量

### SafetyNet 日志的重要性
1. **漏洞追踪**: 记录已知漏洞的利用尝试
2. **威胁情报**: 聚合数据帮助发现新攻击模式
3. **合规要求**: 满足 Android 安全审计要求

### 使用限制
- 仅在检测到真实威胁时调用
- 不记录用户隐私数据
- Bug 编号应映射到公开的 CVE

### 隐私保护
- SafetyNet 日志不包含个人信息
- 仅记录事件类型和时间戳
- 符合 Android 隐私政策

## 注意事项

1. **仅限框架使用**: 这些 API 不稳定,随时可能更改
2. **条件可用性**: 某些功能仅在特定构建配置可用
3. **性能影响**: clipWithStencil 在某些硬件上可能较慢
4. **线程安全**: 大多数函数不是线程安全的
5. **生命周期**: 返回的指针生命周期与输入参数相关
6. **向后兼容**: 旧版标志转换确保 Android 版本兼容性
7. **错误处理**: 大多数函数假设输入有效,调用者负责验证

## 编译时配置

### SK_GANESH
```cpp
#if defined(SK_GANESH)
bool SkAndroidFrameworkUtils::clipWithStencil(SkCanvas* canvas) {
    return canvas->rootDevice()->android_utils_clipWithStencil();
}
#endif
```
未定义时,clipWithStencil 函数不存在。

### SK_BUILD_FOR_ANDROID_FRAMEWORK
```cpp
void SkAndroidFrameworkUtils::SafetyNetLog(const char* bugNumber) {
#ifdef SK_BUILD_FOR_ANDROID_FRAMEWORK
    android_errorWriteLog(0x534e4554, bugNumber);
#endif
}
```
非 Android 框架构建时,SafetyNetLog 为空操作。
