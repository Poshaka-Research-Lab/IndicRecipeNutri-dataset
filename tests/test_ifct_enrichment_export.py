import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_enrichment as exporter
import stamp_units
from column_units import COLUMN_UNITS
from make_data_dictionary import COLUMN_NOTES


class IFCTEnrichmentExportTests(unittest.TestCase):
    def fixture(self, root):
        source=root/'source';out=root/'out';source.mkdir();out.mkdir()
        frame=pd.DataFrame(dict(recipe_id=[1,2],ifct_food_occurrence_count=[1,1],
            ifct_energy_available_occurrence_count=[1,0],ifct_computed_energy_kcal=[100.,None],
            computed_ingredient_energy_kcal=[200.,None],energy_available_count=[2,0],
            fraction_basis=['available_computed_ingredient_energy','unavailable_no_energy'],
            ifct_computed_energy_fraction=[.5,None]))
        frame.to_parquet(source/'recipe_ifct_fraction.parquet',index=False)
        native=dict(source_food_code='A018',source_food_name='Wheat flour, refined',
            preparation_basis='raw_general_convention_named_processing_retained',
            pdf_page_1_based=41,number_of_regions=6,components=[],
            Instructions='PRIVATE RECIPE',reviewer_reason='PRIVATE REVIEW')
        components=[dict(source_tagname=tag,target_field=target,unit=unit,
            denominator='100 g edible portion',value=value,source_standard_deviation=None,
            status='reported_numeric',conversion=None,reviewer_reason='PRIVATE REVIEW')
            for tag,target,unit,value in [('PROTCNT','Nut_Protein','g',10.),
                ('FATCE','Nut_Fat','g',1.),('FIBTG','Nut_Fiber','g',None),
                ('ENERC','Nut_Calories','kcal',300.)]]
        profile=dict(version='ifct_table1_component_projection_v1',source_food_code='A018',
            source_manifest_sha256='a'*64,native_source=native,target_components=components,
            energy_policy='ifct2017_source_kj_per_kcal_4_18',recipe_context='PRIVATE RECIPE')
        (source/'ifct_source_profiles.json').write_text(json.dumps({'A018':profile}))
        manifest=dict(ifct=dict(source_manifest_sha256='a'*64,review_registry_sha256='b'*64,
            energy_policy=profile['energy_policy'],weight_policy='existing_positive_quantity_unit_and_confident_tier_ab_v1',
            human_labels=0,quantity_approvals=0,active_match_status='agent_reviewed_source_identity',
            reviewer_reason='PRIVATE REVIEW'),input_sha256={'C:/private/path':'c'*64},
            retention_policy='legacy_assumed_cooked',retention_factors={'Nut_Protein':1.},
            outputs={name:exporter.file_digest(source/name) for name in exporter.IFCT_COMPANIONS})
        (source/'ingredients_nutrition_manifest.json').write_text(json.dumps(manifest))
        return source,out

    def test_optional_absence_and_partial_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source';out=Path(folder)/'out';source.mkdir();out.mkdir()
            self.assertEqual(exporter.export_ifct_companions(source,out),[])
            self.assertEqual(list(out.iterdir()),[])
            (source/'ifct_source_profiles.json').write_text('{}')
            with self.assertRaises(ValueError):exporter.export_ifct_companions(source,out)

    def test_export_preserves_nulls_filters_withdrawals_and_sanitizes_prose(self):
        with tempfile.TemporaryDirectory() as folder:
            source,out=self.fixture(Path(folder))
            with patch.object(exporter,'DROP_IDS',{1}):records=exporter.export_ifct_companions(source,out)
            self.assertEqual(records[0]['rows_dropped_by_exclusion'],1)
            share=pd.read_parquet(out/'recipe_ifct_fraction.parquet')
            self.assertEqual(share.recipe_id.tolist(),[2])
            self.assertTrue(share.ifct_computed_energy_fraction.isna().all())
            profile=json.loads((out/'ifct_source_profiles.json').read_text())['A018']
            self.assertIsNone(profile['target_components'][2]['value'])
            self.assertEqual(len(profile['target_components']),4)
            for name in ['ifct_source_profiles.json','nutrition_source_provenance.json']:
                text=(out/name).read_text()
                self.assertNotIn('PRIVATE',text);self.assertNotIn('C:/private',text)
                self.assertNotIn('Instructions',text);self.assertNotIn('reviewer_reason',text)
            provenance=json.loads((out/'nutrition_source_provenance.json').read_text())
            self.assertFalse(provenance['ifct_fct_idx_required'])
            self.assertEqual(provenance['source_identity_fields'],['fct_source','fct_food_id'])

    def test_unbound_or_changed_companions_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source,out=self.fixture(Path(folder))
            with (source/'ifct_source_profiles.json').open('a') as stream:stream.write(' ')
            with self.assertRaises(ValueError):exporter.export_ifct_companions(source,out)
            self.assertEqual(list(out.iterdir()),[])

    def test_no_additional_projected_nutrients(self):
        with tempfile.TemporaryDirectory() as folder:
            source,out=self.fixture(Path(folder))
            profiles=json.loads((source/'ifct_source_profiles.json').read_text())
            profiles['A018']['target_components'][0]['target_field']='Nut_Carbohydrates'
            with self.assertRaises(ValueError):exporter.sanitized_ifct_profiles(profiles)

    def test_release_units_and_review_descriptions(self):
        expected={'ifct_food_occurrence_count':'1','ifct_energy_available_occurrence_count':'1',
            'energy_available_count':'1','ifct_computed_energy_kcal':'kcal',
            'computed_ingredient_energy_kcal':'kcal','ifct_computed_energy_fraction':'1'}
        for key,unit in expected.items():self.assertEqual(COLUMN_UNITS[key]['unit'],unit)
        for key in ['ifct_food_review_status','ifct_food_review_id','ifct_source_food_basis',
            'ifct_source_manifest_sha256','ifct_weight_policy','legacy_match_review_status','legacy_match_review_id']:
            self.assertTrue(COLUMN_NOTES[key]);self.assertEqual(exporter.check_licence('ingredients_nutrition',[key]),[])
        self.assertIn('Null is valid',COLUMN_NOTES['fct_idx'])

    def test_main_preserves_ifct_identity_and_all_seven_review_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            source,out=self.fixture(Path(folder))
            for name in ['prep_features.parquet','prep_ingredient.parquet',
                         'ingredients_recovered.parquet','ingredients_weights.parquet']:
                pd.DataFrame({'recipe_id':[1]}).to_parquet(source/name,index=False)
            review_fields=['ifct_food_review_status','ifct_food_review_id','ifct_source_food_basis',
                'ifct_source_manifest_sha256','ifct_weight_policy','legacy_match_review_status','legacy_match_review_id']
            row=dict(recipe_id=1,ing_index=0,fct_source='IFCT2017',fct_food_id='A018',fct_idx=None,
                Nut_Carbohydrates=None,match_review_status='agent_reviewed_source_identity')
            row.update({key:'structured_'+key for key in review_fields})
            before=pd.DataFrame([row]);before.to_parquet(source/'ingredients_nutrition.parquet',index=False)
            with patch.object(exporter,'INCLUDE',[]),patch.object(exporter,'DROP_IDS',set()),\
                 patch.object(sys,'argv',['build_enrichment.py','--source',str(source),'--out',str(out)]),\
                 patch('sys.stdout',new_callable=io.StringIO):
                self.assertEqual(exporter.main(),0)
            result=pd.read_parquet(out/'ingredients_nutrition.parquet')
            pd.testing.assert_frame_equal(result,before)
            manifest=json.loads((out/'ENRICHMENT_MANIFEST.json').read_text())
            self.assertIn('recipe_ifct_fraction.parquet',{r['table'] for r in manifest['tables']})
            self.assertEqual(len(manifest['metadata']),2)

    def test_ifct_share_target_is_stamped_with_values_and_nulls_preserved(self):
        import pyarrow.parquet as pq
        relative='data/enrichment/recipe_ifct_fraction.parquet'
        self.assertIn(relative,stamp_units.TARGETS)
        with tempfile.TemporaryDirectory() as folder:
            source,out=self.fixture(Path(folder))
            (out/'docs').mkdir()
            target=out/relative;target.parent.mkdir(parents=True)
            target.write_bytes((source/'recipe_ifct_fraction.parquet').read_bytes())
            before=pd.read_parquet(target)
            # Exercise main and its actual TARGETS, rather than calling stamp()
            # directly: omission from the target list caused this regression.
            with patch.object(stamp_units,'REPO_ROOT',out),patch('sys.stdout',new_callable=io.StringIO):
                self.assertEqual(stamp_units.main(),0)
            pd.testing.assert_frame_equal(pd.read_parquet(target),before,check_exact=True)
            schema=pq.read_schema(target)
            for column in before.columns:
                if column=='fraction_basis':continue  # categorical availability state
                declaration=COLUMN_UNITS[column]
                metadata=schema.field(column).metadata
                self.assertEqual(metadata[b'unit'].decode(),declaration['unit'])
                self.assertEqual(metadata[b'basis'].decode(),declaration['basis'])
                self.assertEqual(metadata[b'basis_note'].decode(),declaration['basis_note'])
            units=json.loads((out/'docs/UNITS.json').read_text(encoding='utf-8'))
            self.assertFalse(units['undeclared_numeric_columns'])
            self.assertEqual(len(units['files_stamped']),1)
            self.assertEqual(units['files_stamped'][0]['stamped'],7)

    def test_unit_stamping_remains_compatible_without_ifct_share(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'docs').mkdir()
            with patch.object(stamp_units,'REPO_ROOT',root),patch('sys.stdout',new_callable=io.StringIO):
                self.assertEqual(stamp_units.main(),0)
            self.assertFalse((root/'data/enrichment/recipe_ifct_fraction.parquet').exists())
            units=json.loads((root/'docs/UNITS.json').read_text(encoding='utf-8'))
            self.assertEqual(units['files_stamped'],[])


if __name__=='__main__':unittest.main()
