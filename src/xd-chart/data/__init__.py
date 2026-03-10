"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.
"""
"""
data package - Data loading and scientific computing
"""

from .loader import DataLoader
from .scientific import CurveFitter

__all__ = ['DataLoader', 'CurveFitter']
