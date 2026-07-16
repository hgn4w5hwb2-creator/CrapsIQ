from enum import Enum


class GamePhase(str, Enum):
    COME_OUT = "come_out"
    POINT = "point"


class RollResult(str, Enum):
    NATURAL = "natural"
    CRAPS = "craps"
    POINT_ESTABLISHED = "point_established"
    POINT_MADE = "point_made"
    SEVEN_OUT = "seven_out"
    ROLL_AGAIN = "roll_again"


class CrapsEngine:
    def __init__(self, phase: str = GamePhase.COME_OUT.value, point: int | None = None, roll_history: list | None = None):
        self.phase = GamePhase(phase)
        self.point = point
        self.roll_history = list(roll_history or [])

    def process_roll(self, die1: int, die2: int) -> dict:
        total = die1 + die2
        roll_number = len(self.roll_history) + 1
        self.roll_history.append(
            {
                "roll_number": roll_number,
                "die1": die1,
                "die2": die2,
                "total": total,
            }
        )

        if self.phase == GamePhase.COME_OUT:
            if total in (7, 11):
                result = RollResult.NATURAL
            elif total in (2, 3, 12):
                result = RollResult.CRAPS
            else:
                self.phase = GamePhase.POINT
                self.point = total
                result = RollResult.POINT_ESTABLISHED
        elif total == 7:
            self.phase = GamePhase.COME_OUT
            self.point = None
            result = RollResult.SEVEN_OUT
        elif total == self.point:
            self.phase = GamePhase.COME_OUT
            self.point = None
            result = RollResult.POINT_MADE
        else:
            result = RollResult.ROLL_AGAIN

        return {
            "result": result.value,
            "phase": self.phase.value,
            "point": self.point,
            "roll_count": len(self.roll_history),
            "roll_history": self.roll_history,
        }
