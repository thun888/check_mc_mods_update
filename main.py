import os
import yaml
import requests
from collections import Counter
from tqdm import tqdm
import matplotlib.pyplot as plt

def readYamlFile(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
    return data

def getModVersion(modName, mode, apiKey):
    if mode == 'modrinth':
        url = f"https://api.modrinth.com/v2/project/{modName}/version"
        # 设置User-Agent
        headers = {
            "User-Agent": "thun888/check_mc_mods_update/0.0.1 (thun888@hzchu.top)",
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            versionList = []
            for version in response.json():
                nowVersion = version['game_versions']
                for ver in nowVersion:
                    if ver not in versionList:
                        versionList.append(ver)
            # 写入本地文件
            with open(f"./output/{modName}.txt", "w") as f:
                f.write("\n".join(versionList))
            return versionList
        else:
            print(f"获取{modName}版本列表失败: {response.status_code}")
            return None

    elif mode == 'curseforge':
        url = f"https://api.curseforge.com/v1/mods/{modName}"
        headers = {
            "User-Agent": "thun888/check_mc_mods_update/0.0.1 (thun888@hzchu.top)",
            "x-api-key": apiKey
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            versionList = []
            # print(response.json()['data']['latestFilesIndexes'])
            for version in response.json()['data']['latestFilesIndexes']:
                nowVersion = version['gameVersion']
                # print(nowVersion)
                if nowVersion not in versionList:
                    versionList.append(nowVersion)
            with open(f"./output/{modName}.txt", "w") as f:
                f.write("\n".join(versionList))
            return versionList
        else:
            print(f"获取{modName}版本列表失败: {response.status_code}")
            return None


# 计算交集
def computeIntersection(*args):
    """
    接受任意数量的列表作为参数，返回一个集合，包含所有列表中共有的元素。
    """
    # 确保args中的每个元素都是列表
    lists = [lst for lst in args if isinstance(lst, list) and lst]

    # 如果没有提供有效的列表，则返回一个空集合
    if not lists:
        return set()

    # 将第一个列表转换为集合
    common_set = set(lists[0])

    # 遍历剩余的列表
    for lst in lists[1:]:
        # 将列表转换为集合并与现有集合取交集
        common_set &= set(lst)

    # 返回共有元素的集合
    return common_set


def sortAndFilterVersions(version_list, removeAlpha=True):
    """
    处理版本号列表，按照版本先后排列，并去掉包含字母的版本号。
    """
    # 使用filter函数去掉包含字母的版本号
    if removeAlpha:
        filtered_versions = [v for v in version_list if v.replace('.', '').isdigit()]
    else:
        filtered_versions = list(version_list)

    def version_key(v):
        try:
            return [int(num) for num in v.split('.')]
        except ValueError:
            return [0]

    # 使用sorted函数按照版本先后排列
    sorted_versions = sorted(filtered_versions, key=version_key)

    return sorted_versions


def generateVersionHistogram(modsVersionList, outputPath, removeAlpha=True):
    """
    统计所有模组支持的 Minecraft 版本，并生成一个大的直方图。
    x 轴为 Minecraft 版本，y 轴为支持该版本的模组数量。
    """
    # 解决中文显示问题
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC']
    plt.rcParams['axes.unicode_minus'] = False

    allVersions = []
    for mod, versionInfo in modsVersionList.items():
        # versionInfo 结构为 [versionList]
        versionList = versionInfo[0] if versionInfo and isinstance(versionInfo, list) else []
        if versionList:
            allVersions.extend(versionList)

    if not allVersions:
        print("没有可用的版本数据，跳过直方图生成。")
        return

    versionCounter = Counter(allVersions)
    sortedVersions = sortAndFilterVersions(list(versionCounter.keys()), removeAlpha)

    if not sortedVersions:
        print("过滤后没有可排序的版本数据，跳过直方图生成。")
        return

    counts = [versionCounter[v] for v in sortedVersions]
    modCount = len(modsVersionList)

    # 根据版本数量动态调整图片宽度
    plt.figure(figsize=(max(10, len(sortedVersions) * 0.5), 6))
    bars = plt.bar(sortedVersions, counts, color='steelblue')

    plt.xlabel('Minecraft 版本')
    plt.ylabel('支持的模组数量')
    plt.title(f'所有模组支持的 Minecraft 版本分布（共 {modCount} 个模组）')
    plt.xticks(rotation=45, ha='right')

    # 在柱子上方标注具体数量
    for bar, count in zip(bars, counts):
        if count > 0:
            plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                     str(count), ha='center', va='bottom', fontsize=8)

    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    os.makedirs(os.path.dirname(outputPath), exist_ok=True)
    plt.savefig(outputPath, dpi=150)
    plt.close()
    print(f"直方图已保存至: {outputPath}")


if __name__ == '__main__':
    modsList = readYamlFile('modsList.yaml')
    modrinthList = modsList['modrinth']
    curseforgeList = modsList['curseforge']
    specialList = modsList['special']
    config = modsList['config']

    modsVersionList = {}
    # 使用tqdm包裹modrinthList来创建一个进度条
    if modrinthList:
        for mod in tqdm(modrinthList, desc='正在获取版本信息(modrinth)'):
            modsVersionList[mod] = []
            modsVersionList[mod].append(getModVersion(mod, 'modrinth', None))

    if curseforgeList:
        for mod, modid in tqdm(curseforgeList.items(), desc='正在获取版本信息(curseforge)'):
            modsVersionList[mod] = []
            modsVersionList[mod].append(getModVersion(modid, 'curseforge', config['curseforgeApiKey']))

    # 生成所有模组支持版本的直方图（在取交集之前执行，保留每个模组的完整版本信息）
    generateVersionHistogram(modsVersionList, os.path.join('output', 'version_histogram.png'), config['showAlpha'])

    # print(modsVersionList)
    # 取交集
    flatModsVersionList = [version for sublist in modsVersionList.values() for version in sublist]

    # 调用函数并打印结果
    commonModsVersionList = computeIntersection(*flatModsVersionList)
    commonModsVersionList = sortAndFilterVersions(commonModsVersionList, config['showAlpha'])
    print("========================")
    print("以下为共有版本:")

    print(commonModsVersionList)

    print("========================")
    print("以下为特殊mod:")
    print(specialList)
    # print(modsList)
