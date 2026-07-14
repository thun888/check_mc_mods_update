import argparse
import os
import yaml
from datetime import datetime

import requests
from tqdm import tqdm

MOD_LOADER = {
    "forge": 1,
    "fabric": 4,
    "quilt": 5,
    "neoforge": 6,
}


USER_AGENT = "thun888/check_mc_mods_update/0.0.1 (thun888@hzchu.top)"


def load_modslist(path='modslist.yaml'):
    """读取 modslist.yaml，返回配置信息。"""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def ensure_dir(path):
    """确保目录存在。"""
    os.makedirs(path, exist_ok=True)


def find_modrinth_download(mod, target_version, loader="fabric"):
    """
    在 Modrinth 上查找指定 mod 对应目标游戏版本的下载链接。
    返回 (download_url, filename) 或 (None, None)。
    """
    url = f"https://api.modrinth.com/v2/project/{mod}/version"
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"[Modrinth] 获取 {mod} 版本列表失败: {response.status_code}")
        return None, None

    versions = response.json()
    # 只保留包含目标游戏版本的版本，并按发布时间取最新
    matching = [
        v for v in versions
        if target_version in v.get("game_versions", [])
        and loader in v.get("loaders", [])
    ]
    if not matching:
        return None, None

    latest = sorted(matching, key=lambda v: v.get('date_published', ''), reverse=True)[0]
    files = latest.get('files', [])
    if not files:
        return None, None

    # 优先选择标识为 primary 的文件，否则取第一个
    primary_file = next((f for f in files if f.get('primary')), files[0])
    return primary_file.get('url'), primary_file.get('filename')


def find_curseforge_download(mod_id, target_version, api_key):
    """
    在 CurseForge 上查找指定 mod 对应目标游戏版本（Fabric 加载器）的下载链接。
    返回 (download_url, filename) 或 (None, None)。
    """
    url = (
        f"https://api.curseforge.com/v1/mods/{mod_id}/files"
        f"?gameVersion={target_version}&modLoaderType={MOD_LOADER['fabric']}"
    )
    headers = {
        "User-Agent": USER_AGENT,
        "x-api-key": api_key,
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"[CurseForge] 获取 {mod_id} 文件列表失败: {response.status_code}")
        return None, None

    files = response.json().get('data', [])
    if not files:
        return None, None

    # 取最新发布的文件
    latest = sorted(files, key=lambda f: f.get('fileDate', ''), reverse=True)[0]
    return latest.get('downloadUrl'), latest.get('fileName')


def download_file(url, save_path, headers):
    """下载文件并显示进度条。"""
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()

    total = int(response.headers.get('content-length', 0))
    chunk_size = 8192

    with open(save_path, 'wb') as f, tqdm(
        total=total,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
        desc=os.path.basename(save_path),
        leave=False,
    ) as bar:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))


def main():
    parser = argparse.ArgumentParser(
        description='输入目标 Minecraft 版本，下载所有支持该版本的 mod'
    )
    parser.add_argument('version', nargs='?', help='目标 Minecraft 版本，例如 1.20.1')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='只显示会下载哪些文件，不真正下载',
    )
    args = parser.parse_args()

    modslist = load_modslist()
    config = modslist.get('config', {})
    curseforge_api_key = config.get('curseforgeApiKey', '')

    if args.version:
        target_version = args.version.strip()
    else:
        target_version = input('请输入目标 Minecraft 版本: ').strip()

    if not target_version:
        print("版本号不能为空。")
        return

    download_dir = os.path.join('downloads', f"mc_{target_version}")
    if not args.dry_run:
        ensure_dir(download_dir)

    modrinth_list = modslist.get('modrinth', [])
    curseforge_dict = modslist.get('curseforge', {})

    success = []
    skipped = []
    failed = []

    print(f"\n开始处理目标版本: {target_version}")
    print(f"Modrinth 来源: {len(modrinth_list)} 个")
    print(f"CurseForge 来源: {len(curseforge_dict)} 个")
    print(f"模式: {'仅预览（不下载）' if args.dry_run else '下载'}")

    # 处理 Modrinth
    for mod in tqdm(modrinth_list, desc='Modrinth 查询进度'):
        url, filename = find_modrinth_download(mod, target_version)
        if not url or not filename:
            skipped.append((f"[Modrinth] {mod}", "未找到对应版本"))
            continue

        if args.dry_run:
            print(f"[待下载/Modrinth] {mod} -> {filename} ({url})")
            success.append(mod)
            continue

        save_path = os.path.join(download_dir, filename)
        try:
            download_file(url, save_path, {"User-Agent": USER_AGENT})
            success.append(mod)
        except Exception as e:
            failed.append((f"[Modrinth] {mod}", str(e)))

    # 处理 CurseForge
    for mod_name, mod_id in tqdm(curseforge_dict.items(), desc='CurseForge 查询进度'):
        url, filename = find_curseforge_download(mod_id, target_version, curseforge_api_key)
        if not url or not filename:
            skipped.append((f"[CurseForge] {mod_name}", "未找到对应版本"))
            continue

        if args.dry_run:
            print(f"[待下载/CurseForge] {mod_name} -> {filename} ({url})")
            success.append(mod_name)
            continue

        save_path = os.path.join(download_dir, filename)
        try:
            download_file(url, save_path, {
                "User-Agent": USER_AGENT,
                "x-api-key": curseforge_api_key,
            })
            success.append(mod_name)
        except Exception as e:
            failed.append((f"[CurseForge] {mod_name}", str(e)))

    # 汇总
    print("\n====================")
    print(f"处理完成: 共 {len(modrinth_list) + len(curseforge_dict)} 个 mod")
    print(f"  成功/命中: {len(success)} 个")
    print(f"  跳过（无目标版本）: {len(skipped)} 个")
    print(f"  失败: {len(failed)} 个")
    if not args.dry_run:
        print(f"文件保存位置: {os.path.abspath(download_dir)}")

    if failed:
        print("\n失败的 mod:")
        for name, reason in failed:
            print(f"  {name}: {reason}")

    if skipped and args.dry_run:
        print("\n跳过的 mod:")
        for name, reason in skipped:
            print(f"  {name}: {reason}")


if __name__ == '__main__':
    main()
