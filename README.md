# xtc-third-store-backend

第三方手表应用商店后端（纯静态仓库版）。

目标：
- 仓库里只放应用元数据和已编译好的 `.rpk` 安装包。
- 应用列表 `data/index.json` 自动生成。
- 前端优先走 GitHub Raw，国内可切换 jsDelivr 镜像。

## 仓库结构（建议）

```text
xtc-third-store-backend/
  apps/                          # 每个应用一份元数据
    games/
      sample-math.json
    tools/
      sample-timer.json
  packages/                      # rpk 存放区（按分类/应用/版本）
    games/sample-math/1.0.0/sample-math-1.0.0.rpk
    tools/sample-timer/1.0.0/sample-timer-1.0.0.rpk
  data/
    index.json                   # 自动生成，前端直接拉这个
  scripts/
    build_index.py               # 构建索引脚本
  .github/workflows/
    rebuild-index.yml            # push 后自动更新索引
```

## 元数据格式（apps/*.json）

最小字段：

```json
{
  "appId": "sample-math",
  "name": "口算练习",
  "packageName": "com.demo.math",
  "category": "games",
  "versionName": "1.0.0",
  "versionCode": 1
}
```

`rpkPath` 可选（推荐不写，避免手误）：
- 若不写，会自动从 `packages/<category>/<appId>/<versionName>/` 下寻找 `.rpk`
- 该目录仅允许存在 1 个 `.rpk`，否则会报错并阻止生成错误索引

可选字段：
- `icon`, `screenshots`, `description`, `developer`, `tags`, `minPlatformVersion`, `minFirmware`

## 自动更新列表

提交（push）以下内容时会自动更新 `data/index.json`：
- `apps/**/*.json`
- `packages/**/*.rpk`

## 本地手动生成

```bash
python scripts/build_index.py --repo "demo/xtc-third-store-backend"
```

## 前端建议拉取地址

以 `packages/games/sample-math/1.0.0/sample-math-1.0.0.rpk` 为例：

- 主地址（GitHub Raw）
  - `https://raw.githubusercontent.com/<owner>/<repo>/<branch>/packages/games/sample-math/1.0.0/sample-math-1.0.0.rpk`
- 镜像地址（jsDelivr）
  - `https://fastly.jsdelivr.net/gh/<owner>/<repo>@<branch>/packages/games/sample-math/1.0.0/sample-math-1.0.0.rpk`

前端可在下载失败时自动切镜像。

## 你后续上传应用时的最简流程

1. 把 `.rpk` 放到：`packages/<分类>/<appId>/<版本>/xxx.rpk`
2. 新建或更新：`apps/<分类>/<appId>.json`
3. `git add . && git commit && git push`
4. 等 Action 自动更新 `data/index.json`

就这 4 步，不需要额外后台服务。
