import re
from typing import Dict

def canon_name(name: str) -> str:
    n = name.strip().lower()
    n = re.sub(r'^(mr\.|mrs\.|ms\.|dr\.|prof\.)\s+', '', n)
    n = re.sub(r'\s+', ' ', n)
    return n

RELATION_CANON = {
    "works at": "WORKS_AT",
    "works_for": "WORKS_AT",
    "employed by": "WORKS_AT",
    "attended": "ATTENDED",
    "participated in": "ATTENDED",
    "presented at": "ATTENDED",
    "spoke at": "ATTENDED",
    "friend of": "FRIEND_OF",
    "located in": "LOCATED_IN",
    "based in": "LOCATED_IN",
    "situated in": "LOCATED_IN",
    "held in": "LOCATED_IN",
    "causes": "CAUSES",
    "mentions": "MENTIONS",
    "refers to": "MENTIONS",
    "discusses": "MENTIONS",
    "leads": "LEADS",
    "heads": "LEADS",
    "directs": "LEADS",
    "manages": "MANAGES",
    "oversees": "MANAGES",
    "founded": "FOUNDED",
    "established": "FOUNDED",
    "started": "FOUNDED",
    "collaborates with": "COLLABORATES_WITH",
    "collaborates_with": "COLLABORATES_WITH",
    "collaborated with": "COLLABORATES_WITH",
    "works with": "COLLABORATES_WITH",
    "partners with": "COLLABORATES_WITH",
    "teams up with": "COLLABORATES_WITH",
    "affiliated with": "AFFILIATED_WITH",
    "affiliated_with": "AFFILIATED_WITH",
    "member of": "MEMBER_OF",
    "belongs to": "MEMBER_OF",
    "part of": "MEMBER_OF",
    "published in": "PUBLISHED_IN",
    "published_in": "PUBLISHED_IN",
    "appeared in": "PUBLISHED_IN",
    "featured in": "PUBLISHED_IN",
    "authored": "AUTHORED",
    "wrote": "AUTHORED",
    "created": "AUTHORED",
    "discovered": "DISCOVERED",
    "developed": "DISCOVERED",
    "found": "DISCOVERED",
    "invented": "INVENTED",
    "designed": "INVENTED",
    "advised": "ADVISED",
    "supervised": "ADVISED",
    "advised by": "ADVISED",
    "mentored": "ADVISED",
    "guided": "ADVISED",
    "awarded": "AWARDED",
    "won": "AWARDED",
    "received": "AWARDED",
    "honored with": "AWARDED",
    "recognized with": "AWARDED",
    "researched": "RESEARCHES",
    "researches": "RESEARCHES",
    "studies": "RESEARCHES",
    "investigates": "RESEARCHES",
    "works on": "RESEARCHES",
}

def canon_relation(label: str) -> str:
    l = label.strip().lower().replace(" ", "_")
    return RELATION_CANON.get(l, label.upper())