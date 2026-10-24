-- Extrait de acore_world_hard.spell_custom_attr, tel quel, le 2026-09-28.
-- Clause : spell_id BETWEEN 84300 AND 84999
DELETE FROM `spell_custom_attr` WHERE (spell_id BETWEEN 84300 AND 84459 OR spell_id BETWEEN 84480 AND 84919 OR spell_id BETWEEN 84940 AND 84959);
INSERT INTO `spell_custom_attr` (`spell_id`, `attributes`) VALUES (84325,16777216);
INSERT INTO `spell_custom_attr` (`spell_id`, `attributes`) VALUES (84340,16777216);
INSERT INTO `spell_custom_attr` (`spell_id`, `attributes`) VALUES (84401,32776);
INSERT INTO `spell_custom_attr` (`spell_id`, `attributes`) VALUES (84565,16777216);
INSERT INTO `spell_custom_attr` (`spell_id`, `attributes`) VALUES (84942,32768);
