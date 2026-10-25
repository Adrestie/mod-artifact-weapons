"""La partie « Moine » de mod-artifact-weapons (data/parts/monk) : les trois armes artefacts du Moine de
mod-custom-classes (classe 10), installées seulement quand la classe 10 existe (clé « parts » de l'installeur,
condition classes [10]). Cahier validé par Maitre le 24/10/2026 22:02 UTC (fil mod-artifact-weapons).

    python tools/monk_part.py <dossier de travail>

<dossier de travail> : les modèles déjà convertis pour 3.3.5 (m2port : port.py puis validate.py) et leurs textures,
dans les sous-dossiers ported/ (les armes), yulon_final/ (Yu'lon), ported_crane/ (la grue), export/tex/ (les peaux
choisies et les icônes), pictures/ (les images des quêtes, tools/quest_picture.py), ported_sheilun/ (les modèles de sorts
portés par m2port : le nuage du Don de Sheilun, le projectile de brume, la lame de vent ; écrits sous Spells/ArtifactWeapons).

Les visuels de sorts (SpellVisual, SpellVisualKit, SpellVisualEffectName) partent des lignes du CLIENT (son patch-Z) :
c'est lui qui les joue, et ses kits diffèrent de ceux du serveur. Aucun kit d'avant-incantation ni d'incantation emprunté
n'est gardé : leurs animations (51 à 54) ont WeaponFlags 4, qui range les armes, et un poing rangé disparaît. Seul le Don
de Yu Wu en a, avec BattleRoar (55, WeaponFlags 0) : le Moine brandit son bâton.

Écrit data/parts/monk/ : installer.json (les lignes DBC : Spell, Item, ItemDisplayInfo, ItemSet, CreatureDisplayInfo,
CreatureModelData ; les lignes de base à retirer), data/sql/world/mod-artifact-weapons--monk_world.sql et
data/client/ (modèles, textures, icônes, images des quêtes).

Les sorts du Moine visés sont ceux de mod-custom-classes (version installée affc0a8) : Paume du tigre 81113,
Poings de fureur 81198, Brume apaisante 81771 et celle de la statue 81896, les breuvages (src/monk_weapons.cpp).

PROVISOIRE : les images des quêtes que Maitre n'a pas encore validées (tools/quest_picture.py, depuis la carte du monde).
"""
import json
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PART = os.path.join(ROOT, "data", "parts", "monk")
sys.path.insert(0, r"E:\WoW-mods\mod-custom-classes\tools")
from ccgen import dbc as dbclib                     # noqa: E402
from ccgen.spell import FIELD, SPELL_LAYOUT         # noqa: E402
from ccgen.transform import localized               # noqa: E402

SERVER_DBC = r"C:\Users\Arthe\Documents\Serveur WoW\server_test\bin\RelWithDebInfo\Data\dbc"
BASE_SQL = os.path.join(ROOT, "data", "sql", "db-world", "base")
LANGS = ("enUS", "frFR", "deDE", "esES", "ruRU")
LOCALES = ("frFR", "deDE", "esES", "ruRU")
MONK = 10
MONK_MASK = 1 << (MONK - 1)                          # 512 (le 1535 des autres armes exclut la classe 10)
OX_STANCE = 23                                      # forme de la posture du Buffle (mod-custom-classes "forms")

# ------------------------------------------------------------------ identifiants (cahier, ID_RANGES.md tranche 84)
YUWU, JINGU, TIANLEI, TIANFENG = 84035, 84036, 84037, 84038
BOOK = {YUWU: 84135, JINGU: 84136, TIANLEI: 84137, TIANFENG: 84138}
QUEST = {YUWU: 84035, JINGU: 84036, TIANLEI: 84037, TIANFENG: 84038}       # quête et PNJ ont le même numéro
ITEMSET = 84037                                     # Poings des Cieux (ItemSet.dbc)
NPC_YULON, NPC_CRANE = 84205, 84206                 # créatures invoquées ; leurs affichages et modèles du même numéro
NPC_CLOUD = 84207                                   # un Nuage de brume de Yu Wu au sol, vu du seul Moine (src/monk_weapons.cpp) ;
                                                    # son affichage, du même numéro : le nuage du Don de Sheilun (retail)
SPAWN_GUID = {YUWU: 8400035, JINGU: 8400036, TIANLEI: 8400037, TIANFENG: 8400038}
# les sorts
S_GIFT, S_CLOUD, S_GIFT_USE = 84960, 84961, 84962
S_MISTS, S_YULON = 84964, 84965
S_WHISPERS, S_WHISPERS_HEAL = 84966, 84967
S_KEG, S_KEG_MISS = 84980, 84981
S_FACEPALM, S_FORTIF = 84982, 84983
S_THUNDER, S_THUNDER_BUFF, S_THUNDER_HIT = 84920, 84921, 84922
S_CROSSWINDS, S_CRANE, S_CRANE_PULSE = 84460, 84461, 84462
S_WINDBLADES, S_WINDBLADES_HIT = 84463, 84464                  # Lames de vent (Tian Feng), choisies le 25/10 à la place de l'ensemble
S_STORM, S_STORM_CHARGE, S_STORM_STRIKE = 84923, 84924, 84925  # Orage intérieur (Tian Lei)
S_CLOUD_MISSILE = 84963                                         # un nuage aspiré par le Don, en projectile
# les visuels de la partie (SpellVisual, SpellVisualKit, SpellVisualEffectName : tranche 84, 84035 à 84049)
VIS_DON, VIS_NUAGE, VIS_TONNERRE, VIS_LAMES, VIS_ORAGE, VIS_GRUE, VIS_FUT, VIS_MURMURES = range(84035, 84043)
KIT_DON_PRE, KIT_DON_CAST, KIT_GRUE = 84035, 84036, 84037
EFF_NUAGE, EFF_LAMES = 84035, 84036
VISUAL_IDS = [84035, 84049]
ANIM_BATTLEROAR = 55                                            # WeaponFlags 0 : l'arme reste en main
NUAGE_VITESSE = 20.0                                            # m/s, le projectile du nuage (src/monk_weapons.cpp le lit)
CLIENT = r"E:\world of warcraft 3.3.5a hd"
SPELL_BLOCKS = [[84460, 84479], [84920, 84939], [84960, 84999]]

# les PNJ des quêtes : la plante des 32 autres armes (affichage 8391) et un nom sur le modèle des leurs (les syllabes
# de Korogu, le russe en cyrillique ; Maitre, fil des armes, 24/10 22:54-22:56 UTC : Gokuro, Rukogo, Gurok'o, Okurog). Un PNJ par quête.
# leurs emplacements : ceux où Maitre les a posés sur le test (24/10/2026 23:10 UTC ; ses spawns 9700016-9700019),
# carte, zone, sous-zone, x, y, z, orientation
PNJ_DISPLAY = 8391
PNJ = {
    YUWU: {"name": {"enUS": "Gokuro", "frFR": "Gokuro", "deDE": "Gokuro", "esES": "Gokuro", "ruRU": "Гокуро"},
           "spot": (0, 41, 2562, -11189.447, -1859.662, 74.556, 0.5227)},                 # Défilé de Deuillevent, Karazhan (la tour)
    JINGU: {"name": {"enUS": "Rukogo", "frFR": "Rukogo", "deDE": "Rukogo", "esES": "Rukogo", "ruRU": "Рукого"},
            "spot": (530, 3540, 3540, 1779.906, 2360.698, 25.028, 0.834)},                 # Le Néant distordu (le bateau)
    TIANLEI: {"name": {"enUS": "Gurok'o", "frFR": "Gurok'o", "deDE": "Gurok'o", "esES": "Gurok'o", "ruRU": "Гурок'о"},
              "spot": (571, 67, 4430, 7476.672, -586.118, 1968.066, 2.3045)},              # Les pics Foudroyés, Temple des Tempêtes (la rotonde)
    TIANFENG: {"name": {"enUS": "Okurog", "frFR": "Okurog", "deDE": "Okurog", "esES": "Okurog", "ruRU": "Окурог"},
               "spot": (530, 3483, 3483, 78.913, 700.733, -4.776, 2.0593)},                 # Péninsule des Flammes infernales (la porte)
}

# ------------------------------------------------------------------ textes
ITEMS = {
    YUWU: {"name": {"enUS": "Yu Wu, Staff of the Mists", "frFR": "Yu Wu, bâton des Brumes", "deDE": "Yu Wu, Stab der Nebel",
                       "esES": "Yu Wu, bastón de las Brumas", "ruRU": "Юй У, посох Туманов"},
              "desc": {"enUS": "The mists of the Jade Serpent gather around its head, waiting for a wound to close.",
                       "frFR": "Les brumes du Serpent de jade s’amassent autour de sa tête, dans l’attente d’une blessure à refermer.",
                       "deDE": "Die Nebel der Jadeschlange sammeln sich um seinen Kopf und warten auf eine Wunde, die sie schließen können.",
                       "esES": "Las brumas del Dragón de Jade se acumulan en torno a su cabeza, a la espera de una herida que cerrar.",
                       "ruRU": "Туманы Нефритовой Змеи клубятся вокруг его навершия в ожидании раны, которую нужно затянуть."}},
    JINGU: {"name": {"enUS": "Jin Gu, Staff of the Monkey King", "frFR": "Jin Gu, bâton du Roi-Singe", "deDE": "Jin Gu, Stab des Affenkönigs",
                     "esES": "Jin Gu, bastón del Rey Mono", "ruRU": "Цзинь Гу, посох Короля обезьян"},
            "desc": {"enUS": "Its wood still smells of the brew the Monkey King spilled on it, laughing.",
                     "frFR": "Son bois sent encore le breuvage que le Roi-Singe y a renversé en riant.",
                     "deDE": "Sein Holz riecht noch nach dem Gebräu, das der Affenkönig lachend darüber verschüttet hat.",
                     "esES": "Su madera aún huele al brebaje que el Rey Mono derramó sobre ella entre risas.",
                     "ruRU": "Его древко до сих пор пахнет хмелем, который со смехом пролил на него Король обезьян."}},
    TIANLEI: {"name": {"enUS": "Tian Lei, Fist of the Heavenly Lightning", "frFR": "Tian Lei, Poing de la Foudre céleste",
                       "deDE": "Tian Lei, Faust des Himmelsblitzes", "esES": "Tian Lei, Puño del Rayo celestial",
                       "ruRU": "Тянь Лэй, Кулак Небесной молнии"},
              "desc": {"enUS": "The right fist of the Heavens. Thunder rumbles in it before every blow.",
                       "frFR": "Le poing droit des Cieux. Le tonnerre y gronde avant chaque coup.",
                       "deDE": "Die rechte Faust der Himmel. Vor jedem Schlag grollt darin der Donner.",
                       "esES": "El puño derecho de los Cielos. El trueno retumba en él antes de cada golpe.",
                       "ruRU": "Правый кулак Небес. Перед каждым ударом в нем рокочет гром."}},
    TIANFENG: {"name": {"enUS": "Tian Feng, Fist of the Heavenly Wind", "frFR": "Tian Feng, Poing du Vent céleste",
                        "deDE": "Tian Feng, Faust des Himmelswindes", "esES": "Tian Feng, Puño del Viento celestial",
                        "ruRU": "Тянь Фэн, Кулак Небесного ветра"},
               "desc": {"enUS": "The left fist of the Heavens. The wind follows it wherever it strikes.",
                        "frFR": "Le poing gauche des Cieux. Le vent le suit partout où il frappe.",
                        "deDE": "Die linke Faust der Himmel. Der Wind folgt ihr, wohin sie auch schlägt.",
                        "esES": "El puño izquierdo de los Cielos. El viento lo sigue allá donde golpea.",
                        "ruRU": "Левый кулак Небес. Ветер следует за ним, куда бы он ни ударил."}},
}
BOOKS = {
    YUWU: {"name": {"enUS": "Mist-Soaked Scroll", "frFR": "Rouleau trempé de brume", "deDE": "Nebelgetränkte Schriftrolle",
                       "esES": "Pergamino empapado de bruma", "ruRU": "Пропитанный туманом свиток"},
              "desc": {"enUS": "The ink runs as soon as you unroll it.", "frFR": "L’encre coule dès qu’on le déroule.",
                       "deDE": "Die Tinte verläuft, sobald Ihr sie aufrollt.", "esES": "La tinta se corre en cuanto lo desenrollas.",
                       "ruRU": "Чернила расплываются, стоит его развернуть."}, "display": 1246},
    JINGU: {"name": {"enUS": "Brew-Stained Recipe Book", "frFR": "Livre de recettes taché de bière", "deDE": "Biergetränktes Rezeptbuch",
                     "esES": "Recetario manchado de cerveza", "ruRU": "Залитая пивом книга рецептов"},
            "desc": {"enUS": "Every page smells of fermented rice.", "frFR": "Chaque page sent le riz fermenté.",
                     "deDE": "Jede Seite riecht nach vergorenem Reis.", "esES": "Cada página huele a arroz fermentado.",
                     "ruRU": "Каждая страница пахнет перебродившим рисом."}, "display": 1155},
    TIANLEI: {"name": {"enUS": "Storm-Torn Kite", "frFR": "Cerf-volant déchiré par l’orage", "deDE": "Vom Sturm zerrissener Drachen",
                       "esES": "Cometa rasgada por la tormenta", "ruRU": "Разорванный бурей воздушный змей"},
              "desc": {"enUS": "A picture is painted on what is left of its paper.", "frFR": "Une image est peinte sur ce qui reste de son papier.",
                       "deDE": "Auf dem, was von seinem Papier übrig ist, ist ein Bild gemalt.",
                       "esES": "Hay una imagen pintada en lo que queda de su papel.", "ruRU": "На уцелевшей бумаге нарисована картинка."},
              "display": 7139},
    TIANFENG: {"name": {"enUS": "Wind-Frayed Banner", "frFR": "Bannière effilochée par le vent", "deDE": "Vom Wind zerfranstes Banner",
                        "esES": "Estandarte deshilachado por el viento", "ruRU": "Истрепанное ветром знамя"},
               "desc": {"enUS": "A picture is still woven into the cloth.", "frFR": "Une image est encore tissée dans l’étoffe.",
                        "deDE": "In den Stoff ist noch ein Bild gewebt.", "esES": "Aún hay una imagen tejida en la tela.",
                        "ruRU": "В ткань все еще вплетена картинка."}, "display": 7695},
}
QUESTS = {
    YUWU: {"title": {"enUS": "The Song of the Waterfall", "frFR": "Le chant de la cascade", "deDE": "Das Lied des Wasserfalls",
                        "esES": "El canto de la cascada", "ruRU": "Песнь водопада"}},
    JINGU: {"title": {"enUS": "The Laughing Brewer", "frFR": "Le brasseur rieur", "deDE": "Der lachende Brauer",
                      "esES": "El cervecero risueño", "ruRU": "Смеющийся пивовар"}},
    TIANLEI: {"title": {"enUS": "Above the Storm", "frFR": "Au-dessus de l’orage", "deDE": "Über dem Sturm",
                        "esES": "Por encima de la tormenta", "ruRU": "Над бурей"}},
    TIANFENG: {"title": {"enUS": "Where the Wind Turns", "frFR": "Là où tourne le vent", "deDE": "Wo der Wind dreht",
                         "esES": "Donde gira el viento", "ruRU": "Там, где поворачивает ветер"}},
}
# les autres phrases des quêtes, celles des 32 autres (84026 : « The Wing of Penance »)
QUEST_DETAILS = {"enUS": "The book holds nothing but a faded picture of a place you feel you know...",
                 "frFR": "Le livre ne contient qu'une image dégradée d'un lieu que vous avez l'impression de connaître...",
                 "deDE": "Das Buch enthält nichts als ein verblasstes Bild eines Ortes, der Euch bekannt vorkommt...",
                 "esES": "El libro no contiene más que una imagen desvaída de un lugar que crees conocer...",
                 "ruRU": "В книге нет ничего, кроме выцветшего изображения места, которое кажется вам знакомым..."}
QUEST_OBJECTIVE = {"enUS": "Perhaps you should find the place shown in the book?",
                   "frFR": "Peut-être qu'il faut trouver le lieu indiqué dans le livre ?",
                   "deDE": "Vielleicht solltet Ihr den Ort finden, der im Buch abgebildet ist?",
                   "esES": "¿Quizá deberías encontrar el lugar que aparece en el libro?",
                   "ruRU": "Может быть, стоит найти место, изображенное в книге?"}
QUEST_REWARD = {"enUS": "You came a long way. The weapon has been waiting for you.",
                "frFR": "Tu as fait un long chemin. L'arme t'attendait.",
                "deDE": "Du hast einen weiten Weg hinter dir. Die Waffe hat auf dich gewartet.",
                "esES": "Has recorrido un largo camino. El arma te estaba esperando.",
                "ruRU": "Ты прошел долгий путь. Оружие ждало тебя."}

# ------------------------------------------------------------------ les sorts
# chaque sort : son nom, sa description et son infobulle d'aura dans les 5 langues, puis ses champs de Spell.dbc
N = {
    "gift": {"enUS": "Gift of Yu Wu", "frFR": "Don de Yu Wu", "deDE": "Gabe von Yu Wu", "esES": "Don de Yu Wu", "ruRU": "Дар Юй У"},
    "cloud": {"enUS": "Mist Cloud", "frFR": "Nuage de brume", "deDE": "Nebelwolke", "esES": "Nube de bruma", "ruRU": "Облако тумана"},
    "mists": {"enUS": "Mists of Yu Wu", "frFR": "Brumes de Yu Wu", "deDE": "Nebel von Yu Wu", "esES": "Brumas de Yu Wu", "ruRU": "Туманы Юй У"},
    "yulon": {"enUS": "Yu'lon", "frFR": "Yu’lon", "deDE": "Yu'lon", "esES": "Yu'lon", "ruRU": "Юй-лун"},
    "whispers": {"enUS": "Whispers of Shaohao", "frFR": "Murmures de Shaohao", "deDE": "Flüstern von Shaohao", "esES": "Susurros de Shaohao",
                 "ruRU": "Шепот Шаохао"},
    "keg": {"enUS": "Exploding Keg", "frFR": "Fût explosif", "deDE": "Explodierendes Fass", "esES": "Barril explosivo", "ruRU": "Взрывной бочонок"},
    "facepalm": {"enUS": "Face Palm", "frFR": "Paume au visage", "deDE": "Handfläche ins Gesicht", "esES": "Palma en la cara", "ruRU": "Ладонь в лицо"},
    "fortif": {"enUS": "Fortification of Jin Gu", "frFR": "Fortification de Jin Gu", "deDE": "Befestigung von Jin Gu",
               "esES": "Fortificación de Jin Gu", "ruRU": "Укрепление Цзинь Гу"},
    "thunder": {"enUS": "Thunder Fist", "frFR": "Poing de tonnerre", "deDE": "Donnerfaust", "esES": "Puño del trueno", "ruRU": "Громовой кулак"},
    "crosswinds": {"enUS": "Crosswinds", "frFR": "Vents croisés", "deDE": "Kreuzwinde", "esES": "Vientos cruzados", "ruRU": "Встречные ветра"},
    "windblades": {"enUS": "Wind Blades", "frFR": "Lames de vent", "deDE": "Windklingen", "esES": "Cuchillas de viento", "ruRU": "Лезвия ветра"},
    "storm": {"enUS": "Inner Storm", "frFR": "Orage intérieur", "deDE": "Innerer Sturm", "esES": "Tormenta interior", "ruRU": "Внутренняя буря"},
}
D = {
    S_GIFT: {"enUS": "Each of your heals has a 25% chance to condense a Mist Cloud around Yu Wu, up to 10, for 1 min.",
             "frFR": "Chacun de vos soins a 25% de chances de condenser un Nuage de brume autour de Yu Wu, jusqu’à 10, pendant 1 min.",
             "deDE": "Jede Eurer Heilungen hat eine Chance von 25%, eine Nebelwolke um Yu Wu zu verdichten, bis zu 10, 1 Min. lang.",
             "esES": "Cada una de tus sanaciones tiene un 25% de probabilidad de condensar una Nube de bruma en torno a Yu Wu, hasta 10, durante 1 min.",
             "ruRU": "Каждое ваше исцеление с вероятностью 25% сгущает вокруг Юй У облако тумана, до 10 облаков, на 1 мин."},
    S_GIFT_USE: {"enUS": "Consumes your Mist Clouds to heal the friendly target for $s1 per cloud.",
                 "frFR": "Consomme vos Nuages de brume pour rendre à la cible alliée $s1 points de vie par nuage.",
                 "deDE": "Verbraucht Eure Nebelwolken, um das freundliche Ziel pro Wolke um $s1 Gesundheit zu heilen.",
                 "esES": "Consume tus Nubes de bruma para sanar al objetivo aliado $s1 p. de salud por nube.",
                 "ruRU": "Расходует облака тумана, восполняя союзнику $s1 ед. здоровья за каждое облако."},
    S_MISTS: {"enUS": "When your instant healing spells heal a target, you have a 10% chance to summon Yu'lon, who assists you in restoring the raid for $84965d: she casts your healing spells again on the most injured allies. Cannot occur more than once every 130 sec.",
              "frFR": "Quand vos sorts de soin instantanés soignent une cible, vous avez 10% de chances d’invoquer Yu’lon, qui vous assiste pour restaurer le raid pendant $84965d : elle reproduit vos sorts de soin sur les alliés les plus blessés. Ne peut pas se produire plus d’une fois toutes les 130 s.",
              "deDE": "Wenn Eure sofortigen Heilzauber ein Ziel heilen, besteht eine Chance von 10%, Yu'lon zu beschwören, die Euch $84965d lang beim Heilen des Schlachtzugs hilft: Sie wirkt Eure Heilzauber erneut auf die am schwersten verletzten Verbündeten. Kann nicht öfter als einmal alle 130 Sek. auftreten.",
              "esES": "Cuando tus hechizos de sanación instantáneos sanan a un objetivo, tienes un 10% de probabilidad de invocar a Yu'lon, que te ayuda a restablecer a la banda durante $84965d: lanza de nuevo tus hechizos de sanación sobre los aliados más heridos. No puede ocurrir más de una vez cada 130 s.",
              "ruRU": "Когда ваши мгновенные исцеляющие заклинания исцеляют цель, с вероятностью 10% призывается Юй-лун, которая помогает вам восстанавливать рейд в течение $84965d: она повторяет ваши исцеляющие заклинания на самых раненых союзниках. Не чаще одного раза в 130 сек."},
    S_WHISPERS: {"enUS": "Your Soothing Mist and your Jade Serpent Statue's bounce to 2 additional allies, the most injured first, each bounce healing 33% less.",
                 "frFR": "Votre Brume apaisante et celle de votre statue du Serpent de jade rebondissent sur 2 alliés supplémentaires, les plus blessés d’abord, chaque rebond soignant 33% de moins.",
                 "deDE": "Euer Beruhigender Nebel und der Eurer Jadeschlangenstatue springen auf 2 weitere Verbündete über, die am schwersten verletzten zuerst; jeder Sprung heilt 33% weniger.",
                 "esES": "Tu Niebla calmante y la de tu estatua del Dragón de Jade rebotan en 2 aliados adicionales, primero los más heridos, y cada rebote sana un 33% menos.",
                 "ruRU": "Ваш Успокаивающий туман и туман вашей статуи Нефритовой Змеи перескакивают еще на 2 союзников, начиная с самых раненых; каждый скачок исцеляет на 33% меньше."},
    S_KEG: {"enUS": "Hurl a keg at the target location. It explodes, dealing $s1 Fire damage plus 50% of your attack power to enemies within 8 yards and causing a high amount of threat. Enemies hit miss all their melee attacks against you for 3 sec.",
            "frFR": "Lance un fût à l’endroit ciblé. Il explose et inflige $s1 points de dégâts de Feu plus 50% de votre puissance d’attaque aux ennemis à moins de 8 mètres, en générant une forte menace. Les ennemis touchés ratent toutes leurs attaques de mêlée contre vous pendant 3 s.",
            "deDE": "Schleudert ein Fass auf den Zielort. Es explodiert, fügt Gegnern im Umkreis von 8 Metern $s1 Feuerschaden plus 50% Eurer Angriffskraft zu und erzeugt sehr viel Bedrohung. Getroffene Gegner verfehlen Euch 3 Sek. lang mit all ihren Nahkampfangriffen.",
            "esES": "Lanza un barril a la ubicación objetivo. Explota e inflige $s1 p. de daño de Fuego más un 50% de tu poder de ataque a los enemigos a menos de 8 m, generando una gran cantidad de amenaza. Los enemigos alcanzados fallan todos sus ataques cuerpo a cuerpo contra ti durante 3 s.",
            "ruRU": "Бросает бочонок в указанную область. Он взрывается, нанося противникам в радиусе 8 м $s1 ед. урона от огня плюс 50% силы атаки и создавая высокий уровень угрозы. Задетые противники промахиваются всеми атаками ближнего боя по вам в течение 3 сек."},
    S_KEG_MISS: {"enUS": "Misses all melee attacks against the brewer.", "frFR": "Rate toutes ses attaques de mêlée contre le brasseur.",
                 "deDE": "Verfehlt den Brauer mit allen Nahkampfangriffen.", "esES": "Falla todos sus ataques cuerpo a cuerpo contra el cervecero.",
                 "ruRU": "Промахивается всеми атаками ближнего боя по пивовару."},
    S_FACEPALM: {"enUS": "Tiger Palm has a 30% chance to deal double damage and reduce the remaining cooldown of your brews by 1 sec. Cannot occur more than once every 4 sec.",
                 "frFR": "Paume du tigre a 30% de chances d’infliger le double de dégâts et de réduire de 1 s le temps de recharge restant de vos breuvages. Ne peut pas se produire plus d’une fois toutes les 4 s.",
                 "deDE": "Tigerklaue hat eine Chance von 30%, doppelten Schaden zu verursachen und die verbleibende Abklingzeit Eurer Gebräue um 1 Sek. zu verringern. Kann nicht öfter als einmal alle 4 Sek. auftreten.",
                 "esES": "Palma del tigre tiene un 30% de probabilidad de infligir el doble de daño y reducir 1 s el tiempo de reutilización restante de tus brebajes. No puede ocurrir más de una vez cada 4 s.",
                 "ruRU": "Лапа тигра с вероятностью 30% наносит двойной урон и сокращает оставшееся время восстановления ваших отваров на 1 сек. Не чаще одного раза в 4 сек."},
    S_FORTIF: {"enUS": "In Stance of the Sturdy Ox, increases your chance to dodge by $s1%.",
               "frFR": "En posture du Buffle vigoureux, augmente vos chances d’esquiver de $s1%.",
               "deDE": "In der Haltung des wilden Ochsen ist Eure Ausweichchance um $s1% erhöht.",
               "esES": "En la actitud del buey robusto, aumenta tu probabilidad de esquivar un $s1%.",
               "ruRU": "В стойке крепкого быка повышает вероятность уклонения на $s1%."},
    S_THUNDER: {"enUS": "Your melee attacks have a chance to charge Tian Lei with thunder: your next 4 attacks deal $84922s1 additional Nature damage plus 10% of your attack power.",
                "frFR": "Vos attaques de mêlée ont une chance de charger Tian Lei de tonnerre : vos 4 attaques suivantes infligent $84922s1 points de dégâts de Nature supplémentaires plus 10% de votre puissance d’attaque.",
                "deDE": "Eure Nahkampfangriffe haben eine Chance, Tian Lei mit Donner aufzuladen: Eure nächsten 4 Angriffe verursachen zusätzlich $84922s1 Naturschaden plus 10% Eurer Angriffskraft.",
                "esES": "Tus ataques cuerpo a cuerpo tienen probabilidad de cargar a Tian Lei de trueno: tus 4 siguientes ataques infligen $84922s1 p. de daño de Naturaleza adicional más un 10% de tu poder de ataque.",
                "ruRU": "Ваши атаки ближнего боя могут зарядить Тянь Лэй громом: следующие 4 атаки наносят дополнительно $84922s1 ед. урона от сил природы плюс 10% силы атаки."},
    S_CROSSWINDS: {"enUS": "While you channel Fists of Fury, a spinning crane strikes enemies within 8 yards of your target for $84462s1 Nature damage every 0.5 sec.",
                   "frFR": "Pendant que vous canalisez Poings de fureur, une grue tournoyante frappe les ennemis à moins de 8 mètres de votre cible et leur inflige $84462s1 points de dégâts de Nature toutes les 0,5 s.",
                   "deDE": "Während Ihr Furorfäuste kanalisiert, trifft ein wirbelnder Kranich Gegner im Umkreis von 8 Metern um Euer Ziel und verursacht alle 0,5 Sek. $84462s1 Naturschaden.",
                   "esES": "Mientras canalizas Puños de furia, una grulla giratoria golpea a los enemigos a menos de 8 m de tu objetivo e inflige $84462s1 p. de daño de Naturaleza cada 0,5 s.",
                   "ruRU": "Пока вы поддерживаете Неистовые кулаки, вращающийся журавль поражает противников в радиусе 8 м от вашей цели, нанося $84462s1 ед. урона от сил природы каждые 0,5 сек."},
    S_WINDBLADES: {"enUS": "Your Spinning Crane Kick hurls blades of wind: each enemy it strikes takes $84464s1 additional Nature damage plus 6% of your attack power.",
                   "frFR": "Votre Coup tournoyant de la grue projette des lames de vent : chaque ennemi touché subit $84464s1 points de dégâts de Nature supplémentaires plus 6% de votre puissance d’attaque.",
                   "deDE": "Euer Wirbelnder Kranichtritt schleudert Windklingen: Jeder getroffene Gegner erleidet zusätzlich $84464s1 Naturschaden plus 6% Eurer Angriffskraft.",
                   "esES": "Tu Patada giratoria de la grulla lanza cuchillas de viento: cada enemigo alcanzado sufre $84464s1 p. de daño de Naturaleza adicional más un 6% de tu poder de ataque.",
                   "ruRU": "Ваш «Удар журавля» выпускает лезвия ветра: каждый пораженный противник получает дополнительно $84464s1 ед. урона от сил природы плюс 6% силы атаки."},
    S_STORM: {"enUS": "Each Tiger Palm that hits charges Tian Lei with an inner storm, up to 5 charges. At 5 charges, your next Blackout Kick calls lightning down on your target, dealing $84925s1 Nature damage plus 40% of your attack power to it and to all enemies within 8 yards.",
              "frFR": "Chaque Paume du tigre qui touche charge Tian Lei d’un orage intérieur, jusqu’à 5 charges. À 5 charges, votre prochaine Frappe du voile noir fait tomber la foudre sur votre cible et inflige $84925s1 points de dégâts de Nature plus 40% de votre puissance d’attaque à celle-ci et à tous les ennemis à moins de 8 mètres.",
              "deDE": "Jede treffende Tigerklaue lädt Tian Lei mit einem inneren Sturm auf, bis zu 5 Aufladungen. Bei 5 Aufladungen ruft Euer nächster Blackouttritt einen Blitz auf Euer Ziel herab, der ihm und allen Gegnern im Umkreis von 8 Metern $84925s1 Naturschaden plus 40% Eurer Angriffskraft zufügt.",
              "esES": "Cada Palma del tigre que impacta carga a Tian Lei con una tormenta interior, hasta 5 cargas. Con 5 cargas, tu siguiente Patada oscura hace caer un rayo sobre tu objetivo que inflige $84925s1 p. de daño de Naturaleza más un 40% de tu poder de ataque a él y a todos los enemigos a menos de 8 m.",
              "ruRU": "Каждая попавшая «Лапа тигра» заряжает Тянь Лэй внутренней бурей, до 5 зарядов. При 5 зарядах ваш следующий «Удар затмения» обрушивает на цель молнию, которая наносит ей и всем противникам в радиусе 8 м $84925s1 ед. урона от сил природы плюс 40% силы атаки."},
}
A = {   # les infobulles d'aura
    S_CLOUD: {"enUS": "Condensed mist, ready to heal.", "frFR": "Brume condensée, prête à soigner.", "deDE": "Verdichteter Nebel, bereit zu heilen.",
              "esES": "Bruma condensada, lista para sanar.", "ruRU": "Сгущенный туман, готовый исцелять."},
    S_KEG_MISS: D[S_KEG_MISS],
    S_STORM_CHARGE: {"enUS": "Inner storm: at 5 charges, your next Blackout Kick calls down lightning.",
                     "frFR": "Orage intérieur : à 5 charges, votre prochaine Frappe du voile noir fait tomber la foudre.",
                     "deDE": "Innerer Sturm: Bei 5 Aufladungen ruft Euer nächster Blackouttritt einen Blitz herab.",
                     "esES": "Tormenta interior: con 5 cargas, tu siguiente Patada oscura hace caer un rayo.",
                     "ruRU": "Внутренняя буря: при 5 зарядах следующий «Удар затмения» обрушивает молнию."},
    S_THUNDER_BUFF: {"enUS": "Your next attacks deal additional Nature damage.", "frFR": "Vos prochaines attaques infligent des dégâts de Nature supplémentaires.",
                     "deDE": "Eure nächsten Angriffe verursachen zusätzlichen Naturschaden.", "esES": "Tus próximos ataques infligen daño de Naturaleza adicional.",
                     "ruRU": "Следующие атаки наносят дополнительный урон от сил природы."},
}


def icon_id(path):
    icons = dbclib.Dbc(open(os.path.join(SERVER_DBC, "SpellIcon.dbc"), "rb").read(), "is", "SpellIcon")
    for r in icons.rows:
        if r[1].lower() == path.lower():
            return r[0]
    raise SystemExit("icône %s absente de SpellIcon.dbc" % path)


def blank_spell(sid, name, level=80):
    row = [0.0 if c == "f" else ("" if c == "s" else 0) for c in SPELL_LAYOUT]
    row[0] = sid
    for f in ("SpellName", "Rank", "Description", "ToolTip"):
        row[FIELD[f + "Flags"]] = 16712190
    v = localized(name)
    for slot in range(16):
        row[FIELD["SpellName"] + slot] = v.get(slot, "")
    row[FIELD["EquippedItemClass"]] = -1
    row[FIELD["CastingTimeIndex"]] = 1
    row[FIELD["RangeIndex"]] = 1
    row[FIELD["ProcChance"]] = 101
    row[FIELD["SpellLevel"]] = level
    row[FIELD["BaseLevel"]] = level
    row[FIELD["SchoolMask"]] = 1
    row[FIELD["DmgClass"]] = 0
    for e in (1, 2, 3):
        row[FIELD["EffectDamageMultiplier%d" % e]] = 1.0
        row[FIELD["EffectValueMultiplier%d" % e]] = 0.0
    return row


def set_text(row, field, texts):
    v = localized(texts)
    for slot in range(16):
        row[FIELD[field] + slot] = v.get(slot, "")


def effect(row, n, **kw):
    names = {"Effect": "Effect", "BasePoints": "EffectBasePoints", "DieSides": "EffectDieSides", "TargetA": "EffectImplicitTargetA",
             "TargetB": "EffectImplicitTargetB", "Radius": "EffectRadiusIndex", "Aura": "EffectApplyAuraName",
             "Amplitude": "EffectAmplitude", "Misc": "EffectMiscValue", "MiscB": "EffectMiscValueB", "Trigger": "EffectTriggerSpell",
             "ChainTarget": "EffectChainTarget"}
    kw.setdefault("DieSides", 1)
    for k, v in kw.items():
        row[FIELD[names[k] + str(n)]] = v


def spells():
    """(rows de Spell.dbc, rows de spell_proc, rows de spell_bonus_data, rows de spell_script_names)"""
    I = icon_id
    rows, procs, bonus, scripts = [], [], [], []
    passive = 0x40 | 0x80000000          # SPELL_ATTR0_PASSIVE, SPELL_ATTR0_HIDE_IN_COMBAT_LOG... les passifs d'objets des autres armes
    no_log = 0x10000000                  # AttributesEx : SPELL_ATTR1_NO_AURA_ICON, pas d'icône dans les améliorations (les soins sans aura)

    def add(row):
        rows.append(row)
        return row

    # --- Yu Wu
    r = add(blank_spell(S_GIFT, N["gift"]))
    r[FIELD["Attributes"]] = 0x40 | 0x80
    r[FIELD["DurationIndex"]] = 21
    r[FIELD["ProcFlags"]] = 0x4000 | 0x400 | 0x40000      # les soins faits (directs, magiques ou non, et périodiques)
    r[FIELD["ProcChance"]] = 25
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Nature_HealingWaveLesser")
    effect(r, 1, Effect=6, Aura=42, TargetA=1, BasePoints=0, Trigger=S_CLOUD)
    set_text(r, "Description", D[S_GIFT])
    procs.append([S_GIFT, 0, 0, 0, 0, 0, 0, 2, 2, 0, 0, 0, 0, 25, 0, 0])
    scripts.append([S_GIFT, "spell_yuwu_don_nuage"])               # le nuage au sol, vu du seul Moine
    r = add(blank_spell(S_CLOUD, N["cloud"]))                # visible dans les améliorations : ses cumuls comptent les nuages
    r[FIELD["DurationIndex"]] = 3                          # 60 s
    r[FIELD["StackAmount"]] = 10
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Nature_Rejuvenation")
    r[FIELD["SchoolMask"]] = 8
    effect(r, 1, Effect=6, Aura=4, TargetA=1, BasePoints=0)
    set_text(r, "ToolTip", A[S_CLOUD])
    scripts.append([S_CLOUD, "spell_yuwu_nuage"])                 # son départ emporte les nuages du sol
    r = add(blank_spell(S_GIFT_USE, N["gift"]))
    r[FIELD["RangeIndex"]] = 5                             # 40 m
    r[FIELD["CastingTimeIndex"]] = 5                       # 2 s, comme le Don de Sheilun (SpellMisc 205406)
    r[FIELD["InterruptFlags"]] = 0x0F                      # le mouvement, le recul et les interruptions l'arrêtent
    r[FIELD["RecoveryTime"]] = 30000
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Nature_HealingWaveLesser")
    r[FIELD["SchoolMask"]] = 8
    r[FIELD["DmgClass"]] = 1
    r[FIELD["SpellVisual1"]] = VIS_DON                     # le bâton brandi (BattleRoar), l'impact du Toucher guérisseur
    effect(r, 1, Effect=10, TargetA=21, BasePoints=1799)
    set_text(r, "Description", D[S_GIFT_USE])
    bonus.append([S_GIFT_USE, 0.2, 0, 0, 0, "Yu Wu - Don de Yu Wu - 1 800 par nuage + 20 % de la puissance des soins (cahier)"])
    scripts.append([S_GIFT_USE, "spell_yuwu_don"])
    r = add(blank_spell(S_CLOUD_MISSILE, N["cloud"]))      # le projectile d'un nuage aspiré : lancé par le nuage sur le Moine
    r[FIELD["RangeIndex"]] = 13                            # sans limite
    r[FIELD["Speed"]] = NUAGE_VITESSE
    r[FIELD["SchoolMask"]] = 8
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Nature_Rejuvenation")
    r[FIELD["SpellVisual1"]] = VIS_NUAGE
    effect(r, 1, Effect=3, TargetA=25, BasePoints=0)
    r = add(blank_spell(S_MISTS, N["mists"]))
    r[FIELD["Attributes"]] = 0x40 | 0x80
    r[FIELD["DurationIndex"]] = 21
    r[FIELD["ProcFlags"]] = 0x4000 | 0x400
    r[FIELD["ProcChance"]] = 10
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Nature_HealingTouch")
    effect(r, 1, Effect=6, Aura=4, TargetA=1, BasePoints=0)
    set_text(r, "Description", D[S_MISTS])
    procs.append([S_MISTS, 0, 0, 0, 0, 0, 0, 2, 2, 0, 0, 0, 0, 10, 130000, 0])
    scripts.append([S_MISTS, "spell_yuwu_brumes"])
    r = add(blank_spell(S_YULON, N["yulon"]))
    r[FIELD["DurationIndex"]] = 29                         # 12 s
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Nature_HealingTouch")
    effect(r, 1, Effect=28, TargetA=18, BasePoints=0, Misc=NPC_YULON, MiscB=61)
    r = add(blank_spell(S_WHISPERS, N["whispers"]))
    r[FIELD["Attributes"]] = 0x40 | 0x80
    r[FIELD["DurationIndex"]] = 21
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Holy_Heal02")
    effect(r, 1, Effect=6, Aura=4, TargetA=1, BasePoints=-34)            # -33 % par rebond (lu par le script)
    set_text(r, "Description", D[S_WHISPERS])
    r = add(blank_spell(S_WHISPERS_HEAL, N["whispers"]))
    r[FIELD["AttributesEx"]] = no_log
    r[FIELD["AttributesEx3"]] = 0x20000000                 # SPELL_ATTR3_NO_DONE_BONUS : le montant est celui du rebond
    r[FIELD["RangeIndex"]] = 5
    r[FIELD["SchoolMask"]] = 8
    r[FIELD["DmgClass"]] = 1
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Holy_Heal02")
    r[FIELD["SpellVisual1"]] = VIS_MURMURES                # l'impact de la Récupération
    effect(r, 1, Effect=10, TargetA=21, BasePoints=0)
    bonus.append([S_WHISPERS_HEAL, 0, 0, 0, 0, "Yu Wu - Murmures de Shaohao - rebond : le montant du soin rebondi (script)"])

    # --- Jin Gu
    r = add(blank_spell(S_KEG, N["keg"]))
    r[FIELD["RangeIndex"]] = 5
    r[FIELD["RecoveryTime"]] = 75000
    r[FIELD["Targets"]] = 0x40                             # TARGET_FLAG_DEST_LOCATION : un endroit visé
    r[FIELD["SchoolMask"]] = 4
    r[FIELD["DmgClass"]] = 1
    r[FIELD["DurationIndex"]] = 27                         # 3 s, la durée du débuff des ennemis
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\INV_Misc_Ale_01")
    r[FIELD["SpellVisual1"]] = VIS_FUT                     # l'explosion au sol du Choc de flammes
    effect(r, 1, Effect=2, TargetA=87, TargetB=16, Radius=14, BasePoints=2999)
    effect(r, 2, Effect=6, Aura=4, TargetA=87, TargetB=16, Radius=14, BasePoints=0)
    effect(r, 3, Effect=63, TargetA=87, TargetB=16, Radius=14, BasePoints=5999)       # forte menace
    set_text(r, "Description", D[S_KEG])
    set_text(r, "ToolTip", D[S_KEG_MISS])
    bonus.append([S_KEG, 0, 0, 0.5, 0, "Jin Gu - Fût explosif - 3 000 + 50 % PA (cahier)"])
    r = add(blank_spell(S_FACEPALM, N["facepalm"]))
    r[FIELD["Attributes"]] = 0x40 | 0x80
    r[FIELD["DurationIndex"]] = 21
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Ability_Warrior_PunishingBlow")
    effect(r, 1, Effect=6, Aura=4, TargetA=1, BasePoints=29)                         # 30 % (lu par le script)
    set_text(r, "Description", D[S_FACEPALM])
    r = add(blank_spell(S_FORTIF, N["fortif"]))
    r[FIELD["Attributes"]] = 0x40 | 0x80
    r[FIELD["DurationIndex"]] = 21
    r[FIELD["Stances"]] = 1 << (OX_STANCE - 1)
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Ability_Warrior_ShieldWall")
    effect(r, 1, Effect=6, Aura=49, TargetA=1, BasePoints=3)                         # +4 % d'esquive
    set_text(r, "Description", D[S_FORTIF])

    # --- Tian Lei
    r = add(blank_spell(S_THUNDER, N["thunder"]))
    r[FIELD["Attributes"]] = 0x40 | 0x80
    r[FIELD["DurationIndex"]] = 21
    r[FIELD["ProcFlags"]] = 0x4 | 0x10                     # attaques automatiques et techniques de mêlée
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Nature_Lightning")
    effect(r, 1, Effect=6, Aura=42, TargetA=1, BasePoints=0, Trigger=S_THUNDER_BUFF)
    set_text(r, "Description", D[S_THUNDER])
    # 3 déclenchements par minute : 3 PPM laissaient 7 déclenchements en 60 s (les techniques du Moine comptent comme des
    # coups) ; une recharge de 20 s les borne à 3 par minute de combat
    procs.append([S_THUNDER, 0, 0, 0, 0, 0, 0, 1, 2, 0, 0, 0, 0, 100, 20000, 0])
    r = add(blank_spell(S_THUNDER_BUFF, N["thunder"]))
    r[FIELD["DurationIndex"]] = 9                          # 30 s pour s'en servir
    r[FIELD["ProcFlags"]] = 0x4 | 0x10
    r[FIELD["ProcCharges"]] = 4
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Nature_LightningOverload")
    r[FIELD["SchoolMask"]] = 8
    effect(r, 1, Effect=6, Aura=42, TargetA=1, BasePoints=0, Trigger=S_THUNDER_HIT)
    set_text(r, "ToolTip", A[S_THUNDER_BUFF])
    # SpellTypeMask 1 (dégâts) : sans lui, l'effet de la Paume du tigre qui rend du chi au Moine, lui-même pour cible,
    # usait une charge et lui envoyait le coup de tonnerre (essai du 25/10 : 944 sur Testvent)
    procs.append([S_THUNDER_BUFF, 0, 0, 0, 0, 0, 0, 1, 2, 0, 0, 0, 0, 100, 0, 4])
    scripts.append([S_THUNDER_BUFF, "spell_tian_lei_charge"])      # le coup qui pose les charges n'en use aucune
    r = add(blank_spell(S_THUNDER_HIT, N["thunder"]))
    r[FIELD["AttributesEx"]] = no_log & 0
    r[FIELD["RangeIndex"]] = 2                             # mêlée
    r[FIELD["SchoolMask"]] = 8
    r[FIELD["DmgClass"]] = 1
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Nature_LightningOverload")
    r[FIELD["SpellVisual1"]] = VIS_TONNERRE                # l'impact de l'Éclair, sans son incantation (qui rangeait les poings)
    effect(r, 1, Effect=2, TargetA=6, BasePoints=449)
    bonus.append([S_THUNDER_HIT, 0, 0, 0.1, 0, "Tian Lei - Poing de tonnerre - 450 + 10 % PA (cahier)"])

    # --- Tian Feng
    r = add(blank_spell(S_CROSSWINDS, N["crosswinds"]))
    r[FIELD["Attributes"]] = 0x40 | 0x80
    r[FIELD["DurationIndex"]] = 21
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Ability_Druid_GaleWinds")
    effect(r, 1, Effect=6, Aura=4, TargetA=1, BasePoints=0)
    set_text(r, "Description", D[S_CROSSWINDS])
    r = add(blank_spell(S_CRANE, N["crosswinds"]))
    r[FIELD["DurationIndex"]] = 35                         # 4 s, la canalisation de Poings de fureur (le script la règle)
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Ability_Druid_GaleWinds")
    effect(r, 1, Effect=28, TargetA=18, BasePoints=0, Misc=NPC_CRANE, MiscB=61)
    r = add(blank_spell(S_CRANE_PULSE, N["crosswinds"]))
    r[FIELD["AttributesEx"]] = no_log & 0
    r[FIELD["SchoolMask"]] = 8
    r[FIELD["DmgClass"]] = 1
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Ability_Druid_GaleWinds")
    r[FIELD["SpellVisual1"]] = VIS_GRUE                    # le cyclone sur chaque ennemi touché
    effect(r, 1, Effect=2, TargetA=53, TargetB=16, Radius=14, BasePoints=599)          # le Moine la lance sur sa cible : 8 m autour
    bonus.append([S_CRANE_PULSE, 0, 0, 0, 0, "Tian Feng - Vents croisés - 600 fixes toutes les 0,5 s (cahier)"])

    # --- Tian Feng : Lames de vent (passif de l'arme, choisi par Maitre le 25/10/2026 10:16 UTC)
    # 200 + 6 % PA par ennemi et par tic du Coup tournoyant de la grue (un tic toutes les 0,75 s) ; à 4 000 PA, 440 par tic,
    # du même ordre que les 600 fixes de Vents croisés toutes les 0,5 s
    r = add(blank_spell(S_WINDBLADES, N["windblades"]))
    r[FIELD["Attributes"]] = 0x40 | 0x80
    r[FIELD["DurationIndex"]] = 21
    r[FIELD["ProcFlags"]] = 0x10 | 0x1000 | 0x10000          # les coups du Coup tournoyant (le script ne garde que lui)
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Ability_Druid_GaleWinds")
    effect(r, 1, Effect=6, Aura=4, TargetA=1, BasePoints=0)
    set_text(r, "Description", D[S_WINDBLADES])
    procs.append([S_WINDBLADES, 0, 0, 0, 0, 0, 0, 1, 2, 0, 1, 0, 0, 100, 0, 0])   # dégâts, au toucher ; les coups déclenchés comptent
    scripts.append([S_WINDBLADES, "spell_tian_feng_lames_de_vent"])
    r = add(blank_spell(S_WINDBLADES_HIT, N["windblades"]))
    r[FIELD["RangeIndex"]] = 4                             # 30 m
    r[FIELD["Speed"]] = 30.0
    r[FIELD["SchoolMask"]] = 8
    r[FIELD["DmgClass"]] = 1
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Ability_Druid_GaleWinds")
    r[FIELD["SpellVisual1"]] = VIS_LAMES                   # la lame de vent (wind_chakram_missile, retail)
    effect(r, 1, Effect=2, TargetA=6, BasePoints=199)
    bonus.append([S_WINDBLADES_HIT, 0, 0, 0.06, 0, "Tian Feng - Lames de vent - 200 + 6 % PA par ennemi et par tic (Maitre, 25/10)"])

    # --- Tian Lei : Orage intérieur (passif de l'arme, choisi par Maitre le 25/10/2026 10:17 UTC)
    r = add(blank_spell(S_STORM, N["storm"]))
    r[FIELD["Attributes"]] = 0x40 | 0x80
    r[FIELD["DurationIndex"]] = 21
    r[FIELD["ProcFlags"]] = 0x10 | 0x1000 | 0x10000          # la Paume du tigre et la Frappe du voile noir (le script les trie)
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Nature_Lightning")
    effect(r, 1, Effect=6, Aura=4, TargetA=1, BasePoints=0)
    set_text(r, "Description", D[S_STORM])
    procs.append([S_STORM, 0, 0, 0, 0, 0, 0, 1, 2, 0, 0, 0, 0, 100, 0, 0])
    scripts.append([S_STORM, "spell_tian_lei_orage_interieur"])
    r = add(blank_spell(S_STORM_CHARGE, N["storm"]))       # les charges, visibles dans les améliorations
    r[FIELD["DurationIndex"]] = 9                          # 30 s
    r[FIELD["StackAmount"]] = 5
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Nature_LightningOverload")
    r[FIELD["SchoolMask"]] = 8
    effect(r, 1, Effect=6, Aura=4, TargetA=1, BasePoints=0)
    set_text(r, "ToolTip", A[S_STORM_CHARGE])
    r = add(blank_spell(S_STORM_STRIKE, N["storm"]))       # la foudre, sur la cible et à 8 m autour
    r[FIELD["RangeIndex"]] = 5
    r[FIELD["SchoolMask"]] = 8
    r[FIELD["DmgClass"]] = 1
    r[FIELD["SpellIconID"]] = I("Interface\\Icons\\Spell_Nature_CallStorm")
    r[FIELD["SpellVisual1"]] = VIS_ORAGE                   # l'éclair tombé du ciel (Appel de la foudre)
    effect(r, 1, Effect=2, TargetA=53, TargetB=16, Radius=14, BasePoints=1199)
    bonus.append([S_STORM_STRIKE, 0, 0, 0.4, 0, "Tian Lei - Orage intérieur - 1 200 + 40 % PA par ennemi à 8 m (Maitre, 25/10)"])
    return rows, procs, bonus, scripts


_TEMPLATES = {}
_CLIENT_DBC = {}


def client_rows(name):
    """{id: [mots]} d'une DBC telle que le client la lit (son patch-Z), mots bruts (entiers, flottants et textes non convertis)"""
    if name not in _CLIENT_DBC:
        sys.path.insert(0, r"E:\WoW-mods\installer")
        import core
        game = core.Client(CLIENT)
        game = game.in_language("enUS") if "enus" in game.languages else game
        f = "DBFilesClient\\" + name
        raw = game.open(game.winner(f)).read(f)
        n, fields, size, _ = struct.unpack("<4I", raw[4:20])
        _CLIENT_DBC[name] = {struct.unpack_from("<I", raw, 20 + i * size)[0]: list(struct.unpack_from("<%di" % fields, raw, 20 + i * size))
                             for i in range(n)}
    return _CLIENT_DBC[name]


def word(v):
    return struct.unpack("<i", struct.pack("<f", v))[0]


def visuals():
    """(SpellVisual, SpellVisualKit, SpellVisualEffectName) de la partie"""
    SV, KIT = client_rows("SpellVisual.dbc"), client_rows("SpellVisualKit.dbc")

    def sans_animation(vid, new):
        """une copie du visuel, sans ses kits d'avant-incantation et d'incantation (leurs animations rangent les armes)"""
        row = list(SV[vid])
        row[0], row[1], row[2] = new, 0, 0
        return row

    def missile(new, effect):
        row = list(SV[67])                                  # la Boule de feu : un projectile, ses réglages de vol
        row[0] = new
        row[1] = row[2] = row[3] = 0                        # ni avant-incantation, ni incantation, ni impact
        row[8] = effect
        row[11] = 0                                         # pas le son de la Boule de feu
        return row

    kits = []
    for new, src in ((KIT_DON_PRE, 100), (KIT_DON_CAST, 183)):          # ceux du Toucher guérisseur, l'animation remplacée
        row = list(KIT[src])
        row[0], row[2] = new, ANIM_BATTLEROAR
        kits.append(row)
    row = list(KIT[20068])                                  # le cyclone, sans son animation d'étourdi
    row[0], row[2] = KIT_GRUE, -1
    kits.append(row)

    don = list(SV[58])
    don[0], don[1], don[2], don[3] = VIS_DON, KIT_DON_PRE, KIT_DON_CAST, 101
    tonnerre = sans_animation(173, VIS_TONNERRE)
    tonnerre[7] = tonnerre[8] = 0                           # l'Éclair a un projectile ; le coup de poing n'en a pas
    orage = sans_animation(173, VIS_ORAGE)
    orage[3], orage[7], orage[8] = 123, 0, 0                # kit 123 : l'impact de l'Appel de la foudre, tombé du ciel
    grue = sans_animation(8206, VIS_GRUE)
    grue[3], grue[4] = KIT_GRUE, 0
    rows = [don, missile(VIS_NUAGE, EFF_NUAGE), tonnerre, missile(VIS_LAMES, EFF_LAMES), orage, grue,
            sans_animation(10408, VIS_FUT), sans_animation(58, VIS_MURMURES)]
    names = [[EFF_NUAGE, "monk_soothingmist_missile", "Spells\\ArtifactWeapons\\monk_soothingmist_missile.mdx", word(1.0), word(1.0), word(0.01), word(100.0)],
             [EFF_LAMES, "wind_chakram_missile", "Spells\\ArtifactWeapons\\wind_chakram_missile.mdx", word(1.0), word(1.0), word(0.01), word(100.0)]]
    return rows, kits, names


def template_visual(spell_id):
    if not _TEMPLATES:
        from ccgen.spells import SpellFile
        _TEMPLATES["file"] = SpellFile(open(os.path.join(SERVER_DBC, "Spell.dbc"), "rb").read())
    row = _TEMPLATES["file"].row(spell_id)
    if row is None:
        raise SystemExit("sort modèle %d absent" % spell_id)
    return row[FIELD["SpellVisual1"]]


# ------------------------------------------------------------------ le reste
def parse_sql():
    sys.path.insert(0, HERE)
    import awsql
    return awsql.tables()


def sql_value(v):
    if v is None:
        return "NULL"
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, int):
        return str(v)
    s = str(v)
    if re.fullmatch(r"-?\d+(\.\d+)?", s) or s.startswith("'") or s == "NULL":
        return s
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'").replace("\r\n", "\\r\\n").replace("\n", "\\n") + "'"


def insert(table, cols, rows):
    if not rows:
        return []
    lines = ["INSERT INTO `%s` (%s) VALUES" % (table, ", ".join("`%s`" % c for c in cols))]
    lines.append(",\n".join("(" + ", ".join(sql_value(v) for v in r) + ")" for r in rows) + ";")
    return lines


def copy_row(T, table, key, value):
    t = T[table]
    for r in t["rows"]:
        if r[0].strip("'") == str(value):
            return dict(zip(t["cols"], r))
    raise SystemExit("%s %s absent" % (table, value))


def model_box(path):
    head = open(path, "rb").read(0xBC)
    return struct.unpack_from("<6f", head, 0xA0)


def main():
    work = sys.argv[1]
    T = parse_sql()
    out_sql = []
    client = os.path.join(PART, "data", "client")
    if os.path.isdir(client):
        shutil.rmtree(client)

    # --- les fichiers du jeu
    weapon_dir = os.path.join(client, "Item", "ObjectComponents", "Weapon")
    os.makedirs(weapon_dir)
    for f in os.listdir(os.path.join(work, "ported")):
        shutil.copyfile(os.path.join(work, "ported", f), os.path.join(weapon_dir, f))
    for f in ("staff_2h_artifactshaohao_d_03_jade", "staff_2h_artifactmonkeyking_d_03red", "hand_1h_artifactskywall_d_06_jade",
              "hand_1h_artifactskywall_d_06_white"):
        shutil.copyfile(os.path.join(work, "export", "tex", f + ".blp"), os.path.join(weapon_dir, f + ".blp"))
    icons = os.path.join(client, "Interface", "Icons")
    os.makedirs(icons)
    for f in ("inv_staff_2h_artifactshaohao_d_03", "inv_staff_2h_artifactmonkeyking_d_03", "inv_hand_1h_artifactskywall_d_06",
              "inv_hand_1h_artifactskywall_d_06dual"):
        shutil.copyfile(os.path.join(work, "export", "tex", f + ".blp"), os.path.join(icons, f + ".blp"))
    for n in (35, 36, 37, 38):
        shutil.copyfile(os.path.join(work, "pictures", "Papoti_weapon_8010%d.blp" % n), os.path.join(icons, "Papoti_weapon_8010%d.blp" % n))
    for sub, folder in (("yulon_final", "PandarenSerpentGod"), ("ported_crane", "Crane")):
        dst = os.path.join(client, "Creature", folder)
        os.makedirs(dst)
        for f in os.listdir(os.path.join(work, sub)):
            shutil.copyfile(os.path.join(work, sub, f), os.path.join(dst, f))
    shutil.copyfile(os.path.join(work, "export_crane", "spells", "cranewhite.blp"), os.path.join(client, "Creature", "Crane", "cranewhite.blp"))
    dst = os.path.join(client, "Spells", "ArtifactWeapons")
    os.makedirs(dst)
    for f in os.listdir(os.path.join(work, "ported_sheilun")):
        shutil.copyfile(os.path.join(work, "ported_sheilun", f), os.path.join(dst, f))

    # --- les DBC
    spell_rows, procs, bonus, scripts = spells()
    items = [
        [YUWU, 2, 10, -1, 2, YUWU, 17, 2],
        [JINGU, 2, 10, -1, 2, JINGU, 17, 2],
        [TIANLEI, 2, 13, -1, 1, TIANLEI, 21, 7],
        [TIANFENG, 2, 13, -1, 1, TIANFENG, 22, 7],
    ] + [[BOOK[k], 15, 4, -1, 0, BOOKS[k]["display"], 0, 0] for k in BOOK]
    displays = [
        [YUWU, "staff_2h_artifactshaohao_d_03.mdx", "", "staff_2h_artifactshaohao_d_03_jade", "", "inv_staff_2h_artifactshaohao_d_03", ""],
        [JINGU, "staff_2h_artifactmonkeyking_d_03.mdx", "", "staff_2h_artifactmonkeyking_d_03red", "", "inv_staff_2h_artifactmonkeyking_d_03", ""],
        # le poing retail tourné de -60° autour de x dans la prise (tools/fist_rotate.py) : la lame vise droit devant au moment
        # du coup à mains nues ; la copie gauche en est le reflet en y (tools/fist_mirror.py)
        [TIANLEI, "hand_1h_artifactskywall_d_06.mdx", "", "hand_1h_artifactskywall_d_06_jade", "", "inv_hand_1h_artifactskywall_d_06", ""],
        [TIANFENG, "hand_1h_artifactskywall_d_06_l.mdx", "", "hand_1h_artifactskywall_d_06_white", "", "inv_hand_1h_artifactskywall_d_06dual", ""],
    ]
    displays = [d + [0] * 8 + [""] * 8 + [0, 0] for d in displays]
    models = dbclib.Dbc(open(os.path.join(SERVER_DBC, "CreatureModelData.dbc"), "rb").read(),
                        "iisifii" + "fff" + "iiii" + "fff" + "ffffff" + "fffff", "CreatureModelData")
    by_id = {r[0]: r for r in models.rows}
    model_rows, display_rows = [], []
    vis_rows, kit_rows, name_rows = visuals()
    for cid, path, copy_of, files, skins, scale in (
            (NPC_YULON, "Creature\\PandarenSerpentGod\\pandarenserpentgod.mdx", 2071, os.path.join(work, "yulon_final", "pandarenserpentgod.m2"),
             ["pandarenserpentgod_green", "pandarenserpentgod_green_glow", ""], 0.4),     # 0,5 puis -20 % (Maitre, 25/10 00:13 UTC)
            (NPC_CRANE, "Creature\\Crane\\crane.mdx", 373, os.path.join(work, "ported_crane", "crane.m2"), ["cranewhite", "", ""], 1.0),
            # le nuage du Don de Sheilun : un modèle de particules seules ; la ligne de modèle copiée est celle d'un nuage d'orage
            (NPC_CLOUD, "Spells\\ArtifactWeapons\\7fx_monk_mistsofsheilun_statebase.mdx", 2696,
             os.path.join(work, "ported_sheilun", "7fx_monk_mistsofsheilun_statebase.m2"), ["", "", ""], 1.0)):
        row = list(by_id[copy_of])
        box = model_box(files)
        row[0], row[2] = cid, path
        row[5] = row[6] = row[13] = 0
        if not any(box):                                    # un modèle sans sommets : une petite boîte au sol
            box = (-0.5, -0.5, 0.0, 0.5, 0.5, 0.6)
        row[14] = max(box[3] - box[0], box[4] - box[1]) / 2
        row[15] = box[5] - box[2]
        row[17:23] = list(box)
        model_rows.append(row)
        display_rows.append([cid, cid, 0, 0, scale, 255] + skins + [""] + [0] * 6)

    def entry(name, layout, rows, text, owned):
        def words(r):
            return [struct.unpack("<i", struct.pack("<f", v))[0] if c == "f" else v for v, c in zip(r, layout)]
        return {"file": name, "fields": len(layout), "text_fields": text, "client": True, "server": True,
                "owned_ids": owned, "rows": [words(r) for r in rows]}
    dbc_entries = [
        entry("Spell.dbc", SPELL_LAYOUT, spell_rows, [[136, 151], [153, 168], [170, 185], [187, 202]], SPELL_BLOCKS),
        entry("Item.dbc", "i" * 8, items, [], [[YUWU, TIANFENG], [BOOK[YUWU], BOOK[TIANFENG]]]),
        entry("ItemDisplayInfo.dbc", "i" + "s" * 6 + "i" * 8 + "s" * 8 + "ii", displays, [[1, 6], [15, 22]], [[YUWU, TIANFENG]]),
        # plus d'ensemble (25/10) : sa ligne reste déclarée, vide, pour qu'une mise à jour l'enlève (l'installeur ne nettoie
        # que les DBC que le nouveau paquet déclare encore)
        entry("ItemSet.dbc", "i" + "s" * 16 + "i" + "i" * 17 + "i" * 8 + "i" * 8 + "ii", [], [[1, 16]], [[ITEMSET, ITEMSET]]),
        entry("CreatureModelData.dbc", "iisifii" + "fff" + "iiii" + "fff" + "ffffff" + "fffff", model_rows, [2], [[NPC_YULON, NPC_CLOUD]]),
        entry("CreatureDisplayInfo.dbc", "iiii" + "f" + "i" + "ssss" + "iiiiii", display_rows, [6, 7, 8, 9], [[NPC_YULON, NPC_CLOUD]]),
        entry("SpellVisual.dbc", "i" * 32, vis_rows, [], [VISUAL_IDS]),
        entry("SpellVisualKit.dbc", "i" * 38, kit_rows, [], [VISUAL_IDS]),
        entry("SpellVisualEffectName.dbc", "iss" + "iiii", name_rows, [1, 2], [VISUAL_IDS]),
    ]

    # --- le SQL : spell_dbc (les mêmes lignes que Spell.dbc), spell_proc, spell_bonus_data, spell_script_names
    sd = T["spell_dbc"]["cols"]
    out_sql += ["-- mod-artifact-weapons, partie « Moine » (classe 10 de mod-custom-classes) : généré par tools/monk_part.py, ne pas éditer", ""]
    out_sql += ["DELETE FROM `spell_dbc` WHERE %s;" % span("ID")]
    out_sql += insert("spell_dbc", sd, spell_rows) + [""]
    out_sql += ["DELETE FROM `spell_proc` WHERE %s;" % span("ABS(SpellId)")]
    out_sql += insert("spell_proc", T["spell_proc"]["cols"], procs) + [""]
    out_sql += ["DELETE FROM `spell_bonus_data` WHERE %s;" % span("entry")]
    out_sql += insert("spell_bonus_data", T["spell_bonus_data"]["cols"], bonus) + [""]
    out_sql += ["DELETE FROM `spell_script_names` WHERE %s;" % span("ABS(spell_id)")]
    out_sql += insert("spell_script_names", T["spell_script_names"]["cols"], scripts) + [""]

    # --- les objets
    it = T["item_template"]["cols"]
    rows = []
    stats = {YUWU: 84026, JINGU: 84015, TIANLEI: 84027, TIANFENG: 84027}
    dmg = {YUWU: (974, 1274, 3600), JINGU: (1163, 1899, 3600), TIANLEI: (623, 1076, 2600), TIANFENG: (623, 1076, 2600)}
    item_spells = {YUWU: [(S_GIFT, 1), (S_GIFT_USE, 0), (S_MISTS, 1), (S_WHISPERS, 1)], JINGU: [(S_KEG, 0), (S_FACEPALM, 1), (S_FORTIF, 1)],
                   TIANLEI: [(S_THUNDER, 1), (S_STORM, 1)], TIANFENG: [(S_CROSSWINDS, 1), (S_WINDBLADES, 1)]}
    for iid in (YUWU, JINGU, TIANLEI, TIANFENG):
        row = copy_row(T, "item_template", "entry", stats[iid])
        row.update({"entry": iid, "name": ITEMS[iid]["name"]["enUS"], "displayid": iid, "AllowableClass": MONK_MASK,
                    "subclass": 10 if iid in (YUWU, JINGU) else 13, "InventoryType": {TIANLEI: 21, TIANFENG: 22}.get(iid, 17),
                    "Material": 2 if iid in (YUWU, JINGU) else 1, "sheath": 2 if iid in (YUWU, JINGU) else 7,
                    "dmg_min1": dmg[iid][0], "dmg_max1": dmg[iid][1], "delay": dmg[iid][2], "description": ITEMS[iid]["desc"]["enUS"],
                    "itemset": 0})
        for k in range(1, 6):
            row["spellid_%d" % k], row["spelltrigger_%d" % k] = 0, 0
            row["spellcooldown_%d" % k] = row["spellcategorycooldown_%d" % k] = -1
        for k, (sid, trig) in enumerate(item_spells[iid], 1):
            row["spellid_%d" % k], row["spelltrigger_%d" % k] = sid, trig
        rows.append([row[c] for c in it])
    for qid, bid in BOOK.items():
        row = copy_row(T, "item_template", "entry", 84126)
        row.update({"entry": bid, "name": BOOKS[qid]["name"]["enUS"], "displayid": BOOKS[qid]["display"], "AllowableClass": MONK_MASK,
                    "description": BOOKS[qid]["desc"]["enUS"], "startquest": QUEST[qid]})
        rows.append([row[c] for c in it])
    out_sql += ["DELETE FROM `item_template` WHERE entry BETWEEN %d AND %d OR entry BETWEEN %d AND %d;" % (YUWU, TIANFENG, BOOK[YUWU], BOOK[TIANFENG])]
    out_sql += insert("item_template", it, rows) + [""]
    loc = []
    for iid, d in list(ITEMS.items()) + [(BOOK[q], BOOKS[q]) for q in BOOK]:
        for lang in LOCALES:
            loc.append([iid, lang, d["name"][lang], d["desc"][lang], 0])
    out_sql += ["DELETE FROM `item_template_locale` WHERE ID BETWEEN %d AND %d OR ID BETWEEN %d AND %d;" % (YUWU, TIANFENG, BOOK[YUWU], BOOK[TIANFENG])]
    out_sql += insert("item_template_locale", T["item_template_locale"]["cols"], loc) + [""]

    # --- plus d'ensemble (25/10) : ses noms de pièces s'en vont
    out_sql += ["DELETE FROM `item_set_names` WHERE entry BETWEEN %d AND %d;" % (TIANLEI, TIANFENG)]
    out_sql += ["DELETE FROM `item_set_names_locale` WHERE ID BETWEEN %d AND %d;" % (TIANLEI, TIANFENG), ""]

    # --- les PNJ des quêtes, Yu'lon et la grue
    ct = T["creature_template"]["cols"]
    rows, models_sql, locs, spawns = [], [], [], []
    for qid, p in PNJ.items():
        row = copy_row(T, "creature_template", "entry", 84026)
        row.update({"entry": QUEST[qid], "name": p["name"]["enUS"]})
        rows.append([row[c] for c in ct])
        models_sql.append([QUEST[qid], 0, PNJ_DISPLAY, 1, 1, 0])
        locs += [[QUEST[qid], lang, p["name"][lang], "", 0] for lang in LOCALES]
        m, zone, area, x, y, z, o = p["spot"]
        sp = copy_row(T, "creature", "guid", 8400025)
        sp.update({"guid": SPAWN_GUID[qid], "id": QUEST[qid], "map": m, "zoneId": zone, "areaId": area,
                   "position_x": x, "position_y": y, "position_z": z, "orientation": o})
        spawns.append([sp[c] for c in T["creature"]["cols"]])
    for cid, name, script in ((NPC_YULON, N["yulon"], "npc_yuwu_yulon"), (NPC_CRANE, N["crosswinds"], "npc_tian_feng_grue"),
                              (NPC_CLOUD, N["cloud"], "npc_yuwu_nuage")):
        row = copy_row(T, "creature_template", "entry", 84200)
        row.update({"entry": cid, "name": name["enUS"], "subname": "", "ScriptName": script, "unit_flags": 0x2000000 | 0x2,
                    "flags_extra": 0x2 if cid in (NPC_CRANE, NPC_CLOUD) else row.get("flags_extra", 0)})
        if cid == NPC_CLOUD:
            row.update({"faction": 35, "unit_flags": 0x2000000 | 0x2 | 0x100})   # ni ciblable, ni attaquable, amical
        rows.append([row[c] for c in ct])
        models_sql.append([cid, 0, cid, 1, 1, 0])
        locs += [[cid, lang, name[lang], "", 0] for lang in LOCALES]
    ids = "entry BETWEEN %d AND %d OR entry BETWEEN %d AND %d" % (YUWU, TIANFENG, NPC_YULON, NPC_CLOUD)
    out_sql += ["DELETE FROM `creature_template` WHERE %s;" % ids] + insert("creature_template", ct, rows) + [""]
    out_sql += ["DELETE FROM `creature_template_model` WHERE %s;" % ids.replace("entry", "CreatureID")]
    out_sql += insert("creature_template_model", T["creature_template_model"]["cols"], models_sql) + [""]
    out_sql += ["DELETE FROM `creature_model_info` WHERE DisplayID BETWEEN %d AND %d;" % (NPC_YULON, NPC_CLOUD)]
    out_sql += insert("creature_model_info", ["DisplayID", "BoundingRadius", "CombatReach", "Gender", "DisplayID_Other_Gender"],
                      [[NPC_YULON, 1.0, 1.5, 2, 0], [NPC_CRANE, 0.5, 1.0, 2, 0], [NPC_CLOUD, 0.5, 1.0, 2, 0]]) + [""]
    out_sql += ["DELETE FROM `creature_template_locale` WHERE %s;" % ids]
    out_sql += insert("creature_template_locale", T["creature_template_locale"]["cols"], locs) + [""]
    # tout spawn de ces quatre PNJ s'en va d'abord (un posé à la main sur un royaume, une installation d'avant) : un PNJ par arme
    out_sql += ["DELETE FROM `creature` WHERE id BETWEEN %d AND %d OR guid BETWEEN %d AND %d;"
                % (QUEST[YUWU], QUEST[TIANFENG], SPAWN_GUID[YUWU], SPAWN_GUID[TIANFENG])]
    out_sql += insert("creature", T["creature"]["cols"], spawns) + [""]

    # --- les quêtes
    qt = T["quest_template"]["cols"]
    rows, addons, offers, enders, qlocs, olocs = [], [], [], [], [], []
    for qid in QUEST:
        row = copy_row(T, "quest_template", "ID", 84026)
        picture = "\\r\\n|TInterface\\\\Icons\\\\Papoti_weapon_8010%d:256|t" % (qid - 84000)
        row.update({"ID": QUEST[qid], "RewardItem1": qid, "RewardAmount1": 1, "LogTitle": QUESTS[qid]["title"]["enUS"],
                    "LogDescription": QUEST_OBJECTIVE["enUS"], "QuestDescription": "'" + esc(QUEST_DETAILS["enUS"]) + picture + "'",
                    "ObjectiveText1": QUEST_OBJECTIVE["enUS"]})
        rows.append([row[c] for c in qt])
        addon = copy_row(T, "quest_template_addon", "ID", 84026)
        addon.update({"ID": QUEST[qid], "AllowableClasses": MONK_MASK})
        addons.append([addon[c] for c in T["quest_template_addon"]["cols"]])
        offers.append([QUEST[qid], 0, 0, 0, 0, 0, 0, 0, 0, QUEST_REWARD["enUS"], 0])
        enders.append([QUEST[qid], QUEST[qid]])
        for lang in LOCALES:
            qlocs.append([QUEST[qid], lang, QUESTS[qid]["title"][lang], "'" + esc(QUEST_DETAILS[lang]) + picture + "'",
                          QUEST_OBJECTIVE[lang], "", "", QUEST_OBJECTIVE[lang], "", "", "", 0])
            olocs.append([QUEST[qid], lang, QUEST_REWARD[lang], 0])
    out_sql += ["DELETE FROM `quest_template` WHERE ID BETWEEN %d AND %d;" % (YUWU, TIANFENG)] + insert("quest_template", qt, rows) + [""]
    out_sql += ["DELETE FROM `quest_template_addon` WHERE ID BETWEEN %d AND %d;" % (YUWU, TIANFENG)]
    out_sql += insert("quest_template_addon", T["quest_template_addon"]["cols"], addons) + [""]
    out_sql += ["DELETE FROM `quest_offer_reward` WHERE ID BETWEEN %d AND %d;" % (YUWU, TIANFENG)]
    out_sql += insert("quest_offer_reward", T["quest_offer_reward"]["cols"], offers) + [""]
    out_sql += ["DELETE FROM `creature_questender` WHERE quest BETWEEN %d AND %d;" % (YUWU, TIANFENG)]
    out_sql += insert("creature_questender", T["creature_questender"]["cols"], enders) + [""]
    out_sql += ["DELETE FROM `quest_template_locale` WHERE ID BETWEEN %d AND %d;" % (YUWU, TIANFENG)]
    out_sql += insert("quest_template_locale", T["quest_template_locale"]["cols"], qlocs) + [""]
    out_sql += ["DELETE FROM `quest_offer_reward_locale` WHERE ID BETWEEN %d AND %d;" % (YUWU, TIANFENG)]
    out_sql += insert("quest_offer_reward_locale", T["quest_offer_reward_locale"]["cols"], olocs) + [""]

    # --- le butin : les livres dans la référence 84000 (Citadelle de la Couronne de glace), comme les 32 autres
    ref = copy_row(T, "reference_loot_template", "Entry", 84000)
    rl = T["reference_loot_template"]["cols"]
    rows = []
    for qid, bid in BOOK.items():
        r = dict(ref)
        r.update({"Item": bid})
        rows.append([r[c] for c in rl])
    out_sql += ["DELETE FROM `reference_loot_template` WHERE Entry = 84000 AND Item BETWEEN %d AND %d;" % (BOOK[YUWU], BOOK[TIANFENG])]
    out_sql += insert("reference_loot_template", rl, rows) + [""]

    sql_dir = os.path.join(PART, "data", "sql", "world")
    os.makedirs(sql_dir, exist_ok=True)
    open(os.path.join(sql_dir, "mod-artifact-weapons--monk_world.sql"), "w", encoding="utf-8", newline="\n").write("\n".join(out_sql) + "\n")

    # --- installer.json de la partie
    world_rows = [
        {"table": "spell_dbc", "where": span("ID")}, {"table": "spell_proc", "where": span("ABS(SpellId)")},
        {"table": "spell_bonus_data", "where": span("entry")}, {"table": "spell_script_names", "where": span("ABS(spell_id)")},
        {"table": "item_template", "where": "entry BETWEEN %d AND %d OR entry BETWEEN %d AND %d" % (YUWU, TIANFENG, BOOK[YUWU], BOOK[TIANFENG])},
        {"table": "item_template_locale", "where": "ID BETWEEN %d AND %d OR ID BETWEEN %d AND %d" % (YUWU, TIANFENG, BOOK[YUWU], BOOK[TIANFENG])},
        {"table": "creature_template", "where": ids}, {"table": "creature_template_model", "where": ids.replace("entry", "CreatureID")},
        {"table": "creature_model_info", "where": "DisplayID BETWEEN %d AND %d" % (NPC_YULON, NPC_CLOUD)},
        {"table": "creature_template_locale", "where": ids},
        {"table": "creature", "where": "id BETWEEN %d AND %d OR guid BETWEEN %d AND %d" % (QUEST[YUWU], QUEST[TIANFENG], SPAWN_GUID[YUWU], SPAWN_GUID[TIANFENG])},
        {"table": "quest_template", "where": "ID BETWEEN %d AND %d" % (YUWU, TIANFENG)},
        {"table": "quest_template_addon", "where": "ID BETWEEN %d AND %d" % (YUWU, TIANFENG)},
        {"table": "quest_offer_reward", "where": "ID BETWEEN %d AND %d" % (YUWU, TIANFENG)},
        {"table": "creature_questender", "where": "quest BETWEEN %d AND %d" % (YUWU, TIANFENG)},
        {"table": "quest_template_locale", "where": "ID BETWEEN %d AND %d" % (YUWU, TIANFENG)},
        {"table": "quest_offer_reward_locale", "where": "ID BETWEEN %d AND %d" % (YUWU, TIANFENG)},
        {"table": "reference_loot_template", "where": "Entry = 84000 AND Item BETWEEN %d AND %d" % (BOOK[YUWU], BOOK[TIANFENG])},
    ]
    manifest = {
        "format": "wow-mods-installer/1",
        "module": "mod-artifact-weapons--monk",
        "title": "Artifact weapons: Monk",
        "server_module": False,
        "fields": {"game": "required", "worldserver": "required", "mysql": "required"},
        "dbc": dbc_entries,
        "game_files": {"sources": ["data/client"], "owned_folders": ["Creature/PandarenSerpentGod", "Creature/Crane"]},
        "database": {"world": {"rows": world_rows}},
    }
    open(os.path.join(PART, "installer.json"), "w", encoding="utf-8", newline="\n").write(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print("partie Moine : %d sorts, %d objets, %d lignes SQL" % (len(spell_rows), len(items), len(out_sql)))


def esc(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def span(column):
    return "(" + " OR ".join("%s BETWEEN %d AND %d" % (column, lo, hi) for lo, hi in SPELL_BLOCKS) + ")"


if __name__ == "__main__":
    main()
