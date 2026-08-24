"""
Deferred module loading for the URLconf import chain.

`peptide/urls.py` pulls in every sub-app's `views.py` on the very first
request Django resolves (probe, health check, or real traffic — whichever
comes first), since Python imports each `include()`d urls.py, and thus its
views module, in one shot. Several of those views modules pull in pandas/
numpy/scipy transitively through `.services` at module import time, which
adds real latency to that first request. Wrapping the heavy submodule in
LazyModule defers the actual `import` until a view function first touches
it, without changing any call site (`data_processor.load_file(...)` etc.
keeps working unchanged).
"""
import importlib


class LazyModule:
    def __init__(self, name):
        self._name = name
        self._mod = None

    def _load(self):
        if self._mod is None:
            self._mod = importlib.import_module(self._name)
        return self._mod

    def __getattr__(self, attr):
        return getattr(self._load(), attr)
