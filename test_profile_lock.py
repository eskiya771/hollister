import subprocess
import sys
import tempfile
import unittest

from profile_lock import profile_lock


class ProfileLockTests(unittest.TestCase):
    def test_second_process_is_blocked_then_can_use_saved_profile(self):
        with tempfile.TemporaryDirectory() as profile:
            command = [sys.executable, '-c',
                       'from profile_lock import profile_lock; import sys\n'
                       'with profile_lock(sys.argv[1]): pass', profile]
            with profile_lock(profile):
                blocked = subprocess.run(command, capture_output=True, text=True)
                self.assertNotEqual(blocked.returncode, 0)
                self.assertIn('Browserprofil wird bereits verwendet', blocked.stderr)
            released = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(released.returncode, 0, released.stderr)


if __name__ == '__main__':
    unittest.main()
