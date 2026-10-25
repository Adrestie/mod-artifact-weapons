/*
 * Les trois armes artefacts du Moine (classe 10 de mod-custom-classes), partie « Moine » du module
 * (data/parts/monk, installée seulement quand la classe 10 existe). Cahier validé par Maitre le 24/10/2026.
 * Les sorts, objets, PNJ et quêtes : tools/monk_part.py. Les sorts du Moine visés sont ceux de
 * mod-custom-classes (version affc0a8) : sans la partie, ces scripts ne trouvent jamais leurs auras.
 *
 * ---------------------------------------------------------------------------
 * Yu Wu, bâton des Brumes (84035)
 *   - Don de Yu Wu (84960, passif) : chaque soin, 25 % de chances d'un Nuage de brume (84961, 10 au plus,
 *     60 s) : en base, aura de déclenchement et spell_proc. Chaque nuage gagné se pose aussi au sol près de
 *     l'allié soigné (84207), vu du seul Moine : spell_yuwu_don_nuage et npc_yuwu_nuage.
 *   - Don de Yu Wu (84962, utilisation, 2 s d'incantation) : consomme les nuages, soigne la cible de 1 800 (+20 % de
 *     la puissance des soins) par nuage. Pendant l'incantation, le Moine brandit son bâton ; chaque nuage du sol part
 *     en projectile (84963) vers lui, lancé pour arriver à la fin de l'incantation : spell_yuwu_don et npc_yuwu_nuage.
 *   - Brumes de Yu Wu (84964, passif) : un sort de soin instantané qui soigne, 10 % de chances (130 s de
 *     recharge interne, spell_proc) d'invoquer Yu'lon 12 s (84965) : spell_yuwu_brumes ; Yu'lon refait les
 *     sorts de soin du Moine sur les alliés les plus bas en vie, à 75 % : npc_yuwu_yulon, monk_weapons_yulon_copy
 *     et monk_weapons_yulon_soins (les Brumes de surtension, enveloppante et de rénovation y compris ;
 *     l'Extraction du mal, que le Moine lance sur lui-même, elle la lance sur l'allié).
 *   - Murmures de Shaohao (84966, passif) : la Brume apaisante du Moine et de sa statue rebondit sur 2 alliés
 *     de plus, les plus bas en vie, -33 % par rebond (84967) : monk_weapons_shaohao.
 * Jin Gu, bâton du Roi-Singe (84036)
 *   - Fût explosif (84980) : dégâts et menace en base ; les ennemis touchés ratent toutes leurs attaques de
 *     mêlée contre le Moine 3 s : monk_weapons_fut_explosif.
 *   - Paume au visage (84982) : Paume du tigre, 30 % de chances, double dégâts et -1 s sur les breuvages,
 *     4 s entre deux : monk_weapons_paume_au_visage.
 *   - Fortification de Jin Gu (84983) : +4 % d'esquive en posture du Buffle (le script du Report de
 *     mod-custom-classes ne lit aucun bonus extérieur : la solution de repli du cahier), en base.
 * Tian Lei et Tian Feng, Poings des Cieux (84037, 84038)
 *   - Poing de tonnerre (84920) : en base (20 s de recharge, 4 charges de 450 + 10 % PA de Nature) ; le coup qui
 *     pose les charges n'en use aucune : spell_tian_lei_charge.
 *   - Vents croisés (84460) : pendant Poings de fureur, une grue (84206) tournoie au-dessus de la cible, et le
 *     Moine frappe toutes les 0,5 s les ennemis à 8 m d'elle (84462) : monk_weapons_vents_croises et
 *     npc_tian_feng_grue.
 *   - Orage intérieur (84923, Tian Lei) : chaque Paume du tigre qui touche ajoute une charge (84924, 5 au plus) ;
 *     à 5, la Frappe du voile noir suivante fait tomber la foudre (84925) : spell_tian_lei_orage_interieur.
 *   - Lames de vent (84463, Tian Feng) : chaque coup du Coup tournoyant de la grue lance une lame de vent sur
 *     l'ennemi touché (84464) : spell_tian_feng_lames_de_vent.
 *   L'ensemble des deux poings (et la Frappe du Seigneur des vents qu'il apprenait) a été retiré le 25/10/2026.
 * ---------------------------------------------------------------------------
 */

#include "CellImpl.h"
#include "GameTime.h"
#include "GridNotifiers.h"
#include "Group.h"
#include "Player.h"
#include "ScriptMgr.h"
#include "ScriptedCreature.h"
#include "SpellAuraEffects.h"
#include "SpellInfo.h"
#include "SpellMgr.h"
#include "SpellScript.h"
#include "TemporarySummon.h"
#include <mutex>

// doit suivre GridNotifiers.h et CellImpl.h
#include "GridNotifiersImpl.h"
#include <unordered_map>
#include <vector>

enum MonkWeaponSpells
{
    // Yu Wu
    SPELL_YUWU_NUAGE            = 84961,
    SPELL_YUWU_NUAGE_PROJECTILE = 84963,
    SPELL_YUWU_YULON            = 84965,
    SPELL_YUWU_MURMURES         = 84966,
    SPELL_YUWU_MURMURES_SOIN    = 84967,
    // Jin Gu
    SPELL_JINGU_FUT_EXPLOSIF       = 84980,
    SPELL_JINGU_PAUME_AU_VISAGE    = 84982,
    // Poings des Cieux
    SPELL_TIANFENG_VENTS_CROISES   = 84460,
    SPELL_TIANFENG_GRUE_IMPULSION  = 84462,
    SPELL_TIANFENG_LAMES           = 84463,
    SPELL_TIANFENG_LAMES_COUP      = 84464,
    SPELL_TIANLEI_ORAGE            = 84923,
    SPELL_TIANLEI_ORAGE_CHARGE     = 84924,
    SPELL_TIANLEI_ORAGE_FOUDRE     = 84925,
    NPC_YUWU_YULON              = 84205,
    NPC_TIANFENG_GRUE              = 84206,
    NPC_YUWU_NUAGE                 = 84207,
    // les sorts du Moine (mod-custom-classes, premiers rangs)
    SPELL_MONK_TIGER_PALM          = 81113,
    SPELL_MONK_BLACKOUT_KICK       = 81125,
    SPELL_MONK_SPINNING_CRANE_DMG  = 81576,   // chaque coup du Coup tournoyant de la grue (81159 et ses rangs du Serpent)
    SPELL_MONK_FISTS_OF_FURY       = 81198,
    SPELL_MONK_SOOTHING_MIST       = 81771,
    SPELL_MONK_STATUE_SOOTHING     = 81896,   // la Brume apaisante de la statue du Serpent de jade
    // des sorts du Moine (mod-custom-classes, src/monk/monk_spells.cpp) : les trois Brumes ne soignent pas elles-mêmes, un
    // effet factice dont le script lance le soin, rang pour rang ; la copie refait la Brume (son script compte : la
    // Surtension y gagne ~10 %), et ramène à 75 % le soin périodique qu'elle pose
    SPELL_MONK_SURGING_MIST        = 81782,   // 8 rangs (son script lance le soin 81790 et suivants)
    SPELL_MONK_ENVELOPING_MIST     = 81798,   // 10 rangs ; le soin périodique : 81808 et suivants
    SPELL_MONK_ENVELOPING_MIST_HOT = 81808,
    SPELL_MONK_RENEWING_MIST       = 81818,   // 7 rangs ; le soin périodique : 81825 et suivants
    SPELL_MONK_RENEWING_MIST_HOT   = 81825,
    // l'Extraction du mal soigne le Moine qui la lance : la copie prend sa variante sur un allié (celle du glyphe), par
    // posture ; celle du Serpent a 8 rangs (niveaux 24 à 80), sa variante sur un allié 6 (niveaux 40 à 80) : les rangs 3 à
    // 8 y correspondent, niveau pour niveau
    SPELL_MONK_EXPEL_HARM          = 81148,
    SPELL_MONK_EXPEL_HARM_SERPENT  = 81925,
    SPELL_MONK_EXPEL_HARM_ALLY     = 82378,
    SPELL_MONK_EXPEL_HARM_ALLY_SERPENT = 82379,
    EXPEL_HARM_SERPENT_ALLY_DECALAGE = 2,      // rang du Serpent - 2 = rang de la variante
};

// les breuvages du Moine (mod-custom-classes) : Paume au visage réduit leur recharge
static constexpr uint32 MONK_BREUVAGES[] = {
    81745,   // Infusion purificatrice
    81749,   // Infusion insaisissable
    81156,   // Boisson fortifiante
    81157,   // Infusion agile
    81186,   // Infusion énergisante
    81189,   // Infusion œil-du-tigre
    82286,   // Brassage du chi
};

static constexpr float YULON_PORTEE     = 40.0f;   // les alliés que Yu'lon soigne, autour d'elle
static constexpr int32 YULON_PART       = 75;      // % des soins du Moine que font ses copies (Maitre, 25/10/2026 00:13 UTC)
static constexpr uint32 YULON_ALLURE    = 250;     // ms entre deux recopies des vitesses du Moine
static constexpr uint32 YULON_ATTENTE   = 3000;    // ms pendant lesquels le soin périodique d'une copie est attendu
static constexpr float SHAOHAO_PORTEE   = 40.0f;   // les alliés des rebonds, autour de la cible soignée
static constexpr uint32 SHAOHAO_REBONDS = 2;
static constexpr uint32 GRUE_PERIODE    = 500;     // ms, une impulsion de Vents croisés
static constexpr float GRUE_PORTEE      = 8.0f;    // la portée de Poings de fureur : la cible de la grue sans cible du Moine
static constexpr uint32 GRUE_SANS_POINGS = 1500;   // ms sans Poings de fureur avant que la grue s'en aille
static constexpr uint32 GRUE_VIE_MAX     = 10000;  // ms, la durée de vie de la grue au plus
static constexpr uint32 PAUME_RECHARGE  = 4000;    // ms entre deux Paumes au visage
static constexpr int32 PAUME_BREUVAGES  = -1000;   // ms ôtées aux breuvages
static constexpr uint32 NUAGES_MAX      = 10;      // les cumuls de 84961
static constexpr uint32 NUAGE_DUREE     = 60000;   // ms, la durée de 84961
static constexpr float NUAGE_ECART      = 2.5f;    // le nuage se pose à cette distance de l'allié soigné
static constexpr float NUAGE_VITESSE    = 20.0f;   // m/s, le projectile 84963 (la vitesse de son Spell.dbc, tools/monk_part.py)
static constexpr uint32 NUAGE_FONDU     = 200;     // ms : le nuage devient invisible quand son projectile part
static constexpr uint32 ORAGE_CHARGES   = 5;

namespace
{
    std::mutex monkWeaponsLock;
    // vrai pendant qu'une copie de Yu'lon se lance : ses soins directs arrivent avant le retour de CastSpell (déclenché,
    // sans temps d'incantation), monk_weapons_yulon_soins les ramène à 75 %
    thread_local bool copieDeYulon = false;

    // les soins périodiques que posent les copies de Yu'lon, à ramener à 75 % quand ils arrivent : la Brume de rénovation
    // est un projectile (vitesse 30), son soin se pose après le retour de CastSpell
    struct SoinAttendu
    {
        ObjectGuid moine;
        ObjectGuid cible;
        uint32 sort;
        Milliseconds jusqua;
    };
    std::vector<SoinAttendu> soinsAttendus;
    std::unordered_map<ObjectGuid, ObjectGuid> yulonDuMoine;          // le Moine -> sa Yu'lon
    std::unordered_map<ObjectGuid, ObjectGuid> cibleDeLaGrue;         // le Moine -> la cible de sa prochaine grue
    std::unordered_map<ObjectGuid, std::vector<ObjectGuid>> nuagesDuMoine;   // le Moine -> ses nuages au sol, du plus ancien au plus récent

    // les nuages du Moine, retirés de la liste (ceux qui ont déjà disparu sont omis)
    std::vector<Creature*> PrendsNuages(Unit* moine)
    {
        std::vector<ObjectGuid> guids;
        {
            std::lock_guard<std::mutex> garde(monkWeaponsLock);
            auto it = nuagesDuMoine.find(moine->GetGUID());
            if (it == nuagesDuMoine.end())
                return {};
            guids.swap(it->second);
            nuagesDuMoine.erase(it);
        }
        std::vector<Creature*> nuages;
        for (ObjectGuid const& guid : guids)
            if (Creature* nuage = ObjectAccessor::GetCreature(*moine, guid))
                nuages.push_back(nuage);
        return nuages;
    }

    // les alliés (le groupe du Moine, ou lui seul) autour d'un point, vivants et blessés, du plus bas en vie au plus haut
    std::vector<Unit*> AlliesBlesses(Player* moine, WorldObject const* centre, float portee, Unit const* sauf)
    {
        std::vector<Unit*> allies;
        auto consider = [&](Player* membre)
        {
            if (membre && membre != sauf && membre->IsAlive() && membre->IsInMap(centre) && centre->IsWithinDistInMap(membre, portee)
                && membre->GetHealth() < membre->GetMaxHealth())
                allies.push_back(membre);
        };
        if (Group* groupe = moine->GetGroup())
        {
            for (GroupReference* ref = groupe->GetFirstMember(); ref; ref = ref->next())
                consider(ref->GetSource());
        }
        else
            consider(moine);
        std::sort(allies.begin(), allies.end(), [](Unit* a, Unit* b) { return a->GetHealthPct() < b->GetHealthPct(); });
        return allies;
    }

    // un sort qui soigne : directement, en pourcentage, ou par une aura de soin périodique
    bool Soigne(SpellInfo const* sort)
    {
        for (SpellEffectInfo const& effet : sort->GetEffects())
            if (effet.Effect == SPELL_EFFECT_HEAL || effet.Effect == SPELL_EFFECT_HEAL_PCT || effet.Effect == SPELL_EFFECT_HEAL_MAX_HEALTH
                || (effet.Effect == SPELL_EFFECT_APPLY_AURA && (effet.ApplyAuraName == SPELL_AURA_PERIODIC_HEAL
                                                               || effet.ApplyAuraName == SPELL_AURA_OBS_MOD_HEALTH)))
                return true;
        return false;
    }
}

/*
 * spell_yuwu_don — sort 84962 (utilisation de Yu Wu)
 * Refusé sans nuage ; le soin de la base (1 800 + 20 % de la puissance des soins, spell_bonus_data) est
 * multiplié par le nombre de nuages, qui sont alors consommés.
 */
class spell_yuwu_don : public SpellScript
{
    PrepareSpellScript(spell_yuwu_don);

    uint8 nuages = 0;
    bool lances = false;

    // le premier contrôle (Spell::prepare, au début de l'incantation) lance les nuages : chacun part au moment où son
    // projectile, à NUAGE_VITESSE, arrive sur le Moine à la fin de l'incantation ; le second (Spell::cast) ne refait rien
    SpellCastResult CheckCast()
    {
        Unit* moine = GetCaster();
        if (!moine || !moine->HasAura(SPELL_YUWU_NUAGE))
            return SPELL_FAILED_CASTER_AURASTATE;
        if (!lances)
        {
            lances = true;
            uint32 const incantation = GetSpellInfo()->CalcCastTime(moine);
            for (Creature* nuage : PrendsNuages(moine))
            {
                uint32 const vol = uint32(1000.0f * nuage->GetDistance(moine) / NUAGE_VITESSE);
                nuage->AI()->SetGUID(moine->GetGUID());
                nuage->AI()->SetData(0, incantation > vol ? incantation - vol : 0);
            }
        }
        return SPELL_CAST_OK;
    }

    void HandleHeal(SpellEffIndex /*effIndex*/)
    {
        Unit* moine = GetCaster();
        Aura* aura = moine ? moine->GetAura(SPELL_YUWU_NUAGE) : nullptr;
        nuages = aura ? aura->GetStackAmount() : 0;
        SetHitHeal(GetHitHeal() * nuages);
    }

    void HandleAfterHit()
    {
        Unit* moine = GetCaster();
        if (!moine || !nuages)
            return;
        // les nuages sont partis au début de l'incantation (CheckCast)
        moine->RemoveAurasDueToSpell(SPELL_YUWU_NUAGE);
    }

    void Register() override
    {
        OnCheckCast += SpellCheckCastFn(spell_yuwu_don::CheckCast);
        OnEffectHitTarget += SpellEffectFn(spell_yuwu_don::HandleHeal, EFFECT_0, SPELL_EFFECT_HEAL);
        AfterHit += SpellHitFn(spell_yuwu_don::HandleAfterHit);
    }
};

/*
 * spell_yuwu_don_nuage — sort 84960 (passif de Yu Wu)
 * Après chaque Nuage de brume gagné (la base lance 84961), un nuage (84207) se pose au sol près de l'allié soigné,
 * vu du seul Moine (SummonCreature, visibleBySummonerOnly). Il dure ce que dure un cumul ; au-delà de 10, le plus
 * ancien s'en va.
 */
class spell_yuwu_don_nuage : public AuraScript
{
    PrepareAuraScript(spell_yuwu_don_nuage);

    void HandleAfterProc(AuraEffect const* /*aurEff*/, ProcEventInfo& eventInfo)
    {
        Unit* moine = GetTarget();
        if (!moine || !moine->HasAura(SPELL_YUWU_NUAGE))
            return;
        Unit* soigne = eventInfo.GetProcTarget();
        WorldObject* pres = soigne && soigne->IsInMap(moine) ? static_cast<WorldObject*>(soigne) : moine;
        Position pos = pres->GetRandomNearPosition(NUAGE_ECART);
        TempSummon* nuage = moine->SummonCreature(NPC_YUWU_NUAGE, pos, TEMPSUMMON_TIMED_DESPAWN, NUAGE_DUREE, 0, nullptr, true);
        if (!nuage)
            return;
        ObjectGuid trop;
        {
            std::lock_guard<std::mutex> garde(monkWeaponsLock);
            std::vector<ObjectGuid>& liste = nuagesDuMoine[moine->GetGUID()];
            liste.push_back(nuage->GetGUID());
            if (liste.size() > NUAGES_MAX)
            {
                trop = liste.front();
                liste.erase(liste.begin());
            }
        }
        if (!trop.IsEmpty())
            if (Creature* ancien = ObjectAccessor::GetCreature(*moine, trop))
                ancien->DespawnOrUnsummon();
    }

    void Register() override
    {
        AfterEffectProc += AuraEffectProcFn(spell_yuwu_don_nuage::HandleAfterProc, EFFECT_0, SPELL_AURA_PROC_TRIGGER_SPELL);
    }
};

/*
 * spell_yuwu_nuage — sort 84961 (les Nuages de brume, en cumuls)
 * L'aura qui expire, ou part autrement que par le Don (la mort, une dissipation), emporte les nuages du sol.
 */
class spell_yuwu_nuage : public AuraScript
{
    PrepareAuraScript(spell_yuwu_nuage);

    void HandleRemove(AuraEffect const* /*aurEff*/, AuraEffectHandleModes /*mode*/)
    {
        if (Unit* moine = GetTarget())
            for (Creature* nuage : PrendsNuages(moine))
                nuage->DespawnOrUnsummon();
    }

    void Register() override
    {
        AfterEffectRemove += AuraEffectRemoveFn(spell_yuwu_nuage::HandleRemove, EFFECT_0, SPELL_AURA_DUMMY, AURA_EFFECT_HANDLE_REAL);
    }
};

/*
 * npc_yuwu_nuage — créature 84207, un Nuage de brume au sol (le nuage du Don de Sheilun, porté du retail)
 * Immobile et inerte. Le Don lui donne le Moine (SetGUID) puis le délai avant son départ (SetData) : à l'heure, il
 * lance sur le Moine son projectile (84963), s'efface, et disparaît une fois le projectile arrivé (un lanceur qui
 * disparaît trop tôt emporterait son projectile).
 */
struct npc_yuwu_nuage : public ScriptedAI
{
    npc_yuwu_nuage(Creature* creature) : ScriptedAI(creature)
    {
        me->SetReactState(REACT_PASSIVE);
    }

    ObjectGuid moineGuid;
    int32 depart = -1;                     // ms avant le départ ; -1 : pas encore appelé

    void SetGUID(ObjectGuid const& guid, int32 /*id*/) override { moineGuid = guid; }
    void SetData(uint32 /*id*/, uint32 delai) override { depart = int32(delai); }

    void AttackStart(Unit* /*who*/) override { }
    void MoveInLineOfSight(Unit* /*who*/) override { }

    void UpdateAI(uint32 diff) override
    {
        if (depart < 0)
            return;
        if (depart > int32(diff))
        {
            depart -= int32(diff);
            return;
        }
        depart = -1;
        Unit* moine = ObjectAccessor::GetUnit(*me, moineGuid);
        if (!moine)
        {
            me->DespawnOrUnsummon();
            return;
        }
        uint32 const vol = uint32(1000.0f * me->GetDistance(moine) / NUAGE_VITESSE);
        me->CastSpell(moine, SPELL_YUWU_NUAGE_PROJECTILE, true);
        me->SetDisplayId(11686);           // invisible : le nuage est devenu son projectile
        me->DespawnOrUnsummon(Milliseconds(vol + NUAGE_FONDU + 1000));
    }
};

/*
 * spell_yuwu_brumes — sort 84964 (passif de Yu Wu)
 * Les ProcFlags prennent tous les soins faits ; le cahier dit « sort de soin instantané qui soigne une cible » :
 * un soin sans temps d'incantation, ni canalisé, qui a soigné. Les 10 % et les 130 s sont en base (spell_proc).
 */
class spell_yuwu_brumes : public AuraScript
{
    PrepareAuraScript(spell_yuwu_brumes);

    bool CheckProc(ProcEventInfo& eventInfo)
    {
        SpellInfo const* sort = eventInfo.GetSpellInfo();
        HealInfo const* soin = eventInfo.GetHealInfo();
        return sort && soin && soin->GetHeal() > 0 && !sort->IsChanneled() && sort->CalcCastTime() == 0 && Soigne(sort);
    }

    void HandleProc(AuraEffect const* /*aurEff*/, ProcEventInfo& /*eventInfo*/)
    {
        PreventDefaultAction();
        if (Unit* moine = GetTarget())
            moine->CastSpell(moine, SPELL_YUWU_YULON, true);
    }

    void Register() override
    {
        DoCheckProc += AuraCheckProcFn(spell_yuwu_brumes::CheckProc);
        OnEffectProc += AuraEffectProcFn(spell_yuwu_brumes::HandleProc, EFFECT_0, SPELL_AURA_DUMMY);
    }
};

/*
 * npc_yuwu_yulon — créature 84205, invoquée 12 s par 84965 (gardien)
 * Elle vole et suit le Moine ; monk_weapons_yulon_copy lui fait refaire ses sorts de soin.
 */
struct npc_yuwu_yulon : public ScriptedAI
{
    npc_yuwu_yulon(Creature* creature) : ScriptedAI(creature)
    {
        me->SetReactState(REACT_PASSIVE);
    }

    ObjectGuid moineGuid;

    ~npc_yuwu_yulon() override
    {
        std::lock_guard<std::mutex> garde(monkWeaponsLock);
        auto it = yulonDuMoine.find(moineGuid);
        if (it != yulonDuMoine.end() && it->second == me->GetGUID())
            yulonDuMoine.erase(it);
    }

    void IsSummonedBy(WorldObject* summoner) override
    {
        Player* moine = summoner ? summoner->ToPlayer() : nullptr;
        if (!moine)
        {
            me->DespawnOrUnsummon();
            return;
        }
        moineGuid = moine->GetGUID();
        {
            std::lock_guard<std::mutex> garde(monkWeaponsLock);
            yulonDuMoine[moineGuid] = me->GetGUID();
        }
        me->SetDisableGravity(true);
        me->SetCanFly(true);
        me->SetHover(true);
        Allure(moine);
        me->GetMotionMaster()->MoveFollow(moine, 3.0f, float(M_PI));
    }

    // Un gardien sans barre de familier garde sa propre vitesse quand il suit (TargetedMovementGenerator.cpp, GetVelocity) :
    // plus rapide que le Moine, Yu'lon le rattrapait, s'arrêtait, repartait, et son animation de vol repartait à zéro à
    // chaque fois. Elle prend donc les vitesses du Moine, recopiées tant qu'elle le suit (monture, ralentissement...).
    uint32 allure = YULON_ALLURE;

    void Allure(Unit* moine)
    {
        for (UnitMoveType type : { MOVE_WALK, MOVE_RUN, MOVE_FLIGHT })
        {
            float const vitesse = moine->GetSpeedRate(moine->IsFlying() ? MOVE_FLIGHT : (type == MOVE_WALK ? MOVE_WALK : MOVE_RUN));
            if (me->GetSpeedRate(type) != vitesse)
                me->SetSpeed(type, vitesse);
        }
    }

    void AttackStart(Unit* /*who*/) override { }

    void UpdateAI(uint32 diff) override
    {
        if (allure > diff)
        {
            allure -= diff;
            return;
        }
        allure = YULON_ALLURE;
        if (Player* moine = ObjectAccessor::GetPlayer(*me, moineGuid))
            Allure(moine);
    }
};

// la copie d'un sort du Moine : le sort que le Moine relance pour Yu'lon (0 : aucun), et le soin périodique qu'il pose,
// ramené à 75 % après coup (0 : aucun). Les trois Brumes se refont elles-mêmes (leur script pose le soin) ; l'Extraction du
// mal, qui soigne son lanceur, devient sa variante sur un allié ; tout autre sort qui soigne reste lui-même, sauf s'il ne
// vise que son lanceur
struct CopieDeYulon
{
    uint32 lance = 0;
    uint32 periodique = 0;
};

static CopieDeYulon SortDeYulon(SpellInfo const* sort)
{
    uint32 const premier = sort->GetFirstRankSpell()->Id;
    uint32 const rang = sort->Id - premier;
    switch (premier)
    {
        case SPELL_MONK_SURGING_MIST:       return { sort->Id, 0 };
        case SPELL_MONK_ENVELOPING_MIST:    return { sort->Id, SPELL_MONK_ENVELOPING_MIST_HOT + rang };
        case SPELL_MONK_RENEWING_MIST:      return { sort->Id, SPELL_MONK_RENEWING_MIST_HOT + rang };
        case SPELL_MONK_EXPEL_HARM:         return { SPELL_MONK_EXPEL_HARM_ALLY, 0 };
        case SPELL_MONK_EXPEL_HARM_SERPENT:
            return { SPELL_MONK_EXPEL_HARM_ALLY_SERPENT + (rang > EXPEL_HARM_SERPENT_ALLY_DECALAGE ? rang - EXPEL_HARM_SERPENT_ALLY_DECALAGE : 0), 0 };
        default: break;
    }
    if (!Soigne(sort))
        return {};
    for (SpellEffectInfo const& effet : sort->GetEffects())
        if (effet.IsEffect() && effet.TargetA.GetTarget() != TARGET_UNIT_CASTER)
            return { sort->Id, sort->Id };
    return {};
}

// Yu'lon refait chaque sort de soin que le Moine lance lui-même (pas un sort déclenché) sur l'allié le plus bas
// en vie autour d'elle. La copie part du Moine, déclenchée : lancée par Yu'lon, elle perdait les modificateurs de sorts du
// Moine (un gardien n'en a pas : 68 % au lieu de 75 % sur la Brume de surtension) et l'Extraction du mal, qui se calcule sur
// l'arme et la puissance d'attaque de son lanceur, ne soignait plus que 9 %. Yu'lon, elle, joue le lancer.
class monk_weapons_yulon_copy : public PlayerScript
{
public:
    monk_weapons_yulon_copy() : PlayerScript("monk_weapons_yulon_copy", { PLAYERHOOK_ON_SPELL_CAST }) { }

    void OnPlayerSpellCast(Player* moine, Spell* spell, bool /*skipCheck*/) override
    {
        if (!spell || spell->IsTriggered())
            return;
        CopieDeYulon const copie = SortDeYulon(spell->GetSpellInfo());
        if (!copie.lance || !sSpellMgr->GetSpellInfo(copie.lance))
            return;
        ObjectGuid yulonGuid;
        {
            std::lock_guard<std::mutex> garde(monkWeaponsLock);
            auto it = yulonDuMoine.find(moine->GetGUID());
            if (it == yulonDuMoine.end())
                return;
            yulonGuid = it->second;
        }
        Creature* yulon = ObjectAccessor::GetCreature(*moine, yulonGuid);
        if (!yulon || !yulon->IsAlive())
            return;
        std::vector<Unit*> allies = AlliesBlesses(moine, yulon, YULON_PORTEE, nullptr);
        Unit* cible = allies.empty() ? moine : allies.front();
        // son soin périodique : le montant de chaque tic est fixé à la pose ; monk_weapons_yulon_soins le ramène à 75 % quand
        // il arrive (tout de suite, ou à l'arrivée du projectile)
        if (copie.periodique)
        {
            std::lock_guard<std::mutex> garde(monkWeaponsLock);
            soinsAttendus.push_back({ moine->GetGUID(), cible->GetGUID(), copie.periodique, GameTime::GetGameTimeMS() + Milliseconds(YULON_ATTENTE) });
        }
        copieDeYulon = true;
        moine->CastSpell(cible, copie.lance, TRIGGERED_FULL_MASK);
        copieDeYulon = false;
        yulon->HandleEmoteCommand(EMOTE_ONESHOT_SPELL_CAST_OMNI);
    }
};

// les soins d'une copie de Yu'lon : 75 % de ceux du Moine. Les directs pendant la copie ; les périodiques à leur pose,
// d'après soinsAttendus. Les rebonds de la Brume de rénovation, que son script refait à chaque tic avec le Moine pour
// lanceur, ne se distinguent plus des siens : ils restent à 100 %.
class monk_weapons_yulon_soins : public UnitScript
{
public:
    monk_weapons_yulon_soins() : UnitScript("monk_weapons_yulon_soins", true, { UNITHOOK_MODIFY_HEAL_RECEIVED, UNITHOOK_ON_AURA_APPLY }) { }

    void ModifyHealReceived(Unit* /*cible*/, Unit* /*lanceur*/, uint32& soin, SpellInfo const* /*sort*/) override
    {
        if (copieDeYulon)
            soin = CalculatePct(soin, YULON_PART);
    }

    void OnAuraApply(Unit* cible, Aura* aura) override
    {
        if (!cible || !aura)
            return;
        Milliseconds const maintenant = GameTime::GetGameTimeMS();
        bool trouve = false;
        {
            std::lock_guard<std::mutex> garde(monkWeaponsLock);
            if (soinsAttendus.empty())
                return;
            for (auto it = soinsAttendus.begin(); it != soinsAttendus.end();)
            {
                if (it->jusqua < maintenant)
                    it = soinsAttendus.erase(it);
                else if (!trouve && it->sort == aura->GetId() && it->moine == aura->GetCasterGUID() && it->cible == cible->GetGUID())
                {
                    trouve = true;
                    it = soinsAttendus.erase(it);
                }
                else
                    ++it;
            }
        }
        if (!trouve)
            return;
        for (uint8 i = 0; i < MAX_SPELL_EFFECTS; ++i)
            if (AuraEffect* effet = aura->GetEffect(i))
                if (effet->GetAuraType() == SPELL_AURA_PERIODIC_HEAL)
                    effet->ChangeAmount(CalculatePct(effet->GetAmount(), YULON_PART));
    }
};

// Murmures de Shaohao : chaque soin de la Brume apaisante du Moine ou de sa statue (soin périodique : le hook
// reçoit la cible puis le lanceur, SpellAuraEffects.cpp 6657) rebondit sur les 2 alliés les plus bas en vie autour
// de la cible, chaque rebond à -33 % (l'aura 84966, son effet 0) du précédent
class monk_weapons_shaohao : public UnitScript
{
public:
    monk_weapons_shaohao() : UnitScript("monk_weapons_shaohao", true, { UNITHOOK_MODIFY_HEAL_RECEIVED }) { }

    void ModifyHealReceived(Unit* cible, Unit* lanceur, uint32& soin, SpellInfo const* sort) override
    {
        if (!sort || !cible || !lanceur || !soin)
            return;
        uint32 const premier = sort->GetFirstRankSpell()->Id;
        if (premier != SPELL_MONK_SOOTHING_MIST && premier != SPELL_MONK_STATUE_SOOTHING)
            return;
        Player* moine = lanceur->GetCharmerOrOwnerPlayerOrPlayerItself();
        AuraEffect const* murmures = moine ? moine->GetAuraEffect(SPELL_YUWU_MURMURES, EFFECT_0) : nullptr;
        if (!murmures)
            return;
        int32 montant = int32(soin);
        uint32 rebonds = 0;
        for (Unit* allie : AlliesBlesses(moine, cible, SHAOHAO_PORTEE, cible))
        {
            if (rebonds++ >= SHAOHAO_REBONDS)
                break;
            montant = std::max<int32>(1, CalculatePct(montant, 100 + murmures->GetAmount()));
            moine->CastCustomSpell(allie, SPELL_YUWU_MURMURES_SOIN, &montant, nullptr, nullptr, true);
        }
    }
};

// Fût explosif : un ennemi qui porte son aura (84980, 3 s) rate toutes ses attaques de mêlée contre le Moine qui
// l'a lancé, et contre lui seul
class monk_weapons_fut_explosif : public UnitScript
{
public:
    monk_weapons_fut_explosif() : UnitScript("monk_weapons_fut_explosif", true, { UNITHOOK_ON_BEFORE_ROLL_MELEE_OUTCOME_AGAINST }) { }

    void OnBeforeRollMeleeOutcomeAgainst(Unit const* attaquant, Unit const* victime, WeaponAttackType /*attType*/, int32& /*attackerMaxSkillValueForLevel*/,
        int32& /*victimMaxSkillValueForLevel*/, int32& /*attackerWeaponSkill*/, int32& /*victimDefenseSkill*/, int32& crit_chance,
        int32& miss_chance, int32& dodge_chance, int32& parry_chance, int32& block_chance) override
    {
        if (!attaquant || !victime || !attaquant->HasAura(SPELL_JINGU_FUT_EXPLOSIF, victime->GetGUID()))
            return;
        miss_chance = 10000;
        crit_chance = dodge_chance = parry_chance = block_chance = 0;
    }
};

// Paume au visage : la Paume du tigre du Moine qui la porte, à ses chances (l'aura 84982, son effet 0), double ses
// dégâts et ôte 1 s à la recharge de ses breuvages ; pas plus d'une fois toutes les 4 s
class monk_weapons_paume_au_visage : public UnitScript
{
public:
    monk_weapons_paume_au_visage() : UnitScript("monk_weapons_paume_au_visage", true, { UNITHOOK_MODIFY_SPELL_DAMAGE_TAKEN }) { }

    void ModifySpellDamageTaken(Unit* /*cible*/, Unit* attaquant, int32& degats, SpellInfo const* sort) override
    {
        Player* moine = attaquant ? attaquant->ToPlayer() : nullptr;
        if (!moine || !sort || degats <= 0 || sort->GetFirstRankSpell()->Id != SPELL_MONK_TIGER_PALM)
            return;
        AuraEffect const* paume = moine->GetAuraEffect(SPELL_JINGU_PAUME_AU_VISAGE, EFFECT_0);
        if (!paume || moine->HasSpellCooldown(SPELL_JINGU_PAUME_AU_VISAGE) || !roll_chance_i(paume->GetAmount()))
            return;
        degats *= 2;
        for (uint32 breuvage : MONK_BREUVAGES)
            if (moine->HasSpellCooldown(breuvage))
                moine->ModifySpellCooldown(breuvage, PAUME_BREUVAGES);
        moine->AddSpellCooldown(SPELL_JINGU_PAUME_AU_VISAGE, 0, PAUME_RECHARGE);
    }
};

// Vents croisés : quand le Moine qui porte Tian Feng lance Poings de fureur, une grue (84206) se pose sur sa cible, ou
// sur l'ennemi le plus proche à 8 m, pour la durée de la canalisation
class monk_weapons_vents_croises : public PlayerScript
{
public:
    monk_weapons_vents_croises() : PlayerScript("monk_weapons_vents_croises", { PLAYERHOOK_ON_SPELL_CAST }) { }

    void OnPlayerSpellCast(Player* moine, Spell* spell, bool /*skipCheck*/) override
    {
        if (!spell || spell->GetSpellInfo()->GetFirstRankSpell()->Id != SPELL_MONK_FISTS_OF_FURY || !moine->HasAura(SPELL_TIANFENG_VENTS_CROISES))
            return;
        // sa cible, ou, sans cible (Poings de fureur n'en demande pas), l'ennemi le plus proche à portée de ses poings
        Unit* cible = moine->GetVictim();
        if (!cible)
            cible = moine->GetSelectedUnit();
        if (!cible || !moine->IsValidAttackTarget(cible))
        {
            // NearestAttackableUnitInObjectRangeCheck ne prend qu'un ennemi hostile ou déjà en combat : un mannequin neutre
            // lui échappait. Tout ce que le Moine peut attaquer, le plus proche
            cible = nullptr;
            std::list<Unit*> autour;
            Acore::AnyUnfriendlyUnitInObjectRangeCheck verif(moine, moine, GRUE_PORTEE);
            Acore::UnitListSearcher<Acore::AnyUnfriendlyUnitInObjectRangeCheck> chercheur(moine, autour, verif);
            Cell::VisitObjects(moine, chercheur, GRUE_PORTEE);
            float plusPres = GRUE_PORTEE + 1.0f;
            for (Unit* u : autour)
                if (u->IsAlive() && moine->IsValidAttackTarget(u) && moine->GetDistance(u) < plusPres)
                {
                    plusPres = moine->GetDistance(u);
                    cible = u;
                }
        }
        if (!cible)
            return;
        {
            std::lock_guard<std::mutex> garde(monkWeaponsLock);
            cibleDeLaGrue[moine->GetGUID()] = cible->GetGUID();
        }
        // la grue part d'elle-même quand les Poings de fureur cessent (npc_tian_feng_grue) ; GRUE_VIE_MAX n'est qu'un filet
        moine->SummonCreature(NPC_TIANFENG_GRUE, cible->GetPosition(), TEMPSUMMON_TIMED_DESPAWN, GRUE_VIE_MAX);
    }
};

/*
 * npc_tian_feng_grue — créature 84206
 * Prend la faction du Moine et se tient au-dessus de sa cible ; toutes les 0,5 s, le Moine frappe les ennemis à 8 m
 * de la cible (84462). Elle part si le Moine ne canalise plus Poings de fureur, ou si la cible meurt.
 */
struct npc_tian_feng_grue : public ScriptedAI
{
    npc_tian_feng_grue(Creature* creature) : ScriptedAI(creature)
    {
        me->SetReactState(REACT_PASSIVE);
    }

    ObjectGuid moineGuid;
    ObjectGuid cibleGuid;
    uint32 minuteur = GRUE_PERIODE;
    uint32 sansPoings = 0;                 // ms depuis que le Moine n'a plus Poings de fureur

    void IsSummonedBy(WorldObject* summoner) override
    {
        Player* moine = summoner ? summoner->ToPlayer() : nullptr;
        if (!moine)
        {
            me->DespawnOrUnsummon();
            return;
        }
        moineGuid = moine->GetGUID();
        {
            std::lock_guard<std::mutex> garde(monkWeaponsLock);
            auto it = cibleDeLaGrue.find(moineGuid);
            if (it != cibleDeLaGrue.end())
            {
                cibleGuid = it->second;
                cibleDeLaGrue.erase(it);
            }
        }
        me->SetFaction(moine->GetFaction());
        me->SetDisableGravity(true);
        me->SetCanFly(true);
    }

    void AttackStart(Unit* /*who*/) override { }

    void UpdateAI(uint32 diff) override
    {
        if (minuteur > diff)
        {
            minuteur -= diff;
            return;
        }
        minuteur = GRUE_PERIODE;
        Player* moine = ObjectAccessor::GetPlayer(*me, moineGuid);
        Unit* cible = ObjectAccessor::GetUnit(*me, cibleGuid);
        // Poings de fureur de mod-custom-classes : une aura (81198) qui frappe par 81612 et 81613, pas une canalisation que le
        // cœur connaît ; elle est posée, retirée au bout d'une seconde, puis reposée pour le reste du sort. La grue frappe
        // tant qu'elle est là, attend pendant le trou, et ne part qu'après GRUE_SANS_POINGS sans elle
        Spell const* canal = moine ? moine->GetCurrentSpell(CURRENT_CHANNELED_SPELL) : nullptr;
        bool const poings = moine && (moine->HasAura(SPELL_MONK_FISTS_OF_FURY)
            || (canal && canal->GetSpellInfo()->GetFirstRankSpell()->Id == SPELL_MONK_FISTS_OF_FURY));
        if (!moine || !cible || !cible->IsAlive())
        {
            me->DespawnOrUnsummon();
            return;
        }
        if (!poings)
        {
            sansPoings += GRUE_PERIODE;
            if (sansPoings >= GRUE_SANS_POINGS)
                me->DespawnOrUnsummon();
            return;
        }
        sansPoings = 0;
        me->NearTeleportTo(cible->GetPositionX(), cible->GetPositionY(), cible->GetPositionZ() + 2.0f, me->GetOrientation());
        // la grue n'est que l'image : une créature ne trouve pas de cible contre un mannequin neutre ; le Moine lance
        // l'impulsion sur la cible (84462 : 8 m autour d'elle), avec ses propres règles d'attaque
        moine->CastSpell(cible, SPELL_TIANFENG_GRUE_IMPULSION, TRIGGERED_FULL_MASK);
    }
};

/*
 * spell_tian_lei_charge — sort 84921 (Poing de tonnerre, les 4 charges)
 * Le coup qui pose l'aura se poursuit dans la même mise à jour du monde (la seconde main, les coups d'une même
 * technique) : sans garde, il usait déjà une charge. Rien ne se déclenche dans la milliseconde de jeu où l'aura est
 * posée : les 4 charges vont aux 4 attaques suivantes.
 */
class spell_tian_lei_charge : public AuraScript
{
    PrepareAuraScript(spell_tian_lei_charge);

    Milliseconds pose = Milliseconds::zero();

    void HandleApply(AuraEffect const* /*aurEff*/, AuraEffectHandleModes /*mode*/)
    {
        pose = GameTime::GetGameTimeMS();
    }

    // et jamais sur le Moine lui-même (un effet d'une technique qui le vise, comme le chi de la Paume du tigre)
    bool CheckProc(ProcEventInfo& eventInfo)
    {
        Unit* cible = eventInfo.GetProcTarget();
        return GameTime::GetGameTimeMS() != pose && cible && cible != GetTarget();
    }

    void Register() override
    {
        AfterEffectApply += AuraEffectApplyFn(spell_tian_lei_charge::HandleApply, EFFECT_0, SPELL_AURA_PROC_TRIGGER_SPELL,
            AURA_EFFECT_HANDLE_REAL_OR_REAPPLY_MASK);
        DoCheckProc += AuraCheckProcFn(spell_tian_lei_charge::CheckProc);
    }
};

/*
 * spell_tian_lei_orage_interieur — sort 84923 (passif de Tian Lei)
 * Chaque Paume du tigre qui touche ajoute une charge (84924, visible, 5 au plus). À 5 charges, la Frappe du voile noir
 * qui touche fait tomber la foudre sur sa cible (84925 : la cible et les ennemis à 8 m), puis retire les charges.
 */
class spell_tian_lei_orage_interieur : public AuraScript
{
    PrepareAuraScript(spell_tian_lei_orage_interieur);

    bool CheckProc(ProcEventInfo& eventInfo)
    {
        SpellInfo const* sort = eventInfo.GetSpellInfo();
        DamageInfo const* degats = eventInfo.GetDamageInfo();
        if (!sort || !degats || !degats->GetDamage() || !eventInfo.GetProcTarget())
            return false;
        uint32 const premier = sort->GetFirstRankSpell()->Id;
        return premier == SPELL_MONK_TIGER_PALM || premier == SPELL_MONK_BLACKOUT_KICK;
    }

    void HandleProc(AuraEffect const* /*aurEff*/, ProcEventInfo& eventInfo)
    {
        PreventDefaultAction();
        Unit* moine = GetTarget();
        Unit* cible = eventInfo.GetProcTarget();
        if (!moine || !cible)
            return;
        if (eventInfo.GetSpellInfo()->GetFirstRankSpell()->Id == SPELL_MONK_TIGER_PALM)
        {
            moine->CastSpell(moine, SPELL_TIANLEI_ORAGE_CHARGE, true);
            return;
        }
        Aura* charges = moine->GetAura(SPELL_TIANLEI_ORAGE_CHARGE);
        if (!charges || charges->GetStackAmount() < ORAGE_CHARGES)
            return;
        moine->CastSpell(cible, SPELL_TIANLEI_ORAGE_FOUDRE, true);
        moine->RemoveAurasDueToSpell(SPELL_TIANLEI_ORAGE_CHARGE);
    }

    void Register() override
    {
        DoCheckProc += AuraCheckProcFn(spell_tian_lei_orage_interieur::CheckProc);
        OnEffectProc += AuraEffectProcFn(spell_tian_lei_orage_interieur::HandleProc, EFFECT_0, SPELL_AURA_DUMMY);
    }
};

/*
 * spell_tian_feng_lames_de_vent — sort 84463 (passif de Tian Feng)
 * Chaque coup du Coup tournoyant de la grue (81576, un par ennemi et par tic) lance une lame de vent (84464) sur
 * l'ennemi touché. Ces coups sont déclenchés par l'aura du Coup tournoyant : la ligne spell_proc de 84463 porte
 * PROC_ATTR_TRIGGERED_CAN_PROC.
 */
class spell_tian_feng_lames_de_vent : public AuraScript
{
    PrepareAuraScript(spell_tian_feng_lames_de_vent);

    bool CheckProc(ProcEventInfo& eventInfo)
    {
        SpellInfo const* sort = eventInfo.GetSpellInfo();
        DamageInfo const* degats = eventInfo.GetDamageInfo();
        return sort && degats && degats->GetDamage() && eventInfo.GetProcTarget()
            && sort->GetFirstRankSpell()->Id == SPELL_MONK_SPINNING_CRANE_DMG;
    }

    void HandleProc(AuraEffect const* /*aurEff*/, ProcEventInfo& eventInfo)
    {
        PreventDefaultAction();
        if (Unit* moine = GetTarget())
            if (Unit* cible = eventInfo.GetProcTarget())
                moine->CastSpell(cible, SPELL_TIANFENG_LAMES_COUP, true);
    }

    void Register() override
    {
        DoCheckProc += AuraCheckProcFn(spell_tian_feng_lames_de_vent::CheckProc);
        OnEffectProc += AuraEffectProcFn(spell_tian_feng_lames_de_vent::HandleProc, EFFECT_0, SPELL_AURA_DUMMY);
    }
};

void SC_AddMonkWeaponScripts()
{
    RegisterSpellScript(spell_yuwu_don);
    RegisterSpellScript(spell_yuwu_don_nuage);
    RegisterSpellScript(spell_yuwu_nuage);
    RegisterCreatureAI(npc_yuwu_nuage);
    RegisterSpellScript(spell_tian_lei_charge);
    RegisterSpellScript(spell_yuwu_brumes);
    RegisterCreatureAI(npc_yuwu_yulon);
    new monk_weapons_yulon_copy();
    new monk_weapons_yulon_soins();
    new monk_weapons_shaohao();
    new monk_weapons_fut_explosif();
    new monk_weapons_paume_au_visage();
    new monk_weapons_vents_croises();
    RegisterCreatureAI(npc_tian_feng_grue);
    RegisterSpellScript(spell_tian_lei_orage_interieur);
    RegisterSpellScript(spell_tian_feng_lames_de_vent);
}
