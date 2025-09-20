# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT

from typing import Literal

from rank_comparia.ranker import Match, Ranker


def reciprocal_function(score_difference: float):
    """
    Computes the expected score for a player based on the Elo rating system.

    Given the score difference between two players, this function returns the
    expected probability of a win for the player with the higher rating.

    Args:
        score_difference (float): The rating difference between two players (A - B),
            where a positive value indicates player A is stronger.

    Returns:
        float: The expected score (win probability) for the player with the higher rating.
    """
    return 1 / (1 + 10 ** (-score_difference / 400))


class ELORanker(Ranker):
    """
    Elo Ranker.
    """

    def __init__(self, scale: int = 400, default_score: float = 1000.0, bootstrap_samples: int = 100, K: int = 40):
        """
        Constructor.

        Args:
            scale (int): Scale parameter.
            default_score (float): Base score used.
            bootstrap_samples (int): Number of bootstrap samples.
            K (int): Elo K-factor.
        """
        super().__init__(scale, default_score, bootstrap_samples)
        self.K = K
        # initialize scores
        self.players = {}
        self.played_matches = {}

    def add_player(self, player_name: str) -> None:
        """
        Add a player to the Elo ranker.

        Args:
            player_name (str): Name of the player.
        """
        self.players |= {player_name: self.default_score}
        self.played_matches |= {player_name: 0}

    def add_players(self, player_names: list[str]) -> None:
        """
        Add multiple players to the Elo ranker.

        Args:
            player_names (list[str]): Name of the players.
        """
        for player_name in player_names:
            self.add_player(player_name)

    def get_scores(self) -> dict[str, float]:
        """
        Return computed scores.

        Returns:
            dict[str, float]: Dictionary mapping model names to float scores.
        """
        return {player: score for player, score in sorted(self.players.items(), key=lambda x: -x[1])}

    def player_score(self, name: str) -> float:
        """
        Get score for the given players.

        Args:
            name (str): Player name.

        Returns:
            float: Elo score.
        """
        return self.players[name]

    def player_number_of_matches(self, name: str) -> int:
        """
        Return number of matches played by a given player.

        Args:
            name (str): Player name.

        Returns:
            int: Number of played matches.
        """
        return self.played_matches[name]

    def add_match(self, player_a: str, player_b: str, score: Literal[0, 1, 2], K: float = 40.0) -> None:
        """
        Update Elo scores based on a match result.

        Args:
            player_a (str): Player A.
            player_b (str): Player B.
            score (Literal[0, 1, 2]): Match score. 0 -> b wins, 2 -> a wins, 1 -> draw.
            K (float): Elo K-factor.
        """
        W = score / 2.0
        D = min(max(self.player_score(player_a) - self.player_score(player_b), -400), 400)
        pd = reciprocal_function(D)
        self.players[player_a] += self.K * (W - pd)
        self.players[player_b] += self.K * (pd - W)
        self.played_matches[player_a] += 1
        self.played_matches[player_b] += 1

    def _add_match(self, model_a_name: str, model_b_name: str, score: Literal[0, 1, 2]) -> None:
        """
        Update Elo scores based on a match result.

        Args:
            model_a_name (str): Player A.
            model_b_name (str): Player B.
            score (Literal[0, 1, 2]): Match score. 0 -> b wins, 2 -> a wins, 1 -> draw.
        """
        # add players if they do not exist
        if model_a_name not in self.players.keys():
            self.add_player(model_a_name)
        if model_b_name not in self.players.keys():
            self.add_player(model_b_name)

        min_number_of_parties = min(
            self.player_number_of_matches(model_a_name),
            self.player_number_of_matches(model_b_name),
        )
        max_elo = max(self.player_score(model_a_name), self.player_score(model_b_name))
        if max_elo > 2400:
            K = self.K / 4
        elif min_number_of_parties > 30:
            K = self.K / 2
        else:
            K = self.K
        self.add_match(model_a_name, model_b_name, score=score, K=K)

    def compute_scores(self, matches: list[Match]) -> dict[str, float]:
        """
        Compute scores starting at 0 from a list of matches.

        Args:
            matches (list[Match]): List of matches.

        Returns:
            dict[str, float]: Dictionary mapping model names to float scores.
        """
        # reset players and scores based on matches
        self.players = {}
        self.played_matches = {}
        players = list({player for m in matches for player in (m.model_a, m.model_b)})
        self.add_players(players)

        # compute scores
        return self.update_scores(matches)

    def update_scores(self, matches: list[Match]) -> dict[str, float]:
        """
        Update scores from a list of matches.

        Args:
            matches (list[Match]): List of matches.

        Returns:
            dict[str, float]: Dictionary mapping model names to float scores.
        """
        for match in matches:
            self._add_match(match.model_a, match.model_b, score=match.score.value)
        return self.get_scores()
