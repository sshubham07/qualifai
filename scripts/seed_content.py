"""Validate every YAML under content/ against its schema (and later load into Postgres).

Run: python scripts/seed_content.py
"""

from qualifai.content.loader import role_family, round_template, skill_aliases, tier_preset
from qualifai.domain.enums import CompanyTier, RoleFamily, RoundType

if __name__ == "__main__":
    for r in RoundType:
        print("round  ", r.value, "→", round_template(r).name)
    for t in CompanyTier:
        print("tier   ", t.value, "→", tier_preset(t).name)
    for f in RoleFamily:
        spec = role_family(f)
        if spec:
            print("role   ", f.value, "→", spec.support.value)
    print("skills ", len(set(skill_aliases().values())), "canonical skills")
