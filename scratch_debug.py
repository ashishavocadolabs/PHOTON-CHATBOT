import pathlib, sys
p = pathlib.Path(r'c:\Users\AshishGupta\PHOTON-CHATBOT\core\ai_orchestrator.py')
lines = p.read_text(encoding='utf-8').splitlines()
for i,line in enumerate(lines,1):
    if 600 <= i <= 620:
        print(i, repr(line))
