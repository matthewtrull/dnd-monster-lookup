"""
D&D 5e Monster CR Adjuster - MCP Server
Retrieves monsters from the database and adjusts their CR using DMG rules.
Based on D&D 5e Dungeon Master's Guide CR adjustment guidelines.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any
import math

DB_PATH = r'c:\MonsterDB\monsters.db'

class MonsterCRAdjuster:
    """Calculates monster CR adjustments based on DMG rules."""
    
    # DMG CR Adjustment Table (simplified)
    # CR is based on offense (attack bonus + damage per round) and defense (AC + HP)
    CHALLENGE_RATINGS = {
        0: {"min_offense": 0, "max_offense": 3, "min_defense": 2, "max_defense": 13},
        0.125: {"min_offense": 3, "max_offense": 6, "min_defense": 2, "max_defense": 15},
        0.25: {"min_offense": 6, "max_offense": 9, "min_defense": 3, "max_defense": 18},
        0.5: {"min_offense": 9, "max_offense": 12, "min_defense": 3, "max_defense": 21},
        1: {"min_offense": 12, "max_offense": 15, "min_defense": 4, "max_defense": 27},
        2: {"min_offense": 15, "max_offense": 18, "min_defense": 4, "max_defense": 33},
        3: {"min_offense": 18, "max_offense": 21, "min_defense": 5, "max_defense": 39},
        4: {"min_offense": 21, "max_offense": 24, "min_defense": 5, "max_defense": 45},
        5: {"min_offense": 24, "max_offense": 27, "min_defense": 6, "max_defense": 51},
        6: {"min_offense": 27, "max_offense": 30, "min_defense": 6, "max_defense": 57},
        7: {"min_offense": 30, "max_offense": 33, "min_defense": 6, "max_defense": 66},
        8: {"min_offense": 33, "max_offense": 36, "min_defense": 7, "max_defense": 75},
        9: {"min_offense": 36, "max_offense": 39, "min_defense": 7, "max_defense": 84},
        10: {"min_offense": 39, "max_offense": 42, "min_defense": 8, "max_defense": 93},
        11: {"min_offense": 42, "max_offense": 45, "min_defense": 8, "max_defense": 102},
        12: {"min_offense": 45, "max_offense": 48, "min_defense": 8, "max_defense": 111},
        13: {"min_offense": 48, "max_offense": 51, "min_defense": 9, "max_defense": 120},
        14: {"min_offense": 51, "max_offense": 54, "min_defense": 9, "max_defense": 129},
        15: {"min_offense": 54, "max_offense": 57, "min_defense": 10, "max_defense": 138},
        16: {"min_offense": 57, "max_offense": 60, "min_defense": 10, "max_defense": 147},
        17: {"min_offense": 60, "max_offense": 63, "min_defense": 10, "max_defense": 156},
        18: {"min_offense": 63, "max_offense": 66, "min_defense": 11, "max_defense": 165},
        19: {"min_offense": 66, "max_offense": 69, "min_defense": 11, "max_defense": 174},
        20: {"min_offense": 69, "max_offense": 72, "min_defense": 12, "max_defense": 183},
        21: {"min_offense": 72, "max_offense": 75, "min_defense": 12, "max_defense": 192},
        22: {"min_offense": 75, "max_offense": 78, "min_defense": 12, "max_defense": 201},
        23: {"min_offense": 78, "max_offense": 81, "min_defense": 13, "max_defense": 210},
        24: {"min_offense": 81, "max_offense": 84, "min_defense": 13, "max_defense": 219},
        25: {"min_offense": 84, "max_offense": 87, "min_defense": 14, "max_defense": 228},
        26: {"min_offense": 87, "max_offense": 90, "min_defense": 14, "max_defense": 237},
        27: {"min_offense": 90, "max_offense": 93, "min_defense": 14, "max_defense": 246},
        28: {"min_offense": 93, "max_offense": 96, "min_defense": 15, "max_defense": 255},
        29: {"min_offense": 96, "max_offense": 99, "min_defense": 15, "max_defense": 264},
        30: {"min_offense": 99, "max_offense": 102, "min_defense": 16, "max_defense": 273},
    }
    
    @staticmethod
    def calculate_offense(attack_bonus: int, avg_damage_per_action: float, num_actions: int = 1) -> float:
        """Calculate offensive rating per DMG rules."""
        # Offensive CR = (attack bonus) + (average damage per round / 4)
        avg_damage = avg_damage_per_action * num_actions
        offensive_cr = attack_bonus + (avg_damage / 4)
        return offensive_cr
    
    @staticmethod
    def calculate_defense(ac: int, hp: int) -> float:
        """Calculate defensive rating per DMG rules."""
        # Defensive CR = (AC + (HP / 8)) / 2
        defensive_cr = (ac + (hp / 8)) / 2
        return defensive_cr
    
    @staticmethod
    def get_cr_from_ratings(offensive: float, defensive: float) -> float:
        """Determine CR from offensive and defensive ratings."""
        avg_rating = (offensive + defensive) / 2
        
        # Find closest CR
        for cr in sorted(MonsterCRAdjuster.CHALLENGE_RATINGS.keys()):
            if cr >= avg_rating:
                return cr
        return 30
    
    @staticmethod
    def estimate_damage_per_turn(monster_data: dict) -> float:
        """Estimate average damage per turn from actions."""
        total_damage = 0
        action_count = 0
        
        actions = monster_data.get('actions', [])
        for action in actions:
            desc = action.get('description', '')
            
            # Simple regex parsing for damage dice
            import re
            damage_matches = re.findall(r'(\d+)d(\d+)(?:\+(\d+))?', desc)
            
            for match in damage_matches:
                dice_count = int(match[0])
                dice_type = int(match[1])
                bonus = int(match[2]) if match[2] else 0
                avg_damage = (dice_count * (dice_type + 1) / 2) + bonus
                total_damage += avg_damage
                action_count += 1
        
        return total_damage / max(1, action_count) if action_count > 0 else 5

def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_monster(monster_name: str) -> dict | None:
    """Fetch a monster from the database by name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM monsters WHERE LOWER(name) LIKE LOWER(?)', (f'%{monster_name}%',))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None
    
    monster_id = result['id']
    monster = dict(result)
    
    # Fetch related data
    cursor.execute('SELECT action_name, description, attack_bonus FROM actions WHERE monster_id = ?', (monster_id,))
    actions = [{'name': row[0], 'description': row[1], 'attack_bonus': row[2]} for row in cursor.fetchall()]
    monster['actions'] = actions
    
    cursor.execute('SELECT ability_name, description FROM special_abilities WHERE monster_id = ?', (monster_id,))
    monster['special_abilities'] = [{'name': row[0], 'description': row[1]} for row in cursor.fetchall()]
    
    cursor.execute('SELECT action_name, description, action_cost FROM legendary_actions WHERE monster_id = ?', (monster_id,))
    monster['legendary_actions'] = [{'name': row[0], 'description': row[1], 'cost': row[2]} for row in cursor.fetchall()]
    
    # Parse JSON fields
    monster['damage_vulnerabilities'] = json.loads(monster.get('damage_vulnerabilities', '[]'))
    monster['damage_resistances'] = json.loads(monster.get('damage_resistances', '[]'))
    monster['damage_immunities'] = json.loads(monster.get('damage_immunities', '[]'))
    monster['condition_immunities'] = json.loads(monster.get('condition_immunities', '[]'))
    
    conn.close()
    return monster

def adjust_monster_cr(
    monster_name: str,
    target_cr: float = None,
    hp_adjustment: int = 0,
    ac_adjustment: int = 0,
    add_ability: dict = None,
    remove_ability: bool = False,
    str_mod: int = 0,
    dex_mod: int = 0,
    con_mod: int = 0,
    int_mod: int = 0,
    wis_mod: int = 0,
    cha_mod: int = 0,
) -> dict:
    """
    Adjust a monster's CR and return the modified monster.
    
    Parameters:
    - monster_name: Name of the monster to fetch
    - target_cr: Target CR (will adjust HP/AC to reach it)
    - hp_adjustment: Add/subtract from HP
    - ac_adjustment: Add/subtract from AC
    - add_ability: Add a new ability (dict with 'name' and 'description')
    - remove_ability: Remove special abilities (approximates CR change)
    - *_mod: Ability score modifiers (-5 to +5)
    
    Returns: Modified monster data with recalculated CR
    """
    
    monster = fetch_monster(monster_name)
    if not monster:
        return {"error": f"Monster '{monster_name}' not found"}
    
    # Create modified copy
    adjusted = dict(monster)
    
    # Apply ability score modifications
    ability_map = {
        'strength': str_mod,
        'dexterity': dex_mod,
        'constitution': con_mod,
        'intelligence': int_mod,
        'wisdom': wis_mod,
        'charisma': cha_mod,
    }
    
    for ability, mod in ability_map.items():
        if mod != 0:
            current = adjusted.get(ability, 10)
            adjusted[ability] = max(1, min(20, current + mod))
    
    # Apply HP adjustment
    if hp_adjustment != 0:
        current_hp = adjusted.get('hit_points', 10)
        adjusted['hit_points'] = max(1, current_hp + hp_adjustment)
    
    # Apply AC adjustment
    if ac_adjustment != 0:
        current_ac = adjusted.get('armor_class', 10)
        adjusted['armor_class'] = max(8, current_ac + ac_adjustment)
    
    # Calculate new CR
    adjuster = MonsterCRAdjuster()
    avg_damage = adjuster.estimate_damage_per_turn(adjusted)
    
    # Get attack bonus (use highest from actions)
    attack_bonus = 0
    for action in adjusted.get('actions', []):
        if action.get('attack_bonus'):
            attack_bonus = max(attack_bonus, action['attack_bonus'])
    
    offensive = adjuster.calculate_offense(attack_bonus, avg_damage)
    defensive = adjuster.calculate_defense(
        adjusted['armor_class'],
        adjusted['hit_points']
    )
    
    new_cr = adjuster.get_cr_from_ratings(offensive, defensive)
    
    # If target_cr specified, adjust HP/AC to reach it
    if target_cr is not None and target_cr != new_cr:
        # Adjust HP to reach target CR
        current_ac = adjusted['armor_class']
        offensive = adjuster.calculate_offense(attack_bonus, avg_damage)
        
        # Back-calculate required HP
        target_defensive = target_cr  # Simplified
        required_hp = max(1, int((target_defensive * 2 - current_ac) * 8))
        adjusted['hit_points'] = required_hp
        
        defensive = adjuster.calculate_defense(current_ac, required_hp)
        new_cr = adjuster.get_cr_from_ratings(offensive, defensive)
    
    # Add ability if specified
    if add_ability:
        if 'special_abilities' not in adjusted:
            adjusted['special_abilities'] = []
        adjusted['special_abilities'].append(add_ability)
    
    # Calculate original CR for comparison
    original_offensive = adjuster.calculate_offense(attack_bonus, avg_damage)
    original_defensive = adjuster.calculate_defense(monster['armor_class'], monster['hit_points'])
    original_cr = adjuster.get_cr_from_ratings(original_offensive, original_defensive)
    
    return {
        "original_monster": {
            "name": monster['name'],
            "cr": monster.get('challenge_rating', original_cr),
            "hp": monster['hit_points'],
            "ac": monster['armor_class'],
        },
        "adjusted_monster": {
            "name": adjusted['name'],
            "cr": new_cr,
            "hp": adjusted['hit_points'],
            "ac": adjusted['armor_class'],
            "strength": adjusted.get('strength'),
            "dexterity": adjusted.get('dexterity'),
            "constitution": adjusted.get('constitution'),
            "intelligence": adjusted.get('intelligence'),
            "wisdom": adjusted.get('wisdom'),
            "charisma": adjusted.get('charisma'),
            "special_abilities": adjusted.get('special_abilities', []),
        },
        "adjustments": {
            "hp_change": hp_adjustment,
            "ac_change": ac_adjustment,
            "str_mod": str_mod,
            "dex_mod": dex_mod,
            "con_mod": con_mod,
            "int_mod": int_mod,
            "wis_mod": wis_mod,
            "cha_mod": cha_mod,
        },
        "cr_change": f"{original_cr} → {new_cr}",
        "notes": [
            f"Original CR: {original_cr}",
            f"Adjusted CR: {new_cr}",
            f"Offensive Rating: {original_offensive:.1f} → {adjuster.calculate_offense(attack_bonus, avg_damage):.1f}",
            f"Defensive Rating: {original_defensive:.1f} → {adjuster.calculate_defense(adjusted['armor_class'], adjusted['hit_points']):.1f}",
        ]
    }

if __name__ == '__main__':
    # Test the adjuster
    result = adjust_monster_cr(
        'goblin',
        hp_adjustment=10,
        ac_adjustment=1,
        str_mod=2,
    )
    print(json.dumps(result, indent=2))
