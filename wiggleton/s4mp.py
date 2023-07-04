import time
import traceback
from threading import Timer

import objects
import omega
import sims4
from bucks import bucks_commands
from distributor.ops import GenericProtocolBufferOp
from distributor.system import Distributor
from protocolbuffers import UI_pb2, Consts_pb2
from protocolbuffers.DistributorOps_pb2 import Operation
from protocolbuffers.Distributor_pb2 import ViewUpdate
from server_commands import whim_commands, inventory_commands, sim_commands
from sims4multiplayer.client.client_config import LOCAL_ONLY_OPS, LOCAL_ONLY_MSG_IDS
from sims4multiplayer.decorator.networked_command import NetworkedCommand
from sims4multiplayer.interaction.add_interaction.add_interaction_server import AddInteractionServer
from sims4multiplayer.interaction.game_network_message_manager import GameNetworkMessageManager
from sims4multiplayer.launcher.launcher_config import LauncherConfig
from sims4multiplayer.protobuf.SelectChoiceMessage_pb2 import SelectChoiceMessage
from sims4multiplayer.protobuf.WrapperMessage_pb2 import WrapperMessage

from wiggleton.helpers.injector import create_injection
from wiggleton.helpers.logging import log

from inspect import signature

import services
from sims4 import commands
from sims4multiplayer.ui.notification_manager import NotificationManager

from sims4multiplayer.decorator.message_handler import MessageHandler
from sims4multiplayer.decorator.override import Override
from sims4multiplayer.network.network_client import NetworkClient
from sims4multiplayer.protobuf.ChatMessage_pb2 import ChatMessage


class MessageHandlerWrapper:
    func_name = None

    _message_name = None
    _message_handler = None
    _add_hook_func_key = None
    _remove_hook_func_key = None
    _running_key = None

    def __init__(self, message_handler: MessageHandler):
        self._message_handler = message_handler
        attrs = dir(self._message_handler)
        _methods = []

        for attr_name in attrs:
            if attr_name.startswith("_MessageHandler__"):
                value = getattr(self._message_handler, attr_name)
                if type(value) is str:
                    self._message_name = value
                elif type(value) is bool:
                    self._running_key = attr_name
                # elif type(value) is Override.Type:
                elif type(value).__name__ == "function":
                    self.func_name = value.__name__
                elif type(value).__name__ == "method":
                    sig = signature(value)
                    if str(sig) == "()":
                        _methods.append((attr_name, value))

        last_status = self.is_running()
        for (key, method) in _methods:
            method()
            status_changed = self.is_running() != last_status
            last_status = self.is_running()

            if status_changed and self.is_running():
                self._add_hook_func_key = key
            elif status_changed and not self.is_running():
                self._remove_hook_func_key = key
            elif self.is_running():
                self._add_hook_func_key = key
            else:
                self._remove_hook_func_key = key

    def add_hook(self):
        if self._add_hook_func_key is not None:
            getattr(self._message_handler, self._add_hook_func_key)()

    def remove_hook(self):
        if self._remove_hook_func_key is not None:
            getattr(self._message_handler, self._remove_hook_func_key)()

    def is_running(self):
        if self._running_key is not None:
            return getattr(self._message_handler, self._running_key)
        return False


class AddInteractionServerWrapper:
    _server = None

    _choice_menu_key = None
    _generate_choices_message_key = None
    _select_choice_message_key = None
    _generate_phone_choices_message_key = None

    def __init__(self, server:AddInteractionServer):
        self._server = server
        attrs = dir(self._server)
        _methods = []
        for attr_name in attrs:
            if attr_name.startswith("_AddInteractionServer__"):
                value = getattr(self._server, attr_name)
                if type(value).__name__ == "function":
                    _methods.append((attr_name, value))
                elif type(value).__name__ == "dict":
                    self._choice_menu_key = attr_name

        for (key, method) in _methods:
            sig = str(signature(method))
            if sig.endswith("GenerateChoicesMessage_pb2.GenerateChoicesMessage)"):
                self._generate_choices_message_key = key
            elif sig.endswith("SelectChoiceMessage_pb2.SelectChoiceMessage)"):
                self._select_choice_message_key = key
            elif sig.endswith("GeneratePhoneChoicesMessage_pb2.GeneratePhoneChoicesMessage)"):
                self._generate_phone_choices_message_key = key

    def get_choice_menus(self):
        return getattr(self._server, self._choice_menu_key)

    @staticmethod
    @MessageHandler(SelectChoiceMessage, Override.Type.SERVER)
    def receive_select_choice_message(msg:SelectChoiceMessage):
        try:
            AddInteractionServer.waiting_for_callback_player_id = msg.player_id
            if not _AddInteractionServerWrapper.get_choice_menus()[msg.player_id]:
                log(f'Received select choice for not existing menu - player_id: {msg.player_id}')
                return
            if _AddInteractionServerWrapper.get_choice_menus()[msg.player_id].revision != msg.reference_id:
                log(f'Revision mismatch: {_AddInteractionServerWrapper.get_choice_menus()[msg.player_id].revision} != {msg.reference_id}')
                return
            menu_item = _AddInteractionServerWrapper.get_choice_menus()[msg.player_id].menu_items.get(msg.choice_id)

            is_open_inventory_ui = menu_item.aop.affordance.__name__ == "Open_Inventory_Ui"
            if is_open_inventory_ui:
                open_inventory_msg = prepare_open_inventory_msg(menu_item.aop.target.inventory_component)
                GameNetworkMessageManager.send_message_over_network(Consts_pb2.MSG_OBJECTS_VIEW_UPDATE, open_inventory_msg, msg.player_id)
                return

            context = menu_item.context
            if menu_item is not None:
                if menu_item.result and not menu_item.target_invalid:
                    menu_item.aop.test_and_execute(context)
                else:
                    log('Attempt to select invalid interaction from a ChoiceMenu')
            AddInteractionServer.waiting_for_callback_player_id = None
        except Exception as ex:
            log('receive_select_choice_message error: ' + str(ex))
            log(str(traceback.format_exc()))


def prepare_open_inventory_msg(inventory_component):
    pb = UI_pb2.OpenInventory()
    pb.object_id = inventory_component.owner.id
    pb.inventory_id = inventory_component._storage._get_inventory_id()
    pb.inventory_type = inventory_component._storage._get_inventory_ui_type()
    op = GenericProtocolBufferOp(Operation.OPEN_INVENTORY, pb)
    instance = Distributor.instance()
    journal_seed = instance.journal._build_journal_seed(op, None, None)
    journal_entry = instance.journal._build_journal_entry(journal_seed)
    (obj_id, operation, payload_type, manager_id, obj_name) = journal_entry
    view_update = ViewUpdate()
    entry = view_update.entries.add()
    entry.primary_channel.id.manager_id = manager_id
    entry.primary_channel.id.object_id = obj_id
    entry.operation_list.operations.append(operation)
    return view_update


@MessageHandler(ChatMessage, Override.Type.ALL)
def receive_chat_message(msg: ChatMessage):
    if not msg.sender_name.startswith("Wiggleton"):
        NotificationManager.show_notification(f'{msg.sender_name}: {msg.message}')
    else:
        log(f'Processing {msg.sender_name}: {msg.message}')
        splitted = msg.sender_name.split("|")
        process_type = splitted[1]
        player_id = splitted[2]
        if process_type == "Server" and NetworkClient.is_server \
                or process_type == "Client" and not NetworkClient.is_server \
                or process_type == "All":
            log(f'Running {msg.sender_name}: {msg.message}')
            commands.execute(msg.message, services.get_first_client().id)
        else:
            log(f'Skipped {msg.sender_name}: {msg.message}')


def override_message(name:str, all:bool):
    try:
        log("Trying to remove " + name + " handler...")
        removed = False
        tries = 0
        while not removed:
            log("Sleeping...")
            time.sleep(1)
            handlers = get_message_handlers_by_name(name)
            for handler in handlers:
                if all or not handler.func_name.startswith("__"):
                    continue
                log("Removing " + name + " handler: " + handler.func_name)
                removed = True
                handler.remove_hook()
                del handler
            tries = tries + 1
            if tries > 5:
                removed = True
        time.sleep(1)
        log("End trying to remove " + name + " handler.")
    except Exception as ex:
        log('override_message error: ' + str(ex))
        log(str(traceback.format_exc()))


def hooks():
    override_message("chat_message", False)
    override_message("select_choice_message", False)


@sims4.commands.Command('w.start', command_type=sims4.commands.CommandType.Live)
def start_hook(_connection=None):
    logging_delay_timer = Timer(1, hooks)
    logging_delay_timer.daemon = False
    logging_delay_timer.start()


def find_function(obj, search_term):
    attrs = dir(obj)
    for attr_name in attrs:
        if attr_name.startswith("__") and not attr_name.endswith("__"):
            attr = getattr(obj, attr_name)
            if attr is not None:
                annotation = getattr(attr, "__annotations__")
                if annotation is not None:
                    values = annotation.values()
                    if len(values) > 0:
                        value = list(values)[0]
                        if value.__name__ == search_term:
                            return attr
    return None


def get_message_handlers_by_name(name):
    handlers = []
    hooks = getattr(NetworkClient.on_message, "_EventHook__O00O0OOOOO0OOO0O0")
    for hook in hooks:
        hook_instance = hook.__self__
        if hook_instance.__class__.__name__ == "MessageHandler":
            hook_attrs = dir(hook_instance)
            for attr_name in hook_attrs:
                if attr_name.startswith("_MessageHandler__"):
                    value = getattr(hook_instance, attr_name)
                    if value == name:
                        handlers.append(MessageHandlerWrapper(hook_instance))
    return handlers


@NetworkedCommand(bucks_commands.reset_recently_locked_perks, ['bucks.reset_recently_locked_perks'])
def reset_recently_locked_perks(msg:WrapperMessage, *args, **kwargs):
    basic_forward(msg, 'bucks.reset_recently_locked_perks', *args, **kwargs)


@NetworkedCommand(bucks_commands.lock_all_perks_for_bucks_type, ['bucks.lock_all_perks_for_bucks_type'])
def lock_all_perks_for_bucks_type(msg:WrapperMessage, *args, **kwargs):
    basic_forward(msg, 'bucks.lock_all_perks_for_bucks_type', *args, **kwargs)


@NetworkedCommand(bucks_commands.lock_perk_by_name_or_id, ['bucks.lock_perk'])
def lock_perk(msg:WrapperMessage, *args, **kwargs):
    basic_forward(msg, 'bucks.lock_perk', *args, **kwargs)


@NetworkedCommand(bucks_commands.update_bucks_by_amount, ['bucks.update_bucks_by_amount'])
def update_bucks_by_amount(msg:WrapperMessage, *args, **kwargs):
    basic_forward(msg, 'bucks.update_bucks_by_amount', *args, **kwargs)


@NetworkedCommand(bucks_commands.unlock_multiple_perks_with_buck_type, ['bucks.unlock_multiple_perks'])
def unlock_multiple_perks(msg:WrapperMessage, *args, **kwargs):
    basic_forward(msg, 'bucks.unlock_multiple_perks', *args, **kwargs)


@NetworkedCommand(bucks_commands.unlock_perk_by_name_or_id, ['bucks.unlock_perk'])
def unlock_perk(msg:WrapperMessage, *args, **kwargs):
    basic_forward(msg, 'bucks.unlock_perk', *args, **kwargs)


@NetworkedCommand(bucks_commands.request_perks_list, ['bucks.request_perks_list'])
def request_perks_list(msg:WrapperMessage, *args, **kwargs):
    basic_forward(msg, 'bucks.request_perks_list', *args, **kwargs)


@NetworkedCommand(whim_commands.refresh, ['whims.refresh'])
def whim_refresh(msg:WrapperMessage, *args, **kwargs):
    basic_forward(msg, 'whims.refresh', *args, **kwargs)


@NetworkedCommand(whim_commands.toggle_lock, ['whims.toggle_lock'])
def whim_toggle_lock(msg:WrapperMessage, *args, **kwargs):
    basic_forward(msg, 'whims.toggle_lock', *args, **kwargs)


@NetworkedCommand(sim_commands.whims_award_prize, ['sims.whims_award_prize'])
def whims_award_prize(msg:WrapperMessage, *args, **kwargs):
    basic_forward(msg, 'sims.whims_award_prize', args[0], str(services.get_first_client().active_sim_info.id))


@NetworkedCommand(sim_commands.request_satisfaction_reward_list, ['sims.request_satisfaction_reward_list'])
def request_satisfaction_reward_list(msg:WrapperMessage, *args, **kwargs):
    basic_forward(msg, 'sims.request_satisfaction_reward_list', str(services.get_first_client().active_sim_info.id), **kwargs)


def basic_forward(msg:WrapperMessage, cmd, *args, **kwargs):
    msg.chat_message.sender_name = "Wiggleton|Server|" + str(LauncherConfig.player_id)
    msg.chat_message.message = cmd + " " + " ".join(args)
    log("Sending: " + msg.chat_message.message)


@sims4.commands.Command('w.run', command_type=sims4.commands.CommandType.Live)
def run_command(cmd:str , _connection=None):
    msg = WrapperMessage()
    msg.target_client = LauncherConfig.server_id
    msg.chat_message.sender_name = "Wiggleton|Server|" + str(LauncherConfig.player_id)
    msg.chat_message.message = cmd
    log("Sending: " + msg.chat_message.message)
    NetworkClient.send_message(msg)


try:
    NetworkClient.on_connected += start_hook
    _AddInteractionServerWrapper = AddInteractionServerWrapper(AddInteractionServer)
    # Operation.SIM_SATISFACTION_REWARDS, Operation.UI_UPDATE
    LOCAL_ONLY_OPS.extend([Operation.OPEN_INVENTORY, Operation.HEARTBEAT])
    # LOCAL_ONLY_MSG_IDS.extend([Consts_pb2.MSG_GAMEPLAY_PERK_LIST])
    LOCAL_ONLY_MSG_IDS.extend([Consts_pb2.MSG_SET_CHEAT_STATUS])
    # log(services.get_first_client().active_sim_info.id)
except Exception as ex:
    log('error: ' + str(ex))
    log(str(traceback.format_exc()))


# /suggest
# **VERSIONS:** S4MP 0.23.0 Windows
# **EXPLANATION: ** If you add in network commands and server for `whims.refresh` and `whims.togglelock`, this will allow users to lock and refresh whims for people trying to achieve satisfaction rewards quicker.