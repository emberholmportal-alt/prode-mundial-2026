CHAMPION_POINTS = 10
RUNNER_UP_POINTS = 5
EXACT_POINTS = 3
RESULT_POINTS = 1


def _sign(x: int) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def calc_points(pred_home: int, pred_away: int, real_home: int, real_away: int) -> int:
    if pred_home == real_home and pred_away == real_away:
        return EXACT_POINTS
    if _sign(pred_home - pred_away) == _sign(real_home - real_away):
        return RESULT_POINTS
    return 0


def calc_final_points(
    pick_champion: str | None,
    pick_runner_up: str | None,
    real_champion: str | None,
    real_runner_up: str | None,
) -> int:
    if not (pick_champion and pick_runner_up and real_champion and real_runner_up):
        return 0

    pts = 0
    if pick_champion == real_champion:
        pts += CHAMPION_POINTS
    if pick_runner_up == real_runner_up:
        pts += RUNNER_UP_POINTS
    return pts
