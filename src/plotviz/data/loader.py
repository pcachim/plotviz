"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.
"""
"""
data/loader.py - Data loading from multiple formats
"""

import json
from pathlib import Path
from typing import Dict
import numpy as np
import pandas as pd


class DataLoader:
    """Load data from various file formats"""

    @staticmethod
    def load_file(filepath: str) -> Dict[str, np.ndarray]:
        """Load data from Excel, CSV, TXT, or JSON.
        Numeric columns → float64 ndarray.
        String/categorical columns → object ndarray of strings.
        """
        ext = Path(filepath).suffix.lower()

        try:
            if ext in ['.xlsx', '.xls']:
                df = pd.read_excel(filepath)
            elif ext == '.csv':
                df = pd.read_csv(filepath)
            elif ext == '.json':
                with open(filepath) as f:
                    data = json.load(f)
                df = pd.DataFrame(data) if isinstance(data, dict) else pd.DataFrame(data)
            elif ext == '.txt':
                df = pd.read_csv(filepath, sep=r'\s+')
            else:
                raise ValueError(f"Unsupported format: {ext}")

            data_dict = {}
            for col in df.columns:
                series = df[col]
                # Try numeric first — only treat as numeric if ALL non-null values parse
                numeric = pd.to_numeric(series, errors='coerce')
                non_null = series.notna().sum()
                if non_null > 0 and numeric.notna().sum() == non_null:
                    # Every non-null value parsed as numeric → float column
                    data_dict[str(col)] = numeric.to_numpy(dtype=float, na_value=np.nan)
                else:
                    # Any string values → categorical/string column
                    data_dict[str(col)] = series.fillna('').astype(str).to_numpy()

            return data_dict

        except Exception as e:
            raise Exception(f"Error loading file: {str(e)}")
