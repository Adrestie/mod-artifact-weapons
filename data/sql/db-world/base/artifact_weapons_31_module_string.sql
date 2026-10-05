-- Texts of the module's command, English in module_string, the other languages in module_string_locale.
-- Clause : module = 'mod-artifact-weapons'
DELETE FROM `module_string` WHERE `module` = 'mod-artifact-weapons';
INSERT INTO `module_string` (`module`, `id`, `string`) VALUES
('mod-artifact-weapons', 1, 'Damage and healing bonuses of {}:'),
('mod-artifact-weapons', 2, '  Weapon attacks (physical): {:+.1f} %'),
('mod-artifact-weapons', 3, '  Spell damage, by school: Physical {:+.1f} %, Holy {:+.1f} %, Fire {:+.1f} %, Nature {:+.1f} %, Frost {:+.1f} %, Shadow {:+.1f} %, Arcane {:+.1f} %'),
('mod-artifact-weapons', 4, '  Healing done: {:+.1f} %'),
('mod-artifact-weapons', 5, '  Spell power (damage), by school: Holy {}, Fire {}, Nature {}, Frost {}, Shadow {}, Arcane {}'),
('mod-artifact-weapons', 6, '  Healing power: {}'),
('mod-artifact-weapons', 7, '  Only the Damage done % and Healing done % auras count: class talents that change given spells are not included.');
DELETE FROM `module_string_locale` WHERE `module` = 'mod-artifact-weapons';
INSERT INTO `module_string_locale` (`module`, `id`, `locale`, `string`) VALUES
('mod-artifact-weapons', 1, 'frFR', 'Bonus aux dégâts et aux soins de {} :'),
('mod-artifact-weapons', 1, 'deDE', 'Schadens- und Heilungsboni von {}:'),
('mod-artifact-weapons', 1, 'esES', 'Bonificaciones de daño y sanación de {}:'),
('mod-artifact-weapons', 1, 'ruRU', 'Бонусы к урону и исцелению (персонаж {}):'),
('mod-artifact-weapons', 2, 'frFR', '  Attaques à l\'arme (physique) : {:+.1f} %'),
('mod-artifact-weapons', 2, 'deDE', '  Waffenangriffe (körperlich): {:+.1f} %'),
('mod-artifact-weapons', 2, 'esES', '  Ataques con arma (físico): {:+.1f} %'),
('mod-artifact-weapons', 2, 'ruRU', '  Атаки оружием (физический урон): {:+.1f} %'),
('mod-artifact-weapons', 3, 'frFR', '  Dégâts des sorts, par école : Physique {:+.1f} %, Sacré {:+.1f} %, Feu {:+.1f} %, Nature {:+.1f} %, Givre {:+.1f} %, Ombre {:+.1f} %, Arcanes {:+.1f} %'),
('mod-artifact-weapons', 3, 'deDE', '  Zauberschaden nach Schule: Körperlich {:+.1f} %, Heilig {:+.1f} %, Feuer {:+.1f} %, Natur {:+.1f} %, Frost {:+.1f} %, Schatten {:+.1f} %, Arkan {:+.1f} %'),
('mod-artifact-weapons', 3, 'esES', '  Daño de hechizos, por escuela: Físico {:+.1f} %, Sagrado {:+.1f} %, Fuego {:+.1f} %, Naturaleza {:+.1f} %, Escarcha {:+.1f} %, Sombras {:+.1f} %, Arcano {:+.1f} %'),
('mod-artifact-weapons', 3, 'ruRU', '  Урон от заклинаний по школам: физический {:+.1f} %, свет {:+.1f} %, огонь {:+.1f} %, природа {:+.1f} %, лед {:+.1f} %, тьма {:+.1f} %, тайная магия {:+.1f} %'),
('mod-artifact-weapons', 4, 'frFR', '  Soins prodigués : {:+.1f} %'),
('mod-artifact-weapons', 4, 'deDE', '  Verursachte Heilung: {:+.1f} %'),
('mod-artifact-weapons', 4, 'esES', '  Sanación realizada: {:+.1f} %'),
('mod-artifact-weapons', 4, 'ruRU', '  Исходящее исцеление: {:+.1f} %'),
('mod-artifact-weapons', 5, 'frFR', '  Puissance des sorts (dégâts), par école : Sacré {}, Feu {}, Nature {}, Givre {}, Ombre {}, Arcanes {}'),
('mod-artifact-weapons', 5, 'deDE', '  Zaubermacht (Schaden) nach Schule: Heilig {}, Feuer {}, Natur {}, Frost {}, Schatten {}, Arkan {}'),
('mod-artifact-weapons', 5, 'esES', '  Poder con hechizos (daño), por escuela: Sagrado {}, Fuego {}, Naturaleza {}, Escarcha {}, Sombras {}, Arcano {}'),
('mod-artifact-weapons', 5, 'ruRU', '  Сила заклинаний (урон) по школам: свет {}, огонь {}, природа {}, лед {}, тьма {}, тайная магия {}'),
('mod-artifact-weapons', 6, 'frFR', '  Puissance des soins : {}'),
('mod-artifact-weapons', 6, 'deDE', '  Heilkraft: {}'),
('mod-artifact-weapons', 6, 'esES', '  Poder de sanación: {}'),
('mod-artifact-weapons', 6, 'ruRU', '  Сила исцеления: {}'),
('mod-artifact-weapons', 7, 'frFR', '  Seules les auras « dégâts infligés % » et « soins prodigués % » comptent : les talents de classe qui modifient des sorts précis ne sont pas inclus.'),
('mod-artifact-weapons', 7, 'deDE', '  Nur die Auren „Verursachter Schaden %“ und „Verursachte Heilung %“ zählen: Klassentalente, die bestimmte Zauber verändern, sind nicht berücksichtigt.'),
('mod-artifact-weapons', 7, 'esES', '  Solo cuentan las auras de % de daño infligido y % de sanación realizada: no se incluyen los talentos de clase que modifican hechizos concretos.'),
('mod-artifact-weapons', 7, 'ruRU', '  Учитываются только ауры «Наносимый урон, %» и «Исходящее исцеление, %»: классовые таланты, изменяющие отдельные заклинания, в расчет не входят.');
