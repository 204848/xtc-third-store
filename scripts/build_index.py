#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

CATEGORY_NAME_MAP = {
    "games": "游戏",
    "tools": "工具",
    "study": "学习",
    "life": "生活",
    "other": "其他",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def to_url(repo: str, branch: str, rel_path: str) -> dict:
    rel_path = rel_path.replace('\\', '/')
    return {
        "primary": f"https://raw.githubusercontent.com/{repo}/{branch}/{rel_path}",
        "mirror": f"https://fastly.jsdelivr.net/gh/{repo}@{branch}/{rel_path}",
    }


def to_ghfile_proxy(url: str) -> str:
    if url.startswith("https://raw.githubusercontent.com/"):
        return f"https://ghfile.geekertao.top/{url}"
    return url


def resolve_media_url(repo: str, branch: str, media_value):
    if not media_value:
        return media_value
    if isinstance(media_value, str):
        if media_value.startswith("http://") or media_value.startswith("https://"):
            return media_value
        return to_url(repo, branch, media_value)["primary"]
    if isinstance(media_value, list):
        out = []
        for item in media_value:
            if isinstance(item, str) and not (item.startswith("http://") or item.startswith("https://")):
                out.append(to_url(repo, branch, item)["primary"])
            else:
                out.append(item)
        return out
    return media_value


def infer_rpk_path(root: Path, category: str, app_id: str, version_name: str) -> str:
    target_dir = root / "packages" / category / app_id / version_name
    if not target_dir.exists():
        raise ValueError(
            f"missing rpkPath and package dir not found: {target_dir}. "
            f"Please set rpkPath explicitly or place rpk under packages/{category}/{app_id}/{version_name}/"
        )
    rpk_files = sorted(target_dir.glob("*.rpk"))
    if len(rpk_files) == 1:
        return str(rpk_files[0].relative_to(root)).replace('\\', '/')
    if len(rpk_files) == 0:
        raise ValueError(
            f"missing rpkPath and no .rpk found in {target_dir}. "
            f"Please upload rpk or set rpkPath explicitly."
        )
    raise ValueError(
        f"multiple .rpk files found in {target_dir}. "
        f"Please set rpkPath explicitly to avoid wrong filename mapping."
    )


def load_apps(apps_dir: Path, root: Path):
    apps = []
    for p in sorted(apps_dir.rglob('*.json')):
        data = json.loads(p.read_text(encoding='utf-8'))
        data["_metaPath"] = str(p.relative_to(root)).replace('\\', '/')

        if "category" not in data:
            # 默认采用 apps/<category>/<appId>.json 的目录名作为分类
            try:
                data["category"] = p.relative_to(apps_dir).parts[0]
            except Exception:
                data["category"] = "other"

        required = ["appId", "name", "packageName", "versionName", "versionCode"]
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"{p}: missing fields {missing}")

        category = data.get("category", "other")
        if not data.get("rpkPath"):
            data["rpkPath"] = infer_rpk_path(root, category, data["appId"], str(data["versionName"]))

        rpk_path = root / data["rpkPath"]
        if not rpk_path.exists():
            raise ValueError(f"{p}: rpkPath not exists -> {data['rpkPath']}")
        if rpk_path.suffix.lower() != ".rpk":
            raise ValueError(f"{p}: rpkPath must end with .rpk -> {data['rpkPath']}")

        if data.get("rpkFileName") and data["rpkFileName"] != rpk_path.name:
            raise ValueError(
                f"{p}: rpkFileName({data['rpkFileName']}) not match real file name({rpk_path.name})"
            )

        data["_rpkFileName"] = rpk_path.name
        data["_packageSizeBytes"] = rpk_path.stat().st_size

        apps.append(data)
    return apps


def build_index(repo: str, branch: str, apps: list):
    normalized = []
    for a in apps:
        category = a.get("category", "other")
        download_urls = to_url(repo, branch, a["rpkPath"])
        item = {
            "appId": a["appId"],
            "name": a["name"],
            "packageName": a["packageName"],
            "category": category,
            "versionName": a["versionName"],
            "versionCode": int(a["versionCode"]),
            "description": a.get("description", ""),
            "developer": a.get("developer", ""),
            "tags": a.get("tags", []),
            "minPlatformVersion": a.get("minPlatformVersion"),
            "minFirmware": a.get("minFirmware"),
            "icon": resolve_media_url(repo, branch, a.get("icon")),
            "screenshots": resolve_media_url(repo, branch, a.get("screenshots", [])),
            "rpkFileName": a.get("rpkFileName", a.get("_rpkFileName")),
            "packageSizeBytes": a.get("packageSizeBytes", a.get("_packageSizeBytes")),
            "download": {
                **download_urls,
                "proxy": to_ghfile_proxy(download_urls["primary"]),
            },
            "meta": to_url(repo, branch, a["_metaPath"]),
            "updatedAt": a.get("updatedAt", utc_now_iso()),
        }
        normalized.append(item)

    normalized.sort(key=lambda x: (x["category"], x["name"].lower(), -x["versionCode"]))

    buckets = {}
    for app in normalized:
        buckets.setdefault(app["category"], []).append(app)

    categories = []
    for cid in sorted(buckets.keys()):
        categories.append({
            "id": cid,
            "name": CATEGORY_NAME_MAP.get(cid, cid),
            "count": len(buckets[cid]),
            "apps": buckets[cid],
        })

    return {
        "version": "1.0",
        "generatedAt": utc_now_iso(),
        "repo": {
            "id": repo,
            "branch": branch,
        },
        "categories": categories,
        "apps": normalized,
    }


def main():
    parser = argparse.ArgumentParser(description="Build app index for third-party watch store")
    parser.add_argument("--repo", required=True, help="GitHub repo, e.g. owner/repo")
    parser.add_argument("--branch", default="main", help="Git branch")
    parser.add_argument("--apps-dir", default="apps", help="Apps metadata directory")
    parser.add_argument("--out", default="data/index.json", help="Output index file")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    apps_dir = root / args.apps_dir
    out_file = root / args.out

    if not apps_dir.exists():
        raise SystemExit(f"apps dir not found: {apps_dir}")

    apps = load_apps(apps_dir, root)
    index = build_index(args.repo, args.branch, apps)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')
    print(f"[ok] wrote {out_file} ({len(index['apps'])} apps)")


if __name__ == "__main__":
    main()
