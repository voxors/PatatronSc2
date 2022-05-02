import random
from typing import List, Coroutine

from . import queen_helper, surrender_logic, scouting, tech
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2

saving_money = False

async def expand_eco(bot: BotAI, desired_workers: int, desired_gas: int):
    await bot.distribute_workers()

    global saving_money
    # if saving_money:
    #     return

    # Build more hatcheries
    exploitable_mineral_fields = []
    for mineral_field in bot.mineral_field:
        for hatchery in bot.townhalls.ready:
            if mineral_field.distance_to(hatchery) < 10:
                exploitable_mineral_fields.append(mineral_field)

    desired_mineral_fields = (desired_workers - 3 * desired_gas) / 2
    if len(exploitable_mineral_fields) < desired_mineral_fields:
        if not bot.already_pending(UnitTypeId.HATCHERY):
            next_expansion = await bot.get_next_expansion()
            if next_expansion is not None:
                if bot.can_afford(UnitTypeId.HATCHERY):
                    await bot.build(UnitTypeId.HATCHERY, next_expansion)
                else:
                    saving_money = True
                    return # Save for hatchery

    # Build more extractors
    exploitable_extractors = bot.gas_buildings.filter(lambda unit: unit.has_vespene)
    if exploitable_extractors.amount + bot.already_pending(UnitTypeId.EXTRACTOR) < desired_gas:
        unexploited_geysers = []
        for geyser in bot.vespene_geyser:
            for hatchery in bot.townhalls.ready:
                if geyser.distance_to(hatchery) < 10:
                    unexploited_geysers.append(geyser)
                    continue
        if len(unexploited_geysers) > 0:
            target_geyser = unexploited_geysers[0]
            if bot.can_afford(UnitTypeId.EXTRACTOR):
                bot.workers.closest_to(target_geyser).build_gas(target_geyser)
            else:
                saving_money = True
                return # Save for extractor

    # Build more drones
    current_workers = int(bot.supply_workers + bot.already_pending(UnitTypeId.DRONE))
    if current_workers < desired_workers:
        bot.train(UnitTypeId.DRONE, desired_workers - current_workers)

    # Get 1 extra hatchery if floating minerals
    extra_mineral_fields = desired_mineral_fields - len(exploitable_mineral_fields)
    if not extra_mineral_fields >= 8:
        if not bot.already_pending(UnitTypeId.HATCHERY):
            next_expansion = await bot.get_next_expansion()
            if next_expansion is not None:
                if bot.can_afford(UnitTypeId.HATCHERY):
                    await bot.build(UnitTypeId.HATCHERY, next_expansion)

async def expand_army(bot: BotAI):
    if bot.supply_used == 200:
        return

    global saving_money
    if not saving_money and bot.structures(UnitTypeId.GREATERSPIRE).ready.amount > 0:
        corruptors = bot.all_own_units(UnitTypeId.CORRUPTOR)
        if corruptors.amount > 1:
            if bot.can_afford(UnitTypeId.BROODLORD):
                corruptors.first(AbilityId.MORPHTOBROODLORD_BROODLORD)
            else:
                saving_money = True

    if not saving_money and bot.structures(UnitTypeId.SPIRE).ready.amount > 0:
        corruptor_count = bot.all_own_units(UnitTypeId.CORRUPTOR).amount + bot.already_pending(UnitTypeId.CORRUPTOR)
        broodlord_count = bot.all_own_units(UnitTypeId.BROODLORD).amount + bot.already_pending(UnitTypeId.BROODLORD)
        if corruptor_count * 2 + broodlord_count * 4 < 0.4 * bot.supply_army:
            if bot.can_afford(UnitTypeId.CORRUPTOR):
                bot.train(UnitTypeId.CORRUPTOR)
            else:
                saving_money = True

    if not saving_money and bot.structures(UnitTypeId.BANELINGNEST).ready.amount > 0:
        for zergling in bot.all_own_units(UnitTypeId.ZERGLING):
            if bot.can_afford(UnitTypeId.BANELING):
                zergling(AbilityId.MORPHZERGLINGTOBANELING_BANELING)

    if not saving_money and bot.structures(UnitTypeId.ROACHWARREN).ready.amount > 0:
        if bot.can_afford(UnitTypeId.ROACH):
            bot.train(UnitTypeId.ROACH)

    if bot.minerals > 500:
        bot.train(UnitTypeId.ZERGLING)

async def develop_tech(bot: BotAI):
    tech.saving_money = False
    await tech.try_build_tech(bot, UnitTypeId.EVOLUTIONCHAMBER, 2)
    await tech.tech_banelings(bot)
    await tech.tech_zerglings(bot, adrenal_glands=True)
    await tech.tech_broodlords(bot)
    await tech.tech_melee(bot)
    await tech.tech_ground_armor(bot)

    global saving_money
    if tech.saving_money:
        saving_money = True

async def develop_tech_list(bot: BotAI, techs: List[Coroutine]):
    tech.saving_money = False

    for coroutine in techs:
        await coroutine

    global saving_money
    if tech.saving_money:
        saving_money = True

def reset_saving():
    global saving_money
    saving_money = False
    tech.saving_money = False