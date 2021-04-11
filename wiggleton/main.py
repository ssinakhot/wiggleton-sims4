import random
import time
import game_services
import services
import sims4.commands
import server_commands.sim_commands
from os import listdir, remove
from os.path import isfile, join
from threading import Thread
from server_commands.argument_helpers import get_tunable_instance

from wiggleton.helpers import injector
from wiggleton.helpers.customlogging import wiggleton_log


@sims4.commands.Command('modify_funds', command_type=sims4.commands.CommandType.Live)
def _modify_funds(amount: int, _connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    server_commands.sim_commands.modify_fund_helper(amount,
                                                    server_commands.sim_commands.Consts_pb2.TELEMETRY_MONEY_CHEAT,
                                                    tgt_client.active_sim)


@sims4.commands.Command('set_motive_household', command_type=sims4.commands.CommandType.Live)
def set_motives(motive: str, value: int, _connection=None):
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
def randomize_motives_household(_connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    for sim_info in tgt_client.selectable_sims:
        all_motives = ['motive_fun', 'motive_social', 'motive_hygiene', 'motive_hunger', 'motive_energy',
                       'motive_bladder']
        for motive in all_motives:
            stat_type = get_tunable_instance(sims4.resources.Types.STATISTIC, motive, exact_match=True)
            sim_info.set_stat_value(stat_type, stat_type.max_value)


@sims4.commands.Command('tank_motives_household', command_type=sims4.commands.CommandType.Live)
def randomize_motives_household(_connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    for sim_info in tgt_client.selectable_sims:
        all_motives = ['motive_fun', 'motive_social', 'motive_hygiene', 'motive_hunger', 'motive_energy',
                       'motive_bladder']
        for motive in all_motives:
            stat_type = get_tunable_instance(sims4.resources.Types.STATISTIC, motive, exact_match=True)
            sim_info.set_stat_value(stat_type, stat_type.min_value)


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
            wiggleton_log(cmd)
    except Exception as e:
        wiggleton_log(e)


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
