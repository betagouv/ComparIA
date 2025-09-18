# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT

from rank_comparia.elo import ELORanker
from rank_comparia.ranker import Match, MatchScore


PLAYERS = ["bob", "alice", "eve"]
MATCHES = [
    Match(model_a="alice", model_b="bob", score=MatchScore.A),
    Match(model_a="alice", model_b="bob", score=MatchScore.A),
    Match(model_a="alice", model_b="bob", score=MatchScore.Draw),
    Match(model_a="eve", model_b="bob", score=MatchScore.B),
    Match(model_a="eve", model_b="bob", score=MatchScore.B),
]


NEW_MATCHES = [
    Match(model_a="alice", model_b="bob", score=MatchScore.B),
    Match(model_a="alice", model_b="bob", score=MatchScore.B),
    Match(model_a="alice", model_b="bob", score=MatchScore.B),
    Match(model_a="alice", model_b="bob", score=MatchScore.B),
    Match(model_a="alice", model_b="bob", score=MatchScore.B),
]


def test_elo():
    elo_ranking = ELORanker()
    elo_ranking.add_players(PLAYERS)
    scores = elo_ranking.compute_scores(MATCHES)
    assert scores["alice"] > scores["bob"]
    assert scores["bob"] > scores["eve"]
    assert elo_ranking.player_number_of_matches("eve") == 2
    new_scores = elo_ranking.update_scores(NEW_MATCHES)
    assert new_scores["alice"] < new_scores["bob"]
    assert elo_ranking.player_score("alice") == new_scores["alice"]


def test_elo_bootstrap():
    elo_ranking = ELORanker()
    elo_ranking.add_players(PLAYERS)
    df_scores = elo_ranking.compute_bootstrap_scores(MATCHES)
    median_scores = {
        line["model_name"]: line["median"] for line in df_scores.select(["model_name", "median"]).to_dicts()
    }
    assert median_scores["alice"] >= median_scores["bob"]
    assert median_scores["bob"] >= median_scores["eve"]


def test_player_not_known_elo():
    elo_ranking = ELORanker()
    elo_ranking.add_players(PLAYERS)
    elo_ranking.compute_scores(MATCHES)
    elo_ranking.update_scores([Match(model_a="chief", model_b="daniel", score=MatchScore.Draw)])


def test_players_with_high_score():
    elo_ranking = ELORanker(K=1000)
    elo_ranking.add_players(PLAYERS)
    scores = elo_ranking.compute_scores([MATCHES[0]] * 20)
    assert scores["alice"] > 2400


def test_players_with_many_parties():
    elo_ranking = ELORanker(K=1)
    elo_ranking.add_players(PLAYERS)
    scores = elo_ranking.compute_scores([MATCHES[0]] * 50)
    assert scores["alice"] > 1000
