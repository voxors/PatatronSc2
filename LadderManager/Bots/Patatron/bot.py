from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId


class CompetitiveBot(BotAI):
    WorkerCountObjective = 80
    ScoutingWorkerTag = None

    async def on_start(self):
        print("Game started")
        # Do things here before the game starts

    async def on_unit_destroyed(self, unit_tag: int):
        if self.ScoutingWorkerTag == unit_tag:
            self.ScoutingWorkerTag = None

    async def on_step(self, iteration):
        await self.distribute_workers()
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
