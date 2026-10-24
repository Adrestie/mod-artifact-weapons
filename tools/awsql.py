"""Lit les fichiers SQL de mod-artifact-weapons (DELETE + INSERT ... VALUES (...), (...);) : leurs lignes, table par table."""
import glob, os, re

BASE = r"E:\WoW-mods\mod-artifact-weapons\data\sql\db-world\base"


def split_values(text):
    """les tuples d'une liste VALUES, chacun en liste de jetons SQL (texte tel qu'écrit, guillemets compris)"""
    rows, row, cur, i, depth, inq = [], [], [], 0, 0, False
    n = len(text)
    while i < n:
        c = text[i]
        if inq:
            if c == "\\" and i + 1 < n:
                cur.append(text[i:i + 2]); i += 2; continue
            if c == "'":
                if i + 1 < n and text[i + 1] == "'":
                    cur.append("''"); i += 2; continue
                inq = False
            cur.append(c); i += 1; continue
        if c == "'":
            inq = True; cur.append(c)
        elif c == "(":
            depth += 1
            if depth == 1:
                row, cur = [], []
            else:
                cur.append(c)
        elif c == ")":
            depth -= 1
            if depth == 0:
                row.append("".join(cur).strip()); rows.append(row); cur = []
            else:
                cur.append(c)
        elif c == "," and depth == 1:
            row.append("".join(cur).strip()); cur = []
        elif depth >= 1:
            cur.append(c)
        elif c == ";":
            break
        i += 1
    return rows


def tables():
    out = {}
    for path in sorted(glob.glob(os.path.join(BASE, "*.sql"))):
        text = open(path, encoding="utf-8").read()
        for m in re.finditer(r"INSERT INTO `(\w+)` \(([^)]*)\) VALUES", text):
            table = m.group(1)
            cols = [c.strip(" `") for c in m.group(2).split(",")]
            rows = split_values(text[m.end():])
            out.setdefault(table, {"file": os.path.basename(path), "cols": cols, "rows": []})["rows"] += rows
    return out


if __name__ == "__main__":
    import sys
    T = tables()
    want = sys.argv[1:]
    for name, t in T.items():
        for r in t["rows"]:
            if any(v.strip("'") in want for v in r[:3]):
                print("==", name, t["file"])
                print({c: v for c, v in zip(t["cols"], r) if v not in ("0", "''", "NULL", "0.0", "0.00")})
