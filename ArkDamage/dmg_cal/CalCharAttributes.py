import math
from decimal import Decimal

from . import Character, InitChar
from .load_json import specs
from .model.Character import AttributeKeys
from .model.char_data import CharacterData
from ..utils.math_model import get_attribute


async def check_specs(tag: str, spec: str) -> bool or int or str:
    if tag in specs and spec in specs[tag]:
        return specs[tag][spec]
    else:
        return False


async def cal_basic_attributes(char_info: InitChar, char: Character) -> dict:
    """
    :说明:
        计算基础属性，包括等级和潜能
    :参数:
        * char_info: InitChar
            干员基础信息
        * char: Character
            干员信息
    :返回:
        * basic_attributes: dict
    """
    # attributesKeyFrames = {}
    # 计算等级加成
    if char_info.level == char.CharData.phases[char_info.phase].maxLevel:
        attributes_key_frames = char.PhaseData.attributesKeyFrames[1].data.copy()
    else:
        attributes_key_frames = {
            key: await get_attribute(char.PhaseData.attributesKeyFrames, char_info.level, 1, key) for key in
            AttributeKeys}

    # 计算信赖加成
    if char.CharData.get('favorKeyFrames') and char.CharData.get('profession') != 'TOKEN':
        favor_level = Decimal(min(char_info.favor, 100) / 2)
        for key in AttributeKeys:
            attributes_key_frames[key] += await get_attribute(char.CharData.favorKeyFrames, favor_level, 0, key)
            char.buffs[key] = 0

    return attributes_key_frames


PotentialAttributeTypeList = {
    0: "maxHp",
    1: "atk",
    2: "defense",
    3: "magicResistance",
    4: "cost",
    5: "blockCnt",
    6: "moveSpeed",
    7: "attackSpeed",
    21: "respawnTime",
}


async def apply_potential(char_data: CharacterData, rank: int, basic: dict, log) -> dict:
    if not char_data.potentialRanks or len(char_data.potentialRanks) == 0:
        return basic
    for i in range(rank):
        potential_data = char_data.potentialRanks[i]
        if potential_data.buff is not None and potential_data.buff.attributes.attributeModifiers is not None:
            y = potential_data.buff.attributes.attributeModifiers[0]
            key = PotentialAttributeTypeList[y.attributeType]
            value = y.value

            basic[key] += Decimal(value)
            if value > 0:
                log.write(f"潜能 {i + 2}: {key} {basic[key] - Decimal(value)} -> {basic[key]} (+{value})")

    return basic


async def get_blackboard(blackboard_array) -> dict:
    for item in blackboard_array:
        if item.key == "def":
            item.key = "defense"
    return {item.key: item.value for item in blackboard_array}


async def get_dict_blackboard(blackboard_array) -> dict:
    blackboard = {}
    for item in blackboard_array:
        if item['key'] == "def":
            item['key'] = "defense"
        blackboard[item['key']] = item['value']
    return blackboard


async def apply_equip(char: Character, char_info: InitChar, basic: dict, log) -> dict:
    equip_id = char_info.equip_id
    phase = char_info.equipLevel - 1
    # cand = 0
    blackboard = {}
    attr = {}

    if equip_id and char.UniEquipData is not None:
        item = char.UniEquipData.phases[phase]
        attr = await get_blackboard(char.UniEquipData.phases[phase].attributeBlackboard)
        blackboard['attr'] = attr

        if item.tokenAttributeBlackboard is not None:
            tb = {}
            for tok in item.tokenAttributeBlackboard:
                tb[tok] = await get_dict_blackboard(item.tokenAttributeBlackboard[tok])
            blackboard['token'] = tb

        talents = {}
        traits = {}
        for part in item.parts:
            talent_bundle = part.addOrOverrideTalentDataBundle
            trait_bundle = part.overrideTraitDataBundle
            # 天赋变更
            if talent_bundle and talent_bundle.get("candidates"):
                cand = len(talent_bundle["candidates"]) - 1
                while cand > 0:
                    if char_info.potentialRank >= talent_bundle["candidates"][cand]["requiredPotentialRank"]:
                        break
                    cand -= 1
                result = await get_dict_blackboard(talent_bundle['candidates'][cand]['blackboard'])
                talents.update(result)

            # 特性变更
            if trait_bundle and trait_bundle.get("candidates"):
                cand = len(trait_bundle["candidates"]) - 1
                while cand > 0:
                    if char_info.potentialRank >= trait_bundle["candidates"][cand]["requiredPotentialRank"]:
                        break
                    cand -= 1
                traits.update(await get_dict_blackboard(trait_bundle["candidates"][cand]["blackboard"]))
        blackboard['talent'] = talents
        blackboard['trait'] = traits
        which = str(await check_specs(char_info.equip_id, 'override_talent'))
        if which and len(which) > 0 and char_info.equipLevel >= 1:
            blackboard['override_talent'] = which
        blackboard['override_trait'] = await check_specs(char_info.equip_id, 'override_trait')
        blackboard['remove_keys'] = await check_specs(char_info.equip_id, 'remove_keys') or []
    attr_keys = {
        'max_hp': "maxHp",
        'atk': "atk",
        'defense': "defense",
        'magic_resistance': "magicResistance",
        'attack_speed': "attackSpeed",
        'block_cnt': "blockCnt",
        'cost': "cost",
        'respawn_time': "respawnTime",
    }
    if not char_info.options.get('token'):
        for x in attr:
            basic[attr_keys[x]] += Decimal(attr[x])
            if attr[x] != 0:
                log.write(
                    f"模组 Lv{char_info.equipLevel}: "
                    f"{attr_keys[x]} {basic[attr_keys[x]] - Decimal(attr[x])} -> "
                    f"{basic[attr_keys[x]]} (+{Decimal(attr[x])})")
    basic['equip_blackboard'] = blackboard

    return basic


async def get_attributes(char_info: InitChar, char: Character, log) -> Character:
    phase_data = char.CharData.phases[char_info.phase]
    display_names = char.displayNames
    if char_info.char_id.startswith('token'):
        log.write("【召唤物属性】")
    else:
        log.write("【基础属性】")
    log.write("----")
    # 计算基础属性，包括等级和潜能
    if char_info.level == phase_data.maxLevel:
        char.attributesKeyFrames.update(phase_data.attributesKeyFrames[1].data)
    else:
        for key in AttributeKeys:
            char.attributesKeyFrames[key] = \
                await get_attribute(phase_data.attributesKeyFrames, char_info.level, 1, key)

    if char.CharData.favorKeyFrames and char.CharData.profession != "TOKEN":
        favor_level = Decimal(math.floor(min(char_info.favor, 100) / 2))
        for key in AttributeKeys:
            char.attributesKeyFrames[key] = Decimal(char.attributesKeyFrames[key])
            char.attributesKeyFrames[key] += await get_attribute(char.CharData.favorKeyFrames, favor_level, 0, key)
            char.buffs[key] = 0

    # 计算潜能
    char.attributesKeyFrames = await apply_potential(char.CharData, char_info.potentialRank,
                                                     char.attributesKeyFrames, log)
    # 计算模组
    if char_info.equip_id and char_info.phase >= 2:
        char.attributesKeyFrames = await apply_equip(char, char_info, char.attributesKeyFrames, log)
        char.buffList[char_info.equip_id] = char.attributesKeyFrames['equip_blackboard']

    # 计算天赋/特性，记为Buff
    if char.CharData.trait and not char.CharData.get('has_trait'):
        char.CharData.has_trait = True
        char.CharData.talents.append(char.CharData.trait)  # type: ignore
    if char.CharData.talents:
        for talentData in char.CharData.talents:
            if talentData.candidates:
                for i in range(len(talentData.candidates) - 1, -1, -1):
                    cd = talentData.candidates[i]
                    if char_info.phase >= cd.unlockCondition.phase and \
                            char_info.level >= cd.unlockCondition.level and \
                            char_info.potentialRank >= cd.requiredPotentialRank:
                        blackboard = await get_blackboard(cd.blackboard)
                        if cd.prefabKey != '1+' and cd.prefabKey != 'trait' and cd.prefabKey != '#':
                            if not cd.prefabKey or int(cd.prefabKey) < 0:
                                cd.prefabKey = "trait"  # trait as talent
                                cd.name = "特性"
                        prefab_key = f"tachr_{char_info.char_id[5:]}_{cd.prefabKey}"
                        display_names[prefab_key] = cd.name  # add to name cache

                        # 如果天赋被模组修改，覆盖对应面板
                        if char.attributesKeyFrames.get('equip_blackboard'):
                            ebb = char.attributesKeyFrames['equip_blackboard']
                            if ebb['override_talent'] == cd.prefabKey:
                                tb = ebb['talent']
                                for k in ebb['remove_keys']:
                                    del tb[k]
                                for k in tb:
                                    blackboard[k] = tb[k]
                                log.write(f"[模组] 强化天赋 - {cd.name}: {blackboard}")
                            if cd.prefabKey == "trait" and ebb.get('override_trait'):
                                tb = ebb['trait']
                                for k, v in tb.items():
                                    blackboard[k] = v
                                log.write(f"[模组] 强化特性: {blackboard}")
                        # bufflist处理
                        char.buffList[prefab_key] = blackboard
                        break

    # 令3
    if char_info.skill_id == 'skchr_ling_3' and char_info.options.get(
            'ling_fusion') and char_info.options.get('token'):
        log.write("“弦惊” - 高级形态: 添加合体Buff")
        char.buffList["fusion_buff"] = await check_specs(char_info.skill_id, "fusion_buff")

    return char
