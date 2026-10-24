/*
 * Les trois armes artefacts du Moine (classe 10 de mod-custom-classes), partie « Moine » du module
 * (data/parts/monk, installée seulement quand la classe 10 existe). Cahier validé par Maitre le 24/10/2026.
 * Les sorts, objets, PNJ et quêtes : tools/monk_part.py. Les sorts du Moine visés sont ceux de
 * mod-custom-classes (version affc0a8) : sans la partie, ces scripts ne trouvent jamais leurs auras.
 *
 * ---------------------------------------------------------------------------
 * Yu Wu, bâton des Brumes (84035)
 *   - Don de Yu Wu (84960, passif) : chaque soin, 25 % de chances d'un Nuage de brume (84961, 10 au plus,
 *     60 s) : en base, aura de déclenchement et spell_proc.
 *   - Don de Yu Wu (84962, utilisation) : consomme les nuages, soigne la cible de 1 800 (+20 % de la
 *     puissance des soins) par nuage : spell_yuwu_don.
 *   - Brumes de Yu Wu (84964, passif) : un sort de soin instantané qui soigne, 10 % de chances (130 s de
 *     recharge interne, spell_proc) d'invoquer Yu'lon 12 s (84965) : spell_yuwu_brumes ; Yu'lon refait les
 *     sorts de soin du Moine sur les alliés les plus bas en vie : npc_yuwu_yulon et monk_weapons_yulon_copy.
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
 *   - Poing de tonnerre (84920) : en base (3 par minute, 4 charges de 450 + 10 % PA de Nature).
 *   - Vents croisés (84460) : pendant Poings de fureur, une grue (84206) frappe autour de la cible toutes les
 *     0,5 s (84462) : monk_weapons_vents_croises et npc_tian_feng_grue.
 *   - Frappe du Seigneur des vents (ensemble 84037) : l'aura de l'ensemble (84463) apprend la frappe (84464)
 *     tant que les deux poings sont portés : spell_poings_des_cieux_ensemble.
 * ---------------------------------------------------------------------------
 */

#include "CellImpl.h"
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
    SPELL_YUWU_YULON            = 84965,
    SPELL_YUWU_MURMURES         = 84966,
    SPELL_YUWU_MURMURES_SOIN    = 84967,
    // Jin Gu
    SPELL_JINGU_FUT_EXPLOSIF       = 84980,
    SPELL_JINGU_PAUME_AU_VISAGE    = 84982,
    // Poings des Cieux
    SPELL_TIANFENG_VENTS_CROISES   = 84460,
    SPELL_TIANFENG_GRUE_IMPULSION  = 84462,
    SPELL_POINGS_FRAPPE            = 84464,
    NPC_YUWU_YULON              = 84205,
    NPC_TIANFENG_GRUE              = 84206,
    // les sorts du Moine (mod-custom-classes, premiers rangs)
    SPELL_MONK_TIGER_PALM          = 81113,
    SPELL_MONK_FISTS_OF_FURY       = 81198,
    SPELL_MONK_SOOTHING_MIST       = 81771,
    SPELL_MONK_STATUE_SOOTHING     = 81896,   // la Brume apaisante de la statue du Serpent de jade
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
static constexpr float SHAOHAO_PORTEE   = 40.0f;   // les alliés des rebonds, autour de la cible soignée
static constexpr uint32 SHAOHAO_REBONDS = 2;
static constexpr uint32 GRUE_PERIODE    = 500;     // ms, une impulsion de Vents croisés
static constexpr float GRUE_PORTEE      = 8.0f;    // la portée de Poings de fureur : la cible de la grue sans cible du Moine
static constexpr uint32 PAUME_RECHARGE  = 4000;    // ms entre deux Paumes au visage
static constexpr int32 PAUME_BREUVAGES  = -1000;   // ms ôtées aux breuvages

namespace
{
    std::mutex monkWeaponsLock;
    std::unordered_map<ObjectGuid, ObjectGuid> yulonDuMoine;          // le Moine -> sa Yu'lon
    std::unordered_map<ObjectGuid, ObjectGuid> cibleDeLaGrue;         // le Moine -> la cible de sa prochaine grue

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

    SpellCastResult CheckCast()
    {
        Unit* moine = GetCaster();
        return moine && moine->HasAura(SPELL_YUWU_NUAGE) ? SPELL_CAST_OK : SPELL_FAILED_CASTER_AURASTATE;
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
        if (Unit* moine = GetCaster())
            if (nuages)
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
        me->GetMotionMaster()->MoveFollow(moine, 3.0f, float(M_PI));
    }

    void AttackStart(Unit* /*who*/) override { }
    void UpdateAI(uint32 /*diff*/) override { }
};

// Yu'lon refait chaque sort de soin que le Moine lance lui-même (pas un sort déclenché) sur l'allié le plus bas
// en vie autour d'elle ; le Moine reste le lanceur d'origine (ses bonus de soins)
class monk_weapons_yulon_copy : public PlayerScript
{
public:
    monk_weapons_yulon_copy() : PlayerScript("monk_weapons_yulon_copy", { PLAYERHOOK_ON_SPELL_CAST }) { }

    void OnPlayerSpellCast(Player* moine, Spell* spell, bool /*skipCheck*/) override
    {
        if (!spell || spell->IsTriggered() || !Soigne(spell->GetSpellInfo()))
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
        yulon->CastSpell(cible, spell->GetSpellInfo()->Id, TRIGGERED_FULL_MASK, nullptr, nullptr, moine->GetGUID());
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
            cible = nullptr;
            Acore::NearestAttackableUnitInObjectRangeCheck check(moine, moine, GRUE_PORTEE);
            Acore::UnitLastSearcher<Acore::NearestAttackableUnitInObjectRangeCheck> searcher(moine, cible, check);
            Cell::VisitObjects(moine, searcher, GRUE_PORTEE);
        }
        if (!cible)
            return;
        {
            std::lock_guard<std::mutex> garde(monkWeaponsLock);
            cibleDeLaGrue[moine->GetGUID()] = cible->GetGUID();
        }
        int32 duree = std::max<int32>(GRUE_PERIODE, spell->GetSpellInfo()->GetMaxDuration());
        moine->SummonCreature(NPC_TIANFENG_GRUE, cible->GetPosition(), TEMPSUMMON_TIMED_DESPAWN, uint32(duree));
    }
};

/*
 * npc_tian_feng_grue — créature 84206
 * Prend la faction du Moine, se tient au-dessus de sa cible et frappe toutes les 0,5 s les ennemis à 8 m
 * (84462, le Moine lanceur d'origine : les dégâts sont les siens). Elle part si le Moine ne canalise plus
 * Poings de fureur, ou si la cible meurt.
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
        Spell const* canal = moine ? moine->GetCurrentSpell(CURRENT_CHANNELED_SPELL) : nullptr;
        if (!moine || !cible || !cible->IsAlive() || !canal || canal->GetSpellInfo()->GetFirstRankSpell()->Id != SPELL_MONK_FISTS_OF_FURY)
        {
            me->DespawnOrUnsummon();
            return;
        }
        me->NearTeleportTo(cible->GetPositionX(), cible->GetPositionY(), cible->GetPositionZ() + 2.0f, me->GetOrientation());
        me->CastSpell(me, SPELL_TIANFENG_GRUE_IMPULSION, TRIGGERED_FULL_MASK, nullptr, nullptr, moineGuid);
    }
};

/*
 * spell_poings_des_cieux_ensemble — sort 84463 (bonus de l'ensemble 84037, Tian Lei et Tian Feng portés)
 * L'aura de l'ensemble apprend Frappe du Seigneur des vents (84464), pour la session seulement (rien en base), et
 * la reprend quand l'ensemble se défait.
 */
class spell_poings_des_cieux_ensemble : public AuraScript
{
    PrepareAuraScript(spell_poings_des_cieux_ensemble);

    void HandleApply(AuraEffect const* /*aurEff*/, AuraEffectHandleModes /*mode*/)
    {
        if (Player* moine = GetTarget()->ToPlayer())
            if (!moine->HasSpell(SPELL_POINGS_FRAPPE))
                moine->learnSpell(SPELL_POINGS_FRAPPE, true);
    }

    void HandleRemove(AuraEffect const* /*aurEff*/, AuraEffectHandleModes /*mode*/)
    {
        if (Player* moine = GetTarget()->ToPlayer())
            moine->removeSpell(SPELL_POINGS_FRAPPE, SPEC_MASK_ALL, true);
    }

    void Register() override
    {
        AfterEffectApply += AuraEffectApplyFn(spell_poings_des_cieux_ensemble::HandleApply, EFFECT_0, SPELL_AURA_DUMMY, AURA_EFFECT_HANDLE_REAL);
        AfterEffectRemove += AuraEffectRemoveFn(spell_poings_des_cieux_ensemble::HandleRemove, EFFECT_0, SPELL_AURA_DUMMY, AURA_EFFECT_HANDLE_REAL);
    }
};

void SC_AddMonkWeaponScripts()
{
    RegisterSpellScript(spell_yuwu_don);
    RegisterSpellScript(spell_yuwu_brumes);
    RegisterCreatureAI(npc_yuwu_yulon);
    new monk_weapons_yulon_copy();
    new monk_weapons_shaohao();
    new monk_weapons_fut_explosif();
    new monk_weapons_paume_au_visage();
    new monk_weapons_vents_croises();
    RegisterCreatureAI(npc_tian_feng_grue);
    RegisterSpellScript(spell_poings_des_cieux_ensemble);
}
