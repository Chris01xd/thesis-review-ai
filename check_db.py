import sys; sys.path.insert(0, ".")
from modules.database import query

advances  = query("SELECT id, title, status FROM advances ORDER BY id")
analyses  = query("SELECT advance_id, overall_score, grade FROM ai_analyses")
findings  = query("SELECT COUNT(*) AS c FROM findings")[0]["c"]
citations = query("SELECT COUNT(*) AS c FROM citations")[0]["c"]
jobs      = query("SELECT COUNT(*) AS c FROM agent_jobs")[0]["c"]

print(f"Avances:    {len(advances)}")
print(f"Analisis:   {len(analyses)}")
print(f"Hallazgos:  {findings}")
print(f"Citas:      {citations}")
print(f"Agent jobs: {jobs}")
print()
for a in advances:
    grade = next((x["grade"] for x in analyses if x["advance_id"] == a["id"]), None)
    g = f"{grade:.1f}/20" if grade else "sin nota"
    print(f"  ID {a['id']} | {a['title'][:45]:45s} | {g} | {a['status']}")
