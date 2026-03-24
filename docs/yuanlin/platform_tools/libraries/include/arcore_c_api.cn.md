# arcore_c_api.h - ARCore C API 头文件

> 源文件: `platform_tools/libraries/include/arcore_c_api.h`

## 概述

本文件是 Google ARCore（增强现实核心）SDK 的 C 语言 API 头文件，定义了用于 Android 平台增强现实应用开发的完整 C 接口。该文件包含了 ARCore 的所有核心概念：会话管理、相机控制、平面检测、锚点定位、点云处理、增强图像识别、光照估计、命中测试等功能的类型定义、枚举常量和函数声明。这是 Skia 项目中用于 Android 平台 AR 功能集成的外部依赖头文件。

## 架构位置

该文件位于 `platform_tools/libraries/include/` 目录下，是 Skia 项目中引入的第三方库头文件。在 Skia 的架构中，它主要服务于 Android 平台工具和示例程序，提供 AR 功能的底层 API 访问能力。它不是 Skia 渲染引擎的核心组件，而是平台特定的集成支持文件。

## 主要类与结构体

### 核心会话类型
- **`ArSession`**: ARCore 会话对象（值类型），管理 AR 系统的整个生命周期
- **`ArConfig`**: 会话配置对象（值类型），控制 AR 功能的启用和参数设置
- **`ArFrame`**: 每帧状态对象（值类型），包含当前帧的所有 AR 数据

### 空间定位类型
- **`ArPose`**: 刚体变换（值类型），表示从物体局部坐标系到世界坐标系的变换（四元数旋转 + 平移）
- **`ArAnchor`**: 锚点（引用类型，长生命周期），描述现实世界中的固定位置和朝向
- **`ArAnchorList`**: 锚点列表（值类型），持有锚点引用

### 环境感知类型
- **`ArPlane`**: 检测到的平面（引用类型），描述现实世界的平面表面
- **`ArPoint`**: 跟踪点（引用类型），表示 ARCore 跟踪的空间点
- **`ArPointCloud`**: 点云数据（引用类型，瞬态大数据），包含观测到的 3D 点集和置信度值
- **`ArCamera`**: 相机（引用类型），提供相机内参、投影矩阵、跟踪状态等信息
- **`ArLightEstimate`**: 光照估计（值类型），提供环境光照的估计信息

### 图像与数据类型
- **`ArImage`**: CPU 图像数据（引用类型，瞬态大数据）
- **`ArAugmentedImage`**: 增强图像（引用类型），被检测和跟踪的参考图像
- **`ArAugmentedImageDatabase`**: 图像数据库（值类型），待检测图像的集合
- **`ArImageMetadata`**: 图像元数据，提供相机拍摄参数访问

### 可跟踪对象基类
- **`ArTrackable`**: 可跟踪对象（引用类型），Plane、Point、AugmentedImage 的基类型
- **`ArTrackableList`**: 可跟踪对象列表（值类型）
- **`ArHitResult`**: 命中测试结果，描述射线与估计几何体的交点
- **`ArHitResultList`**: 命中测试结果列表

### 枚举类型（部分）
- **`ArTrackingState`**: 跟踪状态（Tracking、Paused、Stopped）
- **`ArPlaneType`**: 平面类型（水平向上、水平向下、垂直）
- **`ArLightEstimationMode`**: 光照估计模式（禁用、环境光强度）
- **`ArPlaneFindingMode`**: 平面检测模式（禁用、水平、垂直、全部）
- **`ArUpdateMode`**: 帧更新模式（阻塞、最新可用）
- **`ArCloudAnchorState`**: 云锚点状态（各种成功/错误状态）

## 公共 API 函数

### 会话管理
- **`ArSession_create()`**: 创建 AR 会话
- **`ArSession_destroy()`**: 销毁 AR 会话
- **`ArSession_configure()`**: 配置会话参数
- **`ArSession_resume()` / `ArSession_pause()`**: 恢复/暂停 AR 跟踪
- **`ArSession_update()`**: 更新帧数据

### 姿态操作
- **`ArPose_create()` / `ArPose_destroy()`**: 创建/销毁姿态对象
- **`ArPose_getPoseRaw()`**: 获取原始姿态数据（四元数 + 平移）
- **`ArPose_getMatrix()`**: 获取 4x4 变换矩阵

### 相机与帧
- **`ArFrame_acquireCamera()`**: 获取当前帧的相机引用
- **`ArCamera_getProjectionMatrix()`**: 获取投影矩阵
- **`ArCamera_getViewMatrix()`**: 获取视图矩阵
- **`ArCamera_getTrackingState()`**: 获取跟踪状态
- **`ArFrame_hitTest()`**: 执行命中测试

### 平面与锚点
- **`ArSession_getAllTrackables()`**: 获取所有可跟踪对象
- **`ArPlane_getCenterPose()`**: 获取平面中心姿态
- **`ArPlane_getPolygon()`**: 获取平面多边形边界
- **`ArSession_acquireNewAnchor()`**: 在指定位置创建新锚点
- **`ArAnchor_getPose()`**: 获取锚点姿态

### 增强图像
- **`ArAugmentedImageDatabase_create()`**: 创建图像数据库
- **`ArAugmentedImageDatabase_addImage()`**: 添加参考图像
- **`ArAugmentedImage_getCenterPose()`**: 获取检测到的图像中心姿态

## 内部实现细节

### 对象所有权模型
ARCore 采用双层所有权模型：
- **值类型**: 应用程序拥有，通过 `create`/`destroy` 方法管理生命周期
- **引用类型**: ARCore 拥有，通过 `acquire`/`release` 方法管理引用计数

引用类型进一步分为：
- **长生命周期对象**: 跨帧持久存在（如 Anchor、Plane）
- **瞬态大数据**: 通常每帧获取，资源有限（如 Image、PointCloud）

### 坐标系统
- 右手坐标系（OpenGL 惯例）
- 平移单位为米
- 姿态表示为：先绕原点进行四元数旋转，再进行平移
- 每帧的世界坐标系可能因环境理解更新而变化

### 云锚点
支持通过 Google Cloud 共享锚点，允许多设备协作 AR 体验。提供了完整的状态机来跟踪托管和解析操作的进展。

## 依赖关系

- **`<stddef.h>`**: `size_t` 等基本类型
- **`<stdint.h>`**: 固定宽度整数类型
- **Android NDK**: 运行时依赖 ARCore 服务 APK
- **OpenGL ES**: 纹理更新等操作需要有效的 GL 上下文

## 设计模式与设计决策

- **C API 设计**: 使用纯 C 接口而非 C++，确保最大的 ABI 兼容性和语言互操作性
- **不透明指针模式**: 所有类型通过 `typedef struct ArXxx_ ArXxx` 定义为不透明指针，隐藏内部实现
- **资源获取/释放配对**: 严格的 `acquire`/`release` 和 `create`/`destroy` 配对设计，防止资源泄漏
- **错误码返回**: 大多数函数返回 `ArStatus` 枚举值指示操作结果
- **const 正确性**: 只读参数标记为 `const`，明确 API 的读写语义

## 性能考量

- 瞬态大数据（如 PointCloud、Image）采用资源池设计，避免频繁分配/释放
- `ArSession_update()` 是性能关键路径，需要在每帧调用以获取最新的 AR 数据
- 平面检测模式可配置为仅检测水平或垂直平面，减少不必要的计算
- 光照估计可禁用以节省计算资源
- 列表操作使用预分配的值类型对象，避免每次查询都分配新内存
- 增强图像数据库的构建是一次性开销，运行时检测采用优化的特征匹配算法
- 云锚点操作是异步的，不会阻塞渲染线程
- 锚点数量应该适度控制，过多锚点会增加每帧更新的计算负担
- `ArPointCloud` 获取应该及时释放，因为它是有限的瞬态资源
- 姿态查询（`getPose`）返回的是快照数据，不需要持有锚点的引用

### API 版本兼容性

该文件对应的 ARCore SDK 版本中包含了对以下功能的支持：
- 基本平面检测和锚点管理
- 增强图像检测和跟踪
- 点云数据获取
- 光照估计
- 云锚点（多设备共享）
- 相机纹理更新和投影计算

较新版本的 ARCore SDK 可能包含此文件中未涵盖的 API（如深度 API、地理空间 API 等）。

### 线程安全

ARCore API 通常不是线程安全的。所有 API 调用应在同一线程（通常是 OpenGL 渲染线程）上进行。会话的 `update()` 和帧数据的读取必须在相同线程上顺序执行。

### 内存管理最佳实践

- 值类型对象应在使用完毕后及时调用 `destroy` 方法释放
- 引用类型对象的 `acquire`/`release` 调用必须严格配对
- 列表对象持有的引用在列表被销毁或重新填充时自动释放
- 避免在帧边界之外持有 `ArFrame` 引用
- `ArPointCloud` 等瞬态大数据应尽快释放，避免资源耗尽

### 错误处理

大多数 API 函数返回 `ArStatus` 枚举值：
- `AR_SUCCESS`: 操作成功
- `AR_ERROR_*`: 各种错误状态（无效参数、资源不可用、不支持的配置等）
- 某些 `acquire` 操作在资源耗尽或目标已释放时返回 `nullptr`

## 相关文件

- `platform_tools/libraries/` - Skia 平台工具的外部库目录
- `platform_tools/android/` - Android 平台特定工具
- `example/external_client/` - 外部客户端示例（可能使用 AR 功能）
- ARCore SDK 官方文档: https://developers.google.com/ar/reference/c
- `include/core/SkCanvas.h` - Skia 画布 API（用于渲染 AR 内容）
- `include/core/SkSurface.h` - Skia Surface API

### 版本信息

本文件对应的 ARCore SDK 版本为 2017 年的初始公开版本。后续版本可能包含更多 API（如深度 API、地理空间锚点、场景语义等），但此文件中未包含这些较新功能的声明。在 Skia 项目中，此文件主要作为编译时依赖，提供 ARCore C API 的类型声明和函数原型，不包含实际实现代码。

### 与 Skia 渲染的集成点

ARCore 与 Skia 的主要集成点包括：
- 相机纹理更新（`ArFrame_acquireCamera`）提供的图像数据可通过 Skia 渲染
- AR 锚点和平面的姿态数据可用于变换 Skia 绘图操作
- 光照估计数据可影响 Skia 渲染的着色参数

### 文件规模说明

本头文件超过 2200 行，是 Skia 项目中最大的单个头文件之一。其体积庞大的原因包括：
- 完整的 Doxygen 风格文档注释
- 大量的 `typedef struct` 前向声明
- 多个功能模块的枚举定义（跟踪状态、平面类型、光照模式等）
- 全面的函数声明覆盖了 ARCore 的所有公共 API
- 详细的对象所有权和生命周期文档

由于这是第三方库头文件的本地副本，Skia 项目不直接修改其内容，而是在需要时更新到新版本的 ARCore SDK。

### 预处理器保护

文件使用标准的头文件保护宏 `ARCORE_C_API_H_`，确保在同一编译单元中多次包含时不会产生重复定义错误。所有类型定义都使用 `typedef` 而非 C++ 的 `class`/`struct` 关键字，确保纯 C 兼容性。

### 函数调用约定

所有 ARCore C API 函数使用默认的平台调用约定（cdecl），无需特殊的调用约定标注。函数参数中的输出参数通常放在参数列表末尾，遵循 Google C API 的设计惯例。
