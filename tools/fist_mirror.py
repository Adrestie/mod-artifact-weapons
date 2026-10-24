"""Le poing gauche de Tian Feng (84038) : copie miroir de hand_1h_artifactskywall_d_06 (Maitre, 24/10/2026 23:25 UTC ;
le retail n'a pas de modèle gauche, ses seuls fichiers « _l » sont des présentoirs).

    python tools/fist_mirror.py <dossier de travail>      (lit ported/, y écrit hand_1h_artifactskywall_d_06_l.m2 et sa skin)

Le plan du miroir est x = 0 : x est l'axe pouce-auriculaire de l'arme (ses attaches 0 et 1 sont une paire symétrique en x) ;
y (paume-dos) et z (la longueur) gardent la lame du bon côté. Changent de signe en x : sommets et normales, pivots et
translations des os, points d'attache, événements, boîtes (du modèle et des séquences), centres des sous-maillages ; les
rotations des os deviennent (x, -y, -z, w) ; l'ordre de chaque triangle est inversé pour que ses faces restent dehors.
Les transformations de texture (des UV) ne bougent pas.
"""
import os, struct, sys
sys.path.insert(0, r"E:\WoW-mods\mod-limit-break\tools\m2port")
import m2

NAME = "hand_1h_artifactskywall_d_06"
LEFT = NAME + "_l"


def flip(v):
    return (-v[0],) + tuple(v[1:])


def flip_box(raw, at):
    """une boîte (min xyz, max xyz) à l'octet at de raw"""
    lo = struct.unpack_from("<3f", raw, at)
    hi = struct.unpack_from("<3f", raw, at + 12)
    return raw[:at] + struct.pack("<6f", -hi[0], lo[1], lo[2], -lo[0], hi[1], hi[2]) + raw[at + 24:]


def flip_track(tr, kind):
    for seq in tr["values"]:
        for i, v in enumerate(seq):
            if kind == "vec3":
                seq[i] = flip(v)
            else:                                  # quat ou compquat : (x, y, z, w) -> (x, -y, -z, w)
                y, z = -v[1], -v[2]
                if kind == "compquat":
                    y, z = max(-32767, min(32767, y)), max(-32767, min(32767, z))
                seq[i] = (v[0], y, z, v[3])


def mirror(m, skin):
    m["name"] = LEFT.encode() + b"\0"
    for v in m["vertices"]:
        raw = bytearray(v["raw"])
        for at in (0, 20):                         # la position, puis la normale
            x = struct.unpack_from("<f", raw, at)[0]
            struct.pack_into("<f", raw, at, -x)
        v["raw"] = bytes(raw)
    for b in m["bones"]:
        b["pivot"] = flip(b["pivot"])
        flip_track(b["translation"], "vec3")
        flip_track(b["rotation"], "compquat")
    for a in m["attachments"]:
        a["position"] = flip(a["position"])
    for e in m["events"]:
        e["position"] = flip(e["position"])
    for k in ("lights", "ribbon_emitters", "particle_emitters", "cameras", "collision_positions"):
        assert not m[k], k                         # rien de tel dans ce modèle ; à traiter s'il en venait
    m["boxes"] = flip_box(flip_box(m["boxes"], 0), 28)
    for s in m["sequences"]:
        s["bounds"] = flip_box(s["bounds"], 0)
    ind = skin["indices"]
    for t in range(0, len(ind), 3):
        ind[t + 1], ind[t + 2] = ind[t + 2], ind[t + 1]
    for sm in skin["submeshes"]:
        sm["center"] = flip(sm["center"])
        sm["sort_center"] = flip(sm["sort_center"])


def main():
    d = os.path.join(sys.argv[1], "ported")
    m, extra = m2.read_file(open(os.path.join(d, NAME + ".m2"), "rb").read())
    assert not extra and m["num_skin"] == 1
    skin = m2.read_skin(open(os.path.join(d, NAME + "00.skin"), "rb").read())
    mirror(m, skin)
    open(os.path.join(d, LEFT + ".m2"), "wb").write(m2.write(m))
    open(os.path.join(d, LEFT + "00.skin"), "wb").write(m2.write_skin(skin))
    print("écrits :", LEFT + ".m2", LEFT + "00.skin")


if __name__ == "__main__":
    main()
