"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

core/mpl_compat.py  –  plotviz

Keyword-argument shims for matplotlib APIs that were renamed or deprecated
between the minimum supported version (3.7) and current releases, so the
app renders without DeprecationWarnings on new versions and still works on old.

No Qt, no ui/ imports.
"""
from __future__ import annotations

import matplotlib

_MPL = tuple(matplotlib.__version_info__[:2])


def box_kwargs(labels, vertical: bool = True) -> dict:
    """kwargs for ``Axes.boxplot``: tick labels and orientation."""
    kw = {('tick_labels' if _MPL >= (3, 9) else 'labels'): labels}
    kw.update(_orientation(vertical))
    return kw


def violin_kwargs(vertical: bool = True) -> dict:
    """kwargs for ``Axes.violinplot``: orientation."""
    return _orientation(vertical)


def _orientation(vertical: bool) -> dict:
    if _MPL >= (3, 10):
        return {'orientation': 'vertical' if vertical else 'horizontal'}
    return {'vert': bool(vertical)}
