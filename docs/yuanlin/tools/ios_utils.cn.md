# ios_utils

> 源文件：tools/ios_utils.h, tools/ios_utils.m

## 概述

`ios_utils` 是 Skia 工具库中为 iOS 平台提供的实用函数模块。该模块提供了 iOS 特定的文件系统操作，主要功能是将工作目录切换到应用的 Documents 目录。这在 iOS 应用中非常重要，因为 Documents 目录是应用沙盒中少数几个可以自由读写文件的位置之一，是保存测试输出、日志和临时文件的标准位置。

## 架构位置

- 位于 `tools/` 目录
- 使用 Objective-C (.m 扩展名)
- iOS 平台专用
- C 风格接口（兼容 C++）
- 用于 iOS 测试应用和工具

## 主要类与结构体

无类定义，仅提供一个全局函数。

### cd_Documents

```c
void cd_Documents(void);
```
- **功能**：切换当前工作目录到 Documents 目录
- **平台**：仅 iOS
- **用途**：确保文件 I/O 操作在可写位置进行

## 公共 API 函数

### cd_Documents
- **实现**：
  1. 使用 `NSFileManager` 查询 Documents 目录
  2. 获取目录的文件系统路径
  3. 调用 POSIX `chdir()` 切换工作目录
- **使用场景**：
  - 应用启动时调用
  - 在执行文件写入操作前调用
  - 测试工具初始化

## 内部实现细节

### iOS 目录查询

```objective-c
NSURL* dir = [[[NSFileManager defaultManager]
    URLsForDirectory:NSDocumentDirectory
           inDomains:NSUserDomainMask] lastObject];
```
- 使用 Foundation 框架的 `NSFileManager`
- 查询用户域的 Documents 目录
- 返回 `NSURL` 对象

### 目录切换

```objective-c
chdir([dir.path UTF8String]);
```
- 提取文件系统路径字符串
- 转换为 UTF-8 C 字符串
- 调用 POSIX `chdir()` 切换工作目录

### 自动释放池

```objective-c
@autoreleasepool {
    // Objective-C API 调用
}
```
管理 Foundation 对象的内存，防止泄漏。

## 依赖关系

**iOS 框架**：
- `<Foundation/Foundation.h>` - NSFileManager
- `<unistd.h>` - chdir()

**使用场景**：
- iOS 测试应用初始化
- Viewer 工具 iOS 版本
- DM（测试运行器）iOS 版本

## 设计模式与设计决策

### 外观模式
隐藏 iOS 特定的目录查询复杂性。

### C 接口
使用 C 风格接口确保 C++ 代码可直接调用。

### 关键决策
1. **C 接口**：避免暴露 Objective-C 到 C++ 头文件
2. **无返回值**：假设操作总是成功（Documents 目录始终存在）
3. **自动释放池**：正确管理 Foundation 对象内存
4. **单一职责**：仅处理目录切换，不创建目录

## 性能考量

- 轻量级操作，开销极小
- 建议在应用启动时调用一次
- 避免频繁调用（无必要）

## 相关文件

- `tools/ios_app/` - iOS 应用框架
- `tools/viewer/` - Viewer iOS 版本
- `dm/` - DM 测试运行器 iOS 支持
- `BUILD.gn` - iOS 目标构建配置
