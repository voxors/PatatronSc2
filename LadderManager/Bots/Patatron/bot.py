from typing import List

from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2, Point3
from sc2.unit import Unit

import macro


class CompetitiveBot(BotAI):
    WorkerCountObjective = 80
    ScoutingWorkerTag = None
    first_push_done = False
    macro_bot: macro.Macro

    def __init__(self):
        super().__init__()
        self.macro_bot = macro.Macro(self)

    async def on_start(self):
        print("Game started")
        self.macro_bot.main_townhall = self.townhalls.first

    async def on_unit_created(self, unit: Unit):
        if unit.type_id == UnitTypeId.SCV:
            if self.townhalls.idle.amount > 0:
                if self.can_afford(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND):
                    self.townhalls.idle.first(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

    async def on_unit_destroyed(self, unit_tag: int):
        if self.ScoutingWorkerTag == unit_tag:
            self.ScoutingWorkerTag = None

    async def on_step(self, iteration):
        await self.distribute_workers()
        number_of_barracks = self.structures(UnitTypeId.BARRACKS).amount + self.already_pending(UnitTypeId.BARRACKS)
        number_of_barracks_tech_lab = self.structures(UnitTypeId.BARRACKSTECHLAB).amount + self.already_pending(UnitTypeId.BARRACKSTECHLAB)
        marine_needed_for_attack = max(self.supply_cap / 2, 20)
        if not self.first_push_done:
            marine_needed_for_attack = 5

        await self.macro_bot.building_routine()

        if self.can_afford(UnitTypeId.SCV) and self.supply_workers < self.WorkerCountObjective:
            self.train(UnitTypeId.SCV)
        if number_of_barracks_tech_lab > 0 and self.can_afford(UnitTypeId.MARAUDER):
            self.train(UnitTypeId.MARAUDER)
        if number_of_barracks > 0 and self.can_afford(UnitTypeId.MARINE):
            self.train(UnitTypeId.MARINE)

        if self.enemy_structures.amount == 0 and self.supply_workers > 15:
            if self.ScoutingWorkerTag is None:
                self.ScoutingWorkerTag = self.all_own_units(UnitTypeId.SCV).first.tag
                for x in range(0, len(self.expansion_locations_list)):
                    self.all_own_units.by_tag(self.ScoutingWorkerTag).move(self.expansion_locations_list[x], True)

        if self.all_own_units.of_type([UnitTypeId.MARINE, UnitTypeId.MARAUDER]).amount > marine_needed_for_attack or self.supply_cap == 200:
            for marine in self.all_own_units.of_type([UnitTypeId.MARINE, UnitTypeId.MARAUDER]):
                if self.enemy_units.amount > 0 and self.enemy_units.first.is_visible:
                    marine.attack(self.enemy_units.first.position)
                elif self.enemy_structures.amount > 0:
                    marine.attack(self.enemy_structures.first.position)
                else:
                    marine.attack(self.enemy_start_locations[0])
            self.first_push_done = True
        else:
            for structure in self.structures:
                for unit in self.enemy_units:
                    if structure.distance_to(unit) < 20 and unit.is_visible:
                        for marine in self.all_own_units.of_type([UnitTypeId.MARINE, UnitTypeId.MARAUDER]):
                            marine.attack(unit.position)
                        break

        pass

    def on_end(self, result):
        print("Game ended.")
