"""Le nuage de Yu Wu (PNJ 84207) et son projectile (84963) réglés pour 3.3.5 (Maitre, 25/10/2026 10:54 UTC : les nuages sont
beaucoup trop gros et blancs ; le projectile doit être plus visible, couleur jade, pas blanc).

    python tools/sheilun_tune.py <dossier de travail>

Lit ported_sheilun_orig/ (les modèles tels que portés du retail, jamais modifiés), écrit ported_sheilun/.

7fx_monk_mistsofsheilun_statebase (Maitre, 11:54 UTC : « de petits nuages discrets, une sorte de brume, pas un point
vert brillant ») : sa brume (émetteur 0) mêle au retail trois textures (le champ texture 2080 : 0, 1 et 2, la volute
grise, l'énergie jade, le feu jade clairsemé), que 3.3.5 ne sait pas mêler : le port gardait la volute grise seule,
blanche et additive. Le mélange est cuit dans une texture à nous (sheilun_mist_jade.blp : le produit des trois, x8) et
les valeurs du retail reviennent (couleur blanche, 40 par seconde, opacité). Ses « twinkle scale » (30, 60, 20), que
3.3.5 applique en facteur de taille (un nuage de 9 m), passent à 3, 4 et 0,7 ; et les particules, posées toutes au même
point au retail, se répartissent sur 1,5 m : quelques bouffées basses d'environ un mètre. Les deux éclats de fin de
boucle (émetteurs 1 et 2) gardent leurs couleurs du retail.

monk_soothingmist_missile : particules jade à or puis blanc, un cœur de 150 particules par seconde, une traînée jade
sombre à 60 % : un point blanc. Tout passe au jade, le cœur à 30 par seconde, les particules deux fois plus grandes, la
traînée claire, opaque à 85 % et deux fois plus haute (elle dessine l'ondulation, SpellMissileMotion 84035).
"""
import os
import struct
import sys

from PIL import Image

sys.path.insert(0, r"E:\WoW-mods\mod-limit-break\tools\m2port")
import m2  # noqa: E402

JADE = (110.0, 255.0, 185.0)          # une couleur de particule (0-255), multipliée par la texture
JADE_SOMBRE = (40.0, 190.0, 130.0)


def track_scale(track, k):
    track["values"] = [tuple(c * k for c in v) for v in track["values"]]


def rate(p, k):
    p["emission_rate"]["values"] = [[v * k for v in seq] for seq in p["emission_rate"]["values"]]


BRUME = "sheilun_mist_jade"
BRUME_AIRE = 1.5                       # m, la zone où naissent les particules
BRUME_GAIN = 8.0                       # le produit de trois textures est sombre


def write_blp(img):
    """BLP2 non compressée (BGRA 8888), avec ses niveaux de mip"""
    mips = [img]
    while min(mips[-1].size) > 1:
        mips.append(mips[-1].resize((max(1, mips[-1].size[0] // 2), max(1, mips[-1].size[1] // 2)), Image.BILINEAR))
    w, h = img.size
    header = struct.pack("<4sIBBBBII", b"BLP2", 1, 3, 8, 8, 1, w, h)
    offsets, sizes, body = [0] * 16, [0] * 16, b""
    start = len(header) + 64 + 64 + 1024
    for k, mip in enumerate(mips[:16]):
        r, g, b, a = mip.split()
        data = Image.merge("RGBA", (b, g, r, a)).tobytes()
        offsets[k], sizes[k] = start + len(body), len(data)
        body += data
    return header + struct.pack("<16I", *offsets) + struct.pack("<16I", *sizes) + bytes(1024) + body


def brume(work):
    """la volute x l'énergie jade x le feu jade clairsemé, l'alpha de la volute"""
    d = os.path.join(work, "ported_sheilun")

    def load(f):
        return Image.open(os.path.join(d, f)).convert("RGBA").resize((256, 256), Image.BILINEAR)
    vol = load("arc_center_wispy_tilt_980437.blp")
    jade = load("etherealenergy_jade_1362014.blp")
    feu = load("fieryenergy_golden_sparse_jade_1362015.blp")
    px = []
    for (r1, g1, b1, a1), (r2, g2, b2, _), (r3, g3, b3, _) in zip(vol.getdata(), jade.getdata(), feu.getdata()):
        px.append(tuple(min(255, int(x * y * z / 65025.0 * BRUME_GAIN)) for x, y, z in ((r1, r2, r3), (g1, g2, g3), (b1, b2, b3))) + (a1,))
    out = Image.new("RGBA", (256, 256))
    out.putdata(px)
    open(os.path.join(d, BRUME + ".blp"), "wb").write(write_blp(out))


def nuage(m):
    m["textures"].append({"type": 0, "flags": 0, "filename": list(("Spells\\ArtifactWeapons\\%s.blp" % BRUME).encode() + b"\0")})
    for p, tw in zip(m["particle_emitters"], ((3.0, 3.0), (4.0, 4.0), (0.7, 0.7))):
        p["twinkle_scale"] = tw
        for k in ("area_length", "area_width"):
            p[k]["values"] = [[BRUME_AIRE for _ in seq] for seq in p[k]["values"]]
    m["particle_emitters"][0]["texture"] = len(m["textures"]) - 1


def projectile(m):
    for i, p in enumerate(m["particle_emitters"]):
        n = len(p["color_track"]["values"])
        p["color_track"]["values"] = [JADE_SOMBRE if k == 0 else JADE for k in range(n)]
        track_scale(p["scale_track"], 2.0)
        if i == 2:                                     # le cœur : 150 particules par seconde, empilées
            rate(p, 0.2)
            p["alpha_track"]["values"] = [min(32767, 2 * a) for a in p["alpha_track"]["values"]]
    r = m["ribbon_emitters"][0]
    r["color"]["values"] = [[(0.3, 1.0, 0.7)]]
    r["alpha"]["values"] = [[27852]]                   # 85 %
    for k in ("height_above", "height_below"):
        r[k]["values"] = [[v * 2 for v in seq] for seq in r[k]["values"]]


def main():
    work = sys.argv[1]
    brume(work)
    for name, fn in (("7fx_monk_mistsofsheilun_statebase", nuage), ("monk_soothingmist_missile", projectile)):
        m, extra = m2.read_file(open(os.path.join(work, "ported_sheilun_orig", name + ".m2"), "rb").read())
        assert not extra
        fn(m)
        open(os.path.join(work, "ported_sheilun", name + ".m2"), "wb").write(m2.write(m))
        print("écrit :", name + ".m2")


if __name__ == "__main__":
    main()
