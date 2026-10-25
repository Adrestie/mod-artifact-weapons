"""Le nuage de Yu Wu (PNJ 84207) et son projectile (84963) réglés pour 3.3.5 (Maitre, 25/10/2026 10:54 UTC : les nuages sont
beaucoup trop gros et blancs ; le projectile doit être plus visible, couleur jade, pas blanc).

    python tools/sheilun_tune.py <dossier de travail>

Lit ported_sheilun_orig/ (les modèles tels que portés du retail, jamais modifiés), écrit ported_sheilun/.

7fx_monk_mistsofsheilun_statebase : ses trois émetteurs ont un « twinkle scale » de 30, 60 et 20, que 3.3.5 applique en
facteur de taille (le retail le lit avec des drapeaux que le port retire) : un nuage de 9 m. Ramené à 2, 4 et 1,33 (le
même rapport), la bouffée fait 60 cm, à hauteur de genou. Ses 60 particules additives, blanches, posées au même point,
saturent en blanc : 12 par seconde au lieu de 40, l'opacité doublée, et une teinte jade qui garde le rouge bas même
empilée.

monk_soothingmist_missile : particules jade à or puis blanc, un cœur de 150 particules par seconde, une traînée jade
sombre à 60 % : un point blanc. Tout passe au jade, le cœur à 30 par seconde, les particules deux fois plus grandes, la
traînée claire, opaque à 85 % et deux fois plus haute (elle dessine l'ondulation, SpellMissileMotion 84035).
"""
import os
import sys

sys.path.insert(0, r"E:\WoW-mods\mod-limit-break\tools\m2port")
import m2  # noqa: E402

JADE = (110.0, 255.0, 185.0)          # une couleur de particule (0-255), multipliée par la texture
JADE_SOMBRE = (40.0, 190.0, 130.0)


def track_scale(track, k):
    track["values"] = [tuple(c * k for c in v) for v in track["values"]]


def rate(p, k):
    p["emission_rate"]["values"] = [[v * k for v in seq] for seq in p["emission_rate"]["values"]]


def nuage(m):
    for p, tw in zip(m["particle_emitters"], ((2.0, 2.0), (4.0, 4.0), (4.0 / 3, 4.0 / 3))):
        p["twinkle_scale"] = tw
        p["color_track"]["values"] = [JADE if any(v) else v for v in p["color_track"]["values"]]
    p = m["particle_emitters"][0]                      # la bouffée qui dure : 40 particules par seconde, au même point
    rate(p, 0.3)
    p["alpha_track"]["values"] = [min(32767, 2 * a) for a in p["alpha_track"]["values"]]


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
    for name, fn in (("7fx_monk_mistsofsheilun_statebase", nuage), ("monk_soothingmist_missile", projectile)):
        m, extra = m2.read_file(open(os.path.join(work, "ported_sheilun_orig", name + ".m2"), "rb").read())
        assert not extra
        fn(m)
        open(os.path.join(work, "ported_sheilun", name + ".m2"), "wb").write(m2.write(m))
        print("écrit :", name + ".m2")


if __name__ == "__main__":
    main()
