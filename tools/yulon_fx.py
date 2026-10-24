"""Yu'lon (pandarenserpentgod.m2 de MoP Classic, converti par m2port) pour les Brumes de Yu Wu (Maitre, 24/10/2026
22:17 UTC : la peau verte, un shader transparent de type Fresnel, la moitié de sa taille).

    python tools/yulon_fx.py <dossier de travail>      (lit ported_yulon/ et export_yulon/, écrit yulon_final/)

- la lueur du corps rendue : le batch du corps de MoP (shader d'effet 0x8006 : la peau, type 11, puis sa lueur, type 12)
  n'a gardé que sa première texture à la conversion ; la lueur redevient une couche additive ;
- la transparence : le corps en mélange alpha, à BODY_ALPHA ;
- le Fresnel : 3.3.5 n'a pas de shader Fresnel ; le plus proche, une couche en carte d'environnement (la convention de
  Blizzard, prouvée en jeu par l'atelier VFX : batch de couche 1, ses drapeaux 0x10, sa combinaison de coordonnées sur
  l'entrée -1 de texture_unit_lookup, mélange 4, matériau 0x13) d'un anneau noir au centre et clair au bord : ce qui
  fait face à l'œil reste transparent, la silhouette brille en vert ;
- la taille : l'échelle de CreatureDisplayInfo (0,5, tools/monk_part.py), pas le modèle.
"""
import math, os, struct, sys
sys.path.insert(0, r"E:\WoW-mods\mod-limit-break\tools\m2port")
sys.path.insert(0, r"E:\WoW-mods\mod-custom-classes\tools")
import m2
from PIL import Image

W = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(W, "ported_yulon")
OUT = os.path.join(W, "yulon_final")
GAMEDIR = "Creature\\PandarenSerpentGod"
RING = "yulon_fresnel_ring"
BODY_ALPHA = 0.40          # the body's opacity where it faces the eye
RING_SIZE = 128


def blp_rgba(image):
    """a BLP2, uncompressed palette with 8-bit alpha (ccgen.talents.blp2's layout)"""
    from ccgen.talents import blp2
    return blp2(image)


def ring_texture(green):
    im = Image.new("RGBA", (RING_SIZE, RING_SIZE))
    px = im.load()
    c = RING_SIZE / 2.0
    for y in range(RING_SIZE):
        for x in range(RING_SIZE):
            r = math.hypot(x + 0.5 - c, y + 0.5 - c) / c
            f = 0.0 if r < 0.45 else min(1.0, ((r - 0.45) / 0.50) ** 2)
            px[x, y] = tuple(int(v * f) for v in green) + (255,)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    b = open(os.path.join(SRC, "pandarenserpentgod.m2"), "rb").read()
    m = m2.read_md20(b)
    skin = m2.read_skin(open(os.path.join(SRC, "pandarenserpentgod00.skin"), "rb").read())

    # the ring's green: the green skin's mean colour, brightened
    skin_tex = Image.open(os.path.join(W, "export_yulon", "spells", "pandarenserpentgod_green.blp")).convert("RGB").resize((64, 64))
    pixels = list(skin_tex.getdata())
    mean = [sum(p[i] for p in pixels) / len(pixels) for i in range(3)]
    k = 255.0 / max(mean)
    green = tuple(min(255, int(v * k)) for v in mean)
    open(os.path.join(OUT, RING + ".blp"), "wb").write(blp_rgba(ring_texture(green)))

    # textures: the ring, a file of the model's folder
    ring_index = len(m["textures"])
    m["textures"].append({"type": 0, "flags": 0, "filename": list((GAMEDIR + "\\" + RING + ".blp").encode("ascii") + b"\0")})
    glow_index = next(i for i, t in enumerate(m["textures"]) if t["type"] == 12)
    lookup = m["texture_lookup"]
    lookup += [glow_index, ring_index]
    glow_lu, ring_lu = len(lookup) - 2, len(lookup) - 1
    # texture coordinates: -1, the environment map
    m["texture_unit_lookup"].append(-1)
    env_lu = len(m["texture_unit_lookup"]) - 1
    # the body's transparency: a texture weight of BODY_ALPHA
    m["texture_weights"].append({"weight": {"interpolation": 0, "global_sequence": -1, "timestamps": [[0]],
                                            "values": [[int(32767 * BODY_ALPHA)]]}})
    m["transparency_lookup"].append(len(m["texture_weights"]) - 1)
    body_alpha_lu = len(m["transparency_lookup"]) - 1
    # materials: the body alpha-blended; the glow and the ring added, unlit, unfogged, no depth write
    m["materials"].append({"flags": 0x0, "blend": 2})
    body_mat = len(m["materials"]) - 1
    m["materials"].append({"flags": 0x1 | 0x2 | 0x10, "blend": 4})
    add_mat = len(m["materials"]) - 1
    # a transform lookup entry with no animation
    tt = m["texture_transform_lookup"]
    if -1 not in tt:
        tt.append(-1)
    no_tr = tt.index(-1)

    body = [bt for bt in skin["batches"] if m["texture_lookup"][bt["texture_combo"]] == 0 and bt["texture_count"] == 1]
    added = []
    for bt in body:
        bt["material"] = body_mat
        bt["weight_combo"] = body_alpha_lu
        # the Fresnel layer as the VFX workshop proved it in game (Blizzard's convention for an environment map): batch
        # layer 1, its batch flags 0x10, its coordinate combo the -1 entry of texture_unit_lookup, blend 4, material 0x13,
        # a sphere map black in its middle; the glow next, layer 2
        ring = dict(bt, layer=bt["layer"] + 1, flags=0x10, material=add_mat, texture_combo=ring_lu, coord_combo=env_lu, weight_combo=0,
                    transform_combo=no_tr, priority=bt["priority"] + 1)
        glow = dict(bt, layer=bt["layer"] + 2, material=add_mat, texture_combo=glow_lu, weight_combo=0, priority=bt["priority"] + 2)
        added += [glow, ring]
    # each submesh's batches together, in their layers' order
    skin["batches"] = sorted(skin["batches"] + added, key=lambda x: (x["submesh"], x["layer"]))

    open(os.path.join(OUT, "pandarenserpentgod.m2"), "wb").write(m2.write(m))
    open(os.path.join(OUT, "pandarenserpentgod00.skin"), "wb").write(m2.write_skin(skin))
    for f in os.listdir(SRC):
        if f.endswith(".blp"):
            open(os.path.join(OUT, f), "wb").write(open(os.path.join(SRC, f), "rb").read())
    for f in ("pandarenserpentgod_green.blp", "pandarenserpentgod_green_glow.blp"):
        open(os.path.join(OUT, f), "wb").write(open(os.path.join(W, "export_yulon", "spells", f), "rb").read())
    print("body batches", len(body), "layers added", len(added), "ring green", green)


if __name__ == "__main__":
    main()
