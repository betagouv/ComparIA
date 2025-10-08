# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT

from pathlib import Path

import polars as pl

from rank_comparia.utils import save_data


def test_save_data_creates_csv(tmp_path: Path):
    df = pl.DataFrame(
        {
            "col1": [1, 2, 3],
            "col2": ["a", "b", "c"],
        }
    )
    title = "test"
    save_data(df, title, tmp_path)

    file_path = tmp_path / f"{title}.csv"
    assert file_path.exists()

    loaded_df = pl.read_csv(file_path, separator=";")
    assert loaded_df.equals(df)
