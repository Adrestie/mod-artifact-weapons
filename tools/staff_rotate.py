"""Le bâton de Jin Gu (84036) retourné : staff_2h_artifactmonkeyking_d_03 et sa physique tournés de 180° autour de y
(Maitre, 25/10/2026 10:59 UTC : dégainé, la tête de dragon et sa cloche sont devant, elles doivent être derrière).

ABANDONNÉ (Maitre, 25/10/2026 11:57 UTC) : tourné, le cylindre passait en haut en garde, « doublement à l'envers ». Le modèle
d'origine met le cylindre en bas en Ready2HL, comme un bâton natif. La partie reprend le bâton et le .phys d'origine ;
l'outil reste pour mémoire.

    python tools/staff_rotate.py <dossier de travail>

Lit ported_orig/ (le bâton porté du retail et le .phys de E:\\atelier\\weapon-physics, jamais modifiés), écrit ported/.

Pourquoi y : comme tout bâton de 3.3.5, le modèle a sa tête en +x (le bout large, ici le dragon) et la prise à l'origine ;
dégainé, +x vise devant et +z le haut. La chaîne de la cloche (os 1, 3, 4, 5, marqués 0x400) est modelée vers +z, donc
au-dessus du dragon dans toutes les poses de 3.3.5. Le demi-tour autour de y (x et z changent de signe) met le dragon
derrière et la chaîne vers le bas, là où elle pend ; autour de z, la cloche resterait au-dessus.
Mais les bâtons se tiennent en Ready2HL / Attack2HL : au repos, +x (la tête) monte et +z part vers l'arrière et le
bas ; tourné, le dragon passe en bas au repos et la chaîne, modelée, pointe vers l'avant et le haut (la physique la fait
pendre quand même). Le choix suit ce que Maitre voit en jeu ; rendus des deux sens à côté d'un bâton natif : voir le
message du commit.

Deux réflexions (x puis z) : les faces gardent leur sens, les rotations des os gardent la composante y et changent le
signe de x et z. Dans le .phys, tous les vecteurs sont dans les axes du modèle : positions des corps (BDY4), extrémités
des capsules (CAPS), repères des articulations (SHJ2, REV2, WLJ3 : trois axes puis une translation).
"""
import os
import struct
import sys

sys.path.insert(0, r"E:\WoW-mods\mod-limit-break\tools\m2port")
import m2  # noqa: E402

NAME = "staff_2h_artifactmonkeyking_d_03"


def turn(v):
    return (-v[0], v[1], -v[2])


def turn_box(raw, at):
    lo = struct.unpack_from("<3f", raw, at)
    hi = struct.unpack_from("<3f", raw, at + 12)
    return raw[:at] + struct.pack("<6f", -hi[0], lo[1], -hi[2], -lo[0], hi[1], -lo[2]) + raw[at + 24:]


def turn_track(tr, kind):
    for seq in tr["values"]:
        for i, v in enumerate(seq):
            if kind == "vec3":
                seq[i] = turn(v)
            else:                                  # compressé à la 3.3.5 : c >= 0 vaut (c - 32767) / 32767, c < 0 (c + 32768) / 32767
                seq[i] = (-1 - v[0], v[1], -1 - v[2], v[3])     # l'opposé exact


def rotate_m2(m, skin):
    for v in m["vertices"]:
        raw = bytearray(v["raw"])
        for at in (0, 20):                         # la position, puis la normale
            struct.pack_into("<3f", raw, at, *turn(struct.unpack_from("<3f", raw, at)))
        v["raw"] = bytes(raw)
    for b in m["bones"]:
        b["pivot"] = turn(b["pivot"])
        turn_track(b["translation"], "vec3")
        turn_track(b["rotation"], "compquat")
    for k in ("attachments", "events", "particle_emitters"):
        for a in m[k]:
            a["position"] = turn(a["position"])
    for k in ("lights", "ribbon_emitters", "cameras", "collision_positions"):
        assert not m[k], k
    m["boxes"] = turn_box(turn_box(m["boxes"], 0), 28)
    for s in m["sequences"]:
        s["bounds"] = turn_box(s["bounds"], 0)
    for sm in skin["submeshes"]:
        sm["center"] = turn(sm["center"])
        sm["sort_center"] = turn(sm["sort_center"])


FRAMES = {"SHJ2": 124, "REV2": 120, "WLJ3": 116}   # deux repères de 4 vecteurs en tête de chaque articulation


def rotate_phys(d):
    out = bytearray(d)
    o = 0
    while o + 8 <= len(d):
        cid = d[o:o + 4][::-1].decode()
        size = struct.unpack_from("<I", d, o + 4)[0]
        at = o + 8
        vecs = []
        if cid == "CAPS":                          # 28 octets : deux extrémités, un rayon
            vecs = [at + 28 * i + k for i in range(size // 28) for k in (0, 12)]
        elif cid == "BDY4":                        # 48 octets : type, os, position…
            vecs = [at + 48 * i + 4 for i in range(size // 48)]
        elif cid in FRAMES:
            n = FRAMES[cid]
            vecs = [at + n * i + 12 * k for i in range(size // n) for k in range(8)]
        else:
            assert cid in ("PHYS", "PHYT", "SHP2", "JOIN"), cid   # sans vecteur (PLYT : à traiter s'il en venait)
        for p in vecs:
            struct.pack_into("<3f", out, p, *turn(struct.unpack_from("<3f", d, p)))
        o = at + size
    return bytes(out)


def main():
    work = sys.argv[1]
    src, dst = os.path.join(work, "ported_orig"), os.path.join(work, "ported")
    m, extra = m2.read_file(open(os.path.join(src, NAME + ".m2"), "rb").read())
    assert not extra and m["num_skin"] == 1
    skin = m2.read_skin(open(os.path.join(src, NAME + "00.skin"), "rb").read())
    rotate_m2(m, skin)
    open(os.path.join(dst, NAME + ".m2"), "wb").write(m2.write(m))
    open(os.path.join(dst, NAME + "00.skin"), "wb").write(m2.write_skin(skin))
    open(os.path.join(dst, NAME + ".phys"), "wb").write(rotate_phys(open(os.path.join(src, NAME + ".phys"), "rb").read()))
    print("écrits :", NAME + ".m2", NAME + "00.skin", NAME + ".phys", "(demi-tour autour de y)")


if __name__ == "__main__":
    main()
