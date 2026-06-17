"""pytest entry point — ensures the bootstrap (sys.path + PyQt6 stubs) runs
before any test module is imported. unittest users get the same setup because
each test module imports ``_bootstrap`` directly.
"""
import _bootstrap  # noqa: F401
