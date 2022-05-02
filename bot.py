from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.unit import Unit


class CompetitiveBot(BotAI):
    WorkerCountObjective = 80
    ScoutingWorkerTag = None

    def gas_routine(self, desired_gas: int = 2):
        exploitable_extractors = self.gas_buildings.filter(lambda unit: unit.has_vespene)
        if exploitable_extractors.amount + self.already_pending(UnitTypeId.REFINERY) < desired_gas:
            unexploited_geysers = []
            for geyser in self.vespene_geyser:
                for commandcenter in self.townhalls.ready:
                    if geyser.distance_to(commandcenter) < 10:
                        unexploited_geysers.append(geyser)
                        continue
            if len(unexploited_geysers) > 0:
                target_geyser = unexploited_geysers[0]
                if self.can_afford(UnitTypeId.REFINERY):
                    self.workers.closest_to(target_geyser).build_gas(target_geyser)

    def mule_routine(self):
        for orbital in self.structures(UnitTypeId.ORBITALCOMMAND):
            if orbital.energy > 50:
                orbital(AbilityId.CALLDOWNMULE_CALLDOWNMULE, self.mineral_field.closest_to(orbital))

    async def on_start(self):
        print("Game started")
        # Do things here before the game starts

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
        self.gas_routine()
        self.mule_routine()
        numberOfBarracks = self.structures(UnitTypeId.BARRACKS).amount + self.already_pending(UnitTypeId.BARRACKS)

        if self.can_afford(UnitTypeId.COMMANDCENTER):
            position = await self.get_next_expansion()
            await self.build(UnitTypeId.COMMANDCENTER, position)
        if self.can_afford(UnitTypeId.BARRACKS) and numberOfBarracks < self.townhalls.amount * 3:
            await self.build(UnitTypeId.BARRACKS, self.townhalls.first.position.towards(self.game_info.map_center, 7))
        if self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.supply_left < 3 and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 1:
            await self.build(UnitTypeId.SUPPLYDEPOT, self.townhalls.first.position.towards(self.game_info.map_center, 7))
        if self.can_afford(UnitTypeId.SCV) and self.supply_workers < self.WorkerCountObjective:
            self.train(UnitTypeId.SCV)
        if numberOfBarracks > 0 and self.can_afford(UnitTypeId.MARINE):
            self.train(UnitTypeId.MARINE)

        if self.enemy_structures.amount == 0 and self.supply_workers > 15:
            if self.ScoutingWorkerTag is None:
                self.ScoutingWorkerTag = self.all_own_units(UnitTypeId.SCV).first.tag
                for x in range(0, len(self.expansion_locations_list)):
                    self.all_own_units.by_tag(self.ScoutingWorkerTag).move(self.expansion_locations_list[x], True)

        if self.all_own_units.of_type(UnitTypeId.MARINE).amount > 20:
            for marine in self.all_own_units.of_type(UnitTypeId.MARINE):
                if self.enemy_units.amount > 0:
                    marine.attack(self.enemy_units.first.position)
                elif self.enemy_structures.amount > 0:
                    marine.attack(self.enemy_structures.first.position)
                else:
                    marine.attack(self.enemy_start_locations[0])

        pass

    def on_end(self, result):
        print("Game ended.")
        # Do things here after the game ends
