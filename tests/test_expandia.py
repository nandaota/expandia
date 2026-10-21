from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
SCRIPTS=Path(__file__).resolve().parents[1]/'plugins/expandia/skills/upscale-natural/scripts'
sys.path.insert(0,str(SCRIPTS))
import doctor

class Profiles(unittest.TestCase):
    def test_memory_limits(self):
        self.assertEqual(doctor.recommend(2*1024**3,4)['max_output_pixels'],8_000_000)
        self.assertEqual(doctor.recommend(4*1024**3,4)['max_output_pixels'],16_000_000)
        self.assertEqual(doctor.recommend(16*1024**3,32)['max_output_pixels'],32_000_000)
        self.assertEqual(doctor.recommend(None,1)['threads'],1)

    def test_intel_mac_diagnostic(self):
        values={('sysctl','-n','hw.memsize'):str(8*1024**3),('sysctl','-n','hw.physicalcpu'):'4',
                ('sysctl','-n','machdep.cpu.brand_string'):'Intel Core i5'}
        with patch('doctor.platform.system',return_value='Darwin'),patch('doctor.platform.machine',return_value='x86_64'),patch('doctor.platform.mac_ver',return_value=('13.6',('','',''),'x86_64')),patch('doctor.command',side_effect=lambda args:values.get(tuple(args),'')):
            report=doctor.detect()
        self.assertEqual(report['ram_gib'],8)
        self.assertEqual(report['cpu'],'Intel Core i5')
        self.assertEqual(report['profile']['backend'],'ncnn-cpu')
        self.assertEqual(report['profile']['threads'],3)
        self.assertNotIn('serial',report)

class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import expandia
        expandia.libraries();cls.app=expandia

    def test_outputs_and_resume(self):
        from PIL import Image
        import numpy as np
        app=self.app;profile=doctor.detect()['profile']
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);source=folder/'imagem com acento é.png'
            Image.new('RGB',(19,13),(120,100,80)).save(source)
            twenty=app.upscale(source,folder,2,300,20,profile)
            thirty=app.upscale(source,folder,2,300,30,profile)
            self.assertEqual(twenty['output_pixels'],[38,26])
            self.assertEqual(thirty['strength'],30)
            self.assertTrue(app.upscale(source,folder,2,300,20,profile)['reused'])
            with Image.open(twenty['file']) as out:
                self.assertLess(abs(out.info['dpi'][0]-300),.1)
            # Proporção resulta da mistura, sem alterar o método base.
            image,_=app.read_image(source)
            base=app.fidelity(image,2)
            neural=app.neural(image,2,profile)
            with Image.open(twenty['file']) as out:
                np.testing.assert_array_equal(out,Image.blend(base,neural,.20))
            Image.new('RGB',(19,13),'red').save(source)
            with self.assertRaises(FileExistsError): app.upscale(source,folder,2,300,20,profile)

    def test_limit_and_cancel(self):
        from PIL import Image
        app=self.app;profile=doctor.detect()['profile']
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/'test.png';Image.new('RGB',(20,20)).save(file)
            with self.assertRaises(ValueError): app.plan(file,4,300,dict(profile,max_output_pixels=100))
            with self.assertRaises(InterruptedError): app.neural(Image.new('RGB',(8,8)),4,profile,cancel=lambda:True)

if __name__=='__main__': unittest.main()
