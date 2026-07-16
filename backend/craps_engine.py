from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime


class GamePhase(str, Enum):
    """Craps game phases."""
    COME_OUT = "come_out"  # First roll of a round
    POINT = "point"       # Point is established


class GameResult(str, Enum):
    """Possible game outcomes."""
    NATURAL = "natural"      # 7 or 11 on come-out (pass wins)
    CRAPS = "craps"          # 2, 3, or 12 on come-out (pass loses)
    POINT_MADE = "point_made"     # Roll equals point (pass wins)
    SEVEN_OUT = "seven_out"       # 7 rolled after point (pass loses)
    CONTINUE = "continue"        # Game continues


class CrapsEngine:
    """Core craps game logic and probability calculator."""

    def __init__(self):
        self.point = None
        self.phase = GamePhase.COME_OUT
        self.roll_history = []
        self.game_start = datetime.now()

    def calculate_roll_probabilities(self) -> Dict[int, float]:
        """Calculate probability of rolling each sum (2-12).
        
        Returns:
            dict with roll values (2-12) as keys and probabilities as values
        """
        ways = {
            2: 1,   # 1+1
            3: 2,   # 1+2, 2+1
            4: 3,   # 1+3, 2+2, 3+1
            5: 4,   # 1+4, 2+3, 3+2, 4+1
            6: 5,   # 1+5, 2+4, 3+3, 4+2, 5+1
            7: 6,   # 1+6, 2+5, 3+4, 4+3, 5+2, 6+1
            8: 5,   # 2+6, 3+5, 4+4, 5+3, 6+2
            9: 4,   # 3+6, 4+5, 5+4, 6+3
            10: 3,  # 4+6, 5+5, 6+4
            11: 2,  # 5+6, 6+5
            12: 1   # 6+6
        }

        total_ways = 36
        probabilities = {}

        for roll, count in ways.items():
            probabilities[roll] = round(
                (count / total_ways) * 100,
                2
            )

        return probabilities

    def calculate_odds_for_point(self) -> Dict[str, float]:
        """Calculate odds for point and against (don't pass).
        
        Returns:
            dict with "for" (pass) and "against" (don't pass) probabilities
        """
        if not self.point:
            return {"for": 0, "against": 0}

        ways_to_make_point = {
            4: 3,   # 1+3, 2+2, 3+1
            5: 4,   # 1+4, 2+3, 3+2, 4+1
            6: 5,   # 1+5, 2+4, 3+3, 4+2, 5+1
            8: 5,   # 2+6, 3+5, 4+4, 5+3, 6+2
            9: 4,   # 3+6, 4+5, 5+4, 6+3
            10: 3   # 4+6, 5+5, 6+4
        }

        ways_to_seven = 6
        ways_to_point = ways_to_make_point.get(self.point, 0)
        total_ways = ways_to_seven + ways_to_point

        if total_ways == 0:
            return {"for": 0, "against": 0}

        return {
            "for": round((ways_to_point / total_ways) * 100, 2),
            "against": round((ways_to_seven / total_ways) * 100, 2)
        }

    def process_roll(self, roll_value: int) -> GameResult:
        """Process a dice roll and update game state.
        
        Args:
            roll_value: Sum of two dice (2-12)
            
        Returns:
            GameResult enum indicating outcome
        """
        self.roll_history.append(roll_value)

        if self.phase == GamePhase.COME_OUT:
            return self._handle_come_out_roll(roll_value)
        else:
            return self._handle_point_roll(roll_value)

    def _handle_come_out_roll(self, roll: int) -> GameResult:
        """Handle roll during come-out phase.
        
        Args:
            roll: Dice roll value
            
        Returns:
            GameResult
        """
        if roll in (7, 11):
            return GameResult.NATURAL
        elif roll in (2, 3, 12):
            return GameResult.CRAPS
        else:
            # Establish point
            self.point = roll
            self.phase = GamePhase.POINT
            return GameResult.CONTINUE

    def _handle_point_roll(self, roll: int) -> GameResult:
        """Handle roll during point phase.
        
        Args:
            roll: Dice roll value
            
        Returns:
            GameResult
        """
        if roll == self.point:
            # Point made, pass line wins
            self._reset_point()
            return GameResult.POINT_MADE
        elif roll == 7:
            # Seven out, pass line loses
            self._reset_point()
            return GameResult.SEVEN_OUT
        else:
            # Game continues
            return GameResult.CONTINUE

    def _reset_point(self):
        """Reset point and return to come-out phase."""
        self.point = None
        self.phase = GamePhase.COME_OUT

    def get_game_state(self) -> Dict:
        """Get current game state.
        
        Returns:
            dict with current game information
        """
        return {
            "phase": self.phase.value,
            "point": self.point,
            "roll_history": self.roll_history,
            "roll_count": len(self.roll_history),
            "odds": self.calculate_odds_for_point() if self.point else None,
            "all_probabilities": self.calculate_roll_probabilities(),
            "game_duration_seconds": (
                datetime.now() - self.game_start
            ).total_seconds()
        }

    def get_ai_recommendation(self) -> Dict[str, str]:
        """Get AI coach recommendation based on game state.
        
        Returns:
            dict with strategy recommendations
        """
        recommendation = {}

        if self.phase == GamePhase.COME_OUT:
            recommendation["phase"] = (
                "Come-out roll. Pass Line + Odds is optimal "
                "(1.4% house edge with odds)."
            )
        else:
            odds = self.calculate_odds_for_point()
            recommendation["phase"] = f"Point is {self.point}."
            recommendation["odds"] = (
                f"Pass Line wins {odds['for']}% of the time. "
                f"Consider taking odds for better payout."
            )

        recommendation["bankroll"] = (
            "Track your bankroll. Don't increase bet sizes "
            "until you're up."
        )
        recommendation["avoid"] = (
            "Avoid proposition bets (Any Craps, Hardways, etc.). "
            "House edge: 2-16%."
        )

        return recommendation
