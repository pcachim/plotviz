"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.
"""
"""
styling/presets.py - Publication presets and style configuration
"""

import matplotlib.pyplot as plt


class ChartPresets:
    """Publication-quality style presets for major journals"""

    PRESETS = {
        'IEEE': {
            'figsize': (3.5, 2.625),
            'dpi': 300,
            'font.size': 8,
            'font.family': 'serif',
        },
        'Nature': {
            'figsize': (8.0, 6.0),
            'dpi': 300,
            'font.size': 10,
            'font.family': 'sans-serif',
        },
        'Science': {
            'figsize': (7.5, 5.5),
            'dpi': 300,
            'font.size': 9,
        },
        'PNAS': {
            'figsize': (6.0, 4.5),
            'dpi': 300,
            'font.size': 9,
        },
        'ACS': {
            'figsize': (3.27, 2.45),
            'dpi': 300,
            'font.size': 8,
        },
        'Thesis': {
            'figsize': (6.0, 4.5),
            'dpi': 300,
            'font.size': 11,
            'font.family': 'serif',
        },
        'Presentation': {
            'figsize': (10, 7),
            'dpi': 150,
            'font.size': 14,
        },
    }

    @staticmethod
    def apply(preset_name: str):
        """Apply a preset"""
        if preset_name not in ChartPresets.PRESETS:
            return False

        preset = ChartPresets.PRESETS[preset_name]
        for key, value in preset.items():
            try:
                plt.rcParams[key] = value
            except Exception as e:
                print(f"Warning: Could not set {key}: {e}")

        return True

    @staticmethod
    def get_names():
        """Get list of preset names"""
        return list(ChartPresets.PRESETS.keys())
