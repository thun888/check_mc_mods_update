import yaml
import requests
from tqdm import tqdm

def readYamlFile(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
    return data

def getModVersion(modName,mode,apiKey):
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
            print(f"获取{modName}版本列表失败: " + response.status_code)
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
            print(f"获取{modName}版本列表失败: " + response.status_code)
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
        filtered_versions = filter(lambda x: x.replace('.', '').isdigit(), version_list)
    
    # 使用sorted函数按照版本先后排列
    sorted_versions = sorted(filtered_versions, key=lambda x: [int(num) for num in x.split('.')])
    
    return sorted_versions



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
        modsVersionList[mod].append(getModVersion(modid,'curseforge', config['curseforgeApiKey']))
# print(modsVersionList)
# 取交集
flatModsVersionList = [version for sublist in modsVersionList.values() for version in sublist]

# 调用函数并打印结果
modsVersionList = computeIntersection(*flatModsVersionList)
modsVersionList = sortAndFilterVersions(modsVersionList, config['showAlpha'])
print("========================")
print("以下为共有版本:")

print(modsVersionList)

print("========================")
print("以下为特殊mod:")
print(specialList)
# print(modsList)



