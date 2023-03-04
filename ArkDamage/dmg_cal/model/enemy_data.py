from typing import List, Union

from pydantic import BaseModel, Field


class SingleEnemyData(BaseModel):
    m_defined: bool
    m_value: Union[int, float, str, bool, None]


class EnemySkillSpdata(BaseModel):
    spType: int
    maxSp: int
    initSp: int
    increment: float


class Blackboard(BaseModel):
    key: str
    value: float
    valueStr: Union[str, None]


class EnemyAttributes(BaseModel):
    maxHp: SingleEnemyData
    atk: SingleEnemyData
    defense: SingleEnemyData = Field(alias='def')
    magicResistance: SingleEnemyData
    cost: SingleEnemyData
    blockCnt: SingleEnemyData
    moveSpeed: SingleEnemyData
    attackSpeed: SingleEnemyData
    baseAttackTime: SingleEnemyData
    respawnTime: SingleEnemyData
    hpRecoveryPerSec: SingleEnemyData
    spRecoveryPerSec: SingleEnemyData
    maxDeployCount: SingleEnemyData
    massLevel: SingleEnemyData
    baseForceLevel: SingleEnemyData
    tauntLevel: SingleEnemyData
    stunImmune: SingleEnemyData
    silenceImmune: SingleEnemyData
    sleepImmune: SingleEnemyData
    frozenImmune: SingleEnemyData
    levitateImmune: SingleEnemyData


class EnemySkill(BaseModel):
    prefabKey: str
    priority: int
    cooldown: float
    initCooldown: float
    spCost: int
    blackboard: Union[List[Blackboard], None]


class EnemyData(BaseModel):
    name: SingleEnemyData
    description: SingleEnemyData
    prefabKey: SingleEnemyData
    attributes: EnemyAttributes
    lifePointReduce: SingleEnemyData
    levelType: SingleEnemyData
    rangeRadius: SingleEnemyData
    numOfExtraDrops: SingleEnemyData
    viewRadius: SingleEnemyData
    talentBlackboard: Union[List[Blackboard], None]
    skills: Union[List[EnemySkill], None]
    spData: Union[EnemySkillSpdata, None]


class EnemyValue(BaseModel):
    level: int
    enemyData: EnemyData


class EnemyDataBase(BaseModel):
    Key: str
    Value: List[EnemyValue]

    def __init__(self, enemy_dict: dict):
        super().__init__(**enemy_dict)


if __name__ == '__main__':
    import json

    with open('C:/Users/qwerdvd/Desktop/ArkDamage/data/ArkDamage/levels/enemydata/enemy_database.json', encoding='utf-8') as f:
        data = json.load(f)
    enemy_list = data['enemies']
    for enemy in enemy_list:
        try:
            EnemyDataBase(enemy)
        except Exception as e:
            print(enemy['Key'], e)
