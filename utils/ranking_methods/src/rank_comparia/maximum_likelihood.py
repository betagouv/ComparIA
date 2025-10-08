# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT

"""Alternative maximum likelihood ranker."""

import math

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

from rank_comparia.ranker import Match, Ranker


class MaximumLikelihoodRanker(Ranker):
    """
    Maximum Likelihood Ranker.
    """

    BASE = 10

    def __init__(
        self, scale: int = 400, default_score: float = 1000.0, bootstrap_samples: int = 100, max_iter: int = 300
    ):
        """
        Constructor.

        Args:
            scale (int): Scale parameter.
            default_score (float): Base score used.
            bootstrap_samples (int): Number of bootstrap samples.
            max_iter (int): Max number of iterations for the LBFGS optimizer.
        """
        super().__init__(scale, default_score, bootstrap_samples)
        self.max_iter = max_iter
        self.scores = {}

    @staticmethod
    def aggregate_matches(matches: list[Match]) -> pl.DataFrame:
        """
        Aggregate a list of matches in a polars DataFrame.

        Args:
            matches (list[Match]): List of matches.

        Returns:
            pl.DataFrame: DataFrame with the number of wins on each side for all pairwise combinations of models.
        """
        # store match list in dataframe
        model_a, model_b, score = zip(*((match.model_a, match.model_b, match.score.value) for match in matches))
        df = (
            pl.DataFrame({"model_a_name": model_a, "model_b_name": model_b, "score": score})
            .with_columns(
                a_wins=(pl.col("score") / 2).cast(int),
                b_wins=pl.max_horizontal(0, 1 - pl.col("score")),
            )
            .with_columns(draws=1 - pl.col("a_wins") - pl.col("b_wins"))
            .drop("score")
            .filter(pl.col("model_a_name") != pl.col("model_b_name"))
        )

        # aggregate match results
        counts = df.group_by(["model_a_name", "model_b_name"]).sum()
        reversed_counts = counts.with_columns(
            model_a_name="model_b_name",
            model_b_name="model_a_name",
            a_wins="b_wins",
            b_wins="a_wins",
        )

        all_counts = pl.concat([counts, reversed_counts]).group_by(["model_a_name", "model_b_name"]).sum()
        return all_counts

    def compute_scores(self, matches: list[Match]) -> dict[str, float]:
        """
        Compute scores from a list of matches.

        Args:
            matches (list[Match]): List of matches.

        Returns:
            dict[str, float]: Dictionary mapping model names to float scores.
        """
        all_counts = self.aggregate_matches(matches=matches)
        # models list
        models = all_counts["model_a_name"].unique().to_list()
        # set up matrices to train model
        non_mirror_matches = all_counts.filter(pl.col("model_a_name") != pl.col("model_b_name"))
        X = np.zeros([len(non_mirror_matches) * 2, len(models)])
        Y = np.zeros(len(non_mirror_matches) * 2)
        sample_weights = []
        model_dict = {model_name: index for index, model_name in enumerate(models)}
        base_log = math.log(self.BASE)

        for current_index, (match_data) in enumerate(non_mirror_matches.iter_rows(named=True)):
            model_a_idx, model_b_idx = model_dict[match_data["model_a_name"]], model_dict[match_data["model_b_name"]]
            a_wins, b_wins, draws = match_data["a_wins"], match_data["b_wins"], match_data["draws"]

            X[2 * current_index, model_a_idx] = base_log
            X[2 * current_index, model_b_idx] = -base_log
            Y[2 * current_index] = 1.0
            sample_weights.append(a_wins * 2 + draws)

            X[2 * current_index + 1, model_a_idx] = base_log
            X[2 * current_index + 1, model_b_idx] = -base_log
            Y[2 * current_index + 1] = 0.0
            sample_weights.append(b_wins * 2 + draws)

        # fit logistic regression
        lr = LogisticRegression(fit_intercept=False, penalty=None, tol=1e-6, max_iter=self.max_iter)  # type: ignore
        lr.fit(X, Y, sample_weight=sample_weights)
        scores = self.scale * lr.coef_[0] + self.default_score

        self.scores = {m: s for m, s in zip(models, scores)}
        return self.get_scores()

    def get_scores(self) -> dict[str, float]:
        """
        Return computed scores.

        Returns:
            dict[str, float]: Dictionary mapping model names to float scores.
        """
        return {model: score for model, score in sorted(self.scores.items(), key=lambda x: -x[1])}
