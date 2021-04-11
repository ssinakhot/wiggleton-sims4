import random
import string
import services
import sims4.commands
import server_commands.sim_commands
from os import listdir, remove
from os.path import isfile, join
from threading import Event, Thread
from server_commands.argument_helpers import get_tunable_instance
from wiggleton.helpers.customlogging import wiggleton_log


@sims4.commands.Command('modify_funds', command_type=sims4.commands.CommandType.Live)
def _modify_funds(amount: int, _connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    server_commands.sim_commands.modify_fund_helper(amount,
                                                    server_commands.sim_commands.Consts_pb2.TELEMETRY_MONEY_CHEAT,
                                                    tgt_client.active_sim)


@sims4.commands.Command('set_motive_household', command_type=sims4.commands.CommandType.Live)
def set_motives(motive: string, max: bool, _connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    for sim_info in tgt_client.selectable_sims:
        stat_type = get_tunable_instance(sims4.resources.Types.STATISTIC, motive, exact_match=True)
        sim_info.set_stat_value(stat_type, stat_type.max_value if max else stat_type.min_value)


@sims4.commands.Command('randomize_motives_household', command_type=sims4.commands.CommandType.Live)
def randomize_motives_household(_connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    for sim_info in tgt_client.selectable_sims:
        all_motives = ['motive_fun', 'motive_social', 'motive_hygiene', 'motive_hunger', 'motive_energy', 'motive_bladder']
        for motive in all_motives:
            stat_type = get_tunable_instance(sims4.resources.Types.STATISTIC, motive, exact_match=True)
            random_value = random.uniform(stat_type.min_value, stat_type.max_value)
            sim_info.set_stat_value(stat_type, random_value)


@sims4.commands.Command('redemption', command_type=sims4.commands.CommandType.Live)
def _redemption(_connection=None):
    redemption_checker()


def redemption_checker():
    client = server_commands.sim_commands.services.get_first_client()
    cheat_service = services.get_cheat_service()
    cheat_service.enable_cheats()
    cheat_service.send_to_client(client)

    directory = 'C:\\Users\\Public\\Documents\\Redemption\\The Sims 4\\'
    files = [f for f in listdir(directory) if isfile(join(directory, f))]
    for file in files:
        f = open(directory + file, "r")
        cmd = f.readline()
        sims4.commands.execute(cmd, client.id)
        f.close()
        remove(directory + file)


class MyThread(Thread):
    def __init__(self, event):
        Thread.__init__(self)
        self.stopped = event
        self.daemon = True

    def run(self):
        while not self.stopped.wait(0.25):
            redemption_checker()


stopFlag = Event()
thread = MyThread(stopFlag)
thread.start()
