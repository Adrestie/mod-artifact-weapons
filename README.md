# mod-artifact-weapons

An AzerothCore module (WotLK 3.3.5a) that adds artifact weapons, each bound to one class and carrying effects of its own.

## Key features

- 32 weapons across the ten classes, with their own models, icons and spell effects:
  - Warrior: Brakk (two-handed sword), Drakthor (one-handed sword, main hand), Malthen (shield), Vorgath (two-handed sword), Draemorr (two-handed sword)
  - Paladin: Ashbringer (two-handed sword), Vindictus (one-handed mace, main hand), Salvation (shield), Solareth (one-handed mace, main hand), Kyresion (shield)
  - Hunter: Kael'Thorr (bow)
  - Rogue: Sanguineus (dagger), Carnifex (dagger), Shuor'ror (one-handed sword), Shuadslayern (one-handed sword)
  - Priest: Sha'haggul (staff), Luminaris (staff)
  - Death Knight: Varkhal (one-handed sword, main hand), Skorrn (one-handed sword, off hand), Vorthalak (two-handed axe), Drethmâr (two-handed axe)
  - Shaman: Ezh'ra (staff), Nairūn (one-handed mace), Kelrah (shield), Drokhan (one-handed mace, main hand), Mak'hor (one-handed mace, off hand)
  - Mage: Vaelthis (staff)
  - Warlock: Xer'thul (staff)
  - Druid: Elun'dor (staff), Liora (staff), Tharnok (polearm), Bloodfang (polearm)
- 143 custom spells behind 59 effects: procs, auras and stacking effects for damage dealers, tanks and healers.
- Each weapon is obtained through a treasure hunt that starts with a class item looted in Icecrown Citadel.

## Dependencies

| Dependency | For |
|---|---|
| [AzerothCore](https://github.com/azerothcore/azerothcore-wotlk) (WotLK 3.3.5a) | the server |

## How to install

1. Download `installer.exe` from the [WoW-mods-installer releases](https://github.com/Adrestie/WoW-mods-installer/releases).
2. Stop the worldserver and close the game.
3. Run `installer.exe`, give it this folder and the folders it asks for, click **Check**, then **Install**.
4. Rebuild the worldserver. On its next start, the core applies the module's SQL.
5. The installer writes the game files into `Data\patch-Z.MPQ`: give that archive to the other players.

## How to update

Same steps with the new version's folder, choosing **Update** instead of **Install**. Rebuild the worldserver, then give the players the new `patch-Z.MPQ`.

## How to uninstall

Same steps, choosing **Remove**. Everything goes, database included. Rebuild the worldserver.
