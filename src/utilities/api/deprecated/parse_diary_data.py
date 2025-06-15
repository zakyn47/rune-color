# Scraped from: https://github.com/christoabrown/group-ironmen/blob/master/site/src/data/diaries.js
from pathlib import Path
from typing import List

if __name__ == "__main__":
    import sys

    # Go up one level to facilitate importing from `mappings` below.
    sys.path[0] = str(Path(sys.path[0]).parents[0])

from mappings.diaries import DIARIES


def is_bit_set(num, bit) -> bool:
    """
    Determines if the bit at the specified position in the integer is set (i.e., is 1).

    Args:
        num (int): The integer to check.
        bit (int): The bit position to check, indexed from 0 (rightmost bit).

    Returns:
        bool: True if the bit at the specified position is set, otherwise False.

    Example:
        >>> is_bit_set(10, 3)
        True

    Explanation:
        The binary representation of 10 is 1010.
        - Bit positions (right to left) are:
          Position 0: 0
          Position 1: 1
          Position 2: 0
          Position 3: 1
        - Checking the bit at position 3:
            - (1 << 3) shifts binary 1 three positions to the left, resulting in binary 1000 (decimal 8).
            - 10 & 8 performs a bitwise AND between 10 (1010) and 8 (1000), resulting in 1000 (decimal 8).
        - Since 8 is not 0, the function returns True, indicating that the bit at position 3 is set.

    Tracking Achievements with Binary Flags:
        - Each achievement in a region is represented by a binary flag (a bit), where 1
            indicates the achievement is complete and 0 indicates it is not complete.
        - For example, if a region has 5 achievements, we represent their collective
            completion status with a string like 10101, where each position in the
            string corresponds to a different achievement.
        - Instead of storing the string of flags directly, we convert it to a decimal
            number. This is more memory-efficient.
    """
    return (num & (1 << bit)) != 0


def numlist(lo, hi) -> List[int]:
    """
    Returns a list of integers from lo to hi, inclusive.

    Args:
        lo (int): Starting integer.
        hi (int): Ending integer.

    Returns:
        List[int]: List of integers from lo to hi.

    Example:
        >>> numlist(3, 7)
        [3, 4, 5, 6, 7]
    """
    return list(range(lo, hi + 1))


def parse_diary_data(diary_vars):
    diary_mappings = {
        "Ardougne": {
            "Easy": [(0, numlist(0, 2) + numlist(4, 7) + [9] + numlist(11, 12))],
            "Medium": [(0, numlist(13, 25))],
            "Hard": [(0, numlist(26, 31)), (1, numlist(0, 5))],
            "Elite": [(1, numlist(6, 13))],
        },
        "Desert": {
            "Easy": [(2, numlist(1, 11))],
            #  The idiosyncratic OR condition is represented with a tuple.
            "Medium": [(2, numlist(12, 21)), (2, [23]), ((2, 22), (3, 9))],
            "Hard": [(2, numlist(24, 31)), (3, numlist(0, 1))],
            "Elite": [(3, [2] + numlist(4, 8))],
        },
        "Falador": {
            "Easy": [(4, numlist(0, 10))],
            "Medium": [(4, numlist(11, 25))],
            "Hard": [(4, numlist(26, 31)), (5, numlist(0, 4))],
            "Elite": [(5, numlist(5, 10))],
        },
        "Fremennik": {
            "Easy": [(6, numlist(1, 10))],
            "Medium": [(6, numlist(11, 15) + numlist(17, 20))],
            "Hard": [(6, [21] + numlist(23, 30))],
            "Elite": [(6, [31]), (7, numlist(0, 4))],
        },
        "Kandarin": {
            "Easy": [(8, numlist(1, 11))],
            "Medium": [(8, numlist(12, 25))],
            "Hard": [(8, numlist(26, 31)), (9, numlist(0, 4))],
            "Elite": [(9, numlist(5, 11))],
        },
        "Karamja": {
            "Easy": [(i, [5] if i in [23, 30] else [1]) for i in range(23, 33)],
            "Medium": [(i, [1]) for i in range(33, 52)],
            "Hard": [(i, [5] if i == 59 else [1]) for i in range(52, 62)],
            "Elite": [(10, numlist(1, 5))],
        },
        "Kourend & Kebos": {
            "Easy": [(11, numlist(1, 12))],
            "Medium": [(11, numlist(13, 25))],
            "Hard": [(11, numlist(26, 31)), (12, numlist(0, 3))],
            "Elite": [(12, numlist(4, 11))],
        },
        "Lumbridge & Draynor": {
            "Easy": [(13, numlist(1, 12))],
            "Medium": [(13, numlist(13, 24))],
            "Hard": [(13, numlist(25, 31)), (14, numlist(0, 3))],
            "Elite": [(14, numlist(4, 9))],
        },
        "Morytania": {
            "Easy": [(15, numlist(1, 11))],
            "Medium": [(15, numlist(12, 22))],
            "Hard": [(15, numlist(23, 30)), (16, numlist(1, 2))],
            "Elite": [(16, numlist(3, 8))],
        },
        "Varrock": {
            "Easy": [(17, numlist(1, 14))],
            "Medium": [(17, numlist(15, 16) + numlist(18, 28))],
            "Hard": [(17, numlist(29, 31)), (18, numlist(0, 6))],
            "Elite": [(18, numlist(7, 11))],
        },
        "Western Provinces": {
            "Easy": [(19, numlist(1, 11))],
            "Medium": [(19, numlist(12, 24))],
            "Hard": [(19, numlist(25, 31)), (20, numlist(0, 5))],
            "Elite": [(20, numlist(6, 9) + numlist(12, 14))],
        },
        "Wilderness": {
            "Easy": [(21, numlist(1, 12))],
            "Medium": [(21, numlist(13, 16) + numlist(18, 24))],
            "Hard": [(21, numlist(25, 31)), (22, numlist(0, 2))],
            "Elite": [(22, [3, 5] + numlist(7, 11))],
        },
    }

    regions = [
        "Ardougne",
        "Desert",
        "Falador",
        "Fremennik",
        "Kandarin",
        "Karamja",
        "Kourend & Kebos",
        "Lumbridge & Draynor",
        "Morytania",
        "Varrock",
        "Western Provinces",
        "Wilderness",
    ]
    difficulties = ["Easy", "Medium", "Hard", "Elite"]
    completion_status = {
        region: {difficulty: [] for difficulty in difficulties} for region in regions
    }
    for region, difficulties in diary_mappings.items():
        for difficulty, tasks in difficulties.items():
            for var_index, bits in tasks:
                # Special OR condition! Thus, rather than `var_index` being an int and
                # `bits` being a list of ints, `var_index` and `bits` are both tuples,
                # each with an int in the first index and a list of ints in the second.
                if isinstance(var_index, tuple):
                    completed = any(
                        [
                            is_bit_set(diary_vars[var_index[0]], var_index[1]),
                            is_bit_set(diary_vars[bits[0]], bits[1]),
                        ]
                    )
                    completion_status[region][difficulty].append(completed)
                    continue
                for bit in bits:
                    if region == "Karamja":  # This diary is uniquely defined.
                        completed = diary_vars[var_index] == bit
                    else:
                        completed = is_bit_set(diary_vars[var_index], bit)
                    completion_status[region][difficulty].append(completed)

    serialized_diary = DIARIES.copy()
    for region, difficulties in completion_status.items():
        for difficulty, statuses in difficulties.items():
            for i, status in enumerate(statuses):
                try:
                    serialized_diary[region][difficulty][i]["status"] = status
                except IndexError:
                    serialized_diary[region][difficulty].append({"task": "UNKNOWN"})

    return serialized_diary


# Example input
diary_vars = [
    -4195593,
    16383,
    -2,
    503,
    -524289,
    2047,
    -4259842,
    31,
    -2,
    4095,
    254,
    -2,
    4095,
    -2,
    1023,
    2147483646,
    510,
    -131074,
    4095,
    -2,
    29695,
    -131074,
    4015,
    5,
    1,
    1,
    1,
    1,
    1,
    1,
    5,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    5,
    1,
    1,
]

diary_vars2 = [
    -1576518921,
    0,
    117848,
    0,
    37814918,
    0,
    8520192,
    0,
    17962524,
    0,
    0,
    34603024,
    0,
    75698754,
    0,
    2136640,
    0,
    277446654,
    0,
    25090,
    0,
    2052,
    0,
    5,
    0,
    0,
    1,
    1,
    1,
    1,
    1,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    1,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
]


# Parsing the input
parsed_data = parse_diary_data(diary_vars)
print("Maxed")
print(parsed_data)
print("-----------------------------")
# Parsing the input
parsed_data = parse_diary_data(diary_vars2)
print("GIM")
print(parsed_data)
