from dataclasses import dataclass
from typing import Optional
import json
import os


@dataclass
class DiceRegion:
    """Defines the region where dice are detected on the table."""
    x: int
    y: int
    width: int
    height: int


@dataclass
class TableCalibration:
    """Stores calibration data for a specific craps table."""
    table_id: str
    dice_region: DiceRegion
    camera_angle: float  # Degrees
    lighting_level: float  # 0-1
    calibrated_at: str


class CalibrationManager:
    """Manages table calibration data."""

    def __init__(self, calibration_file: str = "calibration.json"):
        self.calibration_file = calibration_file
        self.calibrations = {}
        self._load_calibrations()

    def _load_calibrations(self) -> None:
        """Load calibrations from disk."""
        if os.path.exists(self.calibration_file):
            try:
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)
                    for table_id, cal in data.items():
                        dice_region = DiceRegion(
                            x=cal['dice_region']['x'],
                            y=cal['dice_region']['y'],
                            width=cal['dice_region']['width'],
                            height=cal['dice_region']['height']
                        )
                        self.calibrations[table_id] = TableCalibration(
                            table_id=table_id,
                            dice_region=dice_region,
                            camera_angle=cal.get('camera_angle', 0),
                            lighting_level=cal.get('lighting_level', 0.5),
                            calibrated_at=cal.get('calibrated_at', '')
                        )
            except Exception as e:
                print(f"Error loading calibrations: {e}")

    def _save_calibrations(self) -> None:
        """Save calibrations to disk."""
        data = {}
        for table_id, cal in self.calibrations.items():
            data[table_id] = {
                'dice_region': {
                    'x': cal.dice_region.x,
                    'y': cal.dice_region.y,
                    'width': cal.dice_region.width,
                    'height': cal.dice_region.height
                },
                'camera_angle': cal.camera_angle,
                'lighting_level': cal.lighting_level,
                'calibrated_at': cal.calibrated_at
            }

        with open(self.calibration_file, 'w') as f:
            json.dump(data, f, indent=2)

    def set_calibration(
        self,
        table_id: str,
        dice_region: DiceRegion,
        camera_angle: float = 0,
        lighting_level: float = 0.5,
        calibrated_at: str = None
    ) -> None:
        """Set calibration for a table.
        
        Args:
            table_id: Unique table identifier
            dice_region: Region where dice are detected
            camera_angle: Camera angle in degrees
            lighting_level: Lighting level (0-1)
            calibrated_at: ISO timestamp of calibration
        """
        from datetime import datetime
        
        if calibrated_at is None:
            calibrated_at = datetime.utcnow().isoformat()

        self.calibrations[table_id] = TableCalibration(
            table_id=table_id,
            dice_region=dice_region,
            camera_angle=camera_angle,
            lighting_level=lighting_level,
            calibrated_at=calibrated_at
        )
        self._save_calibrations()

    def get_calibration(self, table_id: str = "default") -> Optional[TableCalibration]:
        """Get calibration for a table.
        
        Args:
            table_id: Table identifier
            
        Returns:
            TableCalibration or None if not found
        """
        return self.calibrations.get(table_id)

    def has_calibration(self, table_id: str = "default") -> bool:
        """Check if calibration exists for table.
        
        Args:
            table_id: Table identifier
            
        Returns:
            True if calibration exists
        """
        return table_id in self.calibrations


# Global calibration manager
_calibration_manager = CalibrationManager()


def get_calibration(table_id: str = "default") -> Optional[TableCalibration]:
    """Get current table calibration.
    
    Args:
        table_id: Table identifier
        
    Returns:
        TableCalibration or None
    """
    return _calibration_manager.get_calibration(table_id)


def set_calibration(
    dice_region: DiceRegion,
    table_id: str = "default",
    camera_angle: float = 0,
    lighting_level: float = 0.5
) -> None:
    """Set table calibration.
    
    Args:
        dice_region: Region where dice are detected
        table_id: Table identifier
        camera_angle: Camera angle in degrees
        lighting_level: Lighting level (0-1)
    """
    _calibration_manager.set_calibration(
        table_id,
        dice_region,
        camera_angle,
        lighting_level
    )
