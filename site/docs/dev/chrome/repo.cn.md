
---
title: "在 Chromium 仓库中工作"
linkTitle: "Working in a Chromium repo"

---


要在 Chromium 检出目录中使用 Skia，请运行以下命令：

    cd chromium/src/third_party/skia
    python3 tools/git-sync-deps
    bin/gn gen out/Debug

第二个命令为 Skia 执行一个最小化的"仅同步 DEPS"的 `gclient sync` 模拟，将依赖同步到 chromium/src/third_party/skia/third_party。之后，在 chromium/src/third_party/skia 中执行 `ninja -C out/Debug dm` 就可以开始工作了。

我们不再建议通过 .gclient 文件操作让 Chromium 的 DEPS 同时同步 Skia 的 DEPS。这些 DEPS 大多数仅用于构建和测试；Chromium 不需要其中任何一个，如果它们以某种方式混入 Chromium 构建中，可能会造成混淆和问题。
