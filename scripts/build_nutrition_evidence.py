"""Expose estimator assumptions without changing weights or claiming reference accuracy."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_quality_inputs import sha256
from build_quality_flags import atomic_json, atomic_parquet, validate_output_root


def summarize(corpus, weights, nutrition):
    keys = ['recipe_id','ing_index']
    if corpus.recipe_id.isna().any() or corpus.recipe_id.duplicated().any():
        raise ValueError('Invalid corpus keys')
    for frame in [weights,nutrition]:
        if frame.duplicated(keys).any() or frame[keys].isna().any().any():
            raise ValueError('Invalid occurrence keys')
        if not frame.recipe_id.isin(corpus.recipe_id).all():
            raise ValueError('Occurrence outside corpus')
    joined=weights.merge(nutrition,on=keys,how='outer',validate='one_to_one',indicator=True,suffixes=('_weight','_nutrition'))
    if not joined._merge.eq('both').all():
        raise ValueError('Weight/nutrition occurrence keys differ')
    if not (joined.grams_weight.eq(joined.grams_nutrition) | (joined.grams_weight.isna() & joined.grams_nutrition.isna())).all():
        raise ValueError('Weight/nutrition occurrence grams differ')
    if not (joined.tier.isna() | joined.tier.isin(['A','B','C','D','E','unavailable'])).all():
        raise ValueError('Unknown weight tier')
    if joined.loc[joined.tier.isna(),'grams_weight'].notna().any():
        raise ValueError('Untiered occurrence unexpectedly has grams')
    joined['unassessed_weight']=joined.tier.isna()
    joined['is_ab']=joined.tier.isin(['A','B'])
    joined['assumed']=joined.tier.isin(['C','D','E'])
    joined['flat20']=joined.tier.eq('E') & joined.grams_weight.eq(20)
    joined['mass_positive']=joined.grams_weight.where(joined.grams_weight.gt(0))
    joined['ab_mass']=joined.mass_positive.where(joined.is_ab,0.0)
    joined['energy_available']=joined.Nut_Calories.notna()
    joined['energy_nonnegative']=joined.Nut_Calories.where(joined.Nut_Calories.ge(0))
    joined['ab_energy']=joined.energy_nonnegative.where(joined.is_ab,0.0)
    grouped=joined.groupby('recipe_id')
    summary=grouped.agg(ingredient_line_count=('ing_index','size'),
                       ab_line_count=('is_ab','sum'),assumed_weight_line_count=('assumed','sum'),
                       unassessed_weight_line_count=('unassessed_weight','sum'),
                       flat20_tier_e_line_count=('flat20','sum'),energy_available_line_count=('energy_available','sum'))
    summary['count_confident_fraction']=summary.ab_line_count/summary.ingredient_line_count
    mass=grouped.mass_positive.sum(min_count=1)
    energy=grouped.energy_nonnegative.sum(min_count=1)
    summary['estimated_ab_mass_fraction']=grouped.ab_mass.sum(min_count=1)/mass.where(mass.gt(0))
    summary['partial_ab_energy_fraction']=grouped.ab_energy.sum(min_count=1)/energy.where(energy.gt(0))
    out=corpus.merge(summary,on='recipe_id',how='left',validate='one_to_one').sort_values('recipe_id').reset_index(drop=True)
    for c in ['ingredient_line_count','ab_line_count','assumed_weight_line_count','unassessed_weight_line_count','flat20_tier_e_line_count','energy_available_line_count']:
        out[c]=out[c].fillna(0).astype('int64')
    a,b=out.count_confident_fraction,out.ing_weight_confident_frac
    if not ((a.isna() & b.isna()) | np.isclose(a,b,atol=1e-12,rtol=0,equal_nan=True)).all():
        raise ValueError('Published weight-confidence fraction does not reproduce')
    out['has_assumed_weight_line']=out.assumed_weight_line_count.gt(0)
    out['estimator_high_confidence_rule']=out.per100g_confident.fillna(False) & out.ing_weight_confident_frac.ge(0.8)
    out['reference_validation_status']='not_independently_validated_here'
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['root','protected-root','input-manifest']:
        ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args()
    output=validate_output_root(a.root,a.protected_root)
    receipt=json.loads(a.input_manifest.read_text(encoding='utf-8'))
    sums={x['path']:x['expected'] for x in receipt['checksum_files']}
    paths=['data/corpus/recipes_structured.parquet','data/enrichment/ingredients_weights.parquet','data/enrichment/ingredients_nutrition.parquet']
    for rel in paths:
        if sha256(a.root/rel)!=sums[rel]: raise ValueError('Input differs from baseline: '+rel)
    corpus=pd.read_parquet(a.root/paths[0],columns=['recipe_id','Region','Split_v3','per100g_confident','per100g_basis','serving_basis_v3','ing_weight_confident_frac'])
    weights=pd.read_parquet(a.root/paths[1],columns=['recipe_id','ing_index','tier','grams'])
    nutrition=pd.read_parquet(a.root/paths[2],columns=['recipe_id','ing_index','grams','Nut_Calories'])
    result=summarize(corpus,weights,nutrition)
    path=output/'nutrition_evidence_v1.parquet'
    atomic_parquet(result,path)
    counts={}
    for pop,frame in [('ALL',result),('DEV',result.loc[result.Split_v3.ne('test')])]:
        counts[pop]={'rows':len(frame),'with_assumed_weight_line':int(frame.has_assumed_weight_line.sum()),
                     'with_flat20_line':int(frame.flat20_tier_e_line_count.gt(0).sum()),
                     'unassessed_weight_lines':int(frame.unassessed_weight_line_count.sum()),
                     'estimator_high_confidence_rule':int(frame.estimator_high_confidence_rule.sum()),
                     'no_occurrence_rows':int(frame.ingredient_line_count.eq(0).sum())}
    manifest={'version':'nutrition-evidence-0.12.0-v1','inputs':{p:sums[p] for p in paths},
              'builder_sha256':sha256(Path(__file__)),'payload_sha256':sha256(path),'counts':counts,
              'weight_fraction_reproduced':True,'occurrence_gram_tables_identical':True,
              'numerator_denominator_model_issue':'These occurrence tables agree with each other; this does not establish agreement with the legacy per100g denominator model.',
              'legacy_values_modified':False,'independent_reference_accuracy_measured':False,
              'limits':['Mass fraction uses estimated grams, not reference weights.','Energy fraction is over available ingredient energy, not complete nutrient coverage.','The 0.8 predicate is an estimator rule, not a validated accuracy threshold.']}
    atomic_json(manifest,output/'nutrition_evidence_manifest.json')
    print(json.dumps(counts))


if __name__=='__main__':
    main()
