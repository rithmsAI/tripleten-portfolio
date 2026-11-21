import json
import unittest
import torch
from experiment import cohort,fit_scaler,metrics,choose_threshold,train,export_model,predict,experiment

class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.x,cls.y=cohort(17,100)
        cls.mean,cls.std=fit_scaler(cls.x)
        cls.model=train('mlp',17,(cls.x-cls.mean)/cls.std,cls.y)
        cls.artifact=export_model(cls.model,cls.mean,cls.std,.5)

    def test_reproducible_data(self):
        self.assertTrue(torch.equal(self.x,cohort(17,100)[0]))
    def test_separate_cohorts(self):
        self.assertFalse(torch.equal(self.x,cohort(1017,100)[0]))
    def test_scaling_train_only(self):
        x=(self.x-self.mean)/self.std
        self.assertTrue(torch.allclose(x.mean(0),torch.zeros(4),atol=1e-5))
    def test_scaler_handles_constant(self):
        self.assertTrue((fit_scaler(torch.ones(3,4))[1]>0).all())
    def test_confusion_matrix(self):
        m=metrics(torch.tensor([1.,0.,1.,0.]),torch.tensor([.9,.8,.2,.1]),.5)
        self.assertEqual([m[k] for k in ('tp','fp','tn','fn')],[1,1,1,1])
    def test_no_positives(self):
        self.assertEqual(metrics(torch.zeros(2),torch.zeros(2),.5)['f1'],0)
    def test_threshold_respects_validation_budget(self):
        y=torch.tensor([0.,0.,0.,1.]);s=torch.tensor([.9,.1,.2,.8])
        t=choose_threshold(y,s,0)
        self.assertEqual(metrics(y,s,t)['fpr'],0)
    def test_export_inference_parity(self):
        with torch.inference_mode(): expected=torch.sigmoid(self.model((self.x-self.mean)/self.std).squeeze(1))
        actual=predict(json.loads(json.dumps(self.artifact)),self.x.tolist())
        self.assertTrue(torch.allclose(torch.tensor(actual),expected,atol=1e-6))
    def test_invalid_rows(self):
        for rows in [[],[[1,2,3]],[[1,2,float('nan'),.2]],[[1,2,3,2]],[[True,2,3,.2]]]:
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):predict(self.artifact,rows)
    def test_bad_schema(self):
        with self.assertRaises(ValueError):predict({},[[1,2,3,.2]])
    def test_training_reproducible(self):
        other=train('mlp',17,(self.x-self.mean)/self.std,self.y)
        self.assertTrue(all(torch.equal(a,b) for a,b in zip(self.model.parameters(),other.parameters())))
    def test_full_experiment(self):
        r,_=experiment((17,))
        self.assertEqual(len(r['runs']),2)
        self.assertTrue(all(run['validation']['fpr']<=.05 for run in r['runs']))

if __name__=='__main__':unittest.main()
