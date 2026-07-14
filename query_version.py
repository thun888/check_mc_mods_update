import argparse
import os
import yaml


def load_mods_from_output(output_dir='output', modslist_path='modslist.yaml'):
    """
    读取 output 目录下的缓存文件，建立 mod -> {支持版本集合} 的映射。
    curseforge 缓存文件名是数字 id，会结合 modslist.yaml 转成实际 mod 名。
    """
    mod_versions = {}

    # 尝试读取 modslist.yaml，构建 curseforge id -> mod 名的映射
    mod_id_to_name = {}
    if os.path.exists(modslist_path):
        try:
            data = yaml.safe_load(open(modslist_path, 'r', encoding='utf-8'))
            for mod_name, mod_id in data.get('curseforge', {}).items():
                mod_id_to_name[str(mod_id)] = mod_name
        except Exception as e:
            print(f"读取 {modslist_path} 失败: {e}")

    if not os.path.isdir(output_dir):
        print(f"目录 {output_dir} 不存在，请先运行主程序抓取版本缓存。")
        return mod_versions

    for filename in os.listdir(output_dir):
        if not filename.endswith('.txt'):
            continue

        base_name = filename[:-4]
        # 若是 curseforge 数字 id，尝试解析为 mod 名
        mod_name = mod_id_to_name.get(base_name, base_name)

        file_path = os.path.join(output_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                versions = {line.strip() for line in f if line.strip()}
            mod_versions[mod_name] = versions
        except Exception as e:
            print(f"读取 {file_path} 失败: {e}")

    return mod_versions


def query_version(mod_versions, target_version):
    """
    按目标版本分类：支持和未支持的 mod。
    """
    supported = []
    unsupported = []

    for mod_name, versions in mod_versions.items():
        if target_version in versions:
            supported.append(mod_name)
        else:
            unsupported.append(mod_name)

    supported.sort()
    unsupported.sort()
    return supported, unsupported


def main():
    parser = argparse.ArgumentParser(description='查询指定 Minecraft 版本有哪些 mod 支持/不支持')
    parser.add_argument('version', nargs='?', help='目标 Minecraft 版本，例如 1.20.1')
    args = parser.parse_args()

    mod_versions = load_mods_from_output()
    if not mod_versions:
        return

    if args.version:
        target_version = args.version
    else:
        target_version = input('请输入要查询的 Minecraft 版本: ').strip()

    if not target_version:
        print("版本号不能为空。")
        return

    supported, unsupported = query_version(mod_versions, target_version)

    print(f"\n目标版本: {target_version}")
    print(f"共有 {len(mod_versions)} 个 mod 被检测到")
    print(f"  - 支持该版本的 mod: {len(supported)} 个")
    print(f"  - 不支持该版本的 mod: {len(unsupported)} 个")

    print("\n=== 支持该版本的 mod ===")
    for mod in supported:
        print(mod)

    print("\n=== 不支持该版本的 mod ===")
    for mod in unsupported:
        print(mod)


if __name__ == '__main__':
    main()
