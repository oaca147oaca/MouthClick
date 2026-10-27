import unittest
from types import SimpleNamespace

import numpy as np

from mouthclick_alignment import lighting_state


class LightingTests(unittest.TestCase):
    def setUp(self):
        self.points = [SimpleNamespace(x=.5, y=.5) for _ in range(478)]
        for i, x, y in [(10,.5,.2),(338,.65,.25),(454,.75,.5),(397,.65,.7),
                        (152,.5,.8),(172,.35,.7),(234,.25,.5),(109,.35,.25)]:
            self.points[i] = SimpleNamespace(x=x, y=y)

    def test_exposure_levels(self):
        for value, expected in [(20, 'baja'), (130, 'adecuada'), (250, 'Demasiada')]:
            with self.subTest(value=value):
                ok, text = lighting_state(np.full((120,160,3),value,np.uint8), self.points)
                self.assertEqual(ok, value == 130)
                self.assertIn(expected, text)

    def test_uneven_light(self):
        frame = np.full((120,160,3),80,np.uint8)
        frame[:,80:] = 180
        self.assertIn('desigual', lighting_state(frame,self.points)[1])

    def test_bright_background_does_not_hide_dark_face(self):
        frame = np.full((120,160,3),255,np.uint8)
        frame[20:100,35:125] = 25
        self.assertIn('baja', lighting_state(frame,self.points)[1])

    def test_missing_and_tiny_face(self):
        frame = np.full((120,160,3),130,np.uint8)
        self.assertFalse(lighting_state(frame,None)[0])
        self.assertFalse(lighting_state(None,self.points)[0])
        for point in self.points:
            point.x = point.y = .5
        self.assertFalse(lighting_state(frame,self.points)[0])


if __name__ == '__main__':
    unittest.main()
