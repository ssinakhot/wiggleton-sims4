# The Sims 4 Script Reloader
# Original routine by fetusdip at Mod The Sims
# Enhancements by Scumbumbo:
#   - reload modules in other folders
#   - reload modules from package folders
#   - reload modules with uppercase characters
from sims4.commands import Command, CommandType, CheatOutput
import sims4.reload

import sys
import traceback

def reload_module(filename, output):
    try:
        reloaded_module = sims4.reload.reload_file(filename)
        if reloaded_module is not None:
            return True
        else:
            output('Error reloading module')
    except:
        output('Unable to reload: Exception occurred')
        output(traceback.format_exc())
    return False

@Command('reload', 'r', command_type=CommandType.Live)
def script_reloader(module_name, _connection=None):
    output = CheatOutput(_connection)

    if module_name in sys.modules.keys():
        module = sys.modules[module_name]
        if hasattr(module, '__file__') and module.__file__.endswith('.py'):
            if reload_module(module.__file__, output):
                output('Module "{}" reloaded\n  from {}'.format(module_name, module.__file__))
        else:
            output('Unable to reload: Module "{}" was not loaded from a .py source'.format(module_name))
    else:
        for k,v in sys.modules.items():
            if k.lower() == module_name:
                if hasattr(v, '__file__') and v.__file__.endswith('.py'):
                    if reload_module(v.__file__, output):
                        output('Module "{}"\n  reloaded from {}'.format(k, v.__file__))
                        return True
                else:
                    output('Unable to reload: Module "{}" was not loaded from a .py source'.format(k))
                return False
        output('Unable to reload: Module "{}" was not found'.format(module_name))
    return False