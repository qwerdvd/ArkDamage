from typing import Union

from pydantic import BaseModel


class AnimDetail(BaseModel):
    duration: int
    OnAttack: int
    OnPlayAudio: Union[int, None]


class Anim(BaseModel):
    version: str
    Attack: AnimDetail
    Attack_Begin: Union[int, None]
    Attack_Down: Union[AnimDetail, None]
    Attack_End: Union[int, None]
    Default: int
    Die: int
    Idle: int
    Idle_2: Union[int, None]
    Skill: AnimDetail
    Skill01: Union[AnimDetail, None]
    Skill02: Union[AnimDetail, None]
    Skill_1: Union[AnimDetail, None]
    Skill_2: AnimDetail
    Skill_1_Up: Union[AnimDetail, None]
    Skill_2_Up: Union[AnimDetail, None]
    Skill_2_Begin: Union[AnimDetail, int, None]
    Skill_2_End: Union[AnimDetail, int, None]
    Skill_1_Down: Union[AnimDetail, None]
    Skill_2_Down: Union[AnimDetail, None]
    skill_2_Loop: Union[AnimDetail, None]
    Skill_Begin: int
    Skill_End: int
    Start: AnimDetail
    Stun: int
