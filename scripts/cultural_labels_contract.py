"""Public pending-label sidecar: strict schema and no private source evidence."""
import json
import hashlib
from pathlib import Path
import pandas as pd

FACETS=['Cuisine','Region','State','UT','BroadRegion','Community','CulinarySubregion','Locality','Scope']
COLUMNS=['recipe_id','status','review_status','taxonomy','partial_response']+[f'proposed_{f}_json' for f in FACETS]

def validate_frame(frame,recipe_ids):
    problems=[]
    if list(frame.columns)!=COLUMNS: return ['Unexpected columns; private fields must not be published']
    if frame.recipe_id.isna().any() or frame.recipe_id.duplicated().any(): problems.append('Null/duplicate recipe IDs')
    if not set(frame.recipe_id)<=set(recipe_ids): problems.append('Unknown recipe IDs')
    if set(frame.status)-{'proposed','abstain'}: problems.append('Invalid status')
    if set(frame.review_status)!={'pending'}: problems.append('Proposals must remain pending')
    for row in frame.itertuples(index=False):
        count=0
        for value in row[5:]:
            try: labels=json.loads(value)
            except (ValueError,TypeError): problems.append('Malformed label JSON'); continue
            if not isinstance(labels,list) or any(not isinstance(x,str) or not x.strip() or len(x)>120 or '\n' in x for x in labels):
                problems.append('Invalid/overlong labels'); continue
            count+=len(labels)
        if (row.status=='proposed')!=bool(count): problems.append('Status/labels disagree')
    return sorted(set(problems))

def validate_release(root):
    root=Path(root); folder=root/'data/cultural_labels'
    if not folder.exists(): return ['Missing cultural label sidecar']
    frame=pd.read_parquet(folder/'proposals.parquet')
    core=pd.read_parquet(root/'data/corpus/recipes_structured.parquet',columns=['recipe_id'])
    problems=validate_frame(frame,core.recipe_id)
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    if manifest['rows']!=len(frame) or manifest['status_counts']!=frame.status.value_counts().to_dict(): problems.append('Manifest counts mismatch')
    for name,pin in manifest['base_payload_sha256'].items():
        with (root/name).open('rb') as stream: actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=pin: problems.append('Base payload changed: '+name)
    return problems
