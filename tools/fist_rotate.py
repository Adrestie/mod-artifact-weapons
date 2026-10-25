"""Le poing de Tian Lei (84037) tourné dans la prise : hand_1h_artifactskywall_d_06 pivote autour de l'axe x de l'arme
(Maitre, 25/10/2026 10:53 UTC : tel quel, la lame penche vers l'intérieur et la garde touche la cible ; reflété, elle
penche autant vers l'extérieur). La lame pointe vers -z et penche de +0,19 en y : une rotation d'environ -11° autour
de x la ramène droit devant. La copie gauche se fait ensuite par tools/fist_mirror.py, à partir du poing tourné.

    python tools/fist_rotate.py <dossier de travail> <angle en degrés>

Lit ported_orig/hand_1h_artifactskywall_d_06.m2 et sa skin (le poing porté du retail, jamais modifié), écrit le poing
tourné dans ported/. Le modèle n'a aucune clé d'animation (11 os immobiles) : tournent les sommets et leurs normales,
les pivots des os, les points d'attache, les événements ; les boîtes sont recalculées sur les sommets tournés.
"""
import math
import os
import shutil
import struct
import sys

sys.path.insert(0, r"E:\WoW-mods\mod-limit-break\tools\m2port")
import m2  # noqa: E402

NAME = "hand_1h_artifactskywall_d_06"


def rotation(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)

    def rot(v):
        x, y, z = v
        return (x, y * c - z * s, y * s + z * c)
    return rot


def rotate(m, rot):
    for b in m["bones"]:
        for k in ("translation", "rotation", "scale"):
            assert not any(b[k]["values"]), "os animé : à traiter"
        b["pivot"] = rot(b["pivot"])
    pts = []
    for v in m["vertices"]:
        raw = bytearray(v["raw"])
        for at in (0, 20):                                  # la position, puis la normale
            p = rot(struct.unpack_from("<3f", raw, at))
            struct.pack_into("<3f", raw, at, *p)
            if at == 0:
                pts.append(p)
        v["raw"] = bytes(raw)
    for a in m["attachments"]:
        a["position"] = rot(a["position"])
    for e in m["events"]:
        e["position"] = rot(e["position"])
    for k in ("lights", "ribbon_emitters", "particle_emitters", "cameras", "collision_positions"):
        assert not m[k], k
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    radius = max(math.sqrt(sum(c * c for c in p)) for p in pts)
    raw = bytearray(m["boxes"])
    struct.pack_into("<6ff", raw, 0, *lo, *hi, radius)          # la boîte du modèle et son rayon
    struct.pack_into("<6ff", raw, 28, *lo, *hi, radius)         # celle des collisions
    m["boxes"] = bytes(raw)


def main():
    work, deg = sys.argv[1], float(sys.argv[2])
    src = os.path.join(work, "ported_orig")
    dst = os.path.join(work, "ported")
    m, extra = m2.read_file(open(os.path.join(src, NAME + ".m2"), "rb").read())
    assert not extra and m["num_skin"] == 1
    rotate(m, rotation(deg))
    open(os.path.join(dst, NAME + ".m2"), "wb").write(m2.write(m))
    shutil.copyfile(os.path.join(src, NAME + "00.skin"), os.path.join(dst, NAME + "00.skin"))
    print("écrit :", NAME + ".m2", "tourné de %.1f° autour de x" % deg)


if __name__ == "__main__":
    main()
