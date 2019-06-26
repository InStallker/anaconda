#
# Copyright (C) 2019  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
# Red Hat Author(s): Jiri Konecny <jkonecny@redhat.com>
#
import unittest

from mock import Mock, patch

from pyanaconda.dbus.typing import get_native
from pyanaconda.modules.common.constants.objects import LIVE_OS_HANDLER
from pyanaconda.modules.common.structures.storage import DeviceData
from pyanaconda.modules.common.task import TaskInterface
from pyanaconda.modules.payload.live.live_os import LiveOSHandlerModule
from pyanaconda.modules.payload.live.live_os_interface import LiveOSHandlerInterface
from pyanaconda.modules.payload.live.initialization import SetupInstallationSourceTask, \
    TeardownInstallationSourceTask
from pyanaconda.modules.common.errors.payload import SourceSetupError


class LiveOSHandlerInterfaceTestCase(unittest.TestCase):

    def setUp(self):
        self.live_os_module = LiveOSHandlerModule()
        self.live_os_interface = LiveOSHandlerInterface(self.live_os_module)

        self.callback = Mock()
        self.live_os_interface.PropertiesChanged.connect(self.callback)

    def image_path_empty_properties_test(self):
        """Test Live OS handler image path property when not set."""
        self.assertEqual(self.live_os_interface.ImagePath, "")

    def image_path_properties_test(self):
        """Test Live OS handler image path property is correctly set."""
        self.live_os_interface.SetImagePath("/my/supper/image/path")
        self.assertEqual(self.live_os_interface.ImagePath, "/my/supper/image/path")
        self.callback.assert_called_once_with(
            LIVE_OS_HANDLER.interface_name, {"ImagePath": "/my/supper/image/path"}, [])

    def empty_state_properties_test(self):
        """Test Live OS default state."""
        self.assertEqual(self.live_os_interface.State, "started")

    def state_properties_test(self):
        """Test Live OS set state."""
        self.live_os_interface.SetState("installing")
        self.assertEqual(self.live_os_interface.State, "installing")
        self.callback.assert_called_once_with(
            LIVE_OS_HANDLER.interface_name, {"State": "installing"}, [])

    @patch("pyanaconda.modules.payload.live.live_os.stat")
    @patch("os.stat")
    def detect_live_os_image_test(self, os_stat, stat):
        """Test detect Live OS base image method."""
        stat.S_ISBLK = Mock()
        stat.S_ISBLK.return_value = True
        ret = self.live_os_interface.DetectLiveOSImage()

        # return the first known image from the list
        # See DetectLiveOSImage image code for the list
        self.assertEqual("/dev/mapper/live-base", ret)

    @patch("pyanaconda.modules.payload.live.live_os.stat")
    @patch("os.stat")
    def detect_live_os_image_nothing_found_test(self, os_stat, stat):
        """Test detect Live OS base image method when image doesn't exists."""
        stat.S_ISBLK = Mock()
        stat.S_ISBLK.return_value = False

        ret = self.live_os_interface.DetectLiveOSImage()

        # return empty string because there is no valid image found
        self.assertEqual("", ret)

    @patch('pyanaconda.dbus.DBus.publish_object')
    def setup_installation_source_task_test(self, publisher):
        """Test Live OS is able to create a setup installation source task."""
        task_path = self.live_os_interface.SetupInstallationSourceWithTask()

        publisher.assert_called_once()
        object_path, obj = publisher.call_args[0]

        self.assertEqual(task_path, object_path)
        self.assertIsInstance(obj, TaskInterface)

        self.assertIsInstance(obj.implementation, SetupInstallationSourceTask)

    @patch('pyanaconda.dbus.DBus.publish_object')
    def teardown_installation_source_task_test(self, publisher):
        """Test Live OS is able to create a teardown installation source task."""
        task_path = self.live_os_interface.TeardownInstallationSourceWithTask()

        publisher.assert_called_once()
        object_path, obj = publisher.call_args[0]

        self.assertEqual(task_path, object_path)
        self.assertIsInstance(obj, TaskInterface)

        self.assertIsInstance(obj.implementation, TeardownInstallationSourceTask)


class LiveOSHandlerTasksTestCase(unittest.TestCase):

    def setUp(self):
        self.live_os_module = LiveOSHandlerModule()
        self.live_os_interface = LiveOSHandlerInterface(self.live_os_module)

        self.callback = Mock()
        self.live_os_interface.PropertiesChanged.connect(self.callback)

    @patch("pyanaconda.modules.payload.live.initialization.mount")
    @patch("pyanaconda.modules.payload.live.initialization.stat")
    @patch("os.stat")
    @patch("pyanaconda.dbus.DBus.get_proxy")
    def setup_install_source_task_test(self, proxy_getter, os_stat, stat, mount):
        """Test Live OS setup installation source task."""
        device_tree = Mock()
        proxy_getter.return_value = device_tree
        device_tree.ResolveDevice = Mock()
        device_tree.ResolveDevice.return_value = "resolvedDeviceName"

        device = DeviceData()
        device.path = "/resolved/path/to/base/image"

        device_tree.GetDeviceData = Mock()
        device_tree.GetDeviceData.return_value = get_native(DeviceData.to_structure(device))

        mount.return_value = 0

        SetupInstallationSourceTask(
            "/path/to/base/image",
            "/path/to/mount/source/image"
        ).run()

        device_tree.ResolveDevice.assert_called_once_with("/path/to/base/image")
        os_stat.assert_called_once_with("/resolved/path/to/base/image")

    @patch("pyanaconda.dbus.DBus.get_proxy")
    def setup_install_source_task_missing_image_test(self, proxy_getter):
        """Test Live OS setup installation source task missing image error."""
        device_tree = Mock()
        proxy_getter.return_value = device_tree
        device_tree.ResolveDevice = Mock()
        device_tree.ResolveDevice.return_value = ""

        with self.assertRaises(SourceSetupError):
            SetupInstallationSourceTask(
                "/path/to/base/image",
                "/path/to/mount/source/image"
            ).run()

    @patch("pyanaconda.modules.payload.live.initialization.mount")
    @patch("pyanaconda.modules.payload.live.initialization.stat")
    @patch("os.stat")
    @patch("pyanaconda.dbus.DBus.get_proxy")
    def setup_install_source_task_failed_to_mount_test(self, proxy_getter, os_stat, stat, mount):
        """Test Live OS setup installation source task mount error."""
        device_tree = Mock()
        proxy_getter.return_value = device_tree
        device_tree.ResolveDevice = Mock()
        device_tree.ResolveDevice.return_value = "resolvedDeviceName"

        device = DeviceData()
        device.path = "/resolved/path/to/base/image"

        device_tree.GetDeviceData = Mock()
        device_tree.GetDeviceData.return_value = get_native(DeviceData.to_structure(device))

        mount.return_value = -20

        with self.assertRaises(SourceSetupError):
            SetupInstallationSourceTask(
                "/path/to/base/image",
                "/path/to/mount/source/image"
            ).run()
