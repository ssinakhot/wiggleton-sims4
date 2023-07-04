from __future__ import print_function
import re
import sys
import inspect
import operator
import itertools
import collections
__version__ = '4.0.11'
if sys.version >= '3':
    from inspect import getfullargspec

    def get_init(cls):
        return cls.__init__

else:
    FullArgSpec = collections.namedtuple('FullArgSpec', 'args varargs varkw defaults kwonlyargs kwonlydefaults')

    def getfullargspec(f):
        return FullArgSpec._make(inspect.getargspec(f) + ([], None))

    def get_init(cls):
        return cls.__init__.__func__

ArgSpec = collections.namedtuple('ArgSpec', 'args varargs varkw defaults')

def getargspec(f):
    spec = getfullargspec(f)
    return ArgSpec(spec.args, spec.varargs, spec.varkw, spec.defaults)

DEF = re.compile('\\s*def\\s*([_\\w][_\\w\\d]*)\\s*\\(')

class FunctionMaker(object):
    _compile_count = itertools.count()
    args = varargs = varkw = defaults = kwonlyargs = kwonlydefaults = ()

    def __init__(self, func=None, name=None, signature=None, defaults=None, doc=None, module=None, funcdict=None):
        self.shortsignature = signature
        if func:
            self.name = func.__name__
            if self.name == '<lambda>':
                self.name = '_lambda_'
            self.doc = func.__doc__
            self.module = func.__module__
            if inspect.isfunction(func):
                argspec = getfullargspec(func)
                self.annotations = getattr(func, '__annotations__', {})
                for a in ('args', 'varargs', 'varkw', 'defaults', 'kwonlyargs', 'kwonlydefaults'):
                    setattr(self, a, getattr(argspec, a))
                for (i, arg) in enumerate(self.args):
                    setattr(self, 'arg%d' % i, arg)
                if sys.version < '3':
                    self.shortsignature = self.signature = inspect.formatargspec(*argspec[:-2], formatvalue=lambda val: '')[1:-1]
                else:
                    allargs = list(self.args)
                    allshortargs = list(self.args)
                    if self.varargs:
                        allargs.append('*' + self.varargs)
                        allshortargs.append('*' + self.varargs)
                    elif self.kwonlyargs:
                        allargs.append('*')
                    for a in self.kwonlyargs:
                        allargs.append('%s=None' % a)
                        allshortargs.append('%s=%s' % (a, a))
                    if self.varkw:
                        allargs.append('**' + self.varkw)
                        allshortargs.append('**' + self.varkw)
                    self.signature = ', '.join(allargs)
                    self.shortsignature = ', '.join(allshortargs)
                self.dict = func.__dict__.copy()
        if name:
            self.name = name
        if signature is not None:
            self.signature = signature
        if defaults:
            self.defaults = defaults
        if doc:
            self.doc = doc
        if module:
            self.module = module
        if funcdict:
            self.dict = funcdict
        if not hasattr(self, 'signature'):
            raise TypeError('You are decorating a non function: %s' % func)

    def update(self, func, **kw):
        func.__name__ = self.name
        func.__doc__ = getattr(self, 'doc', None)
        func.__dict__ = getattr(self, 'dict', {})
        func.__defaults__ = self.defaults
        func.__kwdefaults__ = self.kwonlydefaults or None
        func.__annotations__ = getattr(self, 'annotations', None)
        try:
            frame = sys._getframe(3)
        except AttributeError:
            callermodule = '?'
        else:
            callermodule = frame.f_globals.get('__name__', '?')
        func.__module__ = getattr(self, 'module', callermodule)
        func.__dict__.update(kw)

    def make(self, src_templ, evaldict=None, addsource=False, **attrs):
        src = src_templ % vars(self)
        evaldict = evaldict or {}
        mo = DEF.match(src)
        if mo is None:
            raise SyntaxError("""not a valid function template
%s""" % src)
        name = mo.group(1)
        names = set([name] + [arg.strip(' *') for arg in self.shortsignature.split(',')])
        for n in names:
            if n in ('_func_', '_call_'):
                raise NameError("""%s is overridden in
%s""" % (n, src))
        if not src.endswith('\n'):
            src += '\n'
        filename = '<decorator-gen-%d>' % (next(self._compile_count),)
        try:
            code = compile(src, filename, 'single')
            exec(code, evaldict)
        except:
            print('Error in generated code:', file=sys.stderr)
            print(src, file=sys.stderr)
            raise
        func = evaldict[name]
        if addsource:
            attrs['__source__'] = src
        self.update(func, **attrs)
        return func

    @classmethod
    def create(cls, obj, body, evaldict, defaults=None, doc=None, module=None, addsource=True, **attrs):
        if isinstance(obj, str):
            (name, rest) = obj.strip().split('(', 1)
            signature = rest[:-1]
            func = None
        else:
            name = None
            signature = None
            func = obj
        self = cls(func, name, signature, defaults, doc, module)
        ibody = '\n'.join('    ' + line for line in body.splitlines())
        return self.make("""def %(name)s(%(signature)s):
""" + ibody, evaldict, addsource, **attrs)


def decorate(func, caller):
    evaldict = dict(_call_=caller, _func_=func)
    fun = FunctionMaker.create(func, 'return _call_(_func_, %(shortsignature)s)', evaldict, __wrapped__=func)
    if hasattr(func, '__qualname__'):
        fun.__qualname__ = func.__qualname__
    return fun


def decorator(caller, _func=None):
    if _func is not None:
        return decorate(_func, caller)
    if inspect.isclass(caller):
        name = caller.__name__.lower()
        doc = 'decorator(%s) converts functions/generators into factories of %s objects' % (caller.__name__, caller.__name__)
    elif inspect.isfunction(caller):
        if caller.__name__ == '<lambda>':
            name = '_lambda_'
        else:
            name = caller.__name__
        doc = caller.__doc__
    else:
        name = caller.__class__.__name__.lower()
        doc = caller.__call__.__doc__
    evaldict = dict(_call_=caller, _decorate_=decorate)
    return FunctionMaker.create('%s(func)' % name, 'return _decorate_(func, _call_)', evaldict, doc=doc, module=caller.__module__, __wrapped__=caller)

try:
    from contextlib import _GeneratorContextManager
except ImportError:
    from contextlib import GeneratorContextManager as _GeneratorContextManager

class ContextManager(_GeneratorContextManager):

    def __call__(self, func):
        return FunctionMaker.create(func, 'with _self_: return _func_(%(shortsignature)s)', dict(_self_=self, _func_=func), __wrapped__=func)

init = getfullargspec(_GeneratorContextManager.__init__)
n_args = len(init.args)
if n_args == 2 and not init.varargs:

    def __init__(self, g, *a, **k):
        return _GeneratorContextManager.__init__(self, g(*a, **k))

    ContextManager.__init__ = __init__
elif n_args == 2 and init.varargs:
    pass
elif n_args == 4:

    def __init__(self, g, *a, **k):
        return _GeneratorContextManager.__init__(self, g, a, k)

    ContextManager.__init__ = __init__
contextmanager = decorator(ContextManager)

def append(a, vancestors):
    add = True
    for (j, va) in enumerate(vancestors):
        if issubclass(va, a):
            add = False
            break
        if issubclass(a, va):
            vancestors[j] = a
            add = False
    if add:
        vancestors.append(a)


def dispatch_on(*dispatch_args):
    dispatch_str = '(%s,)' % ', '.join(dispatch_args)

    def check(arguments, wrong=operator.ne, msg=''):
        if wrong(len(arguments), len(dispatch_args)):
            raise TypeError('Expected %d arguments, got %d%s' % (len(dispatch_args), len(arguments), msg))

    def gen_func_dec(func):
        argset = set(getfullargspec(func).args)
        if not set(dispatch_args) <= argset:
            raise NameError('Unknown dispatch arguments %s' % dispatch_str)
        typemap = {}

        def vancestors(*types):
            check(types)
            ras = [[] for _ in range(len(dispatch_args))]
            for types_ in typemap:
                for (t, type_, ra) in zip(types, types_, ras):
                    if issubclass(t, type_) and type_ not in t.mro():
                        append(type_, ra)
            return [set(ra) for ra in ras]

        def ancestors(*types):
            check(types)
            lists = []
            for (t, vas) in zip(types, vancestors(*types)):
                n_vas = len(vas)
                if n_vas > 1:
                    raise RuntimeError('Ambiguous dispatch for %s: %s' % (t, vas))
                elif n_vas == 1:
                    (va,) = vas
                    mro = type('t', (t, va), {}).mro()[1:]
                else:
                    mro = t.mro()
                lists.append(mro[:-1])
            return lists

        def register(*types):
            check(types)

            def dec(f):
                check(getfullargspec(f).args, operator.lt, ' in ' + f.__name__)
                typemap[types] = f
                return f

            return dec

        def dispatch_info(*types):
            check(types)
            lst = []
            for anc in itertools.product(*ancestors(*types)):
                lst.append(tuple(a.__name__ for a in anc))
            return lst

        def _dispatch(dispatch_args, *args, **kw):
            types = tuple(type(arg) for arg in dispatch_args)
            try:
                f = typemap[types]
            except KeyError:
                pass
            else:
                return f(*args, **kw)
            combinations = itertools.product(*ancestors(*types))
            next(combinations)
            for types_ in combinations:
                f = typemap.get(types_)
                if f is not None:
                    return f(*args, **kw)
            return func(*args, **kw)

        return FunctionMaker.create(func, 'return _f_(%s, %%(shortsignature)s)' % dispatch_str, dict(_f_=_dispatch), register=register, default=func, typemap=typemap, vancestors=vancestors, ancestors=ancestors, dispatch_info=dispatch_info, __wrapped__=func)

    gen_func_dec.__name__ = 'dispatch_on' + dispatch_str
    return gen_func_dec

