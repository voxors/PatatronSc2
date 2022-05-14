import random
from typing import List

from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2, Point3
from sc2.pixel_map import PixelMap
from sc2.unit import Unit


class Macro:
    opening: bool = True
    bot: BotAI
    main_townhall: Unit

    def __init__(self, bot: BotAI):
        self.bot = bot

    async def addon_building(self, building_id: UnitTypeId):
        def points_to_build_addon(sp_position: Point2) -> List[Point2]:
            """ Return all points that need to be checked when trying to build an addon. Returns 4 points. """
            addon_offset: Point2 = Point2((2.5, -0.5))
            addon_position: Point2 = sp_position + addon_offset
            addon_points = [
                (addon_position + Point2((x - 0.5, y - 0.5))).rounded for x in range(0, 2) for y in range(0, 2)
            ]
            return addon_points

        # Build building addon or lift if no room to build addon
        building: Unit
        for building in self.bot.structures(UnitTypeId.BARRACKS).ready.idle:
            if not building.has_add_on and self.bot.can_afford(building_id):
                addon_points = building.add_on_position
                if await self.bot.can_place_single(UnitTypeId.SUPPLYDEPOT, addon_points):
                    building.build(building_id)
                else:
                    building(AbilityId.LIFT)

        # Find a position to land for a flying building so that it can build an addon
        for building in self.bot.structures(UnitTypeId.BARRACKSFLYING).idle:
            land_position = building.position.rounded.offset((0.5, 0.5))
            land_positions = [land_position.offset((x, y)) for x in range(-10, 10) for y in range(-10, 10)]
            random.shuffle(land_positions)
            for target_land_position in land_positions:
                if await self.bot.can_place_single(UnitTypeId.BARRACKS, target_land_position) and await self.bot.can_place_single(UnitTypeId.SUPPLYDEPOT, target_land_position.offset((2.5, 0.5))):
                    building(AbilityId.LAND_BARRACKS, target_land_position)
                    break

        # Show where it is flying to and show grid
        unit: Unit
        for building in self.bot.structures(UnitTypeId.BARRACKSFLYING).filter(lambda unit: not unit.is_idle):
            if isinstance(building.order_target, Point2):
                p: Point3 = Point3((*building.order_target, self.bot.get_terrain_z_height(building.order_target)))
                self.bot.client.debug_box2_out(p, color=Point3((255, 0, 0)))

    def mule_routine(self):
        for orbital in self.bot.structures(UnitTypeId.ORBITALCOMMAND):
            if orbital.energy > 50:
                orbital(AbilityId.CALLDOWNMULE_CALLDOWNMULE, self.bot.mineral_field.closest_to(orbital))

    def unit_generic_upgrade_routine(self):
        for engineering_bay in self.bot.structures(UnitTypeId.ENGINEERINGBAY).idle:
            if self.bot.can_afford(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1):
                engineering_bay(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1)
            if self.bot.can_afford(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1):
                engineering_bay(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1)
            if self.bot.can_afford(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2):
                engineering_bay(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2)
            if self.bot.can_afford(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2):
                engineering_bay(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2)
            if self.bot.can_afford(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3):
                engineering_bay(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3)
            if self.bot.can_afford(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3):
                engineering_bay(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3)

    async def get_structure_position(self, position: Point2, building_id: UnitTypeId):
        return await self.bot.find_placement(building_id, position)

    def supply_routine(self):
        for supply in self.bot.structures.of_type(UnitTypeId.SUPPLYDEPOT):
            supply(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

    def get_addon_to_build(self):
        building_to_build = []
        if not self.opening:
            total_barrack_reactor = self.bot.structures(UnitTypeId.BARRACKSREACTOR).amount
            total_barrack_tech = self.bot.structures(UnitTypeId.BARRACKSTECHLAB).amount
            total_barrack = self.bot.structures(UnitTypeId.BARRACKS).amount
            total_barrack_reactor_objective = abs(total_barrack * 0.5)
            total_barrack_tech_objective = total_barrack - total_barrack_reactor_objective
            barrack_without_addon = self.bot.structures(UnitTypeId.BARRACKS).filter(lambda barrack: not barrack.has_add_on)
            if self.bot.can_afford(AbilityId.BUILD_TECHLAB_BARRACKS) and total_barrack_tech_objective > total_barrack_tech and barrack_without_addon.amount > 0:
                building_to_build.append(UnitTypeId.BARRACKSTECHLAB)
            if self.bot.can_afford(AbilityId.BUILD_REACTOR_BARRACKS) and total_barrack_reactor_objective > total_barrack_reactor and barrack_without_addon.amount > 0:
                building_to_build.append(UnitTypeId.BARRACKSREACTOR)
        return building_to_build

    def get_building_and_pending_amount(self, unit_type_id: UnitTypeId):
        return self.bot.structures(unit_type_id).amount + self.bot.already_pending(unit_type_id)

    def get_building_to_build(self):
        building_to_build = []
        if self.opening:
            if self.get_building_and_pending_amount(UnitTypeId.SUPPLYDEPOT) + self.get_building_and_pending_amount(UnitTypeId.SUPPLYDEPOTLOWERED) == 0:
                building_to_build.append(UnitTypeId.SUPPLYDEPOT)
            elif self.get_building_and_pending_amount(UnitTypeId.BARRACKS) == 0:
                building_to_build.append(UnitTypeId.BARRACKS)
            elif self.get_building_and_pending_amount(UnitTypeId.REFINERY) == 0:
                building_to_build.append(UnitTypeId.REFINERY)
            elif self.get_building_and_pending_amount(UnitTypeId.ORBITALCOMMAND) == 0 and self.bot.structures(UnitTypeId.BARRACKS).filter(lambda unit: unit.is_ready).amount == 1:
                building_to_build.append(UnitTypeId.ORBITALCOMMAND)
            elif self.get_building_and_pending_amount(UnitTypeId.ORBITALCOMMAND) == 1:
                building_to_build.append(UnitTypeId.COMMANDCENTER)
                if self.bot.townhalls.amount > 2:
                    self.opening = False
        else:
            if self.bot.structures(UnitTypeId.COMMANDCENTER).amount > 0:
                building_to_build.append(UnitTypeId.ORBITALCOMMAND)
            if self.bot.can_afford(UnitTypeId.SUPPLYDEPOT) and self.bot.supply_cap != 200:
                if self.bot.supply_cap > 150 and self.bot.already_pending(UnitTypeId.SUPPLYDEPOT) < 6 and self.bot.supply_left < 15:
                    building_to_build.append(UnitTypeId.SUPPLYDEPOT)
                elif self.bot.supply_cap > 100 and self.bot.already_pending(UnitTypeId.SUPPLYDEPOT) < 4 and self.bot.supply_left < 10:
                    building_to_build.append(UnitTypeId.SUPPLYDEPOT)
                elif self.bot.supply_cap > 50 and self.bot.already_pending(UnitTypeId.SUPPLYDEPOT) < 3 and self.bot.supply_left < 8:
                    building_to_build.append(UnitTypeId.SUPPLYDEPOT)
                elif self.bot.already_pending(UnitTypeId.SUPPLYDEPOT) < 2 and self.bot.supply_left < 5:
                    building_to_build.append(UnitTypeId.SUPPLYDEPOT)
            if self.bot.can_afford(UnitTypeId.BARRACKS) and \
                    (self.get_building_and_pending_amount(UnitTypeId.BARRACKS) + self.get_building_and_pending_amount(UnitTypeId.BARRACKSFLYING)) \
                    <= max(self.bot.townhalls.amount * 2, 7):
                building_to_build.append(UnitTypeId.BARRACKS)
            if self.bot.can_afford(UnitTypeId.COMMANDCENTER) and self.bot.already_pending(UnitTypeId.COMMANDCENTER) == 0:
                building_to_build.append(UnitTypeId.COMMANDCENTER)
            if self.bot.can_afford(UnitTypeId.ENGINEERINGBAY) and self.get_building_and_pending_amount(UnitTypeId.ENGINEERINGBAY) < 2:
                building_to_build.append(UnitTypeId.ENGINEERINGBAY)
            if self.bot.can_afford(UnitTypeId.REFINERY) and self.bot.gas_buildings.filter(lambda unit: unit.has_vespene).amount + self.bot.already_pending(UnitTypeId.EXTRACTOR) < 4:
                building_to_build.append(UnitTypeId.REFINERY)
        building_to_build.extend(self.get_addon_to_build())
        return building_to_build

    async def building_routine(self):
        building_to_build = self.get_building_to_build()
        self.supply_routine()
        self.unit_generic_upgrade_routine()
        self.mule_routine()
        for building_id in building_to_build:
            position_to_build = None
            if building_id == UnitTypeId.COMMANDCENTER:
                position_to_build = await self.bot.get_next_expansion()
            elif self.bot.townhalls.amount > 0:
                position_to_build = self.main_townhall.position.towards(self.bot.game_info.map_center, 7)

            if building_id == UnitTypeId.ORBITALCOMMAND:
                if self.bot.can_afford(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND) and self.bot.townhalls.amount > 0:
                    for townhall in self.bot.townhalls:
                        if townhall.is_idle:
                            townhall(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)
                        elif townhall.build_progress < 0.2 or self.opening:
                            townhall(AbilityId.CANCEL_QUEUE1)
                            townhall(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)
            elif building_id == UnitTypeId.REFINERY:
                unexploited_geysers = []
                for geyser in self.bot.vespene_geyser:
                    for commandcenter in self.bot.townhalls.ready:
                        if geyser.distance_to(commandcenter) < 10:
                            unexploited_geysers.append(geyser)
                if len(unexploited_geysers) > 0:
                    if self.bot.can_afford(building_id):
                        await self.bot.build(building_id, unexploited_geysers[0])
            elif building_id == UnitTypeId.BARRACKSTECHLAB or building_id == UnitTypeId.BARRACKSREACTOR:
                await self.addon_building(building_id)
            elif position_to_build is not None:
                if self.bot.can_afford(building_id):
                    position = await self.get_structure_position(position_to_build, building_id)
                    if position is not None:
                        worker = self.bot.select_build_worker(position)
                        if worker is not None:
                            worker.build(building_id, position)
