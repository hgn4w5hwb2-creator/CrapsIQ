from enum import Enum


class GamePhase(str, Enum):
    COME_OUT = "come_out"
    POINT = "point"
    ENDED = "ended"


class GameResult(str, Enum):
    NATURAL = "natural"
    CRAPS = "craps"
    POINT_ESTABLISHED = "point_established"
    POINT_MADE = "point_made"
    SEVEN_OUT = "seven_out"
    NO_DECISION = "no_decision"


class CrapsEngine:
    def __init__(self, phase: GamePhase = GamePhase.COME_OUT, point: int | None = None, roll_history: list[int] | None = None) -> None:
        self.phase = phase
        self.point = point
        self.roll_history = list(roll_history or [])

    def get_game_state(self) -> dict:
        return {
            "phase": self.phase.value,
            "point": self.point,
            "total_rolls": len(self.roll_history),
            "roll_history": self.roll_history,
        }

    def process_roll(self, dice_values: list[int]) -> tuple[int, GameResult]:
        if self.phase == GamePhase.ENDED:
            raise ValueError("Game has already ended")
        if len(dice_values) != 2:
            raise ValueError("Exactly two dice values are required")
        if any(value < 1 or value > 6 for value in dice_values):
            raise ValueError("Dice values must be in the range [1, 6]")

        total = sum(dice_values)
        self.roll_history.append(total)

        if self.phase == GamePhase.COME_OUT:
            if total in (7, 11):
                return total, GameResult.NATURAL
            if total in (2, 3, 12):
                return total, GameResult.CRAPS
            self.phase = GamePhase.POINT
            self.point = total
            return total, GameResult.POINT_ESTABLISHED

        if total == self.point:
            self.phase = GamePhase.COME_OUT
            self.point = None
            return total, GameResult.POINT_MADE
        if total == 7:
            self.phase = GamePhase.COME_OUT
            self.point = None
            return total, GameResult.SEVEN_OUT
        return total, GameResult.NO_DECISION

    def end_game(self) -> dict:
        self.phase = GamePhase.ENDED
        self.point = None
        return self.get_game_state()
