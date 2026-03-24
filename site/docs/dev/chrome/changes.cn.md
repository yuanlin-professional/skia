
---
title: "Chrome 更改"
linkTitle: "Chrome changes"

---


如果您的更改修改了 Skia API，您可能还需要在 Chromium 中提交一个更改。

您用于同步 Skia 和 Chromium 仓库更改的策略可能因更改的性质而异，但一般来说，我们建议使用构建标志抑制（定义）。
我们也倾向于尽可能让旧代码路径变为选择加入 (Opt-in)。

方法 1（推荐）- 使旧代码路径为 Chromium 选择加入

  * 向 Skia 添加新代码，保留旧代码不变。
  * 弃用旧代码路径，使其必须通过 'SK_SUPPORT_LEGACY_XXX' 等标志才能启用。
  * 通过在 Chromium 的 'skia/skia_common.gypi' 或 'skia/config/SkUserConfig.h' 中提交启用已弃用 Skia API 的更改，来同步上述 Skia 更改。
      * 请注意，代码抑制不能同时存在于头文件和 gyp 文件中，它应该只存在于一个位置。
  * 在 Chromium 中测试新的或更新的 Skia API。
  * 当旧代码路径不再使用时，删除标志和代码。

方法 2 - 使新代码路径为 Chromium 选择加入

  * 向 Skia 添加新代码，通过标志抑制。
  * 保留旧代码路径不变。
  * 在 Chromium 的 'skia/skia_common.gypi' 或 'skia/config/SkUserConfig.h' 中设置标志以启用新的或更新的 Skia API。
  * 在 Chromium 中测试新的或更新的 Skia API。
  * 当旧 API 不再使用时，删除代码抑制（和代码）。

如果您的更改会影响 Blink 布局测试，请参阅[此处](../blink)的详细说明，了解如何在 Skia、Blink 和 Chromium 之间同步更改。
