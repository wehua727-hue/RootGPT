# Script to fix emoji list in admin_handler.py

with open('src/handlers/admin_handler.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with the emoji list (around line 1289)
for i, line in enumerate(lines):
    if "emojis = ['👍', '❤️', '🔥', '😍', '🎉', '💯', '🤩', '🥰', '👏'," in line:
        print(f"Found emoji list at line {i+1}")
        # Replace with full emoji list
        new_emojis = """        emojis = [
            '👍', '👎', '❤️', '🔥', '🥰', '👏', '😁', '🤔', '🤯', '😱',
            '🤬', '😢', '🎉', '🤩', '🤮', '💩', '🙏', '👌', '🕊', '🤡',
            '🥱', '🥴', '😍', '🐳', '❤️‍🔥', '🌚', '🌭', '💯', '🤣', '⚡️',
            '🍌', '🏆', '💔', '🤨', '😐', '🍓', '🍾', '💋', '🖕', '😈',
            '😴', '😭', '🤓', '👻', '👨‍💻', '👀', '🎃', '🙈', '😇', '😨',
            '🤝', '✍️', '🤗', '🫡', '🎅', '🎄', '☃️', '💅', '🤪', '🗿',
            '🆒', '💘', '🙉', '🦄', '😘', '💊', '🙊', '😎', '👾', '🤷‍♂️',
            '🤷', '🤷‍♀️', '😡'
        ]
"""
        lines[i] = new_emojis
        break

# Write back
with open('src/handlers/admin_handler.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Emoji list updated!")
