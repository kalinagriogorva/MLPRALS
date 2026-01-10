from typing import Tuple

def is_sme(employees: int, turnover_m: float, balance_m: float) -> bool:
    """
    EU SME definition used in the app:
    - employees < 250
    - and (turnover <= 50m OR balance sheet <= 43m)
    """
    return (employees < 250) and ((turnover_m <= 50.0) and (balance_m <= 43.0))

def eligibility_snapshot(employees: int, turnover_m: float, balance_m: float) -> Tuple[int, float, float]:
    return (employees, float(turnover_m), float(balance_m))
