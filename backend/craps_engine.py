from enum import Enum
from typing import Dict, List

class GameResult(str, Enum):
    COME_OUT_ROLL = "come_out_roll"
    POINT_ESTABLISHED = "point_established"
    POINT_MADE = "point_made"
    CRAPS = "craps"
    NATURAL = "natural"
    SEVEN_OUT = "seven_out"

class GamePhase(str, Enum):
    COME_OUT = "come_out"
    POINT = "point"
    ENDED = "ended"

class CrapsEngine:
    def __init__(self):
        self.phase = GamePhase.COME_OUT
        self.point = None
        self.roll_history = []
        self.come_out_rolls = 0
        
    def get_game_state(self) -> Dict:
        return {
            "phase": self.phase.value,
            "point": self.point,
            "roll_count": len(self.roll_history),
            "roll_history": self.roll_history
        }
    
    def process_roll(self, total: int) -> GameResult:
        self.roll_history.append(total)
        
        if self.phase == GamePhase.COME_OUT:
            return self._process_come_out_roll(total)
        else:
            return self._process_point_roll(total)
    
    def _process_come_out_roll(self, total: int) -> GameResult:
        if total == 7 or total == 11:
            return GameResult.NATURAL
        elif total == 2 or total == 3 or total == 12:
            return GameResult.CRAPS
        else:
            self.point = total
            self.phase = GamePhase.POINT
            return GameResult.POINT_ESTABLISHED
    
    def _process_point_roll(self, total: int) -> GameResult:
        if total == self.point:
            self.phase = GamePhase.COME_OUT
            self.point = None
            return GameResult.POINT_MADE
        elif total == 7:
            self.phase = GamePhase.COME_OUT
            self.point = None
            return GameResult.SEVEN_OUT
        return GameResult.CRAPS
    
    def calculate_roll_probabilities(self) -> Dict:
        probabilities = {}
        for i in range(2, 13):
            if i == 2 or i == 12:
                probabilities[i] = 1/36
            elif i == 3 or i == 11:
                probabilities[i] = 2/36
            elif i == 4 or i == 10:
                probabilities[i] = 3/36
            elif i == 5 or i == 9:
                probabilities[i] = 4/36
            elif i == 6 or i == 8:
                probabilities[i] = 5/36
            else:  # 7
                probabilities[i] = 6/36
        return probabilities
    
    def calculate_odds_for_point(self) -> Dict:
        if not self.point:
            return {}
        
        point = self.point
        prob_make_point = {4: 3/36, 5: 4/36, 6: 5/36, 8: 5/36, 9: 4/36, 10: 3/36}
        prob_seven = 6/36
        
        return {
            "point": point,
            "prob_make_point": prob_make_point.get(point, 0),
            "prob_seven": prob_seven,
            "odds": (prob_make_point.get(point, 0) / prob_seven) if prob_seven > 0 else 0
        }
    
    def get_ai_recommendation(self) -> str:
        if self.phase == GamePhase.COME_OUT:
            return "Come out roll - all bets are open"
        elif self.phase == GamePhase.POINT:
            odds = self.calculate_odds_for_point()
            if odds.get("odds", 0) > 1:
                return f"Point {self.point} established - odds favor making the point"
            else:
                return f"Point {self.point} established - odds favor seven out"
        return "Game ended"
