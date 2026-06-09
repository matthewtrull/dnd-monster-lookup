"""
HTTP API Wrapper for D&D 5e Monster CR Adjuster MCP Server
Exposes MCP tools via REST API for remote access via ngrok
"""

from flask import Flask, request, jsonify
import json
from monster_cr_adjuster import (
    fetch_monster,
    adjust_monster_cr,
    get_db_connection
)

app = Flask(__name__)
@app.route('/api/wakeup', methods=['GET'])
def wakeup():
    return {"status": "ready", "message": "Server is awake!"}, 200
@app.route('/', methods=['GET'])
def index():
    """API documentation."""
    return jsonify({
        "service": "D&D 5e Monster CR Adjuster API",
        "version": "1.0",
        "endpoints": {
            "GET /api/monsters": "List all monsters",
            "GET /api/monsters/search?name=goblin": "Search monsters",
            "GET /api/monster/<name>": "Fetch specific monster",
            "POST /api/adjust": "Adjust monster CR",
        },
        "example_adjust": {
            "monster_name": "goblin",
            "target_cr": 5,
            "hp_adjustment": 20,
            "ac_adjustment": 1,
            "str_mod": 2
        }
    })
@app.route('/api/wakeup', methods=['GET'])
def wakeup():
    return {"status": "ready", "message": "Server is awake!"}, 200
@app.route('/api/monsters', methods=['GET'])
def list_monsters():
    """List all monsters with optional search."""
    search = request.args.get('search', '')
    limit = request.args.get('limit', 50, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if search:
        query = "SELECT name, size, type, armor_class, hit_points, challenge_rating FROM monsters WHERE LOWER(name) LIKE LOWER(?) ORDER BY challenge_rating LIMIT ?"
        cursor.execute(query, (f'%{search}%', limit))
    else:
        query = "SELECT name, size, type, armor_class, hit_points, challenge_rating FROM monsters ORDER BY challenge_rating LIMIT ?"
        cursor.execute(query, (limit,))
    
    monsters = [
        {
            "name": row[0],
            "size": row[1],
            "type": row[2],
            "ac": row[3],
            "hp": row[4],
            "cr": row[5]
        }
        for row in cursor.fetchall()
    ]
    conn.close()
    
    return jsonify({
        "count": len(monsters),
        "monsters": monsters
    })

@app.route('/api/monster/<name>', methods=['GET'])
def get_monster(name):
    """Fetch a specific monster."""
    monster = fetch_monster(name)
    if not monster:
        return jsonify({"error": f"Monster '{name}' not found"}), 404
    
    return jsonify({
        "name": monster.get('name'),
        "size": monster.get('size'),
        "type": monster.get('type'),
        "alignment": monster.get('alignment'),
        "ac": monster.get('armor_class'),
        "hp": monster.get('hit_points'),
        "hit_dice": monster.get('hit_dice'),
        "cr": monster.get('challenge_rating'),
        "xp": monster.get('xp'),
        "str": monster.get('strength'),
        "dex": monster.get('dexterity'),
        "con": monster.get('constitution'),
        "int": monster.get('intelligence'),
        "wis": monster.get('wisdom'),
        "cha": monster.get('charisma'),
        "languages": monster.get('languages'),
        "special_abilities_count": len(monster.get('special_abilities', [])),
        "actions_count": len(monster.get('actions', [])),
    })

@app.route('/api/adjust', methods=['POST'])
def adjust_cr():
    """Adjust a monster's CR."""
    data = request.get_json()
    
    if not data or 'monster_name' not in data:
        return jsonify({"error": "monster_name is required"}), 400
    
    result = adjust_monster_cr(
        monster_name=data.get('monster_name'),
        target_cr=data.get('target_cr'),
        hp_adjustment=data.get('hp_adjustment', 0),
        ac_adjustment=data.get('ac_adjustment', 0),
        str_mod=data.get('str_mod', 0),
        dex_mod=data.get('dex_mod', 0),
        con_mod=data.get('con_mod', 0),
        int_mod=data.get('int_mod', 0),
        wis_mod=data.get('wis_mod', 0),
        cha_mod=data.get('cha_mod', 0),
    )
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "Monster CR Adjuster API"})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    print("D&D 5e Monster CR Adjuster - HTTP API")
    print("=" * 50)
    print(f"Starting on http://0.0.0.0:{port}")
    print("=" * 50)
    app.run(debug=False, port=port, host='0.0.0.0')
