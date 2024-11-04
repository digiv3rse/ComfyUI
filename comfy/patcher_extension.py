from __future__ import annotations
from typing import Callable

class CallbacksMP:
    ON_CLONE = "on_clone"
    ON_LOAD = "on_load_after"
    ON_CLEANUP = "on_cleanup"
    ON_PRE_RUN = "on_pre_run"
    ON_PREPARE_STATE = "on_prepare_state"
    ON_APPLY_HOOKS = "on_apply_hooks"
    ON_REGISTER_ALL_HOOK_PATCHES = "on_register_all_hook_patches"
    ON_INJECT_MODEL = "on_inject_model"
    ON_EJECT_MODEL = "on_eject_model"

    @classmethod
    def init_callbacks(cls):
        return {
            cls.ON_CLONE: {None: []},
            cls.ON_LOAD: {None: []},
            cls.ON_CLEANUP: {None: []},
            cls.ON_PRE_RUN: {None: []},
            cls.ON_PREPARE_STATE: {None: []},
            cls.ON_APPLY_HOOKS: {None: []},
            cls.ON_REGISTER_ALL_HOOK_PATCHES: {None: []},
            cls.ON_INJECT_MODEL: {None: []},
            cls.ON_EJECT_MODEL: {None: []},
        }

def add_callback(call_type: str, callback: Callable, transformer_options: dict, is_model_options=False):
    add_callback_with_key(call_type, None, callback, transformer_options, is_model_options)

def add_callback_with_key(call_type: str, key: str, callback: Callable, transformer_options: dict, is_model_options=False):
    if is_model_options:
        transformer_options = transformer_options.get("transformer_options", {})
    callbacks: dict[str, dict[str, list]] = transformer_options.get("callbacks", {})
    if call_type not in callbacks:
        raise Exception(f"Callback '{call_type}' is not recognized.")
    c = callbacks[call_type].setdefault(key, [])
    c.append(callback)

def get_all_callbacks(call_type: str, transformer_options: dict, is_model_options=False):
    if is_model_options:
        transformer_options = transformer_options.get("transformer_options", {})
    c_list = []
    callbacks: dict[str, list] = transformer_options.get("callbacks", {})
    for c in callbacks.get(call_type, {}).values():
        c_list.extend(c)
    return c_list

class WrappersMP:
    OUTER_SAMPLE = "outer_sample"
    SAMPLER_SAMPLE = "sampler_sample"
    CALC_COND_BATCH = "calc_cond_batch"
    APPLY_MODEL = "apply_model"
    DIFFUSION_MODEL = "diffusion_model"

    @classmethod
    def init_wrappers(cls):
        return {
            cls.OUTER_SAMPLE: {None: []},
            cls.SAMPLER_SAMPLE: {None: []},
            cls.CALC_COND_BATCH: {None: []},
            cls.APPLY_MODEL: {None: []},
            cls.DIFFUSION_MODEL: {None: []},
        }

def add_wrapper(wrapper_type: str, wrapper: Callable, transformer_options: dict, is_model_options=False):
    add_wrapper_with_key(wrapper_type, None, wrapper, transformer_options, is_model_options)

def add_wrapper_with_key(wrapper_type: str, key: str, wrapper: Callable, transformer_options: dict, is_model_options=False):
    if is_model_options:
        transformer_options = transformer_options.get("transformer_options", {})
    wrappers: dict[str, dict[str, list]] = transformer_options.get("wrappers", {})
    if wrapper_type not in wrappers:
        raise Exception(f"Wrapper '{wrapper_type}' is not recognized.")
    w = wrappers[wrapper_type].setdefault(key, [])
    w.append(wrapper)

def get_all_wrappers(wrapper_type: str, transformer_options: dict, is_model_options=False):
    if is_model_options:
        transformer_options = transformer_options.get("transformer_options", {})
    w_list = []
    wrappers: dict[str, list] = transformer_options.get("wrappers", {})
    for w in wrappers.get(wrapper_type, {}).values():
        w_list.extend(w)
    return w_list

class WrapperExecutor:
    """Handles call stack of wrappers around a function in an ordered manner."""
    def __init__(self, original: Callable, class_obj: object, wrappers: list[Callable], idx: int):
        # NOTE: class_obj exists so that wrappers surrounding a class method can access
        #       the class instance at runtime via executor.class_obj
        self.original = original
        self.class_obj = class_obj
        self.wrappers = wrappers.copy()
        self.idx = idx
        self.is_last = idx == len(wrappers)
    
    def __call__(self, *args, **kwargs):
        """Calls the next wrapper or original function, whichever is appropriate."""
        new_executor = self._create_next_executor()
        return new_executor.execute(*args, **kwargs)
    
    def execute(self, *args, **kwargs):
        """Used to initiate executor internally - DO NOT use this if you received executor in wrapper."""
        args = list(args)
        kwargs = dict(kwargs)
        if self.is_last:
            return self.original(*args, **kwargs)
        return self.wrappers[self.idx](self, *args, **kwargs)

    def _create_next_executor(self) -> 'WrapperExecutor':
        new_idx = self.idx + 1
        if new_idx > len(self.wrappers):
            raise Exception(f"Wrapper idx exceeded available wrappers; something went very wrong.")
        if self.class_obj is None:
            return WrapperExecutor.new_executor(self.original, self.wrappers, new_idx)
        return WrapperExecutor.new_class_executor(self.original, self.class_obj, self.wrappers, new_idx)

    @classmethod
    def new_executor(cls, original: Callable, wrappers: list[Callable], idx=0):
        return cls(original, class_obj=None, wrappers=wrappers, idx=idx)
    
    @classmethod
    def new_class_executor(cls, original: Callable, class_obj: object, wrappers: list[Callable], idx=0):
        return cls(original, class_obj, wrappers, idx=idx)

class PatcherInjection:
    def __init__(self, inject: Callable, eject: Callable):
        self.inject = inject
        self.eject = eject

def copy_nested_dicts(input_dict: dict):
    new_dict = input_dict.copy()
    for key, value in input_dict.items():
        if isinstance(value, dict):
            new_dict[key] = copy_nested_dicts(value)
        elif isinstance(value, list):
            new_dict[key] = value.copy()
    return new_dict

def merge_nested_dicts(dict1: dict, dict2: dict):
    merged_dict = copy_nested_dicts(dict1)
    for key, value in dict2.items():
        if isinstance(value, dict):
            curr_value = merged_dict.setdefault(key, {})
            merged_dict[key] = merge_nested_dicts(value, curr_value)
        elif isinstance(value, list):
            merged_dict.setdefault(key, []).extend(value)
        else:
            merged_dict[key] = value
    return merged_dict
