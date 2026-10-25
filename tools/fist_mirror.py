"""Le poing gauche de Tian Feng (84038) : copie miroir de hand_1h_artifactskywall_d_06 (Maitre, 24/10/2026 23:25 UTC ;
le retail n'a pas de modèle gauche, ses seuls fichiers « _l » sont des présentoirs).

    python tools/fist_mirror.py <dossier de travail> [x|y|z]   (lit ported/, y écrit hand_1h_artifactskywall_d_06_l.m2 et sa skin)

Le plan du miroir est y = 0 par défaut : le plan sagittal du personnage. Les objets portés suivent ses axes (x vers l'avant,
y vers sa gauche, z vers le haut), les attaches de 3.3.5 n'ont qu'une position, et le bras gauche s'anime en miroir du
droit : une arme vue en main gauche est donc celle de la main droite reflétée en y. La première version reflétait x (les
attaches 0 et 1 forment une paire en x) ; en jeu, le poing restait du mauvais côté (Maitre, 25/10/2026 23:44 UTC).
Changent de signe sur l'axe choisi : sommets et normales, pivots et translations des os, points d'attache, événements,
boîtes (du modèle et des séquences), centres des sous-maillages ; les rotations des os gardent la composante de l'axe et
changent le signe des deux autres ; l'ordre de chaque triangle est inversé pour que ses faces restent dehors. Les
transformations de texture (des UV) ne bougent pas.
"""
import os, struct, sys
sys.path.insert(0, r"E:\WoW-mods\mod-limit-break\tools\m2port")
import m2

NAME = "hand_1h_artifactskywall_d_06"
LEFT = NAME + "_l"


AXIS = 1                                       # 0 x, 1 y, 2 z : l'axe nié


def flip(v):
    v = list(v)
    v[AXIS] = -v[AXIS]
    return tuple(v)


def flip_box(raw, at):
    """une boîte (min xyz, max xyz) à l'octet at de raw"""
    lo = list(struct.unpack_from("<3f", raw, at))
    hi = list(struct.unpack_from("<3f", raw, at + 12))
    lo[AXIS], hi[AXIS] = -hi[AXIS], -lo[AXIS]
    return raw[:at] + struct.pack("<6f", *lo, *hi) + raw[at + 24:]


def flip_track(tr, kind):
    for seq in tr["values"]:
        for i, v in enumerate(seq):
            if kind == "vec3":
                seq[i] = flip(v)
            else:                                  # quat ou compquat : l'axe garde son signe, les deux autres le perdent
                q = [-c for c in v[:3]]
                q[AXIS] = v[AXIS]
                if kind == "compquat":
                    q = [max(-32767, min(32767, c)) for c in q]
                seq[i] = tuple(q) + (v[3],)


def mirror(m, skin):
    m["name"] = LEFT.encode() + b"\0"
    for v in m["vertices"]:
        raw = bytearray(v["raw"])
        for at in (0, 20):                         # la position, puis la normale
            c = struct.unpack_from("<f", raw, at + 4 * AXIS)[0]
            struct.pack_into("<f", raw, at + 4 * AXIS, -c)
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
    global AXIS
    if len(sys.argv) > 2:
        AXIS = "xyz".index(sys.argv[2])
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
