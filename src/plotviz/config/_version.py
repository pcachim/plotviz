"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.

config/_version.py — single source of truth for the application version.

To release a new version, change __version__ here ONLY.
pyproject.toml reads this file via hatchling's path-based versioning,
so the package metadata stays in sync automatically.
"""

__version__ = "2.5.0"
