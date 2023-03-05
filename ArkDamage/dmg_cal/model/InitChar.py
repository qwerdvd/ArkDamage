from pydantic import BaseModel, Field

from ..load_json import dps_options, character_table


class InitChar(BaseModel):
    """
    :说明:
        初始化干员信息
    :参数:
        * character_id: str
            干员ID
        * level: int
            干员等级
        * skill_id: str
            技能ID
        * equip_id: str
            模组ID
    :返回:
        * InitChar
    """
    char_id = Field(str, alias='characterId', title='干员ID')
    rarity = Field(int, alias='rarity', title='干员稀有度')
    level = Field(int, alias='level', title='干员等级')
    skill_id = Field(str, alias='skillId', title='技能ID')
    equip_id = Field(str, alias='equipId', title='模组ID')
    phase = Field(int, alias='phase', title='干员阶段')
    potentialRank = Field(int, alias='potentialRank', title='潜能等级')
    equipLevel = Field(int, alias='equipLevel', title='模组等级')
    options = Field(dict, alias='options', title='选项')
    favor = Field(int, alias='favor', title='好感度')
    skillLevel = Field(int, alias='skillLevel', title='技能等级')

    def __init__(self, mes: list):
        super().__init__()
        self.char_id = mes[0]
        self.potentialRank = int(mes[1]) - 1
        self.get_rarity()
        self.phase = int(mes[2][0])
        self.level = int(mes[2][1:])
        self.check_level()
        self.skill_id = mes[3]
        self.equip_id = mes[4]
        self.equipLevel = 3
        self.get_option()
        self.favor = 200
        self.get_skill_level()
        self.check_uniequip()

    def get_phase(self) -> int:
        """
        :说明:
            获取干员阶段
        :参数:
            * 无
        :返回:
            * phase: int
                干员阶段
        """
        level = int(self.level)
        phase = 0 if level <= 50 else (1 if level <= 180 else 2)
        self.level = int(self.level[-2:])
        return phase

    def get_option(self):
        """
        :说明:
            获取选项
        :参数:
            * 无
        :返回:
            * options: dict
                选项
        """
        self.options = {}
        if self.char_id in dps_options['char']:
            for item in dps_options['char'][self.char_id]:
                if item in dps_options['tags']:
                    if dps_options['tags'][item].get('off'):
                        self.options[item] = False
                    else:
                        self.options[item] = True

        # 团辅
        # self.options["buff"] =

    def get_skill_level(self):
        """
        :说明:
            获取技能等级
        :参数:
            * 无
        :返回:
            * skillLevel: int
                技能等级
        """
        self.skillLevel = 9 if self.phase == 2 else 6

    def get_rarity(self):
        """
        :说明:
            获取稀有度
        :参数:
            * 无
        :返回:
            * rarity: int
                稀有度
        """
        self.rarity = character_table[self.char_id]['rarity']

    def check_level(self):
        """
        :说明:
            检查等级
        :参数:
            * 无
        :返回:
            * 无
        """
        if self.rarity == 5:
            if self.phase == 2 and self.level > 90:
                self.level = 90
            if self.phase == 1 and self.level > 80:
                self.level = 80
            if self.phase == 0 and self.level > 50:
                self.level = 50
        if self.rarity == 4:
            if self.phase == 2 and self.level > 80:
                self.level = 80
            if self.phase == 1 and self.level > 70:
                self.level = 70
            if self.phase == 0 and self.level > 50:
                self.level = 50
        if self.rarity == 3:
            if self.phase == 2 and self.level > 70:
                self.level = 70
            if self.phase == 1 and self.level > 60:
                self.level = 60
            if self.phase == 0 and self.level > 50:
                self.level = 50
        if self.rarity == 2:
            if self.phase == 1 and self.level > 55:
                self.level = 55
            if self.phase == 0 and self.level > 40:
                self.level = 40

        if int(self.level) <= 0:
            self.level = 1

    def check_phase(self):
        """
        :说明:
            检查阶段
        :参数:
            * 无
        :返回:
            * 无
        """
        if self.rarity == 5:
            if self.level > 90:
                self.phase = 2
            elif self.level > 80:
                self.phase = 1
            else:
                self.phase = 0
        if self.rarity == 4:
            if self.level > 80:
                self.phase = 2
            elif self.level > 70:
                self.phase = 1
            else:
                self.phase = 0
        if self.rarity == 3:
            if self.level > 70:
                self.phase = 2
            elif self.level > 60:
                self.phase = 1
            else:
                self.phase = 0
        if self.rarity == 2:
            if self.level > 55:
                self.phase = 1
            else:
                self.phase = 0

    def check_uniequip(self):
        """
        :说明:
            检查是否为统一模组
        :参数:
            * 无
        :返回:
            * 无
        """
        if self.equip_id == 'None':
            self.options['equip'] = False

        if self.phase != 2:
            self.equip_id = 'None'
            self.options['equip'] = False
