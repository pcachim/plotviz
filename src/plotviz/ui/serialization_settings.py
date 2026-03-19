"""
Copyright (c) 2026 Paulo Cachim
ui/serialization_settings.py  –  plotviz
Combines collect and apply mixins for widget state serialization.
"""
from ui.serialization_collect import SerializationCollectMixin
from ui.serialization_apply import SerializationApplyMixin


class SerializationSettingsMixin(SerializationCollectMixin, SerializationApplyMixin):
    pass
