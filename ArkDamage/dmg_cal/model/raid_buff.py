from pydantic import BaseModel


class RaidBlackboard(BaseModel):
    atk: float = 0
    atk_override: float = 0
    attack_speed: float = 0
    sp_recovery_per_sec: float = 0
    base_atk: float = 0
    damage_scale: float = 0

    def __init__(self, raid_buff: dict):
        super().__init__(**raid_buff)
