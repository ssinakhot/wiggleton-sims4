__version__ = '0.2.0'

def undecorated(o):
    if type(o) is type:
        return o
    try:
        closure = o.func_closure
    except AttributeError:
        pass
    try:
        closure = o.__closure__
    except AttributeError:
        return
    else:
        if closure:
            for cell in closure:
                if cell.cell_contents is o:
                    continue
                undecd = undecorated(cell.cell_contents)
                if undecd:
                    return undecd
        else:
            return o

