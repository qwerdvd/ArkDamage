from typing import Any, Optional

from pydantic import Field, BaseModel


class Dur(BaseModel):
    attackCount = Field(int)
    attackSpeed = Field(float)
    times = Field(int)
    hitCount = Field(int)
    duration = Field(float)
    stunDuration = Field(float)
    prepDuration = Field(float)
    dpsDuration = Field(float)
    tags = Field(str)
    startSp = Field(float)
    critCount = Field(int)
    critHitCount = Field(int)
    remain_frame = Field(float)

    def __init__(self, data: dict):
        super().__init__()
        if data is not None:
            for key, value in data.items():
                setattr(self, key, value)
        # self.attackCount = data['attackCount']
        # self.attackSpeed = data['attackSpeed']
        # self.times = data['times']
        # self.hitCount = data['hitCount']
        # self.duration = data['duration']
        # self.stunDuration = data['stunDuration']
        # self.prepDuration = data['prepDuration']
        # self.dpsDuration = data['dpsDuration']
        # self.tags = data['tags']
        # self.startSp = data['startSp']

    def __getitem__(self, item):
        # if item not in self.__dict__:
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def items(self):
        return self.__dict__.items()


class Enemy(BaseModel):
    defense = Field(int)
    magicResistance = Field(int)
    count = Field(int)
    hp = Field(int)

    def __init__(self, data: dict):
        super().__init__()
        self.defense = data['defense']
        self.magicResistance = data['magicResistance']
        self.count = data['count']
        self.hp = data['hp']


class BlackBoard:
    id: str
    trait: Optional
    talent: Optional

    def __init__(self, data: dict):
        for items in data:
            if 'builtin_function_or_method' not in str(type(items)):
                setattr(self, items, data[items])

    def __iter__(self):
        return iter(self.__dict__.items())

    def __delitem__(self, key):
        del self.__dict__[key]

    def get(self, key: str, default: Optional[Any] = None):
        return self.__dict__.get(key, default)

    def value(self, key: str):
        self.get(key)
        if self.get(key) is not None:
            return self.__dict__[key]

    def delete(self, key: str):
        self.__delitem__(key)

    def update(self, key: str, value: Any):
        self.__dict__[key] = value
