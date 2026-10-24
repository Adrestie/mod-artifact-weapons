"""L'image d'une quête d'arme (512 x 512, BLP2 DXT1 sans alpha avec mipmaps, filtre « cristallisé » comme les 32 autres) fabriquée depuis la carte du
monde du jeu, centrée sur le lieu du PNJ. Image provisoire : une capture d'écran du lieu la remplace en passant
--capture (elle reçoit alors le même filtre).

    python tools/quest_picture.py <sortie.blp> <carte> <x> <y> <nom de zone WorldMapArea> [--capture image.png]

Lit le client 3.3.5 (ses archives et celles de enUS, dans l'ordre du jeu, la dernière qui a le fichier gagne) : WorldMapArea.dbc, puis
les 12 tuiles de la zone (Interface\\WorldMap\\<zone>\\<zone>1..12.blp, 4 x 3 tuiles de 256, la carte sur 1002 x 668).
"""
import io
import os
import random
import struct
import sys

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "installer"))
from mpq_archive import Archive  # noqa: E402

CLIENT = r"E:\world of warcraft 3.3.5a hd\Data"
SIZE = 512
CELL = 9            # taille moyenne d'une facette du filtre, en pixels


def archives():
    def order(path):
        base = os.path.basename(path).lower()[:-4]
        if base in ("common", "common-2", "expansion", "lichking"):
            return (0, base)
        if base == "patch":
            return (1, "")
        return (2, base.replace("patch-", ""))
    def locale_order(path):
        base = os.path.basename(path).lower()[:-4]
        return (0, base) if base.startswith(("locale-", "expansion-locale", "lichking-locale")) else (1, base)
    found = [os.path.join(CLIENT, n) for n in os.listdir(CLIENT) if n.lower().endswith(".mpq")]
    # the language's archives too (DBFilesClient), read after the common ones as the game does
    lang = os.path.join(CLIENT, "enus")
    local = [os.path.join(lang, n) for n in os.listdir(lang) if n.lower().endswith(".mpq")] if os.path.isdir(lang) else []
    return [Archive(p) for p in sorted(found, key=order)] + [Archive(p) for p in sorted(local, key=locale_order)]


def read(arcs, name):
    data = None
    for a in arcs:
        if a.contains(name):
            data = a.read(name)
    if data is None:
        raise SystemExit("%s absent du client" % name)
    return data


def world_map_area(arcs, zone):
    raw = read(arcs, "DBFilesClient\\WorldMapArea.dbc")
    n, f, size, ssize = struct.unpack_from("<4I", raw, 4)
    strings = raw[20 + n * size:]
    for i in range(n):
        row = struct.unpack_from("<4i4f3i", raw, 20 + i * size)
        name = strings[row[3]:strings.index(b"\0", row[3])].decode("utf-8")
        if name.lower() == zone.lower():
            return row
    raise SystemExit("zone %s absente de WorldMapArea.dbc" % zone)


def crystallize(image, seed):
    """des facettes de couleur unie (le filtre « Cristallisation » des images des 32 autres armes)"""
    rnd = random.Random(seed)
    w, h = image.size
    cols, rows = w // CELL + 2, h // CELL + 2
    pts = {(cx, cy): (cx * CELL + rnd.uniform(0, CELL), cy * CELL + rnd.uniform(0, CELL)) for cx in range(cols) for cy in range(rows)}
    src = image.load()
    owner = {}
    for y in range(h):
        for x in range(w):
            cx, cy = int(x // CELL), int(y // CELL)
            best, bd = None, 1e9
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    p = pts.get((cx + dx, cy + dy))
                    if p:
                        d = (p[0] - x) ** 2 + (p[1] - y) ** 2
                        if d < bd:
                            best, bd = (cx + dx, cy + dy), d
            owner.setdefault(best, []).append((x, y))
    out = Image.new("RGB", image.size)
    dst = out.load()
    for cell, pixels in owner.items():
        r = g = b = 0
        for x, y in pixels:
            pr, pg, pb = src[x, y][:3]
            r, g, b = r + pr, g + pg, b + pb
        k = len(pixels)
        colour = (r // k, g // k, b // k)
        for x, y in pixels:
            dst[x, y] = colour
    return out


def _dxt1(rgb):
    """les blocs DXT1 d'une image RGB (numpy, hauteur x largeur x 3, côtés multiples de 4) : deux couleurs extrêmes
    de chaque bloc 4 x 4 (sa plus sombre et sa plus claire), les quatre teintes entre elles, le texel à la plus proche"""
    import numpy as np
    h, w, _ = rgb.shape
    blocks = rgb.reshape(h // 4, 4, w // 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 3).astype(np.float32)
    lum = blocks @ np.array([0.299, 0.587, 0.114], np.float32)
    c0 = blocks[np.arange(len(blocks)), lum.argmax(1)]
    c1 = blocks[np.arange(len(blocks)), lum.argmin(1)]

    def to565(c):
        c = np.clip(np.rint(c), 0, 255).astype(np.uint32)
        return ((c[:, 0] >> 3) << 11) | ((c[:, 1] >> 2) << 5) | (c[:, 2] >> 3)

    def from565(v):
        return np.stack([((v >> 11) & 31) * 255 / 31, ((v >> 5) & 63) * 255 / 63, (v & 31) * 255 / 31], 1).astype(np.float32)
    v0, v1 = to565(c0), to565(c1)
    swap = v0 < v1
    v0, v1 = np.where(swap, v1, v0), np.where(swap, v0, v1)
    e0, e1 = from565(v0), from565(v1)
    palette = np.stack([e0, e1, (2 * e0 + e1) / 3, (e0 + 2 * e1) / 3], 1)              # mode 4 couleurs (v0 > v1)
    same = v0 == v1
    dist = ((blocks[:, :, None, :] - palette[:, None, :, :]) ** 2).sum(-1)
    index = dist.argmin(2).astype(np.uint32)
    index[same] = 0
    bits = (index << (2 * np.arange(16, dtype=np.uint32))).sum(1).astype(np.uint32)
    out = np.zeros((len(blocks), 2), np.uint32)
    out[:, 0] = v0 | (v1 << 16)
    out[:, 1] = bits
    return out.astype("<u4").tobytes()


def blp_rgb(image):
    """un BLP2 DXT1 sans alpha, avec ses mipmaps jusqu'à 1 x 1 (le format des images des 32 autres armes : encodage 2,
    profondeur d'alpha 0, mipmaps)"""
    import numpy as np
    w, h = image.size
    levels = []
    while True:
        level = image.resize((w, h), Image.LANCZOS) if levels else image
        pw, ph = max(4, w), max(4, h)
        canvas = Image.new("RGB", (pw, ph))
        canvas.paste(level, (0, 0))
        levels.append(_dxt1(np.asarray(canvas, dtype=np.uint8)))
        if w == 1 and h == 1:
            break
        w, h = max(1, w // 2), max(1, h // 2)
    header_size = 4 + 4 + 4 + 8 + 16 * 4 * 2 + 256 * 4
    offsets, sizes, at = [], [], header_size
    for data in levels:
        offsets.append(at)
        sizes.append(len(data))
        at += len(data)
    head = b"BLP2" + struct.pack("<I4B2I", 1, 2, 0, 0, 1, image.size[0], image.size[1])
    head += struct.pack("<16I", *(offsets + [0] * (16 - len(offsets))))
    head += struct.pack("<16I", *(sizes + [0] * (16 - len(sizes))))
    head += bytes(256 * 4)
    return head + b"".join(levels)


def main():
    args = sys.argv[1:]
    capture = None
    if "--capture" in args:
        i = args.index("--capture")
        capture = args[i + 1]
        del args[i:i + 2]
    out, map_id, x, y, zone = args[0], int(args[1]), float(args[2]), float(args[3]), args[4]
    if capture:
        picture = Image.open(capture).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
    else:
        arcs = archives()
        row = world_map_area(arcs, zone)
        if row[1] != map_id:
            raise SystemExit("zone %s : carte %d, pas %d" % (zone, row[1], map_id))
        left, right, top, bottom = row[4:8]
        u = (left - y) / (left - right)
        v = (top - x) / (top - bottom)
        canvas = Image.new("RGB", (1024, 768))
        for k in range(12):
            tile = Image.open(io.BytesIO(read(arcs, "Interface\\WorldMap\\%s\\%s%d.blp" % (zone, zone, k + 1)))).convert("RGB")
            canvas.paste(tile, ((k % 4) * 256, (k // 4) * 256))
        px, py = u * 1002, v * 668
        half = 160                                  # un tiers de la carte, agrandi à 512
        box = (int(px - half), int(py - half), int(px + half), int(py + half))
        dx = max(0, -box[0]) - max(0, box[2] - 1002)
        dy = max(0, -box[1]) - max(0, box[3] - 668)
        box = (box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy)
        picture = canvas.crop(box).resize((SIZE, SIZE), Image.LANCZOS)
    picture = crystallize(picture, out)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, "wb").write(blp_rgb(picture))
    picture.save(os.path.splitext(out)[0] + ".preview.png")
    print("%s : %d x %d" % (out, SIZE, SIZE))


if __name__ == "__main__":
    main()
