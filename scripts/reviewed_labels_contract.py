"""Fail-closed public reviewed-label schema and frozen approval provenance."""
import hashlib,json,re
from pathlib import Path
import pandas as pd

BUNDLE='a254b15694ddda5eb8f6397e8a2b8a980c21e1706aa46d5b7dc78e75d145810a'
DECL=['recipe_id','facet','controlled_value','verbatim_value','evidence_field','evidence_quote_sha256','review_decision','reviewer','review_basis','result_hash','approval_bundle_sha256','SourceSite','independent_human_semantic_validation']
SCOPE=['recipe_id','reviewed_scope_terms_json','reviewed_legacy_scope_candidate','review_decision','non_indian_exclusion_supported','approval_bundle_sha256']
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def validate_frame(f,ids,scope=False):
    errors=[]
    if list(f.columns)!=(SCOPE if scope else DECL):return ['Unexpected columns: private evidence prohibited']
    if f.recipe_id.isna().any() or not set(f.recipe_id)<=set(ids):errors.append('Invalid recipe IDs')
    if f.isna().drop(columns=['reviewed_legacy_scope_candidate'] if scope else ['controlled_value']).any().any():errors.append('Missing required values')
    if not f.approval_bundle_sha256.eq(BUNDLE).all():errors.append('Wrong approval bundle')
    if scope:
        if f.recipe_id.duplicated().any():errors.append('Duplicate scope recipe')
        if not set(f.review_decision)<={'owner_approved_assistant_review','abstain'}:errors.append('Invalid scope decision')
        if f.non_indian_exclusion_supported.ne(False).any():errors.append('Unsupported non-Indian exclusion')
        for r in f.itertuples():
            try:terms=json.loads(r.reviewed_scope_terms_json)
            except (TypeError,ValueError):errors.append('Invalid scope JSON');continue
            if not isinstance(terms,list) or not set(terms)<={'Indian','Pan-Indian','Fusion','International'}:errors.append('Invalid scope terms');continue
            expected=None
            if r.review_decision=='owner_approved_assistant_review':expected='indo-fusion' if 'Fusion' in terms else None if 'International' in terms else 'indian' if terms and set(terms)<={'Indian','Pan-Indian'} else None
            actual=None if pd.isna(r.reviewed_legacy_scope_candidate) else r.reviewed_legacy_scope_candidate
            if actual!=expected:errors.append('Scope mapping disagrees')
    else:
        if f.duplicated(['recipe_id','facet','verbatim_value','evidence_field','evidence_quote_sha256']).any():errors.append('Duplicate declaration')
        if not set(f.review_decision)<={'accept','reject'}:errors.append('Unreviewed declaration')
        if not set(f.facet)<={'cuisine','region','scope'}:errors.append('Invalid facet')
        if not f.review_basis.eq('owner_approved_rule_assisted_review').all() or f.independent_human_semantic_validation.ne(False).any():errors.append('Misrepresented review basis')
        for col in ['evidence_quote_sha256','result_hash','approval_bundle_sha256']:
            if not f[col].map(lambda s:isinstance(s,str) and re.fullmatch('[0-9a-f]{64}',s) is not None).all():errors.append('Invalid digest: '+col)
        for col in ['verbatim_value','controlled_value']:
            if not f[col].dropna().map(lambda s:isinstance(s,str) and 0<len(s)<=120 and '\n' not in s).all():errors.append('Invalid label: '+col)
    return sorted(set(errors))
def validate_release(root):
    try:
        root=Path(root);folder=root/'data/labels';m=json.loads((folder/'REVIEWED_MANIFEST.json').read_text())
        errors=[];ids=pd.read_parquet(root/'data/corpus/recipes_structured.parquet',columns=['recipe_id']).recipe_id
        if m['approval_bundle_sha256']!=BUNDLE or m['source_quotes_published'] or m['independent_human_semantic_validation'] or not m['original_labels_preserved']:errors.append('Invalid review manifest')
        for name,columns in [('cuisine_declarations_v1.parquet',DECL),('reviewed_scope_v1.parquet',SCOPE)]:
            f=pd.read_parquet(folder/name);meta=m['tables'][name]
            errors+=validate_frame(f,ids,scope=name.startswith('reviewed_scope'))
            if len(f)!=meta['rows'] or list(f.columns)!=meta['columns'] or list(f.columns)!=columns:errors.append('Manifest schema/count mismatch')
            if sha(folder/name)!=meta['sha256'] or sha(folder/name.replace('.parquet','.csv'))!=meta['csv_sha256']:errors.append('Reviewed payload drift')
            csv=pd.read_csv(folder/name.replace('.parquet','.csv'),keep_default_na=False)
            expected=f.fillna('').astype(str);actual=csv.fillna('').astype(str)
            if not actual.equals(expected):errors.append('CSV/Parquet mismatch')
        for name,pin in m['base_payload_sha256'].items():
            if sha(root/name)!=pin:errors.append('Core payload drift: '+name)
        return sorted(set(errors))
    except (OSError,ValueError,KeyError,TypeError) as e:return ['Cannot validate reviewed labels: '+str(e)]
