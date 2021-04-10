#    Copyright 2020 June Hanabi
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
import random

import sims4.commands
import server_commands.sim_commands
from os import listdir, remove
from os.path import isfile, join
from threading import Event, Thread


@sims4.commands.Command('modify_funds', command_type=sims4.commands.CommandType.Live)
def _modify_funds(amount: int, _connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    server_commands.sim_commands.modify_fund_helper(amount,
                                                    server_commands.sim_commands.Consts_pb2.TELEMETRY_MONEY_CHEAT,
                                                    tgt_client.active_sim)


@sims4.commands.Command('fill_commodities_household', command_type=sims4.commands.CommandType.Live)
def set_commodities_to_best_values_household(_connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    sims4.commands.output('Setting all motives on all household sims to full.', _connection)
    for sim_info in tgt_client.selectable_sims:
        if sim_info.commodity_tracker is not None:
            sim_info.commodity_tracker.set_all_commodities_to_best_value(visible_only=False)


@sims4.commands.Command('tank_commodities_household', command_type=sims4.commands.CommandType.Live)
def set_commodities_to_best_values_household(_connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    for sim_info in tgt_client.selectable_sims:
        if sim_info.commodity_tracker is not None:
            sim_info.commodity_tracker.debug_set_all_to_min()


def _randomize_motive(stat_type, sim_info):
    min_value = stat_type.min_value
    max_value = stat_type.max_value
    random_value = random.uniform(min_value, max_value)
    sim_info.set_stat_value(stat_type, random_value)


@sims4.commands.Command('randomize_motives_household', command_type=sims4.commands.CommandType.Live)
def randomize_motives_household(_connection=None):
    tgt_client = server_commands.sim_commands.services.client_manager().get(_connection)
    for sim_info in tgt_client.selectable_sims:
        for stat_type in sim_info.get_initial_commodities():
            _randomize_motive(stat_type, sim_info)



@sims4.commands.Command('redemption', command_type=sims4.commands.CommandType.Live)
def _redemption(_connection=None):
    redemption_checker()


def redemption_checker():
    directory = 'C:\\Users\\Public\\Documents\\Redemption\\The Sims 4\\'
    files = [f for f in listdir(directory) if isfile(join(directory, f))]
    for file in files:
        f = open(directory + file, "r")
        cmd = f.readline()
        id = server_commands.sim_commands.services.get_first_client().id
        sims4.commands.execute("testingcheats on", id)
        sims4.commands.execute(cmd, id)
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
