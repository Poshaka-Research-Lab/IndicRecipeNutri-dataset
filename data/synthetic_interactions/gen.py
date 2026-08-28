import pandas as pd, numpy as np, json, os
from datetime import datetime, timedelta

np.random.seed(42)
OUT = '/tmp/bench/synth50'
ZIPF_EXP = float(os.environ.get('ZIPF_EXP', '0.35'))   # flat within-catalog weight -> retain more items
GAMMA_EXP = float(os.environ.get('GAMMA_EXP', '0.6'))  # exposure weight in selection logits
os.makedirs(OUT, exist_ok=True)
SRC = '/mnt/user-data/uploads/PhD/datasets/scraped_indian_recipes/retrieval/recipe_attrs.csv'

print('loading...')
df = pd.read_csv(SRC, low_memory=False)
N = len(df)
print('recipes', N)

# ---------- Diet normalization ----------
def norm_diet(s):
    if not isinstance(s, str):
        return 'Vegetarian'
    t = s.lower()
    if 'non veg' in t or 'non-veg' in t or 'nonveg' in t:
        return 'Non-Vegetarian'
    if 'vegan' in t:
        return 'Vegan'
    if 'egg' in t:
        return 'Eggetarian'
    if 'veg' in t:
        return 'Vegetarian'
    return 'Vegetarian'
df['diet_norm'] = df['Diet'].map(norm_diet)
print('diet_norm:\n', df.diet_norm.value_counts())

# ---------- Region + zones ----------
region = df['Region'].fillna('Pan-Indian').astype(str).values  # NaN region -> treat as Pan-Indian
df['region_f'] = region
south = {'Tamil Nadu','Kerala','Karnataka','Andhra Pradesh','Telangana','South India'}
north = {'Punjab','North India','Rajasthan','Uttar Pradesh','Jammu & Kashmir','Himachal Pradesh','Uttarakhand','Mughlai (North India)','Delhi','Haryana'}
east  = {'West Bengal','Bihar','Odisha','Assam','East India','Nagaland','Manipur','Jharkhand','Sikkim','Tripura','Meghalaya','Arunachal Pradesh','Mizoram'}
west  = {'Maharashtra','Gujarat','Goa','Sindhi (community)','Parsi (community)','West India'}
def zone_of(r):
    if r in south: return 'S'
    if r in north: return 'N'
    if r in east:  return 'E'
    if r in west:  return 'W'
    return 'O'
zone_arr = np.array([zone_of(r) for r in region])

# ---------- Static recipe feature arrays ----------
grade_map = {'A':5,'B':4,'C':3,'D':2,'E':1}
grade_num = df['HealthGrade'].map(grade_map).fillna(3).values.astype(float)
grade_score = (grade_num - 1) / 4.0  # A=1..E=0

gl_map = {'low':1.0,'medium':0.5,'high':0.0}
gl_score = df['GlycemicLoad'].map(gl_map).fillna(0.5).values

def pctl(col):
    v = pd.to_numeric(df[col], errors='coerce')
    r = v.rank(pct=True)
    return r.fillna(0.5).values
sodium_p = pctl('Nut_Sodium')
satfat_p = pctl('Nut_SaturatedFat')
cal_p    = pctl('Nut_Calories')

rc = pd.to_numeric(df['RatingCount'], errors='coerce').fillna(0).values
pop = np.log1p(rc)
pop = pop / pop.max()  # normalized [0,1]

# intrinsic exposure/popularity weight (Zipfian) so a shared "hot catalog"
# recurs across users -> item degrees high enough to survive 10-core.
# Capped hot-catalog: interactions concentrate on ~HOTC shared items with a
# fairly flat within-catalog weight, so many items keep >=10 users after 10-core.
HOTC = int(os.environ.get('HOTC', '18000'))
_rank = np.random.permutation(N)
base = 1.0 / np.power(_rank + 1.0, ZIPF_EXP)   # ZIPF_EXP small (~0.35) => flat catalog
q = base * (1.0 + 2.0*pop)
q = np.where(_rank < HOTC, q, q * 5e-4)         # strongly suppress non-catalog items
q = np.maximum(q, 1e-12)
logq = np.log(q)

spice_rank = {'mild':0,'medium':1,'hot':2}
spice = df['SpiceLevel'].values
spice_r = np.array([spice_rank.get(s, -1) for s in spice])  # -1 = blank

course = df['Course'].fillna('Unknown').astype(str).values
diet_arr = df['diet_norm'].values
grade_letter = df['HealthGrade'].fillna('NA').astype(str).values
gl_letter = df['GlycemicLoad'].fillna('NA').astype(str).values
spice_letter = df['SpiceLevel'].fillna('NA').astype(str).values

# diet-compatibility masks (boolean over all recipes) per USER diet class
is_vegan = (diet_arr == 'Vegan')
is_vve   = np.isin(diet_arr, ['Vegetarian','Vegan','Eggetarian'])
pool_mask = {
    'Vegan': is_vegan,
    'Vegetarian': is_vve,
    'Eggetarian': is_vve,
    'Non-Vegetarian': np.ones(N, bool),
}
pool_idx = {k: np.where(v)[0] for k, v in pool_mask.items()}
for k,v in pool_idx.items(): print('pool', k, len(v))
# per-pool exposure prob (normalized q) for candidate sampling
pool_q = {k: (q[idx] / q[idx].sum()) for k, idx in pool_idx.items()}

# region -> indices (all recipes)
region_to_idx = {}
for i, r in enumerate(region):
    region_to_idx.setdefault(r, []).append(i)
region_to_idx = {k: np.array(v) for k,v in region_to_idx.items()}

# ---------- USERS ----------
NU = 50000
regions_present = [r for r in region_to_idx.keys()]
counts = {r: len(region_to_idx[r]) for r in regions_present}
# home_region distribution: Pan-Indian 25%, rest ~ sqrt(count)
non_pan = [r for r in regions_present if r != 'Pan-Indian']
sq = np.array([np.sqrt(counts[r]) for r in non_pan])
sq = sq / sq.sum() * 0.75
home_regions = ['Pan-Indian'] + non_pan
home_p = np.array([0.25] + list(sq))
home_p = home_p / home_p.sum()
home_region = np.random.choice(home_regions, size=NU, p=home_p)
# guarantee every region with recipes has >=1 user
for ri, r in enumerate(regions_present):
    if not (home_region == r).any():
        home_region[ri] = r  # overwrite a slot

diet_u = np.random.choice(['Vegetarian','Vegan','Non-Vegetarian','Eggetarian'], NU, p=[0.40,0.15,0.35,0.10])
health_u = np.random.choice(['general','diabetic','heart_lowsodium','weight_loss'], NU, p=[0.60,0.15,0.15,0.10])
spice_u = np.random.choice(['mild','medium','hot'], NU, p=[0.20,0.45,0.35])
age_u = np.random.choice(['18-25','26-35','36-50','51+'], NU, p=[0.25,0.35,0.25,0.15])

# n_interactions: lognormal clip[5,200], mean~20 -> total~400k. calibrate mu.
sigma = 0.75
def sample_counts(mu, seed=1):
    rs = np.random.RandomState(seed)
    x = rs.lognormal(mean=mu, sigma=sigma, size=NU)
    x = np.clip(np.round(x), 5, 200).astype(int)
    return x
mu = 2.55
for _ in range(40):
    c = sample_counts(mu)
    m = c.mean()
    if abs(m - 20) < 0.15: break
    mu += (20 - m) * 0.03
n_inter = sample_counts(mu, seed=99)
print('mu', round(mu,3), 'mean n_inter', n_inter.mean(), 'total', n_inter.sum())

users = pd.DataFrame({
    'user_id': np.arange(NU),
    'home_region': home_region,
    'diet': diet_u,
    'health_profile': health_u,
    'spice_pref': spice_u,
    'age_band': age_u,
    'n_interactions': n_inter,
})
users.to_csv(f'{OUT}/users.csv', index=False)

# ---------- INTERACTIONS ----------
W_REGION, W_HEALTH, W_SPICE, W_POP = 0.35, 0.20, 0.15, 0.10
TEMP = 0.3
sp_rank_u = {'mild':0,'medium':1,'hot':2}
date_start = datetime(2016,1,1)
date_span_days = (datetime(2026,6,30) - date_start).days

# normalized target (drop implicit-0, renormalize the 5 buckets to 100%)
raw_t = np.array([1,2,4,16,72], float)  # for ratings 1,2,3,4,5
norm_t = raw_t / raw_t.sum()  # index0=1star ... index4=5star
# cumulative from top (5star first)
frac_5 = norm_t[4]; frac_4 = norm_t[3]; frac_3 = norm_t[2]; frac_2 = norm_t[1]; frac_1 = norm_t[0]

rows_u = []; rows_i = []; rows_r = []; rows_d = []
rng = np.random.RandomState(2024)

for u in range(NU):
    dclass = diet_u[u]
    base = pool_idx[dclass]
    hr = home_region[u]
    n = int(n_inter[u])
    # candidate set: region-matching (up to 600) + random from pool (~1800)
    cand_parts = []
    rmatch = region_to_idx.get(hr, None)
    if rmatch is not None:
        rm = rmatch[pool_mask[dclass][rmatch]]
        if len(rm) > 400:
            rw = q[rm]; rw = rw/rw.sum()
            rm = rng.choice(rm, 400, replace=True, p=rw)
        cand_parts.append(rm)
    # exposure-weighted draw from the diet pool (shared hot catalog -> recurrence)
    draw = max(2500, n*15)
    cand_parts.append(rng.choice(base, draw, replace=True, p=pool_q[dclass]))
    cand = np.unique(np.concatenate(cand_parts))
    if len(cand) < n:
        n = len(cand)
    # ---- affinity over candidates ----
    rreg = region[cand]
    rz = zone_arr[cand]
    uz = zone_of(hr)
    rmatch_score = np.where(rreg == hr, 1.0,
                    np.where(rreg == 'Pan-Indian', 0.5,
                    np.where((rz == uz) & (uz != 'O'), 0.5, 0.1)))
    # health
    hp = health_u[u]
    if hp == 'diabetic':
        health = 0.5*gl_score[cand] + 0.5*grade_score[cand]
    elif hp == 'heart_lowsodium':
        health = 0.4*(1-sodium_p[cand]) + 0.3*(1-satfat_p[cand]) + 0.3*grade_score[cand]
    elif hp == 'weight_loss':
        health = 0.7*(1-cal_p[cand]) + 0.3*grade_score[cand]
    else:
        health = grade_score[cand]
    # spice
    ur = sp_rank_u[spice_u[u]]
    sr = spice_r[cand]
    spice_match = np.where(sr < 0, 0.3,
                   np.where(sr == ur, 1.0,
                   np.where(np.abs(sr - ur) == 1, 0.5, 0.3)))
    aff = (W_REGION*rmatch_score + W_HEALTH*health + W_SPICE*spice_match
           + W_POP*pop[cand] + rng.normal(0, 0.15, len(cand)))
    # selection logits = personalized affinity + exposure bias (shared hot catalog)
    z = aff / TEMP + GAMMA_EXP * logq[cand]
    z -= z.max()
    p = np.exp(z); p /= p.sum()
    if n < len(cand):
        chosen = rng.choice(len(cand), size=n, replace=False, p=p)
    else:
        chosen = np.arange(len(cand))
    ch_idx = cand[chosen]
    ch_aff = aff[chosen]
    # rating by affinity rank within user's set
    order = np.argsort(-ch_aff)  # high affinity first
    m = len(order)
    ratings = np.empty(m, int)
    c5 = int(round(frac_5*m)); c4 = int(round(frac_4*m)); c3 = int(round(frac_3*m)); c2 = int(round(frac_2*m))
    pos = 0
    for cnt, val in [(c5,5),(c4,4),(c3,3),(c2,2)]:
        ratings[order[pos:pos+cnt]] = val; pos += cnt
    ratings[order[pos:]] = 1
    # timestamps
    days = rng.randint(0, date_span_days+1, m)
    dates = [date_start + timedelta(days=int(d)) for d in days]
    dstr = np.array([d.strftime('%Y-%m-%d') for d in dates])
    o2 = np.argsort(days)  # sort by time
    rows_u.append(np.full(m, u)); rows_i.append(ch_idx[o2]); rows_r.append(ratings[o2]); rows_d.append(dstr[o2])

inter = pd.DataFrame({
    'user_id': np.concatenate(rows_u),
    'recipe_id': np.concatenate(rows_i),
    'rating': np.concatenate(rows_r),
    'date': np.concatenate(rows_d),
})
inter.to_csv(f'{OUT}/interactions.csv', index=False)
print('interactions', len(inter))
print('rating hist:\n', inter.rating.value_counts(normalize=True).sort_index())

# ---------- KGAT pipeline ----------
pos = inter[inter.rating >= 4][['user_id','recipe_id','date']].copy()
print('positives', len(pos))
# iterative 10-core
CORE = 10
while True:
    uc = pos.user_id.value_counts()
    ic = pos.recipe_id.value_counts()
    keep_u = set(uc[uc >= CORE].index)
    keep_i = set(ic[ic >= CORE].index)
    before = len(pos)
    pos = pos[pos.user_id.isin(keep_u) & pos.recipe_id.isin(keep_i)]
    if len(pos) == before:
        break
print('post-10core positives', len(pos), 'users', pos.user_id.nunique(), 'items', pos.recipe_id.nunique())
if os.environ.get('FAST'):
    print('FAST_RESULT zipf=%s gamma=%s distinct_rated=%d post10_items=%d post10_users=%d post10_pos=%d total_inter=%d'
          % (ZIPF_EXP, GAMMA_EXP, inter.recipe_id.nunique(), pos.recipe_id.nunique(), pos.user_id.nunique(), len(pos), len(inter)))
    raise SystemExit

# temporal 80/20 split per user
pos = pos.sort_values(['user_id','date']).reset_index(drop=True)
train_mask = np.ones(len(pos), bool)
test_rows = []
for uid, g in pos.groupby('user_id', sort=False):
    idx = g.index.values
    ntest = max(1, int(round(len(idx)*0.2)))
    ntest = min(ntest, len(idx)-1)  # keep >=1 in train
    test_rows.extend(idx[-ntest:])
train_mask[test_rows] = False
train = pos[train_mask]; test = pos[~train_mask]
print('train', len(train), 'test', len(test))

# remap
u_ids = sorted(pos.user_id.unique())
i_ids = sorted(pos.recipe_id.unique())
u_remap = {o:i for i,o in enumerate(u_ids)}
i_remap = {o:i for i,o in enumerate(i_ids)}
nI = len(i_ids)

with open(f'{OUT}/user_list.txt','w') as f:
    f.write('org_id remap_id\n')
    for o in u_ids: f.write(f'{o} {u_remap[o]}\n')
with open(f'{OUT}/item_list.txt','w') as f:
    f.write('org_id remap_id\n')
    for o in i_ids: f.write(f'{o} {i_remap[o]}\n')

def write_ui(fn, dfp):
    d = {}
    for uid, iid in zip(dfp.user_id.values, dfp.recipe_id.values):
        d.setdefault(u_remap[uid], []).append(i_remap[iid])
    with open(fn,'w') as f:
        for uid in sorted(d):
            f.write(str(uid)+' '+' '.join(map(str, d[uid]))+'\n')
    return d
train_d = write_ui(f'{OUT}/train.txt', train)
test_d = write_ui(f'{OUT}/test.txt', test)

# leakage check
leak = 0
for uid, items in test_d.items():
    if uid in train_d:
        leak += len(set(items) & set(train_d[uid]))
print('leakage', leak)

# ---------- KG ----------
relations = [('has_region',0),('has_diet',1),('has_course',2),('has_healthgrade',3),('has_spice',4)]
with open(f'{OUT}/relation_list.txt','w') as f:
    f.write('org_id remap_id\n')
    for name, rid in relations: f.write(f'{name} {rid}\n')

# entities: items first (remap == item remap), then attribute-value nodes
ent_org = [f'item:{o}' for o in i_ids]  # index == item remap id
attr_node_id = {}
next_id = nI
def get_node(val):
    global next_id
    if val not in attr_node_id:
        attr_node_id[val] = next_id
        ent_org.append(val)
        next_id += 1
    return attr_node_id[val]

triples = []
surv_items = set(i_ids)
for o in i_ids:
    h = i_remap[o]
    r = region[o]; d = diet_arr[o]; c = course[o]; g = grade_letter[o]; s = spice_letter[o]
    triples.append((h, 0, get_node(f'region:{r}')))
    triples.append((h, 1, get_node(f'diet:{d}')))
    if c != 'Unknown':
        triples.append((h, 2, get_node(f'course:{c}')))
    if g != 'NA':
        triples.append((h, 3, get_node(f'grade:{g}')))
    if s != 'NA':
        triples.append((h, 4, get_node(f'spice:{s}')))

with open(f'{OUT}/entity_list.txt','w') as f:
    f.write('org_id remap_id\n')
    for i, name in enumerate(ent_org):
        f.write(f'{name} {i}\n')
with open(f'{OUT}/kg_final.txt','w') as f:
    for h,r,t in triples:
        f.write(f'{h} {r} {t}\n')
print('kg triples', len(triples), 'entities', len(ent_org))

# ---------- STATS ----------
ach = inter.rating.value_counts(normalize=True).sort_index()
ach_hist = {int(k): round(float(v),4) for k,v in ach.items()}
target_hist = {1:round(float(norm_t[0]),4),2:round(float(norm_t[1]),4),3:round(float(norm_t[2]),4),4:round(float(norm_t[3]),4),5:round(float(norm_t[4]),4)}
pc = inter.user_id.value_counts()
pctls = {str(p): float(np.percentile(pc.values, p)) for p in [1,5,25,50,75,90,95,99]}
region_cov = users.home_region.value_counts().to_dict()
diet_split = users.diet.value_counts(normalize=True).round(4).to_dict()

# diet constraint audit: vegan users on non-veg
um = users.set_index('user_id')
mm = inter.merge(users[['user_id','diet']], on='user_id')
recipe_diet = pd.Series(diet_arr, index=df.recipe_id.values)
mm['rdiet'] = recipe_diet.loc[mm.recipe_id.values].values
vegan_nonveg = int(((mm.diet=='Vegan') & (mm.rdiet!='Vegan')).sum())
veg_nonveg = int(((mm.diet.isin(['Vegetarian','Eggetarian'])) & (mm.rdiet=='Non-Vegetarian')).sum())

stats = {
    'n_users': int(NU),
    'n_items_total_rated': int(inter.recipe_id.nunique()),
    'n_interactions_total': int(len(inter)),
    'n_positives_pre_10core': int(len(inter[inter.rating>=4])),
    'n_positives_post_10core': int(len(pos)),
    'n_users_post_10core': int(pos.user_id.nunique()),
    'n_items_post_10core': int(nI),
    'n_train': int(len(train)),
    'n_test': int(len(test)),
    'rating_hist_achieved': ach_hist,
    'rating_hist_target_normalized': target_hist,
    'rating_hist_target_raw_pct': {5:72,4:16,3:4,2:2,1:1},
    'per_user_count_percentiles': pctls,
    'per_user_count_mean': round(float(pc.mean()),3),
    'region_coverage_users': {k:int(v) for k,v in region_cov.items()},
    'n_regions_with_recipes': len(regions_present),
    'n_regions_covered_by_users': int(users.home_region.nunique()),
    'diet_split_users': {k:float(v) for k,v in diet_split.items()},
    'n_kg_triples': int(len(triples)),
    'n_kg_entities': int(len(ent_org)),
    'n_kg_relations': 5,
    'train_test_leakage': int(leak),
    'diet_violation_vegan_on_nonvegan': vegan_nonveg,
    'diet_violation_veg_on_nonveg': veg_nonveg,
}
with open(f'{OUT}/stats.json','w') as f:
    json.dump(stats, f, indent=2)
print(json.dumps(stats, indent=2))

# ---------- REPORT ----------
lines = []
lines.append('# Synthetic Indian-Recipe Interaction Log — Distribution Report\n')
lines.append(f'Generated {datetime.now().strftime("%Y-%m-%d")} with numpy seed 42. Source: {N:,} recipes.\n')
lines.append('## Scale')
lines.append(f'- Users: {NU:,}')
lines.append(f'- Interactions (explicit 1-5): {len(inter):,} (mean {pc.mean():.1f}/user)')
lines.append(f'- Distinct items rated: {inter.recipe_id.nunique():,}\n')
lines.append('## Rating distribution (achieved vs target, normalized dropping implicit-0)')
lines.append('| Star | Achieved | Target |')
lines.append('|------|----------|--------|')
for st in [5,4,3,2,1]:
    lines.append(f'| {st}★ | {ach_hist.get(st,0)*100:.2f}% | {target_hist[st]*100:.2f}% |')
lines.append('')
lines.append('## Per-user interaction count (heavy-tailed lognormal, clip [5,200])')
lines.append('| pctl | ' + ' | '.join(pctls.keys()) + ' |')
lines.append('|------|' + '------|'*len(pctls))
lines.append('| count | ' + ' | '.join(f'{int(v)}' for v in pctls.values()) + ' |')
lines.append(f'\nmin={int(pc.min())}, max={int(pc.max())}, mean={pc.mean():.1f}\n')
lines.append('## User diet split')
for k,v in diet_split.items(): lines.append(f'- {k}: {v*100:.1f}%')
lines.append('\n## Region coverage of users')
lines.append(f'{len(regions_present)} regions have recipes; {users.home_region.nunique()} are covered by ≥1 user (Pan-Indian share {region_cov.get("Pan-Indian",0)/NU*100:.1f}%).')
lines.append('\n<details><summary>users per home_region</summary>\n')
for k,v in sorted(region_cov.items(), key=lambda x:-x[1]):
    lines.append(f'- {k}: {v}')
lines.append('</details>\n')
lines.append('## KGAT export')
lines.append(f'- After iterative 10-core on positives (rating≥4): {len(pos):,} positives, {pos.user_id.nunique():,} users, {nI:,} items')
lines.append(f'- Temporal 80/20 split: train {len(train):,} / test {len(test):,}')
lines.append(f'- KG: {len(triples):,} triples over {len(ent_org):,} entities, 5 relations (has_region/diet/course/healthgrade/spice)\n')
lines.append('## Integrity checks')
lines.append(f'- (a) Diet compatibility HELD: Vegan-user→non-Vegan ratings = {vegan_nonveg}; Veg/Egg-user→Non-Veg ratings = {veg_nonveg} (expected 0).')
lines.append(f'- (b) 10-core satisfied: every retained user ≥{CORE} items, every retained item ≥{CORE} users.')
lines.append(f'- (c) Train/test leakage = {leak} (expected 0).')
with open(f'{OUT}/DISTRIBUTION_REPORT.md','w') as f:
    f.write('\n'.join(lines))
print('DONE')
