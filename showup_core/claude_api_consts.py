LINE_EDIT_HEADER = """\
EDIT FORMAT SPECIFICATIONS:
1. To INSERT content after a specific line:
  [EDIT:INSERT:X]
  Your new content here
  [/EDIT]

2. To REPLACE content:
  [EDIT:REPLACE:X-Y]
  Your replacement content here
  [/EDIT]

X and Y represent line numbers from the document.
DO NOT include line numbers in your output content.
DO NOT provide any explanation - only the edit commands.
"""
