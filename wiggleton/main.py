import inspect
import os
import random
import time
import traceback
from functools import wraps

from areaserver import c_api_zone_init, c_api_client_connect
import areaserver
import game_services
import services
import sims4.reload as r
import sims4.commands
import server_commands.sim_commands
from os import listdir, remove
from os.path import isfile, join
from threading import Thread

from server_commands import whim_commands, autonomy_commands, inventory_commands
from server_commands.argument_helpers import get_tunable_instance, get_optional_target, OptionalSimInfoParam
from sims import sim
from traits import traits

from wiggleton import s4mp
from wiggleton.helpers import injector
from wiggleton.helpers.injector import create_injection
from wiggleton.helpers.logging import log, create_injection_log, create_command_log, create_injection_append, \
    log_method_call
from wiggleton.helpers.native.undecorated import undecorated


@sims4.commands.Command('test', command_type=sims4.commands.CommandType.Live)
def test(opt_target:OptionalSimInfoParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection=_connection, target_type=OptionalSimInfoParam)
    if target is None:
        return False


@sims4.commands.Command('test_sims', command_type=sims4.commands.CommandType.Live)
def test_sims(_connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    for sim_info in tgt_client.selectable_sims:
        log("sim_info=" + str(sim_info))
        #sim_info.last_name = "Test"
    #tgt_client.send_selectable_sims_update()


@sims4.commands.Command('get_sims', command_type=sims4.commands.CommandType.Live)
def get_sims(_connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    for sim_info in tgt_client.selectable_sims:
        log(str(sim_info.id) + "|" + sim_info.first_name + "|" + sim_info.last_name)


@sims4.commands.Command('buffs', command_type=sims4.commands.CommandType.Live)
def buffs(opt_target:OptionalSimInfoParam=None, remove:bool=False, _connection=None):
    target = get_optional_target(opt_target, _connection=_connection, target_type=OptionalSimInfoParam)
    if target is None:
        return False
    current_timestamp = services.time_service().sim_now.absolute_ticks()
    log(str(current_timestamp) + "|" + str(target.id) + "|" + target.first_name + "|" + target.last_name)
    buffs_to_remove = []
    for buff_entry in target.Buffs:
        (timestamp, rate_multiplier) = buff_entry.get_timeout_time()
        if timestamp == 0:
            continue

        log(str(buff_entry) + "|" + str(timestamp - current_timestamp) + "|" + str(rate_multiplier))
        if remove:
            buffs_to_remove.append(buff_entry)

    for buff_entry in buffs_to_remove:
        target.Buffs.remove_buff_entry(buff_entry)


@sims4.commands.Command('modify_funds', command_type=sims4.commands.CommandType.Live)
def _modify_funds(amount: int, _connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    current_amount = tgt_client.active_sim.family_funds.money
    if amount < 0 and (current_amount - amount) < 0:
        amount = 0 - current_amount
    server_commands.sim_commands.modify_fund_helper(amount,
                                                    server_commands.sim_commands.Consts_pb2.TELEMETRY_MONEY_CHEAT,
                                                    tgt_client.active_sim)


@sims4.commands.Command('set_motive_household', command_type=sims4.commands.CommandType.Live)
def set_motive_household(motive: str, value: int, _connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    for sim_info in tgt_client.selectable_sims:
        stat_type = get_tunable_instance(sims4.resources.Types.STATISTIC, motive, exact_match=True)
        sim_info.set_stat_value(stat_type, value)


@sims4.commands.Command('randomize_motives_household', command_type=sims4.commands.CommandType.Live)
def randomize_motives_household(_connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    for sim_info in tgt_client.selectable_sims:
        all_motives = ['motive_fun', 'motive_social', 'motive_hygiene', 'motive_hunger', 'motive_energy',
                       'motive_bladder']
        for motive in all_motives:
            stat_type = get_tunable_instance(sims4.resources.Types.STATISTIC, motive, exact_match=True)
            random_value = random.uniform(stat_type.min_value, stat_type.max_value)
            sim_info.set_stat_value(stat_type, random_value)


@sims4.commands.Command('fill_motives_household', command_type=sims4.commands.CommandType.Live)
def fill_motives_household(_connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    for sim_info in tgt_client.selectable_sims:
        all_motives = ['motive_fun', 'motive_social', 'motive_hygiene', 'motive_hunger', 'motive_energy',
                       'motive_bladder']
        for motive in all_motives:
            stat_type = get_tunable_instance(sims4.resources.Types.STATISTIC, motive, exact_match=True)
            sim_info.set_stat_value(stat_type, stat_type.max_value)


@sims4.commands.Command('tank_motives_household', command_type=sims4.commands.CommandType.Live)
def tank_motives_household(_connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    for sim_info in tgt_client.selectable_sims:
        all_motives = ['motive_fun', 'motive_social', 'motive_hygiene', 'motive_hunger', 'motive_energy',
                       'motive_bladder']
        for motive in all_motives:
            stat_type = get_tunable_instance(sims4.resources.Types.STATISTIC, motive, exact_match=True)
            sim_info.set_stat_value(stat_type, stat_type.min_value)


@sims4.commands.Command('w.reload', command_type=sims4.commands.CommandType.Live)
def reload_service(file_path:str, _connection=None):
    try:
        success = None
        if file_path == "all":
            files = ["__init__", "main", "s4mp"]
            basepath = os.path.dirname(os.path.realpath(__file__))
            for file in files:
                path = os.path.join(basepath, file) + '.py'
                log('Reloading ' + path)
                success = r.reload_file(path)
                if success is None:
                    break
        else:
            path = os.path.dirname(os.path.realpath(__file__))
            path = os.path.join(path, file_path) + '.py'
            log('Reloading ' + path)
            success = r.reload_file(path)
        if success is not None:
            log('Done reloading!')
        else:
            log('Error loading module or module does not exist')
    except BaseException as ex:
        log('Reload failed: ')
        for arg in ex.args:
            log(arg)


@sims4.commands.Command('redemption', command_type=sims4.commands.CommandType.Live)
def _redemption(_connection=None):
    redemption_checker()


def redemption_checker():
    try:
        service_manager = game_services.service_manager
        if service_manager is None:
            return
        client_manager = service_manager.client_manager
        if client_manager is None:
            return
        client = client_manager.get_first_client()
        if client is None:
            return
        cheat_service = service_manager.cheat_service
        if cheat_service is None:
            return
        cheat_service.enable_cheats()
        cheat_service.send_to_client(client)

        directory = 'C:\\Users\\Public\\Documents\\Redemption\\The Sims 4\\'
        files = [f for f in listdir(directory) if isfile(join(directory, f))]
        for file in files:
            if not file.endswith(".txt"):
                continue
            f = open(directory + file, "r")
            cmd = f.readline()
            f.close()
            remove(directory + file)
            sims4.commands.execute(cmd, client.id)
            log(cmd)
    except Exception as e:
        log(e)


class MyThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True

    def run(self):
        while thread_runner:
            redemption_checker()
            time.sleep(1)


thread_runner = True
thread = MyThread()
thread.start()


@injector.inject(services, 'stop_global_services')
def stop_global_services(original):
    global thread_runner
    thread_runner = False
    original()


def inject():
    log("wiggleton injecting...")
    services.on_enter_main_menu = create_injection_log(undecorated(services.on_enter_main_menu))
    # areaserver.c_api_client_connect = create_injection_log(undecorated(areaserver.c_api_client_connect))
    # areaserver.c_api_zone_init = create_injection_log(undecorated(areaserver.c_api_zone_init))
    areaserver.c_api_zone_loaded = create_injection_log(undecorated(areaserver.c_api_zone_loaded))
    areaserver.c_api_server_init = create_injection_log(undecorated(areaserver.c_api_server_init))
    # create_command_log("whims.refresh", sims4.commands.CommandType.Live, whim_commands.refresh)
    # create_command_log("whims.toggle_lock", sims4.commands.CommandType.Live, whim_commands.toggle_lock)
    # create_command_log("inventory.open_ui", sims4.commands.CommandType.Live, inventory_commands.open_inventory_ui)
    log("wiggleton injecting done.")


inject()


c_api_zone_init = log_method_call(c_api_zone_init)


c_api_client_connect = log_method_call(c_api_client_connect)
