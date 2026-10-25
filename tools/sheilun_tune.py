"""Le nuage de Yu Wu (PNJ 84207) et son projectile (84963) réglés pour 3.3.5 (Maitre, 25/10/2026 10:54 UTC : les nuages sont
beaucoup trop gros et blancs ; le projectile doit être plus visible, couleur jade, pas blanc).

    python tools/sheilun_tune.py <dossier de travail>

Lit ported_sheilun_orig/ (les modèles tels que portés du retail, jamais modifiés), écrit ported_sheilun/.

7fx_monk_mistsofsheilun_statebase (Maitre, 11:54 UTC : « de petits nuages discrets, une sorte de brume, pas un point
vert brillant » ; 12:14 UTC : « les étincelles sont beaucoup trop grosses, il doit y avoir un truc à faire avec la brume
au niveau des UV et/ou du blending »). Sa brume (émetteur 0) mêle au retail trois textures (le champ texture 2080 : 0, 1
et 2), la volute grise qui donne la forme, l'énergie jade et le feu jade clairsemé qui défilent dedans ; 3.3.5 ne mêle
pas les textures d'une particule ni ne les fait défiler (le port gardait la volute seule, blanche et additive : un
point brillant). sheilun_mist_jade.blp est une feuille de 4 x 4 images : la volute portant les deux textures, décalées
d'un seizième de tour à chaque image, que la particule joue sur sa vie (head_cell 0 à 15). La brume passe en blend alpha
(elle voile au lieu de s'allumer), son opacité quadruplée. Ses « twinkle scale » (30, 60, 20), que 3.3.5 applique en
facteur de taille (un nuage de 9 m), passent à 3 pour la brume, 1,5 et 0,12 pour les étincelles (des points de 5 à
11 cm) ; et les particules, posées toutes au même point au retail, se répartissent sur 1,5 m.

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
BRUME_GRILLE = 4                       # la feuille : 4 x 4 images, jouées sur la vie de la particule
BRUME_CASE = 128                       # px, une image
BRUME_ALPHA = 4                        # l'opacité du retail (0,10 au plus), quadruplée : en blend alpha, rien ne s'ajoute


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
    """La feuille de la brume. Au retail, la volute (sa forme, son alpha) porte l'énergie jade et le feu jade
    clairsemé, qui défilent en UV ; 3.3.5 ne fait pas défiler la texture d'une particule, mais joue une feuille de
    sprites sur sa vie : chaque image décale les deux textures d'un seizième de tour."""
    d = os.path.join(work, "ported_sheilun")
    n, c = BRUME_GRILLE, BRUME_CASE

    def load(f):
        return Image.open(os.path.join(d, f)).convert("RGBA").resize((c, c), Image.BILINEAR)
    vol = load("arc_center_wispy_tilt_980437.blp")
    jade = load("etherealenergy_jade_1362014.blp")
    feu = load("fieryenergy_golden_sparse_jade_1362015.blp")

    def decale(img, du, dv):                     # les deux textures se répètent (wrap) ; la volute non
        x, y = int(du * c) % c, int(dv * c) % c
        out = Image.new("RGBA", (c, c))
        for ox in (-c, 0):
            for oy in (-c, 0):
                out.paste(img, (x + ox, y + oy))
        return out
    feuille = Image.new("RGBA", (n * c, n * c), (0, 0, 0, 0))
    forme = [a for _, _, _, a in vol.getdata()]
    for k in range(n * n):
        t = k / float(n * n)
        jd = decale(jade, 0.0, t).getdata()
        fe = decale(feu, 0.25 * t, -0.5 * t).getdata()
        px = []
        for a, (r1, g1, b1, _), (r2, g2, b2, _) in zip(forme, jd, fe):
            lum = (r2 + g2 + b2) / 765.0
            k1 = (0.6 + lum) * 1.3
            px.append((min(255, int(r1 * k1)), min(255, int(g1 * k1)), min(255, int(b1 * k1)), int(a * (0.35 + 0.65 * lum))))
        img = Image.new("RGBA", (c, c))
        img.putdata(px)
        feuille.paste(img, ((k % n) * c, (k // n) * c))
    open(os.path.join(d, BRUME + ".blp"), "wb").write(write_blp(feuille))


def nuage(m):
    nom = "Spells\\ArtifactWeapons\\%s.blp" % BRUME
    m["textures"].append({"type": 0, "flags": 0, "filename": list(nom.encode() + b"\0")})
    for p, tw in zip(m["particle_emitters"], ((3.0, 3.0), (1.5, 1.5), (0.12, 0.12))):
        p["twinkle_scale"] = tw                    # les étincelles (1 et 2) : de petits points
        for k in ("area_length", "area_width"):
            p[k]["values"] = [[BRUME_AIRE for _ in seq] for seq in p[k]["values"]]
    p = m["particle_emitters"][0]
    p["texture"] = len(m["textures"]) - 1
    p["blend"] = 2                                 # alpha : une brume voile, elle ne s'allume pas
    p["rows"] = p["cols"] = BRUME_GRILLE
    p["head_cell"] = {"timestamps": [0, 32767], "values": [0, BRUME_GRILLE * BRUME_GRILLE - 1]}
    p["alpha_track"]["values"] = [min(32767, BRUME_ALPHA * a) for a in p["alpha_track"]["values"]]


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
