from dataclasses import dataclass
from typing import Optional, Tuple, List
import re

@dataclass
class Conversion:
    target_unit: str
    factor: float
    threshold: Optional[float] = None

class MeasurementConverter:
    def __init__(self):
        self.conversions = {
            'IN': [Conversion('CM', 2.54),Conversion('MR', 0.0254, 40)],
            'MM': [Conversion('CM', 0.1, 9),Conversion('MR', 0.001, 999)],
            'CM': Conversion('MR', 0.01, 99),
            'YD': Conversion('MR', 0.9144),
            'YARD': Conversion('MR', 0.9144),
            'FT': Conversion('MR', 0.3048),

            # Weight conversions
            'OZ': Conversion('GR', 28.3495),
            'OUNCE': Conversion('GR', 28.3495),
            'GR': Conversion('KG', 0.001, 999),

            # Volume conversions
            'GALLON': Conversion('LT', 3.78541),
            'GAL': Conversion('LT', 3.78541),
            'GA': Conversion('LT', 3.78541),
            'GL': Conversion('LT', 3.78541),
            'ML': Conversion('LT', 0.001, 999)
        }
        self.unit_pattern = '|'.join(self.conversions.keys())
        self.measurement_pattern = re.compile(
            rf'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*({self.unit_pattern})|'  # Range
            rf'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)\s*({self.unit_pattern})|'  # Fraction
            rf'(\d+\.?\d*)\s*X\s*(\d+\.?\d*)\s*({self.unit_pattern})|'  # Multiplication
            rf'(\d+\.?\d*)\s*({self.unit_pattern})',  # Single measurement
            re.IGNORECASE
        )

    def format_number(self, num: float) -> str:
        """Format a number to remove trailing zeros and decimal if unnecessary."""
        return f"{num:.3f}".rstrip('0').rstrip('.')

    def convert_value(self, value: float, unit: str) -> Tuple[float, str]:
        """Convert a value from one unit to another based on conversion rules."""
        unit = unit.upper()
        if unit not in self.conversions:
            return value, unit

        conv_rules = self.conversions[unit]
        if isinstance(conv_rules, list):
            for conv in reversed(conv_rules):
                if conv.threshold is None or value > conv.threshold:
                    return value * conv.factor, conv.target_unit
        else:
            conv = conv_rules
            if conv.threshold is None or value > conv.threshold:
                return value * conv.factor, conv.target_unit
        return value, unit

    def process_measurement(self, match: re.Match) -> str:
        """Process a regex match to convert and format a measurement."""
        if match.group(1):  # Range
            start, end, unit = float(match.group(1)), float(match.group(2)), match.group(3)
            start_val, start_unit = self.convert_value(start, unit)
            end_val, end_unit = self.convert_value(end, unit)
            return (f"{self.format_number(start_val)}-{self.format_number(end_val)} {start_unit}"
                    if start_unit == end_unit else
                    f"{self.format_number(start_val)}{start_unit}-{self.format_number(end_val)}{end_unit}")

        elif match.group(4):  # Fraction
            num, denom, unit = float(match.group(4)), float(match.group(5)), match.group(6)
            num_val, num_unit = self.convert_value(num, unit)
            denom_val, denom_unit = self.convert_value(denom, unit)
            return f"{self.format_number(num_val)}{num_unit}/{self.format_number(denom_val)}{denom_unit}"

        elif match.group(7):  # Multiplication
            val1, val2, unit = float(match.group(7)), float(match.group(8)), match.group(9)
            val1_conv, unit_conv = self.convert_value(val1, unit)
            val2_conv, _ = self.convert_value(val2, unit)
            return f"{self.format_number(val1_conv)} X {self.format_number(val2_conv)} {unit_conv}"

        else:  # Single measurement
            value, unit = float(match.group(10)), match.group(11)
            conv_value, conv_unit = self.convert_value(value, unit)
            return f"{self.format_number(conv_value)} {conv_unit}"

    def convert_text(self, text: str) -> str:
        """Convert measurements in the text."""
        return self.measurement_pattern.sub(self.process_measurement, text)